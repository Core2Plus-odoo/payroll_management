{
    "name": "C2P Payroll — EY Demo Dataset",
    "summary": "Four clients, four salary structures, 140 employees — the demo",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Payroll",
    "author": "Core2Plus",
    "license": "LGPL-3",
    "depends": ["c2p_payroll_bpo", "c2p_payroll_import", "c2p_l10n_pk_hr_payroll"],
    "data": [
        "data/res_company_data.xml",
        "data/hr_payroll_structure_type_data.xml",
        "data/hr_payslip_input_type_data.xml",
        "data/hr_payroll_structure_data.xml",
        "data/hr_salary_rule_data.xml",
        "data/payroll_import_profile_data.xml",
    ],
    "demo": [
        "demo/hr_department_demo.xml",
        "demo/hr_employee_demo.xml",
        "demo/hr_contract_demo.xml",
        "demo/hr_payslip_input_demo.xml",
    ],
    "installable": True,
    # Source of truth for all of the above: data/EY_Payroll_Master_Data.xlsx
    # Regenerate with: make demo   (scripts/load_demo.py)
}
