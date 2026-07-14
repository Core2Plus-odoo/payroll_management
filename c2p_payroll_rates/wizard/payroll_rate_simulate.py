from odoo import fields, models
from odoo.exceptions import UserError


class PayrollRateSimulate(models.TransientModel):
    """Draft → Simulate → Approve → Activate (RATE_ENGINE.md §4).

    Simulate recomputes a period's tax under a DRAFT slab version into a scratch calculation and
    reports the diff per batch — live payslips are never touched. This is the feature that wins the
    room on budget day: load the proposed Finance Act in the morning, tell every client what it costs
    them by lunchtime.
    """

    _name = "payroll.rate.simulate"
    _description = "Simulate a draft tax-slab version against a live batch"

    draft_version_id = fields.Many2one(
        "payroll.tax.slab.version", required=True, domain=[("state", "=", "draft")])
    payslip_run_id = fields.Many2one("hr.payslip.run", required=True, string="Batch to simulate against")
    result_summary = fields.Text(readonly=True)

    def action_simulate(self):
        self.ensure_one()
        draft = self.draft_version_id
        slabs = self.env["payroll.tax.slab.version"]
        n, delta_tax, crossers = 0, 0.0, 0
        for slip in self.payslip_run_id.slip_ids:
            taxable_line = slip.line_ids.filtered(lambda l: l.code == "TAXABLE_ANNUAL")
            if not taxable_line:
                continue
            annual = taxable_line[0].total
            current_tax = slip.slab_tax(annual) if hasattr(slip, "slab_tax") else 0.0
            draft_tax = self._tax_under(draft, annual)
            n += 1
            delta_tax += (draft_tax - current_tax) / 12.0
            if abs(draft_tax - current_tax) > 0.005:
                crossers += 1
        if not n:
            raise UserError(
                "No payslip in this batch carries a TAXABLE_ANNUAL line — nothing to simulate.")
        sign = "+" if delta_tax <= 0 else "-"  # more tax = less net
        self.result_summary = (
            "SIMULATION ONLY — no live payslip changed.\n\n"
            "Batch: %s (%d payslips)\n"
            "Draft slab version: %s\n\n"
            "Net pay impact: %s%.0f / month total\n"
            "Employees whose tax changes: %d"
            % (self.payslip_run_id.name, n, draft.name, sign, abs(delta_tax), crossers))
        return {
            "type": "ir.actions.act_window", "res_model": self._name, "res_id": self.id,
            "view_mode": "form", "target": "new",
        }

    def _tax_under(self, version, annual):
        for b in version.line_ids.sorted("lower_limit"):
            upper = b.upper_limit or float("inf")
            if b.lower_limit < annual <= upper:
                return b.base_tax + (annual - b.lower_limit) * b.rate_on_excess
        return 0.0
