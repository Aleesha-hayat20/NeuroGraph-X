# Model checkpoints

The final model of each atlas is committed here (memo 0009, option A, agreed at the Week 6
Monday stand-up), so the API and the dashboard serve exactly the measured models on any
machine without Kaggle.

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
