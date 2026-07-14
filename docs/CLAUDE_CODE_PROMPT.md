# Claude Code Build Prompt — EY BPO Payroll Platform on Odoo 19 / Odoo.sh

> 🚨 **STOP. This spec was written for Odoo 18. The instance runs Odoo 19 on Odoo.sh.**
> Odoo 19 reworked the HR/contract data model. Your **first action** is
> `odoo-bin shell < scripts/verify_environment.py` on a **dev** build, then reconcile every
> `contract.wage`, every model name and every rule body in this document to what it reports.
> Do not write code against this spec until you have. Never build on `production/19.0`.

> Paste everything below the line into Claude Code at the repo root. Read it fully before writing a
> single file. `CLAUDE.md` carries the rules that apply to every change; this is the spec.

---

## ROLE

You are a Senior Odoo Solution Architect + Developer building a **payroll-as-a-service platform for
EY**, a BPO that runs payroll *on behalf of* many client companies. **Pakistan is the primary
market**; one UAE client proves the platform crosses borders.

**CORE RULE:** never build a feature that exists in standard Odoo. Classify every requirement as
`STANDARD` / `CONFIGURABLE` / `STUDIO` / `CUSTOM` before you touch it. `CUSTOM` requires an entry in
`docs/GAP_REGISTER.md` naming the standard alternative you rejected and why.

## DECISIONS ALREADY MADE

| # | Decision | Why |
|---|---|---|
| D1 | **Odoo 19 Enterprise on Odoo.sh** | Settled — Odoo.sh is Enterprise, so `hr_payroll` is available. Deploy by `git push`; modules live at the **repo root**; Python deps go in root `requirements.txt`. No docker, no `odoo.conf`. |
| D2 | **One `res.company` per client**, children of "EY Payroll Services" | Per-client structures, journals, sequences, numbering, and record-level isolation, free. Odoo licenses per *user*, not per company. Never model a client as a field on `hr.employee`. |
| D3 | **Pakistan payroll is genuinely custom** — Odoo has no `l10n_pk_hr_payroll` | The one substantial build. Read `docs/PAKISTAN_PAYROLL.md` before writing any of it. |
| D4 | **The UAE client is not custom** — `l10n_ae_hr_payroll` is standard | Configure it. Do not write UAE code. |
| D5 | **Five** custom modules | `c2p_payroll_rates`, `c2p_l10n_pk_hr_payroll`, `c2p_payroll_import`, `c2p_payroll_bpo`, `c2p_payroll_demo`. A sixth needs the user's sign-off. |
| D6 | **No statutory number is ever a literal in Python** | A Finance Act lands every June; provincial minimum wages move on their own schedule; a client can switch its PF scheme by board resolution. Every rate resolves at runtime from the rate engine — see `docs/RATE_ENGINE.md`. There is a test that greps the addons for statutory-looking literals and fails on any hit. |
| D7 | **Rates are effective-dated; history is immutable** | A payslip resolves the rate version whose date range contains its period end. Loading TY2027 slabs must not alter a validated TY2026 payslip — recompute it and it must come back identical to the penny. |

## VERIFY BEFORE YOU TRUST ME

> ✅ **Phase 0 verification is complete — read `docs/VERIFICATION_ODOO19.md` first.** It reconciles this
> spec to Odoo 19: `contract.wage`→`version.wage` (40/50 rules), the Pakistan localization now exists
> (G4 scope-pending), `hr.rule.parameter` (G5) + the UAE client are standard. The paragraph below is
> retained as the rationale for the verify step.

This spec was written from memory and may be stale. Before implementing, read the installed source:

```bash
odoo-bin shell < scripts/verify_environment.py
```

It reports, from the running instance: the real version · **whether `l10n_pk_hr_payroll` exists** (if
so, delete `c2p_l10n_pk_hr_payroll` and Gap G4 with it — the highest-value thing you can discover) ·
**whether `hr.contract` still exists or `hr.version` replaced it** · what names are actually in scope
inside `amount_python_compute` · the current state of the DB.

If something I called custom turns out to ship with Odoo, **use the standard version and delete my
spec for it.** Report every such deletion — finding that custom scope is already standard is a win.

---

## THE FOUR CLIENTS

Data: `source_data/EY_Payroll_Master_Data.xlsx` (150 employees, 50 salary rules, sheet `06_salary_rules`
holds the actual Python bodies — paste them verbatim).

| Code | Client | | HC | Structure demonstrates |
|---|---|---|---|---|
| ITM | Indus Textile Mills | 🇵🇰 Karachi | 60 | Min wage, 26-day divisor, OT @2×, EOBI, SESSI, gratuity. Most below the tax threshold → **zero tax, correctly**. |
| FSL | Falcon Software | 🇵🇰 Lahore | 30 | Salaries walk **every s.149 slab**. PF, medical exemption, bonus crossing a boundary. |
| MBS | Meridian BPO | 🇵🇰 Islamabad | 40 | Shift allowance, commission, PF members vs non-members. One agent at PKR 618k/yr → **PKR 75/month tax**. |
| GRL | Gulf Retail LLC | 🇦🇪 Dubai | 20 | No income tax, no EOBI, EOSB instead. Same engine, different statute. |

## THE GAPS

**G5 — The rate engine. ⚠ Verify standard first, this is not a free pass.**
EY must change a tax slab, a minimum wage, an EOBI rate or a PF percentage *themselves* — no
developer, no deployment. **Before designing anything, check whether Odoo already does this:**

```bash
grep -rn "rule_parameter\|rule\.parameter" ~/src/odoo/addons/hr_payroll/models/
grep -rn "rule_parameter" ~/src/odoo/addons/l10n_*_hr_payroll/
```

I believe `hr.rule.parameter` / `hr.rule.parameter.value` exists and gives effective-dated,
country-scoped parameters (the Belgian and Indian localizations appear to use it for bracket tables).
**I could not verify it. If it exists, it is the storage substrate — extend it, do not build a
parallel table**, and the custom work shrinks to what standard genuinely doesn't do:

- **Scoping** — `company > province > country` precedence. Falcon runs 10% PF vs Pakistan's 8.33%;
  Sindh and Punjab set minimum wage separately.
- **Structure** — an editable, *validated* slab grid, not an opaque text blob. Reject overlapping
  bands, gaps, descending bands, a rate of `3.5` where `0.35` was meant. At save time.
- **Governance** — approver, reason, effective date, measured impact, audit log
  (sheet `12_rate_change_log` is the shape).
- **Simulation** — `draft → simulate → approve → activate`. Recompute the period into a *scratch* set
  under draft rates and diff it. Live payslips untouched. On Pakistan's budget day EY loads the
  proposed slabs in the morning and tells every client what it costs them by lunchtime. **That is a
  billable product and it falls out of the architecture for free.**

**Read `docs/RATE_ENGINE.md` in full before touching this.** Report what you find about
`hr.rule.parameter` *before* you design.

**G4 — Pakistan payroll.** No `l10n_pk_hr_payroll` exists. s.149 tax is annualised, progressive and
cumulative over a **1 July – 30 June** year: a stateless salary rule cannot compute it. Needs a
YTD-aware helper plus `pk.tax.slab` / config-parameter tables.
→ **Read `docs/PAKISTAN_PAYROLL.md` in full. It is the technical design; this prompt does not repeat it.**
Only the **tax helper** is custom. The slab and rate tables belong to G5. The allowance splits, EOBI,
PF, gratuity and overtime are ordinary salary-rule *configuration* — and every one of them resolves
its rates through `payslip.rate('key')`, never a literal.

The proof the layering is right: **the ITM (Pakistan) and GRL (UAE) overtime rules are byte-identical
Python.** 26-day/2× vs 30-day/1.25× lives entirely in data. If your rules don't come out that way,
something is hard-coded that shouldn't be.

**G1 — Client Excel intake.** `base_import` needs a human to hand-map columns per file, per run, with
no validation, staging, audit or idempotency. A bureau receives ~50 differently-shaped files a month.

Models: `payroll.import.profile` (per client × doc type: sheet name, header row, mapping lines) ·
`payroll.import.mapping.line` (source header → target field, transform: `strip|date_dmy|
number_from_text|clean_iban|yn_to_bool|strip_currency_prefix|constant|python`, the last via
`safe_eval`, never `eval`) · `payroll.import.batch` (`draft → parsed → validated → committed | error`,
`mail.thread`) · `payroll.import.line` (staging: raw JSON, resolved values, per-row errors).

Flow: **Upload → Parse → Validate (dry-run, writes nothing) → Review exceptions → Commit.**
Commit is an idempotent upsert on external ID keyed by `emp_code`, in a savepoint; any failure rolls
the batch back and names the failing row. Never delete a batch — it is the audit trail.

*Acceptance:* `source_data/CLIENT_ITM_Attendance_RAW.xlsx` (headers on row 5, "— section break —" rows,
`-` for zeros, `1,500` as text, employee code `007` not `ITM-007`, trailing TOTAL and notes) and
`source_data/CLIENT_FSL_PayrollInput_RAW.xlsx` (data starts at column B, `Rs. 200,000` strings, `Y/N` flags,
spaced IBANs, full `FSL-001` codes) both import cleanly **through mapping profiles alone, with zero
code changes.** If you special-case a file in Python, the engine is wrong.

**G2 — Payroll cycle / SLA.** `payroll.cycle`: one per client per period. Stages `Data Collection →
Data Received → Validated → Payslips Computed → Client Review → Client Approved → Paid → Posted →
Closed`. Links to the standard `hr.payslip.run` — do **not** reimplement batches. Kanban across all
clients, SLA breach in red, pivot of cost per client per month.

**G3 — Client onboarding wizard.** Clones a template client → company, CoA, journals, schedules,
structure, rules, import profiles, first cycle. Creates *standard* records only.

**Security groups:** EY Payroll Manager (all companies) · EY Payroll Officer (only companies in
`user.assigned_client_ids`, enforced by `ir.rule`, not by hiding menus) · Client HR (own company,
read + approve) · Employee (portal, own payslips).

## BUILD PHASES — do not skip or reorder

**Phase 0 — Verify.** Push to `dev/payroll`. Run `make verify`. **Reconcile this entire spec to Odoo
19 and report every change** before writing a line of code. Then `make standard` and confirm a stock
payslip computes. Commit.

**Phase 1 — Standard configuration, zero custom code.** Companies, currencies (PKR/AED), CoA,
salary journals, working schedules (PK 48h/6-day), work entry types, leave types, structure types,
input types, employees, contracts. Configure the **UAE client end-to-end** and compute a real GRL
payslip. Tag `v0.1-standard`. **This commit is the proof that most of the ask needs no development.
It is the most important commit in the repo.**

**Phase 2 — `c2p_payroll_rates`.** Verify `hr.rule.parameter` first and report. Then: resolver with
scoping precedence, slab grid + validation, effective dating, draft/simulate/approve/activate, audit.
Write the immutability test *before* the resolver.

**Phase 3 — `c2p_l10n_pk_hr_payroll`.** Tax helper + PK salary rules, all rates resolved. Write the
four tax-helper property tests *before* the helper (see `PAKISTAN_PAYROLL.md` §4).

**Phase 4 — `c2p_payroll_import`.** Build against the two RAW files as fixtures. Add profiles for
`tax_slab` and `statutory_rate` so EY loads a new Finance Act from a spreadsheet, dry-run and all.

**Phase 5 — `c2p_payroll_bpo`.** Cycle, dashboard, wizard, security.

**Phase 6 — `c2p_payroll_demo`** + loader (idempotent: run twice, same result).

**Phase 7 — Tests, docs, demo script.**

Commit per phase. Then **stop and summarise**: what you built, what turned out to be standard after
all, what you'd challenge in this spec.

## DEFINITION OF DONE

- [ ] `make init && make test` green from a clean clone, no manual steps.
- [ ] **Golden payslip tests** — `c2p_payroll_demo/tests/fixtures/golden_payslips.csv` holds the expected value of
      every rule line for 13 employees across 4 clients. Assert exactly. These catch silent rule
      regressions, the one bug that actually kills a payroll bureau.
- [ ] **Tax edge cases, each its own test:** ITM min-wage worker (PKR 570k/yr → **zero** tax) ·
      MBS agent at 618k/yr (**PKR 75/month** — just over the threshold) · FSL at 750k/month (top
      slab) · synthetic PKR 1m/month (**surcharge** applies) · every slab boundary ±1 rupee.
- [ ] **Tax helper properties:** stable salary → 12 equal deductions summing to the annual liability ·
      mid-year bonus → later months absorb it, year total ties out · mid-year joiner → annualised
      over remaining months only · never negative.
- [ ] **EOBI is 1%/5% of the *minimum wage*, not of actual salary** — a test asserts PKR 370 / 1,850
      flat for a worker on 37,000 *and* one on 750,000. (This is the commonest Pakistani payroll bug.)
- [ ] Import the same file twice → zero duplicates.
- [ ] A GRL payroll officer gets `AccessError` reading an ITM payslip.
- [ ] `docs/GAP_REGISTER.md` current · `docs/DEMO_SCRIPT.md` written · `pre-commit` clean.
- [ ] No `eval`, no monkeypatching, no `sudo()` without a justifying comment, no ORM in loops.
- [ ] **No statutory rate appears as a literal anywhere in Python.**

## THE 12-MINUTE DEMO (build toward this — it is the actual deliverable)

1. **The pain** — open `CLIENT_ITM_Attendance_RAW.xlsx`. Section breaks, dashes for zeros, text
   numbers, a TOTAL row. "This is what your clients send. Today someone retypes it."
2. **Import** — pick the ITM profile, dry-run, 2 exceptions caught (the worker who left on 15 June),
   commit. 60 workers in 30 seconds, fully audited.
3. **Zero tax, correctly** — a loom operator on PKR 37,000. Annual 570k, under the threshold. The
   system deducts EOBI 370 and no tax. Being right about *nothing* is the hard part.
4. **Every slab** — Falcon: an engineer on 90k, a lead on 200k, a director on 750k. One structure,
   three different effective rates, computed automatically. Show the medical-allowance exemption
   reducing taxable income.
5. **The threshold** — the Meridian agent at PKR 618,000/year. PKR 75/month. "Your spreadsheet
   rounds this to zero. Ours doesn't."
6. **The bonus problem** — add a bonus to an FSL employee, recompute: the system re-annualises and
   trues up. *No spreadsheet does this.*
7. **Budget day** — open the TY2027 draft slabs. Hit **Simulate**. In seconds: *"Falcon Software, 30
   employees, net pay +1.8%, 4 crossing a slab boundary, employer cost −PKR 96,000."* Nothing live
   has moved. Approve it, and it activates on 1 July — **last month's payslips are untouched.**
   Then show `12_rate_change_log`: who changed what, when, on whose authority, and what it cost.
   *"When the Finance Act lands in June, you'll have this out to every client before lunch."*
8. **Cross-border** — the same platform runs Gulf Retail in Dubai. No income tax, no EOBI, EOSB
   accrual. "When your client opens in Dubai, you don't buy another system."
9. **Control tower** — the cycle kanban: 4 clients, 4 stages, 1 SLA breach in red.
10. **Client self-service** — log in as Client HR: sees only their company, approves.
11. **Accounting** — post the batch: salary expense, EOBI payable, tax payable, gratuity provision.
12. **Onboard client #5 live**, from the wizard, in under 3 minutes.
