UV-Vis AUC descriptors computed from TD-DFT excited-state calculations (Gaussian 16).

Each row corresponds to one molecule. Columns are UV-Vis area-under-the-curve (AUC)
descriptors in wavelength windows used as ML features, together with Morgan fingerprint
bits and RDKit physicochemical properties.

Computational methods
=====================

3-D conformers are generated with RDKit (ETKDGv2 embedding, MMFF94s optimisation).
Conformational sampling uses CREST with the GFN2-xTB Hamiltonian in implicit water
(ALPB model). The lowest-energy conformer is refined at the GFN2-xTB level, then
submitted to Gaussian 16 for TD-DFT excited-state calculations — B3LYP/6-311+G(d,p),
30 singlet states, water PCM (``scrf=(solvent=water)``). UV-Vis AUC descriptors are
extracted from the resulting spectrum and combined with Morgan fingerprints and
RDKit physicochemical properties to produce the feature vector for the ML classifier.

References
==========

- **XTB (program)** — Bannwarth, C.; Caldeweyher, E.; Ehlert, S.; Hansen, A.; Pracht, P.; Seibert, J.; Spicher, S.; Grimme, S. *WIREs Comput. Mol. Sci.* **2021**, *11*, e1493. https://doi.org/10.1002/wcms.1493
- **GFN2-xTB (method)** — Bannwarth, C.; Ehlert, S.; Grimme, S. *J. Chem. Theory Comput.* **2019**, *15*, 1652-1671. https://doi.org/10.1021/acs.jctc.8b01176
- **ALPB (implicit solvation)** — Ehlert, S.; Stahn, M.; Spicher, S.; Grimme, S. *J. Chem. Theory Comput.* **2021**, *17*, 4250-4261. https://doi.org/10.1021/acs.jctc.1c00471
- **CREST** — Pracht, P.; Bohle, F.; Grimme, S. *Phys. Chem. Chem. Phys.* **2020**, *22*, 7169-7192. https://doi.org/10.1039/C9CP06869D ; Pracht, P. *et al.* *J. Chem. Phys.* **2024**, *160*, 114110. https://doi.org/10.1063/5.0197592
- **Gaussian 16** — Frisch, M. J. *et al.*, Gaussian 16, Gaussian Inc., Wallingford CT, 2016. Cite the revision you ran.
- **RDKit** — Landrum, G. *et al.* RDKit: Open-Source Cheminformatics Software. https://www.rdkit.org
- **ETKDG (conformer embedding)** — Riniker, S.; Landrum, G. A. *J. Chem. Inf. Model.* **2015**, *55*, 2562-2574. https://doi.org/10.1021/acs.jcim.5b00654
- **MMFF94s** — Halgren, T. A. *J. Comput. Chem.* **1999**, *20*, 720-729. https://doi.org/10.1002/(SICI)1096-987X(199905)20:7%3C720::AID-JCC7%3E3.0.CO;2-X
- **ASE** — Hjorth Larsen, A. *et al.* *J. Phys.: Condens. Matter* **2017**, *29*, 273002. https://doi.org/10.1088/1361-648X/aa680e
- **scikit-learn** — Pedregosa, F. *et al.* *J. Mach. Learn. Res.* **2011**, *12*, 2825-2830. https://jmlr.org/papers/v12/pedregosa11a.html
- **Snakemake** — Moelder, F. *et al.* *F1000Research* **2021**, *10*, 33. https://doi.org/10.12688/f1000research.29032.2
- **QM-LUX** — Milani, N.; Anelli, A.; Schmucki, R. *et al.* QM-LUX: Quantum Molecular Learning for UV-Vis-based phototoxicity prediction. *Manuscript in preparation* (2026).
