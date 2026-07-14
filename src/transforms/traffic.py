import pandas as pd

CHANNEL_NAME_MAP = {
    "Organic Search": "Organic Search",
    "Paid Search": "Paid Search",
    "Direct": "Direct",
    "Referral": "Referral",
    "Organic Social": "Social",
    "Paid Social": "Social",
    "Cross-network": "Paid Search",
    "AI Assistant": "AI Assistant",
    "Organic Video": "Organic Video",
    "Email": "Email",
    "Unassigned": "Unassigned",
}


def normalize_channels(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["channel"] = df["channel"].map(CHANNEL_NAME_MAP).fillna("Other")
    df = (
        df.groupby("channel", as_index=False)
        .agg({"sessions": "sum", "users": "sum", "pageviews": "sum"})
    )

    total_sessions = df["sessions"].sum()
    df["pct_of_total"] = (
        (df["sessions"] / total_sessions * 100).round(2) if total_sessions > 0 else 0.0
    )

    return df.sort_values("sessions", ascending=False).reset_index(drop=True)


def add_week_start(df: pd.DataFrame, week_start: str) -> pd.DataFrame:
    df = df.copy()
    df.insert(0, "week_start", week_start)
    return df


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates(subset=["week_start", "channel"]).reset_index(drop=True)
