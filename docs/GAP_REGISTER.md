# Gap Register

Every custom model in this repo appears here. No entry → the code gets reverted.

> 🏗️ **Build status (Phases 2–6 implemented).** `c2p_payroll_rates` (G5), `c2p_l10n_pk_hr_payroll`
> (G4), `c2p_payroll_import` (G1), `c2p_payroll_bpo` (G2+G3) and `c2p_payroll_demo` are built. The
> statutory arithmetic is proven by `scripts/verify_golden.py` (162/162 golden lines to the penny, no
> Odoo needed). The Odoo module wiring still needs one `make init && make test` pass on an Odoo.sh dev
> build — see the two residual items in `docs/VERIFICATION_ODOO19.md §9` (the `categories.*` sandbox
> object type, and whether the standard `l10n_pk_hr_payroll` supersedes G4).

> ⚠️ **Reconciled to Odoo 19 — see `docs/VERIFICATION_ODOO19.md`.** Two verdicts below changed since
> this was written for Odoo 18:
> - **G4** — Odoo 19 now ships a **Pakistan payroll localization** (`l10n_pk_hr_payroll`). G4's
>   founding premise ("it does not exist") is **false on 19**. G4 is **SCOPE-PENDING**: install and
>   inspect the standard module on a dev build before building any custom PK tax code; most likely G4
>   shrinks to a YTD tax helper or is deleted entirely.
> - **G5** — `hr.rule.parameter` (effective-dated, country-scoped) is **confirmed to exist** in Odoo
>   19 Enterprise. It **is** the storage substrate; the custom scope shrinks to scoping / grid UI /
>   governance / simulation, as this register already anticipated.

| ID | Requirement | Standard option considered | Why it fails | Verdict | Module |
|----|---|---|---|---|---|
| **G4** | **Pakistan payroll: s.149 income tax, EOBI, PF, social security, gratuity** | `l10n_pk_hr_payroll` | ⚠ **RECONCILED ON 19 — premise no longer holds.** On Odoo **18** this did not exist. On Odoo **19** it **does** (official docs list Pakistan as a shipped payroll localization). The *second* reason still stands independently: s.149 tax is *annualised, progressive and cumulative over a July–June fiscal year*, which a stateless per-period rule cannot express without a YTD-aware helper — **but only if the shipped module doesn't already do it.** | **SCOPE-PENDING** — install & inspect `l10n_pk_hr_payroll` on a dev build first (`VERIFICATION_ODOO19.md §4`); most likely shrinks to a YTD helper or is deleted | `c2p_l10n_pk_hr_payroll` |
| **G5** | **Change tax slabs / statutory rates without a developer — scoped, dated, approved, simulated** | `hr.rule.parameter` + `hr.rule.parameter.value` (Odoo Enterprise `hr_payroll`) | ✅ **CONFIRMED ON 19 — it exists** and provides effective-dated, country-scoped parameters (`VERIFICATION_ODOO19.md §6`), so it IS the storage substrate — salary rules call the standard accessor, no parallel table. It still leaves four gaps: (A) no company/province scoping, and a BPO needs per-client overrides (Falcon runs 10% PF vs the 8.33% norm); (B) values are opaque blobs, not an editable, validated slab grid; (C) no approver, reason, or audit of who changed a rate; (D) no simulation — you cannot model a Finance Act before committing it. | **CUSTOM — thin layer over standard.** Exercising the "a fifth module needs sign-off" clause: **please confirm.** | `c2p_payroll_rates` |
| G1 | Ingest ~50 client Excel files/month in ~50 different layouts, validated and audited | `base_import` | Manual column mapping per file, per run. No reusable profile, no dry-run, no staging, no error report, no audit, no idempotency. Unusable at bureau volume. | **CUSTOM** | `c2p_payroll_import` |
| G2 | Track where each client's payroll sits in EY's process, who owns it, whether it's late | `hr.payslip` state; project tasks | Payslip state tracks the *document*, not the *service*. A bureau's product is the control tower across clients. Tasks give no payroll context and no SLA maths. | **CUSTOM** (thin — 1 model + views; reuses `hr.payslip.run`) | `c2p_payroll_bpo` |
| G3 | Stand up a new client (company, CoA, journals, schedules, structure, rules, import profiles) in minutes | Manual configuration | ~2 days of clicking per client, error-prone; the margin killer for a bureau. Wizard clones from a template client and creates *standard* records only. | **CUSTOM** (wizard only) | `c2p_payroll_bpo` |

## Explicitly NOT custom — configure these, do not code them

Salary structures · salary rules · rule categories · payslip input types · work entry types · leave
types · payslip batches (`hr.payslip.run`) · journal entries (`hr_payroll_account`) · payslip PDF ·
employee self-service portal · multi-company isolation · contract management · employee onboarding
(`hr_contract_salary` + `sign`) · **the entire UAE client** (`l10n_ae_hr_payroll` — WPS, EOSB).

Within G4, only the **tax helper** is custom — the slab and rate *tables* belong to G5, and the
Pakistani allowance splits, EOBI, PF, gratuity and overtime rules are ordinary `hr.salary.rule`
configuration. Build them that way.

Within G5, only **scoping, the grid UI, governance and simulation** are custom. If standard rule
parameters exist, effective dating and storage are NOT. The Pakistani allowance
splits, EOBI, PF, gratuity and overtime rules are ordinary `hr.salary.rule` configuration and must be
built that way.

## Rejected

| Idea | Why |
|---|---|
| Hard-code tax slabs / EOBI rates in salary-rule Python | A Finance Act lands every June. Rates live in the rate engine so an update is a data edit, not a deployment. A test greps the addons for statutory-looking literals and fails if it finds any. |
| Build a parallel rate table if `hr.rule.parameter` exists | Standard would already give effective dating and the runtime accessor. Extend it; don't replace it. |
| Let a rate edit alter a validated payslip | Effective dating makes history immutable. A test recomputes a filed payslip after a rate change and asserts it is identical to the penny. |
| Custom `payslip` model | `hr.payslip` is fine. Extend, never replace. |
| `client_id` field on `hr.employee` instead of multi-company | Breaks accounting, sequences, and record-level security. See blueprint §2. |
| Compute tax per-period without YTD | Wrong by construction the moment anyone gets a bonus or a raise. |
