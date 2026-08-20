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
   obtain the UV-Vis absorption spectrum: B3LYP/6-311+G(d,p), 30 singlet
   states, water PCM.
5. **Prediction** -- applies a pre-trained ML classifier
   (method: ``{{ snakemake.config["model_method"] }}``,
   descriptor: ``{{ snakemake.config["model_descriptor"] }}``)
   to predict phototoxicity from UV-Vis AUC descriptors, Morgan fingerprints,
   and RDKit physicochemical properties.
6. **Results** -- per-molecule phototoxicity labels, ML probability scores,
   and UV-Vis spectra (``results_ML_with_mol_UV.html``, ``summary.html``).


Rule graph
==========

The whole workflow -- data preparation through ML prediction, Gaussian 16
included -- runs as a single Snakemake invocation. Gaussian 16 is scheduled
as an ordinary rule; it executes outside the container, against your own
licensed installation, but that needs no separate submission on your part.
The interactive rule graph is available in the **Workflow** section of this
report.

References
==========

- **XTB (program)** -- Bannwarth, C.; Caldeweyher, E.; Ehlert, S.; Hansen, A.; Pracht, P.; Seibert, J.; Spicher, S.; Grimme, S. *WIREs Comput. Mol. Sci.* **2021**, *11*, e1493. https://doi.org/10.1002/wcms.1493
- **GFN2-xTB (method)** -- Bannwarth, C.; Ehlert, S.; Grimme, S. *J. Chem. Theory Comput.* **2019**, *15*, 1652-1671. https://doi.org/10.1021/acs.jctc.8b01176
- **ALPB (implicit solvation)** -- Ehlert, S.; Stahn, M.; Spicher, S.; Grimme, S. *J. Chem. Theory Comput.* **2021**, *17*, 4250-4261. https://doi.org/10.1021/acs.jctc.1c00471
- **CREST** -- Pracht, P.; Bohle, F.; Grimme, S. *Phys. Chem. Chem. Phys.* **2020**, *22*, 7169-7192. https://doi.org/10.1039/C9CP06869D ; Pracht, P. *et al.* *J. Chem. Phys.* **2024**, *160*, 114110. https://doi.org/10.1063/5.0197592
- **Gaussian 16** -- Frisch, M. J. *et al.*, Gaussian 16, Gaussian Inc., Wallingford CT, 2016. Cite the revision you ran.
- **RDKit** -- Landrum, G. *et al.* RDKit: Open-Source Cheminformatics Software. https://www.rdkit.org
- **ETKDG (conformer embedding)** -- Riniker, S.; Landrum, G. A. *J. Chem. Inf. Model.* **2015**, *55*, 2562-2574. https://doi.org/10.1021/acs.jcim.5b00654
- **MMFF94s** -- Halgren, T. A. *J. Comput. Chem.* **1999**, *20*, 720-729. https://doi.org/10.1002/(SICI)1096-987X(199905)20:7%3C720::AID-JCC7%3E3.0.CO;2-X
- **ASE** -- Hjorth Larsen, A. *et al.* *J. Phys.: Condens. Matter* **2017**, *29*, 273002. https://doi.org/10.1088/1361-648X/aa680e
- **scikit-learn** -- Pedregosa, F. *et al.* *J. Mach. Learn. Res.* **2011**, *12*, 2825-2830. https://jmlr.org/papers/v12/pedregosa11a.html
- **Snakemake** -- Moelder, F. *et al.* *F1000Research* **2021**, *10*, 33. https://doi.org/10.12688/f1000research.29032.2
- **QM-LUX** -- Milani, N.; Anelli, A.; Schmucki, R. *et al.* QM-LUX: Quantum Molecular Learning for UV-Vis-based phototoxicity prediction. *Manuscript in preparation* (2026).
