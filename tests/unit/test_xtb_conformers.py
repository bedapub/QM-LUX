# © 2026 Roche
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the conformer driver :func:`qm_lux.xtb.sdf_run`.

`sdf_run` had no coverage in either repo until this module: the internal copy
that used to carry characterisation tests went with the DEDUP-4 deletions.

Conformer embedding is the expensive part of the chain and is not what these
tests are about, so most of them stub `get_conf_MMFF_opt` / `get_energy_conf` /
`write_SDF` and assert on how `sdf_run` drives them — which compounds it
processes, which folder index each one is written to, and what it returns.
`TestOverwriteHappyPath` runs the real chain once on benzene so the stubs are
anchored to something.
"""
import os

import pandas as pd
import pytest

from qm_lux import xtb
from qm_lux.xtb import sdf_run


def _df(srns):
    return pd.DataFrame({
        "SRN": srns,
        "SMILES_CLEAN": ["c1ccccc1"] * len(srns),
    })


def _run(tmp_path, srns, check="OVERWRITE", cluster=0):
    return sdf_run(str(tmp_path), srns, "SMILES_CLEAN", _df(srns),
                   0.1, 2, cluster, check)


@pytest.fixture
def stub_chain(monkeypatch):
    """Replace the RDKit chain with a recorder.

    Returns the list of (folder_index, srn) pairs write_SDF was called with.
    Compounds whose SRN is in `fail_conf` take the error_conf branch; those in
    `fail_ff` come back from get_energy_conf with "ERROR".
    """
    written = []
    state = {"fail_conf": set(), "fail_ff": set()}

    def fake_conf(smiles, rmsthresh, nconfs):
        # (mol, opt_mols, mp, cids, bad_ID) — only bad_ID is read by sdf_run.
        return ("mol", None, None, [0], "OK_conf")

    def fake_energy(mol, mp, cids):
        # (mol, sorted_res, error)
        return ("mol", [(0, 0.0)], "OK")

    def fake_write(mol, sorted_res, output_pat, mol_n, mol_name, error, error_conf):
        written.append((mol_n, mol_name))
        # Write for real, into the same place write_SDF would. A recorder that
        # only appends cannot tell whether the index it was handed clobbered a
        # folder that was supposed to be preserved.
        target = os.path.join(output_pat, str(mol_n))
        os.makedirs(target, exist_ok=True)
        with open(os.path.join(target, str(mol_n) + ".sdf"), "w") as fh:
            fh.write(mol_name)
        return "OK"

    monkeypatch.setattr(xtb, "get_conf_MMFF_opt", fake_conf)
    monkeypatch.setattr(xtb, "get_energy_conf", fake_energy)
    monkeypatch.setattr(xtb, "write_SDF", fake_write)
    return written, state


# ---------------------------------------------------------------------------
# check is validated
# ---------------------------------------------------------------------------

class TestCheckIsValidated:
    """An unrecognised `check` appended nothing to the `skip` list, so the
    list desynchronised from `list_comp` and the mistake surfaced as an
    IndexError deep in the second loop instead of at the call site."""

    @pytest.mark.parametrize("check", [
        "overwrite", "OVERWRITE ", "NO_OVERWRITE", "no overwrite", "", None,
    ])
    def test_unrecognised_check_raises(self, tmp_path, check):
        with pytest.raises(ValueError) as exc:
            _run(tmp_path, ["A"], check=check)
        assert "check must be" in str(exc.value)

    def test_the_message_names_both_values_and_echoes_the_input(self, tmp_path):
        with pytest.raises(ValueError) as exc:
            _run(tmp_path, ["A"], check="overwrite")
        message = str(exc.value)
        assert "OVERWRITE" in message and "NO OVERWRITE" in message
        assert "'overwrite'" in message

    def test_it_raises_before_creating_anything(self, tmp_path):
        """The guard is up front, so a bad call leaves no half-built tree."""
        with pytest.raises(ValueError):
            _run(tmp_path, ["A", "B"], check="overwrite")
        assert not os.path.exists(os.path.join(str(tmp_path), "0"))


# ---------------------------------------------------------------------------
# Nothing to do is not an error
# ---------------------------------------------------------------------------

class TestEmptyBatchIsANoOp:
    """`al_mol` was only bound inside the success branch, so a batch in which
    nothing was processed fell off the end into `print(al_mol[2])` and raised
    UnboundLocalError. A fully-cached batch is a legitimate input."""

    def test_empty_list_comp_returns_ok(self, tmp_path):
        assert _run(tmp_path, []) == "OK"

    def test_fully_cached_batch_returns_ok(self, tmp_path, stub_chain):
        written, _ = stub_chain
        for i in range(3):
            os.makedirs(os.path.join(str(tmp_path), "0", str(i)))
        assert _run(tmp_path, ["A", "B", "C"], check="NO OVERWRITE") == "OK"
        assert written == [], "nothing should have been processed"

    def test_every_compound_failing_embedding_returns_error_not_a_crash(
            self, tmp_path, monkeypatch):
        monkeypatch.setattr(xtb, "get_conf_MMFF_opt",
                            lambda *a, **k: ("mol", None, None, [], "error_conf"))
        assert _run(tmp_path, ["A", "B"]) == "ERROR"


# ---------------------------------------------------------------------------
# The return value aggregates the batch
# ---------------------------------------------------------------------------

class TestReturnValueAggregates:
    """The return was the LAST processed compound's status, so a failure on any
    earlier compound was reported as "OK"."""

    def test_clean_batch_is_ok(self, tmp_path, stub_chain):
        assert _run(tmp_path, ["A", "B", "C"]) == "OK"

    def test_an_early_embedding_failure_is_not_masked_by_a_later_success(
            self, tmp_path, monkeypatch, stub_chain):
        """A fails, B succeeds. The old code returned B's status."""
        def fake_conf(smiles, rmsthresh, nconfs):
            fake_conf.n += 1
            if fake_conf.n == 1:
                return ("mol", None, None, [], "error_conf")
            return ("mol", None, None, [0], "OK_conf")
        fake_conf.n = 0
        monkeypatch.setattr(xtb, "get_conf_MMFF_opt", fake_conf)
        assert _run(tmp_path, ["A", "B"]) == "ERROR"

    def test_an_early_force_field_failure_is_not_masked_either(
            self, tmp_path, monkeypatch, stub_chain):
        def fake_energy(mol, mp, cids):
            fake_energy.n += 1
            return ("mol", [(0, 0.0)], "ERROR" if fake_energy.n == 1 else "OK")
        fake_energy.n = 0
        monkeypatch.setattr(xtb, "get_energy_conf", fake_energy)
        assert _run(tmp_path, ["A", "B"]) == "ERROR"


# ---------------------------------------------------------------------------
# NO OVERWRITE must not shift the folder index
# ---------------------------------------------------------------------------

class TestNoOverwriteDoesNotCorruptPreservedFolders:
    """The output index was a counter that only advanced on processed
    compounds, while the folders were created by position. One skipped
    compound wrote every later one an index too low — on top of the file
    "NO OVERWRITE" was asked to preserve — and left the last folder empty."""

    def test_a_skip_does_not_shift_later_compounds_down(self, tmp_path, stub_chain):
        written, _ = stub_chain
        os.makedirs(os.path.join(str(tmp_path), "0", "0"))
        _run(tmp_path, ["A", "B", "C"], check="NO OVERWRITE")
        # A is preserved; B and C keep their own positions.
        assert written == [(1, "B"), (2, "C")]

    def test_the_preserved_file_survives(self, tmp_path, stub_chain):
        preserved = os.path.join(str(tmp_path), "0", "0")
        os.makedirs(preserved)
        sentinel = os.path.join(preserved, "0.sdf")
        with open(sentinel, "w") as fh:
            fh.write("PRESERVE ME")
        _run(tmp_path, ["A", "B"], check="NO OVERWRITE")
        with open(sentinel) as fh:
            assert fh.read() == "PRESERVE ME"

    def test_two_skips_in_the_middle(self, tmp_path, stub_chain):
        written, _ = stub_chain
        for i in (1, 2):
            os.makedirs(os.path.join(str(tmp_path), "0", str(i)))
        _run(tmp_path, ["A", "B", "C", "D"], check="NO OVERWRITE")
        assert written == [(0, "A"), (3, "D")]

    def test_overwrite_wipes_and_reprocesses_the_same_index(self, tmp_path, stub_chain):
        written, _ = stub_chain
        stale = os.path.join(str(tmp_path), "0", "0")
        os.makedirs(stale)
        with open(os.path.join(stale, "0.sdf"), "w") as fh:
            fh.write("STALE")
        _run(tmp_path, ["A", "B"], check="OVERWRITE")
        assert written == [(0, "A"), (1, "B")]
        # Folder 0 was wiped and rebuilt from compound A, not left stale.
        with open(os.path.join(stale, "0.sdf")) as fh:
            assert fh.read() == "A"


# ---------------------------------------------------------------------------
# One real run, so the stubs above are anchored
# ---------------------------------------------------------------------------

class TestOverwriteHappyPath:
    def test_real_chain_writes_one_folder_per_compound(self, tmp_path):
        srns = ["mol_a", "mol_b"]
        assert _run(tmp_path, srns) == "OK"
        for i, srn in enumerate(srns):
            folder = os.path.join(str(tmp_path), "0", str(i))
            assert os.path.isfile(os.path.join(folder, srn + ".sdf"))
            assert os.path.isfile(os.path.join(folder, str(i) + ".sdf"))

    def test_cluster_number_selects_the_subfolder(self, tmp_path):
        _run(tmp_path, ["mol_a"], cluster=7)
        assert os.path.isdir(os.path.join(str(tmp_path), "7", "0"))
