import time
from datetime import date, datetime
from dateutil import rrule
from dateutil import parser, relativedelta
from odoo import SUPERUSER_ID
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF

from pytz import UTC


class LeaveRequest(models.Model):
    _inherit = "hr.leave"

    @api.model
    def _get_hr_year(self):
        """Get Hr Year.

        The method used to get HR year value.
        @param self : Object Pointer
        @return : id of HR year
        ------------------------------------------------------
        """
        today = time.strftime(DSDF)
        return self.fetch_hryear(today)

    @api.model
    def fetch_hryear(self, date=False):
        """Fetch Year.

        The method used to fetch HR year value.
        @param self : Object Pointer
        @return : id of HR year
        ------------------------------------------------------
        """
        if not date:
            date = fields.Date.context_today(self)
        if isinstance(date, str):
            date = datetime.strptime(date, DSDF)
        hr_year_obj = self.env['hr.year']
        args = [('date_start', '<=', date), ('date_stop', '>=', date)]
        hr_year_brw = hr_year_obj.search(args)
        if hr_year_brw and hr_year_brw.ids:
            hr_year_ids = hr_year_brw
        else:
            year = date.year
            end_date = str(year) + '-12-31'
            start_date = str(year) + '-01-01'
            hr_year_ids = hr_year_obj.create({'date_start': start_date,
                                              'date_stop': end_date,
                                              'code': str(year),
                                              'name': str(year)})
        return hr_year_ids.ids[0]

    @api.depends('employee_id')
    def _user_view_validate(self):
        uid = self.env.uid
        res_user = self.env['res.users']
        for holiday in self:
            if uid != SUPERUSER_ID and \
                    (res_user.has_group('base.group_user') or
                     res_user.has_group('hr.group_hr_user')) and not\
                    (res_user.has_group('hr.group_hr_manager')):
                if holiday.employee_id.user_id.id == uid:
                    holiday.user_view = True
                else:
                    holiday.user_view = False
            else:
                holiday.user_view = False

    leave_config_id = fields.Many2one('holiday.group.config',
                                      related='employee_id.leave_config_id',
                                      string='Leave Structure')
    leave_type_code = fields.Char("code")
    child_birthdate = fields.Date('Child DOB')
    compassionate_other = fields.Selection([('cr_ill_sib',
                                             'Critical Illness of Siblings'),
                                            ('dth_sib', 'Death of Siblings')])
    gender = fields.Selection([('male', 'Male'),
                               ('female', 'Female'),
                               ('other', 'Other')], 'Gender')
    off_in_lieu_detail = fields.Selection(
        [('gt4', '> 4 hrs on weekends/public holidays'),
         ('lt4', '< 4 hrs on weekends /public holidays'),
         ('others', 'Others')],
        string="Off-in Lieu")
    compassionate_immidiate = fields.Selection(
        [('cr_ill', 'Critical Illness'),
         ('cr_ill_sc', 'Critical Illness of spouse/Children'),
         ('cr_ill_prn', 'Critical Illness of parents, Gp,PI-Law'),
         ('dth_sc', 'Death of spouse/Children'),
         ('dth_prn', 'Death of parents, Gp,PI-Law')])
    remainig_days = fields.Float('Remaining Leave Days')
    hr_year_id = fields.Many2one('hr.year', 'HR Year', default=_get_hr_year)
    leave_expire = fields.Boolean('Leave Expire', help='Leave Expire')
    user_view = fields.Boolean(compute='_user_view_validate',
                               string="validate")

    @api.constrains('date_from', 'date_to')
    def _check_start_end_date(self):
        for rec in self:
            if rec.hr_year_id and rec.hr_year_id.state == 'done':
                raise ValidationError(_(
                        'You are not able to apply '
                        'leave Request of Close HR Year!'))

    @api.constrains('number_of_days')
    def _check_num_of_days(self):
        for rec in self:
            if rec.holiday_status_id.request_unit in ('day', 'half_day'):
                if not rec.number_of_days:
                    raise ValidationError(_(
                        'You are not able to apply '
                        'leave Request of zero days Holiday!'))

    @api.constrains('date_from', 'date_to', 'holiday_status_id')
    def _check_public_holiday_leave(self):
        for rec in self:
            holiday_status = rec.holiday_status_id or False
            if holiday_status and holiday_status.count_days_by == 'working_days_only':
                diff_day = rec._check_holiday_to_from_dates(
                    rec.date_from,
                    rec.date_to,
                    rec.employee_id.id)
                if diff_day == 0:
                    raise ValidationError(_(
                        'You are not able to apply leave Request on Holiday.!'))

    # Commenting the  method as it's giving warning of 
    # You can not set 2 time off that overlaps on the same day for the same employee.
    # and don't allow medical leaves to approve. - Anu Patel (10 March 2022)

    # def action_validate(self):
    #     """Action validate.

    #     override holidays_validate method for create hospitalization leave,
    #     on creation of Medical out patient leave.
    #     @param self : Object Pointer
    #     """
    #     h_status_obj = self.env['hr.leave.type']
    #     for rec in self:
    #         if rec.holiday_status_id.name == "MOL":
    #             today = datetime.today().date()
    #             hr_year_id = self.fetch_hryear(today)
    #             hos_leave_id = h_status_obj.search([('name', '=', 'HOL')], limit=1)
    #             leave_config = rec.employee_id.leave_config_id
    #             if leave_config and leave_config.holiday_group_config_line_ids:
    #                 emp_leave_ids = [leave.leave_type_id.id for leave in leave_config.holiday_group_config_line_ids if leave.leave_type_id]
    #                 if hos_leave_id and hos_leave_id.id in emp_leave_ids:
    #                     med_leave_dict = {
    #                         'name': rec.name or False,
    #                         'employee_id': rec.employee_id.id,
    #                         'holiday_type': 'employee',
    #                         'holiday_status_id': hos_leave_id.id,
    #                         'number_of_days': rec.number_of_days,
    #                         'hr_year_id': hr_year_id or False,
    #                         'state': 'validate',
    #                         'date_from': rec.date_from,
    #                         'date_to': rec.date_to,
    #                         'leave_config_id': rec.leave_config_id.id or False
    #                     }
    #                     self.create(med_leave_dict)
    #     return super(LeaveRequest, self).action_validate()

    def add_follower(self, employee_id):
        """Add the followers."""
        partner_ids = []
        employee = self.env['hr.employee'].sudo().browse(employee_id)
        if employee.user_id:
            partner_ids.append(employee.user_id.partner_id.id)
            if employee.leave_manager and employee.leave_manager.user_id and \
                    employee.leave_manager.user_id.id:
                partner_ids.append(
                    employee.leave_manager.user_id.partner_id.id)
        if partner_ids:
            self.message_subscribe(partner_ids=partner_ids)

#     @api.onchange('holiday_status_id')
#     def _onchange_holiday_status_id(self):
#         """Onchange Leave type.
# 
#         when you change Leave types, this method will set
#         it's code accordingly.
#         @param self: The object pointer
#         ------------------------------------------------------
#         @return: Dictionary of values.
#         """
#         if self.holiday_status_id:
#             for rec in self.holiday_status_id:
#                 self.leave_type_code = rec.name
#                 self.remainig_days = rec.remaining_leaves
#         working_days = False
#         if self.holiday_status_id.count_days_by == 'working_days_only':
#             working_days = True
#         self.number_of_days = self.with_context(
#             {'working_days': working_days}).\
#             _get_number_of_days(
#                 self.date_from,
#                 self.date_to,
#                 self.employee_id.id)['days']
#         super(LeaveRequest, self)._onchange_holiday_status_id()

    @api.onchange('employee_id')
    def onchange_employee(self):
        """Onchange Employee.

        when you change employee, this method will set
        it's leave structures accordingly.
        @param self: The object pointer
        ------------------------------------------------------
        @return: Dictionary of values.
        """
        result = {}
        leave_type_ids = self.env['hr.leave.type'].search([])
        self.leave_config_id = False
        self.holiday_status_id = False
        result.update({'domain': {
            'holiday_status_id': [('id', 'not in', leave_type_ids.ids)]}})
        if self.employee_id and self.employee_id.id:
            self.department_id = self.employee_id.department_id
            if self.employee_id.gender:
                self.gender = self.employee_id.gender
            leave_config = self.employee_id.leave_config_id
            if leave_config and leave_config.id:
                self.leave_config_id = leave_config.id
                config_line = leave_config.holiday_group_config_line_ids
                leave_type_list = [leave_type.leave_type_id.id for leave_type in config_line if leave_type.leave_type_id]
                result['domain'] = {'holiday_status_id': [('id', 'in', leave_type_list)]}
            else:
                return {'warning': {
                    'title': 'Leave Warning',
                    'message': 'No Leave Structure Found!'
                               '\nPlease configure leave structure for'
                    ' current employee from employee\'s profile!'},
                    'domain': result['domain']}
        return result

    @api.depends('number_of_days')
    def _compute_number_of_hours_display(self):
        for holiday in self:
            calendar = holiday._get_calendar()
            if holiday.date_from and holiday.date_to:
                # Take attendances into account, in case the leave validated
                # Otherwise, this will result into number_of_hours = 0
                # and number_of_hours_display = 0 or
                # (#day * calendar.hours_per_day),
                # which could be wrong if the employee doesn't
                # work the same number
                # hours each day
                if holiday.state == 'validate':
                    start_dt = holiday.date_from
                    end_dt = holiday.date_to
                    if not start_dt.tzinfo:
                        start_dt = start_dt.replace(tzinfo=UTC)
                    if not end_dt.tzinfo:
                        end_dt = end_dt.replace(tzinfo=UTC)
                    intervals = calendar._attendance_intervals(
                        start_dt, end_dt, holiday.employee_id.resource_id) \
                        - calendar._leave_intervals(
                        start_dt, end_dt, None)  # Substract Global Leaves
                    number_of_hours = sum(
                        (stop - start).total_seconds() / 3600
                        for start, stop, dummy in intervals)
                else:
                    number_of_hours = holiday.with_context({
                        'working_days': True}
                    )._get_number_of_days(
                        holiday.date_from,
                        holiday.date_to,
                        holiday.employee_id.id)['hours']
                holiday.number_of_hours_display = number_of_hours or (
                    holiday.number_of_days * (calendar.hours_per_day or 8))
            else:
                holiday.number_of_hours_display = 0

    def get_date_from_range(self, from_date, to_date):
        '''
            Returns list of dates from from_date to to_date
            @self : Current Record Set
            @param from_date: Starting date for range
            @param to_date: Ending date for range
            @return : Returns list of dates from from_date to to_date
            -----------------------------------------------------------
        '''
        dates = []
        if from_date and to_date:
            dates = list(rrule.rrule(rrule.DAILY,
                                     dtstart=from_date,
                                     until=to_date))
        return dates

    def _check_holiday_to_from_dates(self, start_date, end_date, employee_id):
        '''
        Checks that there is a public holiday,Saturday and Sunday
        on date of leave
        @param self : Object Pointer
        @param cr : Database Cursor
        @param uid : Current User Id
        @param ids : The current object of id
        @param from_date: Starting date for range
        @param to_date: Ending date for range
        @return : Returns the numbers of days
        -----------------------------------------------------------
        '''
        public_holiday_dates = [
            line.holiday_date for line in
            self.env['hr.holiday.lines'].search([
                ('holiday_date', '>=', start_date),
                ('holiday_date', '<=', end_date),
                ('holiday_id.state', '=', 'validated')])]
        dates = self.get_date_from_range(start_date, end_date)
        dates = [date for date in dates
                 if date.isoweekday() not in [6, 7] and date.date()
                 not in public_holiday_dates]
        no_of_day = len(dates)
        days = {'days': no_of_day, 'hours': 0}
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            hour_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            days['hours'] = no_of_day * hour_per_day
            days['days'] = no_of_day
        return days

    def _get_number_of_days(self, date_from, date_to, employee_id):
        """Get number of days.

        Returns a float equals to the timedelta between two dates
        given as string.
        """
        if self._context.get('working_days'):
            leave_day = self._check_holiday_to_from_dates(
                date_from, date_to, employee_id)
            return leave_day
        return super(LeaveRequest, self)._get_number_of_days(
            date_from,
            date_to,
            employee_id)

    @api.onchange('date_from', 'date_to', 'employee_id')
    def _onchange_leave_dates(self):
        """Onchnage Leave dates.

        The method purpose is to check the date_from and date_to and also
        recalculate number_od_days based on Holiday Type.
        """
        if self.date_from and self.date_to:
            if (self.holiday_status_id and
                self.holiday_status_id.count_days_by == 'working_days_only'):

                diff_day = self.with_context({
                    'working_days': True})._get_number_of_days(
                        self.date_from,
                        self.date_to, self.employee_id.id)['days']
                self.number_of_days = diff_day
            else:
                self.number_of_days = self._get_number_of_days(
                    self.date_from, self.date_to, self.employee_id.id)['days']
        else:
            self.number_of_days = 0


class HrHolidaysStatus(models.Model):
    _inherit = "hr.leave.type"
    _rec_name = 'name2'
    _order = 'name2'

    paid_leave = fields.Boolean("Paid Leave",
                                help="Checked if leave type is paid.")
    allow_half_day = fields.Boolean("Allow half day",
                                    help="If checked, system allows the \
                                    employee to take half day leave for this \
                                    leave type")
    carryover = fields.Selection([('none', 'None'),
                                  ('up_to', '50% of Entitlement'),
                                  ('unlimited', 'Unlimited'),
                                  ('no_of_days', 'Number of Days')],
                                 string="Carryover",
                                 help="Select way of carry forward leaves \
                                 allocation", default='none')
    pro_rate = fields.Boolean("Pro-rate",
                              help="If checked, system allows the employee \
                              to take leaves on pro rated basis.")
    count_days_by = fields.Selection([('calendar_day', 'Calendar Days'),
                                      ('working_days_only',
                                       'Working Days only')],
                                     string="Count Days By",
                                     help="If Calendar Days : system will \
                                     counts all calendar days in leave request\
                                     .\nIf Working Days only : system will \
                                     counts all days except public and weekly \
                                     holidays in leave request. ",
                                     default='calendar_day')
    earned_leave = fields.Boolean("Earned Leave")
    max_leave_kept = fields.Integer('Maximum Leave Kept',
                                    help="Configure Maximum Number of Leaves \
                                    to be allocated for this leave type.")
    incr_leave_per_year = fields.Integer('Increment Number of Leave Per Year',
                                         help="Configure Number of Leave \
                                         which auto increments in leave \
                                         allocation per year.")
    number_of_year = fields.Integer('Number of Year After Carry \
                                    Forward Allocate',
                                    help="Configure Number of year after \
                                    which carry forward leaves will be \
                                    allocated.Put O (Zero) if allocation of \
                                    carry forward from joining")
    pre_approved = fields.Boolean("Pre Approved")
    carry_no_of_days = fields.Float("Carry Number of Days")
    no_of_days = fields.Float("Number of Days")

    def get_employees_days(self, employee_ids):
        today = date.today()
        hr_year_id = self.env['hr.leave'].fetch_hryear(today)
        result = {
            employee_id: {
                leave_type.id: {
                    'max_leaves': 0,
                    'leaves_taken': 0,
                    'remaining_leaves': 0,
                    'virtual_remaining_leaves': 0,
                    'virtual_leaves_taken': 0,
                } for leave_type in self
            } for employee_id in employee_ids
        }

        requests = self.env['hr.leave'].search([
            ('employee_id', 'in', employee_ids),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
            ('holiday_status_id', 'in', self.ids),
            ('leave_expire', '!=', True),
            ('hr_year_id', '=', hr_year_id)
        ])

        allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', 'in', employee_ids),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
            ('holiday_status_id', 'in', self.ids),
            ('leave_expire', '!=', True),
            ('hr_year_id', '=', hr_year_id)
        ])

        for request in requests:
            status_dict = result[request.employee_id.id][request.holiday_status_id.id]
            status_dict['virtual_remaining_leaves'] -= (request.number_of_hours_display
                                                    if request.leave_type_request_unit == 'hour'
                                                    else request.number_of_days)
            status_dict['virtual_leaves_taken'] += (request.number_of_hours_display
                                                if request.leave_type_request_unit == 'hour'
                                                else request.number_of_days)
            if request.state == 'validate':
                status_dict['leaves_taken'] += (request.number_of_hours_display
                                            if request.leave_type_request_unit == 'hour'
                                            else request.number_of_days)
                status_dict['remaining_leaves'] -= (request.number_of_hours_display
                                                if request.leave_type_request_unit == 'hour'
                                                else request.number_of_days)

        for allocation in allocations.sudo():
            status_dict = result[allocation.employee_id.id][allocation.holiday_status_id.id]
            if allocation.state == 'validate':
                # note: add only validated allocation even for the virtual
                # count; otherwise pending then refused allocation allow
                # the employee to create more leaves than possible
                status_dict['virtual_remaining_leaves'] += (allocation.number_of_hours_display
                                                          if allocation.type_request_unit == 'hour'
                                                          else allocation.number_of_days)
                status_dict['max_leaves'] += (allocation.number_of_hours_display
                                            if allocation.type_request_unit == 'hour'
                                            else allocation.number_of_days)
                status_dict['remaining_leaves'] += (allocation.number_of_hours_display
                                                  if allocation.type_request_unit == 'hour'
                                                  else allocation.number_of_days)
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """Name search."""
        if not args:
            args = []
        ids = self.search([('name2', operator, name)] + args, limit=limit)
        if self._context and 'leave_status' in self._context:
            employee_id = self._context.get('leave_status', False)
            if employee_id:
                employee = self.env['hr.employee'].browse(employee_id)
                if employee.leave_config_id and employee.leave_config_id.holiday_group_config_line_ids:
                    lev_cnfg_ids = employee.leave_config_id.holiday_group_config_line_ids
                    leave_type_list = [leaves.leave_type_id.id for leaves in lev_cnfg_ids if leaves.leave_type_id]
                    if len(leave_type_list) > 0:
                        ids = self.search([
                            ('name2', operator, name),
                            ('id', 'in', leave_type_list)] + args,
                            limit=limit)
        return ids.name_get()


class HrHolidayPublic(models.Model):
    _name = 'hr.holiday.public'
    _description = 'Public holidays'

    @api.constrains('name')
    def is_name_digit(self):
        """Checked is digit or not."""
        for rec in self:
            if rec.name and not rec.name.isdigit():
                raise ValidationError(_("Please enter valid holiday year!"))

    name = fields.Char('Holiday Year', required=True,
                       help='Name of holiday list',
                       default=lambda * a: date.today().year)
    holiday_line_ids = fields.One2many('hr.holiday.lines', 'holiday_id',
                                       'Holidays')
    email_body = fields.Html(
        'Email Body',
        default='Dear Manager,<br><br>Kindly find attached'
                ' pdf document containing Public Holiday List.'
                '<br><br>Thanks,')
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed'),
                              ('validated', 'Validated'),
                              ('refused', 'Refused'),
                              ('cancelled', 'Cancelled'), ], 'State',
                             index=True, readonly=True, default='draft')

    def setstate_draft(self):
        """Update state to to draft."""
        self.write({'state': 'draft'})
        return True

    def setstate_cancel(self):
        """Update state to cancelled."""
        self.write({'state': 'cancelled'})
        return True

    def setstate_validate(self):
        """Update state to validated."""
        mail_obj = self.env["ir.mail_server"]
        res_user_obj = self.env['res.users'].search([])
        emp_obj = self.env['hr.employee']
        report_action_obj = self.env['ir.actions.report']
        for self_rec in self:
            mail_server_id = mail_obj.search([], limit=1)
            if mail_server_id:
                if mail_server_id.smtp_user:
                    if not self_rec.email_body:
                        raise ValidationError(_('Please specify email body!'))
                    user_rec = res_user_obj.filtered(
                        lambda x: x.has_group('hr.group_hr_manager')).ids
                    if 1 in user_rec:
                        user_rec.remove(1)
                    work_email = []
                    emp_ids = emp_obj.search([('user_id', 'in', user_rec)])
                    #  fetch work email of HR manager
                    work_email = list(set([str(emp.work_email or
                                               emp.user_id.login)
                                           for emp in emp_ids]))
                    email_to = ",".join(work_email)
                    if not work_email:
                        raise ValidationError(_('No HR Manager found!'))
                    #  generate report of public holiday and attached in mail
                    report_name = (
                        'sg_holiday_extended.employee_public_holiday_report')
                    report = report_action_obj._get_report_from_name(
                        report_name)
                    if report:
                        temp_name = (
                            'sg_holiday_extended.mail_template_puublic_holiday'
                        )
                        template_id = self.env.ref(temp_name)
                        template_id.write({
                            'email_from': mail_server_id.smtp_user,
                            'email_to': email_to,
                            'body_html': self_rec.email_body,
                            'report_name': 'Public Holiday',
                           'report_template': report.id,
                        })
                        template_id.send_mail(self_rec.id, force_send=True)
            self_rec.write({'state': 'validated'})
        return True

    def setstate_refuse(self):
        """Update state to refused."""
        self.write({'state': 'refused'})

    def setstate_confirm(self):
        """Update state to confirmed."""
        if not self.holiday_line_ids:
            raise ValidationError(_('Please add holidays.'))
        self.write({'state': 'confirmed'})

    def unlink(self):
        """Check state before unlink."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    'Warning! \n You cannot delete a public holiday which is not in draft state !'))
        return super(HrHolidayPublic, self).unlink()


class HrHolidayLines(models.Model):
    _name = 'hr.holiday.lines'
    _description = 'Holiday Lines'

    name = fields.Char('Reason', help='Reason for holiday')
    day = fields.Char('Day', help='Day')
    holiday_id = fields.Many2one('hr.holiday.public', 'Holiday List',
                                 help='Holiday list')
    holiday_date = fields.Date('Date', help='Holiday date', required=True)
    value = fields.Char('No of Days')

    def init(self):
        """Alter the exist constrain."""
        self._cr.execute("SELECT conname FROM pg_constraint where \
        conname = 'hr_holiday_lines_date_uniq'")
        if self._cr.fetchall():
            self._cr.execute('ALTER TABLE hr_holiday_lines DROP \
            CONSTRAINT hr_holiday_lines_date_uniq')
            self._cr.commit()
        return True

    @api.onchange('holiday_date')
    def onchange_holiday_date(self):
        """Set the weekday based on holiday date."""
        for holiday_rec in self:
            holiday_dt = holiday_rec.holiday_date or False
            if holiday_dt:
                daylist = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                           'Friday', 'Saturday', 'Sunday']
                parsed_date = parser.parse(str(holiday_dt))
                day = parsed_date.weekday()
                self.day = daylist[day]


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    @api.model
    def _get_hr_year(self):
        """Get HR year.

        The method used to get HR year value.
        @param self : Object Pointer
        @return : id of HR year
        ------------------------------------------------------
        """
        today = time.strftime(DSDF)
        return self.fetch_hryear(today)

    @api.model
    def fetch_hryear(self, date=False):
        """Fetch hr year.

        The method used to fetch HR year value.
        @param self : Object Pointer
        @return : id of HR year
        ------------------------------------------------------
        """
        if not date:
            date = time.strftime(DSDF)
        if isinstance(date, str):
            date = datetime.strptime(date, DSDF)
        hr_year_obj = self.env['hr.year']
        args = [('date_start', '<=', date), ('date_stop', '>=', date)]
        hr_year_brw = hr_year_obj.search(args)
        if hr_year_brw and hr_year_brw.ids:
            hr_year_ids = hr_year_brw
        else:
            year = date.year
            end_date = str(year) + '-12-31'
            start_date = str(year) + '-01-01'
            hr_year_ids = hr_year_obj.create({'date_start': start_date,
                                              'date_stop': end_date,
                                              'code': str(year),
                                              'name': str(year)})
        return hr_year_ids.ids[0]

    hr_year_id = fields.Many2one('hr.year', 'HR Year', default=_get_hr_year)
    leave_expire = fields.Boolean('Leave Expire', help='Leave Expire')
    leave_config_id = fields.Many2one('holiday.group.config',
                                      related='employee_id.leave_config_id',
                                      string='Leave Structure')
    gender = fields.Selection([('male', 'Male'),
                               ('female', 'Female'),
                               ('other', 'Other')], 'Gender')

    @api.model
    def fetch_hryear_allocation(self, date=False):
        """Fetch HR year allocation.

        The method used to fetch HR year value.
        @param self : Object Pointer
        @return : id of HR year
        ------------------------------------------------------
        """
        if not date:
            date = time.strftime(DSDF)
        hr_year_obj = self.env['hr.year']
        args = [('date_start', '<=', date), ('date_stop', '>=', date)]
        hr_year_brw = hr_year_obj.search(args)
        if hr_year_brw and hr_year_brw.ids:
            hr_year_ids = hr_year_brw
        else:
            year = datetime.strptime(date, DSDF).year
            end_date = str(year) + '-12-31'
            start_date = str(year) + '-01-01'
            hr_year_ids = hr_year_obj.create({'date_start': start_date,
                                              'date_stop': end_date,
                                              'code': str(year),
                                              'name': str(year)})
        return hr_year_ids.ids[0]

    @api.model
    def assign_annual_other_leaves(self):
        """Assign the annual other leaves.

        This method will be called by scheduler which will assign
        Annual Marriage,Compassionate,Infant care,Child care,
        Extended child care,Paternity leaves at end of the year.
        @param self : Object Pointer
        @return: Return the True
        ----------------------------------------------------------
        """
        date_today = datetime.today()
        year = date_today.year
        curr_year_date = str(date_today.year) + '-01-01'
        curr_year_date = datetime.strptime(curr_year_date, DSDF).strftime(DSDF)
        emp_obj = self.env['hr.employee']
        empl_ids = emp_obj.search([('active', '=', True),
                                   ('leave_config_id', '!=', False)])
        leave_rec = []
        for employee in empl_ids:
            config_line = (
                employee.leave_config_id.holiday_group_config_line_ids) or []
            for holiday in config_line:
                tot_allocation_leave = holiday.default_leave_allocation
                if tot_allocation_leave > 0:
                    if employee.user_id and employee.user_id.id == 1:
                        continue
                    add = 0.0
                    self.env.cr.execute("""SELECT sum(number_of_days)
                    FROM hr_leave_allocation where employee_id=%d and state='validate'
                    and holiday_status_id = %d""" % (
                        employee.id, holiday.leave_type_id.id))
                    all_datas = self._cr.fetchone()
                    if all_datas and all_datas[0]:
                        add += all_datas[0]
                    if add > 0.0:
                        continue
                    if holiday.leave_type_id.name == 'AL' and \
                            employee.join_date.strftime(DSDF) > curr_year_date:
                        join_month = datetime.strptime(
                            employee.join_date.strftime(DSDF), DSDF).month
                        remaining_months = 12 - int(join_month)
                        if remaining_months:
                            tot_allocation_leave = (float(
                                                    tot_allocation_leave) / 12
                                                    ) * remaining_months
                            tot_allocation_leave = round(tot_allocation_leave)
                    if holiday.leave_type_id.name in ['PL', 'SPL'] and \
                            employee.gender != 'male':
                        continue
                    if holiday.leave_type_id.name == 'PCL' and \
                            not employee.singaporean:
                        continue
                    if config_line and config_line.ids:
                        for leave in config_line:
                            leave_rec.append(leave.leave_type_id.id)
                        if config_line:
                            if holiday.leave_type_id.name == 'AL' and \
                                employee.join_date.strftime(
                                    DSDF) < curr_year_date:
                                join_year = datetime.strptime(
                                    employee.join_date.strftime(
                                        DSDF), DSDF).year
                                tot_year = year - join_year
                                if holiday.incr_leave_per_year != 0 and \
                                        tot_year != 0:
                                    tot_allocation_leave += (
                                        holiday.incr_leave_per_year *
                                        tot_year)
                            if holiday.max_leave_kept != 0 and \
                                    tot_allocation_leave > \
                                    holiday.max_leave_kept:
                                tot_allocation_leave = holiday.max_leave_kept
                            leave_dict = {
                                'name': 'Assign Default ' + str(
                                    holiday.leave_type_id.name2),
                                'employee_id': employee.id,
                                'holiday_type': 'employee',
                                'holiday_status_id': holiday.leave_type_id.id,
                                'number_of_days': tot_allocation_leave,
                            }
                            self.env['hr.leave.allocation'].create(leave_dict)
        return True

    @api.onchange('employee_id')
    def onchange_employee(self):
        """Onchange Employee.

        when you change employee, this method will set
        it's leave structures accordingly.
        @param self: The object pointer
        ------------------------------------------------------
        @return: Dictionary of values.
        """
        result = {}
        leave_type_ids = self.env['hr.leave.type'].search([])
        self.leave_config_id = False
        self.holiday_status_id = False
        result.update({'domain': {
            'holiday_status_id': [('id', 'not in', leave_type_ids.ids)]}})
        if self.employee_id and self.employee_id.id:
            self.department_id = self.employee_id.department_id
            if self.employee_id.gender:
                self.gender = self.employee_id.gender
            leave_config = self.employee_id.leave_config_id
            if leave_config and leave_config.id:
                self.leave_config_id = leave_config.id
                config_line = leave_config.holiday_group_config_line_ids
                leave_type_list = [leave_type.leave_type_id.id for leave_type in config_line if leave_type.leave_type_id]
                result['domain'] = {'holiday_status_id': [('id', 'in', leave_type_list)]}
            else:
                return {
                    'warning': {
                        'title': 'Leave Warning',
                        'message': 'No Leave Structure Found!'
                                   '\nPlease configure leave structure for current employee from employee\'s profile!'
                    },
                    'domain': result['domain']
                }
        return result

    def send_email(self, holiday_id, temp_id, force_send=False):
        """Send email.

        This method sends mail using information given in message
        @self : Current Record Set
        @param int holiday_id : The current object of id
        @param int temp_id: The Email Template of id
        @param bool force_send : if True, the generated mail.
            message is immediately sent after being created,
            as if the scheduler was executed for this message
            only
        -----------------------------------------------------------
        """
        mail_obj = self.env['mail.template']
        mail_obj.browse(temp_id).send_mail(holiday_id, force_send=force_send)

    @api.model
    def assign_carry_forward_leave(self):
        """Assign carry forward leave.

        This method will be called by scheduler which will assign
        carry forward leave on end of the year.
        @param self : Object Pointer
        @return: Return the True
        ----------------------------------------------------------------------
        """
        today = date.today()
        prev_year_date = today + relativedelta.relativedelta(years=-1,
                                                             month=1,
                                                             day=1)
        empl_ids = self.env['hr.employee'].search([('active', '=', True),
                                                   ('leave_config_id', '!=',
                                                    False)])
        hr_year_id = self.fetch_hryear(prev_year_date)
        current_hr_year_id = self.fetch_hryear(today)
        hr_year_rec = self.env['hr.year'].browse(hr_year_id)
        start_date = hr_year_rec.date_start
        end_date = hr_year_rec.date_stop
        holiday_ids_lst = []
        for employee in empl_ids:
            holiday_group_config_line_ids = employee.leave_config_id and\
                employee.leave_config_id.holiday_group_config_line_ids or []
            for holiday in holiday_group_config_line_ids:
                if employee.user_id and employee.user_id.id == 1:
                    continue
                if (employee.join_date and
                        holiday.leave_type_id.number_of_year > 0):
                    joining_date = datetime.strptime(employee.join_date,
                                                     DSDF).date()
                    qualify_date = joining_date + \
                        relativedelta.relativedelta(
                            years=int(holiday.leave_type_id.number_of_year))
                    if datetime.today().date() < qualify_date:
                        continue
                add = 0.0
                remove = 0.0
                self._cr.execute("""SELECT sum(number_of_days) FROM
                hr_leave_allocation  where employee_id=%d and state='validate' and
                holiday_status_id = %d and start_date>='%s' and 
                end_date<='%s'""" % (employee.id,
                                     holiday.leave_type_id.id,
                                     str(start_date), str(end_date)))
                all_datas = self._cr.fetchone()
                if all_datas and all_datas[0]:
                    add += all_datas[0]
                self._cr.execute("""SELECT sum(number_of_days) FROM
                hr_leave where employee_id=%d and state='validate' and
                holiday_status_id = %d and date_from >= '%s'
                and date_to <= '%s'""" % (employee.id,
                                          holiday.leave_type_id.id,
                                          start_date, end_date))
                leave_datas = self._cr.fetchone()
                if leave_datas and leave_datas[0]:
                    remove += leave_datas[0]
                final = add - remove
                if holiday.carryover == 'none':
                    final = 0
                elif holiday.carryover == 'up_to':
                    if float(add / 2) > final:
                        final = final
                    elif float(add / 2) < final:
                        final = float(add / 2)
                    final = final
                elif holiday.carryover == 'unlimited':
                    final = final
                elif holiday.carryover == 'no_of_days':
                    if holiday.carry_no_of_days > final:
                        final = final
                    else:
                        final = holiday.carry_no_of_days
                else:
                    final = 0
                if final > 0.0:
                    cleave_dict = {
                        'name': 'Default Carry Forward Leave Allocation',
                        'employee_id': employee.id,
                        'holiday_type': 'employee',
                        'holiday_status_id': holiday.leave_type_id.id,
                        'number_of_days': final,
                        'hr_year_id': current_hr_year_id,
                        'carry_forward': True
                    }
                    new_holiday_rec = self.create(cleave_dict)
                    holiday_ids_lst.append(new_holiday_rec.id)
        temp_id = self.env.ref('sg_hr_holiday.sg10_email_temp_hr_holiday')
        for holiday_id in holiday_ids_lst:
            self.send_email(holiday_id, temp_id.id, force_send=True)
        return True
