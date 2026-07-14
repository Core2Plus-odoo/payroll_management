from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PayrollTaxSlabVersion(models.Model):
    """A versioned, effective-dated set of progressive tax bands for one country/tax-year.

    Generic on purpose (RATE_ENGINE.md §1: "adding a country is a data exercise"). Pakistan seeds it
    from c2p_l10n_pk_hr_payroll; the UAE simply has no active version, so its TAX rule resolves to nil.
    ``draft`` versions never touch a real payslip; ``active`` is in force; ``archived`` is superseded
    but retained for audit.
    """

    _name = "payroll.tax.slab.version"
    _description = "Tax Slab Version (effective-dated)"
    _order = "country_id, date_from desc"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    tax_year = fields.Integer(help="Label only, e.g. 2026 = 1 Jul 2025 – 30 Jun 2026.")
    country_id = fields.Many2one("res.country", required=True, index=True, ondelete="cascade")
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    source_reference = fields.Char()
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("archived", "Archived")],
        default="draft", required=True, index=True)
    line_ids = fields.One2many("payroll.tax.slab", "version_id", string="Bands")

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for v in self:
            if v.date_to < v.date_from:
                raise ValidationError("Slab version %s: date_to precedes date_from." % v.code)

    @api.constrains("line_ids", "state")
    def _check_grid(self):
        """Grid validation (RATE_ENGINE.md §2 Gap B): bands must start at 0, be ascending, contiguous
        with no gaps or overlaps, the top band open-ended, and every rate in [0, 1]. Catching a
        fat-fingered 3.5 where 0.35 was meant, at save time, is the point of the module."""
        for v in self:
            if v.state == "draft" and not v.line_ids:
                continue
            bands = v.line_ids.sorted("lower_limit")
            if not bands:
                raise ValidationError("Slab version %s has no bands." % v.code)
            if bands[0].lower_limit != 0:
                raise ValidationError("Slab version %s: the first band must start at 0." % v.code)
            for i, b in enumerate(bands):
                if not (0.0 <= b.rate_on_excess <= 1.0):
                    raise ValidationError(
                        "Slab version %s: rate %s is outside [0, 1] — did you mean %s?"
                        % (v.code, b.rate_on_excess, b.rate_on_excess / 10.0))
                if i < len(bands) - 1:
                    nxt = bands[i + 1]
                    if not b.upper_limit:
                        raise ValidationError(
                            "Slab version %s: only the top band may be open-ended." % v.code)
                    if b.upper_limit != nxt.lower_limit:
                        raise ValidationError(
                            "Slab version %s: gap/overlap between %s and %s."
                            % (v.code, b.upper_limit, nxt.lower_limit))
                else:
                    if b.upper_limit:
                        raise ValidationError(
                            "Slab version %s: the top band must be open-ended." % v.code)

    @api.model
    def tax_on(self, annual_taxable, country_id, date):
        """Progressive tax on an annual taxable amount, resolving the version in force on ``date``."""
        country_id = country_id.id if hasattr(country_id, "id") else country_id
        version = self.search([
            ("country_id", "=", country_id), ("state", "=", "active"),
            ("date_from", "<=", date), ("date_to", ">=", date),
        ], limit=1)
        if not version:
            return 0.0
        for b in version.line_ids.sorted("lower_limit"):
            upper = b.upper_limit or float("inf")
            if b.lower_limit < annual_taxable <= upper:
                return b.base_tax + (annual_taxable - b.lower_limit) * b.rate_on_excess
        return 0.0


class PayrollTaxSlab(models.Model):
    _name = "payroll.tax.slab"
    _description = "Tax Slab Band"
    _order = "version_id, lower_limit"

    version_id = fields.Many2one("payroll.tax.slab.version", required=True, ondelete="cascade", index=True)
    lower_limit = fields.Monetary(required=True)
    upper_limit = fields.Monetary(help="Empty = open-ended (top band only).")
    base_tax = fields.Monetary(help="Tax on all income up to lower_limit.")
    rate_on_excess = fields.Float(digits=(6, 4), help="Marginal rate on income above lower_limit, as a ratio.")
    currency_id = fields.Many2one(related="version_id.country_id.currency_id", string="Currency")
