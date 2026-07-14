{
    "name": "C2P Payroll — Client Excel Intake",
    "summary": "Reusable, validated, audited Excel import profiles for BPO payroll clients",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Payroll",
    "author": "Core2Plus",
    "license": "LGPL-3",
    "depends": ["hr_payroll", "mail"],
    "external_dependencies": {"python": ["openpyxl"]},
    "data": [
        "security/ir.model.access.csv",
        "security/payroll_import_security.xml",
        "views/payroll_import_profile_views.xml",
        "views/payroll_import_batch_views.xml",
        "views/payroll_import_menus.xml",
    ],
    "installable": True,
    # GAP G1 — base_import requires manual per-file column mapping with no validation,
    # no staging, no audit and no reusability. A BPO ingests ~50 differently-shaped files
    # a month. See docs/GAP_REGISTER.md.
}
