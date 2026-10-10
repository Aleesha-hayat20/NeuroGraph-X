# Week 2: publishing to GitHub

Repository `Aleesha-hayat20/NeuroGraph-X`, branch `feature/m2-week2-connectome`.

## What is already done locally

The branch was created from `main` (commit `091dcb7`, the Week 1 merge) and all Week 2
work is committed on it in logical pieces. Run `git log --oneline main..` to see them.

## Publish in one command (MacBook terminal)

```bash
bash ~/Downloads/neurograph-x/docs/progress/week-02/publish_week2.sh
```

The script, in order:

1. Checks it is on the Week 2 branch with nothing uncommitted and that `gh` is logged in.
2. Fetches GitHub. If teammates merged anything into `main` since 2 October, it merges
   that into the branch first. On a conflict it stops and pushes nothing.
3. Installs the pinned dependencies into `.venv` (one new pin this week: `tabulate`).
4. Runs `ruff` and `pytest`, the same commands CI runs. Any failure stops it.
5. Pushes the branch.
6. Opens the pull request with `pr_body.md` as the description (or reuses an open one).
7. Waits for GitHub Actions on the PR. If CI fails, it stops without merging.
8. Merges with a merge commit (like PR #25), deletes the branch, switches to `main`,
   pulls, and shows the CI run on `main`.

Output is also saved to `.git/publish_week2.log`.

## If it stops

| Message | What it means | What to do |
|---|---|---|
| uncommitted changes | A tracked file was edited after the commits | Show Claude `git status` |
| merge conflict with teammates' work | Someone changed the same lines on `main` | Nothing was pushed. Ask Claude to resolve |
| tests failed / lint failed | Something differs on the Mac | Nothing was pushed. Share the log |
| CI failed on PR | GitHub's run failed | Nothing was merged. `gh run view --repo Aleesha-hayat20/NeuroGraph-X --log-failed` |
| gh is not logged in | Session expired | `gh auth login`, then rerun the script |

Rerunning the script after fixing a problem is safe: it reuses the open PR.

## Manual equivalent

```bash
cd ~/Downloads/neurograph-x
git switch feature/m2-week2-connectome
git fetch origin && git merge origin/main
source .venv/bin/activate && pip install -r requirements-dev.txt && pip install -e .
ruff check src scripts tests && pytest
git push -u origin feature/m2-week2-connectome
gh pr create --base main --title "Week 2: connectome engine, frozen evaluation set, leakage test" \
  --body-file docs/progress/week-02/pr_body.md
gh pr checks --watch
gh pr merge --merge --delete-branch
git switch main && git pull --ff-only origin main
```

## After merging

Paste the link of the green CI run on `main` into `log.md` under "CI run for the Week 2
pull request". Tell Laiba to run `git switch main && git pull --ff-only origin main`.
