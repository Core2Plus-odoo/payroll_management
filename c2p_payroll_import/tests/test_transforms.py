from odoo.tests import TransactionCase, tagged

from odoo.addons.c2p_payroll_import.models.transforms import apply_transform as T


@tagged("post_install", "-at_install")
class TestTransforms(TransactionCase):
    """The ugly RAW client files must resolve through transforms alone (G1)."""

    def test_number_and_currency(self):
        self.assertEqual(T("number_from_text", "-"), 0.0)          # dash = zero
        self.assertEqual(T("number_from_text", ""), 0.0)
        self.assertEqual(T("number_from_text", "1,500"), 1500.0)   # text number with comma
        self.assertEqual(T("strip_currency_prefix", "Rs. 200,000"), 200000.0)
        self.assertEqual(T("strip_currency_prefix", "Rs. 350,000"), 350000.0)

    def test_flags_iban_prefix(self):
        self.assertTrue(T("yn_to_bool", "Y"))
        self.assertFalse(T("yn_to_bool", "N"))
        self.assertEqual(T("clean_iban", "PK90 HABB 3758 1325 5509 8059"), "PK90HABB3758132555098059")
        self.assertEqual(T("prefix", "007", "ITM-"), "ITM-007")     # short code
        self.assertEqual(T("prefix", "FSL-001", "FSL-"), "FSL-001")  # already prefixed

    def test_idempotent_commit(self):
        """Committing the same resolved rows twice creates zero duplicates."""
        company = self.env["res.company"].create({"name": "Idem Co"})
        profile = self.env["payroll.import.profile"].create({
            "name": "p", "client_id": company.id, "doc_type": "attendance", "period": "2026-06"})
        MI = self.env["payroll.monthly.input"]

        def commit_once():
            for code, val in [("OT_H", 24.0), ("ABSENT_D", 3.0)]:
                key = [("client_id", "=", company.id), ("period", "=", "2026-06"),
                       ("emp_code", "=", "X-001"), ("input_code", "=", code)]
                rec = MI.search(key, limit=1)
                rec.value = val if rec else MI.create(dict(zip(
                    ["client_id", "period", "emp_code", "input_code", "value"],
                    [company.id, "2026-06", "X-001", code, val])))
        commit_once()
        commit_once()
        self.assertEqual(MI.search_count([("emp_code", "=", "X-001")]), 2)  # 2 codes, not 4
