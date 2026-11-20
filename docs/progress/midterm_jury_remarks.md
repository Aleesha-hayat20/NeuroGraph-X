# Midterm jury remarks

**Midterm defence:** Wednesday 21 October 2026
**Written remarks released:** Tuesday 17 November 2026
**Board task:** #44, "Log every midterm jury comment as its own issue with an owner"

Each remark is its own issue with an owner, quoted exactly as released.

| # | Remark | Owner | Issue | Response | Status on 17 November |
|---|---|---|---|---|---|
| 1 | "Moving the project from a strictly research domain to a more real-world application can be helpful." | Aleesha | #162 | Memo 0015: reposition and extend, approved by the supervisor on 17 November | Memo accepted; README, SRS and report outline updated; final deck slide pending |
| 2 | "Design/analysis figures need reordering." | Alishba | #163 | Analysis figures first, then design figures, in the same order in the deck and the report | Open |
| 3 | "Class diagram should use standard annotations." | Alishba | #164 | Class diagram redrawn in standard UML notation | Redrawn; in review |

## 1. Real-world application

The system keeps its disorder, data, models and modules, and names its real user: research
groups and hospital research units with their own resting-state fMRI. FYP-II opens the
system to their uploaded data, checks how far the data resemble the training data, and
reports with every result how far it can be trusted on an unseen scanner. Full decision,
FYP-I changes and FYP-II order of work:
[memo 0015](../decisions/0015-real-world-repositioning.md).

## 2. Order of the design and analysis figures

Analysis figures describe what the system must do; design figures describe how it is
built. The final rubric marks them as separate rows (CLO2: system analysis diagrams, system
design diagrams), so the deck and the report present them in two groups. Proposed order, to
be confirmed by Alishba:

1. **Analysis:** use case diagram; activity diagram; DFD level 0; DFD level 1.
2. **Design:** system architecture; class diagram; sequence diagram for running an
   analysis; sequence diagram for regenerating an analysis; ER diagram (database schema).

Applies to the final deck, Report Chapter 3 and its list of figures. The Chapter 3 outline
in `docs/report/README.md` still interleaves the two groups (3.1 architecture comes before
3.2 use cases) and is reordered in the same change.

## 3. Class diagram notation

Standard UML class notation (OMG Unified Modeling Language 2.5.1,
https://www.omg.org/spec/UML/2.5.1):

- Three compartments per class: name, attributes, operations.
- Visibility on every member: `+` public, `-` private, `#` protected, `~` package.
- Attributes as `name: Type`; operations as `name(parameter: Type): ReturnType`.
- Abstract classes and operations in italics; static members underlined; interfaces marked
  `<<interface>>`.
- Relationship lines with the standard ends: generalisation (hollow triangle), realisation
  (dashed line, hollow triangle), composition (filled diamond), aggregation (hollow
  diamond), dependency (dashed arrow), and multiplicities (`1`, `0..1`, `*`, `1..*`) at both
  ends of every association.

The redrawn class diagram, the DFD level 1 and the sequence diagram for regenerate are
committed under `docs/design/` with their source files, so the deck, the report and the
repository show the same versions.
