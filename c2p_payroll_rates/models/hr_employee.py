from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    payroll_province = fields.Char(
        groups="hr.group_hr_user",
        help="Work province/state used to scope statutory rates (e.g. Sindh, Punjab, ICT). "
             "The rate resolver reads this for province-level overrides such as minimum wage.")
