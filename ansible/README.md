# Ansible — Observatory host bootstrap

This is intentionally small. Portfolio signal: inventory, group_vars, Jinja templating, tagged plays, FQCN `ansible.builtin.*`, idempotent apt/service.

**What it does:**
- `provision` tag: ensures Docker + compose plugin on Debian/Ubuntu (needs `become`)
- `config` tag: templates `.env` from `group_vars/all.yml` per environment (`local` / `staging` / `prod`)

**What it does NOT do:**
- No fleet, no Grafana resource management (Terraform does that — `terraform plan` stays 0/0/0)
- No overwriting of `docker-compose.yml`, `alloy/config.river`, dashboards

**Usage:**

```bash
cd ansible

# Local dev — just templating, no sudo
ansible-playbook -i inventory.ini playbook.yml --tags config
cat ../.env

# Staging env
ansible-playbook -i inventory.ini playbook.yml --tags config -e env_name=staging

# Full host provision (Debian host, needs sudo)
ansible-playbook -i inventory.ini playbook.yml --tags provision -K
```

**Verify:**
- `ls -l ../.env` exists, mode 0600
- `docker compose config --quiet` passes
- `make validate` still passes
- `terraform -chdir=../terraform plan` still 0 to add / 0 to change / 0 to destroy
