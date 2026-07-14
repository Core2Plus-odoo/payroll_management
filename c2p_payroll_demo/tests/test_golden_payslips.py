import csv
import os
from collections import defaultdict

from odoo.tests import TransactionCase, tagged

# emp_code -> (client, monthly_wage, pf_member, {input_code: value})
FIXTURE = {
    "ITM-054": ("ITM", 37000, False, {"OT_H": 24, "ABSENT_D": 3, "BONUS": 2000}),
    "ITM-002": ("ITM", 75000, False, {"OT_H": 24, "ABSENT_D": 3, "BONUS": 2000}),
    "ITM-001": ("ITM", 180000, False, {"ABSENT_D": 1}),
    "FSL-006": ("FSL", 90000, False, {"BONUS": 10000, "OTH_DED": 500}),
    "FSL-002": ("FSL", 200000, True, {"BONUS": 25000}),
    "FSL-012": ("FSL", 350000, False, {"OTH_DED": 1500}),
    "FSL-024": ("FSL", 750000, True, {"BONUS": 25000}),
    "MBS-029": ("MBS", 130000, True, {"COMM": 30000, "SHIFT_ALW": 8000, "ABSENT_D": 1, "OTH_DED": 500}),
    "MBS-034": ("MBS", 50000, True, {"SHIFT_ALW": 8000, "ABSENT_D": 1, "OTH_DED": 500}),
    "MBS-035": ("MBS", 45000, True, {"SHIFT_ALW": 5000, "ABSENT_D": 3, "OTH_DED": 1500}),
    "GRL-008": ("GRL", 3500, False, {"OT_H": 8, "ABSENT_D": 2, "OTH_DED": 500}),
    "GRL-018": ("GRL", 3500, False, {"OT_H": 8, "ABSENT_D": 1}),
    "FSL-SYNTH-SUR": ("FSL", 1000000, True, {}),
}
COMPANY_REF = {c: "c2p_payroll_demo.company_%s" % c.lower() for c in ("ITM", "FSL", "MBS", "GRL")}
STRUCT_REF = {
    "ITM": "c2p_payroll_demo.struct_ss_itm_factory", "FSL": "c2p_payroll_demo.struct_ss_fsl_whitecollar",
    "MBS": "c2p_payroll_demo.struct_ss_mbs_callcentre", "GRL": "c2p_payroll_demo.struct_ss_grl_retail",
}
STYPE_REF = {
    "ITM": "c2p_l10n_pk_hr_payroll.structure_type_pk_monthly",
    "FSL": "c2p_l10n_pk_hr_payroll.structure_type_pk_monthly",
    "MBS": "c2p_l10n_pk_hr_payroll.structure_type_pk_monthly",
    "GRL": "c2p_payroll_demo.structure_type_uae_monthly",
}
PROVINCE = {"ITM": "Sindh", "FSL": "Punjab", "MBS": "ICT", "GRL": False}


@tagged("post_install", "-at_install")
class TestGoldenPayslips(TransactionCase):
    """Every rule line for 13 employees across 4 clients, asserted exactly against
    tests/fixtures/golden_payslips.csv. These catch silent rule regressions — the bug that kills a
    payroll bureau. Numbers are independently reproduced by scripts/verify_golden.py."""

    def _golden(self):
        path = os.path.join(os.path.dirname(__file__), "fixtures", "golden_payslips.csv")
        expected = defaultdict(dict)
        with open(path) as f:
            for row in csv.DictReader(f):
                expected[row["emp_code"]][row["rule_code"]] = float(row["expected_amount"])
        return expected

    def _make_payslip(self, emp_code):
        client, wage, pf_member, inputs = FIXTURE[emp_code]
        company = self.env.ref(COMPANY_REF[client])
        employee = self.env["hr.employee"].with_company(company).create({
            "name": emp_code, "barcode": emp_code, "company_id": company.id,
            "pk_pf_member": pf_member, "payroll_province": PROVINCE[client],
        })
        employee.version_id.write({
            "wage": wage, "contract_date_start": "2019-01-01",
            "structure_type_id": self.env.ref(STYPE_REF[client]).id,
        })
        itypes = {t.code: t.id for t in self.env["hr.payslip.input.type"].search([])}
        slip = self.env["hr.payslip"].create({
            "name": "Golden %s" % emp_code, "employee_id": employee.id,
            "version_id": employee.version_id.id, "struct_id": self.env.ref(STRUCT_REF[client]).id,
            "company_id": company.id, "date_from": "2026-06-01", "date_to": "2026-06-30",
            "input_line_ids": [(0, 0, {"input_type_id": itypes[c], "amount": v})
                               for c, v in inputs.items() if c in itypes],
        })
        slip.compute_sheet()
        return slip

    def test_golden_payslips(self):
        expected = self._golden()
        failures = []
        for emp_code, rules in expected.items():
            slip = self._make_payslip(emp_code)
            got = {line.code: line.total for line in slip.line_ids}
            for code, exp in rules.items():
                actual = got.get(code)
                if actual is None or abs(actual - exp) > 0.02:
                    failures.append("%s/%s: expected %.2f got %s" % (emp_code, code, exp, actual))
        self.assertFalse(failures, "Golden payslip mismatches:\n" + "\n".join(failures))
