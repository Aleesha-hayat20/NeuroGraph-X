#!/usr/bin/env bash
# Publish the Week 2 branch: sync with GitHub, test, push, open the PR, wait for CI, merge.
#
# Run from anywhere on the Mac:
#     bash ~/Downloads/neurograph-x/docs/progress/week-02/publish_week2.sh
#
# It stops at the first problem and says what to do. Nothing is merged unless the
# local tests pass AND GitHub Actions is green. A copy of the output is written to
# .git/publish_week2.log (inside .git, so it is never committed).

set -euo pipefail

REPO="Aleesha-hayat20/NeuroGraph-X"
BRANCH="feature/m2-week2-connectome"
TITLE="Week 2: connectome engine, frozen evaluation set, leakage test"

cd "$(dirname "$0")/../../.."
exec > >(tee .git/publish_week2.log) 2>&1

step() { printf '\n==== %s ====\n' "$1"; }
stop() { printf '\nSTOPPED: %s\n' "$1"; exit 1; }

step "1/8 Checking the repository"
git rev-parse --is-inside-work-tree >/dev/null || stop "not a git repository"
gh auth status >/dev/null 2>&1 || stop "gh is not logged in (run: gh auth login)"
[ "$(git branch --show-current)" = "$BRANCH" ] || git switch "$BRANCH"
if ! git diff --quiet || ! git diff --cached --quiet; then
  git status --short
  stop "there are uncommitted changes to tracked files; tell Claude before continuing"
fi
git log --oneline -8

step "2/8 Fetching GitHub"
git fetch origin --prune
NEW=$(git rev-list --count HEAD..origin/main)
if [ "$NEW" -gt 0 ]; then
  echo "GitHub main has $NEW commit(s) this branch does not have:"
  git log --oneline --format='%h  %an  %s' HEAD..origin/main
  echo "Merging them into $BRANCH so the PR is up to date..."
  git merge --no-edit origin/main || {
    git merge --abort || true
    stop "merge conflict with teammates' work; nothing was pushed. Tell Claude."
  }
else
  echo "GitHub main has nothing new. Branch is up to date."
fi

step "3/8 Installing pinned dependencies"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
"$PY" -m pip install -q -r requirements-dev.txt
"$PY" -m pip install -q -e .

step "4/8 Lint and tests on this Mac (same commands as CI)"
"$PY" -m ruff check src scripts tests || stop "lint failed"
"$PY" -m pytest || stop "tests failed; nothing was pushed"

step "5/8 Pushing $BRANCH"
git push -u origin "$BRANCH"

step "6/8 Opening the pull request"
PR=$(gh pr list --repo "$REPO" --head "$BRANCH" --state open --json number --jq '.[0].number // empty')
if [ -z "$PR" ]; then
  gh pr create --repo "$REPO" --base main --head "$BRANCH" --title "$TITLE" \
    --body-file docs/progress/week-02/pr_body.md
  PR=$(gh pr list --repo "$REPO" --head "$BRANCH" --state open --json number --jq '.[0].number')
fi
echo "Pull request #$PR"

step "7/8 Waiting for GitHub Actions"
for _ in $(seq 1 18); do
  if gh pr checks "$PR" --repo "$REPO" >/dev/null 2>&1 || [ $? -eq 8 ]; then break; fi
  sleep 10
done
gh pr checks "$PR" --repo "$REPO" --watch --interval 15 \
  || stop "CI failed on PR #$PR. Nothing was merged. See: gh run view --repo $REPO --log-failed"

step "8/8 Merging into main"
gh pr merge "$PR" --repo "$REPO" --merge --delete-branch
git switch main
git pull --ff-only origin main
git log --oneline -8
sleep 15
gh run list --repo "$REPO" --branch main --limit 3

printf '\nDONE. Week 2 is merged into main. PR: https://github.com/%s/pull/%s\n' "$REPO" "$PR"
