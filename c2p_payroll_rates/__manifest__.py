{
    "name": "C2P Payroll — Statutory Rate Engine",
    "summary": "Effective-dated, scoped, auditable tax slabs and statutory rates — editable without a developer",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Payroll",
    "author": "Core2Plus",
    "license": "LGPL-3",
    "depends": ["hr_payroll", "mail"],
    "data": [
        "security/payroll_rates_groups.xml",
        "security/ir.model.access.csv",
        "views/payroll_rate_version_views.xml",   # slab grid: draft / active / archived
        "views/payroll_statutory_rate_views.xml",  # scoped rate table
        "wizard/payroll_rate_simulate_views.xml",  # draft -> simulate -> approve -> activate
        "views/payroll_rates_menus.xml",
    ],
    "installable": True,
    # GAP G5 — see docs/RATE_ENGINE.md.
    #
    # ⚠ FIRST: verify whether Odoo 19 hr_payroll ships `hr.rule.parameter` /
    # `hr.rule.parameter.value` (effective-dated, country-scoped rule parameters — the Belgian and
    # Indian localizations appear to use them for bracket tables):
    #
    #     grep -rn "rule_parameter" ~/src/odoo/addons/hr_payroll/models/
    #
    # IF IT EXISTS, it is the storage + effective-dating substrate. Salary rules must call the
    # STANDARD accessor, and this module shrinks to the four things standard does not do:
    #   A. scoping    — company > province > country precedence (a BPO needs per-client overrides)
    #   B. structure  — an editable, validated slab GRID instead of an opaque text blob
    #   C. governance — approver, reason, effective date, measured impact, audit log
    #   D. simulation — recompute into a scratch set under draft rates; live payslips untouched
    #
    # Do NOT build a parallel rate table if the standard one exists. Report what you find first.
}
