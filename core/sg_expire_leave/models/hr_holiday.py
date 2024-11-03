from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models


class HolidaysRequest(models.Model):
    _inherit = 'hr.leave'

    def expire_annual_leave_allocation(self):
        """Expired annual leave allocation and leave request.

        This method will be called by scheduler which will extra annual
        leave expire and current year of annual leave approved on end of the
        year i.e YYYY/04/01 00:00:00.

        @self : Object Pointer
        @return: Return the True or False
        ----------------------------------------------------------------------
        """
        today = datetime.today().date()
        current_year = today.year
        current_hr_year_id = self.fetch_hryear(today)
        curr_year_start_date = today + relativedelta(
            day=1, month=1, year=current_year)
        curr_year_end_date = today + relativedelta(
            day=31, month=3, year=current_year)

        user_brw = self.env.user
        if user_brw.company_id.carry_forward_end_date:
            curr_year_end_date = user_brw.company_id.carry_forward_end_date
            if curr_year_end_date:
                curr_year_end_date = curr_year_end_date + \
                    relativedelta(year=current_year)
        empl_ids = self.env['hr.employee'].search([
            ('leave_config_id', '!=', False)])
        leave_allocation_obj = self.env['hr.leave.allocation']
        for employee in empl_ids:
            lines = employee.leave_config_id.holiday_group_config_line_ids
            holiday_status_ids = [line.leave_type_id for line in lines
                                  if line.carryover in ('up_to', 'unlimited')]
            for holiday_status_rec in holiday_status_ids:
                carry_leave_allocation_ids = leave_allocation_obj.search(
                    [('employee_id', '=', employee.id),
                     ('state', '=', 'validate'),
                     ('carry_forward', '=', True),
                     ('holiday_status_id', '=', holiday_status_rec.id),
                     ('hr_year_id', '=', current_hr_year_id)])

                #  Get current year leave request
                rmv_holiday_ids = self.search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id', '=', holiday_status_rec.id),
                    ('state', '=', 'validate'),
                    ('hr_year_id', '=', current_hr_year_id),
                    ('date_from', '>=', curr_year_start_date),
                    ('date_to', '<=', curr_year_end_date)])
                # Get partial leave which is start in
                # previous year but end in current year
                # like 28-12-2019 to 03-01-2020
                # so get that leave and separatr both leave by year like:
                # 28-12-2019 to 31-12-2019 and 01-01-2020 to 03-01-2020
                rmv_prtl_holiday_ids = self.search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id', '=', holiday_status_rec.id),
                    ('state', '=', 'validate'),
                    ('hr_year_id', '=', current_hr_year_id),
                    ('date_from', '<=', curr_year_end_date),
                    ('date_to', '>=', curr_year_end_date)])
                for holiday_prtl_rmv_rec in rmv_prtl_holiday_ids:
                    total_amount = holiday_prtl_rmv_rec.number_of_days
                    curr_year_end_datetime = curr_year_end_date + \
                        relativedelta(hour=3, minute=30)
                    next_year_prtl_leave_start_date = \
                        curr_year_end_datetime + \
                        relativedelta(days=1)
                    leave_config_id = holiday_prtl_rmv_rec.leave_config_id
                    ttl_amt_before = holiday_prtl_rmv_rec.\
                        _check_holiday_to_from_dates(
                            holiday_prtl_rmv_rec.date_from,
                            curr_year_end_datetime,
                            holiday_prtl_rmv_rec.employee_id.id)
                    if ttl_amt_before.get('days') == \
                            holiday_prtl_rmv_rec.number_of_days:
                        holiday_prtl_rmv_rec.write({'leave_expire': True})
                    elif ttl_amt_before.get('days') < \
                            holiday_prtl_rmv_rec.number_of_days:
                        total_amount_days = total_amount - \
                            ttl_amt_before.get('days')
                        leave_dict = {
                            'name': holiday_prtl_rmv_rec.name or False,
                            'employee_id': employee.id,
                            'holiday_type': 'employee',
                            'holiday_status_id': holiday_status_rec.id,
                            'number_of_days': total_amount_days or 0.0,
                            'hr_year_id': current_hr_year_id or False,
                            'request_date_from':
                            next_year_prtl_leave_start_date.date(),
                            'state': 'confirm',
                            'request_date_to':
                            holiday_prtl_rmv_rec.date_to.date(),
                            'date_from': next_year_prtl_leave_start_date,
                            'date_to': holiday_prtl_rmv_rec.date_to,
                            'leave_config_id': leave_config_id.id or False,
                            'leave_expire': False,
                        }
                        holiday_prtl_rmv_rec.state = 'confirm'
                        curr_year_end_date = curr_year_end_date + \
                            relativedelta(hour=12, minute=30)
                        prtl_rmv_dict = {
                            'leave_expire': True,
                            'date_to': curr_year_end_date,
                            'request_date_to': curr_year_end_date.date(),
                        }
                        holiday_prtl_rmv_rec.write(prtl_rmv_dict)
                        holiday_prtl_rmv_rec._onchange_leave_dates()
                        holiday_prtl_rmv_rec.action_approve()
                        new_holiday_create = self.create(leave_dict)
                        new_holiday_create._onchange_leave_dates()
                        new_holiday_create.action_approve()
                if carry_leave_allocation_ids:
                    carry_leave_allocation_ids.write({'leave_expire': True})
                if rmv_holiday_ids:
                    rmv_holiday_ids.write({'leave_expire': True})
        return True
