"""Extract SOS day-of-year metrics from smoothed beech time series.

This script is publication-safe and works on the small sample CSV files
included in this repository. It reads a smoothed time-series table, computes
SOS for NDVI, EVI, and IRECI, excludes 2017, and writes one combined table
plus one CSV per year.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


VEG_INDICES = ["NDVI", "EVI", "IRECI"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract SOS DOY metrics from smoothed vegetation-index time series."
    )
    parser.add_argument(
        "--sample-csv",
        type=Path,
        default=Path("data/beech_sample_50pixels.csv"),
        help="CSV with selected sample pixel IDs (P_ID only).",
    )
    parser.add_argument(
        "--smoothed-timeseries-csv",
        type=Path,
        default=Path("data/beech_sample_50pixels_timeseries_smoothed.csv"),
        help="CSV with smoothed NDVI, EVI, and IRECI time series.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory where yearly SOS tables will be written.",
    )
    parser.add_argument("--patch-name", default="33TVL_2_1_0_1")
    parser.add_argument("--sos-threshold", type=float, default=0.5)
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2021)
    return parser.parse_args()


def calculate_sos_from_smoothed_series(
    pheno_df: pd.DataFrame,
    vi_columns: list[str],
    sos_threshold: float,
) -> pd.DataFrame:
    rows = []

    for p_id, p_id_data in pheno_df.groupby("P_ID"):
        p_id_data = p_id_data.copy()
        p_id_data["TIMESTAMP"] = pd.to_datetime(p_id_data["TIMESTAMP"])
        p_id_data = p_id_data.set_index("TIMESTAMP").sort_index()

        for year, year_data in p_id_data.groupby(p_id_data.index.year):
            for vi_name in vi_columns:
                point = year_data[vi_name].dropna()
                if point.empty:
                    continue

                max_value = point.max()
                max_index = point.idxmax()
                left = point.loc[:max_index]
                if left.empty:
                    continue

                min_idx_left = left.idxmin()
                min_value_left = left.min()
                amplitude_sos = max_value - min_value_left
                if amplitude_sos <= 0:
                    continue

                sos_value = (amplitude_sos * sos_threshold) + min_value_left
                sos_idx = point.loc[min_idx_left:max_index].sub(sos_value).abs().idxmin()

                rows.append(
                    {
                        "P_ID": p_id,
                        "YEAR": year,
                        "Column_Name": vi_name,
                        "SOS_idx": sos_idx,
                        "SOS_DOY": sos_idx.dayofyear,
                    }
                )

    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    sample_pixels = pd.read_csv(args.sample_csv)
    sample_pixels["P_ID"] = sample_pixels["P_ID"].astype("int64")

    smoothed_ts_df = pd.read_csv(args.smoothed_timeseries_csv)
    smoothed_ts_df["P_ID"] = smoothed_ts_df["P_ID"].astype("int64")
    smoothed_ts_df["TIMESTAMP"] = pd.to_datetime(smoothed_ts_df["TIMESTAMP"])

    sos_long_df = calculate_sos_from_smoothed_series(
        smoothed_ts_df,
        vi_columns=VEG_INDICES,
        sos_threshold=args.sos_threshold,
    )

    years_to_keep = range(args.start_year, args.end_year + 1)
    sos_long_df = sos_long_df[sos_long_df["YEAR"].isin(years_to_keep)].copy()
    sos_long_df = sos_long_df.sort_values(["P_ID", "YEAR", "Column_Name"]).reset_index(
        drop=True
    )

    sos_wide_df = (
        sos_long_df.pivot_table(
            index=["P_ID", "YEAR"],
            columns="Column_Name",
            values="SOS_DOY",
            aggfunc="first",
        )
        .reset_index()
        .rename(
            columns={
                "NDVI": "NDVI_SOS_DOY",
                "EVI": "EVI_SOS_DOY",
                "IRECI": "IRECI_SOS_DOY",
            }
        )
    )

    sos_wide_df = sample_pixels.merge(sos_wide_df, on="P_ID", how="inner")
    sos_wide_df = sos_wide_df.sort_values(["YEAR", "P_ID"]).reset_index(drop=True)

    combined_output = (
        args.output_dir
        / f"beech_sample_50pixels_sos_doy_wide_{args.start_year}_{args.end_year}.csv"
    )
    sos_wide_df.to_csv(combined_output, index=False)
    print(f"Saved combined SOS table to {combined_output}")

    for year in years_to_keep:
        year_df = sos_wide_df[sos_wide_df["YEAR"] == year].copy()
        year_output = (
            args.output_dir
            / f"beech_sample_50pixels_sos_doy_wide_{year}.csv"
        )
        year_df.to_csv(year_output, index=False)
        print(f"Saved {year} SOS table to {year_output}")


if __name__ == "__main__":
    main()
