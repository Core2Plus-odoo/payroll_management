from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    assigned_client_ids = fields.Many2many(
        "res.company", "res_users_assigned_client_rel", "user_id", "company_id",
        string="Assigned Clients",
        help="Companies an EY Payroll Officer may act on. Enforced by ir.rule, not by hiding menus.")
