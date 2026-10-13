# [Project name] — Design Document

| | |
|---|---|
| **Authors** | [everyone who wrote it] |
| **Reviewers** | [who reviewed it — a teammate, the instructor, a design-review partner] |
| **Status** | Draft · In review · Approved · Superseded |
| **Last updated** | [date] |
| **Links** | [proposal] · [repository] · [issue tracker] |

## Revision history

*A design doc changes as the design does. Record each meaningful revision so a reader can tell what the doc said when a decision was made.*

| Date | Author | What changed |
|---|---|---|
| [date] | [name] | First draft |

---

## 1. Context and scope

*One or two paragraphs. What is being built, for whom, and what landscape it sits in. Link the proposal instead of repeating it — a reader who needs the full argument can follow the link.*

## 2. Goals and non-goals

**Goals** — *what this design must achieve, stated so you could check them:*

- [goal]

**Non-goals** — *things a reasonable reader would expect this system to do, which it deliberately won't. Carry them over from the proposal; here they bound the design.*

- [non-goal]

## 3. System-context diagram

*The system as a single box. Around it, every kind of user and every external service it depends on. Label every arrow with what crosses the boundary. A photo of a whiteboard is fine; a diagram that disagrees with the prose is not.*

[diagram]

## 4. Architecture and components

*Three to six components. For each: what it is responsible for, what it talks to, and its rough interface. A paragraph each — no code.*

| Component | Responsibility | Talks to | Interface (rough) |
|---|---|---|---|
| [name] | [one sentence] | [components / services] | [e.g., HTTP form posts, function calls, a queue] |

[component diagram]

### Core flow, traced end to end

*The single most important user action in your MVP, step by step through the components above. If the trace needs a component the table doesn't have, the table is wrong.*

1. [step]

### The failure case

*The same flow when something goes wrong — the network drops, an external service is down, two people act at once. What does the user see, and where does the system recover?*

1. [step]

## 5. Data model

*Entities, their key fields, and how they relate. Mark what the MVP needs and what only the roadmap needs. Key fields, not every column; no copied schemas.*

| Entity | Key fields | Relationships | MVP or roadmap |
|---|---|---|---|
| [entity] | [fields] | [e.g., belongs to one Show] | MVP |

## 6. Technology choices and alternatives considered

*One block per significant decision. The alternative must be one a reasonable team would actually pick. Where you did real work to decide — a spike, a benchmark, a prototype — cite it; that evidence is the difference between a preference and a decision.*

### Decision: [what was decided]

- **Chosen:** [option]
- **Alternative considered:** [option]
- **Why the chosen option wins, given our goals:** [reasoning]
- **Evidence:** [spike, measurement, prototype, prior experience — or "none yet"]
- **What would change our mind:** [the condition under which you'd switch]

## 7. Risks and open questions

*What you don't know yet, stated honestly. Each open question gets an owner and a way to find the answer.*

| Risk or question | Why it matters | Owner | How we'll find out, and by when |
|---|---|---|---|
| [risk] | [consequence] | [name] | [spike / test / conversation — milestone] |

## 8. Implementation plan

*The build order at milestone altitude — not a task list. Start with the thinnest vertical slice through the core flow, then widen it.*

| Milestone | What works when it's done | Depends on |
|---|---|---|
| 1 | [the thinnest end-to-end slice] | — |

---

## Sign-off

*Who reviewed this version and agreed it is ready to build from.*

| Reviewer | Role | Date | Approved |
|---|---|---|---|
| [name] | [role] | [date] | ☐ |
