from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    pk_pf_member = fields.Boolean(
        string="Provident Fund Member", groups="hr.group_hr_user",
        help="If set, the PF_EE/PF_ER salary rules apply for this employee. PF is per-member, not universal.")
    pk_cnic = fields.Char(
        string="CNIC", groups="hr.group_hr_user",
        help="Pakistan Computerised National Identity Card number (13 digits).")
