QM-LUX -- PhotoTox Prediction
##############################

QM-LUX predicts the phototoxicity of small molecules using UV-Vis spectra
computed with quantum mechanics. The workflow combines 3-D conformer generation
(RDKit MMFF94s), conformational sampling with CREST/XTB, excited-state TD-DFT
calculations with Gaussian 16, and an ML classifier trained on UV-Vis AUC
descriptors, Morgan fingerprints, and RDKit physicochemical properties.


Workflow steps
==============

1. **Data preparation** -- parses the input SMILES/SDF file and generates
   3-D conformers (RDKit MMFF94s force field).
2. **Conformer search** (CREST/XTB) -- explores low-energy conformations in
   implicit water solvent (ALPB model) using the GFN2-xTB Hamiltonian.
3. **Semi-empirical optimisation** (XTB) -- refines the lowest-energy
   conformer at the GFN2-xTB level.
4. **UV-Vis calculation** (Gaussian 16) -- computes TD-DFT excited states to
   obtain the UV-Vis absorption spectrum.
5. **Prediction** -- applies a pre-trained ML classifier
   (method: ``{{ snakemake.config["model_method"] }}``,
   descriptor: ``{{ snakemake.config["model_descriptor"] }}``)
   to predict phototoxicity from UV-Vis AUC descriptors, Morgan fingerprints,
   and RDKit physicochemical properties.
6. **Results** -- per-molecule phototoxicity labels, ML probability scores,
   and UV-Vis spectra (``results_ML_with_mol_UV.html``, ``summary.html``).


Rule graph
==========

The workflow runs in two phases because Gaussian 16 executes outside the
container and requires a separate job submission. Phase 1 covers data
preparation through XTB optimisation; Phase 2 picks up from Gaussian 16
through ML prediction. The interactive rule graph is available in the
**Workflow** section of this report.

References
==========

- **XTB / GFN2-xTB** -- Bannwarth, C.; Ehlert, S.; Grimme, S. *J. Chem. Theory Comput.* **2019**, *15*, 1652-1671. https://doi.org/10.1021/acs.jctc.8b01176
- **CREST** -- Pracht, P.; Bohle, F.; Grimme, S. *Phys. Chem. Chem. Phys.* **2020**, *22*, 7169-7192. https://doi.org/10.1039/C9CP06869D; Pracht, P. *et al.* *J. Chem. Phys.* **2024**, *160*, 114110. https://doi.org/10.1063/5.0197592
- **Gaussian 16** -- Frisch, M. J. *et al.*, Gaussian 16, Revision C.01, Gaussian Inc., Wallingford CT, 2016.
- **RDKit** -- Landrum, G. *et al.* RDKit: Open-Source Cheminformatics Software. https://www.rdkit.org
- **scikit-learn** -- Pedregosa, F. *et al.* *J. Mach. Learn. Res.* **2011**, *12*, 2825-2830. https://jmlr.org/papers/v12/pedregosa11a.html
- **Snakemake** -- Moelder, F. *et al.* *F1000Research* **2021**, *10*, 33. https://doi.org/10.12688/f1000research.29032.2
- **QM-LUX** -- Milani, N.; Anelli, A.; Schmucki, R. *et al.* QM-LUX: Quantum Molecular Learning for UV-Vis-based phototoxicity prediction. *Manuscript in preparation* (2026).
