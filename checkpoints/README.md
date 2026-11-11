# Model checkpoints

The final model of each atlas is committed here (memo 0009, option A, accepted 12 November
2026), so the API and the dashboard serve exactly the measured models on any machine
without Kaggle. The CC200 baseline `cc200_00252f2b.pt` is committed too: its frozen-set
result is compared with the final CC200 model in the report, so every model we quote can be
loaded and checked from a clean clone. It is not served.

- Which file serves which atlas: `runs/model_registry.json`.
- Each file's SHA-256 is in its run's record in `runs/run_log.jsonl` (`checkpoint_sha256`);
  the model loader refuses a file that does not match.
- Model cards: `docs/model_cards/`.

## Licence

The models are trained on ABIDE I data (Preprocessed Connectomes Project), released under
**Creative Commons Attribution-NonCommercial-ShareAlike 3.0 (CC BY-NC-SA 3.0)**. The
checkpoints are derived from that data and are shared under the same licence: research
and teaching use, non-commercial, with attribution to ABIDE and the Preprocessed
Connectomes Project. They are not a diagnostic or medical device.

Please cite the data as:

- A. Di Martino et al., "The autism brain imaging data exchange: towards a large-scale evaluation of the intrinsic brain architecture in autism," Molecular Psychiatry, vol. 19, no. 6, pp. 659-667, 2014, doi:10.1038/mp.2013.78.
- C. Craddock et al., "The Neuro Bureau Preprocessing Initiative: open sharing of preprocessed neuroimaging data and derivatives," Frontiers in Neuroinformatics, Conference Abstract: Neuroinformatics 2013, doi:10.3389/conf.fninf.2013.09.00041.
