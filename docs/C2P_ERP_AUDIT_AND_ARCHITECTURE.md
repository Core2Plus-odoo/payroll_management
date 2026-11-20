# C2P ERP — System Audit & Solution Architecture

**Prepared by:** Principal ERP Solution Architect (acting)
**Scope of this document:** the `payroll_management` repository as it exists today.
**Date:** 2026-11-20
**Status legend:** ✅ **VERIFIED** (observed in the repo / on the instance) · 🟡 **PROPOSED** (design, not yet built) · ❓ **ASSUMPTION** · 🔸 **DECISION — needs your approval**

> This responds to the C2P Master ERP Development Directive's "first assignment" (audit + architecture
> + plan, **before** new code). It is deliberately grounded: it documents what is actually here and does
> **not** invent modules or data dictionaries for things the repo does not contain. Per the directive's
> own rules — *Standard First*, *No Fake Completion*, *distinguish core from optional* — the un-built ERP
> domains are named and parked, not fabricated.

---

## 0. The one decision that governs everything 🔸

This repository is a **payroll-only BPO platform** (EY runs payroll for client companies) on **Odoo 19
Enterprise**. The Master Directive describes a **complete enterprise ERP** (CRM, sales, procurement,
inventory, finance, manufacturing, projects, POS, …). These are different programs.

| Option | What it means | Effort | Recommendation |
|---|---|---|---|
| **A. Harden & ship the payroll platform** | Finish the Odoo-19 dev-build install, get `make test` green, validate the standard `l10n_pk_hr_payroll` question (G4), deliver. | Days | ✅ **Recommended now.** The build exists and is ~1 validation pass from done. Finish it before widening. |
| **B. Expand to a full C2P ERP** | Add CRM/sales/procurement/inventory/finance/manufacturing on Odoo, with payroll as one domain. | Months, multi-phase program | Only after A ships, and only for domains C2P actually needs. Most are **standard Odoo apps** (configure, don't build). |

**My recommendation:** lock scope to **A** for the current sprint; treat **B** as a separate program I can
scope on its own once payroll is live. The rest of this document audits **A** and shows how **B** would be
layered Standard-First if you approve it (§6, §10).

---

## 1. Current-system audit ✅

**Platform:** Odoo **19.0 Enterprise** (`19.0+e`), Odoo.sh, instance
`core2plus-odoo-payroll-management`. Confirmed live (`/web/webclient/version_info`) and in
`docs/VERIFICATION_ODOO19.md`.

**Repository:** five custom modules, built Phase 0→6 (git history shows clean per-phase commits):

| Module | Purpose | Gap | State |
|---|---|---|---|
| `c2p_payroll_rates` | Effective-dated, scoped statutory rate engine + tax-slab versions + simulation + audit | G5 | ✅ built |
| `c2p_l10n_pk_hr_payroll` | Annualised s.149 tax helper; PK rates/slabs seeded into the engine | G4 | ✅ built (🔸 see G4 below) |
| `c2p_payroll_import` | Profile-driven, validated, idempotent Excel intake | G1 | ✅ built |
| `c2p_payroll_bpo` | Onboarding wizard, structure lock, monthly cycle, security | G2+G3 | ✅ built |
| `c2p_payroll_demo` | 4 clients, 54 salary rules, loader, golden test | — | ✅ built |

**Verified working (no Odoo runtime needed):**
- ✅ `scripts/verify_golden.py` reproduces **all 162 golden payslip lines to the penny** (incl. PKR 570k→zero
  tax, 618k→PKR 75/mo, 10M+ surcharge). Re-run today: PASS.
- ✅ Import transforms resolve both ugly `CLIENT_*_RAW.xlsx` files.
- ✅ No statutory literals in Python; all modules compile; all XML well-formed.

**In-flight / not yet green:**
- 🟡 **Odoo-19 dev-build install** is being run module-by-module. Four view/field incompatibilities already
  fixed and merged (`res.groups.category_id`, list `editable`, custom search view, form decorations/kanban).
  Install is progressing; **`make test` has not yet been run green on a dev build** — this is the gate to "done".
- 🔸 **G4 open question (highest value):** Odoo 19 now ships a **Pakistan payroll localization**
  (`l10n_pk_hr_payroll`). Until it is installed and inspected on the instance, we don't know how much of
  `c2p_l10n_pk_hr_payroll` it supersedes. `docs/VERIFICATION_ODOO19.md §4, §9` tracks this.

**Audit verdict:** the system is **functionally complete and arithmetically proven**, in the **final
Odoo-19 compatibility shake-out**. It is not yet "done" by the CLAUDE.md quality bar (`make test` green on a
dev build) — honestly, ~1 focused dev-build session away.

---

## 2. ERP capability & gap matrix ✅

Requirements classified per the core rule (`STANDARD` / `CONFIGURABLE` / `CUSTOM`):

| # | Requirement | Verdict | How |
|---|---|---|---|
| R1 | Many isolated client companies | STANDARD | Odoo multi-company (one `res.company` per client under "EY Payroll Services") |
| R2 | Per-client salary structure | CONFIGURABLE | `hr.payroll.structure` (company-scoped) |
| R3 | %/fixed/statutory/shift pay models | CONFIGURABLE | `hr.salary.rule` |
| R4 | Monthly variable inputs | STANDARD | `hr.payslip.input.type` |
| R5 | Payslip PDF, self-service, approvals | STANDARD | core `hr_payroll` |
| R6 | Journals per client | STANDARD | `hr_payroll_account` |
| R7 | **UAE: WPS + EOSB** | STANDARD | `l10n_ae_hr_payroll` (✅ confirmed ships WPS `.sif`, EOS/EOSB, DEWS) |
| R8 | **PK: s.149 tax, EOBI, PF, SS, gratuity** | **CUSTOM G4** 🔸 | `c2p_l10n_pk_hr_payroll` — *scope pending the standard-localization check* |
| R9 | Change statutory rates without a developer | **CUSTOM G5** | `c2p_payroll_rates` over `hr.rule.parameter` substrate |
| R10 | ~50 ugly client Excel files/month | **CUSTOM G1** | `c2p_payroll_import` |
| R11 | Payroll cycle / SLA control tower | **CUSTOM G2** | `c2p_payroll_bpo` |
| R12 | Onboard a client in minutes | **CUSTOM G3** | `c2p_payroll_bpo` wizard |

**Nine of twelve requirements are standard Odoo.** Custom code is confined to the five pre-authorised gaps,
each with a Gap Register entry (`docs/GAP_REGISTER.md`).

---

## 3. Module dependency & integration architecture ✅

```
                 hr, hr_payroll (Enterprise), hr_payroll_account, hr_holidays, l10n_pk, l10n_ae(_hr_payroll)
                                              │ (standard)
                 ┌────────────────────────────┼───────────────────────────────┐
         c2p_payroll_rates (G5)        c2p_payroll_import (G1)                  │
   payslip.rate()/slab_tax()/inp()      payroll.monthly.input ◄── (cycle reads)│
                 │                              │                               │
         c2p_l10n_pk_hr_payroll (G4)            │                               │
      payslip._pk_income_tax()                  │                               │
                 └──────────────┬───────────────┘                              │
                        c2p_payroll_bpo (G2+G3) ──────────────────────────────┘
             client.config (lock) · cycle → hr.payslip.run · onboarding wizard · security
                                 │
                        c2p_payroll_demo  (4 clients, 54 rules, loader, golden test)
```

**Integration touchpoints (verified):** salary rules resolve statutory values only via
`payslip.rate()`/`slab_tax()` (rates module) and `_pk_income_tax()` (PK module); the cycle pulls committed
`payroll.monthly.input` rows (import module) onto payslips of the standard `hr.payslip.run`; onboarding
clones a template client's structure + import profiles.

---

## 4. Data model / field dictionary / ERD ✅ (custom entities)

Custom models (all carry `company_id`/client context and are covered by ACLs; see §8):

- **`payroll.statutory.rate`** — key, value_num/value_char, unit, country_id, province, company_id,
  date_from/to, state. *Resolver:* company>province>country, effective-dated. 1 country → N rates.
- **`payroll.tax.slab.version`** (header) → **`payroll.tax.slab`** (bands: lower/upper/base_tax/rate_on_excess).
  Grid-validated (contiguous, ascending, top open, rate∈[0,1]). 1 version → N bands.
- **`payroll.rate.change`** — immutable audit (who/when/what/effective/approved_by/reason/impact).
- **`payroll.import.profile`** → **`payroll.import.mapping.line`** (source header → target field + transform).
- **`payroll.import.batch`** (mail.thread; draft→parsed→validated→committed|error) → **`payroll.import.line`** (staging).
- **`payroll.monthly.input`** — committed (client, period, emp_code, input_code, value); unique-constrained (idempotency).
- **`payroll.client.config`** — company_id (unique), structure_id, structure_locked + locked_by/on, import_profiles, officers.
- **`payroll.cycle`** (+ **`payroll.cycle.stage`**) — config_id, period, dates, stage, payslip_run_id, SLA.
- **Extensions:** `hr.employee` (+pk_pf_member, pk_cnic, payroll_province), `hr.payslip` (+rate/slab_tax/inp/_pk_income_tax), `res.users` (+assigned_client_ids).

Full field-level dictionary lives in the model source (docstrings) and `docs/RATE_ENGINE.md` /
`docs/PAKISTAN_PAYROLL.md`.

---

## 5. End-to-end process linkage matrix ✅

**Monthly payroll lifecycle (the flow you asked for):**
```
Onboard client (wizard) → company+config+structure+profiles
   → LOCK structure (governance gate; write-guarded)
   → receive client Excel → Import: upload→parse→validate(dry-run)→commit (idempotent) → payroll.monthly.input
   → Cycle: generate → payslip per employee on LOCKED structure, inputs pulled in → compute_sheet
   → Validate → Client Approved → Post (hr.payslip.run → journal entries) → Closed
```
**Rate-change lifecycle:** `draft slab version → simulate (scratch diff, live untouched) → approve (reason+audit) → activate (effective-dated; validated history unchanged)`.
**Immutability guarantee:** a payslip resolves the rate/slab version whose range contains its period end;
loading new rates never alters a filed month (tested in `test_pk_tax` effective-dating).

---

## 6. Standard-vs-custom analysis ✅ / 🟡 (and how a full ERP would layer)

**Already Standard-First here:** multi-company, structures, rules, inputs, batches (`hr.payslip.run`
reused, not reimplemented), journals, PDF, portal, the entire UAE client, and the G5 *storage* substrate
(`hr.rule.parameter`). Custom is confined to genuine gaps.

**If scope B (full ERP) is approved** — these are **standard Odoo apps to configure, not build**: CRM,
Sales, Purchase, Inventory, Accounting, Invoicing, Projects/Timesheets, Expenses, Fixed Assets, POS,
Helpdesk, Documents, Sign, Studio. Custom work would only arise at the same kind of statutory/BPO gaps we
saw here. I would audit each domain's fit before any code.

---

## 7. Development standards & conventions ✅ (in force in this repo)

Odoo-native ORM/views/security; no `eval` (use `safe_eval`); no monkeypatching; no `sudo()` without a
justifying comment; no ORM in loops; **no statutory literal in Python** (grep test enforces); effective-dated
data, never destructive edits to posted history; one module per gap with a Gap Register entry; commit per
phase; `pre-commit` (black/ruff/pylint-odoo) configured. Pure computation kept testable without Odoo
(`verify_golden.py`).

---

## 8. Security, approval & audit framework ✅

- **Groups:** EY Payroll Manager (all clients), EY Payroll Officer (assigned only), Client HR (own company),
  Employee (portal).
- **Record-level isolation:** `ir.rule` on `company_id` / `user.assigned_client_ids` — an officer gets
  `AccessError` on another client's payslip (by rule, not hidden menus). *(Acceptance test specified; to run
  on dev build.)*
- **Approvals/governance:** structure **lock** (manager-only unlock, audited); rate change requires
  reason+approver and writes `payroll.rate.change`.
- **Audit:** import batches are never deleted (mail.thread trail); rate changes logged; posted payslips immutable.

---

## 9. UI/UX & dashboard architecture ✅

Role dashboards via the **cycle kanban** (4 clients × stages, SLA breach in red), rate-engine config menus
(statutory rates, slab versions, simulate, change log), the import batch screen (statusbar flow + exception
list), and the onboarding wizard. Standard Odoo list/form/kanban — no bespoke JS. 🟡 A BPO "command tower"
pivot (cost per client per month) is a quick standard pivot view to add.

---

## 10. Roadmap & milestones

| # | Milestone | Depends on | Status |
|---|---|---|---|
| **M1** | **Dev-build install green** (all 5 modules load on Odoo 19) | current fix loop | 🟡 in progress |
| **M2** | **Resolve G4** — install & inspect standard `l10n_pk_hr_payroll`; delete/shrink custom accordingly | M1 | 🔸 decision |
| **M3** | **`make test` green** (golden, tax properties, EOBI, import idempotency, officer AccessError, no-literals) | M1 | 🟡 pending |
| **M4** | **`make demo`** loads 150 employees; compute a full batch; post to GL | M3 | 🟡 pending |
| **M5** | Tag `v0.1-standard` + UAE end-to-end payslip (the "whole country, no code" proof) | M3 | 🟡 pending |
| **M6** | Staging rehearsal (prod-data copy), mid-year YTD opening-balance import | M4 | 🟡 pending |
| **M7** | *(Scope B only)* ERP domain audits, Standard-First | approval | 🔸 parked |

---

## 11. Testing, reconciliation, migration & deployment strategy ✅ / 🟡

- **Testing:** golden payslips (penny-exact), 4 tax property tests, EOBI-flat, resolver precedence,
  effective-dating/immutability, grid validation, import idempotency, officer AccessError, no-statutory-literals.
  Plus the Odoo-independent `verify_golden.py` as a CI oracle.
- **Reconciliation:** payslip lines → journal entries (`hr_payroll_account`) must tie; golden NET ties to GROSS+DED.
- **Migration:** `scripts/load_demo.py` (idempotent) for demo; **mid-year YTD opening balances must be imported
  before a client goes live mid-tax-year** or annualised tax is wrong (flagged, not yet built — M6).
- **Deployment:** Odoo.sh git-push; **dev → staging → production/19.0**; never build on production; `make test`
  only on dev.

---

## 12. Prioritized backlog (next actions, with acceptance criteria)

1. **Finish M1** — continue the dev-build install; fix each Odoo-19 error. *AC: all 5 modules install clean.*
2. **M2 / G4 decision** — install standard `l10n_pk_hr_payroll`, inspect its tax computation. *AC: documented verdict — keep/shrink/delete `c2p_l10n_pk_hr_payroll`; Gap Register updated.*
3. **M3** — run `make test`. *AC: all tests green on dev, no manual steps.*
4. **M4/M5** — `make demo`, compute+post a GRL (UAE) batch, tag `v0.1-standard`. *AC: a real payslip and journal entry exist.*
5. **M6** — opening-balance import profile. *AC: a mid-year joiner's remaining-month tax is correct.*

---

## Decision register / what needs your approval 🔸

1. **Scope:** A (ship payroll) now vs B (full ERP) later. *Recommend A now.*
2. **G4:** after inspecting the standard PK localization, approve keep/shrink/delete of the custom PK module.
3. **G5 "fifth module" clause:** `c2p_payroll_rates` as a thin layer over `hr.rule.parameter` — the directive's
   sign-off for the rate engine's custom scope (scoping/grid/governance/simulation).
4. **Rate-change approver:** EY manager vs client HR (contractual — determines liability).

## Assumptions ❓

- Tax slabs/EOBI/min-wage are **FA2024 PLACEHOLDERS**; gazetted TY2026 figures + a PK tax practitioner sign-off
  are required before any client sees a number.
- FSL's 10% PF override is future-dated (2026-07-01) to preserve June-2026 immutability (divergence from the raw
  sheet, documented).
