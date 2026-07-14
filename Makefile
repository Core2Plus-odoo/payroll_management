# ---------------------------------------------------------------------------
# Deployment is git-push driven — Odoo.sh builds every branch it receives.
# NEVER push untested payroll code to production/19.0.
#
#   git checkout -b dev/payroll
#   git push origin dev/payroll        -> Odoo.sh spins up a dev build + DB copy
#   (test) -> merge to staging -> merge to production
#
# These targets run INSIDE the Odoo.sh shell (odoo-bin, odoo-update are on PATH).
# ---------------------------------------------------------------------------
DB ?= $(shell psql -tAc "SELECT current_database()" 2>/dev/null)

STD_MODULES := hr,hr_payroll,hr_payroll_account,hr_holidays,hr_work_entry_contract,l10n_pk,l10n_ae,l10n_ae_hr_payroll
C2P_MODULES := c2p_l10n_pk_hr_payroll,c2p_payroll_import,c2p_payroll_bpo,c2p_payroll_demo

.PHONY: verify standard init upgrade test demo shell

verify:   ## FIRST. Answers every version-dependent unknown in the spec.
	odoo-bin shell < scripts/verify_environment.py

standard: ## Phase 1: standard payroll only — proves most of the ask needs no code
	odoo-update $(STD_MODULES) -i

init:     ## standard + the four custom modules
	odoo-update $(STD_MODULES),$(C2P_MODULES) -i

upgrade:
	odoo-update $(C2P_MODULES)

test:     ## golden payslips, PK tax edge cases, import idempotency, access rules
	odoo-bin -d $(DB) -u $(C2P_MODULES) --test-enable \
	  --test-tags /c2p_l10n_pk_hr_payroll,/c2p_payroll_import,/c2p_payroll_bpo,/c2p_payroll_demo \
	  --stop-after-init

demo:     ## (re)load the 4-client dataset from source_data/*.xlsx — idempotent
	odoo-bin shell < scripts/load_demo.py

shell:
	odoo-bin shell
