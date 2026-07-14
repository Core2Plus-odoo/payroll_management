from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPkTax(TransactionCase):
    """Statutory correctness for the Pakistan tax engine. Numbers are the golden fixtures'
    (golden_payslips.csv) and are cross-checked by scripts/verify_golden.py."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pk = cls.env.ref("base.pk")
        cls.SlabV = cls.env["payroll.tax.slab.version"]
        cls.Rate = cls.env["payroll.statutory.rate"]
        cls.period_end = date(2026, 6, 30)

    # ---- slab math (progressive, boundaries) ----
    def test_slab_thresholds(self):
        tax_on = lambda a: self.SlabV.tax_on(a, self.pk.id, self.period_end)
        self.assertAlmostEqual(tax_on(600000), 0.0, 2)               # threshold: nil
        self.assertAlmostEqual(tax_on(600100), 5.0, 2)              # +1 rupee band: 5% of excess
        self.assertAlmostEqual(tax_on(1131692.31), 26584.62, 2)    # ITM-002 annual
        self.assertAlmostEqual(tax_on(2160000), 174000.0, 2)       # ITM-001 annual
        self.assertAlmostEqual(tax_on(618000), 900.0, 2)           # MBS-034: 618k -> 900/yr -> 75/mo
        self.assertAlmostEqual(tax_on(8850000), 2362500.0, 2)      # FSL-024 top slab

    def test_zero_tax_under_threshold(self):
        # ITM-054: annual taxable 570,461.54 < 600k -> zero tax, correctly.
        self.assertEqual(self.SlabV.tax_on(570461.54, self.pk.id, self.period_end), 0.0)

    # ---- surcharge above 10m taxable ----
    def test_surcharge(self):
        base = self.SlabV.tax_on(11400000, self.pk.id, self.period_end)  # FSL-SYNTH-SUR
        self.assertAlmostEqual(base, 3255000.0, 2)
        rate = self.Rate.value_of("surcharge_rate", self.pk.id, self.period_end)
        self.assertAlmostEqual(base * (1 + rate), 3580500.0, 2)          # /12 -> 298,375 monthly

    # ---- EOBI is 1%/5% of the MINIMUM WAGE, not of salary (the commonest PK bug) ----
    def test_eobi_flat_on_min_wage(self):
        mw = self.Rate.value_of("min_wage", self.pk.id, self.period_end, province="Sindh")
        ee = self.Rate.value_of("eobi_ee_rate", self.pk.id, self.period_end)
        er = self.Rate.value_of("eobi_er_rate", self.pk.id, self.period_end)
        self.assertEqual(mw, 37000)
        self.assertAlmostEqual(mw * ee, 370.0, 2)     # same for a 37k worker AND a 750k one
        self.assertAlmostEqual(mw * er, 1850.0, 2)

    # ---- resolver precedence: company > province > country, effective-dated ----
    def test_resolver_precedence(self):
        # Country default PF is 8.33%; a June-2026 payslip resolves that (FSL's 10% is future-dated).
        self.assertAlmostEqual(
            self.Rate.value_of("pf_rate", self.pk.id, self.period_end), 0.0833, 4)
        # A company override in force beats the country default.
        client = self.env["res.company"].create({"name": "PF Override Co", "country_id": self.pk.id})
        self.Rate.create({
            "key": "pf_rate", "value_num": 0.10, "country_id": self.pk.id,
            "company_id": client.id, "date_from": "2025-07-01", "state": "active"})
        self.assertAlmostEqual(
            self.Rate.value_of("pf_rate", self.pk.id, self.period_end, company_id=client.id), 0.10, 4)
        # ...but only for that company; others still get the country default.
        self.assertAlmostEqual(
            self.Rate.value_of("pf_rate", self.pk.id, self.period_end), 0.0833, 4)

    # ---- effective dating / immutability of history ----
    def test_effective_dating(self):
        # TY2025 slabs apply to a June-2025 period; TY2026 to a June-2026 period — same DB, same time.
        self.assertAlmostEqual(self.SlabV.tax_on(1131692.31, self.pk.id, date(2025, 6, 30)), 26584.62, 2)
        self.assertAlmostEqual(self.SlabV.tax_on(1131692.31, self.pk.id, date(2026, 6, 30)), 26584.62, 2)
        # A draft version (TY2027) is never resolved as active.
        active_codes = self.SlabV.search([
            ("country_id", "=", self.pk.id), ("state", "=", "active")]).mapped("code")
        self.assertNotIn("PK-TY2027-DRAFT", active_codes)

    # ---- grid validation rejects a fat-fingered rate at save ----
    def test_grid_validation_rejects_bad_rate(self):
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            v = self.SlabV.create({
                "code": "BAD", "name": "bad", "country_id": self.pk.id,
                "date_from": "2030-07-01", "date_to": "2031-06-30", "state": "active"})
            self.env["payroll.tax.slab"].create({
                "version_id": v.id, "lower_limit": 0, "rate_on_excess": 3.5})  # 3.5, not 0.35
            v._check_grid()
