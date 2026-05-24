# Beech Phenology Reproducibility Sample

Author: Ana Potočnik Buhvald  
Affiliation: UL FGG  
Year: 2026

## Overview

This repository is a small reproducibility package for the data-preparation part of a beech phenology study in Slovenia.

It documents the time-series processing workflow used to derive spring onset phenology (SOS) from Sentinel-2 vegetation indices. The package is meant to make it clear that the main goal is time-series processing for phenology extraction.

It is not the full national processing archive. Instead, it provides a publication-friendly test sample built from 50 randomly selected beech pixels.

The package documents how the sample time series and derived SOS products were prepared and includes the CSV files needed to reproduce yearly SOS tables for the selected pixels.

## What Is Included

The repository contains:

- a sample table of 50 selected beech pixels;
- raw cloud-masked Sentinel-2 vegetation-index time series for those pixels;
- smoothed daily vegetation-index time series for those pixels;
- yearly SOS tables for 2018, 2019, 2020, and 2021;
- a combined SOS table for 2018-2021;
- small sample scripts and a notebook that document the workflow.

## What Is Not Included

The repository does not include:

- the complete Sentinel-2 L2A national time-series archive;
- the full code used to download and manage the complete national archive;
- the full production workflow used to generate nationwide layers for all EOPATCHes.

Those source data are large, publicly accessible, and were obtained independently from the Copernicus Data Space Ecosystem / Sentinel Hub Batch Processing API v2 workflow:

https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/BatchV2.html

Because the source archive is both very large and publicly available, only this small reproducibility sample is shared here.

## Study Context

In the full study workflow:

- Sentinel-2 L2A data were prepared for Slovenia;
- time-series parquet tables were generated per EOPATCH;
- vegetation indices were calculated;
- cloud masking was applied;
- time series were smoothed;
- SOS metrics were extracted;
- yearly map layers were produced for the whole country.

This repository contains only a small test example for that workflow, based on 50 randomly selected beech pixels. It documents the pre-processing steps used to generate the SOS IRECI GeoTIFF products that are published on Zenodo at DOI `10.5281/zenodo.20358835`.

## Processing Logic in This Sample

The sample follows these steps:

1. select 50 beech pixels from one classification table;
2. read Sentinel-2 L2A time-series values for the selected `P_ID` values;
3. keep only the bands required for `NDVI`, `EVI`, and `IRECI`;
4. calculate `EVI` and `IRECI` while using the existing `NDVI`;
5. apply cloud masking;
6. export raw cloud-masked time series;
7. smooth the series with a Savitzky-Golay filter;
8. interpolate the smoothed series to daily resolution;
9. calculate SOS using a relative threshold approach;
10. export yearly SOS tables.

The SOS threshold used in this package is `0.5`.

## Demo: demo_vegetation_index_sos_workflow

Below is a minimal demo showing how to create the yearly wide SOS CSV from
the smoothed time-series CSV using the helper from
`extract_sos_from_smoothed_timeseries.py`. This snippet is a concise
illustration — the notebook contains the full explanation and step-by-step
processing.

```python
# demo_vegetation_index_sos_workflow
from pathlib import Path
import pandas as pd

from extract_sos_from_smoothed_timeseries import calculate_sos_from_smoothed_series, VEG_INDICES

SMOOTHED = Path('data/beech_sample_50pixels_timeseries_smoothed.csv')
OUT = Path('outputs')
OUT.mkdir(exist_ok=True)

pheno_df = pd.read_csv(SMOOTHED, parse_dates=['TIMESTAMP'])
sos_long = calculate_sos_from_smoothed_series(pheno_df, vi_columns=VEG_INDICES, sos_threshold=0.5)
sos_long = sos_long[sos_long['YEAR'].isin(range(2018, 2022))]

sos_wide = (
  sos_long.pivot_table(index=['P_ID', 'YEAR'], columns='Column_Name', values='SOS_DOY', aggfunc='first')
  .reset_index()
  .rename(columns={'NDVI': 'NDVI_SOS_DOY', 'EVI': 'EVI_SOS_DOY', 'IRECI': 'IRECI_SOS_DOY'})
)

out_path = OUT / 'beech_sample_50pixels_sos_doy_wide_2018_2021.csv'
sos_wide.to_csv(out_path, index=False)
print('Saved', out_path)
```

## Repository Structure

```text
github_publication/
  README.md
  requirements.txt
  smoothing.py
  Phenology_data_preparation.ipynb
  prepare_beech_phenology.py
  extract_sos_from_smoothed_timeseries.py
  write_ireci_sos_yearly_tifs.py
  data/
    beech_sample_50pixels.csv
    beech_sample_50pixels_timeseries_raw.csv
    beech_sample_50pixels_timeseries_smoothed.csv
    beech_sample_50pixels_sos_doy_wide_2018.csv
    beech_sample_50pixels_sos_doy_wide_2019.csv
    beech_sample_50pixels_sos_doy_wide_2020.csv
    beech_sample_50pixels_sos_doy_wide_2021.csv
    beech_sample_50pixels_sos_doy_wide_2018_2021.csv
  maps/
    beech_sample_50pixels.tif
    IRECI_SOS_DOY_2018.tif
    IRECI_SOS_DOY_2019.tif
    IRECI_SOS_DOY_2020.tif
    IRECI_SOS_DOY_2021.tif
```

## Key Input and Output Files

### Selected Pixel Table

`data/beech_sample_50pixels.csv`

Columns:

- `P_ID`

This sample table contains the selected pixel identifiers only; spatial and classification metadata have been removed.

### Raw Time Series

`data/beech_sample_50pixels_timeseries_raw.csv`

Columns:

- `P_ID`
- `TIMESTAMP`
- `NDVI`
- `EVI`
- `IRECI`

This file contains cloud-masked observed time-series values.

### Smoothed Time Series

`data/beech_sample_50pixels_timeseries_smoothed.csv`

Columns:

- `TIMESTAMP`
- `NDVI`
- `EVI`
- `IRECI`
- `P_ID`

This file contains the smoothed and daily interpolated time series. It is the key input for SOS extraction in the public sample package.

### Yearly SOS Tables

Files:

- `data/beech_sample_50pixels_sos_doy_wide_2018.csv`
- `data/beech_sample_50pixels_sos_doy_wide_2019.csv`
- `data/beech_sample_50pixels_sos_doy_wide_2020.csv`
- `data/beech_sample_50pixels_sos_doy_wide_2021.csv`

Columns:

- `P_ID`
- `YEAR`
- `NDVI_SOS_DOY`
- `EVI_SOS_DOY`
- `IRECI_SOS_DOY`
- `IRECI_SOS_DOY`

### Example Maps

Files:

- `maps/IRECI_SOS_DOY_2018.tif`
- `maps/IRECI_SOS_DOY_2019.tif`
- `maps/IRECI_SOS_DOY_2020.tif`
- `maps/IRECI_SOS_DOY_2021.tif`

These are example yearly raster outputs in `EPSG:32633`.

## How To Reproduce the Sample Outputs

Install dependencies:

```bash
pip install -r requirements.txt
```

### 1. Prepare Sample Time Series From a Local Parquet Archive

This step requires your own local Sentinel-2 L2A parquet archive.

```bash
python prepare_beech_phenology.py ^
  --classification-csv data/beech_sample_50pixels.csv ^
  --sentinel2-parquet-dir ADD_PATH_TO_SENTINEL2_L2A_PARQUET_DIRECTORY ^
  --output-dir outputs
```

This creates:

- `..._timeseries_raw.csv`
- `..._timeseries_smoothed.csv`

### 2. Extract SOS From the Smoothed Time Series

This step works directly on the included sample CSV files.

```bash
python extract_sos_from_smoothed_timeseries.py --output-dir outputs
```

This creates:

- one combined SOS CSV for 2018-2021;
- one yearly SOS CSV for each year 2018, 2019, 2020, and 2021.

### 3. Write Yearly IRECI SOS GeoTIFF Files

```bash
python write_ireci_sos_yearly_tifs.py --input-dir outputs --output-dir outputs
```

This creates one `IRECI_SOS_DOY` GeoTIFF per year.

## Reproducibility Scope

This package is intended to document and test the data-preparation logic on a small example. It is not a release of the full national archive.

The included files are sufficient to:

- inspect the selected-pixel sample;
- inspect raw and smoothed vegetation-index time series;
- regenerate yearly SOS CSV tables from the smoothed sample time series;
- regenerate yearly IRECI SOS GeoTIFF maps for the sample pixels.

## Notes

- Source Sentinel-2 L2A data are publicly accessible and were obtained through the CDSE Sentinel Hub Batch Processing API v2 workflow linked above.
- The sample repository includes only a small subset needed to illustrate and test the workflow.
- The nationwide annual layers for 2018-2021 are separate study products and are not stored in this repository.
