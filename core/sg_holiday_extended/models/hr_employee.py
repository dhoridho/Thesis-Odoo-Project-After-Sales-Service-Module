
import time
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    dependent_ids = fields.One2many('dependents', 'employee_id', 'Dependents')
    leave_config_id = fields.Many2one('holiday.group.config',
                                      'Leave Structure',
                                      help="Structure of Leaves")
    depends_singaporean = fields.Boolean('Depends are Singaporean',
                                         help='Checked if depends are \
                                         Singaporean')
    leave_all_bool = fields.Boolean('For Invisible Allocate Leave Button')

    def allocate_leaves_mannualy(self):
        """Allocated leaves manually.

        This Allocate Leaves button method will assign annual leaves from
        employee form view.
        @param self : Object Pointer
        @return: Return the True
        """
        holiday_obj = self.env['hr.leave.allocation']
        date_today = datetime.today()
        year = date_today.year
        curr_year_date = str(year) + '-01-01'
        curr_year_date = datetime.strptime(curr_year_date, DSDF)
        for employee in self:
            holiday_config = employee.leave_config_id
            holiday_config_line = holiday_config.holiday_group_config_line_ids or []
            for holiday in holiday_config_line:
                tot_allocation_leave = holiday.default_leave_allocation
                if tot_allocation_leave == 0.0:
                    continue
                if employee.user_id and employee.user_id.id == 1:
                    continue
                add = 0.0
                self.env.cr.execute("""SELECT sum(number_of_days)
                FROM hr_leave_allocation where employee_id=%d and
                state='validate' and holiday_status_id = %d""" % (
                    employee.id, holiday.leave_type_id.id))
                all_datas = self.env.cr.fetchone()
                if all_datas and all_datas[0]:
                    add += all_datas[0]
                if add > 0.0:
                    continue
                curr_year_date_only = curr_year_date.strftime(DSDF)
                if holiday.leave_type_id.name == 'AL' and str(
                        employee.join_date) > str(curr_year_date_only):
                    join_month = datetime.strptime(
                        employee.join_date.strftime(DSDF),
                        DSDF).month
                    remaining_months = 12 - int(join_month)
                    if remaining_months:
                        tot_allocation_leave = (
                            float(tot_allocation_leave) / 12) \
                            * remaining_months
                        tot_allocation_leave = round(
                            tot_allocation_leave)
                if holiday.leave_type_id.name in ['PL', 'SPL'] and \
                        employee.gender != 'male':
                    continue
                if holiday.leave_type_id.name == 'PCL' and \
                        employee.singaporean is not True:
                    continue
#                emp_leave_ids = [leave.leave_type_id.id for leave in holiday_config_line if leave.leave_type_id]
                if employee.leave_config_id.holiday_group_config_line_ids:
                    if holiday.leave_type_id.name == 'AL' and \
                        str(employee.join_date) < str(curr_year_date_only):
                        join_year = datetime.strptime(
                            employee.join_date.strftime(DSDF), DSDF).year
                        tot_year = year - join_year
                        if holiday.incr_leave_per_year != 0 and tot_year != 0:
                            tot_allocation_leave += (
                                holiday.incr_leave_per_year *
                                tot_year)
                    if holiday.max_leave_kept != 0 and \
                        tot_allocation_leave > holiday.max_leave_kept:
                        tot_allocation_leave = holiday.max_leave_kept
                    leave_dict = {
                        'name': 'Assign Default ' +
                        str(holiday.leave_type_id.name),
                        'employee_id': employee.id,
                        'holiday_type': 'employee',
                        'holiday_status_id': holiday.leave_type_id.id,
                        'number_of_days': tot_allocation_leave,
                    }
                    holiday_obj.create(leave_dict)
            employee.write({'leave_all_bool': True})
        return True

    @api.model
    def cessation_date_deadline(self):
        """Cessation Date deadline.

        This method is called when scheduler to change employee's state from
        notice period/terminate to Inactive who are in notice period or
        terminate.
        """
        today = datetime.today().date().strftime(DSDF)
        employee_ids = self.search([
            ('cessation_date', '<', today),
            ('emp_status', 'in', ['terminated', 'in_notice'])])
        if employee_id and employee_ids:
            employee_id.write({'emp_status': 'inactive', 'active': False})
        return True

    def _compute_leaves_count(self):
        today = time.strftime(DSDF)
        current_hr_year_id = self.env['hr.leave'].fetch_hryear(today)
        leaves = self.env['hr.leave'].read_group([
            ('employee_id', 'in', self.ids),
            ('state', '=', 'validate'),
            ('hr_year_id', '=', current_hr_year_id),
        ], fields=['number_of_days', 'employee_id'], groupby=['employee_id'])
        mapping = dict([(leave['employee_id'][0], leave['number_of_days'])
                        for leave in leaves])
        for employee in self:
            employee.leaves_count = mapping.get(employee.id)

    def copy(self, default=None):
        emp = super(HrEmployee, self).copy(default=default)
        emp['leave_all_bool'] = False
        return emp

    @api.onchange('emp_status')
    def onchange_emp_status(self):
        if self.emp_status == 'inactive':
            self.active = False
        else:
            self.active = True
            self.cessation_date = False


class Dependents(models.Model):
    _name = 'dependents'
    _description = "Employee Depends"

    employee_id = fields.Many2one('hr.employee', 'Employee ID')
    first_name = fields.Char('First Name')
    last_name = fields.Char('Last Name')
    birth_date = fields.Date('Birth Date')
    relation_ship = fields.Selection([('son', 'Son'),
                                      ('daughter', 'Daughter'),
                                      ('father', 'Father'),
                                      ('mother', 'Mother')],
                                     string='Relationship')
    email = fields.Char('Email')
    identification_number = fields.Integer('Identification Number')
    contact_number = fields.Char('Contact Number')

    @api.constrains('birth_date')
    def _check_dependent_birthday(self):
        for rec in self:
            today = time.strftime(DSDF)
            if rec.birth_date.strftime(DSDF) >= today:
                raise ValidationError(_(
                    "Please enter valid birthday for dependent"))


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    half_day = fields.Boolean('Half Day')
