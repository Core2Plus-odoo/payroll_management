from odoo import fields, models


class PayrollImportProfile(models.Model):
    """A reusable, per-client × doc-type mapping recipe. The ugly client file imports through THIS
    alone — sheet name, header row, column offset, and one mapping line per source column — with zero
    per-file Python (docs/GAP_REGISTER.md G1)."""

    _name = "payroll.import.profile"
    _description = "Payroll Import Profile"

    name = fields.Char(required=True)
    client_id = fields.Many2one("res.company", required=True, string="Client")
    doc_type = fields.Selection(
        [("attendance", "Attendance / OT"), ("payroll_input", "Payroll Input"),
         ("statutory_rate", "Statutory Rates"), ("tax_slab", "Tax Slabs")],
        required=True, default="payroll_input")
    sheet_name = fields.Char(help="Worksheet to read. Empty = first sheet.")
    header_row = fields.Integer(default=1, help="1-based row that holds the column headers.")
    data_start_row = fields.Integer(default=0, help="1-based first data row. 0 = header_row + 1.")
    col_offset = fields.Integer(default=0, help="Columns to skip on the left (FSL data starts at column B -> 1).")
    emp_code_prefix = fields.Char(help="Prefix to normalise short codes, e.g. 'ITM-' turns 007 into ITM-007.")
    period = fields.Char(help="Default period stamped on committed rows, e.g. 2026-06.")
    mapping_line_ids = fields.One2many("payroll.import.mapping.line", "profile_id", string="Column mapping")

    def mapping_dict(self):
        self.ensure_one()
        return {ml.source_header.strip(): ml for ml in self.mapping_line_ids}


class PayrollImportMappingLine(models.Model):
    _name = "payroll.import.mapping.line"
    _description = "Payroll Import Mapping Line"
    _order = "sequence, id"

    profile_id = fields.Many2one("payroll.import.profile", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    source_header = fields.Char(required=True, help="Exact header text in the client file.")
    target_field = fields.Char(
        required=True,
        help="Where it lands: 'emp_code' for the key, or an input code (OT_H, ABSENT_D, BONUS, ...).")
    transform = fields.Selection(
        [("strip", "strip"), ("number_from_text", "number_from_text"),
         ("strip_currency_prefix", "strip_currency_prefix"), ("yn_to_bool", "yn_to_bool"),
         ("clean_iban", "clean_iban"), ("date_dmy", "date_dmy"),
         ("constant", "constant"), ("prefix", "prefix")],
        default="strip", required=True)
    transform_arg = fields.Char(help="Argument for the transform (prefix value, constant value, ...).")


class PayrollMonthlyInput(models.Model):
    """Committed, deduplicated monthly variable inputs per employee/period. The payroll cycle reads
    these onto payslips. The (client, period, emp_code, input_code) tuple is unique — re-importing the
    same file writes the same rows, never duplicates."""

    _name = "payroll.monthly.input"
    _description = "Payroll Monthly Input (committed)"
    _order = "period desc, emp_code, input_code"

    client_id = fields.Many2one("res.company", required=True, index=True)
    period = fields.Char(required=True, index=True)
    emp_code = fields.Char(required=True, index=True)
    input_code = fields.Char(required=True)
    value = fields.Float()

    _sql_constraints = [
        ("uniq_input", "unique(client_id, period, emp_code, input_code)",
         "One value per employee, period and input code — enforced to keep imports idempotent."),
    ]
