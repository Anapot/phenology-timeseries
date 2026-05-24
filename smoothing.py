import pandas as pd
from scipy.signal import find_peaks, savgol_filter


def savitzky_golay_filtering(timeseries, window=5, order=3):
    """
    Performs Savitzky-Golay filtering on timeseries

    :param timeseries: satellite image timeseries
    :param window: filtering window
    :param order: polyorder
    :return: filtered satellite image timeseries
    """
    interp_ts = pd.Series(timeseries)
    interp_ts = interp_ts.interpolate(method="linear", axis=0).ffill().bfill()
    if len(interp_ts) < window:
        return interp_ts
    smoother_ts = savgol_filter(interp_ts, window_length=window, polyorder=order)
    return pd.Series(smoother_ts, index=interp_ts.index)
