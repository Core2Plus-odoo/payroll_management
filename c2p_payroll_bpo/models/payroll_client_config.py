from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PayrollClientConfig(models.Model):
    """Per-client BPO setup: which salary structure runs their payroll, which import profiles feed it,
    who owns it — and whether the structure is LOCKED. Locking is the governance gate between
    onboarding and monthly running: once a client's structure is signed off and locked, it cannot be
    silently changed under a running payroll; unlocking is a deliberate, manager-only, audited act."""

    _name = "payroll.client.config"
    _description = "Payroll Client Configuration"
    _inherit = ["mail.thread"]
    _order = "company_id"

    name = fields.Char(compute="_compute_name", store=True)
    company_id = fields.Many2one("res.company", required=True, ondelete="cascade", string="Client")
    country_id = fields.Many2one(related="company_id.country_id", store=True)
    structure_id = fields.Many2one(
        "hr.payroll.structure", string="Payroll Structure", tracking=True,
        help="The salary structure this client's monthly payroll runs on.")
    import_profile_ids = fields.One2many("payroll.import.profile", "client_id", string="Import Profiles")
    officer_ids = fields.Many2many("res.users", string="Assigned Officers")

    structure_locked = fields.Boolean(
        default=False, tracking=True, readonly=True,
        help="When set, the payroll structure is frozen — monthly runs use exactly this structure.")
    locked_by = fields.Many2one("res.users", readonly=True)
    locked_on = fields.Datetime(readonly=True)
    monthly_wage_locked = fields.Boolean(
        string="Freeze base wages", default=False, tracking=True,
        help="When set, employee base wages for this client cannot change without unlocking.")

    cycle_ids = fields.One2many("payroll.cycle", "config_id")
    cycle_count = fields.Integer(compute="_compute_cycle_count")

    @api.depends("company_id")
    def _compute_name(self):
        for c in self:
            c.name = c.company_id.name or "New client"

    def _compute_cycle_count(self):
        for c in self:
            c.cycle_count = len(c.cycle_ids)

    _sql_constraints = [
        ("uniq_company", "unique(company_id)", "Each client company has exactly one payroll config."),
    ]

    # ---------------------------------------------------------------- locking
    def action_lock_structure(self):
        for c in self:
            if not c.structure_id:
                raise UserError("Set a payroll structure before locking %s." % c.company_id.name)
            c.write({"structure_locked": True, "locked_by": self.env.user.id,
                     "locked_on": fields.Datetime.now()})
            c.message_post(body="Payroll structure <b>%s</b> locked." % c.structure_id.name)

    def action_unlock_structure(self):
        if not self.env.user.has_group("c2p_payroll_bpo.group_ey_payroll_manager"):
            raise UserError("Only an EY Payroll Manager may unlock a client's payroll structure.")
        for c in self:
            c.write({"structure_locked": False, "locked_by": False, "locked_on": False})
            c.message_post(body="Payroll structure unlocked for reconfiguration.")

    def write(self, vals):
        # Guard: cannot swap the structure out from under a locked client (RATE_ENGINE-style immutability
        # applied to configuration). Unlock first, deliberately.
        if "structure_id" in vals:
            locked = self.filtered(lambda c: c.structure_locked)
            if locked:
                raise ValidationError(
                    "Cannot change the payroll structure of %s while it is locked. Unlock first."
                    % ", ".join(locked.mapped("company_id.name")))
        return super().write(vals)

    def action_open_cycles(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": "Payroll Cycles",
            "res_model": "payroll.cycle", "view_mode": "kanban,list,form",
            "domain": [("config_id", "=", self.id)],
            "context": {"default_config_id": self.id},
        }

    def action_new_cycle(self):
        self.ensure_one()
        if not self.structure_locked:
            raise UserError(
                "Lock the payroll structure for %s before running a monthly cycle." % self.company_id.name)
        return {
            "type": "ir.actions.act_window", "name": "New Payroll Cycle",
            "res_model": "payroll.cycle", "view_mode": "form",
            "context": {"default_config_id": self.id},
        }
