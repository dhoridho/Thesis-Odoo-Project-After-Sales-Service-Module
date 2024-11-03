from odoo import api, fields, models, _
from datetime import date, timedelta
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
from odoo.addons.hr_holidays.models.hr_leave import HolidaysRequest

class HrLeaveReplace(models.Model):
    _inherit = 'hr.leave'

    @api.model
    def create(self, vals):
        sequence_no = self.env['ir.sequence'].next_by_code('hr.leave')
        vals.update({'seq_name': sequence_no})
        result = super(HrLeaveReplace, self).create(vals)
        return result

    def write(self, values):
        employee_id = values.get('employee_id', False)
        if not self.env.context.get('leave_fast_create'):
            if values.get('state'):
                self._check_approval_update(values['state'])
                if any(holiday.validation_type == 'both' for holiday in self):
                    if values.get('employee_id'):
                        employees = self.env['hr.employee'].browse(values.get('employee_id'))
                    else:
                        employees = self.mapped('employee_id')
                    self._check_double_validation_rules(employees, values['state'])
            if 'date_from' in values:
                values['request_date_from'] = values['date_from']
            if 'date_to' in values:
                values['request_date_to'] = values['date_to']
        result = super(HolidaysRequest, self).write(values)
        if not self.env.context.get('leave_fast_create'):
            for holiday in self:
                if employee_id:
                    holiday.add_follower(employee_id)
        return result