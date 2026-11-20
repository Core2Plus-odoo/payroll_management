# AS-IS Audit & Gate-0 — C2P Payroll Platform

> Produced per `docs/erp_pack/START_HERE_PROMPT.md` and the ERP Master Blueprint. **No implementation in
> this task.** Facts are cited from the repo; recommendations and assumptions are marked separately.
> Companion: `docs/C2P_ERP_AUDIT_AND_ARCHITECTURE.md` (architecture/data/roadmap). The pack itself is
> installed read-only under `docs/erp_pack/`.

```
TASK:               AS-IS repository & solution audit (Gate-0), per C2P ERP Blueprint START_HERE
REPOSITORY STATUS:  Odoo 19.0 Enterprise; 5 custom payroll modules built (Phases 0–6); dev-build
                    install in final Odoo-19 compatibility shake-out; make test NOT YET run on a dev build
IMPACT:             Planning only — no code, no schema, no data changed in this task
PLAN:               Deliver AS-IS inventory + architecture findings + Gate-0 decisions + next safe task
IMPLEMENTED:        Nothing (audit). Pack installed under docs/erp_pack/ as reference only
VERIFIED:           scripts/verify_golden.py → 162/162 golden lines PASS (re-run today, no Odoo needed)
RECONCILIATION:     N/A (no transactions in this task)
DECISIONS/BLOCKERS: Scope A vs B (see Gate-0 #1); G4 standard-localization check (#2)
NEXT ACTION:        Finish the Odoo-19 dev-build install of c2p_payroll_rates, then make test (M1→M3)
```

## Project profile (from evidence; else "To confirm")

| Field | Value |
|---|---|
| Client / product | EY Payroll Services — multi-client **payroll BPO** platform |
| Jurisdictions | **Pakistan** (primary) + **UAE** (one client) |
| Industry / verticals | Payroll bureau (textile, software, call-centre, retail demo clients) |
| Existing platform | **Odoo 19.0 Enterprise** on Odoo.sh (`core2plus-odoo-payroll-management`) — ✅ verified |
| Legal entities | Parent "EY Payroll Services" + 4 client companies (PKR×3, AED×1) |
| Roles / scale | EY Payroll Manager, EY Payroll Officer, Client HR, Employee; ~150 employees demo |
| History to migrate | Mid-year **YTD opening balances** (not yet built) — To confirm per real client |
| Module scope | Payroll + statutory rate engine + Excel intake + BPO cycle/onboarding. **Full ERP = To confirm (Gate-0 #1)** |
| Integrations | Client Excel files (in); WPS `.sif` (UAE, standard). Banking/e-invoicing — To confirm |
| Hosting / envs | Odoo.sh: dev → staging → **production/19.0**. Deploy by git push |
| Constraints | FA2024 tax figures are **PLACEHOLDERS**; need gazetted TY2026 + practitioner sign-off |
| Non-negotiables | No statutory literals in code; effective-dated immutability; one company per client; EOBI on min wage |

## AS-IS Capability Inventory (ERP domains)

Marked **Existing / Partial / Missing / Out-of-scope / Unknown**, with code evidence.

| Domain | Status | Evidence / note |
|---|---|---|
| Organization / multi-company | **Existing** | `c2p_payroll_demo/data/res_company_data.xml` — EY parent + 4 client companies |
| Users / roles / security | **Existing** | `c2p_payroll_bpo/security/*` — 4 groups, `ir.rule` company/officer isolation |
| **HR / Payroll** | **Existing (core)** | all 5 modules; `hr`/`hr_payroll` (Enterprise); salary rules, cycle, payslip run |
| — PK statutory tax (s.149, EOBI, PF, SS, gratuity) | **Existing — custom G4** 🔸 | `c2p_l10n_pk_hr_payroll` — *pending standard-localization check* |
| — UAE payroll (WPS, EOSB) | **Existing — standard** | `l10n_ae_hr_payroll` (configure; zero custom) |
| — Statutory rate engine | **Existing — custom G5** | `c2p_payroll_rates` (resolver, slabs, simulate, audit) |
| — Client Excel intake | **Existing — custom G1** | `c2p_payroll_import` (profiles, transforms, idempotent) |
| — Payroll cycle / SLA / onboarding | **Existing — custom G2/G3** | `c2p_payroll_bpo` (lock, cycle, wizard) |
| Finance / Accounting / Tax | **Partial** | payslip→journal via standard `hr_payroll_account`; **no AR/AP/GL work beyond payroll posting** |
| Treasury / banking | **Missing** | not in repo (UAE WPS export is standard payroll, not treasury) |
| Fixed Assets | **Out of scope** | standard Odoo app if ever needed |
| CRM / Sales / Quotations | **Out of scope** | not in repo; standard Odoo apps |
| Procurement / Suppliers | **Out of scope** | not in repo; standard Odoo apps |
| Inventory / Warehouse | **Out of scope** | not in repo; standard Odoo apps |
| Projects / Timesheets | **Out of scope** | not in repo |
| Manufacturing / Quality | **Out of scope** | not in repo |
| Maintenance / Fleet | **Out of scope** | not in repo |
| Service / Helpdesk | **Out of scope** | not in repo |
| POS / E-commerce | **Out of scope** | not in repo |
| Documents / Approvals | **Partial** | structure lock + rate-change approval in payroll; no org-wide DMS |
| Budgeting / Forecasting | **Missing** | rate-change **simulation** exists (payroll only) |
| Dashboards / BI | **Partial** | cycle kanban + SLA; no cross-domain BI |
| Notifications / Automations | **Partial** | `mail.thread` on batches/cycles/configs |
| AI agents / BI | **Out of scope** | none in repo |

**Reading:** the repo is a **deep, mostly-complete payroll vertical**, not a broad ERP. Everything outside
payroll is **Out-of-scope/Missing by design** — and would be **standard Odoo apps** (configure, not build)
if Gate-0 #1 approves expansion.

## Architecture & data-integrity findings (summary; full detail in the architecture doc)

- **Multi-company integrity:** ✅ one `res.company` per client; `ir.rule` isolation; no `client_id` field anti-pattern.
- **Money/tax correctness:** ✅ `float_round`; no statutory literal in Python (grep test); effective-dated
  resolution; **immutability** (filed payslip recomputes identically) — tested in `test_pk_tax`.
- **Document→ledger lineage:** payslip → `hr.payslip.run` → journal entry (standard `hr_payroll_account`).
  🟡 End-to-end posting **not yet exercised on a dev build** (M4).
- **Idempotency:** ✅ import commit upsert; `payroll.monthly.input` unique constraint.
- **Security:** ✅ groups + record rules; 🟡 officer-AccessError acceptance test specified, to run on dev build.
- **No destructive ops:** ✅ posted history never edited; superseded rates archived, not deleted.

## Critical risks

1. 🔸 **G4 duplication risk** — if standard `l10n_pk_hr_payroll` already computes s.149 correctly, the custom
   PK module is partly revert-bait. **Mitigation:** inspect before trusting (M2).
2. 🟡 **`make test` not yet green on a dev build** — "done" is unproven until it is. Golden math is proven
   independently, but Odoo wiring (sandbox `categories.*`, payslip/version API) needs the live run.
3. ❓ **Placeholder statutory data** — must not reach a client as if verified; needs gazetted figures + sign-off.
4. ❓ **Mid-year YTD opening balances** — without them, annualised tax is wrong for a client onboarded mid-year (M6).

## Gate-0 decisions (needed before further build) 🔸

1. **Scope:** **A** = finish & ship the payroll platform (recommended now) vs **B** = expand to full C2P ERP later.
2. **G4:** after inspecting standard `l10n_pk_hr_payroll`, approve keep / shrink-to-YTD-helper / delete of the custom module.
3. **G5 fifth-module sign-off:** confirm `c2p_payroll_rates` as the approved thin layer over `hr.rule.parameter`.
4. **Rate-change approver:** EY manager vs client HR (liability).

## Conditional milestones (dependency-gated, not calendar promises)

- **Gate-0 accepted** → **M1** dev-build install green → **M2** G4 verdict → **M3** `make test` green →
  **M4** `make demo` + compute/post a real GRL (UAE) batch → **M5** tag `v0.1-standard` →
  **M6** opening-balance import → *(B only)* **M7** ERP-domain fit-gaps, standard-first.

## First vertical slice to verify (once M1 passes) — GIVEN/WHEN/THEN

**Slice:** *Compute & post one UAE (GRL) monthly payslip, end to end — the "whole country, no custom code" proof.*
- **GIVEN** the demo data is loaded and GRL's structure is locked,
- **WHEN** a payroll officer runs the GRL cycle for 2026-06 (generate → compute → validate → post),
- **THEN** each GRL payslip matches `golden_payslips.csv` to the penny, a journal entry posts (salary
  expense / payable / EOSB provision), and a Client-HR user sees only GRL while an ITM officer gets `AccessError`.
- **Acceptance evidence:** `make test` output (golden + AccessError tests), and the posted journal entry id.

## Next smallest safe task

Continue the **Odoo-19 dev-build install of `c2p_payroll_rates`** (the current fix loop), module by module,
then run `make test`. No production changes; no scope expansion until Gate-0 #1 is decided.
