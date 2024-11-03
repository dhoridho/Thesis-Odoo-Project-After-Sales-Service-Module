from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AllocateLeave(models.TransientModel):
    _name = 'allocate.leaves'
    _description = "Allocate Leaves"

    employee_ids = fields.Many2many('hr.employee', 'wiz_emp_rel', 'wiz_al_id',
                                    'emp_id', 'Employees')
    holiday_status_id = fields.Many2one('hr.leave.type', 'Leave Type')
    hr_year_id = fields.Many2one('hr.year', "HR Year")
    no_of_days = fields.Float('No of Days')

    @api.onchange('holiday_status_id')
    def onchange_employee(self):
        self.employee_ids = False

    @api.onchange('holiday_status_id')
    def onchange_holiday_status(self):
        """Onchange Holiday status.

        This method is used to to create domain on employee_ids field
        according to holiday_status_id.
        """
        result = {}
        if self.holiday_status_id:
            employees_ids = self.env['hr.employee'].search([('leave_config_id',
                                                             '!=', False)])
            emp_rec = []
            for emp in employees_ids:
                leave_config = emp.leave_config_id
                line_ids = leave_config.holiday_group_config_line_ids
                leave_rec = [leave.leave_type_id.id for leave in line_ids if leave.leave_type_id] or []
                if self.holiday_status_id.id in leave_rec:
                    emp_rec.append(emp.id)
            result.update({'domain': {'employee_ids': [('id', 'in', emp_rec)]}})
        return result

    def allocate_leaves(self):
        """Allocate leaves.

        This method is used to allocate leave to selected employees.
        """
        leaves = []
        if self.no_of_days == 0.0:
            raise ValidationError(_('Please configure number of days!'))
        if not self.employee_ids:
            raise ValidationError(_('Please select employee!'))
        for emp in self.employee_ids:
            if emp.leave_config_id and emp.leave_config_id.holiday_group_config_line_ids:
                leave_rec = [
                    leave.leave_type_id.id
                    for leave in
                    emp.leave_config_id.holiday_group_config_line_ids if leave.leave_type_id] or []
                if self.holiday_status_id.id in leave_rec:
                    status_name = self.holiday_status_id.name2
                    vals = {
                        'name': 'Assign Default ' + str(status_name),
                        'holiday_status_id': self.holiday_status_id.id,
                        'employee_id': emp.id,
                        'number_of_days': self.no_of_days,
                        'state': 'confirm',
                        'holiday_type': 'employee',
                        'hr_year_id': self.hr_year_id.id,
                    }
                    if self.hr_year_id and self.hr_year_id.period_ids:
                        vals.update({
                            'start_date': self.hr_year_id.period_ids[0].date_start,
                            'end_date': self.hr_year_id.period_ids[0].date_stop
                        })
                    leave_record = self.env['hr.leave.allocation'].create(vals)
                    leaves.append(leave_record.id)
        if leaves:
            return {
                'name': _('Allocated Leaves'),
                'view_mode': 'tree,form',
                'view_id': False,
                'res_model': 'hr.leave.allocation',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', 'in', leaves)]
            }
        return True
