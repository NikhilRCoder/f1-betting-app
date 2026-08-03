"""Tests for the feature-engineering pipeline."""
from __future__ import annotations

from pathlib import Path

from models.feature_engineering import FEATURE_COLUMNS, TARGET_COLUMN, FeatureEngineer


def test_matrix_shape_and_columns(model_db: Path):
    fe = FeatureEngineer(db_path=model_db)
    matrix = fe.build_matrix()
    # 12 races x 5 drivers.
    assert len(matrix) == 60
    for col in FEATURE_COLUMNS:
        assert col in matrix.columns
    assert TARGET_COLUMN in matrix.columns
    assert "finish_pos" in matrix.columns


def test_no_nan_features(model_db: Path):
    fe = FeatureEngineer(db_path=model_db)
    matrix = fe.build_matrix()
    assert int(matrix[list(FEATURE_COLUMNS)].isna().sum().sum()) == 0


def test_first_appearance_is_leak_free(model_db: Path):
    """A driver's first race must carry neutral defaults, not race outcomes."""
    fe = FeatureEngineer(db_path=model_db)
    matrix = fe.build_matrix().sort_values(["date", "race_id"])
    first_race_id = matrix["race_id"].iloc[0]
    first = matrix[matrix["race_id"] == first_race_id]
    # With no prior history, career win rate must be the 0.0 default for all.
    assert (first["career_win_rate"] == 0.0).all()


def test_target_matches_win(model_db: Path):
    fe = FeatureEngineer(db_path=model_db)
    matrix = fe.build_matrix()
    winners = matrix[matrix[TARGET_COLUMN] == 1]
    # Every flagged winner actually finished first.
    assert (winners["finish_pos"] == 1).all()


def test_build_race_features_subset(model_db: Path):
    fe = FeatureEngineer(db_path=model_db)
    race = fe.build_race_features(12)
    assert len(race) == 5
    assert set(race["race_id"]) == {12}
