# Pakistan Payroll — Functional & Technical Design

> This is the module that does not exist in Odoo. Everything else in this repo is configuration.

## 1. The finding

> 🔴 **RECONCILED ON ODOO 19 — this finding has flipped. See `docs/VERIFICATION_ODOO19.md §4`.**
> On Odoo **18** there was no `l10n_pk_hr_payroll`. On Odoo **19** the official docs list **Pakistan**
> among the shipped payroll localizations, so `l10n_pk_hr_payroll` now exists. **Before building any of
> this module, install the standard one on a dev build and inspect it.** If it already computes
> annualised, cumulative s.149 tax and ships EOBI/PF/SESSI/gratuity/OT, this whole module is deleted
> (a win). If it computes tax per-period, keep only §4's YTD tax helper layered on top of it. The
> design below is the fallback for what standard still doesn't do — not a licence to rebuild what it
> does.

**(Odoo 18 finding, retained for context.) Odoo ships no Pakistan payroll localization.** There is
`l10n_pk` (chart of accounts), but no `l10n_pk_hr_payroll` — the Odoo app store returns nothing for
it. Compare with UAE, KSA, India, Egypt, Kenya, which all have one.

So for the Pakistani clients, EY has **no standard path**. This is the single legitimate, substantial
piece of custom development in the project — and it is exactly the piece that becomes EY's moat: a
payroll bureau that has a tested, maintained Pakistan tax engine sells that engine to every
Pakistani client it onboards.

*(Verify on the instance, not from this document: `make verify` reports whether
`l10n_pk_hr_payroll` is installable. **This was checked against Odoo 18. You are on Odoo 19 — if a
Pakistan payroll module has since appeared, use it and delete this whole module.**)*

## 2. Why standard salary rules cannot do Pakistani income tax

> ✅ **CONFIRMED on Odoo 19: the contract model IS `hr.version`, not `hr.contract`.** In the salary-rule
> sandbox the variable is now **`version`** (an `hr.version` record), so every `contract.wage` below
> and in the sheet becomes **`version.wage`**, and `rules.X.amount` becomes `result_rules['X']['amount']`.
> See `docs/VERIFICATION_ODOO19.md §2, §3, §5` for the full mapping.

Odoo's rule engine evaluates **one payslip, one period, in isolation**. Section 149 withholding is:

- **Annualised** — tax is a function of *projected annual* taxable income, not of this month's pay.
- **Progressive** — six slabs, each a base amount plus a rate on the excess.
- **Cumulative** — the correct monthly deduction is
  `(annual tax liability − tax already withheld this tax year) ÷ months remaining`.
- **Fiscal-year bound** — Pakistan's tax year runs **1 July – 30 June**, not January–December.

A bonus in month 9 can push someone into a higher slab and must retroactively adjust months 9–12.
No arrangement of stateless `hr.salary.rule` expressions produces that. It needs a helper with access
to year-to-date payslip history.

Everything *else* about Pakistani payroll — allowance splits, EOBI, PF, gratuity, overtime — **is
ordinary salary-rule configuration.** Do not custom-build those.

## 3. Statutory reference

> ⚠️ **Every number below is a placeholder pending verification against the current Finance Act, EOBI
> notification, and provincial minimum-wage notification.** They are seeded in *data tables*
> precisely so that an annual Finance Act is a config edit, not a code deployment. Do not let a
> client see a computed number until a Pakistani tax practitioner has signed off the slab table.

**Income tax — salaried slabs.** Seeded from Finance Act 2024 (TY2025):

| Annual taxable income (PKR) | Tax |
|---|---|
| 0 – 600,000 | Nil |
| 600,001 – 1,200,000 | 5% of excess over 600,000 |
| 1,200,001 – 2,200,000 | 30,000 + 15% of excess over 1,200,000 |
| 2,200,001 – 3,200,000 | 180,000 + 25% of excess over 2,200,000 |
| 3,200,001 – 4,100,000 | 430,000 + 30% of excess over 3,200,000 |
| Above 4,100,000 | 700,000 + 35% of excess over 4,100,000 |

Plus a **surcharge on the tax** where taxable income exceeds PKR 10,000,000.
**Finance Act 2025 changed the lower-slab rates and the surcharge — get the gazetted TY2026 table.**

**Exempt from salary tax:** medical allowance up to **10% of basic** (2nd Schedule, Part I, cl. 139).
This is why the FSL structure sets medical at exactly 10% of basic — it is the cheapest legal
structuring lever available, and demonstrating that EY's system applies it automatically is worth
real money to a client.

**EOBI:** employee 1%, employer 5% — **of the minimum wage, not of actual salary.** At PKR 37,000
that is PKR 370 and PKR 1,850 flat, for everyone. Getting this wrong (charging % of actual salary) is
the single most common Pakistani payroll bug.

**Provincial social security** (SESSI Sindh / PESSI Punjab): employer ~6%, employee nil. Rates and
wage ceilings differ by province — hence `company_id`-scoped config, not a global constant.

**Provident fund:** typically 8.33% of basic, employee + matching employer. Recognised-PF tax
treatment differs from unrecognised.

**Gratuity:** 30 days' wages per year of service (Standing Orders Ordinance 1968), where no PF.

**Overtime:** 2× ordinary rate (Factories Act 1934, s.59). Divisor **26 days**, not 30 — a real and
frequently-botched difference from the Gulf.

## 4. Technical design

### Models

```python
class PkTaxSlab(models.Model):
    _name = "pk.tax.slab"
    _order = "tax_year desc, lower_limit"
    tax_year      = fields.Integer(required=True)   # 2026 = 1 Jul 2025 – 30 Jun 2026
    lower_limit   = fields.Monetary(required=True)
    upper_limit   = fields.Monetary()               # empty = no ceiling
    base_tax      = fields.Monetary()
    rate_on_excess = fields.Float(digits=(3, 4))
    company_id    = fields.Many2one("res.company")  # nullable = applies to all
```

`pk.tax.surcharge` (threshold, rate, tax_year) as a sibling — do not hard-code 10m/10%.

Config parameters (per company): `pk_min_wage`, `pk_eobi_ee_rate`, `pk_eobi_er_rate`,
`pk_ss_er_rate`, `pk_pf_rate`, `pk_monthly_days`, `pk_ot_multiplier`, `pk_tax_year_start`.

`hr.employee`: `pk_pf_member` (bool), `pk_cnic` (char, validated), `pk_tax_exemption_ids`
(certificates, disability, etc.).

### The tax helper — the whole point of the module

```python
def _pk_income_tax(self):
    """Monthly s.149 withholding for this payslip. Called from the TAX salary rule."""
    self.ensure_one()
    year_start, year_end = self._pk_tax_year_bounds()      # 1 Jul – 30 Jun
    months_elapsed  = self._pk_months_elapsed(year_start)  # incl. current
    months_left     = 12 - months_elapsed + 1

    taxable_this_month = self._pk_taxable_income()         # gross − exempt allowances
    ytd_taxable = self._pk_ytd("TAXABLE")                  # from validated payslips
    ytd_tax     = self._pk_ytd("TAX")

    projected_annual = ytd_taxable + taxable_this_month * months_left
    annual_liability = self._pk_slab_tax(projected_annual) # slab table + surcharge
    return max((annual_liability - ytd_tax) / months_left, 0.0)
```

Four properties this must hold, and each is a test:

1. **Stable salary, no events** → 12 equal monthly deductions summing exactly to the annual liability.
2. **Mid-year raise or bonus** → months after the event absorb the whole extra liability; the
   year-total still ties out.
3. **Joiner mid-year** → annualised over *remaining* months only, never over 12.
4. **Never negative** — a projection that falls (e.g. commission dries up) yields zero, not a refund.

Read YTD in **one** `read_group` over `hr.payslip.line` for the tax year. Never loop payslips.

### Salary rules

Rules stay declarative and call the helper: `result = -payslip._pk_income_tax()`. Statutory rates are
read from config (`payroll.pk_eobi_ee_rate`), never written as literals in a rule body. When the
Finance Act lands, EY updates a table and reruns — no code, no deploy, no regression risk.

## 5. Demo clients — chosen to cover the whole statute

| Client | HC | What it proves |
|---|---|---|
| **Indus Textile Mills** (Karachi) | 60 | Minimum wage, 26-day divisor, OT @2×, EOBI, SESSI, gratuity. Most workers fall **below** the 600k threshold → **zero tax**, which is itself the demo: the system knows not to deduct. |
| **Falcon Software** (Lahore) | 30 | The tax showcase. Salaries from 90k to 750k/month walk **every slab**. Provident fund, medical-allowance exemption, bonus pushing a slab boundary. |
| **Meridian BPO** (Islamabad) | 40 | Shift allowance, commission, PF members and non-members side by side. One agent lands at PKR 618,000 annual — **PKR 75/month tax**, just over the threshold. The precision is the point. |
| **Gulf Retail LLC** (Dubai) | 20 | The expansion proof: same engine, no income tax, no EOBI, EOSB instead. "When your client opens in Dubai, you don't buy another system." |

150 employees. `c2p_payroll_demo/tests/fixtures/golden_payslips.csv` holds the expected value of **every rule line** for
13 of them, including the two threshold edge cases and a synthetic PKR 1m/month surcharge case.

## 6. What to challenge before building

- **Which province?** Sindh and Punjab differ on minimum wage and social security. ITM is Karachi
  (SESSI), FSL/MBS are Punjab/ICT. If a client operates across provinces, config must be per company
  *and* per work location.
- **Recognised vs unrecognised PF** changes the tax treatment of the employer contribution.
- **Final settlement** (gratuity, leave encashment, notice pay, and the tax on them) is where
  Pakistani payroll actually goes wrong. Out of demo scope — put it on the roadmap slide, not in the
  build.
- **Tax certificates / exemptions** (disabled persons, senior citizens, teachers' rebate) — model as
  a per-employee exemption record from day one, or retrofitting it will hurt.
