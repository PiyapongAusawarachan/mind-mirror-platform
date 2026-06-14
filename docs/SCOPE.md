# Mind Mirror Platform — Scope

> Implementation checklist extracted from the proposal.

## Status: MVP + advanced features delivered

### Phase 2 additions (delivered)

- [x] Multiple-choice questions alongside open-ended (auto-graded)
- [x] Quiz answers via typing / photo / audio (not just typing)
- [x] Long-term mastery timeline (per-lesson + course-wide), multi-week demo history
- [x] Internationalization: Thai (default) + English with switcher
- [x] Production-grade UI redesign + cleaner route names (`/student/lessons`, `/student/quiz`)
- [x] Production setup: Docker + docker-compose (Postgres), gunicorn, security headers,
      secure cookies, trusted hosts, optional HTTPS redirect, env-driven config
- [x] Automated test suite (pytest) — auth, student flow, teacher flow, units


## Confirmed decisions

| Decision | Choice |
|----------|--------|
| Interface | Web application |
| Backend | FastAPI + Jinja2 templates |
| Frontend | Server-rendered HTML + vanilla JS; Cytoscape.js (knowledge map), Chart.js (pie charts) via CDN |
| AI provider | OpenAI (chat for analysis/grading, vision for image OCR, Whisper for speech) |
| PDF text | pypdf (local extraction) |
| Storage | SQLite via SQLAlchemy; uploaded files on disk under `data/uploads/` |
| Auth | Lightweight session-based, role = student or teacher |
| Build order | MVP: student S1→S4, then teacher T1/T2 |
| Context | Academic course project, single class, demo data, runs locally |
| AI fallback | Mock responses when `OPENAI_API_KEY` is absent, so the app always runs |

## Goals

- Help students surface and close gaps in understanding through self-explanation + AI feedback.
- Give teachers a clear, per-student and per-topic view of understanding before/after assessment.

## Roles

- **Student** — creates learning contexts, explains content, views knowledge map, takes assessments.
- **Teacher/Lecturer** — views dashboards, per-student and per-topic understanding, progress over time.

## Student features

- [ ] **S1. Learning context creation**
  - [ ] Upload PDF
  - [ ] Upload JPEG/image
  - [ ] AI extracts/understands content scope (text extraction + topic detection)
- [ ] **S2. Explain content in own words**
  - [ ] Typing input
  - [ ] Handwriting via photo upload (image → text)
  - [ ] Speaking input (audio → text)
- [ ] **S3. Blind-spot / misconception detection**
  - [ ] Compare learner explanation vs source material
  - [ ] Classify topics: understood / confused / not understood
  - [ ] **Knowledge Map** visualization with subtopic relationships
- [ ] **S4. Personalized assessment**
  - [ ] Generate open-ended questions targeted at weak areas
  - [ ] Answer via typing / speaking / writing (no multiple choice)
  - [ ] AI grades conceptual understanding + feedback

## Teacher features

- [ ] **T1. Teacher Dashboard**
  - [ ] Per-student understanding state (pre-assessment): understood / confused / not understood
  - [ ] Post-assessment scores
  - [ ] Improvement tracking (which weak topics improved / still weak)
- [ ] **T2. Long-term per-topic pie chart** (e.g. understood 70% / confused 20% / not 10%)

## Cross-cutting

- [ ] Authentication + role separation (student vs teacher)
- [ ] Class/course grouping (link students to a teacher/course)
- [ ] Persistent storage for materials, explanations, maps, assessments, results
- [ ] AI integration layer (LLM + OCR + speech-to-text)

## Out of scope (proposed defaults — confirm)

- Multiple-choice questions (explicitly excluded by proposal)
- Real-time collaboration / chat
- Mobile native apps (web-first assumed)
- Payment/billing

## Technical decisions

| Decision | Choice | Notes |
|----------|--------|-------|
| Runtime | Python 3 | Current codebase |
| Interface | **TBD** | Proposal needs web (uploads, audio, dashboards, 2 roles) |
| Web framework | **TBD** | Candidate: FastAPI + frontend, or Django, or Flask |
| Frontend | **TBD** | Candidate: React/Next.js for knowledge map + charts |
| AI / LLM | **TBD** | Provider + API key (e.g. OpenAI) vs local models |
| OCR (image→text) | **TBD** | e.g. Tesseract (local) vs cloud vision |
| Speech-to-text | **TBD** | e.g. Whisper (local) vs cloud API |
| Knowledge map UI | **TBD** | e.g. Cytoscape.js / react-flow / D3 |
| Charts | **TBD** | e.g. Chart.js / Recharts |
| Storage | **TBD** | SQLite (dev) → Postgres; file storage for uploads |
| Auth | **TBD** | Session vs JWT |

## Open questions — resolved

1. Interface → **Web application** ✅
2. AI provider → **OpenAI** ✅
3. First build → **Focused MVP** (student S1–S4, then teacher) ✅
4. Audience → **Academic course project, runs locally** ✅

## Phasing (proposed)

| Phase | Focus |
|-------|-------|
| 1 — Foundation | Web app skeleton, auth + roles, data models, upload + storage |
| 2 — Student core | S1 context ingestion (PDF/image OCR), S2 multi-modal input, S3 analysis + knowledge map |
| 3 — Assessment | S4 personalized open-ended questions + AI grading |
| 4 — Teacher | T1 dashboard, T2 per-topic pie charts, progress tracking |
| 5 — Polish | Tests, seed/demo data, docs, deployment notes |
