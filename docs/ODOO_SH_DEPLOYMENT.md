# Deploying on Odoo.sh

The target is an Odoo.sh instance: `core2plus-odoo-payroll-management-main-34875662`, running
**Odoo 19 on Ubuntu 24.04**, currently on the **`production/19.0`** branch.

Two consequences, and both matter more than any line of code in this repo.

## 1. Do not build on production

Odoo.sh deploys **every branch you push**. Push this scaffold to `production` and it installs four
untested modules into the live database on the next build.

```bash
# on your LAPTOP, in a clone of the GitHub repo — not in the Odoo.sh shell
git checkout -b dev/payroll
tar -xzf payroll_management_scaffold.tar.gz
cp -r payroll_management/. .
git add -A && git commit -m "Phase 0: scaffold — Odoo 19 / Odoo.sh"
git push origin dev/payroll
```

Odoo.sh picks up the new branch, spins up a **development build with its own database**, and installs
the modules there. Nothing touches production.

Promotion path: `dev/payroll` → merge into a **staging** branch (staging gets a *copy of production
data* — this is where you rehearse the demo and the mid-year cutover) → only then merge to
`production`.

> The tarball is on your laptop. The Odoo.sh shell is a different machine, which is why `tar` said
> "No such file or directory". You never need to upload it there — Odoo.sh pulls from GitHub.

## 2. Odoo.sh layout differs from a local install

| | Local docker | **Odoo.sh** |
|---|---|---|
| Addons path | you set it | **the repository root** — modules must be top-level directories |
| Python deps | you `pip install` | **`requirements.txt` at the repo root**, installed at build time |
| Runtime config | `odoo.conf` | managed by Odoo.sh — no `odoo.conf`, no `docker-compose.yml` |
| Deploy | `docker compose up` | **`git push`** |
| Edition | you choose | **Enterprise** — so `hr_payroll` is available. That question is settled. |

This repo is laid out accordingly: the four modules sit at the root, `requirements.txt` declares
`openpyxl`, and there is no docker-compose or odoo.conf. `source_data/` and `docs/` have no
`__manifest__.py`, so Odoo ignores them.

## 3. Verify before writing code — the spec targets Odoo 18

> ✅ **Phase 0 verification is done — results in `docs/VERIFICATION_ODOO19.md`.** Headlines: Odoo
> **19.0 Enterprise** (live-confirmed); `hr.contract` → **`hr.version`** (sandbox variable `version`,
> `rules`→`result_rules`); **Odoo 19 now ships a Pakistan payroll localization** (Gap G4 scope-pending);
> `hr.rule.parameter` (G5) and `l10n_ae_hr_payroll` (UAE) are standard. The steps below are retained as
> the definition of the verify step; four residual items still need the on-instance shell run (report §9).

`docs/CLAUDE_CODE_PROMPT.md`, `docs/ODOO_CONFIG_BLUEPRINT.md` and `docs/PAKISTAN_PAYROLL.md` were
written against **Odoo 18**. You are on **19**. Odoo 19 reworked the HR/contract data model, and if
`hr.contract` has been superseded (by an employee-version model), then **every `contract.wage` in
every salary rule in this repo is wrong** — which is most of the salary rules.

Do not guess, and do not let Claude Code guess. Run:

```bash
odoo-bin shell < scripts/verify_environment.py
```

It reports, from the running instance:

1. Exact Odoo version and addons path (confirms Enterprise).
2. Whether **`l10n_pk_hr_payroll` exists**. If it does, `c2p_l10n_pk_hr_payroll` is deleted and Gap
   G4 disappears. That is the single highest-value thing to find out.
3. Whether **`hr.contract` still exists**, or whether `hr.version` has replaced it — and dumps the
   wage/structure/date fields either way.
4. What names are actually in scope inside `amount_python_compute` (`categories`, `rules`, `inputs`,
   `payslip`, `worked_days`) — the rule bodies in `source_data/EY_Payroll_Master_Data.xlsx` assume the
   Odoo 18 sandbox.
5. The current state of the production DB — companies, employees, whether PKR and AED are active.

**Paste the output into the chat before Phase 1 starts.** Every rule body, and the whole Pakistan
module, gets rewritten against what it says. Nothing in this repo is authoritative until it does.

## 4. Sequence

1. Push the scaffold to `dev/payroll`. Confirm the build goes green (it will: the modules are
   manifests only, no code yet).
2. Run `scripts/verify_environment.py` on the dev build.
3. Reconcile the spec to Odoo 19 based on that output.
4. Then, and only then, Phase 1 — standard configuration, zero custom code.
