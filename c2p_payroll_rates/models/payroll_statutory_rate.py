from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PayrollStatutoryRate(models.Model):
    """Effective-dated, scoped statutory rate (EOBI %, PF %, minimum wage, divisors, ...).

    Storage substrate is deliberately parallel to Odoo's standard ``hr.rule.parameter`` but adds the
    three things standard does not (RATE_ENGINE.md §2): company/province scoping, governance state,
    and the resolver precedence a BPO needs. No statutory number is ever a literal in a salary rule;
    rules call ``payslip.rate('key')`` which lands here.
    """

    _name = "payroll.statutory.rate"
    _description = "Payroll Statutory Rate (scoped, effective-dated)"
    _order = "key, country_id, date_from desc"

    name = fields.Char(compute="_compute_name", store=True)
    key = fields.Char(
        required=True, index=True,
        help="Resolver key used by salary rules, e.g. eobi_ee_rate, pf_rate, monthly_days.")
    value_num = fields.Float(string="Numeric value", digits=(16, 6))
    value_char = fields.Char(string="Text value", help="For non-numeric rates, e.g. tax_year_start = 07-01.")
    unit = fields.Char()

    country_id = fields.Many2one("res.country", required=True, index=True, ondelete="cascade")
    province = fields.Char(help="Province/state scope, e.g. Sindh, Punjab, ICT. Empty = whole country.")
    company_id = fields.Many2one(
        "res.company", index=True,
        help="Client company override. Empty = applies to every company in the country.")

    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(help="Empty = open-ended (in force). Superseding a rate SETS this, never deletes.")
    source_reference = fields.Char()
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("archived", "Archived")],
        default="active", required=True, index=True)

    @api.depends("key", "country_id", "province", "company_id", "value_num", "value_char")
    def _compute_name(self):
        for r in self:
            scope = r.company_id.name or r.province or (r.country_id.code or "")
            val = r.value_char or r.value_num
            r.name = f"{r.key} = {val} [{scope}]"

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for r in self:
            if r.date_to and r.date_from and r.date_to < r.date_from:
                raise ValidationError("Rate %s: date_to is before date_from." % r.key)

    @api.model
    def resolve(self, key, country_id, date, province=None, company_id=None):
        """Return the single most specific active rate record in force on ``date``.

        Precedence (most specific first, first match wins), per RATE_ENGINE.md §2:
            company+province > company > province > country
        """
        company_id = company_id.id if hasattr(company_id, "id") else company_id
        country_id = country_id.id if hasattr(country_id, "id") else country_id
        domain = [
            ("key", "=", key), ("country_id", "=", country_id), ("state", "=", "active"),
            ("date_from", "<=", date),
            "|", ("date_to", "=", False), ("date_to", ">=", date),
        ]
        candidates = self.search(domain)

        def score(rec):
            s = 0
            if rec.company_id:
                if rec.company_id.id != company_id:
                    return None
                s += 4
            if rec.province:
                if rec.province != province:
                    return None
                s += 2
            return s

        scored = [(score(r), r) for r in candidates]
        scored = [(s, r) for s, r in scored if s is not None]
        if not scored:
            return self.browse()
        scored.sort(key=lambda t: t[0], reverse=True)
        return scored[0][1]

    @api.model
    def value_of(self, key, country_id, date, province=None, company_id=None):
        """Resolved value: numeric if set, else the text value. None if the key is unknown."""
        rec = self.resolve(key, country_id, date, province, company_id)
        if not rec:
            return None
        return rec.value_char if rec.value_char else rec.value_num
