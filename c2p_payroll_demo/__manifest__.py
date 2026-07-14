{
    "name": "C2P Payroll — EY Demo Dataset",
    "summary": "Four clients, four salary structures — the demo configuration",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Payroll",
    "author": "Core2Plus",
    "license": "LGPL-3",
    "depends": ["c2p_payroll_bpo", "c2p_payroll_import", "c2p_l10n_pk_hr_payroll"],
    "data": [
        "data/hr_salary_rule_category_data.xml",
        "data/hr_payslip_input_type_data.xml",
        "data/hr_payroll_structure_type_data.xml",
        "data/hr_payroll_structure_data.xml",
        "data/hr_salary_rule_data.xml",
        "data/uae_statutory_rate_data.xml",
        "data/res_company_data.xml",
        "data/fsl_pf_override_data.xml",
        "data/payroll_import_profile_data.xml",
    ],
    "installable": True,
    # Employees / contracts (hr.version) / monthly inputs are bulk data loaded from the canonical
    # workbook by scripts/load_demo.py (idempotent):  make demo
    # The golden-payslip test (tests/test_golden_payslips.py) builds the 13 fixture employees itself
    # and asserts every rule line against tests/fixtures/golden_payslips.csv.
}
