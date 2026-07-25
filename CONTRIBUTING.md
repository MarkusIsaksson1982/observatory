# Contributing to Observatory

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Types
| Type | Meaning |
|------|---------|
| `feat` | New feature for a persona |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes nor adds features |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `chore` | Maintenance, tooling, CI |
| `style` | Formatting, no logic change |

### Scopes
| Scope | Area |
|-------|------|
| `apps` | Gateway service |
| `alloy` | Alloy configuration |
| `grafana` | Dashboards, datasources, provisioning |
| `terraform` | IaC for Grafana resources |
| `ansible` | Host bootstrap playbooks |
| `tools` | Load gen, fault injection, screenshots |
| `scripts` | Validation scripts |
| `ci` | GitHub Actions workflows |
| `docs` | Documentation (ADRs, runbooks, portfolio) |
| `adrs` | Architecture Decision Records |

### Examples
```
feat(apps): add OpenTelemetry auto-instrumentation
fix(alloy): correct Loki label cardinality in log pipeline
docs(adr): add ADR-001 Alloy vs OTel Collector
chore(ci): add dashboard JSON schema validation
```

---

## Branch Strategy

```
main                    # Protected; only via PR
```

- `main` always runnable via `docker compose up`
- Feature branches: `feat/<scope>-<description>`, `fix/<scope>-<description>`
- Squash-merge with conventional commit message

---

## Review Gates (Self-Enforced)

| Gate | Check |
|------|-------|
| **Pre-commit** | `make lint` (ruff, hadolint, terraform fmt, yamllint) |
| **Pre-push** | `make validate` (docker-compose config, TF plan, dashboard JSON syntax) |
| **PR merge** | All CI green + architecture decision logged if new ADR needed |

---

## Evidence Density Rule

Every PR must improve at least one:
- Working functionality
- Demonstrable engineering practice
- Documentation quality
- Interview readiness
- Portfolio presentation

If a change doesn't improve any of these, it should be deferred.

---

## Adding New Architecture Decisions

1. Create `ADR/ADR-XXX-title.md` using template below
2. Update `DECISION_LOG.md`
3. Reference in PR description

### ADR Template

```markdown
# ADR-XXX: <Title>

**Status:** Proposed | Accepted | Rejected | Superseded
**Date:** YYYY-MM-DD
**Deciders:** <names>
**Technical Story:** <link to issue/PR>

## Context
What is the issue? What constraints exist?

## Decision
What are we doing?

## Consequences
### Positive
- 

### Negative
- 

### Neutral
- 

## Alternatives Considered
1. <alt 1> — rejected because...
2. <alt 2> — rejected because...

## References
- <links>
```

---

## Code Style

| Language | Tool | Config |
|----------|------|--------|
| Python | `ruff` + `mypy` | `pyproject.toml` |
| Terraform | `terraform fmt` | `.terraformrc` |
| YAML | `yamllint` | `.yamllint.yaml` |
| Dockerfile | `hadolint` | `.hadolint.yaml` |
| JSON | `jq` validation | — |
| Commits | `commitlint` | `.commitlintrc.yaml` |

---

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting.