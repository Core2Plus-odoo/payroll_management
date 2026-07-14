# EY BPO Payroll — Odoo 19 / Odoo.sh

Payroll-as-a-service for a BPO: **four client companies, four salary structures, 150 employees, one
Odoo instance.** Messy client Excel in, statutory-compliant payslips out.

**Primary market: Pakistan.** One UAE client is included to prove the platform crosses borders.

| Client | | HC | Demonstrates |
|---|---|---|---|
| Indus Textile Mills | 🇵🇰 Karachi | 60 | Minimum wage, 26-day divisor, OT @2× (Factories Act), EOBI, SESSI, gratuity. Most workers below the tax threshold → **zero tax**, correctly. |
| Falcon Software | 🇵🇰 Lahore | 30 | The tax showcase — salaries walk **every s.149 slab**. Provident fund, medical-allowance exemption, bonus crossing a slab boundary. |
| Meridian BPO | 🇵🇰 Islamabad | 40 | Shift allowance, commission, PF members and non-members. One agent at PKR 618k annual → **PKR 75/month tax**. |
| Gulf Retail LLC | 🇦🇪 Dubai | 20 | Same engine, different statute: no income tax, no EOBI, EOSB instead. |

## The thesis

Most of what EY needs is **standard Odoo, configured**. Exactly four things are not:

- **`c2p_l10n_pk_hr_payroll`** — Odoo has *no Pakistan payroll localization*. Section 149 tax is
  annualised, progressive and cumulative over a July–June year; the stateless rule engine can't
  express it. This module is the moat. → `docs/PAKISTAN_PAYROLL.md`
- **`c2p_payroll_import`** — reusable, validated, audited Excel intake. Clients send chaos.
- **`c2p_payroll_bpo`** — payroll cycle, SLA control tower, client onboarding wizard.
- **`c2p_payroll_demo`** — the four-client dataset.

Everything else is configured, not coded. Every line of custom code is justified in
`docs/GAP_REGISTER.md`.

## Quick start

Deployment is **git-push driven**: Odoo.sh builds every branch it receives.

```bash
git checkout -b dev/payroll && git push origin dev/payroll   # dev build + its own DB
```

Then, in the Odoo.sh shell **of that dev build**:

```bash
make verify     # FIRST — reconcile the spec to Odoo 19. Do not skip.
make standard   # Phase 1: standard payroll only — zero custom code
make init       # + the four custom modules
make demo       # load 150 employees from source_source_data/*.xlsx
make test       # golden payslips, tax edge cases, import idempotency, access rules
```

> 🚫 **Never push this to `production/19.0`.** Odoo.sh installs whatever it receives. Dev → staging →
> production. See `docs/ODOO_SH_DEPLOYMENT.md`.
>
> ⚠️ **The spec targets Odoo 18; the instance runs 19.** Odoo 19 reworked the HR/contract model. If
> `hr.contract` is gone, every `contract.wage` in every salary rule here is wrong. `make verify`
> tells you. Nothing in this repo is authoritative until it has run.
>
> ⚠️ **Tax slabs and EOBI rates in `source_data/` are PLACEHOLDERS** from Finance Act 2024. Replace
> with gazetted TY2026 figures, signed off by a Pakistani tax practitioner, before any client sees a
> computed number.

## Docs

| | |
|---|---|
| `docs/ODOO_SH_DEPLOYMENT.md` | **Read first** — branch strategy, Odoo.sh layout, the v19 unknowns |
| `docs/PAKISTAN_PAYROLL.md` | The tax engine — design, statute, edge cases |
| `docs/CLAUDE_CODE_PROMPT.md` | Full build spec |
| `docs/ODOO_CONFIG_BLUEPRINT.md` | Functional design + salary rules per client |
| `docs/GAP_REGISTER.md` | Every line of custom code, justified |
| `CLAUDE.md` | Working rules for AI-assisted development here |
