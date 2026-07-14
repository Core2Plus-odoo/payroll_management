from odoo import fields, models


class PayrollRateChange(models.Model):
    """Immutable audit of every statutory-rate / slab change: who, when, what, on whose authority,
    why, and the measured impact (RATE_ENGINE.md §2 Gap C — the shape of sheet 12_rate_change_log).
    When a client asks 'why is my March tax different from February?', this table is the answer."""

    _name = "payroll.rate.change"
    _description = "Payroll Rate Change (audit)"
    _order = "changed_at desc"

    changed_at = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    changed_by = fields.Many2one("res.users", default=lambda s: s.env.user, readonly=True)
    model_touched = fields.Char(string="Table")
    record_ref = fields.Char(string="Record")
    change = fields.Char()
    effective_from = fields.Date()
    approved_by = fields.Char()
    reason = fields.Text(required=True)
    impact = fields.Text()
