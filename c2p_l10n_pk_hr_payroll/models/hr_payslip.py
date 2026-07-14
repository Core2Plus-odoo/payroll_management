from dateutil.relativedelta import relativedelta

from odoo import models
from odoo.tools import float_round


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    # ------------------------------------------------------------------ tax year
    def _pk_tax_year_bounds(self):
        """(start, end) of the Pakistan tax year containing this payslip's period end.
        Start month/day comes from the rate engine ('tax_year_start' = 07-01), never a literal."""
        self.ensure_one()
        mmdd = self.rate("tax_year_start") or "07-01"
        start_month = int(str(mmdd).split("-")[0])
        period_end = self.date_to
        year = period_end.year if period_end.month >= start_month else period_end.year - 1
        start = period_end.replace(year=year, month=start_month, day=1)
        end = start + relativedelta(years=1) - relativedelta(days=1)
        return start, end

    def _pk_annualisation_months(self, year_start, year_end):
        """N — the number of tax-year months this employee is employed over: the annualisation base.
        Full-year employee = 12; a mid-year joiner is annualised over remaining months only, never 12
        (PAKISTAN_PAYROLL.md §4, property 3)."""
        self.ensure_one()
        start_dates = (self.version_id.contract_date_start, self.version_id.date_version)
        emp_start = max([d for d in start_dates if d] + [year_start])
        emp_start = max(emp_start, year_start)
        months = (year_end.year - emp_start.year) * 12 + (year_end.month - emp_start.month) + 1
        return max(min(months, 12), 1)

    def _pk_prior_payslips(self, year_start):
        """Validated payslips for this employee earlier in the same tax year (YTD source)."""
        self.ensure_one()
        return self.search([
            ("employee_id", "=", self.employee_id.id),
            ("state", "in", ("done", "paid")),
            ("date_to", ">=", year_start),
            ("date_to", "<", self.date_from),
            ("id", "!=", self.id),
        ])

    def _pk_ytd(self, prior_payslips, code):
        """Sum of a line code across prior payslips, in ONE read_group — never loop payslips
        (PAKISTAN_PAYROLL.md §4)."""
        if not prior_payslips:
            return 0.0
        groups = self.env["hr.payslip.line"].read_group(
            [("slip_id", "in", prior_payslips.ids), ("code", "=", code)],
            ["total:sum"], [])
        return groups[0]["total"] if groups and groups[0].get("total") else 0.0

    # ------------------------------------------------------------------ the helper
    def _pk_income_tax(self, monthly_taxable):
        """Monthly s.149 withholding for this payslip. Called from the TAX salary rule as
        ``result = -payslip._pk_income_tax(<monthly taxable>)``.

        Annualised, progressive, cumulative over the July–June tax year. With no YTD history a stable
        full-year salary yields 12 equal deductions summing to the annual liability; a mid-year event
        is trued up by later months; a joiner is annualised over remaining months only; never negative
        (the four properties in PAKISTAN_PAYROLL.md §4). Every rate/slab is resolved from the engine.
        """
        self.ensure_one()
        year_start, year_end = self._pk_tax_year_bounds()
        n = self._pk_annualisation_months(year_start, year_end)
        prior = self._pk_prior_payslips(year_start)
        months_paid = len(prior)
        months_remaining = max(n - months_paid, 1)

        # TAXABLE_ANNUAL on each prior slip = that month's taxable x 12, so /12 recovers the monthly
        # taxable; summed over priors this is the true YTD taxable. One read_group, no payslip loop.
        ytd_taxable = self._pk_ytd(prior, "TAXABLE_ANNUAL") / 12.0
        ytd_tax = abs(self._pk_ytd(prior, "TAX"))

        projected_annual = ytd_taxable + monthly_taxable * months_remaining
        annual_liability = self.slab_tax(projected_annual)

        threshold = self.rate("surcharge_threshold")
        if threshold and projected_annual > threshold:
            annual_liability *= (1 + self.rate("surcharge_rate"))

        monthly = (annual_liability - ytd_tax) / months_remaining
        return float_round(max(monthly, 0.0), precision_digits=2)
