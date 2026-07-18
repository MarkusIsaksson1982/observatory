# Decision Log — Observatory

*Captain's log. Chronological record of why decisions were made. Not ADRs — those are formal. This is the narrative.*

---

## 2026-07-18

**Decision:** Freeze governance (PROJECT_CONSTITUTION.md v1.0) before any implementation.
**Reason:** Prevent planning loop; establish evidence-first discipline from commit #1.
**Reference:** Architecture Review → Constitution v1.0
**Impact:** All future architectural changes require ADR; implementation changes go to Roadmap.

---

## 2026-07-18

**Decision:** Begin with Gateway telemetry → Alloy before adding LGTM backends.
**Reason:** Validate signal flow independently; "telemetry first, infrastructure second."
**Reference:** Phase 1.5 recommendation; ADR-001
**Impact:** Phase 1 scope reduced to Gateway + Alloy only. LGTM added in Phase 1.5.

---

## 2026-07-18

**Decision:** Three-output rule for every task — (1) working code, (2) portfolio evidence, (3) documentation paragraph.
**Reason:** Keep portfolio evidence synchronized with implementation; prevent docs debt.
**Reference:** Design Principle #12; Portfolio Evidence Map
**Impact:** Every PR must include screenshot/update to CAPABILITY_MATRIX.md / PORTFOLIO_EVIDENCE.md + one-paragraph IMPLEMENTATION_STATUS.md entry.

---

## 2026-07-18

**Decision:** Repository name = `observatory` (matching fullstack-observatory, hpc-observatory brand).
**Reason:** LGTM is the first implementation, not the identity. Extensible to K8s, Pyroscope, eBPF, service mesh.
**Reference:** Constitution Section 14
**Impact:** Repo created at github.com/MarkusIsaksson1982/observatory