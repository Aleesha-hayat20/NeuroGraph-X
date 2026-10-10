# Connectome Engine: Independent Verification

**Generated:** 2026-10-10  
**Sample:** 20 participants per atlas, seed 20261007, 200 region pairs per participant for scipy  
**Result:** ALL PASSED

The engine (numpy loadtxt, corrcoef, arctanh) is compared with routes that share
none of its code: pandas to read the file, the Pearson formula written out by hand,
scipy.stats.pearsonr on sampled region pairs, nilearn ConnectivityMeasure with the
empirical covariance, and the Fisher formula 0.5 ln((1 + r) / (1 - r)) written out.

Tolerance: absolute 1e-06 for r; absolute 1e-05 plus relative 1e-05 for z. Values are stored as float32, about seven significant digits.

## Per atlas

| Atlas          |   Participants checked |   With flat regions |   Max abs diff r, manual |   Max abs diff r, scipy |   Max abs diff r, nilearn |   Max abs diff z | NaN pattern matches   | Passed   |
|:---------------|-----------------------:|--------------------:|-------------------------:|------------------------:|--------------------------:|-----------------:|:----------------------|:---------|
| AAL            |                     20 |                   1 |                    3e-08 |                 3e-08   |                     3e-08 |          5.9e-08 | 20/20                 | 20/20    |
| CC200          |                     20 |                   1 |                    3e-08 |                 3e-08   |                     3e-08 |          6e-08   | 20/20                 | 20/20    |
| Harvard-Oxford |                     20 |                   6 |                    3e-08 |                 3e-08   |                     3e-08 |          5.9e-08 | 20/20                 | 20/20    |
| Dosenbach 160  |                     20 |                   1 |                    3e-08 |                 2.9e-08 |                     3e-08 |          5.9e-08 | 20/20                 | 20/20    |

## Every participant checked

| atlas          | FILE_ID          |   flat_regions |   r_max_abs_diff_manual |   z_max_abs_diff | passed   |
|:---------------|:-----------------|---------------:|------------------------:|-----------------:|:---------|
| AAL            | NYU_0051094      |              0 |                 3.0e-08 |          5.8e-08 | True     |
| AAL            | NYU_0051102      |              0 |                 3.0e-08 |          5.7e-08 | True     |
| AAL            | Yale_0050602     |              0 |                 3.0e-08 |          5.9e-08 | True     |
| AAL            | NYU_0051047      |              0 |                 3.0e-08 |          5.9e-08 | True     |
| AAL            | Yale_0050576     |              0 |                 3.0e-08 |          5.9e-08 | True     |
| AAL            | OHSU_0050148     |              0 |                 3.0e-08 |          5.9e-08 | True     |
| AAL            | UM_1_0050341     |              0 |                 3.0e-08 |          5.9e-08 | True     |
| AAL            | Trinity_0050268  |              0 |                 3.0e-08 |          5.9e-08 | True     |
| AAL            | UCLA_2_0051297   |              0 |                 3.0e-08 |          5.7e-08 | True     |
| AAL            | Leuven_2_0050723 |              0 |                 3.0e-08 |          5.6e-08 | True     |
| AAL            | Yale_0050627     |              0 |                 3.0e-08 |          5.8e-08 | True     |
| AAL            | KKI_0050778      |              0 |                 3.0e-08 |          5.9e-08 | True     |
| AAL            | NYU_0050956      |              0 |                 3.0e-08 |          5.1e-08 | True     |
| AAL            | UM_1_0050364     |              0 |                 3.0e-08 |          5.6e-08 | True     |
| AAL            | USM_0050434      |              0 |                 2.9e-08 |          5.7e-08 | True     |
| AAL            | UCLA_2_0051309   |              0 |                 3.0e-08 |          5.0e-08 | True     |
| AAL            | UM_1_0050282     |              0 |                 3.0e-08 |          4.5e-08 | True     |
| AAL            | UCLA_1_0051273   |              0 |                 3.0e-08 |          5.9e-08 | True     |
| AAL            | Caltech_0051477  |              0 |                 3.0e-08 |          5.6e-08 | True     |
| AAL            | KKI_0050790      |              1 |                 3.0e-08 |          5.6e-08 | True     |
| CC200          | USM_0050493      |              0 |                 3.0e-08 |          3.0e-08 | True     |
| CC200          | KKI_0050812      |              0 |                 3.0e-08 |          5.9e-08 | True     |
| CC200          | Yale_0050551     |              0 |                 3.0e-08 |          5.9e-08 | True     |
| CC200          | MaxMun_c_0051345 |              0 |                 3.0e-08 |          5.9e-08 | True     |
| CC200          | UCLA_1_0051264   |              0 |                 3.0e-08 |          6.0e-08 | True     |
| CC200          | UM_1_0050381     |              0 |                 3.0e-08 |          5.5e-08 | True     |
| CC200          | KKI_0050823      |              0 |                 3.0e-08 |          5.7e-08 | True     |
| CC200          | NYU_0050960      |              0 |                 3.0e-08 |          5.9e-08 | True     |
| CC200          | NYU_0051015      |              0 |                 3.0e-08 |          5.0e-08 | True     |
| CC200          | Yale_0050601     |              0 |                 3.0e-08 |          5.6e-08 | True     |
| CC200          | NYU_0051146      |              0 |                 3.0e-08 |          5.7e-08 | True     |
| CC200          | Olin_0050121     |              0 |                 3.0e-08 |          5.8e-08 | True     |
| CC200          | NYU_0050991      |              0 |                 3.0e-08 |          5.6e-08 | True     |
| CC200          | NYU_0051089      |              0 |                 3.0e-08 |          5.8e-08 | True     |
| CC200          | USM_0050528      |              0 |                 3.0e-08 |          5.6e-08 | True     |
| CC200          | NYU_0051131      |              0 |                 3.0e-08 |          5.9e-08 | True     |
| CC200          | UCLA_1_0051219   |              0 |                 3.0e-08 |          5.9e-08 | True     |
| CC200          | Pitt_0050060     |              0 |                 3.0e-08 |          5.6e-08 | True     |
| CC200          | Caltech_0051482  |              0 |                 3.0e-08 |          5.9e-08 | True     |
| CC200          | CMU_b_0050644    |              4 |                 3.0e-08 |          5.7e-08 | True     |
| Harvard-Oxford | NYU_0051094      |              0 |                 3.0e-08 |          5.9e-08 | True     |
| Harvard-Oxford | NYU_0051114      |              1 |                 3.0e-08 |          5.9e-08 | True     |
| Harvard-Oxford | UM_2_0050428     |              0 |                 3.0e-08 |          5.2e-08 | True     |
| Harvard-Oxford | UM_1_0050365     |              0 |                 3.0e-08 |          5.9e-08 | True     |
| Harvard-Oxford | UCLA_1_0051271   |              2 |                 3.0e-08 |          5.7e-08 | True     |
| Harvard-Oxford | USM_0050463      |              1 |                 2.9e-08 |          5.8e-08 | True     |
| Harvard-Oxford | Pitt_0050033     |              0 |                 3.0e-08 |          5.9e-08 | True     |
| Harvard-Oxford | USM_0050470      |              0 |                 3.0e-08 |          5.7e-08 | True     |
| Harvard-Oxford | MaxMun_c_0051344 |              0 |                 3.0e-08 |          5.0e-08 | True     |
| Harvard-Oxford | UM_2_0050411     |              0 |                 3.0e-08 |          5.2e-08 | True     |
| Harvard-Oxford | Leuven_2_0050745 |              0 |                 3.0e-08 |          5.0e-08 | True     |
| Harvard-Oxford | UCLA_1_0051239   |              0 |                 3.0e-08 |          5.3e-08 | True     |
| Harvard-Oxford | UM_2_0050424     |              1 |                 3.0e-08 |          5.9e-08 | True     |
| Harvard-Oxford | MaxMun_a_0051607 |              1 |                 3.0e-08 |          5.9e-08 | True     |
| Harvard-Oxford | CMU_a_0050654    |              0 |                 3.0e-08 |          5.9e-08 | True     |
| Harvard-Oxford | USM_0050466      |              1 |                 2.9e-08 |          4.5e-08 | True     |
| Harvard-Oxford | NYU_0051012      |              0 |                 3.0e-08 |          5.8e-08 | True     |
| Harvard-Oxford | Yale_0050606     |              0 |                 3.0e-08 |          5.9e-08 | True     |
| Harvard-Oxford | SBL_0051579      |              0 |                 3.0e-08 |          5.7e-08 | True     |
| Harvard-Oxford | UCLA_1_0051210   |              0 |                 3.0e-08 |          5.7e-08 | True     |
| Dosenbach 160  | Trinity_0051142  |              0 |                 3.0e-08 |          5.6e-08 | True     |
| Dosenbach 160  | Trinity_0050263  |              0 |                 3.0e-08 |          4.0e-08 | True     |
| Dosenbach 160  | MaxMun_a_0051365 |              0 |                 3.0e-08 |          3.0e-08 | True     |
| Dosenbach 160  | NYU_0050969      |              0 |                 3.0e-08 |          5.5e-08 | True     |
| Dosenbach 160  | USM_0050504      |              0 |                 2.9e-08 |          3.0e-08 | True     |
| Dosenbach 160  | NYU_0051128      |              0 |                 3.0e-08 |          3.0e-08 | True     |
| Dosenbach 160  | Caltech_0051484  |              0 |                 3.0e-08 |          4.1e-08 | True     |
| Dosenbach 160  | Yale_0050614     |              0 |                 3.0e-08 |          5.9e-08 | True     |
| Dosenbach 160  | UM_2_0050411     |              0 |                 3.0e-08 |          2.9e-08 | True     |
| Dosenbach 160  | UM_1_0050320     |              0 |                 2.9e-08 |          5.9e-08 | True     |
| Dosenbach 160  | Yale_0050620     |              0 |                 3.0e-08 |          5.7e-08 | True     |
| Dosenbach 160  | UCLA_2_0051304   |              0 |                 3.0e-08 |          4.8e-08 | True     |
| Dosenbach 160  | SBL_0051567      |              4 |                 3.0e-08 |          3.0e-08 | True     |
| Dosenbach 160  | NYU_0050964      |              0 |                 3.0e-08 |          4.4e-08 | True     |
| Dosenbach 160  | Pitt_0050032     |              0 |                 3.0e-08 |          2.9e-08 | True     |
| Dosenbach 160  | Stanford_0051182 |              0 |                 3.0e-08 |          5.8e-08 | True     |
| Dosenbach 160  | Stanford_0051189 |              0 |                 3.0e-08 |          5.8e-08 | True     |
| Dosenbach 160  | UCLA_2_0051294   |              0 |                 3.0e-08 |          5.9e-08 | True     |
| Dosenbach 160  | UCLA_1_0051256   |              0 |                 3.0e-08 |          5.8e-08 | True     |
| Dosenbach 160  | Leuven_2_0050748 |              0 |                 3.0e-08 |          5.8e-08 | True     |
