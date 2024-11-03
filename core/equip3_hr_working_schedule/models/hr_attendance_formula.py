from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

DEFAULT_PYTHON_CODE = """# Pastikan 'result' harus ada
# result harus ber-type integer atau float
# variables:
#  - wage (Wage dari contract pada data payslip) 
#  - durasi (Durasi keterlambatan pada data attendance dalam satuan menit)
if durasi <= 30:
    var_pengali = 1
elif durasi > 30 and durasi <= 60:
    var_pengali = 1.5
elif durasi > 60:
    var_pengali = 2
result = (1/173) * wage * var_pengali"""

DEFAULT_PYTHON_CODE_ALW = """# Pastikan 'result' harus ada
# result harus ber-type integer atau float
result = 0"""

class HrAttendanceFormula(models.Model):
    _name = 'hr.attendance.formula'
    _description = 'Hr Attendance Formula'

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)
    formula = fields.Text(
        string="Late Deduction Formula",
        default=DEFAULT_PYTHON_CODE,
        required=True,
        help="Make sure the 'result' is defined and it contains the new current value."
    )
    alw_formula = fields.Text(
        string="Allowance Formula",
        default=DEFAULT_PYTHON_CODE_ALW,
        required=True,
        help="Make sure the 'result' is defined and it contains the new current value."
    )

    @api.constrains('name')
    def check_name(self):
        for rec in self:
            check_name = self.search([('id','!=',rec.id)])
            for item in check_name:
                if item.name.strip().lower() == rec.name.strip().lower():
                    raise ValidationError("Name must be Unique! Please define another name!")
    
    @api.constrains('code')
    def check_code(self):
        for rec in self:
            check_code = self.search([('id','!=',rec.id)])
            for item in check_code:
                if item.code.strip().lower() == rec.code.strip().lower():
                    raise ValidationError("Code must be Unique! Please define another code name!")
    
    def _execute_formula(self, wage, durasi):
        self.ensure_one()
        cxt = {
            'wage': wage,
            'durasi': durasi,
        }
        code = self.formula.strip()
        try:
            safe_eval(code, cxt, mode="exec", nocopy=True)
            result = cxt.get('result')
            if result is None:
                result = _("Computation Error: Python code is incorrect: it doesn't contain 'result' key word")
            elif not isinstance(result, (int, float)):
                result = _(
                    "Computation Error: Python code is incorrect: it returns not number but {}".format(type(result))
                )
        except Exception as e:
            result = _("Computation Error: {}".format(e))
        return result
    
    def _execute_formula_alw(self):
        self.ensure_one()
        cxt = {
        }
        code = self.alw_formula.strip()
        try:
            safe_eval(code, cxt, mode="exec", nocopy=True)
            result = cxt.get('result')
            if result is None:
                result = _("Computation Error: Python code Allowance Formula is incorrect: it doesn't contain 'result' key word")
            elif not isinstance(result, (int, float)):
                result = _(
                    "Computation Error: Python code Allowance Formula is incorrect: it returns not number but {}".format(type(result))
                )
        except Exception as e:
            result = _("Computation Error: {}".format(e))
        return result