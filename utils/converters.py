import pandas as pd

def convert_dataframe_types(df):
    df["Budget Per Project"] = pd.to_numeric(df["Budget Per Project"], errors="coerce")
    df["Total Budget"] = pd.to_numeric(df["Total Budget"], errors="coerce")
    df["Number of Projects"] = pd.to_numeric(df["Number of Projects"], errors="coerce")
    df["Opening Date"] = pd.to_datetime(df["Opening Date"], errors="coerce", dayfirst=True)
    df["Deadline"] = pd.to_datetime(df["Deadline"], errors="coerce", dayfirst=True)
    return df
