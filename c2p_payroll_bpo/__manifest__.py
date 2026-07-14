{
    "name": "C2P Payroll — BPO Control Tower",
    "summary": "Payroll cycle, SLA tracking and client onboarding for multi-client payroll bureaus",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Payroll",
    "author": "Core2Plus",
    "license": "LGPL-3",
    "depends": ["hr_payroll", "hr_payroll_account", "c2p_payroll_rates", "c2p_payroll_import", "mail"],
    "data": [
        "security/payroll_bpo_groups.xml",
        "security/payroll_bpo_rules.xml",
        "security/ir.model.access.csv",
        "data/payroll_cycle_stage_data.xml",
        "views/payroll_client_config_views.xml",
        "views/payroll_cycle_views.xml",
        "wizard/payroll_client_onboard_wizard_views.xml",
        "views/payroll_bpo_menus.xml",
    ],
    "installable": True,
    # GAP G2 (cycle/SLA) + G3 (client onboarding wizard). See docs/GAP_REGISTER.md.
}
