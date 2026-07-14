from odoo import models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def _rate_context(self):
        """(country_id, date, province, company) used to resolve any statutory rate for this payslip.
        Effective date is the PERIOD END, so a payslip always resolves the version whose range
        contains its period — the basis of immutability (RATE_ENGINE.md §3)."""
        self.ensure_one()
        employee = self.employee_id
        company = self.company_id or employee.company_id
        country = company.country_id or employee.country_id
        province = employee.payroll_province or False
        return country, self.date_to, province, company

    def rate(self, key):
        """Resolve a statutory rate for this payslip — the ONLY way a salary rule may read a
        statutory number. Company > province > country, effective-dated. Raises nothing: an unknown
        key returns 0.0 so a mis-typed key surfaces as a zero line, not a traceback mid-run."""
        self.ensure_one()
        country, date, province, company = self._rate_context()
        if not country:
            return 0.0
        val = self.env["payroll.statutory.rate"].value_of(key, country.id, date, province, company)
        return val if val is not None else 0.0

    def slab_tax(self, annual_taxable):
        """Progressive tax on an annual taxable amount, using the slab version in force at period end."""
        self.ensure_one()
        country, date, _province, _company = self._rate_context()
        if not country:
            return 0.0
        return self.env["payroll.tax.slab.version"].tax_on(annual_taxable, country.id, date)
