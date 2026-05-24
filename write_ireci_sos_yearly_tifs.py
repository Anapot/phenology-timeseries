"""Write one IRECI SOS GeoTIFF per year from yearly SOS CSV tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create one GeoTIFF per year for IRECI SOS day-of-year values."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing yearly SOS CSV tables.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory where yearly GeoTIFF files will be written.",
    )
    parser.add_argument("--patch-name", default="33TVL_2_1_0_1")
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2021)
    return parser.parse_args()


def write_year_tif(year_df: pd.DataFrame, tif_path: Path) -> None:
    pixel_size = 10
    nodata = -9999

    year_df = year_df.dropna(subset=["COORD_X", "COORD_Y", "IRECI_SOS_DOY"]).copy()
    year_df["COORD_X"] = year_df["COORD_X"].astype(float)
    year_df["COORD_Y"] = year_df["COORD_Y"].astype(float)
    year_df["IRECI_SOS_DOY"] = year_df["IRECI_SOS_DOY"].round().astype("int16")

    min_x = year_df["COORD_X"].min()
    max_x = year_df["COORD_X"].max()
    min_y = year_df["COORD_Y"].min()
    max_y = year_df["COORD_Y"].max()

    width = int(round((max_x - min_x) / pixel_size)) + 1
    height = int(round((max_y - min_y) / pixel_size)) + 1
    transform = from_origin(
        min_x - pixel_size / 2,
        max_y + pixel_size / 2,
        pixel_size,
        pixel_size,
    )

    band = np.full((height, width), nodata, dtype=np.int16)
    cols = np.rint((year_df["COORD_X"].to_numpy() - min_x) / pixel_size).astype(int)
    rows = np.rint((max_y - year_df["COORD_Y"].to_numpy()) / pixel_size).astype(int)
    band[rows, cols] = year_df["IRECI_SOS_DOY"].to_numpy(dtype=np.int16)

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "int16",
        "crs": "EPSG:32633",
        "transform": transform,
        "nodata": nodata,
        "compress": "lzw",
    }

    with rasterio.open(tif_path, "w", **profile) as dst:
        dst.write(band, 1)
        dst.set_band_description(1, tif_path.stem)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for year in range(args.start_year, args.end_year + 1):
        year_csv = (
            args.input_dir
            / f"beech_sample_50pixels_sos_doy_wide_{year}.csv"
        )
        if not year_csv.exists():
            print(f"Skipping {year}: {year_csv} not found")
            continue

        year_df = pd.read_csv(year_csv)
        tif_path = args.output_dir / f"IRECI_SOS_DOY_{year}.tif"
        write_year_tif(year_df, tif_path)
        print(f"Saved {tif_path}")


if __name__ == "__main__":
    main()
