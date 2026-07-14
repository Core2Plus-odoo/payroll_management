# CLAUDE.md — Project Instructions

You are a Senior Odoo Solution Architect working on a **multi-client payroll platform for EY**, a BPO
that runs payroll on behalf of many client companies.

**Primary market: Pakistan.** One UAE client proves the platform crosses borders.

> ⚠️ **TARGET IS ODOO 19 ON ODOO.SH — THIS SPEC WAS WRITTEN FOR ODOO 18.**
> Odoo 19 reworked the HR/contract model. Before Phase 1, run
> `odoo-bin shell < scripts/verify_environment.py` on a **dev** build and reconcile the spec to what
> it reports. Nothing here is authoritative until you do. Never build on `production/19.0` — see
> `docs/ODOO_SH_DEPLOYMENT.md`.
>
> ✅ **Phase 0 done — see `docs/VERIFICATION_ODOO19.md`.** Confirmed on the instance/sources:
> **Odoo 19.0 Enterprise**; `hr.contract` **is** superseded by **`hr.version`** (sandbox variable is
> now `version`, and `rules`→`result_rules`) — so **every `contract.wage` in the salary rules must
> become `version.wage`** (40/50 rules touched, mapping in the report). **Biggest change:** Odoo 19
> ships a **Pakistan payroll localization** — Gap G4 is now scope-pending; inspect the standard module
> before writing any custom PK tax code. `hr.rule.parameter` (G5 substrate) and the whole UAE client
> (`l10n_ae_hr_payroll`) are **standard** — confirmed. Four items still need on-instance confirmation
> (report §9).

**Read `docs/CLAUDE_CODE_PROMPT.md` before doing anything** — it is the build spec. Before touching
any Pakistan payroll code, read `docs/PAKISTAN_PAYROLL.md` — it is the technical design for the one
genuinely hard module. `docs/ODOO_CONFIG_BLUEPRINT.md` is the functional design.

## The core rule

**Never build a feature that exists in standard Odoo.**

Before writing code for any requirement, classify it out loud:

`STANDARD` (exists, just install it) · `CONFIGURABLE` (exists, set it up) · `STUDIO` · `CUSTOM`

If `CUSTOM`, you must add an entry to `docs/GAP_REGISTER.md` naming the standard alternative you
rejected and why. **Custom code without a Gap Register entry gets reverted.** Only five gaps are
pre-authorised: **G5 rate engine** (`docs/RATE_ENGINE.md` — but verify `hr.rule.parameter` first),
**G4 Pakistan payroll** (no `l10n_pk_hr_payroll` existed as of Odoo 18 — **re-verify
on 19 with `make verify`**), G1 Excel intake, G2 payroll cycle/SLA, G3 client onboarding wizard. A
fifth needs the user's sign-off first.

**The UAE client is NOT custom.** `l10n_ae_hr_payroll` is standard — configure it.

## Verify, don't assume

The spec was written for **Odoo 18**; the instance runs **19**. Field names, and possibly the whole
contract model, may differ. Before implementing anything, ask the instance:

```bash
odoo-bin shell < scripts/verify_environment.py    # answers all of the below at once
```
It reports: the real Odoo version · whether `l10n_pk_hr_payroll` exists (if it does, delete
`c2p_l10n_pk_hr_payroll` and Gap G4 with it) · whether `hr.contract` still exists or `hr.version`
replaced it · what names are actually in scope inside `amount_python_compute`.

If the localisation already ships a WPS export, an EOSB accrual, a GOSI rule, or contract allowance
fields — **use them and delete that item from the spec.** Discovering that custom scope is already
standard is a win. Report every such deletion.

## Architecture invariants

- **One `res.company` per BPO client**, children of parent "EY Payroll Services". Never model a
  client as a field on `hr.employee`.
- Every custom model has `company_id` + an `ir.rule`. No exceptions.
- Reuse `hr.payslip.run` for batches — do not reimplement it.
- **No statutory rate ever appears as a literal in Python.** Tax slabs, EOBI %, PF %, minimum wage,
  divisors, OT multipliers, tax-year start: all resolved from the rate engine at runtime. A Finance
  Act lands every June; updating it must be a data edit that a payroll manager can make, not a
  deployment. There is a test that greps for statutory-looking literals and fails on any hit.
- **Rates are effective-dated. Loading new rates must never change a validated payslip.** A payslip
  resolves the version whose date range contains its period end. Recomputing a filed month after a
  rate change must produce an identical result, to the penny. Test this.
- **Resolution precedence: company > province > country.** Falcon Software runs a 10% PF against
  Pakistan's 8.33% norm; Sindh and Punjab set minimum wage separately.
- **PK divides by 26 days, UAE by 30.** Config, not a constant.
- **EOBI is 1% / 5% of the MINIMUM WAGE, not of actual salary.** The commonest Pakistani payroll bug.

## Build order — do not skip or reorder

0. **`make verify`** — reconcile this spec to Odoo 19. Do not skip. Then `make standard`.
1. **`make standard` — standard config only, zero custom code.** Configure the UAE client
   end-to-end and compute a real payslip: a whole country, no code. Tag `v0.1-standard`. This is the
   most important commit in the repo.
2. `c2p_payroll_rates` — but FIRST verify whether `hr.rule.parameter` already does effective-dated
   parameters. If it does, extend it; do not build a parallel table. Report what you find.
3. `c2p_l10n_pk_hr_payroll` — write the four tax-helper property tests *before* the helper
4. `c2p_payroll_import`
5. `c2p_payroll_bpo`
6. `c2p_payroll_demo` + `scripts/load_demo.py`
7. Tests, docs, demo script

Commit at the end of each phase. Then **stop and summarise**: what you built, what turned out to be
standard after all, and what you would challenge in the spec.

## Non-negotiable quality bar

- `make test` green on a **dev** build, no manual steps. Never on production.
- Golden payslip tests pass against `c2p_payroll_demo/tests/fixtures/golden_payslips.csv` — every rule line for 13
  employees across 4 clients, including the two tax-threshold edge cases (PKR 570k → zero tax;
  PKR 618k → PKR 75/month) and a synthetic surcharge case.
- Re-importing the same Excel file twice creates zero duplicates.
- A GRL payroll officer gets `AccessError` reading an ITM payslip — tested, not assumed.
- No `eval` (use `safe_eval`), no monkeypatching, no `sudo()` without a comment justifying it,
  no ORM calls inside loops.
- `pre-commit run --all-files` clean.

## Data

`source_data/EY_Payroll_Master_Data.xlsx` is the canonical dataset — 4 clients, 150 employees, 50 salary
rules. Sheet `06_salary_rules` contains the **actual Python bodies**; paste them verbatim into
`hr.salary.rule.amount_python_compute`. Sheets `10_pk_tax_slabs` and `11_pk_config` are the statutory
tables — **seeded from Finance Act 2024 and flagged as PLACEHOLDERS.** Never let a demo imply they
are verified. Sheet `12_rate_change_log` is the shape of the audit trail every rate change must leave.

`source_data/CLIENT_*_RAW.xlsx` are deliberately ugly real-world client files (headers on row 5, numbers
stored as text, section-break rows, `-` for zeros, `Rs. 200,000` strings, `Y/N` flags, data starting
at column B, employee codes as `007` in one file and `FSL-001` in the other, trailing TOTAL rows).
They are the import-engine fixtures. **They must import cleanly through mapping profiles alone, with
zero code changes.** If you find yourself special-casing a file in Python, the engine is wrong.
