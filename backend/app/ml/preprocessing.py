"""
FloodSense AI - Data Preprocessing Pipeline
Handles: NaN precipitation, inf water_area_pct_change, duplicates,
         anomalous rows, elevation merge, class imbalance
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from typing import Tuple, Optional
import logging
import warnings

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────
NUMERIC_FEATURES = [
    "elevation", "evaporation", "latitude", "longitude",
    "precipitation", "pressure", "soil_moisture", "temperature",
    "water_area_km2", "wind_speed", "humidity",
    "precip_3day_avg", "precip_7day_avg", "temp_3day_avg",
    "soil_3day_avg", "water_area_change", "water_area_pct_change",
    "day_of_year", "month", "year", "is_monsoon",
]

CATEGORICAL_FEATURES = ["district"]
TARGET_COL = "flood_event"

INF_CAP_PCT = 500.0  # Cap water_area_pct_change at ±500%
PRESSURE_MIN = 80000   # Pa — below is anomalous
PRESSURE_MAX = 110000  # Pa — above is anomalous
SOIL_MIN = 0.0
SOIL_MAX = 1.0
WIND_MAX = 60.0        # m/s — above hurricane force
HUMIDITY_MIN = 0.0
HUMIDITY_MAX = 100.0


# ─── Step 1: Load & Merge ─────────────────────────────────────────────────────
def load_and_merge(
    training_path: str,
    elevation_path: str,
    ndma_path: Optional[str] = None,
) -> pd.DataFrame:
    """Load all datasets and merge elevation reference."""
    df = pd.read_csv(training_path, parse_dates=["date"], dayfirst=True)
    elev = pd.read_csv(elevation_path)

    # Normalize district names for join
    df["district_key"] = df["district"].str.strip().str.lower()
    elev["district_key"] = elev["district"].str.strip().str.lower()

    df = df.merge(
        elev[["district_key", "avg_elevation_m", "terrain_type"]],
        on="district_key",
        how="left",
    )
    df.drop(columns=["district_key"], inplace=True)

    # If elevation column already exists from training data, prefer merged one
    if "avg_elevation_m" in df.columns and "elevation" in df.columns:
        df["elevation_merged"] = df["avg_elevation_m"].fillna(df["elevation"])
    else:
        df["elevation_merged"] = df.get("avg_elevation_m", df.get("elevation", np.nan))

    logger.info(f"Loaded {len(df)} rows from {training_path}")
    logger.info(f"Elevation merge coverage: {df['avg_elevation_m'].notna().mean():.1%}")
    return df


# ─── Step 2: Remove Duplicates ────────────────────────────────────────────────
def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove exact duplicates before any split."""
    before = len(df)
    subset = ["date", "district", "precipitation", "temperature", "flood_event"]
    subset_present = [c for c in subset if c in df.columns]
    df = df.drop_duplicates(subset=subset_present, keep="first")
    removed = before - len(df)
    if removed:
        logger.info(f"Removed {removed} duplicate rows")
    return df.reset_index(drop=True)


# ─── Step 3: Anomaly Detection ────────────────────────────────────────────────
def flag_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Flag impossible/anomalous rows without dropping (for transparency)."""
    df = df.copy()
    df["anomaly_flag"] = 0

    # Impossible soil moisture
    if "soil_moisture" in df.columns:
        mask = (df["soil_moisture"] < SOIL_MIN - 0.05) | (df["soil_moisture"] > SOIL_MAX + 0.05)
        df.loc[mask, "anomaly_flag"] = 1
        logger.info(f"Soil moisture anomalies: {mask.sum()}")

    # Impossible humidity
    if "humidity" in df.columns:
        mask = (df["humidity"] < HUMIDITY_MIN) | (df["humidity"] > HUMIDITY_MAX)
        df.loc[mask, "anomaly_flag"] = 1
        logger.info(f"Humidity anomalies: {mask.sum()}")

    # Unrealistic pressure
    if "pressure" in df.columns:
        mask = (df["pressure"] < PRESSURE_MIN) | (df["pressure"] > PRESSURE_MAX)
        df.loc[mask, "anomaly_flag"] = 1
        logger.info(f"Pressure anomalies: {mask.sum()}")

    # Extreme wind
    if "wind_speed" in df.columns:
        mask = df["wind_speed"] > WIND_MAX
        df.loc[mask, "anomaly_flag"] = 1
        logger.info(f"Wind speed anomalies: {mask.sum()}")

    total = df["anomaly_flag"].sum()
    logger.info(f"Total anomalous rows flagged: {total} ({total/len(df):.1%})")
    return df


# ─── Step 4: Handle Missing Values ────────────────────────────────────────────
def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Impute NaN precipitation and other missing numerics."""
    df = df.copy()

    # Precipitation: NaN means no rain for that district-date → 0 is defensible
    # But use district-month median as smarter fallback
    if "precipitation" in df.columns:
        nan_count = df["precipitation"].isna().sum()
        if nan_count > 0:
            district_month_median = (
                df.groupby(["district", "month"])["precipitation"]
                .transform("median")
            )
            df["precipitation"] = df["precipitation"].fillna(district_month_median)
            # Final fallback: 0
            df["precipitation"] = df["precipitation"].fillna(0.0)
            logger.info(f"Imputed {nan_count} NaN precipitation values")

    # Other numerics: forward fill within district group, then global median
    num_cols = [c for c in NUMERIC_FEATURES if c in df.columns and c != "precipitation"]
    for col in num_cols:
        if df[col].isna().any():
            n = df[col].isna().sum()
            df[col] = df.groupby("district")[col].transform(
                lambda x: x.ffill().bfill()
            )
            df[col] = df[col].fillna(df[col].median())
            logger.info(f"Imputed {n} NaN values in '{col}'")

    return df


# ─── Step 5: Handle Infinite Values ───────────────────────────────────────────
def handle_infinite_values(df: pd.DataFrame) -> pd.DataFrame:
    """Cap water_area_pct_change; replace other inf values."""
    df = df.copy()

    if "water_area_pct_change" in df.columns:
        inf_count = np.isinf(df["water_area_pct_change"]).sum()
        df["water_area_pct_change"] = df["water_area_pct_change"].replace(
            [np.inf, -np.inf], np.nan
        )
        df["water_area_pct_change"] = df["water_area_pct_change"].clip(
            -INF_CAP_PCT, INF_CAP_PCT
        )
        df["water_area_pct_change"] = df["water_area_pct_change"].fillna(0.0)
        logger.info(f"Handled {inf_count} inf values in water_area_pct_change")

    # Global inf sweep
    for col in df.select_dtypes(include=[np.number]).columns:
        if np.isinf(df[col]).any():
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)
            df[col] = df[col].fillna(df[col].median())

    return df


# ─── Step 6: Feature Engineering ──────────────────────────────────────────────
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features that help flood prediction."""
    df = df.copy()

    # Composite flood stress index
    df["flood_stress_index"] = (
        df.get("precip_7day_avg", df.get("precipitation", 0)) * 0.4
        + df.get("soil_moisture", 0.5) * 0.3
        + df.get("water_area_pct_change", 0).clip(0, 500) / 500 * 0.3
    )

    # Soil saturation proxy
    if "soil_moisture" in df.columns and "precip_3day_avg" in df.columns:
        df["sat_proxy"] = df["soil_moisture"] * df["precip_3day_avg"]

    # Monsoon-precipitation interaction
    if "is_monsoon" in df.columns and "precipitation" in df.columns:
        df["monsoon_precip"] = df["is_monsoon"] * df["precipitation"]

    # Temperature-humidity heat index
    if "temperature" in df.columns and "humidity" in df.columns:
        df["heat_index"] = df["temperature"] + 0.33 * df["humidity"] - 4.0

    # Elevation risk factor (lower elevation = higher flood risk)
    elev_col = "avg_elevation_m" if "avg_elevation_m" in df.columns else "elevation_merged"
    if elev_col in df.columns:
        max_elev = df[elev_col].replace(0, np.nan).quantile(0.95)
        df["elevation_risk"] = 1.0 - (df[elev_col].clip(0, max_elev) / max_elev).fillna(0.5)

    # Day-of-year cyclical encoding
    if "day_of_year" in df.columns:
        df["doy_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)
        df["doy_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)

    # Month cyclical encoding
    if "month" in df.columns:
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    logger.info("Feature engineering complete")
    return df


# ─── Step 7: Encode Categoricals ──────────────────────────────────────────────
def encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode district and terrain_type."""
    df = df.copy()
    cols_to_encode = [c for c in ["district", "terrain_type"] if c in df.columns]
    df = pd.get_dummies(df, columns=cols_to_encode, drop_first=False, dtype=int)
    return df


# ─── Step 8: Get Final Feature List ───────────────────────────────────────────
def get_feature_columns(df: pd.DataFrame) -> list:
    """Return final list of feature columns (exclude target, metadata, flags)."""
    exclude = {
        TARGET_COL, "date", "ds_idx", "anomaly_flag",
        "district", "terrain_type", "district_key",
        "elevation",  # replaced by elevation_merged
        # Exclude features that may introduce leakage or overly optimistic signal
        "water_area_change", "water_area_pct_change",
        "precip_3day_avg", "precip_7day_avg",
        "temp_3day_avg", "soil_3day_avg",
    }
    return [c for c in df.columns if c not in exclude and df[c].dtype != object]


# ─── Full Pipeline ─────────────────────────────────────────────────────────────
def run_full_pipeline(
    training_path: str,
    elevation_path: str,
    ndma_path: Optional[str] = None,
    apply_smote: bool = True,
    test_size: float = 0.2,
    val_size: float = 0.1,
    random_state: int = 42,
) -> dict:
    """
    Run complete preprocessing pipeline.
    Returns dict with: X_train, X_val, X_test, y_train, y_val, y_test,
                       feature_names, scaler, raw_df
    """
    from sklearn.model_selection import GroupShuffleSplit

    # 1. Load & merge
    df = load_and_merge(training_path, elevation_path, ndma_path)

    # 2. Remove duplicates BEFORE split
    df = remove_duplicates(df)

    # 3. Flag anomalies
    df = flag_anomalies(df)

    # 4. Handle missing values
    df = handle_missing_values(df)

    # 5. Handle infinite values
    df = handle_infinite_values(df)

    # 6. Feature engineering
    df = engineer_features(df)

    # 7. Encode categoricals
    groups = df["district"].astype(str)
    df = encode_categoricals(df)

    # 8. Get features
    feature_cols = get_feature_columns(df)
    X = df[feature_cols].values.astype(np.float32)
    y = df[TARGET_COL].values.astype(int)

    # 9. Train/val/test split by district groups, preventing leakage across districts
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_val_idx, test_idx = next(splitter.split(X, y, groups=groups))
    X_train_val, X_test = X[train_val_idx], X[test_idx]
    y_train_val, y_test = y[train_val_idx], y[test_idx]
    groups_train_val = groups.iloc[train_val_idx]

    val_fraction = val_size / (1 - test_size)
    splitter = GroupShuffleSplit(n_splits=1, test_size=val_fraction, random_state=random_state)
    train_idx, val_idx = next(splitter.split(X_train_val, y_train_val, groups=groups_train_val))
    X_train, X_val = X_train_val[train_idx], X_train_val[val_idx]
    y_train, y_val = y_train_val[train_idx], y_train_val[val_idx]

    logger.info(f"Group split — Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    logger.info(f"Group info — districts train/val/test: {groups.iloc[train_val_idx].nunique()}/{groups_train_val.iloc[val_idx].nunique()}/{groups.iloc[test_idx].nunique()}")
    logger.info(f"Class balance (train) — 0: {(y_train==0).sum()}, 1: {(y_train==1).sum()}")

    # 10. Scale
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    X_test = scaler.transform(X_test)

    # 11. SMOTE for class imbalance
    if apply_smote and (y_train == 1).sum() > 5:
        try:
            smote = SMOTE(random_state=random_state, k_neighbors=5)
            X_train, y_train = smote.fit_resample(X_train, y_train)
            logger.info(f"After SMOTE — Train: {len(X_train)}, flood: {(y_train==1).sum()}")
        except Exception as e:
            logger.warning(f"SMOTE failed: {e}. Proceeding without.")

    return {
        "X_train": X_train,
        "X_val": X_val,
        "X_test": X_test,
        "y_train": y_train,
        "y_val": y_val,
        "y_test": y_test,
        "feature_names": feature_cols,
        "scaler": scaler,
        "raw_df": df,
        "n_features": len(feature_cols),
    }


# ─── Inference Preprocessor ───────────────────────────────────────────────────
def preprocess_single_input(
    input_dict: dict,
    feature_names: list,
    scaler: StandardScaler,
    elevation_lookup: Optional[dict] = None,
) -> np.ndarray:
    """
    Preprocess a single prediction request dict into a scaled feature vector.
    Never crashes on missing/extreme inputs.
    """
    row = {}

    # Fill from input
    for feat in feature_names:
        val = input_dict.get(feat, np.nan)
        if val is None or val == "":
            val = np.nan
        try:
            val = float(val)
        except (ValueError, TypeError):
            val = np.nan
        # Replace inf
        if np.isinf(val):
            val = np.nan
        row[feat] = val

    # Elevation lookup by district
    if elevation_lookup and "district" in input_dict:
        district = input_dict["district"].strip().lower()
        if np.isnan(row.get("elevation_merged", np.nan)):
            row["elevation_merged"] = elevation_lookup.get(district, 300.0)

    # Cap water_area_pct_change
    if "water_area_pct_change" in row:
        row["water_area_pct_change"] = np.clip(
            row.get("water_area_pct_change", 0), -INF_CAP_PCT, INF_CAP_PCT
        )

    vec = np.array([row.get(f, 0.0) for f in feature_names], dtype=np.float32)
    vec = np.nan_to_num(vec, nan=0.0, posinf=INF_CAP_PCT, neginf=-INF_CAP_PCT)
    vec = scaler.transform(vec.reshape(1, -1))
    return vec