from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class PayrollClientOnboard(models.TransientModel):
    """Stand up a new BPO client in minutes, not days (G3): company under the EY parent, its payroll
    config, a structure cloned from a template client, its import profiles, and optionally the first
    monthly cycle — all standard records. The margin-killer for a bureau is ~2 days of clicking per
    client; this is the wizard that removes it."""

    _name = "payroll.client.onboard"
    _description = "Onboard Payroll Client"

    client_name = fields.Char(required=True)
    client_code = fields.Char(required=True, help="Short code, e.g. ITM. Used to prefix employee codes.")
    country_id = fields.Many2one("res.country", required=True)
    currency_id = fields.Many2one("res.currency", required=True)
    parent_company_id = fields.Many2one(
        "res.company", string="Bureau parent",
        default=lambda s: s._default_parent(), help="EY Payroll Services — the BPO umbrella company.")
    template_config_id = fields.Many2one(
        "payroll.client.config", string="Copy setup from",
        help="Existing client whose structure and import profiles are cloned for the new client.")
    lock_structure = fields.Boolean(string="Lock structure on creation", default=True)
    create_first_cycle = fields.Boolean(string="Open first monthly cycle", default=True)
    period = fields.Char(default=lambda s: fields.Date.today().strftime("%Y-%m"))

    @api.model
    def _default_parent(self):
        return self.env["res.company"].search([("name", "=", "EY Payroll Services")], limit=1).id

    def action_onboard(self):
        self.ensure_one()
        parent = self.parent_company_id or self.env["res.company"].search(
            [("name", "=", "EY Payroll Services")], limit=1)
        if not parent:
            parent = self.env["res.company"].create({"name": "EY Payroll Services"})

        company = self.env["res.company"].create({
            "name": self.client_name, "parent_id": parent.id,
            "country_id": self.country_id.id, "currency_id": self.currency_id.id,
        })

        structure = False
        if self.template_config_id and self.template_config_id.structure_id:
            structure = self.template_config_id.structure_id.copy({
                "name": "%s — %s" % (self.client_code, self.template_config_id.structure_id.name),
            })

        config = self.env["payroll.client.config"].create({
            "company_id": company.id, "structure_id": structure and structure.id,
        })

        # Clone import profiles from the template so the client can receive files on day one.
        if self.template_config_id:
            for profile in self.template_config_id.import_profile_ids:
                profile.copy({"client_id": company.id, "name": profile.name.replace(
                    self.template_config_id.company_id.name, self.client_name) if profile.name else profile.name})

        if self.lock_structure and structure:
            config.action_lock_structure()

        if self.create_first_cycle:
            if not structure:
                raise UserError(
                    "Cannot open a cycle without a structure. Pick a template to copy from, or "
                    "create the structure and open the cycle later.")
            start = fields.Date.to_date("%s-01" % self.period)
            self.env["payroll.cycle"].create({
                "config_id": config.id, "period": self.period,
                "date_start": start, "date_end": start + relativedelta(months=1, days=-1),
                "sla_due_date": start + relativedelta(months=1, days=5),
            })

        return {
            "type": "ir.actions.act_window", "name": self.client_name,
            "res_model": "payroll.client.config", "res_id": config.id, "view_mode": "form",
        }
