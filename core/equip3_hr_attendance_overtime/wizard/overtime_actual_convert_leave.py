from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
import pytz
from odoo.tools.safe_eval import safe_eval

class HrOvertimeActualConvertLeave(models.TransientModel):
    _name = 'hr.overtime.actual.convert.leave'

    overtime_id = fields.Many2one('hr.overtime.actual')
    state = fields.Char(related='overtime_id.overtime_wizard_state')
    request_type = fields.Selection(related='overtime_id.request_type')
    leave_type = fields.Many2one('hr.leave.type', string="Leave Type", domain=[('leave_method', 'in', ['none']),('overtime_extra_leave', '=', True)])
    durations = fields.Float('Durations')
    effective_date = fields.Date('Effective Date', default=fields.Date.context_today)

    # @api.onchange('leave_type')
    # def onchange_leave_type(self):
    #     for res in self:
    #         if res.leave_type and res.leave_type.overtime_extra_leave == False:
    #             raise ValidationError(_("Selected leave types not allow to overtime extra leave"))

    @api.onchange('overtime_id', 'leave_type')
    def onchange_overtime_id(self):
        for res in self:
            if res.leave_type and res.overtime_id:
                res.durations = 0.0
                formula = res.leave_type.formula
                if res.leave_type.total_actual_hours:
                    localdict = {"actual_hours": res.overtime_id.total_actual_hours,"duration": 0.0}
                    safe_eval(formula, localdict, mode='exec', nocopy=True)
                    res.durations = localdict['duration']
                else:
                    total_duration = 0.0
                    for line in res.overtime_id.actual_line_ids:
                        localdict = {"actual_hours": line.actual_hours,"duration": 0.0}
                        safe_eval(formula, localdict, mode='exec', nocopy=True)
                        total_duration += localdict['duration']
                    res.durations = total_duration

    def save(self):
        line_date = []
        if self.leave_type:
            if self.leave_type.allocation_type != 'fixed_allocation':
                if not self.leave_type.responsible_id:
                    raise ValidationError(f"Responsible not set in leave types {self.leave_type.name}")
                line_data = [(0, 0, {'user_ids': [(4, self.leave_type.responsible_id.id)]})]
            elif self.leave_type.allocation_type == 'fixed_allocation':
                if self.leave_type.allocation_validation_type == 'hr':
                    if not self.leave_type.responsible_id:
                        raise ValidationError(f"Responsible not set in leave types {self.leave_type.name}")
                    line_data = [(0, 0, {'user_ids': [(4, self.leave_type.responsible_id.id)]})]
                if self.leave_type.allocation_validation_type == 'manager':
                    if not self.overtime_id.employee_id.parent_id:
                        raise ValidationError(f"Manager not set in Employee {self.overtime_id.employee_id.name}")
                    if not self.overtime_id.employee_id.parent_id.user_id:
                        raise ValidationError(f"User not set in Employee {self.overtime_id.employee_id.parent_id.name}")
                    line_data = [(0, 0, {'user_ids': [(4, self.overtime_id.employee_id.parent_id.user_id.id)]})]
                if self.leave_type.allocation_validation_type == 'both':
                    if not self.overtime_id.employee_id.parent_id:
                        raise ValidationError(f"Manager not set in Employee {self.overtime_id.employee_id.name}")
                    if not self.overtime_id.employee_id.parent_id.user_id:
                        raise ValidationError(f"User not set in Employee {self.overtime_id.employee_id.parent_id.name}")
                    if not self.leave_type.responsible_id:
                        raise ValidationError(f"Responsible not set in leave types {self.leave_type.name}")
                    line_data = [(0, 0, {'user_ids': [(4, self.overtime_id.employee_id.parent_id.user_id.id)]})]
                    line_data.append((0, 0, {'user_ids': [(4, self.leave_type.responsible_id.id)]}))
        if self.request_type == 'by_employee':
            leave_allocation = self.env['hr.leave.allocation'].create({
                                    'name': self.leave_type.name + ' Allocation',
                                    'employee_id': self.overtime_id.employee_id.id,
                                    'department_id': self.overtime_id.employee_id.department_id.id,
                                    'holiday_status_id': self.leave_type.id,
                                    'allocation_type_by': 'overtime',
                                    'overtime_id': self.overtime_id.id,
                                    'number_of_days': self.durations,
                                    'effective_date': self.effective_date,
                                    'state': 'validate',
                                    # 'approver_user_ids': line_data
                                })
            leave_balance_active = self.env['hr.leave.balance'].search([('employee_id', '=', leave_allocation.employee_id.id),
                                                                    ('holiday_status_id', '=', leave_allocation.holiday_status_id.id),
                                                                    ('current_period', '=', date.today().year),
                                                                    ('active', '=', True)], limit=1)
            if leave_balance_active:
                if leave_allocation.holiday_status_id.repeated_allocation == True:
                    assigned = leave_balance_active.assigned + leave_allocation.number_of_days_display
                    leave_balance_active.write({'assigned': assigned})
            else:
                self.env['hr.leave.balance'].create({'employee_id': leave_allocation.employee_id.id,
                                                    'holiday_status_id': leave_allocation.holiday_status_id.id,
                                                    'assigned': leave_allocation.number_of_days_display,
                                                    'current_period': date.today().year,
                                                    'start_date': date.today(),
                                                    'hr_years': date.today().year,
                                                    'description': "Leave Allocation Request"
                                                    })
            self.env['hr.leave.count'].create({'employee_id': leave_allocation.employee_id.id,
                                            'holiday_status_id': leave_allocation.holiday_status_id.id,
                                            'count': leave_allocation.number_of_days_display,
                                            'expired_date': date.today() + timedelta(
                                                days=int(leave_allocation.holiday_status_id.expiry_days)),
                                            'start_date': leave_allocation.effective_date,
                                            'hr_years': date.today().year,
                                            'description': "Leave Allocation Request"
                                            })
        elif self.request_type == 'by_manager':
            for emp in self.overtime_id.employee_ids.ids:
                employee_data = self.env['hr.employee'].browse(emp)
                formula = self.leave_type.formula
                if self.leave_type.total_actual_hours:
                    total_actual_hours = 0.0
                    for line in self.overtime_id.actual_line_ids:
                        if line.employee_id == employee_data:
                            total_actual_hours += line.actual_hours
                    localdict = {"actual_hours": total_actual_hours,"duration": 0.0}
                    safe_eval(formula, localdict, mode='exec', nocopy=True)
                    total_duration = localdict['duration']
                else:
                    total_duration = 0.0
                    for line in self.overtime_id.actual_line_ids:
                        if line.employee_id == employee_data:
                            localdict = {"actual_hours": line.actual_hours,"duration": 0.0}
                            safe_eval(formula, localdict, mode='exec', nocopy=True)
                            total_duration += localdict['duration']
                leave_allocation = self.env['hr.leave.allocation'].create({
                                        'name': self.leave_type.name + ' Allocation',
                                        'employee_id': employee_data.id,
                                        'department_id': employee_data.department_id.id,
                                        'holiday_status_id': self.leave_type.id,
                                        'allocation_type_by': 'overtime',
                                        'overtime_id': self.overtime_id.id,
                                        'number_of_days': total_duration,
                                        'effective_date': self.effective_date,
                                        'state': 'validate',
                                        # 'approver_user_ids': line_data
                                    })
                leave_balance_active = self.env['hr.leave.balance'].search([('employee_id', '=', leave_allocation.employee_id.id),
                                                                        ('holiday_status_id', '=', leave_allocation.holiday_status_id.id),
                                                                        ('current_period', '=', date.today().year),
                                                                        ('active', '=', True)], limit=1)
                if leave_balance_active:
                    if leave_allocation.holiday_status_id.repeated_allocation == True:
                        assigned = leave_balance_active.assigned + leave_allocation.number_of_days_display
                        leave_balance_active.write({'assigned': assigned})
                else:
                    self.env['hr.leave.balance'].create({'employee_id': leave_allocation.employee_id.id,
                                                        'holiday_status_id': leave_allocation.holiday_status_id.id,
                                                        'assigned': leave_allocation.number_of_days_display,
                                                        'current_period': date.today().year,
                                                        'start_date': date.today(),
                                                        'hr_years': date.today().year,
                                                        'description': "Leave Allocation Request"
                                                        })
                self.env['hr.leave.count'].create({'employee_id': leave_allocation.employee_id.id,
                                                'holiday_status_id': leave_allocation.holiday_status_id.id,
                                                'count': leave_allocation.number_of_days_display,
                                                'expired_date': date.today() + timedelta(
                                                    days=int(leave_allocation.holiday_status_id.expiry_days)),
                                                'start_date': leave_allocation.effective_date,
                                                'hr_years': date.today().year,
                                                'description': "Leave Allocation Request"
                                                })
        self.overtime_id.write({'state': 'convert_as_leave'})
