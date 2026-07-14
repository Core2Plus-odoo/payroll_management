#!/usr/bin/env python3
"""
Run on the Odoo.sh shell:

    odoo-bin shell < verify_environment.py

Answers every question the build spec currently guesses at. Paste the output back.
"""
import odoo, os, re

print("=" * 72)
print("ODOO ENVIRONMENT PROBE")
print("=" * 72)
print(f"Odoo version : {odoo.release.version}")
print(f"Edition      : {'ENTERPRISE' if odoo.tools.config.get('addons_path') and any('enterprise' in p for p in odoo.tools.config['addons_path'].split(',')) else 'check addons_path below'}")
print(f"addons_path  : {odoo.tools.config['addons_path']}")
print(f"database     : {env.cr.dbname}")
print()

# ---------------------------------------------------------------- 1. modules
M = env["ir.module.module"]
print("-" * 72)
print("1. PAYROLL MODULES AVAILABLE")
print("-" * 72)
for pat in ["hr_payroll", "hr_contract", "l10n_pk", "l10n_ae", "hr_work_entry", "hr_holidays"]:
    mods = M.search([("name", "like", pat)])
    if not mods:
        print(f"  {pat:22} -> NONE FOUND")
    for m in mods:
        print(f"  {m.name:36} {m.state:12} v{m.latest_version or m.installed_version or '-'}")
print()
pk = M.search([("name", "=", "l10n_pk_hr_payroll")])
print(f"  >>> PAKISTAN PAYROLL LOCALIZATION EXISTS: {'YES — USE IT, delete c2p_l10n_pk_hr_payroll' if pk else 'NO — confirms Gap G4'}")
print()

# ---------------------------------------------------------------- 2. the v19 HR refactor
print("-" * 72)
print("2. CONTRACT MODEL — did Odoo 19 replace hr.contract?")
print("-" * 72)
for model in ["hr.contract", "hr.version", "hr.employee", "hr.payslip", "hr.payroll.structure",
              "hr.salary.rule", "hr.payslip.input.type", "hr.payslip.run"]:
    exists = model in env
    print(f"  {model:26} {'OK' if exists else '*** DOES NOT EXIST ***'}")
print()
if "hr.version" in env:
    print("  >>> hr.version EXISTS. Odoo 19 moved contract data onto employee versions.")
    print("      EVERY 'contract.wage' in the spec must be rewritten. Dump the fields:")
    for f in sorted(env["hr.version"]._fields):
        if any(k in f for k in ("wage", "salary", "struct", "date", "allowance")):
            print(f"        hr.version.{f}")
print()

# ---------------------------------------------------------------- 3. payslip API
print("-" * 72)
print("3. SALARY RULE SANDBOX — what names are in scope in amount_python_compute?")
print("-" * 72)
src = ""
for base in odoo.tools.config["addons_path"].split(","):
    p = os.path.join(base.strip(), "hr_payroll", "models", "hr_payslip.py")
    if os.path.exists(p):
        src = open(p, encoding="utf-8", errors="ignore").read()
        print(f"  source: {p}")
        break
if src:
    m = re.search(r"localdict\s*=\s*\{(.{0,600}?)\}", src, re.S)
    print("  localdict keys:", re.findall(r"[\"'](\w+)[\"']\s*:", m.group(1)) if m else "not matched — grep manually")
    # Odoo 19 renamed the sandbox: `contract` -> `version` (hr.version), `rules` -> `result_rules`.
    # See docs/VERIFICATION_ODOO19.md §3. Presence of `version`/`result_rules` and ABSENCE of
    # `contract`/`rules` in the localdict is the confirmation that the refactor landed here.
    for token in ["sum_worked_hours", "_get_worked_day_lines", "payslip.", "categories.",
                  "version", "result_rules", "contract", "rules.", "inputs.", "worked_days."]:
        print(f"    {'YES' if token in src else 'no '}  {token}")
else:
    print("  !! hr_payroll not found on the addons path — Enterprise addons may not be mounted.")
print()

# ---------------------------------------------------------------- 4. companies / currencies
print("-" * 72)
print("4. CURRENT STATE OF THE PRODUCTION DB")
print("-" * 72)
print(f"  companies : {env['res.company'].sudo().search_count([])}")
for c in env["res.company"].sudo().search([], limit=10):
    print(f"      {c.id:>3}  {c.name:34} {c.currency_id.name}  parent={c.parent_id.name or '-'}")
print(f"  employees : {env['hr.employee'].sudo().search_count([])}")
print(f"  PKR active: {bool(env['res.currency'].sudo().search([('name','=','PKR'),('active','=',True)]))}")
print(f"  AED active: {bool(env['res.currency'].sudo().search([('name','=','AED'),('active','=',True)]))}")
print()
print("=" * 72)
print("Paste this whole output back into the chat.")
print("=" * 72)
