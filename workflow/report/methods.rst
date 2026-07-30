UV-Vis AUC descriptors computed from TD-DFT excited-state calculations (Gaussian 16).

Each row corresponds to one molecule. Columns are UV-Vis area-under-the-curve (AUC)
descriptors in wavelength windows used as ML features, together with Morgan fingerprint
bits and RDKit physicochemical properties.

Computational methods
=====================

3-D conformers are generated with RDKit (MMFF94s). Conformational sampling uses
CREST with the GFN2-xTB Hamiltonian in implicit water (ALPB model). The lowest-energy
conformer is refined at the GFN2-xTB level, then submitted to Gaussian 16 for
TD-DFT excited-state calculations (B3LYP/6-31G*). UV-Vis AUC descriptors are
extracted from the resulting spectrum and combined with Morgan fingerprints and
RDKit physicochemical properties to produce the feature vector for the ML classifier.

References
==========

- **XTB / GFN2-xTB** — Bannwarth, C.; Ehlert, S.; Grimme, S. *J. Chem. Theory Comput.* 2019, 15, 1652.
- **CREST** — Pracht, P. et al. *J. Chem. Phys.* 2024, 160, 114110.
- **Gaussian 16** — Frisch, M. J. et al., Gaussian Inc., Wallingford CT, 2016.
- **RDKit** — Landrum, G. et al. https://www.rdkit.org
- **scikit-learn** — Pedregosa, F. et al. *JMLR* 2011, 12, 2825.
