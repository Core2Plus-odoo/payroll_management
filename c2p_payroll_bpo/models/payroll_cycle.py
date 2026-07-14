from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class PayrollCycleStage(models.Model):
    _name = "payroll.cycle.stage"
    _description = "Payroll Cycle Stage"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean()
    is_done = fields.Boolean(string="Closing stage")


class PayrollCycle(models.Model):
    """One client, one period: the control-tower record that tracks where a payroll sits in EY's
    process (G2). It does NOT reimplement batches — it wraps the standard hr.payslip.run and drives it
    through Data Collection -> ... -> Posted -> Closed, with an SLA the bureau is measured on."""

    _name = "payroll.cycle"
    _description = "Payroll Cycle"
    _inherit = ["mail.thread"]
    _order = "date_end desc, company_id"

    name = fields.Char(compute="_compute_name", store=True)
    config_id = fields.Many2one("payroll.client.config", required=True, ondelete="cascade")
    company_id = fields.Many2one(related="config_id.company_id", store=True, string="Client")
    structure_id = fields.Many2one(related="config_id.structure_id")
    period = fields.Char(required=True, help="e.g. 2026-06", default=lambda s: fields.Date.today().strftime("%Y-%m"))
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    stage_id = fields.Many2one("payroll.cycle.stage", group_expand="_read_group_stage_ids",
                               default=lambda s: s.env["payroll.cycle.stage"].search([], limit=1))
    payslip_run_id = fields.Many2one("hr.payslip.run", readonly=True, string="Batch")
    payslip_count = fields.Integer(compute="_compute_stats")
    net_total = fields.Monetary(compute="_compute_stats")
    currency_id = fields.Many2one(related="company_id.currency_id")

    sla_due_date = fields.Date(help="When this client's payroll is contractually due.")
    sla_state = fields.Selection(
        [("on_track", "On track"), ("due_soon", "Due soon"), ("breached", "Breached")],
        compute="_compute_sla", store=True)

    @api.depends("company_id", "period")
    def _compute_name(self):
        for c in self:
            c.name = "%s — %s" % (c.company_id.name or "?", c.period or "?")

    @api.depends("payslip_run_id.slip_ids", "payslip_run_id.slip_ids.net_wage")
    def _compute_stats(self):
        for c in self:
            slips = c.payslip_run_id.slip_ids
            c.payslip_count = len(slips)
            c.net_total = sum(slips.mapped("net_wage")) if slips else 0.0

    @api.depends("sla_due_date", "stage_id.is_done")
    def _compute_sla(self):
        today = fields.Date.today()
        for c in self:
            if c.stage_id.is_done or not c.sla_due_date:
                c.sla_state = "on_track"
            elif c.sla_due_date < today:
                c.sla_state = "breached"
            elif c.sla_due_date <= today + relativedelta(days=2):
                c.sla_state = "due_soon"
            else:
                c.sla_state = "on_track"

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env["payroll.cycle.stage"].search([])

    @api.onchange("period")
    def _onchange_period(self):
        if self.period and len(self.period) == 7:
            year, month = int(self.period[:4]), int(self.period[5:7])
            start = fields.Date.to_date("%04d-%02d-01" % (year, month))
            self.date_start = start
            self.date_end = start + relativedelta(months=1, days=-1)

    # ---------------------------------------------------------------- run the month
    def action_generate_payslips(self):
        """Create the standard batch and a payslip per active employee, on the LOCKED structure,
        pulling committed monthly inputs (from c2p_payroll_import) onto each payslip."""
        self.ensure_one()
        config = self.config_id
        if not config.structure_locked:
            raise UserError("Lock the payroll structure before generating payslips.")
        if self.payslip_run_id:
            raise UserError("This cycle already has a batch. Delete it to regenerate.")

        run = self.env["hr.payslip.run"].create({
            "name": self.name, "date_start": self.date_start, "date_end": self.date_end,
            "company_id": self.company_id.id,
        })
        employees = self.env["hr.employee"].search([
            ("company_id", "=", self.company_id.id), ("contract_date_start", "!=", False)])
        if not employees:
            raise UserError("No employees with a contract/version found for %s." % self.company_id.name)

        inputs_by_emp = self._committed_inputs_by_employee()
        input_types = {t.code: t.id for t in self.env["hr.payslip.input.type"].search([])}
        Payslip = self.env["hr.payslip"]
        for emp in employees:
            version = emp.version_id
            slip = Payslip.create({
                "name": "Salary — %s — %s" % (emp.name, self.period),
                "employee_id": emp.id, "version_id": version.id,
                "struct_id": config.structure_id.id,
                "date_from": self.date_start, "date_to": self.date_end,
                "payslip_run_id": run.id, "company_id": self.company_id.id,
            })
            lines = []
            for code, value in inputs_by_emp.get(emp.barcode, {}).items():
                if code in input_types and value:
                    lines.append((0, 0, {"input_type_id": input_types[code], "amount": value}))
            if lines:
                slip.write({"input_line_ids": lines})
            slip.compute_sheet()
        self.payslip_run_id = run.id
        self._advance_to("Payslips Computed")
        self.message_post(body="Generated and computed %d payslips." % len(employees))

    def _committed_inputs_by_employee(self):
        recs = self.env["payroll.monthly.input"].search([
            ("client_id", "=", self.company_id.id), ("period", "=", self.period)])
        out = {}
        for r in recs:
            out.setdefault(r.emp_code, {})[r.input_code] = r.value
        return out

    def action_recompute(self):
        self.ensure_one()
        self.payslip_run_id.slip_ids.compute_sheet()
        self.message_post(body="Recomputed %d payslips." % len(self.payslip_run_id.slip_ids))

    def action_validate(self):
        self.ensure_one()
        self.payslip_run_id.slip_ids.action_payslip_done()
        self._advance_to("Client Approved")

    def action_post(self):
        self.ensure_one()
        self.payslip_run_id.action_validate() if hasattr(self.payslip_run_id, "action_validate") else None
        self._advance_to("Posted")

    def _advance_to(self, stage_name):
        stage = self.env["payroll.cycle.stage"].search([("name", "=", stage_name)], limit=1)
        if stage:
            self.stage_id = stage.id

    def action_open_batch(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "res_model": "hr.payslip.run",
            "res_id": self.payslip_run_id.id, "view_mode": "form",
        }
