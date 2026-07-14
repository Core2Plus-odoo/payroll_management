{
    "name": "Pakistan — Payroll",
    "summary": "Pakistan payroll: s.149 annualised income tax, EOBI, provident fund, social security, gratuity",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Payroll/Localizations",
    "author": "Core2Plus",
    "license": "LGPL-3",
    "depends": ["hr_payroll", "hr_payroll_account", "c2p_payroll_rates"],
    "data": [
        "security/ir.model.access.csv",
        "data/hr_payroll_structure_type_data.xml",
        "data/pk_statutory_rate_data.xml",    # min wage (per province), EOBI %, PF %, divisors, surcharge
        "data/pk_tax_slab_data.xml",          # TY2025/26/27 slab VERSIONS in the rate engine
        "views/hr_employee_views.xml",
    ],
    "installable": True,
    # GAP G4 — SCOPE PENDING re-verification on Odoo 19. See docs/VERIFICATION_ODOO19.md §4.
    #
    # ⚠ The premise below was TRUE on Odoo 18 and is now FALSE on Odoo 19: the official Odoo 19
    # docs list Pakistan among the shipped payroll localizations, i.e. `l10n_pk_hr_payroll`
    # (+ `_account`) now EXISTS. Before writing any PK tax code, install it on the dev build and
    # inspect whether it computes annualised, cumulative s.149 withholding and ships EOBI/PF/
    # SESSI/gratuity/OT. If it does, DELETE this module and Gap G4. If it computes tax per-period,
    # keep only the YTD tax helper, layered on the standard module. Build ON TOP OF the
    # localization's structures, never beside them.
    #
    # (Historical, Odoo 18:) Odoo shipped NO Pakistan payroll localization; s.149 withholding is
    # ANNUALISED and progressive, which the per-period rule engine cannot express on its own.
    # See docs/GAP_REGISTER.md and docs/PAKISTAN_PAYROLL.md.
}
