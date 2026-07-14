# The Rate Engine — changing tax rates, slabs and statutory rates without a developer

> A Finance Act lands every June. Provincial minimum wages change on their own schedule. Clients
> switch their PF scheme by board resolution. If any of these needs a developer, EY hasn't bought a
> product — it's bought a liability.
>
> **Requirement: EY's payroll manager changes a rate, sees who it affects, gets it approved, and it
> takes effect on the right date — without touching code, and without altering a single validated
> payslip from last month.**

## 0. FIRST — check whether Odoo already does this

I believe Odoo Enterprise `hr_payroll` ships **`hr.rule.parameter`** and
**`hr.rule.parameter.value`**: named parameters, versioned by `date_from`, country-scoped, read from
a salary rule with something like `payslip.rule_parameter('code')`. The Belgian and Indian
localizations use it precisely for effective-dated bracket tables.

**I could not verify this from my environment. It is your first job.**

```bash
grep -rn "rule_parameter\|rule\.parameter" ~/src/odoo/addons/hr_payroll/models/ | head -30
grep -rn "rule_parameter" ~/src/odoo/addons/l10n_*_hr_payroll/ | head -20
```

**If it exists — and I expect it does — do NOT build a parallel rate table.** Standard becomes the
storage and effective-dating substrate; the salary rules call the standard accessor; and the custom
work shrinks to the four genuine gaps in §2. That is a smaller, safer module and it survives Odoo
upgrades. Report what you find before designing anything.

**If it does not exist**, build `payroll.rate.value` with the same semantics (code, value, date_from,
country) and layer §2 on top. The design below works either way, which is deliberate.

## 1. What has to be configurable

Nothing statutory may appear as a literal in Python. Everything in `source_data/EY_Payroll_Master_Data.xlsx`
sheets `10_tax_slabs` and `11_statutory_rates`:

| | |
|---|---|
| **Tax slabs** | Six bands: lower, upper, base tax, rate on excess. Count of bands is itself variable — never assume six. |
| **Surcharge** | Threshold and rate. |
| **Exemptions** | Medical allowance as % of basic; future: disability, teachers' rebate. |
| **EOBI** | Employee %, employer %, **and the base it applies to** (`min_wage` today — but if the law switches to gross, that's a config change, not a code change). |
| **Provident fund** | %, and whether the client even runs one. |
| **Social security** | %, per province. |
| **Minimum wage** | Per province, per year. |
| **Divisors & multipliers** | 26 days PK / 30 UAE; OT 2× PK / 1.25× UAE. |
| **Tax year start** | 1 July for PK, 1 January elsewhere. |
| **Whether income tax applies at all** | UAE: no. Same rule, resolves to nil. |

The last row is the tell. If the engine is right, adding a country is a data exercise.

## 2. The four gaps standard parameters leave

**Gap A — Scoping.** `hr.rule.parameter` is country-scoped. A BPO needs three more levels:

```
company + province + date   →   company + date   →   province + date   →   country + date
     (most specific wins; first match returns)
```

Falcon Software runs a **10% PF** against the Pakistani norm of 8.33% — a *company* override.
Sindh and Punjab set minimum wage separately — a *province* override. Sheet `11_statutory_rates`
carries both, and the resolver must implement exactly that precedence, tested.

**Gap B — Structure.** A slab table stored as an opaque text blob is not editable by a payroll
manager. It needs to be a **grid** — one row per band, typed fields, with validation on save:
bands contiguous, no gaps, no overlaps, ascending, top band open-ended, rates between 0 and 1.
Catching a fat-fingered `3.5` instead of `0.35` at save time is worth the whole module.

**Gap C — Governance.** Who changed the EOBI rate, when, on whose authority, and why? Standard
parameters have no approver, no reason, no impact record. Sheet `12_rate_change_log` is the shape:
`changed_at · changed_by · record · change · effective_from · approved_by · reason · impact`.
When a client asks *"why is my March tax different from February?"*, this table is the answer, and
answering it in ten seconds is the service EY is selling.

**Gap D — Simulation.** A rate change must be modelled before it is committed. See §4.

## 3. Effective dating — the non-negotiable

Every rate and every slab version carries `date_from` / `date_to`. A payslip resolves the version
**whose range contains its period end**.

Consequences, and each is a test:

1. **Loading TY2027 slabs never changes a validated TY2026 payslip.** History is immutable. If a
   rate edit can retroactively alter a filed month, the system is unsafe at any speed.
2. A payslip **recomputed** later resolves the *same* version it originally used.
3. A rate with no `date_to` is open-ended; superseding it **sets** its `date_to`, it does not delete
   it. Nothing is ever destroyed — sheet `11` shows Sindh minimum wage 32,000 archived beneath
   37,000.
4. Mid-year amendments work: two versions inside one tax year, split by date. Pakistan does this.

`state`: `draft` (simulate only, never touches a real payslip) · `active` · `archived`.
Sheet `10_tax_slabs` ships three versions — TY2025 (archived), TY2026 (active), and a clearly-marked
**hypothetical** TY2027 draft that exists solely to demo the workflow below.

## 4. Draft → Simulate → Approve → Activate

This is the feature that wins the room.

1. **Draft.** Payroll manager copies the active slab version, edits the grid. State `draft`.
   It cannot affect any payslip.
2. **Simulate.** One button: recompute the current period's payslips **into a scratch set** under the
   draft rates. Output a diff, per client and per employee:

   > *Falcon Software — 30 employees. Net pay +1.8% avg (+PKR 412,000/month total). 4 employees cross
   > a slab boundary. Employer cost −PKR 96,000. Largest individual change: FSL-024, +PKR 31,200/month.*

   Live payslips are untouched. Run it as often as you like.
3. **Approve.** Reason and approver are mandatory. Writes the change log.
4. **Activate.** Sets `date_from`, archives the superseded version, and — if `hr.rule.parameter`
   exists — writes down into standard `hr.rule.parameter.value` records so the runtime path stays
   standard Odoo.

Budget day in Pakistan: EY loads the proposed slabs in the morning, and by lunchtime every client has
a report saying exactly what the Finance Act does to their payroll. **That is a billable product**,
and it falls out of the architecture for free.

## 5. Loading rates from Excel

EY lives in Excel; the rate tables must load the same way as everything else — through
`c2p_payroll_import`, with a profile for `tax_slab` and `statutory_rate`. Same dry-run, same
validation, same audit, same idempotency. The FBR publishes the slabs; someone pastes them into a
sheet; the engine validates contiguity and flags anything odd before it goes anywhere near a payslip.

## 6. Tests that must exist

- Resolver precedence: company > province > country. FSL resolves `pf_rate` = 10%; ITM resolves 8.33%.
- Effective dating: a June-2025 payslip uses TY2025 slabs; a June-2026 payslip uses TY2026 — **from
  the same database, at the same time.**
- Immutability: activate TY2027, recompute a validated June-2026 payslip → **identical to the penny**.
- Grid validation: overlapping bands, a gap between bands, a descending band, a rate of `3.5` — each
  rejected at save.
- Simulation isolates: run a draft simulation, then assert no live payslip line changed.
- **Zero literals:** a test that greps the addons for statutory-looking numbers
  (`0.0975`, `37000`, `0.0833`, `600000`…) in `.py` files and fails if any is found. Blunt, and it
  will save the project.
- Adding a country is data-only: a test that builds a fictional country's payroll purely from rate
  rows, with no new Python.

## 7. What I'd still flag

- **Rounding.** Pakistani tax is conventionally rounded to the rupee; where and how you round changes
  net pay by a rupee or two, and clients *will* notice. Make it a config parameter, decide it once,
  and put it in the golden tests.
- **Mid-year rate changes vs the annualised tax helper.** If EOBI changes in month 8, the projection
  for months 8–12 uses the new rate while months 1–7 used the old. The helper must project with the
  rate **effective in each future month**, not blindly with today's. This is the subtlest bug in the
  build. Write the test first.
- **Who approves?** The change log has an `approved_by` column. Decide now whether that's an EY
  manager or the client's HR — it's a contractual question, not a technical one, and it determines
  where liability sits when a rate is wrong.
