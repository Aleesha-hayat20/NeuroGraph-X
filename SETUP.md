# Setting up the repository

Follow this once. It takes about ten minutes.

> **Never paste a personal access token into a chat, a document, or a commit.**
> Every step below authenticates on your own machine. If a token is ever exposed,
> revoke it immediately at GitHub, Settings, Developer settings, Personal access tokens.

## 1. Create the empty repository on GitHub

In the browser at github.com:

1. Click **New repository**.
2. Name: `neurograph-x`
3. Description: `A graph neural network platform for reliability-aware brain connectivity analysis in autism research`
4. Visibility: **Private** for now. Make it public before the final submission if the
   department asks for it.
5. **Do not** tick "Add a README", "Add .gitignore" or "Choose a license". This scaffold
   already contains them, and pre-filling causes a merge conflict on the first push.
6. Click **Create repository**.

## 2. Put the scaffold on your machine

Unzip `neurograph-x.zip` somewhere sensible, for example `~/projects/neurograph-x`.

## 3. Initialise and push

Open a terminal in that folder and run these, replacing `YOUR-USERNAME`:

```bash
git init
git branch -M main
git add .
git commit -m "Initial scaffold: package layout, CI, configs, decision memos, week 1 scripts"
git remote add origin https://github.com/YOUR-USERNAME/neurograph-x.git
git push -u origin main
```

Git will ask you to authenticate. On the first push:

- **Windows:** a browser window opens, sign in, done.
- **macOS and Linux:** if it asks for a password, that means a personal access token.
  Create one at GitHub, Settings, Developer settings, Personal access tokens, Fine-grained
  tokens. Give it **Contents: read and write** on this one repository only. Paste it as the
  password. Your terminal will not echo it, which is normal.

Alternatively install the GitHub CLI and run `gh auth login` once, which handles all of this.

## 4. Confirm CI is green

Open the repository on GitHub and click the **Actions** tab. A run named **CI** should
appear within a minute and finish green. That is the first Week 1 gate item met, and it is
the CI/CD deliverable the handbook requires from Development projects.

If it fails, read the log. The most common cause is a pinned version in
`requirements.txt` that does not exist for the runner's Python version.

## 5. Add your teammates

Repository **Settings**, **Collaborators and teams**, **Add people**. Give Laiba and
Alishba **Write** access.

## 6. Protect the main branch

Repository **Settings**, **Branches**, **Add branch ruleset**:

- Target: `main`
- Require a pull request before merging
- Require status checks to pass, and select the **test** check

This is what makes "every pull request is read by one other member" real rather than a
promise, and it produces the review history the midterm asks for.

## 7. Create the project board

On the repository, **Projects** tab, **New project**, choose the **Board** template.

Create four columns: `Backlog`, `This week`, `In review`, `Done`.

Then open the whole four week backlog as issues, not just this week's. Label each one with
its module (`M1` to `M7`) and assign it. A board that only ever holds the current week is
the thing evaluators notice.

Screenshot the board every Sunday and save it to `docs/progress/week-NN/board.png`.

## 8. Set up locally and run the tests

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
pytest
```

Every test should pass (209 as of Week 4). `requirements.txt` includes PyTorch and PyTorch
Geometric, so the model tests run too; without them installed they are skipped. If one fails, read its message before
changing anything: several tests guard the frozen evaluation set on purpose.

## 9. Run the Week 1 scripts

```bash
python scripts/01_fetch_phenotypic.py
python scripts/02_metadata_report.py
python scripts/03_pilot_atlas.py --n 5
```

Then commit what they produced:

```bash
git add docs/reports
git commit -m "Week 1: metadata report and pilot connectivity matrix"
git push
```

## 10. Run the model on a CPU (inference, memo 0009)

No GPU is needed to serve a model. Training runs on Kaggle; prediction runs on any laptop.

**Without the real data** (checks the CPU path on the committed fixture dataset, memo 0014):

```bash
NGX_DATA=fixtures python scripts/predict_one.py --participant 0090001
```

**With the real CC200 model.** You need two things that are not in git:

1. The checkpoint `cc200_00252f2b.pt` (from Laiba, or the Kaggle notebook's evidence
   folder), copied to `checkpoints/cc200_00252f2b.pt`.
2. The connectomes in `data/processed/connectomes/cpac_filt_global/`, built with
   `scripts/01_fetch_phenotypic.py`, `04_fetch_all_atlases.py` and `07_build_connectomes.py`
   (or copied from a machine that already has them).

Then, from the repository root:

```bash
python scripts/predict_one.py --participant 0050011 --atlas cc200 --expect control:0.7052
```

The last line must read `matches reference control:0.7052 (tolerance 0.001): True`. The
reference is the Kaggle GPU result of run `00252f2b`. The script only predicts: it reads no
labels and writes nothing, so it is safe on frozen-set participants and is not a frozen-set
measurement. Never run `scripts/train_gnn.py --stage final` to check a setup: it measures the
frozen set, which happens once per atlas (memo 0011).

## Branch naming

```
feature/m1-ingestion-qc
feature/m2-connectome-engine
feature/m3-gnn-baseline
docs/decision-0002-pipeline
```

One branch per issue. Open a pull request, get one review, merge, delete the branch.
