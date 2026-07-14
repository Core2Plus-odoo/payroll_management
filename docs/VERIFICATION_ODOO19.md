# Phase 0 — Odoo 19 Environment Verification & Spec Reconciliation

> **This is the output of build-order step 0 (`make verify`).** The spec in this repo was written for
> **Odoo 18**; the target instance runs **Odoo 19 on Odoo.sh**. Per `CLAUDE.md` and
> `docs/ODOO_SH_DEPLOYMENT.md §3`, nothing in this repo is authoritative until the spec is reconciled
> to what the instance actually reports. This document is that reconciliation. Read it before Phase 1.

- **Instance:** `core2plus-odoo-payroll-management` → <https://core2plus-odoo-payroll-management.odoo.com>
- **Date:** 2026-07-14
- **Author:** Solution Architect (Phase 0)

## How this was verified

`scripts/verify_environment.py` is designed to run in the **Odoo.sh shell of a dev build**
(`odoo-bin shell < scripts/verify_environment.py`). That shell was not reachable from this
environment (no SSH/shell to the Odoo.sh container, no DB login), so the questions the probe answers
were resolved from **authoritative, version-pinned sources** instead, and cross-checked against the
live instance where an unauthenticated endpoint allowed it:

| Method | What it settled |
|---|---|
| Live JSON-RPC `POST /web/webclient/version_info` on the instance | Exact version + edition (no login needed) |
| Odoo 19.0 **community source** (`github.com/odoo/odoo` @ `19.0`) | `hr.version` model, `hr.employee` fields — the contract refactor |
| Odoo 19.0 **official documentation** (`odoo/documentation` @ `19.0`) | Salary-rule sandbox variables; payroll localization country list; rule parameters |

**Confidence legend:** ✅ **CONFIRMED** (authoritative source) · 🟡 **CONFIRM ON INSTANCE** (strongly
indicated; must be re-checked by running `make verify` on the dev build before code depends on it).

---

## 1. Version & edition — ✅ CONFIRMED

Live probe of the instance:

```
POST https://core2plus-odoo-payroll-management.odoo.com/web/webclient/version_info
→ {"server_version": "19.0+e",
   "server_version_info": [19, 0, 0, "final", 0, "e"],
   "server_serie": "19.0", "protocol_version": 1}
```

- **Odoo 19.0**, edition **Enterprise** (the `+e` / trailing `"e"`). D1 is settled: `hr_payroll` and
  the Enterprise localizations (`l10n_ae_hr_payroll`, etc.) are available.
- The spec is therefore **one major version stale**. Odoo 19 reworked the HR/contract data model —
  the single biggest source of drift, addressed in §2.

---

## 2. The contract refactor: `hr.contract` → `hr.version` — ✅ CONFIRMED

**Odoo 19 replaced `hr.contract` with `hr.version`.** This is the exact change the spec warned might
have happened, and it did.

Evidence from Odoo 19.0 community source:

- `addons/hr/models/__init__.py` imports **`hr_version`** and `hr_contract_type` — there is **no
  `hr_contract`** import/model.
- `addons/hr/models/hr_version.py` → `_name = 'hr.version'`, `_description = 'Version'`. It carries
  the former contract payload: `wage`, `contract_wage`, `structure_type_id`, `contract_type_id`,
  `contract_date_start`, `contract_date_end`, `date_version`, `date_start`, `date_end`,
  `trial_date_end`, `departure_date`.
- `addons/hr/models/hr_employee.py`: **no `contract_id` field.** Instead
  `version_id` (Many2one `hr.version`, the current version), `current_version_id`, and
  `contract_wage = fields.Monetary(related="version_id.contract_wage", …)`.

**Consequence:** every `contract.*` reference in every salary rule and in the spec is written against
a model that no longer exists in the payslip sandbox. Reconciled in §5.

---

## 3. Salary-rule sandbox (`amount_python_compute`) — ✅ CONFIRMED (object type 🟡)

Source: official Odoo 19.0 docs, `content/applications/hr/payroll/salaries.rst`, *Python Code /
Available variables*. The sandbox now exposes:

| Odoo 19 variable | Type (per docs) | Odoo 18 equivalent | Change |
|---|---|---|---|
| `payslip` | `hr.payslip` | `payslip` | same |
| `employee` | `hr.employee` | `employee` | same |
| **`version`** | **`hr.version`** | `contract` (`hr.contract`) | **renamed + remodelled** |
| **`result_rules`** | dict `{code: {total, amount, quantity, rate, ytd}}` | `rules` (BrowsableObject) | **renamed; dict-of-dicts** |
| `categories` | dict `{code: summed total}` | `categories` (BrowsableObject) | dict access documented |
| `worked_days` | dict `{wetype: worked_days obj}` | `worked_days` | same shape |
| `inputs` | dict `{code: summed value}` | `inputs` (BrowsableObject) | dict access documented |

Outputs: `result`, `result_rate`, `result_qty`, `result_name`.

- ✅ **`contract` is gone from the sandbox; the variable is now `version`.** `contract.wage` →
  `version.wage`.
- ✅ **`rules` is now `result_rules`**, a dict keyed by rule code whose value is a dict. So
  `rules.HRENT.amount` → `result_rules['HRENT']['amount']`.
- 🟡 **`categories` / `inputs` attribute-vs-subscript.** The docs describe these as *dicts*. In Odoo 18
  they were `BrowsableObject`s that accepted **both** `categories.BASIC` and `categories['BASIC']`.
  Whether attribute access still works in 19 must be confirmed on the instance. Treat `categories['BASIC']`
  and `inputs['OT_H']` (subscript) as the safe form. `inputs['CODE']` is documented as the *summed
  value* (a scalar), so `inputs.OT_H.amount` → `inputs['OT_H']`.

---

## 4. The headline finding: Odoo 19 ships a **Pakistan payroll localization** — ✅ CONFIRMED / 🟡 scope

This is the highest-value thing the verify step exists to find, and the answer flipped between 18 and
19.

Odoo 19.0 official docs, `content/applications/hr/payroll/payroll_localizations.rst`, *List of
countries* ("Payroll localization modules are available for the countries listed below"), lists —
alongside Australia, Belgium, Egypt, India, Jordan, Kenya, Saudi Arabia, UAE, United States, and
others — **Pakistan**.

- ✅ **A Pakistan payroll localization now exists in Odoo 19.** In Odoo 18 it did not (the premise of
  D3 / Gap G4). By the naming convention this is **`l10n_pk_hr_payroll`** (and likely
  `l10n_pk_hr_payroll_account`).
- 🟡 **Unknown without the instance:** what the module actually implements. Pakistan is listed
  *without* a dedicated documentation page (unlike UAE/Saudi/India), which typically means a newer,
  thinner localization. Gap G4 was justified on **two** grounds — (a) "no module exists" *and*
  (b) "s.149 is annualised/cumulative over a July–June year, which a stateless rule cannot express."
  Ground (a) is now **false**. Ground (b) may or may not be handled by the shipped module.

**Action — do this first on the dev build, before writing any PK tax code:**

```bash
# Apps → clear filter → search "Pakistan"; install l10n_pk_hr_payroll (+ _account)
# then inspect what it gives you:
env['ir.module.module'].search([('name','like','l10n_pk')]).mapped('name')
env['hr.salary.rule'].search([('struct_id.country_id.code','=','PK')]).mapped('code')
env['hr.rule.parameter'].search([]).filtered(lambda p: 'pk' in p.code or p.country_id.code=='PK')
```

Then decide, per the CORE RULE ("never build a feature that exists in standard Odoo"):

- If it computes annualised, cumulative s.149 withholding correctly and ships EOBI / PF / SESSI /
  gratuity / OT rules → **delete `c2p_l10n_pk_hr_payroll` and Gap G4.** Configure the standard module.
  Reduce this repo to G1/G2/G3 + the thin G5 scoping layer. That is a large, real win.
- If it ships slabs/EOBI but computes tax **per-period** (not annualised/YTD) → keep only the
  **YTD tax helper** as custom, layered on top of the standard module's data; delete everything the
  module already provides. G4 shrinks dramatically.
- Only if no usable PK tax computation exists does the current G4 scope stand — and even then, build
  **on top of** the localization's structures, not beside them.

Until that inspection runs, `c2p_l10n_pk_hr_payroll` is retained in the tree but must be treated as
**scope-pending**, not approved.

---

## 5. Salary-rule reconciliation (`source_data/EY_Payroll_Master_Data.xlsx`, `06_salary_rules`)

**40 of 50 rule bodies reference sandbox variables that changed in Odoo 19.** The Excel is the
canonical dataset and is pasted verbatim into `hr.salary.rule.amount_python_compute` in Phase 3 — so
these transforms must be applied *as the rules are loaded*, not left to chance. The proof that the
rate engine is layered correctly (ITM `OT2X` and GRL `OT125` being byte-identical Python) survives
the refactor: both still resolve `payslip.rate('monthly_days')` / `payslip.rate('ot_multiplier')`.

### Mechanical transforms (apply to every rule at load time)

| Odoo 18 (as written in the sheet) | Odoo 19 | Confidence | Rules affected |
|---|---|---|---|
| `contract.wage` | `version.wage` | ✅ | 10 — every `BASIC` + the `ABSENT` rules that divide raw wage |
| `rules.HRENT.amount` (and `.MEDICAL`, `.UTIL`) | `result_rules['HRENT']['amount']` … | ✅ | 1 — `SS_FSL_WHITECOLLAR/CONVEY` |
| `categories.BASIC` / `.ALW` / `.GROSS` / `.DED` | `categories['BASIC']` … | 🟡 (attribute may still work) | ~28 |
| `inputs.CODE.amount` | `inputs['CODE']` | 🟡 | ~11 (OT_H, BONUS, ABSENT_D, OTH_DED, SHIFT_ALW, COMM) |
| `inputs.CODE` (as a condition truthiness test) | `inputs.get('CODE')` / `'CODE' in inputs` | 🟡 | conditions on the same ~11 |

`payslip.rate('…')` and `payslip._pk_income_tax()` are **custom** methods added by
`c2p_payroll_rates` / `c2p_l10n_pk_hr_payroll` on the extended `hr.payslip`; they are unaffected by
the core refactor *except* that any code inside the helper that read `contract.wage` must now read
`version.wage` (or `employee.contract_wage`).

### The 10 `contract.wage` rules (fully enumerated)

| Structure / rule | Odoo 18 body | Odoo 19 body |
|---|---|---|
| `SS_ITM_FACTORY/BASIC` | `result = contract.wage` | `result = version.wage` |
| `SS_FSL_WHITECOLLAR/BASIC` | `result = contract.wage * 0.50` | `result = version.wage * 0.50` |
| `SS_FSL_WHITECOLLAR/CONVEY` | `result = contract.wage - categories.BASIC - rules.HRENT.amount - rules.MEDICAL.amount - rules.UTIL.amount` | `result = version.wage - categories['BASIC'] - result_rules['HRENT']['amount'] - result_rules['MEDICAL']['amount'] - result_rules['UTIL']['amount']` |
| `SS_MBS_CALLCENTRE/BASIC` | `result = contract.wage * 0.60` | `result = version.wage * 0.60` |
| `SS_MBS_CALLCENTRE/ABSENT` | `result = -((contract.wage / payslip.rate('monthly_days')) * inputs.ABSENT_D.amount)` | `result = -((version.wage / payslip.rate('monthly_days')) * inputs['ABSENT_D'])` |
| `SS_GRL_RETAIL/BASIC` | `result = contract.wage * 0.60` | `result = version.wage * 0.60` |
| `SS_GRL_RETAIL/HRA` | `result = contract.wage * 0.25` | `result = version.wage * 0.25` |
| `SS_GRL_RETAIL/TRANS` | `result = contract.wage * 0.10` | `result = version.wage * 0.10` |
| `SS_GRL_RETAIL/OTHALW` | `result = contract.wage * 0.05` | `result = version.wage * 0.05` |
| `SS_GRL_RETAIL/ABSENT` | `result = -((contract.wage / payslip.rate('monthly_days')) * inputs.ABSENT_D.amount)` | `result = -((version.wage / payslip.rate('monthly_days')) * inputs['ABSENT_D'])` |

> The source `.xlsx` is left **unmodified** in this Phase-0 commit — it is the canonical Odoo-18-shaped
> input and the golden-payslip fixtures are keyed to it. The transforms above are the authoritative
> mapping to apply during Phase 3 loading (and to encode in the loader), *after* the 🟡 items are
> confirmed on the dev build.

---

## 6. Gap G5 — the rate engine substrate exists — ✅ CONFIRMED (scoping 🟡)

- ✅ **`hr.rule.parameter` / `hr.rule.parameter.value` exist** in Odoo 19 Enterprise `hr_payroll`
  (docs: *Payroll → Configuration → Rule Parameters*; each parameter shows "the code, **when the rule
  is active**, and the parameter value" → effective-dated, country-scoped). Per the Gap Register's own
  "Rejected" row, this **is the storage + effective-dating substrate**: do **not** build a parallel
  dated table. Salary rules must call the standard accessor.
- 🟡 Standard rule parameters are scoped **country-level** only. The four things the register lists as
  genuinely custom for G5 — **(A) company/province scoping** (Falcon's 10% PF vs 8.33% norm; Sindh vs
  Punjab minimum wage), **(B) a validated slab grid**, **(C) governance/audit**, **(D) simulation** —
  are **not** provided by standard and remain the legitimate custom scope. Confirm on the instance that
  parameter *values* cannot be `company_id`-scoped before building (A).

**G5 verdict:** the substrate is standard; `c2p_payroll_rates` shrinks to (A)–(D) as a thin layer over
`hr.rule.parameter`. This still requires the user's sign-off (the "fifth module" clause) — unchanged.

---

## 7. The UAE client is standard — ✅ CONFIRMED

Docs: `payroll_localizations/united_arab_emirates.rst`. `l10n_ae_hr_payroll` +
`l10n_ae_hr_payroll_account` ship:

- **WPS** (Wages Protection System) report with **`.sif`** export aligned to MoHRE guidelines.
- **End of Service (EOS/EOSB)** calculation **and EOS Provision** (accrual) — the register's "EOSB".
- **DEWS** (Daman end-of-service programme).

D4 / the register's "the entire UAE client is not custom" is **confirmed**. Write zero UAE code —
configure. The GRL overtime rule (`OT125`) stays ordinary salary-rule config resolving
`payslip.rate('monthly_days')` / `('ot_multiplier')` from the engine.

---

## 8. Spec deltas applied in this commit

Surgical reconciliation notes were added to the following (originals preserved; this report is the
authority):

- `CLAUDE.md` — verify-step banner updated with the confirmed findings.
- `docs/GAP_REGISTER.md` — G4 marked scope-pending (PK localization exists); G5 substrate confirmed.
- `docs/PAKISTAN_PAYROLL.md` — `hr.contract`→`hr.version` reconciled; PK-localization finding noted.
- `docs/CLAUDE_CODE_PROMPT.md` / `docs/ODOO_SH_DEPLOYMENT.md` — verify results linked.
- `c2p_l10n_pk_hr_payroll/__manifest__.py` — the now-false "no l10n_pk_hr_payroll exists" comment
  corrected.
- `scripts/verify_environment.py` — sandbox token list updated for the Odoo 19 variables.

## 9. Residual items — must be confirmed by running `make verify` on a dev build

Everything below is 🟡 and gated the same way the spec always intended — on the running instance, not
from a document:

1. **`l10n_pk_hr_payroll` contents** — does it compute annualised/cumulative s.149? Ship EOBI (on min
   wage), PF, SESSI/PESSI, gratuity, OT@2×, 26-day divisor? This decides how much of G4 survives (§4).
2. **Sandbox object types** — do `categories` / `inputs` still accept attribute access, or is dict
   subscript now required (§3, §5)?
3. **`hr.rule.parameter` value scoping** — country-only, or can values be company-scoped (§6)?
4. **DB state** (probe §4) — companies under "EY Payroll Services", employee count, and whether **PKR**
   and **AED** are active currencies. Not observable without login.

## 10. Bottom line

- Version/edition: **Odoo 19.0 Enterprise** — confirmed live.
- The contract refactor is **real**: `contract` → `version`, `rules` → `result_rules`. 40/50 rules
  need the mechanical transforms in §5.
- **Biggest change to the plan:** Odoo 19 ships a Pakistan payroll localization. Gap G4's founding
  premise no longer holds — inspect and, most likely, shrink or delete the custom PK module. Finding
  that custom scope is now standard is the win the verify step is for.
- G5 substrate (`hr.rule.parameter`) and the entire UAE client are **standard** — confirmed.
- **Do not start Phase 1 code** until the four §9 items are checked on the dev build.
