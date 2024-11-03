from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrShiftVariation(models.Model):
    _name = 'hr.shift.variation'
    _description = 'Shift Variations'

    name = fields.Char('Shift Name')
    shift_code = fields.Char('Shift Code')
    day_type = fields.Selection([('work_day', 'Work Day'),
                                ('day_off', 'Day Off')
                                ], string='Day Type', default="work_day")
    work_from = fields.Float('Work From', default=0)
    work_to = fields.Float('Work To', default=0)
    tolerance_for_late = fields.Float('Tolerance for Late', default=0)
    break_from = fields.Float('Break From', default=0)
    break_to = fields.Float('Break To', default=0)
    minimum_hours = fields.Float(string='Minimum Hours', default=0)
    start_checkin = fields.Float(string='Start Checkin', default=0)
    end_checkout = fields.Float(string='End Checkout', default=0)
    attendance_formula_id = fields.Many2one('hr.attendance.formula', string="Attendance Formula")

    @api.constrains('shift_code')
    def check_shift_code(self):
        for record in self:
            if record.shift_code:
                check_shift_code = self.search([('shift_code', '=', record.shift_code), ('id', '!=', record.id)])
                if check_shift_code:
                    raise ValidationError("Shift Code must be unique!")
    
    @api.onchange('day_type')
    def onchange_day_type(self):
        for rec in self:
            if rec.day_type == "day_off":
                rec.work_from = 0
                rec.work_to = 0
                rec.tolerance_for_late = 0
                rec.break_from = 0
                rec.break_to = 0
                rec.minimum_hours = 0
                rec.start_checkin = 0
                rec.end_checkout = 0
                rec.attendance_formula_id = False