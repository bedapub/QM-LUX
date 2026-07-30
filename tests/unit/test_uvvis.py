# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for qm_lux/utils/uvvis.py."""
import numpy as np
import pandas as pd
import pytest

from qm_lux.utils.uvvis import (
    AUC_meas_entire_from250_pred,
    AUC_meas_entire_pred,
    AUC_meas_entire_to700_pred,
    run_AUCs_spectra,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy(df):
    """Return a copy so mutation inside the function under test doesn't bleed."""
    return df.copy()


# ---------------------------------------------------------------------------
# AUC_meas_entire_from250_pred
# ---------------------------------------------------------------------------

class TestAUCFrom250:
    def test_output_is_dataframe(self, uvvis_df):
        seg = np.arange(260, 360, 10)
        result = AUC_meas_entire_from250_pred(_copy(uvvis_df), seg, "trapz")
        assert isinstance(result, pd.DataFrame)

    def test_srn_column_present(self, uvvis_df):
        seg = np.arange(260, 360, 10)
        result = AUC_meas_entire_from250_pred(_copy(uvvis_df), seg, "trapz")
        assert "SRN" in result.columns

    def test_column_names_follow_250_convention(self, uvvis_df):
        seg = np.arange(260, 360, 10)
        result = AUC_meas_entire_from250_pred(_copy(uvvis_df), seg, "trapz")
        auc_cols = [c for c in result.columns if c != "SRN"]
        assert all(c.startswith("250-") and c.endswith("pred") for c in auc_cols)

    def test_one_row_per_molecule(self, uvvis_df):
        seg = np.arange(260, 360, 10)
        result = AUC_meas_entire_from250_pred(_copy(uvvis_df), seg, "trapz")
        assert len(result) == uvvis_df["SRN"].nunique()

    def test_auc_values_positive(self, uvvis_df):
        seg = np.arange(260, 360, 10)
        result = AUC_meas_entire_from250_pred(_copy(uvvis_df), seg, "trapz")
        auc_cols = [c for c in result.columns if c != "SRN"]
        assert (result[auc_cols].astype(float) >= 0).all().all()

    def test_monotone_cumulative_auc(self, uvvis_df):
        """250-350 AUC must be >= 250-260 AUC (wider range = more area)."""
        seg = np.arange(260, 360, 10)
        result = AUC_meas_entire_from250_pred(_copy(uvvis_df), seg, "trapz")
        # last real column is 250-350pred; 700 is the sentinel boundary, not a column
        auc_wide = float(result["250-350pred"].iloc[0])
        auc_narrow = float(result["250-260pred"].iloc[0])
        assert auc_wide >= auc_narrow

    def test_raises_when_spectrum_too_short(self, uvvis_df):
        """Segment endpoint beyond spectrum max should raise ValueError."""
        seg = np.arange(260, 1100, 10)   # goes past 1000 nm
        with pytest.raises(ValueError):
            AUC_meas_entire_from250_pred(_copy(uvvis_df), seg, "trapz")


# ---------------------------------------------------------------------------
# AUC_meas_entire_to700_pred
# ---------------------------------------------------------------------------

class TestAUCTo700:
    def test_output_is_dataframe(self, uvvis_df):
        seg = np.arange(250, 360, 10)
        result = AUC_meas_entire_to700_pred(_copy(uvvis_df), seg, "trapz")
        assert isinstance(result, pd.DataFrame)

    def test_column_names_follow_to700_convention(self, uvvis_df):
        seg = np.arange(250, 360, 10)
        result = AUC_meas_entire_to700_pred(_copy(uvvis_df), seg, "trapz")
        auc_cols = [c for c in result.columns if c != "SRN"]
        assert all(c.endswith("-700pred") for c in auc_cols)

    def test_auc_values_positive(self, uvvis_df):
        seg = np.arange(250, 360, 10)
        result = AUC_meas_entire_to700_pred(_copy(uvvis_df), seg, "trapz")
        auc_cols = [c for c in result.columns if c != "SRN"]
        assert (result[auc_cols].astype(float) >= 0).all().all()

    def test_monotone_cumulative_auc(self, uvvis_df):
        """250-700 AUC must be >= 350-700 AUC (starting earlier = more area)."""
        seg = np.arange(250, 360, 10)
        result = AUC_meas_entire_to700_pred(_copy(uvvis_df), seg, "trapz")
        auc_full = float(result["250-700pred"].iloc[0])
        auc_late = float(result["350-700pred"].iloc[0])
        assert auc_full >= auc_late


# ---------------------------------------------------------------------------
# AUC_meas_entire_pred (100-1000 nm)
# ---------------------------------------------------------------------------

class TestAUCEntire:
    def test_output_is_dataframe(self, uvvis_df):
        seg = np.arange(100, 1000, 10)
        result = AUC_meas_entire_pred(_copy(uvvis_df), seg, "trapz")
        assert isinstance(result, pd.DataFrame)

    def test_column_count(self, uvvis_df):
        """90 segment columns + SRN."""
        seg = np.arange(100, 1000, 10)
        result = AUC_meas_entire_pred(_copy(uvvis_df), seg, "trapz")
        auc_cols = [c for c in result.columns if c != "SRN"]
        assert len(auc_cols) == 90

    def test_peak_segment_is_largest(self, uvvis_df):
        """Segment containing 300 nm peak should have highest AUC."""
        seg = np.arange(100, 1000, 10)
        result = AUC_meas_entire_pred(_copy(uvvis_df), seg, "trapz")
        auc_cols = [c for c in result.columns if c != "SRN"]
        values = result[auc_cols].iloc[0].astype(float)
        peak_col = values.idxmax()
        assert peak_col in ("290-300pred", "300-310pred")

    def test_peak_segments_symmetric(self, uvvis_df):
        """290-300 and 300-310 AUC should be equal for a peak centred at 300 nm."""
        seg = np.arange(100, 1000, 10)
        result = AUC_meas_entire_pred(_copy(uvvis_df), seg, "trapz")
        auc_290_300 = float(result["290-300pred"].iloc[0])
        auc_300_310 = float(result["300-310pred"].iloc[0])
        assert np.isclose(auc_290_300, auc_300_310, rtol=1e-6)

    def test_segment_sum_matches_total_trapz(self, uvvis_df):
        """Sum of all 90 segment AUCs should approximate the full 100-1000 trapezoid."""
        seg = np.arange(100, 1000, 10)
        result = AUC_meas_entire_pred(_copy(uvvis_df), seg, "trapz")
        auc_cols = [c for c in result.columns if c != "SRN"]
        seg_sum = result[auc_cols].iloc[0].astype(float).sum()

        # reference: trapz on raw data
        lam = pd.to_numeric(uvvis_df["lambda (nm)"]).values
        eps = pd.to_numeric(uvvis_df["Epsilon (mL/cm/mol)"]).values
        full_trapz = np.trapz(eps, lam)

        assert np.isclose(seg_sum, full_trapz, rtol=1e-3)


# ---------------------------------------------------------------------------
# run_AUCs_spectra (integration of all three functions)
# ---------------------------------------------------------------------------

class TestRunAUCsSpectra:
    def test_returns_dataframe(self, uvvis_df):
        result = run_AUCs_spectra(_copy(uvvis_df))
        assert isinstance(result, pd.DataFrame)

    def test_one_row_per_molecule(self, uvvis_df):
        result = run_AUCs_spectra(_copy(uvvis_df))
        assert len(result) == 1

    def test_list_columns_present(self, uvvis_df):
        result = run_AUCs_spectra(_copy(uvvis_df))
        for col in ("100-1000", "from250", "to700"):
            assert col in result.columns, f"Missing column: {col}"

    def test_list_column_lengths(self, uvvis_df):
        result = run_AUCs_spectra(_copy(uvvis_df))
        assert len(result["100-1000"].iloc[0]) == 90
        assert len(result["from250"].iloc[0]) == 11
        assert len(result["to700"].iloc[0]) == 11

    def test_list_values_all_finite(self, uvvis_df):
        result = run_AUCs_spectra(_copy(uvvis_df))
        for col in ("100-1000", "from250", "to700"):
            arr = np.array(result[col].iloc[0], dtype=float)
            assert np.all(np.isfinite(arr)), f"Non-finite values in {col}"

    def test_list_values_all_nonnegative(self, uvvis_df):
        """Non-negative spectrum must yield non-negative AUCs."""
        result = run_AUCs_spectra(_copy(uvvis_df))
        for col in ("100-1000", "from250", "to700"):
            arr = np.array(result[col].iloc[0], dtype=float)
            assert np.all(arr >= 0), f"Negative AUC in {col}"

    def test_srn_preserved(self, uvvis_df):
        result = run_AUCs_spectra(_copy(uvvis_df))
        assert result["SRN"].iloc[0] == "test_mol_uvvis"

    def test_250_700_scalar_value(self, uvvis_df):
        """Regression: 250-700 AUC for the synthetic peak fixture."""
        result = run_AUCs_spectra(_copy(uvvis_df))
        assert "250-700pred" in result.columns
        auc = float(result["250-700pred"].iloc[0])
        assert np.isclose(auc, 2491040.07, rtol=1e-4)

    def test_peak_segment_290_300(self, uvvis_df):
        """Regression: 290-300 nm segment AUC for the synthetic peak fixture."""
        result = run_AUCs_spectra(_copy(uvvis_df))
        auc = float(result["290-300pred"].iloc[0])
        assert np.isclose(auc, 479833.28, rtol=1e-4)

    def test_multiple_molecules(self, uvvis_df):
        """Two-molecule input should produce two rows."""
        df2 = uvvis_df.copy()
        df2["SRN"] = "second_mol_uvvis"
        combined = pd.concat([uvvis_df, df2], ignore_index=True)
        result = run_AUCs_spectra(combined)
        assert len(result) == 2
