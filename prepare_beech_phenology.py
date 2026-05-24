"""Prepare beech phenology metrics from Sentinel-2 L2A parquet time series.

This script is a publication-safe template. It does not contain local paths.
Set the command-line arguments below to point to your own classification CSV,
Sentinel-2 L2A parquet directory, and output directory.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from smoothing import savitzky_golay_filtering


VEG_INDICES = ["NDVI", "EVI", "IRECI"]
SELECTED_BANDS = ["B02", "B04", "B05", "B06", "B07", "B08", "NDVI"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare SOS metrics for a random sample of beech pixels."
    )
    parser.add_argument(
        "--classification-csv",
        type=Path,
        required=True,
        help="Path to a CSV with P_ID, Razred, COORD_X, and COORD_Y columns.",
    )
    parser.add_argument(
        "--sentinel2-parquet-dir",
        type=Path,
        required=True,
        help="Path to the local Sentinel-2 L2A parquet time-series directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory where derived CSV outputs will be written.",
    )
    parser.add_argument("--patch-name", default="33TVL_2_1_0_1")
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--beech-class", type=int, default=2)
    parser.add_argument("--sos-threshold", type=float, default=0.5)
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2021)
    return parser.parse_args()


def prepare_beech_sample(
    classification_csv: Path,
    output_csv: Path,
    sample_size: int,
    random_state: int,
    beech_class: int,
) -> pd.DataFrame:
    df = pd.read_csv(classification_csv)
    beech_df = df[df["Razred"].astype(str) == str(beech_class)].copy()
    beech_df["P_ID"] = beech_df["P_ID"].astype("int64")
    beech_df = beech_df.drop_duplicates(subset=["P_ID"])

    if len(beech_df) < sample_size:
        raise ValueError(f"Only {len(beech_df)} unique beech P_ID values are available.")

    sample_df = (
        beech_df.sample(n=sample_size, random_state=random_state)
        .sort_values("P_ID")
        .reset_index(drop=True)
    )
    sample_df = sample_df[["P_ID"]]
    sample_df.to_csv(output_csv, index=False)
    return sample_df


def add_vegetation_indices(s2_df: pd.DataFrame) -> pd.DataFrame:
    s2_df = s2_df.copy()

    ireci_denominator = s2_df["B05"] / s2_df["B06"]
    s2_df["IRECI"] = np.where(
        (s2_df["B05"] != 0) & (s2_df["B06"] != 0) & (ireci_denominator != 0),
        (s2_df["B07"] - s2_df["B04"]) / ireci_denominator,
        np.nan,
    )

    evi_denominator = s2_df["B08"] + 6 * s2_df["B04"] - 7.5 * s2_df["B02"] + 1
    s2_df["EVI"] = np.where(
        evi_denominator != 0,
        2.5 * (s2_df["B08"] - s2_df["B04"]) / evi_denominator,
        np.nan,
    )
    return s2_df


def smooth_ts_7d_adjusted(group: pd.DataFrame) -> pd.DataFrame:
    group = group.sort_values("TIMESTAMP").copy()
    smoothed_data = (
        group.set_index("TIMESTAMP")[VEG_INDICES]
        .resample("7D")
        .mean()
        .apply(savitzky_golay_filtering)
        .resample("1D")
        .mean()
        .interpolate()
        .reset_index()
    )
    smoothed_data["P_ID"] = group["P_ID"].iloc[0]
    return smoothed_data


def calculate_sos(
    pheno_df: pd.DataFrame,
    sos_threshold: float,
) -> pd.DataFrame:
    rows = []

    for p_id, p_id_data in pheno_df.groupby("P_ID"):
        p_id_data = p_id_data.copy()
        p_id_data["TIMESTAMP"] = pd.to_datetime(p_id_data["TIMESTAMP"])
        p_id_data = p_id_data.set_index("TIMESTAMP").sort_index()

        for year, year_data in p_id_data.groupby(p_id_data.index.year):
            for vi_name in VEG_INDICES:
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
                        "Column_Name": vi_name,
                        "YEAR": year,
                        "SOS_idx": sos_idx,
                        "SOS_DOY": sos_idx.dayofyear,
                    }
                )

    return pd.DataFrame(rows)




def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    sample_csv = args.output_dir / f"beech_sample_{args.sample_size}pixels.csv"
    raw_timeseries_csv = (
        args.output_dir
        / f"beech_sample_{args.sample_size}pixels_timeseries_raw.csv"
    )
    smoothed_timeseries_csv = (
        args.output_dir
        / f"beech_sample_{args.sample_size}pixels_timeseries_smoothed.csv"
    )
    sos_csv = (
        args.output_dir
        / f"beech_sample_{args.sample_size}pixels_sos_ndvi_evi_ireci.csv"
    )
    pheno_head_csv = args.output_dir / "pheno_df_head.csv"
    tif_path = (
        args.output_dir
        / f"{args.patch_name}_beech_sample_{args.sample_size}pixels_sos_doy_ndvi_evi_ireci.tif"
    )

    sample_pixels = prepare_beech_sample(
        args.classification_csv,
        sample_csv,
        sample_size=args.sample_size,
        random_state=args.random_state,
        beech_class=args.beech_class,
    )
    sample_pids = sample_pixels["P_ID"].tolist()

    s2_df = pd.read_parquet(
        args.sentinel2_parquet_dir,
        columns=["P_ID", "TIMESTAMP", *SELECTED_BANDS, "CLP", "CLM", "OUT_PROBA", "EOPATCH"],
        filters=[
            ("EOPATCH", "==", args.patch_name),
            ("F_ID", "!=", -1),
            ("P_ID", "in", sample_pids),
        ],
    )
    s2_df = add_vegetation_indices(s2_df)

    cloud_mask = ((s2_df["CLP"] <= 0.54) | (s2_df["CLM"] <= 0.99)) & (
        s2_df["OUT_PROBA"] <= 0.5
    )
    s2_cf_cm = s2_df.loc[cloud_mask, ["P_ID", "TIMESTAMP", *VEG_INDICES]].copy()
    s2_cf_cm["P_ID"] = s2_cf_cm["P_ID"].astype("int64")
    s2_cf_cm["TIMESTAMP"] = pd.to_datetime(s2_cf_cm["TIMESTAMP"])
    s2_cf_cm[VEG_INDICES] = s2_cf_cm[VEG_INDICES].astype("float32")
    s2_cf_cm = s2_cf_cm.sort_values(["P_ID", "TIMESTAMP"]).reset_index(drop=True)
    s2_cf_cm.to_csv(raw_timeseries_csv, index=False)

    pheno_df = (
        s2_cf_cm.groupby("P_ID", group_keys=False)
        .apply(smooth_ts_7d_adjusted)
        .reset_index(drop=True)
    )
    pheno_df = pheno_df.sort_values(["P_ID", "TIMESTAMP"]).reset_index(drop=True)
    pheno_df.to_csv(smoothed_timeseries_csv, index=False)
    pheno_df.head().to_csv(pheno_head_csv, index=False)

    sos_df = calculate_sos(
        pheno_df,
        sos_threshold=args.sos_threshold,
    )
    years_to_keep = range(args.start_year, args.end_year + 1)
    result_df = sample_pixels.merge(sos_df, on="P_ID", how="inner")
    result_df = result_df[result_df["YEAR"].isin(years_to_keep)].copy()
    result_df = result_df.sort_values(["P_ID", "Column_Name", "YEAR"]).reset_index(drop=True)
    result_df.to_csv(sos_csv, index=False)

    print(f"Saved sample pixels to {sample_csv}")
    print(f"Saved raw masked time series to {raw_timeseries_csv}")
    print(f"Saved smoothed time series to {smoothed_timeseries_csv}")
    print(f"Saved pheno_df.head() to {pheno_head_csv}")
    print(f"Saved SOS results to {sos_csv}")


if __name__ == "__main__":
    main()
