import pytz
import time

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import _, api, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF, \
    DEFAULT_SERVER_DATETIME_FORMAT as DSDTF


class HrHolidays(models.Model):
    _inherit = "hr.leave"

    @api.constrains('employee_id')
    def _check_cessation_date_for_leave(self):
        """
        The method used to check cessation date before Leave request.
        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        for rec in self:
            if rec.date_from and rec.date_to and rec.employee_id.cessation_date:
                start_date = rec.date_from.date()
                end_date = rec.date_to.date()
                c_date = rec.employee_id.cessation_date
                if (start_date <= c_date <= end_date or
                        c_date < start_date or c_date < end_date):
                    raise ValidationError(_(
                        'You can not request a leave over your cessation date!'))

    @api.constrains('holiday_status_id', 'employee_id', 'date_from', 'date_to')
    def _check_employee_leave(self):
        """
        This constraint method use to check that if the leave type pre_approved
        is true and check the days before request for leave is satisfied with
        no_of_days or not.
        """

        for rec in self:
            if rec.holiday_status_id.pre_approved and rec.date_from:
                from_date = rec.date_from.date()
                ttl_days = rec.holiday_status_id.no_of_days
                qualify_date = from_date - relativedelta(days=ttl_days)
                if qualify_date < datetime.today().date():
                    raise ValidationError(_('You have to apply '
                                            'leave before %s days!' % ('%.2f' %(
                                                rec.holiday_status_id.no_of_days))))

    @api.constrains('holiday_status_id', 'employee_id')
    def _check_sg_maternity_leave_16_weeks(self):
        """
        The method used to Validate for Maternity Leave.
        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        curr_date = datetime.today().date()
        for rec in self:
            if rec.holiday_status_id.name in ['ML16', 'ML15', 'ML8', 'ML4']:
                if rec.holiday_status_id.pre_approved:
                    if rec.employee_id and rec.employee_id.join_date:
                        if rec.employee_id.singaporean and \
                                rec.employee_id.depends_singaporean:
                            joining_date = rec.employee_id.join_date
                            qualify_date = joining_date + relativedelta(months=3)
                            if curr_date < qualify_date:
                                raise ValidationError(_(
                                    'Not Qualified in Joining date! \n '
                                    'Employee must have worked in the company for '
                                    'a continuous duration of at least 3 months!'))
                            if rec.date_from:
                                from_date = rec.date_from.date()
                                two_month_date = from_date - relativedelta(months=2)
                                if two_month_date < curr_date:
                                    raise ValidationError(_(
                                        'Warning! \n '
                                        'Maternity Leave request should '
                                        'be submitted 2 months prior to '
                                        'the requested date.!'))
                        else:
                            raise ValidationError(_(
                                'Warning! \n Child is not Singapore citizen!'))
                    else:
                        raise ValidationError(_(
                            'You are not able to apply Request '
                            'for this Maternity leave!'))

    @api.constrains('date_from', 'date_to', 'hr_year_id')
    def _check_current_year_leave_req(self):
        """
        The method is used to validate only current year leave request.
 
        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """
        current_year = datetime.today().date().year
        for rec in self:
            if rec.holiday_status_id.id:
                if rec.date_from:
                    if current_year != rec.date_from.date().year:
                        raise ValidationError(_('You can apply leave Request '
                                                'only for the current year!'))
                if rec.date_to:
                    if current_year != rec.date_to.date().year:
                        raise ValidationError(_('You can apply leave Request '
                                                'only for the current year!'))
                if rec.hr_year_id and rec.hr_year_id.date_start and \
                        rec.hr_year_id.date_stop:
                    if rec.date_from and rec.date_to:
                        if rec.hr_year_id.date_start > rec.date_from.date() or \
                                rec.hr_year_id.date_stop < rec.date_to.date():
                            raise ValidationError(_('Start date and end date \
                            must be related to selected HR year!'))

    @api.constrains('holiday_status_id', 'employee_id', 'date_from',
                    'date_to', 'child_birthdate')
    def _check_paternity_leave(self):
        """
        The method used to Validate for Paternity Leave.

        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        today_date = datetime.today().date()
        dependents_obj = self.env['dependents']
        for rec in self:
            if rec.holiday_status_id.name == 'PL' and\
                    rec.holiday_status_id.pre_approved:
                if not rec.employee_id.dependent_ids:
                    raise ValidationError(_(
                        'No Child Depends found! \n Please Add Child Detail '
                        'in Depend list for this employee Profile !'))
                depends_ids = dependents_obj.search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('birth_date', '=', rec.child_birthdate),
                    ('relation_ship', 'in', ['son', 'daughter'])], limit=1)
                if not depends_ids:
                    raise ValidationError(_(
                        'No Child found! \nNo Child found for the Birth date'
                        ' %s !' % (rec.child_birthdate)))
                if rec.employee_id and rec.employee_id.singaporean and \
                        rec.employee_id.depends_singaporean and \
                        rec.employee_id.join_date:
                    joining_date = rec.employee_id.join_date.date()
                    qualify_date = joining_date + relativedelta(months=3)
                    if today_date >= qualify_date and rec.date_from and \
                            rec.date_to:
                        child_birth_date = rec.child_birthdate.date()
                        from_date = rec.date_from.date()
                        to_date = rec.date_to.date()
                        qualify_date = child_birth_date + \
                            relativedelta(years=1)
#                         child_bd_week = child_birth_date.isocalendar()
                        sixteen_weeks_later = child_birth_date + \
                            relativedelta(weeks=16)
                        before_qualify_date = from_date - \
                            relativedelta(weeks=2)
                        if to_date > qualify_date:
                            raise ValidationError(_(
                                'Not Qualified in Joining date! \n'
                                'Employee must have worked in the company for '
                                'a continuous duration of at least 3 months!'))
                        if to_date > sixteen_weeks_later:
                            raise ValidationError(_(
                                'Warning! \n'
                                'Paternity leave should be taken within 16 '
                                'weeks of the child\'s birth date!'))
                        if before_qualify_date < today_date:
                            raise ValidationError(_(
                                'Warning! \nPaternity Leave request should be '
                                'submitted 2 weeks prior to the requested date.!'))
                    else:
                        raise ValidationError(_(
                            'Not Qualified in Joining date! \n'
                            'Employee must have worked in the company '
                            'for a continuous duration of at least 3 months!'))
                else:
                    raise ValidationError(_(
                        'Warning! \nChild is not Singapore citizen!'))

    @api.constrains('holiday_status_id', 'employee_id', 'date_to',
                    'child_birthdate')
    def _check_unpaid_infant_care_leave(self):
        """
        The method used to Validate for Unpaid Infant Care Leave.

        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        dependents_obj = self.env['dependents']
        for rec in self:
            if rec.holiday_status_id.name == 'UICL':
                if rec.holiday_status_id.pre_approved:
                    if not rec.employee_id.dependent_ids:
                        raise ValidationError(_(
                            'No Child Depends found! \n'
                            'Please Add Child Detail in Depend list for this '
                            'employee Profile !'))
                    depends_ids = dependents_obj.search([
                        ('employee_id', '=', rec.employee_id.id),
                        ('birth_date', '=', rec.child_birthdate),
                        ('relation_ship', 'in', ['son', 'daughter'])], limit=1)
                    if not depends_ids:
                        raise ValidationError(_(
                            'No Child found! \n No Child found for the '
                            'Birth date %s!' % (rec.child_birthdate)))
                    if rec.employee_id and rec.employee_id.singaporean and \
                            rec.employee_id.depends_singaporean:
                        if rec.employee_id.join_date:
                            qualify_date = rec.employee_id.join_date.date() + \
                                relativedelta(months=3)
                            if datetime.today().date() >= qualify_date:
                                if rec.child_birthdate and rec.date_to:
                                    child_birth_date = rec.child_birthdate.date()
                                    to_date = rec.date_todate()
                                    qualify_date = child_birth_date + \
                                        relativedelta(years=2)
                                    if to_date > qualify_date:
                                        raise ValidationError(_(
                                            'Warning! \n Child is not '
                                            'Singapore citizen!'))
                            else:
                                raise ValidationError(_(
                                    'Not Qualified in Joining date! \n'
                                    'Employee must have worked in the '
                                    'company for a continuous duration '
                                    'of at least 3 months!'))
                    else:
                        raise ValidationError(_(
                            'You are not able to apply Request for this Unpaid '
                            'Infant Care leave!'))

    @api.constrains('holiday_status_id', 'employee_id', 'date_to',
                    'child_birthdate')
    def _check_paid_child_care_leave(self):
        """
        The method used to Validate for Paid Child Care Leave.

        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        today_date = datetime.today().date()
        dependents_obj = self.env['dependents']
        for rec in self:
            if rec.holiday_status_id.name == 'CCL':
                if rec.holiday_status_id.pre_approved:
                    if not rec.employee_id.dependent_ids:
                        raise ValidationError(_(
                            'No Child Depends found! \n'
                            'Please Add Child Detail in Depend list for this '
                            'employee Profile !'))
                    depends_count = dependents_obj.search_count([
                        ('employee_id', '=', rec.employee_id.id),
                        ('birth_date', '=', rec.child_birthdate),
                        ('relation_ship', 'in', ['son', 'daughter'])])
                    if depends_count == 0:
                        raise ValidationError(_('No Child found! \nNo Child '
                                                'found for the Birth date %s '
                                                '!' % (rec.child_birthdate)))
                    if rec.employee_id and rec.employee_id.singaporean and \
                            rec.employee_id.depends_singaporean and \
                            rec.employee_id.join_date:
                        qualify_date = rec.employee_id.join_date.date() +\
                            relativedelta(months=3)
                        if today_date >= qualify_date:
                            if rec.child_birthdate and rec.date_to:
                                child_birth_date = rec.child_birthdate.date()
                                to_date = rec.date_to.date()
                                qualify_date = child_birth_date + \
                                    relativedelta(years=7)
                                if to_date > qualify_date:
                                    raise ValidationError(_(
                                        'You are not able to apply Request '
                                        'for this Paid Child Care leave!'))
                        else:
                            raise ValidationError(_(
                                'You are not able to apply Request for this '
                                'Paid Child Care leave!'))
                    else:
                        raise ValidationError(_(
                            'You are not able to apply Request for this '
                            'Paid Child Care leave!'))

    @api.constrains('holiday_status_id', 'employee_id', 'date_to',
                    'child_birthdate')
    def _check_extended_child_care_leave(self):
        """
        The method used to Validate for Extended Child Care Leave.

        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        dependents_obj = self.env['dependents']
        today_date = datetime.today().date()
        for rec in self:
            if rec.holiday_status_id.name == 'ECL':
                if rec.holiday_status_id.pre_approved:
                    if not rec.employee_id.dependent_ids:
                        raise ValidationError(_(
                            'No Child Depends found! \n'
                            'Please Add Child Detail in Depend list for this '
                            'employee Profile !'))
                    depends_ids = dependents_obj.search([
                        ('employee_id', '=', rec.employee_id.id),
                        ('birth_date', '=', rec.child_birthdate),
                        ('relation_ship', 'in', ['son', 'daughter'])], limit=1)
                    if not depends_ids:
                        raise ValidationError(_('No Child found! \nNo Child '
                                                'found for the Birth date %s '
                                                '!' % (rec.child_birthdate)))
                    if rec.employee_id and rec.employee_id.singaporean and \
                            rec.employee_id.depends_singaporean and \
                            rec.employee_id.join_date:
                        joining_date = rec.employee_id.join_date.date()
                        qualify_date = joining_date + relativedelta(months=3)
                        if today_date >= qualify_date:
                            if rec.child_birthdate and rec.date_to:
                                child_birth_date = rec.child_birthdate.date()
                                to_date = rec.date_to.date()
                                qualify_date_from = child_birth_date + \
                                    relativedelta(years=7)
                                qualify_date_to = child_birth_date + \
                                    relativedelta(years=12)
                                if to_date < qualify_date_from or \
                                        to_date > qualify_date_to:
                                    raise ValidationError(_(
                                        'You are not able to apply Request '
                                        'for this Extended Child Care leave!'))
                        else:
                            raise ValidationError(_(
                                'You are not able to apply Request for this '
                                'Extended Child Care leave!'))
                    else:
                        raise ValidationError(_(
                            'You are not able to apply Request for this '
                            'Extended Child Care leave!'))

    @api.constrains('number_of_days', 'holiday_status_id')
    def check_allocation_holidays(self):
        """
        The method used to Validate for Pro rate type Leaves.
        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        date_today = datetime.today().date()
        for rec in self:
            if rec.holiday_status_id.pro_rate:
                default_allocation = \
                    rec.holiday_status_id.default_leave_allocation
                leave = remain_month = 0.0
                if rec.employee_id.join_date:
                    join_date = rec.employee_id.join_date
                    after_one_year = join_date + relativedelta(years=1)
                    if date_today < after_one_year:
                        working_months = relativedelta(date_today, join_date)
                        if working_months and working_months.months:
                            remain_month = working_months.months
                        if default_allocation:
                            leave = (float(default_allocation) / 12) *\
                                remain_month
                            leave = round(leave)
                        if rec.number_of_days > leave:
                            raise ValidationError(_('You can not apply leave '
                                                    'more than %s !' % (
                                                        leave)))

    @api.constrains('date_from', 'date_to', 'holiday_status_id')
    def _check_imm_compassionate_leave(self):
        """
        The method used to Validate immediate compassionate leave.

        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        for rec in self:
            if rec.holiday_status_id.name == 'CL' and\
                    rec.holiday_status_id.pre_approved:
                if rec.number_of_days and \
                        rec.number_of_days > 5:
                    raise ValidationError(_(
                        'You are not able to apply leave Request more than 5 '
                        'Working days For compassionate leave!'))

    @api.constrains('date_from', 'date_to', 'holiday_status_id')
    def _check_other_compassionate_leave(self):
        """
        The method used to Validate other compassionate leave.
        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        for rec in self:
            if rec.holiday_status_id.name == 'CLO' and\
                    rec.holiday_status_id.pre_approved:
                if rec.number_of_days and \
                        rec.number_of_days > 3:
                    raise ValidationError(_(
                        'You are not able to apply leave Request more than 3 '
                        'Working days For compassionate leave!'))

    @api.constrains('holiday_status_id', 'date_from', 'date_to')
    def _check_off_in_leave(self):
        """
        The method used to Validate other compassionate leave.
        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        curr_month = datetime.today().month
        for rec in self:
            if rec.holiday_status_id.name == 'OIL' and\
                    rec.holiday_status_id.pre_approved:
                if rec.date_from and rec.date_to:
                    from_date = rec.date_from.month
                    to_date = rec.date_to.month
                    if int(from_date) != int(curr_month) or \
                            int(to_date) != int(curr_month):
                        raise ValidationError(_(
                            'You can apply off in leave Request for '
                            'current month only!'))

    @api.constrains('holiday_status_id', 'date_from', 'date_to', 'employee_id')
    def _check_marriage_leave(self):
        """
        The method used to Validate other compassionate leave.
        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        for rec in self:
            if rec.holiday_status_id.name in ('MLC', 'ML') and\
                    rec.holiday_status_id.pre_approved:
                from_date = rec.date_from.date()
                qualify_date = from_date - relativedelta(weeks=2)
                if qualify_date < datetime.today().date():
                    raise ValidationError(_(
                        'Marriage Leave request should be submitted 2 weeks '
                        'prior to the requested date.!'))

    @api.constrains('holiday_status_id', 'employee_id', 'date_from', 'date_to')
    def _check_sg_annual_leave(self):
        """
        The method used to Validate annual leave.
        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        curr_date = datetime.today().date()
        for rec in self:
            if rec.holiday_status_id.name == 'AL' and\
                    rec.holiday_status_id.pre_approved:
                if rec.date_from:
                    qualify_date = rec.date_from.date() - relativedelta(
                        weeks=1)
                    if qualify_date < curr_date:
                        raise UserError((
                            'Annual Leave request should be submitted 1 weeks '
                            'prior to the requested date.!'))

    @api.constrains('date_from', 'date_to')
    def _check_current_month_leave_req(self):
        """
        The method used to Validate current month leave request.
        @param self : Object Pointer
        @return: Return the False or True
        ----------------------------------------------------------
        """

        date_today = datetime.today()
        first_day = datetime(date_today.year, date_today.month, 1, 0, 0, 0)
        first_date_from = first_day.strftime(DSDTF)
        for rec in self:
            if rec.holiday_status_id.pre_approved and rec.date_from:
                rec_date_from1 = rec.date_from.replace(
                    tzinfo=pytz.utc).astimezone(pytz.timezone('Singapore'))
                rec_date_from2 = rec_date_from1.strftime(DSDTF)
                if rec_date_from2 and rec_date_from2 < first_date_from:
                    raise ValidationError(
                        _('You can apply leave Request only for the current '
                          'month!'))

    @api.constrains('holiday_status_id', 'employee_id', 'date_from', 'date_to')
    def _check_sg_medical_opt_leave(self):
        """
        The method used to Validate medical leave.
        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        today = time.strftime(DSDF)
        date_today = datetime.today()
        for rec in self:
            if rec.holiday_status_id.name == 'MOL':
                if rec.holiday_status_id.pre_approved:
                    if rec.employee_id.join_date and \
                            rec.employee_id.join_date <= today:
                        join_date = rec.employee_id.join_date
                        one_year_day = join_date + relativedelta(months=12)
                        three_months = join_date + relativedelta(months=3)
                        if three_months < date_today and \
                                one_year_day > date_today:
                            med_rmv = 0.0
                            self._cr.execute("""SELECT sum(number_of_days)
                            FROM hr_leave where employee_id=%d and
                            holiday_status_id = %d
                            """ % (rec.employee_id.id,
                                   rec.holiday_status_id.id))
                            all_datas = self._cr.fetchone()
                            if all_datas and all_datas[0]:
                                med_rmv += all_datas[0]
                            res_date = relativedelta(date_today, join_date)
                            tot_month = res_date.months
                            if tot_month == 3 and med_rmv > 5:
                                raise ValidationError(_(
                                    'You can not apply medical leave more '
                                    'than 5 days in 3 months!'))
                            elif tot_month == 4 and med_rmv > 8:
                                raise ValidationError(_(
                                    'You can not apply medical leave more '
                                    'than 8 days in 4 months!'))
                            elif tot_month == 5 and med_rmv > 11:
                                raise ValidationError(_(
                                    'You can not apply medical leave more '
                                    'than 11 days in 5 months!'))
                            elif tot_month >= 6 and med_rmv > 14:
                                raise ValidationError(_(
                                    'You can not apply medical leave more '
                                    'than 14 days in one Year!'))
                        if three_months > date_today:
                            raise ValidationError(_(
                                'You are not able to apply Medical leave Request.!'))

    @api.constrains('holiday_status_id', 'employee_id', 'date_from', 'date_to')
    def _check_sg_hospitalisation_leave(self):
        """
        The method used to Validate hospitalization leave.

        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        today = time.strftime(DSDF)
        date_today = datetime.today()
        for rec in self:
            if rec.holiday_status_id.name == 'HOL' and\
                    rec.holiday_status_id.pre_approved:
                if rec.employee_id.join_date and \
                        rec.employee_id.join_date <= today:
                    join_date = rec.employee_id.join_date
                    one_year_day = join_date + relativedelta(months=12)
                    three_months = join_date + relativedelta(months=3)
                    if three_months < date_today and \
                            one_year_day > date_today:
                        med_rmv = 0.0
                        self._cr.execute("""SELECT sum(number_of_days)
                        FROM hr_leave where employee_id=%d and
                        holiday_status_id = %d
                        """ % (rec.employee_id.id,
                               rec.holiday_status_id.id))
                        all_datas = self._cr.fetchone()
                        if all_datas and all_datas[0]:
                            med_rmv += all_datas[0]
                        res_date = relativedelta(date_today, join_date)
                        tot_month = res_date.months
                        if tot_month == 3 and med_rmv > 15:
                            raise ValidationError(_(
                                'You can not apply medical leave more than '
                                '15 days in 3 months!'))
                        elif tot_month == 4 and med_rmv > 30:
                            raise ValidationError(_(
                                'You can not apply medical leave more than '
                                '30 days in 4 months!'))
                        elif tot_month == 5 and med_rmv > 45:
                            raise ValidationError(_(
                                'You can not apply medical leave more than '
                                '45 days in 5 months!'))
                        elif tot_month >= 6 and med_rmv > 60:
                            raise ValidationError(_(
                                'You can not apply medical leave more than '
                                '60 days in one Year!'))
                    if three_months > date_today:
                        raise ValidationError(_(
                            'You are not able to apply Hospitalization leave '
                            'Request.!'))


class HrHolidayPublic(models.Model):
    _inherit = 'hr.holiday.public'

    @api.constrains('holiday_line_ids')
    def _check_holiday_line_year(self):
        """
        The method used to Validate duplicate public holidays.

        @param self : Object Pointer
        @return : True or False
        ------------------------------------------------------
        """

        for holiday in self:
            for line in holiday.holiday_line_ids:
                holiday_year = line.holiday_date.year
                if holiday.name != str(holiday_year):
                    raise ValidationError(_('You can not create holidays for '
                                            'different year!'))
                holiday_line_count = self.env['hr.holiday.lines'].search_count([
                    ('holiday_id', '=', line.holiday_id.id),
                    ('holiday_date', '=', line.holiday_date)])
                if holiday_line_count > 1:
                    raise ValidationError(
                        "You can not add holiday twice on same date")

    @api.constrains('name')
    def _check_public_holiday(self):
        for rec in self:
            pub_holiday_count = rec.search_count([('name', '=', rec.name)])
            if pub_holiday_count > 1:
                raise ValidationError(_('You can not have multiple public '
                                        'holiday for same year!'))


class HrPeriod(models.Model):
    _inherit = "hr.period"

    @api.constrains('date_start', 'date_stop')
    def _check_hr_period_duration(self):
        for obj_period in self:
            if obj_period.date_stop < obj_period.date_start:
                raise ValidationError(_('Error!\nThe duration of the '
                                        'Period(s) is/are invalid.'))

    @api.constrains('date_stop')
    def _check_year_limit(self):
        for obj_period in self:
            if obj_period.hr_year_id.date_stop < obj_period.date_stop or \
               obj_period.hr_year_id.date_stop < obj_period.date_start or \
               obj_period.hr_year_id.date_start > obj_period.date_start or \
               obj_period.hr_year_id.date_start > obj_period.date_stop:
                raise ValidationError(_(
                    'Error!\nThe period is invalid. Either some periods are '
                    'overlapping or the period\'s dates are not matching the '
                    'scope of the hr year.'))
            pids = self.search([('date_stop', '>=', obj_period.date_start),
                                ('date_start', '<=', obj_period.date_stop),
                                ('id', '!=', obj_period.id)], limit=1)
            if pids:
                raise ValidationError(_(
                    'Error!\nThe period is invalid. Either some periods are '
                    'overlapping or the period\'s dates are not matching the '
                    'scope of the HR year.'))


class HrHolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    @api.constrains('holiday_status_id', 'employee_id')
    def _check_holiday_status_id(self):
        for rec in self:
            if rec.holiday_status_id and\
                rec.holiday_status_id.name in ['ML16', 'ML15', 'ML8', 'ML4'] and\
                rec.employee_id and rec.employee_id.gender=='male':
                raise ValidationError(_(
                        'You are not able to apply Maternity Leave '
                        'Allocation of Male Employee!'))
