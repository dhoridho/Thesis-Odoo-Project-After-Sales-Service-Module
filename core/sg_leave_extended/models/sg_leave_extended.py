import time
from dateutil.relativedelta import relativedelta

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HolidayGroupConfig(models.Model):
    _inherit = "holiday.group.config"

    status_history_ids = fields.One2many('hr.leave.history', 'history_id',
                                         'Holiday Status History')


class HolidayGroupConfigLine(models.Model):
    _inherit = 'holiday.group.config.line'

    @api.constrains('increment_count', 'increment_number')
    def _check_increment_count(self):
        """
            This Method is restrict the system that not configure negative
            values for Interval Number and  Number of Calls.
        """
        for rec in self:
            if rec.increment_count < 0 or rec.increment_number < 0:
                raise ValidationError(
                    _('Please set Interval Number or Number of Calls properly.!'))

    increment_count = fields.Integer('Interval Number', help="Repeat every x.")
    status_history_ids = fields.One2many(
        'hr.leave.history', 'history_id', 'Holiday Status History')
    increment_number = fields.Integer(
        'Number of Calls', help='How many times the allocation is schedule.')
    execution_date = fields.Date(
        "Execution Date", default=lambda *a: time.strftime(DSDF),
        help="A start date from where the leave allocation is schedule.")
    last_execution_date = fields.Date(
        "Last Execution Date",
        help="Last date from where the leave allocation is stable.")
    inc_leave_per_freq = fields.Integer(
        "Increment Leave Per Frequency",
        help='Increase Number of leave for every Interval Unit.')
    last_increment_number = fields.Integer(
        'Last Interval Number', help="Last leave amount from where the leave \
        allocation is stable.")
    increment_frequency = fields.Selection([
        ('month', 'Month'), ('year', 'Year')], string="Interval Unit",
        help='Unit of Interval.', default="year")

    def validate_leaves(self):
        """
            This Method is used to create Leave History on a
            Given leave allocation Configurations.
        """
        job_history_obj = self.env['hr.leave.history']
        for leave_rec in self:
            if leave_rec.execution_date:
                curr_date = leave_rec.execution_date
            else:
                raise ValidationError(_('Please Configure Execution Date.'))
            default_leave = leave_rec.default_leave_allocation
            if leave_rec.status_history_ids and leave_rec.status_history_ids.ids:
                leave_rec.status_history_ids.unlink()
            for incr in range(leave_rec.increment_number + 1):
                if leave_rec.increment_frequency == 'year':
                    if incr == 0:
                        history_detail = {
                            'increment_count': leave_rec.increment_count,
                            'increment_number': default_leave,
                            'history_id': leave_rec.id,
                            'start_date': curr_date,
                        }
                    else:
                        default_leave = leave_rec.default_leave_allocation + (incr * leave_rec.inc_leave_per_freq)
                        curr_date = curr_date + relativedelta(years=leave_rec.increment_count)
                        history_detail = {
                            'increment_count': leave_rec.increment_count,
                            'increment_number': default_leave,
                            'history_id': leave_rec.id,
                            'start_date': curr_date,
                        }
                    job_history_obj.create(history_detail)
                if leave_rec.increment_frequency == 'month':
                    if incr == 0:
                        history_detail = {
                            'increment_count': leave_rec.increment_count,
                            'increment_number': leave_rec.default_leave_allocation,
                            'history_id': leave_rec.id,
                            'start_date': curr_date,
                        }
                    else:
                        default_leave = leave_rec.default_leave_allocation + (incr * leave_rec.inc_leave_per_freq)
                        curr_date = curr_date + relativedelta(months=leave_rec.increment_count)
                        history_detail = {
                            'increment_count': leave_rec.increment_count,
                            'increment_number': default_leave,
                            'history_id': leave_rec.id,
                            'start_date': curr_date,
                        }
                    job_history_obj.create(history_detail)
            leave_rec.write({
                'last_execution_date': curr_date,
                'last_increment_number': default_leave})
        return True


class HRLeaveHistory(models.Model):
    _name = 'hr.leave.history'
    _description = "Hr Leave History"

    @api.constrains('start_date')
    def _check_leave_history_date(self):
        for leave_status in self:
            nholidays = self.search_count([
                ('start_date', '=', leave_status.start_date),
                ('history_id', '=', leave_status.history_id.id)])
            if nholidays > 1:
                raise ValidationError(
                    "You can not generate same holiday status history for "
                    "leave type '%s'." % (
                        leave_status.history_id.leave_type_id.name2))
        return True

    history_id = fields.Many2one('holiday.group.config.line', 'History')
    start_date = fields.Date("Date", help="Start Date Of leave History.")
    increment_count = fields.Integer(
        "Increment Count", help="Number of allocation leaves.")
    increment_number = fields.Integer(
        "Increment Leave", help="Total number of allocation leaves.")
    done_bol = fields.Boolean(
        "Complete", help="It's True when allocation is completed on given date.")


class hr_holidays(models.Model):

    _inherit = "hr.leave"

    @api.model
    def assign_annual_other_leaves(self):
        '''
        This method will be called by scheduler which will assign
        Annual Marriage,Compassionate,Infant care,Child care,
        Extended child care,Paternity leaves at end of the year.
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current User Id
        @param context : Standard Dictionary
        @return: Return the True
        ----------------------------------------------------------
        '''
        emp_obj = self.env['hr.employee']
        today = time.strftime(DSDF)
        curr_hr_year_id = self.fetch_hryear(today)
        empl_ids = emp_obj.search([('active', '=', True),
                                   ('leave_config_id', '!=', False)])

        for employee in empl_ids:
            if employee.leave_config_id and employee.leave_config_id.holiday_group_config_line_ids:
                for holiday in employee.leave_config_id.holiday_group_config_line_ids:
                    tot_allocation_leave = holiday.default_leave_allocation
                    if employee.user_id and employee.user_id.id == 1:
                        continue
                    add = 0.0
                    self._cr.execute("""SELECT
                                            sum(number_of_days)
                                        FROM
                                            hr_leave_allocation
                                        where
                                            employee_id=%d and
                                            state='validate' and
                                            holiday_status_id = %d
                                    """ % (employee.id,
                                           holiday.leave_type_id.id))
                    all_datas = self._cr.fetchone()
                    if all_datas and all_datas[0]:
                        add += all_datas[0]
                    if add > 0.0:
                        continue
                    if holiday.leave_type_id.name in ['PL', 'SPL'] and \
                            employee.gender != 'male':
                        continue
                    if holiday.leave_type_id.name == 'PCL' and \
                            employee.singaporean is not True:
                        continue
                    if holiday.status_history_ids and \
                            holiday.status_history_ids.ids:
                        for holiday_status in holiday.status_history_ids:
                            if today == holiday_status.start_date and \
                                    holiday_status.done_bol is False:
                                tot_allocation_leave = holiday_status.increment_number
                                if tot_allocation_leave > 0:
                                    leave_dict = {
                                        'name': 'Assign Default ' + str(
                                            holiday.leave_type_id.name2),
                                        'employee_id': employee.id,
                                        'holiday_type': 'employee',
                                        'holiday_status_id':
                                            holiday.leave_type_id.id,
                                        'number_of_days':
                                            tot_allocation_leave,
                                        'hr_year_id': curr_hr_year_id,
                                    }
                                    self.env['hr.leave.allocation'
                                             ].create(leave_dict)
                                    holiday_status.write({'done_bol': True})
                    else:
                        if tot_allocation_leave > 0:
                            leave_dict = {
                                'name': 'Assign Default ' + str(
                                    holiday.leave_type_id.name2),
                                'employee_id': employee.id,
                                'holiday_type': 'employee',
                                'holiday_status_id':
                                    holiday.leave_type_id.id,
                                'number_of_days': tot_allocation_leave,
                                'hr_year_id': curr_hr_year_id,
                            }
                            self.env['hr.leave.allocation'].create(leave_dict)
        return True
