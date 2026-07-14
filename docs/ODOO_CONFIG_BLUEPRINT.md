# EY BPO Payroll — Odoo Configuration Blueprint
### Standard first. Custom only where standard genuinely stops.

Primary market **Pakistan**; one UAE client proves multi-country.
The Pakistan tax engine has its own document: `docs/PAKISTAN_PAYROLL.md`.

---

## 1. Requirement breakdown

| # | Requirement | Verdict |
|---|---|---|
| R1 | Payroll for many unrelated client companies, isolated from each other | **STANDARD** — multi-company |
| R2 | Different salary structure per client | **STANDARD** — `hr.payroll.structure` is company-scoped |
| R3 | %-based, fixed-allowance, statutory and shift/commission pay models | **CONFIGURABLE** — salary rules |
| R4 | Monthly variable inputs (OT, bonus, commission, deductions) | **STANDARD** — `hr.payslip.input.type` |
| R5 | Leave / absence feeding payroll | **STANDARD** — `hr_holidays` + work entries |
| R6 | Payslip PDF, employee self-service, approvals | **STANDARD** |
| R7 | Journal entries per client | **STANDARD** — `hr_payroll_account` |
| R8 | Employee onboarding: offer → contract → docs → first payslip | **STANDARD** — `hr_contract_salary`, `sign` |
| R9 | **UAE**: WPS, EOSB | **STANDARD** — `l10n_ae_hr_payroll` |
| R10 | **Pakistan**: s.149 income tax, EOBI, PF, social security, gratuity | **CUSTOM — Gap G4. No Odoo localization exists.** |
| R11 | Ingest ~50 client Excel files/month in ~50 layouts, validated and audited | **CUSTOM — Gap G1** |
| R12 | Track where each client's payroll sits in EY's process, with SLA | **CUSTOM — Gap G2** |
| R13 | Stand up a new client in minutes, not days | **CUSTOM — Gap G3** |

Nine of thirteen are standard. **The message to EY: you are not buying a build, you are buying a
configuration — plus a Pakistan tax engine that nobody else has.**

## 2. Why one company per client (and not a `client_id` field)

| | Multi-company (chosen) | Single company + client field |
|---|---|---|
| Data isolation | `ir.rule` on `company_id`, free | Hand-written rules on every model, leak-prone |
| Separate CoA / journals / sequences | Native | Impossible |
| Payslip numbering per client | Native | Custom sequence per record |
| Client HR sees only own staff | Native | Custom |
| PKR and AED side by side | Native | Painful |
| Cost | Odoo licenses per **user** | — |

The shortcut is faster to demo and fatal in production. Don't.

## 3. Configuration sequence (Phase 1 — no code)

1. **Apps:** `hr`, `hr_contract`, `hr_holidays`, `hr_work_entry_contract`, `hr_payroll`,
   `hr_payroll_account`, `l10n_pk` (CoA only — there is no PK payroll module), `l10n_ae` +
   `l10n_ae_hr_payroll`, `sign`, `documents`.
2. **Companies:** parent *EY Payroll Services*; children *Indus Textile Mills* (PKR, Karachi),
   *Falcon Software* (PKR, Lahore), *Meridian BPO* (PKR, Islamabad), *Gulf Retail LLC* (AED, Dubai).
   Enable multi-currency.
3. **Accounting per client:** localisation CoA · `Salaries` journal · accounts: Salary Expense,
   Salaries Payable, **EOBI Payable**, **Income Tax Payable (s.149)**, **Provident Fund Payable**,
   **Social Security Payable**, **Gratuity Provision** (PK) / **EOSB Provision** (UAE).
4. **Working schedules:** PK 48h / 6-day (Mon–Sat) · UAE 48h / 6-day.
   ⚠️ **PK payroll divisor is 26 days; UAE is 30.** This is configuration, and it is where
   cross-border payroll systems quietly go wrong.
5. **Work entry types:** Attendance, Paid Leave, Unpaid Leave, Overtime, Sick, Public Holiday.
6. **Leave types** mapped to work entry types — this is what makes leave hit the payslip
   automatically, with no code.
7. **Payslip input types** (sheet `04_input_types`): `OT_H`, `ABSENT_D`, `BONUS`, `COMM`,
   `SHIFT_ALW`, `OTH_DED`.
8. **Structure types:** *Pakistan Employee (Monthly)*, *UAE Employee (Monthly)*.
9. **Structures + rules:** sheets `05_structures` / `06_salary_rules`. Categories: BASIC, ALW, GROSS,
   DED, NET, COMP (employer cost — `appears_on_payslip = False`).
10. **Employees & contracts:** sheets `07_employees` / `08_contracts`. Contract `wage` = **monthly
    gross**; the structure splits it.
11. **Run:** an `hr.payslip.run` per client for June 2026 → Generate → Compute → Validate → Post.

Configure **Gulf Retail end-to-end in this phase** and compute a real payslip. It proves a whole
country works with zero custom code — before anyone writes any.

## 4. The four structures

Sequence: BASIC(10) → allowances(20–60) → deductions(70–100) → GROSS(190) → NET(200) → employer
cost(210+). Full Python in sheet `06_salary_rules`. The load-bearing lines:

**ITM — Pakistan factory**
```python
BASIC    result = contract.wage                                   # minimum-wage floor: contract constraint
OT2X     result = (categories.BASIC / 26 / 8) * 2 * inputs.OT_H.amount    # Factories Act s.59 — 26-day divisor
ABSENT   result = -((categories.BASIC / 26) * inputs.ABSENT_D.amount)
EOBI_EE  result = -(payroll.pk_min_wage * payroll.pk_eobi_ee_rate)        # 1% of MIN WAGE, not of salary
TAX      result = -payslip._pk_income_tax()
EOBI_ER  result = payroll.pk_min_wage * payroll.pk_eobi_er_rate           # COMP — 5%, employer
SS_ER    result = payroll.pk_min_wage * payroll.pk_ss_er_rate             # COMP — SESSI/PESSI 6%
GRATUITY result = categories.BASIC / 12                                   # COMP — 30 days/year
```

**FSL — Pakistan IT (the tax showcase)**
```python
BASIC    result = contract.wage * 0.50
HRENT    result = categories.BASIC * 0.45
MEDICAL  result = categories.BASIC * 0.10      # EXEMPT from tax — 2nd Sch, Pt I, cl.139
UTIL     result = categories.BASIC * 0.10
CONVEY   result = contract.wage - categories.BASIC - rules.HRENT.amount - rules.MEDICAL.amount - rules.UTIL.amount
PF_EE    result = -(categories.BASIC * payroll.pk_pf_rate)      # cond: employee.pk_pf_member
TAX      result = -payslip._pk_income_tax()                     # taxable = GROSS - MEDICAL, annualised
```
Setting medical at exactly 10% of basic is the cheapest legal structuring lever in Pakistan. That the
system applies it automatically is worth real money to a client — say so in the demo.

**MBS — call centre:** BASIC 60%, HRENT, MEDICAL, plus `SHIFT_ALW` and `COMM` inputs (both taxable),
PF for members only.

**GRL — UAE:** BASIC 60 / HRA 25 / TRANS 10 / OTHALW 5, OT @1.25× on a **30-day** divisor, EOSB
accrual, **no income tax, no EOBI**. Same engine, different statute.

## 5. Accounting mapping

| Rule | Debit | Credit |
|---|---|---|
| Basic / allowances / OT | Salary Expense | Salaries Payable |
| Income tax (s.149) | Salaries Payable | Income Tax Payable |
| EOBI employee (1%) | Salaries Payable | EOBI Payable |
| EOBI employer (5%) · Social security (6%) | Salary Expense | EOBI / SS Payable |
| PF employee | Salaries Payable | Provident Fund Payable |
| PF employer | Salary Expense | Provident Fund Payable |
| Gratuity / EOSB provision | Gratuity Expense | Gratuity Provision (liability) |

## 6. Security matrix

| Group | Companies | Employees | Payslips | Cycle | Import |
|---|---|---|---|---|---|
| EY Payroll Manager | All | RW | RW + validate | RW | RW |
| EY Payroll Officer | Assigned only (`ir.rule`) | RW | RW, no validate | RW | RW |
| Client HR | Own only | R | R | Approve | R |
| Employee | — | Own | Own | — | — |

The Officer restriction is an `ir.rule` with a failing-access test — not a hidden menu.

## 7. Flag to EY before build starts

- **Enterprise vs Community.** `hr_payroll` is Enterprise-only. Confirm the licence first.
- **The slab table is a placeholder.** Seeded from Finance Act 2024. Get the gazetted TY2026 figures
  signed off by a Pakistani tax practitioner before a single client sees a computed number.
- **Province matters.** Minimum wage and social security differ across Sindh / Punjab / ICT. Config is
  per company — confirm each client's province and work locations.
- **Final settlement** (gratuity, leave encashment, notice pay and the tax on them) is where
  Pakistani payroll actually breaks. Roadmap slide, not demo scope.
- **Mid-year cutover.** YTD opening balances must be imported before a client goes live mid-tax-year,
  or the annualised tax will be wrong for every remaining month. Build the opening-balance import
  *before* the first real client, not after.
