# Decision Log — Observatory

*Chronological record of why decisions were made.*

---

## 2026-07-23

**Decision:** Qwen's fault injector integrated as-is — no gateway code changes needed.
**Reason:** Empirical check of `/orders` span in Tempo confirmed `STATUS_CODE_ERROR` is already set automatically. The `httpx.ConnectError` propagates through `span.record_exception(e)` at `main.py:116`, flipping the span to ERROR before `HTTPException(503)` is raised. FastAPI auto-instrumentation captures the exception on the HTTP span. Nemotron's concern about span status not flipping was invalid for this codebase. Zero gateway changes = zero risk to `main.py` (which has hard-won history — SPAN_KIND_SERVER bug, `instrument_app()` fix).
**Reference:** Tempo trace inspection (`/api/traces/{traceID}`), span `status.code = STATUS_CODE_ERROR` confirmed
**Impact:** `tools/fault-injector.py` placed from Qwen's contribution. Old `ansible/fault-injector.yml` (which fabricated error responses instead of generating real failure traffic) removed. `--probe-only` mode verified working.

---

**Decision:** Gemini's Alloy cleanup applied — dead spanmetrics connector removed.
**Reason:** `otelcol.connector.spanmetrics` had `output { metrics = [] }` (disabled per ADR-011), making the entire branch dead code: the `keep_keys` transform processor that fed it, the connector itself, and the orphaned `otelcol.exporter.prometheus "default"` (defined but never referenced). Scrape blocks already wire directly to `prometheus.remote_write.mimir.receiver` — confirmed live, not completed by Gemini's change. ADR-011 preserves the historical context. `config.river` reduced from 160 to 107 lines.
**Reference:** Gemini 3.1 Pro contribution (Option 3: Dead code review), Claude Sonnet 5 verification that scrape blocks were already wired
**Impact:** `alloy/config.river` cleaned. Alloy restarted, healthy. Traces verified flowing post-cleanup.

---

**Decision:** Ansible implemented from Muse Spark's contribution — Grafana version fixed.
**Reason:** Muse Spark was the only Ansible contribution that addressed both concerns the prompt named (host provisioning + env-specific config templating) and showed awareness that Terraform now owns Grafana provisioning (`terraform plan still 0/0/0` in its README). DeepSeek, GLM-5.2, and Mistral-Vibe all wrote "install Docker, run compose up" without env templating. One bug fixed: `group_vars/all.yml` pinned `grafana_version: "11.1.0"` but `docker-compose.yml` runs `grafana/grafana:13.1.0` — corrected before implementation. `failed_when: false` on Docker service task signals awareness of running inside containers.
**Reference:** Muse Spark contribution, Claude Sonnet 5 triage
**Impact:** Full Ansible structure implemented: `ansible.cfg`, `inventory.ini`, `group_vars/all.yml`, `templates/env.j2`, `templates/docker-compose.override.yml.j2`, `playbook.yml`, `README.md`. Old `setup.yml` removed. YAML syntax validated.

---

**Decision:** Deployer-guide.md corrected — `make validate` does not run correlation script.
**Reason:** DeepSeek flagged that `deployer-guide.md` claims `make validate` runs `scripts/validate_trace_log_correlation.py`, but the Makefile's actual `validate` target only does health checks via curl (Alloy + Gateway). Verified: deployer-guide.md was misleading. Corrected to document both `make validate` (health checks) and the separate `python scripts/validate_trace_log_correlation.py` command.
**Reference:** DeepSeek contribution, Makefile inspection
**Impact:** `docs/deployer-guide.md` corrected.

---

## 2026-07-21

**Decision:** Configure custom histogram_buckets in Tempo instead of accepting 512ms approximation.
**Reason:** `le="0.512"` is not cosmetically different from `le="0.5"` — it's measuring a looser SLI than the one documented. The fix was already fully specified in the ADR writeup (custom `histogram_buckets` config), and the "additional cardinality" cost was overstated — it replaces Tempo's default bucket list with a similarly-sized custom one, not adds buckets on top. Given the fix is a known, contained config change, applied it rather than carry the 512-vs-500 gap forward.
**Reference:** ADR-011 technical detail section, Tempo span-metrics documentation
**Impact:** `tempo.yml` updated with `histogram_buckets: [0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]`. Sloth SLO spec reverted to `le="0.5"`. Rules regenerated and deployed via `docker cp`. Mimir restarted. `le="0.5"` confirmed returning data. README updated from "512ms" back to "500ms". ADR-011 updated to reflect the fix is applied, not deferred.

---

**Decision:** Fix Tempo histogram bucket mismatch — `le="0.5"` → `le="0.512"` in SLO latency queries.
**Reason:** Tempo metrics-generator uses custom histogram boundaries (powers of 2), not Prometheus defaults. The bucket `le="0.5"` does NOT exist in `traces_spanmetrics_latency_bucket`. The closest bucket is `le="0.512"`. The `le="0.5"` value in Mimir's global label values list comes from OTHER metrics (Alloy internals), not from Tempo's span metrics. Using the wrong bucket returns empty results, causing the latency SLO recording rules to produce NaN and fail to store.
**Reference:** Mimir label values verification (`/api/v1/label/le/values` showed `0.5` but querying `traces_spanmetrics_latency_bucket{le="0.5"}` returned empty; `le="0.512"` returned data)
**Impact:** Sloth SLO spec updated (`sloth/gateway-slo.yaml`), rules regenerated (`sloth/gateway-slo-rules.yaml`), rules copied into Mimir container via `docker cp`, Mimir restarted. Latency SLO recording rules now evaluate correctly. `slo:sli_error:ratio_rate5m` now appears in Mimir's `__name__` label values.

---

**Decision:** Fix FastAPI auto-instrumentation initialization order to produce SERVER spans.
**Reason:** FastAPI auto-instrumentation was not creating SPAN_KIND_SERVER spans because `FastAPIInstrumentor().instrument()` was called before the app was created. The instrumentor replaces `fastapi.FastAPI` with `_InstrumentedFastAPI` whose `__init__` adds `OpenTelemetryMiddleware`. But the local name `FastAPI` in `main.py` was bound before the patch, so the app used the original (uninstrumented) class. Additionally, the singleton pattern meant the second call was a no-op. Fix: call `FastAPIInstrumentor().instrument()` BEFORE `from fastapi import FastAPI` so the patched class is bound.
**Reference:** Root cause analysis of `opentelemetry-instrumentation-fastapi 0.46b0` source code
**Impact:** SERVER spans now appear in Tempo traces and generate metrics. Dashboard and SLO queries updated to filter by `span_kind="SPAN_KIND_SERVER"` and use `status_code` label (not `status`). All 6 panels and 2 SLOs now correctly measure server-side RED metrics.

---

**Decision:** Fix `status` → `status_code` label mismatch in dashboard and SLO queries.
**Reason:** Tempo metrics-generator uses `status_code` label for span status (`STATUS_CODE_OK`, `STATUS_CODE_ERROR`, `STATUS_CODE_UNSET`), not `status`. The `status` label exists in Mimir but contains different values (Alloy/Mimir internals). Dashboard error rate and SLO error queries were using the wrong label name.
**Reference:** Mimir label values verification (`/api/v1/label/status_code/values` vs `/api/v1/label/status/values`)
**Impact:** Dashboard and SLO now correctly filter by `status_code="STATUS_CODE_ERROR"` for error rate calculations.

---

**Decision:** Add `span_kind="SPAN_KIND_SERVER"` filter to all RED dashboard and SLO queries.
**Reason:** Without filtering by span kind, metrics aggregate CLIENT, INTERNAL, and SERVER spans together. RED metrics should measure server-side request rate/error rate/latency. SERVER spans represent the actual HTTP request boundary.
**Reference:** OpenTelemetry span kind semantics, RED methodology
**Impact:** Dashboard panels and SLO queries now only measure SERVER spans, providing accurate HTTP RED metrics.

---

**Decision:** Tempo metrics-generator is the primary RED metrics source (ADR-011 accepted).
**Reason:** Portfolio signal (Tempo metrics-generator is more advanced than Alloy connector), aligns with Grafana Labs recommended architecture, exemplars enabled, single source of truth for SLOs. Evaluated OTTL transform as alternative — found it silently dropped metrics (Alloy experimental component), reverted to raw names. Dual-source causes double-counting; recording rules abstraction deferred as unnecessary complexity for now.
**Reference:** ADR-011, multi-model analyses (muse-spark, mimo, chatgpt, deepseek, minimax, qwen), empirical Mimir verification
**Impact:** Dashboard and SLO migrated to Tempo metric names (`traces_spanmetrics_*`) and labels (`service`, `status`). Alloy spanmetrics output set to `[]`.

---

**Decision:** Add custom dimensions to Tempo metrics_generator: `http.method`, `http.route`, `http.status_code`.
**Reason:** Default Tempo span-metrics only emit intrinsic labels (`service`, `span_name`, `span_kind`, `status`). HTTP method and route dimensions are needed for service-level drill-down in the RED dashboard and for filtering by endpoint in SLO queries. `http.status_code` adds numeric HTTP status for compatibility with Alloy-style queries.
**Reference:** Grafana Tempo span-metrics documentation, nais.io span-metrics reference
**Impact:** Tempo config updated; new labels available in Mimir after restart.

---

## 2026-07-19

**Decision:** Switch from Nemotron to Big Pickle as primary implementer, Claude Sonnet 5 as senior planner.
**Reason:** Nemotron buried a missing config file under governance docs and never produced a running container. Big Pickle's Task B session was the only one where the stated goal was actually met. Claude Sonnet 5 has the full architectural vision and ecosystem knowledge.
**Reference:** Model comparison results (Task A + Task B)
**Impact:** Three-model workflow: Claude (planner) → ChatGPT (interim planner) → Big Pickle (implementer)

---

**Decision:** Fix Alloy healthcheck with `bash -c 'echo > /dev/tcp/localhost/12345'` instead of curl.
**Reason:** grafana/alloy:v1.5.0 has no curl/wget. Bash TCP check is the most reliable in-container option.
**Reference:** Big Pickle diagnostic session, Claude Sonnet 5 analysis
**Impact:** Gateway can now start (depends_on: alloy: condition: service_healthy passes)

---

**Decision:** Wire Alloy OTLP receiver → `otelcol.exporter.loki` → `loki.write` → Loki.
**Reason:** The empty `output {}` block meant no logs flowed anywhere. This fix makes the pipeline functional end-to-end.
**Reference:** Big Pickle Task B session (the only one that closed this gap)
**Impact:** Logs now actually flow from Gateway through Alloy to Loki

---

**Decision:** Use Loki TSDB schema (not deprecated boltdb-shipper).
**Reason:** Loki 3.x defaults to TSDB. boltdb-shipper is deprecated.
**Reference:** Grafana Loki 3.x documentation
**Impact:** Future-proof storage backend

---

**Decision:** Gateway CMD changed to `python main.py` (removed `opentelemetry-instrument` CLI).
**Reason:** `instrumentation.py` already does manual instrumentation. The CLI is redundant and caused import conflicts.
**Reference:** Big Pickle diagnostic session
**Impact:** Simpler Dockerfile, no dependency on opentelemetry-instrument CLI

---

**Decision:** Create AI Execution Roadmap as the single source of truth for project planning.
**Reason:** Multiple models produced analyses but no unified plan. The roadmap consolidates version blocks, metadata, decision classes, and model role assignments.
**Reference:** ChatGPT's AI Execution Roadmap concept, Gemini's JSON roadmap, Grok's milestones
**Impact:** All hand-offs reference this document

---

**Decision:** FORK_01 — Tempo storage: local filesystem.
**Reason:** Consistent with Loki's filesystem storage pattern. Durable across `docker compose down/up` — traces survive restart. Only option that supports "close the laptop, come back tomorrow." Ephemeral storage would require regenerating traffic before every demo.
**Reference:** Claude Sonnet 5 senior planning review
**Impact:** Tempo uses `local` backend in v0.3.0

---

**Decision:** FORK_02 — Mimir mode: single-binary.
**Reason:** Keeps `docker compose up` as a one-command demo instead of a 10-container fan-out. One sentence in the Mimir ADR ("single-binary for local demo; production would split into microservices mode for independent scaling") signals the tradeoff knowledge without paying for operational complexity.
**Reference:** Claude Sonnet 5 senior planning review
**Impact:** Mimir uses single-binary mode in v0.5.0

---

**Decision:** FORK_03 — Terraform migration moved from v2.0.0 to v0.6.0.
**Reason:** Terraform is a named, required skill on the job posting, listed twice. Shipping v1.0.0 without it leaves a gap against the target role that's easy to close. ADR-009 already decided Phase 2 = Terraform; timing was the only question.
**Reference:** Claude Sonnet 5 senior planning review, job posting requirements
**Impact:** Terraform added in v0.6.0, before v1.0.0 publication

---

**Decision:** FORK_04 — Expand v0.2.0 scope instead of choosing portfolio-first vs roadmap-first.
**Reason:** False choice. Logs are already verified flowing. Grafana provisioning files already exist and are further along than the six-model summary suggested. Fix label-mapping hints first, then wire Grafana and build one logs panel. Converts "verified log pipeline" from an internal checkbox into something a recruiter can see.
**Reference:** Claude Sonnet 5 senior planning review
**Impact:** v0.2.0 grows from 2-3h to 3-4h, includes Grafana + one logs panel + screenshot

---

**Decision:** Use Sloth (open-source) for SLO implementation instead of Grafana Cloud SLO app.
**Reason:** The Grafana SLO app is a Cloud-only capability; our stack is fully self-hosted. Sloth generates burn-rate rules targeting vanilla Prometheus rule format (which Mimir ruler consumes natively). Stronger portfolio signal — shows you can implement the burn-rate math yourself, not just operate someone else's UI.
**Reference:** Claude Sonnet 5 senior planning review, Grafana OSS vs Cloud comparison
**Impact:** v0.5.0 includes Sloth-generated recording rules and multi-window multi-burn-rate alerting rules

---

**Decision:** Metrics pipeline: keep Alloy as collector for everything (matching ADR-001 pattern).
**Reason:** One ingestion path per signal type. Don't have gateway push metrics directly — add MeterProvider + OTLPMetricExporter to instrumentation.py, wire through Alloy's OTLP receiver. Consistent with the log pipeline pattern already working. Better portfolio story: "OTLP end-to-end through a single collector."
**Reference:** Claude Sonnet 5 senior planning review, ADR-001
**Impact:** v0.5.0 fixes OTLP metrics path end-to-end through Alloy

---

**Decision:** OTLP-to-Loki label mapping requires `otelcol.processor.attributes` hint step.
**Reason:** `otelcol.exporter.loki` does NOT convert OTLP resource attributes to Loki labels by default — needs special hint attributes (`loki.resource.labels`, `loki.attribute.labels`). GLM-5.2 was wrong about deprecation but right about the underlying label concern. This blocks v0.2.0 acceptance criteria (`{service="gateway"}` returning data).
**Reference:** Claude Sonnet 5 ecosystem knowledge check, otelcol.exporter.loki documentation
**Impact:** First concrete task for v0.2.0: add processor attributes block to alloy/config.river

---

**Decision:** Accept label naming: `service.name` → `service_name` (not `service`).
**Reason:** otelcol.exporter.loki sanitizes promoted resource attributes to Prometheus label format — dots become underscores. So `service.name` becomes `service_name`, not `service` (ADR-003's naming) and not `job` (the roadmap's original acceptance criterion). Fix docs to match reality rather than add a relabeling step for cosmetic naming.
**Reference:** Claude Sonnet 5 partial output (cap hit mid-delivery), otelcol.exporter.loki documentation
**Impact:** Acceptance criteria updated: `{service_name="gateway"}` instead of `{job="gateway"}` or `{service="gateway"}`. ADR-003 needs update.

---

**Decision:** Fix loki.resource.labels hint — use `value` (key-list string), not `from_attribute` (value copy).
**Reason:** Initial config used `from_attribute = "service.name"` which copies the VALUE of service.name (e.g., "gateway") into a label called `loki.resource.labels`. The otelcol.exporter.loki docs show `value = "service.name,service.namespace"` — a comma-separated string of attribute NAMES to promote. hy3-free model flagged this semantic inversion; confirmed against Grafana docs.
**Reference:** hy3-free analysis, otelcol.exporter.loki documentation examples
**Impact:** Config corrected from `from_attribute` to `value`. Without this fix, `{service_name="gateway"}` would return empty results.

---

**Decision:** Tempo metrics_generator: set `generation_enabled: false` until v0.5.0.
**Reason:** Tempo config references `mimir:9009` for remote_write but Mimir doesn't exist yet. Tempo doesn't crash — it logs and retries (counters like `prometheus_remote_storage_samples_failed_total`). Setting generation_enabled: false avoids a debugging session convinced something's broken when it's just Tempo shouting into a hostname that doesn't resolve.
**Reference:** Claude Sonnet 5 Tempo troubleshooting docs check
**Impact:** v0.3.0 Tempo config has generation_enabled: false, no remote_write block

---

**Decision:** prometheus.scrape "alloy"/"loki" forward_to reverted to [] until v0.5.0.
**Reason:** Both scrape blocks were wired live to prometheus.remote_write.mimir.receiver, but Mimir isn't in docker-compose yet — same failure mode already avoided for Tempo's metrics_generator. Retried, logged push failures against a hostname that doesn't resolve; not a crash, but log noise with no upside before v0.5.0.
**Reference:** Claude Sonnet 5 config.river review, 2026-07-19
**Impact:** forward_to = [] on both scrape blocks; re-enable at v0.5.0

---

**Decision:** deployment.environment vs deployment.environment.name — verify before editing.
**Reason:** deployment.environment is deprecated in current OTel semantic conventions, superseded by deployment.environment.name. ADR-003 and config.river's loki.resource.labels hint both reference the old name. Whether this is actually broken depends on what instrumentation.py's Resource object sets — that's the thing to check, not either doc.
**Reference:** Claude Sonnet 5 ecosystem knowledge check, OpenTelemetry deployment-environment semantic convention
**Impact:** Resolved: instrumentation.py hand-sets literal `"deployment.environment"` (not the semconv package constant). Matches config.river and ADR-003 exactly. No edit needed. Modernizing to `deployment.environment.name` would touch 3 files for cosmetic gain — not worth the effort now.

---

**Decision:** spanmetrics connector placement — version-agnostic, traces-gate.
**Reason:** Claude's corrected analysis: spanmetrics connector taps spans inside Alloy's pipeline. It needs traces flowing (v0.3.0+) but doesn't need Tempo itself running to be configured — same pattern as prometheus.remote_write "mimir" (declared-but-inert since v0.2.0). Its output is metrics with nowhere to go until Mimir exists (v0.5.0). v0.4.0 is specifically scoped to trace-to-log correlation (Loki/Tempo concern), not metrics. So it's a connector definition that belongs whenever traces start flowing, with a forward_to that stays empty until Mimir does.
**Reference:** Claude Sonnet 5 corrected analysis, Alloy pipeline architecture
**Impact:** Config added to alloy/config.river. Output stays empty until v0.5.0. No version number filed under — it's a preparatory step that lives wherever traces are wired.

---

**Decision:** Metric name mismatch — three sources guessed at names before spanmetrics was chosen.
**Reason:** Claude flagged: spanmetrics emits its own metric family (calls counter + duration histogram, namespaced with configurable prefix), not http_requests_total or http_server_request_duration_seconds_count. Three existing files query wrong names: sloth/gateway-slo.yaml (http_server_request_duration_seconds_count), service-health-red.json (http_requests_total, http_request_duration_seconds_bucket), service-health.json (duplicate of first). All need re-pointing once real names are visible via Mimir's label API at v0.5.0.
**Reference:** Claude Sonnet 5 metric name analysis
**Impact:** Known issue flagged. No fix now — real names only visible after v0.5.0 Mimir deploy. Dashboard JSONs and SLO spec will need a pass at that point.

---

**Decision:** Raw spanmetrics names used everywhere — OTTL transform abandoned.
**Reason:** `otelcol.processor.transform` with `set(name, ...) where name == "..."` silently consumed metrics without renaming. Root cause unknown — `error_mode = "propagate"` showed no parse errors for valid syntax, yet metrics disappeared from Mimir query results. Empty `statements = []` passes metrics through; any `set(name,...) with where` causes metrics to vanish. Pipeline now sends raw spanmetrics names (`traces_span_metrics_calls_total`, `traces_span_metrics_duration_milliseconds_bucket`) directly to Mimir; dashboard and SLO updated to match.
**Reference:** Big Pickle diagnostic session, empirical testing with Mimir `/prometheus/api/v1/query`
**Impact:** Dashboard panels and SLO query use raw names. If OTTL transform is fixed in future Alloy version, can revisit renaming.

---

**Decision:** Mimir 2.12.0 config format — all `common.*` sub-blocks except `storage`, `ring`, `instance_limits` are invalid.
**Reason:** `common.path_prefix` and `common.replication_factor` do not exist in Mimir 2.12.0 — causes startup crash. Correct replication_factor lives under `ingester.ring.replication_factor`. Compactor uses `data_dir` (not `working_directory`). `multitenancy_enabled` and `no_auth_tenant` are top-level fields, NOT nested under any `auth:` block. All non-blocks-storage paths (`compactor.data_dir`, `ruler.rule_path`, `ruler_storage.local.directory`, `alertmanager_storage.local.path`) must NOT overlap with `common.storage.filesystem.dir` (`/data`).
**Reference:** Big Pickle diagnostic session, Mimir 2.12.0 documentation
**Impact:** `mimir/mimir.yml` fully restructured; Mimir now starts and returns 200 on `/ready`.

---

**Decision:** Raw Span from start_span() supports context manager protocol.
**Reason:** Empirically verified: `tracer.start_span()` returns a Span object with `__enter__` and `__exit__` methods. The `business_spans.http_call()` pattern in main.py (using `with` on a raw Span) is valid. No code change needed.
**Reference:** Claude Sonnet 5 flagged as concern; empirical test confirmed OK
**Impact:** No change — existing main.py code is correct.

---

**Decision:** Don't create CLAUDE_VISION.md for reasoning capture.
**Reason:** DECISION_LOG.md already has a Reason column. Extend entries there instead of adding a ninth meta-document. The process doc pile is already heavy (11 process files vs 3 running containers).
**Reference:** Claude Sonnet 5 senior planning review
**Impact:** Reasoning captured in DECISION_LOG.md Reason column, not a separate file

---

**Decision:** Keep AI orchestration out of public README.
**Reason:** A hiring manager for a hands-on Grafana role is trying to gauge your judgment. A repo whose docs read like an AI coordination log invites the question of how much of the architecture is yours. Engineering artifacts (dashboards, SLO rules, Terraform, ADRs) carry the signal better. Mention "AI-assisted development" in one line at most.
**Reference:** Claude Sonnet 5 senior planning review
**Impact:** v1.0.0 README focuses on architecture, demo, case studies — not AI model coordination

---

## 2026-07-18

**Decision:** Freeze governance (PROJECT_CONSTITUTION.md v1.0) before any implementation.
**Reason:** Prevent planning loop; establish evidence-first discipline from commit #1.
**Reference:** Architecture Review → Constitution v1.0
**Impact:** All future architectural changes require ADR; implementation changes go to Roadmap.

---

*This log is maintained by Big Pickle (opencode). Major decisions are recorded here; formal ADRs are in `ADR/`.*
