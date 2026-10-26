# 0012. Dashboard stack and Streamlit fallback

**Status:** Accepted. Decided by the owner of M7; the dashboard stack affects no other member's deliverable.
**Date:** 2026-10-26
**Owner:** Alishba Fayaz
**Related:** 0004 (one model per atlas, so four atlases are offered), 0006 (model architecture, meaning of confidence), 0008 (database schema), 0010 (calibration, in draft), 0013 (analysis log and API contract, in draft), 0014 (fixture data, in draft)

## Context

M7, the web dashboard, is the presentation layer of NeuroGraph-X. The final work plan needs
it working end to end on real data by 8 November (W6-10), feature complete on 15 November
(W7-24) and demonstrable in the FYP-I evaluation window (23 November to 4 December). It has
seven pages: Overview, Participants, Analysis, History, Models, Exclusions and About.

The revised system proposal (section 6.4) names React, JavaScript, HTML and CSS for the
frontend, FastAPI behind it, and NiiVue for brain visualisation in FYP-II. Its risk table
lists "Frontend work expands and displaces model work" as a medium risk, mitigated by keeping
the first dashboard minimal. This memo fixes the stack and also states, in advance, the rule
for abandoning it, so that the choice is not made under pressure later.

Constraints: one person builds the dashboard; the API contract is not frozen until 29 October
(W5-01); CI runs on Ubuntu with Python 3.11 (`.github/workflows/ci.yml`); the dashboard must
work on fixture data (memo 0014), so it never waits for real models.

## Decision

### Primary stack: React with Vite

| Concern | Choice |
|---|---|
| Framework | React |
| Build tool and dev server | Vite |
| Language | JavaScript (JSX), as in the proposal. Not TypeScript |
| Routing | React Router, client side, one route per page |
| Talking to the API | Browser `fetch` through one module, `dashboard/src/api/client.js`. No data-fetching library |
| Styling | Plain CSS. No component library |
| Lint | ESLint, with the configuration the Vite React template provides |
| Unit tests | Vitest with React Testing Library (W5-16) |
| End-to-end test | Playwright, in CI, fixture mode (W6-13) |
| Node.js | 24 (LTS) |
| Packages | npm. Exact versions in `package.json`, `package-lock.json` committed, CI installs with `npm ci` |
| Location | `dashboard/` at the repository root |

Versions checked on 2026-10-26: React 19.3.1 (released 14 October 2026), Vite 8.3.4, and
Node.js 24 with security support until April 2028. The lock file written at scaffold time
(W4-19), not this memo, is the record of the versions in use. Node.js 26 is the next LTS
line; it is not adopted now so that the toolchain does not change mid-term.

Not decided here: the chart library (decided when the first chart is built, W7-16), the
brain viewer (NiiVue, FYP-II) and how the built dashboard is served in the final demo and in
the FYP-II Docker package.

### How the dashboard talks to the API

- The dashboard is a client of the REST API only. It never reads files under `data/`,
  `runs/` or `db/`, and never imports `neurographx`. This keeps the architecture and
  sequence diagrams true: the dashboard calls the Model Service REST API (M3), and M3
  reaches everything else.
- In development Vite proxies `/api` to `http://127.0.0.1:8000` and removes the prefix. The
  API needs no CORS change and its routes stay as documented. The same proxy is set for
  `vite preview`.
- Any 404, 409, 422 or 503 response shows its `detail` text in plain language (error
  contract, memo 0013). A failed call never leaves a blank page.
- When the API runs in fixture mode (`NGX_DATA=fixtures`), the dashboard shows a visible
  "fixture data" marker, so a screenshot of fixture results cannot be mistaken for a real
  result. This needs `GET /health` to report the data mode (see To confirm).

### Pages and the endpoints they use

| Page | Endpoints | Built in |
|---|---|---|
| Participants | `GET /participants` with filters (W5-03) | W5-14 |
| Analysis | `GET /atlases` (W5-02), `POST /analyses` (W5-09) | W5-15 |
| History | `GET /analyses`, `GET /analyses/{analysis_id}` (W5-07); later export and regenerate (W6-06, W6-07) | W6-12, W7-17 |
| Models | `GET /models`, `GET /models/{atlas}` (W5-10) | W6-11 |
| Exclusions | `GET /exclusions` (W5-02) | W7-15 |
| Overview | `GET /cohort/summary` (W5-02) | W7-16 |
| About | `GET /health`, static text | Iteration 7 |

### Display rules carried over from earlier decisions

- Every page carries the research-use notice: a research analysis tool, not a diagnosis, not
  a medical device. The proposal (section 7.3) requires this in the interface itself.
- Confidence is the softmax probability of the predicted class, between 0.5 and 1, not the
  probability of autism (memo 0006). The result shows it as confidence in this prediction,
  next to the `calibrated` flag, and labels it "not calibrated" while `calibrated` is false,
  until the calibration of memo 0010 is registered (W6-04).
- An excluded participant cannot be run: the Run button is disabled and the exclusion reason
  from the quality screen (memo 0003) is shown.
- Every result shows the atlas, `run_id` and `analysis_id`, so it can be traced to a
  training run (memo 0008).

### Fallback rule: Streamlit

**When.** Sunday 1 November 2026 (W5-18). One decision, made once, recorded at the end of
this memo and in `docs/progress/week-05/log.md`.

**Test.** The API runs in fixture mode, the dashboard runs from its branch, and every check
below is shown in one sitting. A short recording or screenshots go in
`docs/progress/week-05/`.

| # | Check |
|---|---|
| P1 | Participants lists participants from `GET /participants` with the total, included and excluded counts |
| P2 | The site, group and quality-status filters work and combine |
| P3 | An excluded participant shows its exclusion reason and its Run button is disabled |
| A1 | On Analysis, an included participant and one of the four atlases can be chosen and run |
| A2 | The result shows prediction, confidence, calibrated, atlas, run_id, analysis_id and the research-use notice |
| A3 | An API error (409 for an excluded participant, 503 for no model) shows its `detail` text |
| C1 | The `frontend` CI job (W4-20) is green on the dashboard branch |

**Rule.** If any check fails on 1 November, React is dropped and the Streamlit dashboard
below is built. If all pass, React stays, the fallback is closed and there is no later
switch.

**What does not count against React.** The test measures the dashboard, not the backend. If
`POST /analyses` (W5-09) is not merged by 1 November, checks A1 to A3 are run against a stub
that returns the response shape in memo 0013, and the missing endpoint is reported as a
backend delay. A late backend never triggers the fallback, because a Streamlit dashboard
would call the same endpoint.

**What the fallback is.**
- A Streamlit app in `dashboard_streamlit/` with the same seven pages in the same order and
  the same research-use notice on every page. The `dashboard/` folder is removed from `main`
  in the same pull request and stays in git history.
- It calls the same REST API with `requests`, which is already pinned in
  `requirements.txt`. It does not import `neurographx`, so the architecture stays M7 over
  REST over M3.
- Tests: pytest with Streamlit's `AppTest` replaces Vitest, and the Playwright test (W6-13)
  is dropped. The manual test cases (W5-17) do not change, because they are written per use
  case.
- CI: the `frontend` job is removed, and Streamlit is added to the Python requirements with
  an exact pin at the moment the fallback is triggered.
- Dates do not move: Participants and Analysis on live data by 4 November (W6-10), History
  by 6 November (W6-12), Models by 8 November (W6-11).
- Documents that name React are updated: the as-built architecture diagram (W6-14), the
  dashboard section of the report (W7-21) and SETUP.md.

**Readiness check, by Thursday 29 October.** So that the fallback is real, install Streamlit
in the project's virtual environment on the Windows machine and run a one-page test app
against the fixture-mode API. That machine runs Python 3.14 while CI runs 3.11, and
`pyyaml==6.0.2` already fails to install on 3.14, so the fallback must not be tried for the
first time on 1 November.

## Rationale

- React is what the proposal names, so the dashboard matches the approved design.
- The FYP-II brain viewer (NiiVue) is a browser WebGL library. A React page hosts it
  directly; Streamlit would need a custom component.
- A separate frontend shows that the REST API (deliverable D2) is complete enough for
  something other than its authors to use, which is the engineering gap in the project
  statement.
- Vite is a small standard setup with quick rebuilds, and Vitest shares its configuration.
- JavaScript rather than TypeScript: the proposal says JavaScript, and types add setup and
  learning time to a four week build with one frontend owner.
- Plain CSS and no component library keep the dependency list short, which means fewer
  packages to pin, update and explain.
- A written fallback with a test and a date caps the cost of a wrong choice at about a week.

## Alternatives considered

- **Streamlit as the primary dashboard.** The fastest to build and all Python. Rejected as
  the primary choice because of the viewer and API-client points above. Kept as the fallback.
- **Next.js or another React framework.** Adds a second server and server rendering the
  dashboard does not need.
- **Vue or Svelte.** Not in the proposal, and there is no reason to depart from it.
- **Serving the dashboard from FastAPI.** Possible for a one process demo. Left open for the
  FYP-II Docker package.
- **A CORS rule in the API instead of the Vite proxy.** Works, but changes API code that is
  frozen on 29 October, for no gain in development.

## Consequences

- The repository gets a second toolchain, Node.js. The existing `.gitignore` already covers
  `dist/` and `.venv/`; it needs `node_modules/` added. An `.npmrc` with `save-exact=true`
  keeps versions exact, like `requirements.txt`. The scaffold (W4-19) adds both.
- CI gets a second job (W4-20): `npm ci`, lint and build, plus the Vitest tests from Week 5.
  It runs on the same triggers as the existing `test` job. The ruleset on `main` requires
  the `test` check (SETUP.md, step 6), so a repository admin adds `frontend` to the required
  checks once the job exists.
- SETUP.md needs a dashboard section (install Node 24, `npm ci`, start the API, start the
  dashboard), and the clean-clone test (W8-08) checks it. Whether the presentation laptop
  runs the dashboard from Node 24 or from a served build is settled with the SETUP.md draft
  (W7-07).
- Dashboard work depends on the API contract in memo 0013, frozen at W5-01. A change after
  that goes through an amendment to 0013 and a message to the dashboard owner.
- If the fallback is triggered, brain visualisation in FYP-II needs either a Streamlit
  component or a return to React. FYP-I does not use it.

## Needs from teammates

These are requests, not conditions. The decision above stands without them; they only
confirm that the API side matches what the dashboard will call.

- [ ] Aleesha: fixture mode (memo 0014) serves every endpoint the Participants and Analysis
  pages call, and `GET /health` reports the data mode (fixtures or real).
- [ ] Laiba: the `POST /analyses` response in memo 0013 carries `participant_id`, `atlas`,
  `prediction`, `confidence`, `calibrated`, `run_id` and `analysis_id`.

## To do by the owner

- [ ] Alishba: the Streamlit readiness check is done by 29 October.

## Decision on 1 November (W5-18)

To be filled in on the day.

- Checks P1 to C1:
- Result (React kept, or switched to Streamlit):
- Evidence (file in `docs/progress/week-05/`):

Sources for the version check: vite.dev/releases, endoflife.date/react, endoflife.date/nodejs.
