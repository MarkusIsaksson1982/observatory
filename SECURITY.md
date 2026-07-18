# Security Policy

## Supported Versions

This is a portfolio demonstration project, not a production service. Security updates are provided on a best-effort basis for the `main` branch only.

| Version | Supported |
|---------|-----------|
| main    | ✅        |

## Reporting a Vulnerability

If you discover a security vulnerability in this repository, please report it responsibly:

1. **Do not** create a public GitHub issue
2. Email the maintainer directly: **security@observatory.local**
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Response Timeline

| Severity | Target Response |
|----------|-----------------|
| Critical | 48 hours |
| High     | 1 week |
| Medium   | 2 weeks |
| Low      | Best effort |

## Scope

This policy covers the repository code and configuration. It does not cover:

- Upstream dependencies (Docker images, Python packages, Terraform providers)
- Infrastructure where this code might be deployed
- The Grafana Cloud public demo endpoint (managed by Grafana Labs)

## Security-Related Configuration

This repository demonstrates security practices but is not hardened for production:

- Default credentials in docker-compose (`admin/admin`) — **change before any real deployment**
- No TLS termination in local compose
- No network policies or service mesh
- No secret management (uses `.env` files)

See [CONTRIBUTING.md](CONTRIBUTING.md) for development practices.