from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DSDTF, \
    DEFAULT_SERVER_DATE_FORMAT as DSDF


def _offset_format_timestamp1(src_tstamp_str, src_format, dst_format,
                              ignore_unparsable_time=True, context=None):
    """Get Local time.

    Convert a source timestamp string into a destination timestamp string,
    attempting to apply the correct offset if both the server and local
    timezone are recognized, or no offset at all if they aren't or if
    tz_offset is false (i.e. assuming they are both in the same TZ).

    @param src_tstamp_str: the str value containing the timestamp.
    @param src_format: the format to use when parsing the local timestamp.
    @param dst_format: the format to use when formatting the
                       resulting timestamp.
    @param server_to_client: specify timezone offset direction
                            (server=src and client=dest if True,
                            or client=src and server=dest if False)
    @param ignore_unparsable_time: if True, return False if src_tstamp_str
                                   cannot be parsed using src_format
                                   or formatted using dst_format.
    @return: destination formatted timestamp, expressed in the destination
             timezone if possible and if tz_offset is true,or src_tstamp_str
             if timezone offset could not be determined.
    """
    if not src_tstamp_str:
        return False
    res = str(src_tstamp_str)
    if src_format and dst_format:
        try:
            dt_value = datetime.strptime(str(src_tstamp_str), src_format)
            if context.get('tz', False):
                try:
                    import pytz
                    src_tz = pytz.timezone(context['tz'])
                    dst_tz = pytz.timezone('UTC')
                    src_dt = src_tz.localize(dt_value, is_dst=True)
                    dt_value = src_dt.astimezone(dst_tz)
                except Exception:
                    pass
            res = dt_value.strftime(dst_format)
        except Exception:
            #  Normal ways to end up here are if strptime or strftime failed
            if not ignore_unparsable_time:
                return False
            pass
    return res


class HrHolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    start_date = fields.Date(
        'Starting Date',
        default=lambda * a: datetime.strftime(date.today(), '%Y-01-01'))
    end_date = fields.Date(
        'Ending Date',
        default=lambda *d: datetime.strftime(date.today(), '%Y-12-31'))
    notes = fields.Text('Reasons', readonly=False,
                        states={'validate': [('readonly', True)]})
    state = fields.Selection(selection_add=[
        ('draft', 'New'), ('confirm', 'Waiting Pre-Approval'),
        ('refuse', 'Refused'), ('validate1', 'Waiting Final Approval'),
        ('validate', 'Approved'), ('cancel', 'Cancelled')], string='State',
        readonly=True, help='The state is set to \'Draft\', when a holiday \
        request is created.\nThe state is \'Waiting Approval\', when holiday\
        request is confirmed by user.\nThe state is \'Refused\', when holiday \
        request is refused by manager.\nThe state is \'Approved\', when \
        holiday request is approved by manager.')
    rejection = fields.Text('Reason')
    create_date = fields.Datetime('Create Date', readonly=True)
    write_date = fields.Datetime('Write Date', readonly=True)
    day = fields.Char(string='Day')
    carry_forward = fields.Boolean('Carry Forward Leave')

    def get_date(self, date=False):
        """Get Date.

        The method used to get the start and end date
        @self : Current Record Set
        @param date: get the date
        @return: Returns the start and end date in dictionary
        """
        date_dict = {}
        start_date = end_date = False
        if date:
            if isinstance(date, str):
                date = datetime.strptime(date, DSDF)
            start_date = '%s-01-01' % str(date.year)
            end_date = '%s-12-31' % str(date.year)
        date_dict.update({'start_date': start_date, 'end_date': end_date})
        return date_dict

    @api.model
    def get_dbname(self):
        """Get database name.

        The method used to get the database name
        ------------------------------------------------------
        @self : Current Record Set
        @api.model : The decorator of model
        @return : Return the database name
        """
        return self._cr.dbname or ''

    def get_work_email(self):
        """Email Template Method.

        The method used to get the employee of work email either user login,
        Which used in carry forward leave email template.
        @self : Current Record Set
        @return : Return the employee of work email either user login
        """
        #  fetch users who have rights of HR manager
        user_ids = self.env.ref("hr.group_hr_manager").users.ids
        emp_ids = self.env['hr.employee'].search([('user_id', 'in', user_ids)])
        #  fetch work email of HR manager
        work_email = list(set([str(emp.work_email or emp.user_id.login)
                               for emp in emp_ids]))
        email = ''
        for employee_email in work_email:
            email += employee_email + ','
        return email

    def get_from_mail(self):
        """Email Template Method.

        The method used to get the from email,Which used in
        carry forward leave email template.
        @self : Current Record Set
        @return : Return the from email
        """
        mail_server_ids = self.env['ir.mail_server'].search(
            [], order="id desc", limit=1)
        if mail_server_ids.ids:
            return mail_server_ids.smtp_user or ''

    @api.model
    def reminder_to_hr_manager(self):
        """Scheduler Method : Reminder to hr manager.

        This method will be called by scheduler on YYYY/01/07 00:01:01
        which will send reminder to HR manager for New Leaves which is not
        approved
        @self: Current Record Set
        @api.model: The decorator of model
        @return: True
        """
        mail_server_ids = self.env['ir.mail_server'].search([], limit=1)
        if mail_server_ids and mail_server_ids.smtp_user and \
                mail_server_ids.smtp_pass:
            h_status_ids = self.env['hr.leave.type'].search(
                [('default_leave_allocation', '>', 0)])
            holiday_id = self.search([
                ('state', 'in', ['draft', 'confirm']),
                ('holiday_status_id', 'in', h_status_ids.ids)], limit=1)
            temp_id = self.env.ref('sg_hr_holiday.sg10_email_temp_hr_reminder')
            if holiday_id:
                temp_id.send_mail(holiday_id.id, force_send=True)
        return True

    def get_holiday_data(self):
        """Get Holiday data.

        The method used to hr holiday data of employee
        @self : Current Record Set
        @return : Return the holiday data in dictionary
        """
        leave_allocation_obj = self.env['hr.leave.allocation']
        current_yr_date = self.get_date(datetime.today().date())
        start_dt = current_yr_date.get('start_date', False)
        end_dt = current_yr_date.get('end_date', False)
        holiday_status_ids = self.env['hr.leave.type'].search([
            ('default_leave_allocation', '>', 0)])
        holiday_ids = leave_allocation_obj.search([
            ('holiday_status_id', 'in', holiday_status_ids.ids),
            ('state', 'in', ['draft', 'confirm']),
            ('start_date', '>=', start_dt),
            ('end_date', '<=', end_dt)])
        hr_data = {}
        for holiday in holiday_ids:
            hr_name = holiday.employee_id.name + str(holiday.id)
            hr_data.update({hr_name: {
                                "name": holiday.employee_id.name,
                                "status": holiday.holiday_status_id.name,
                                "day": holiday.number_of_days}})
        return hr_data

    def get_holiday_leave_data(self):
        """Get holiday leave data.

        The method used to get the detail about employee of name, status and
        leaves of days
        --------------------------------------------------------------------
        @self : Current Record Set
        @return : Return the name of employee, leave type and days of leave in
                list of dictionary
        """
        hr_data = self.get_holiday_data()
        hr_data_sorted_keys = sorted(hr_data.keys())
        hr_holiday_lst = []
        for hr_value in hr_data_sorted_keys:
            hr_holiday_lst.append({
                'employee_name': hr_data[hr_value].get("name"),
                'status': hr_data[hr_value].get("status"),
                'leave_day': hr_data[hr_value].get("day")
            })
        return hr_holiday_lst

    @api.model
    def assign_annual_other_leaves(self):
        """Assign Annual Leave.

        This method will be called by scheduler which will assign
        Annual leave at end of the year i.e YYYY/12/01 00:01:01
        @self: Current Record Set
        @api.model: The decorator of model
        @return: True
        """
        h_status_rec = self.env['hr.leave.type'].search(
            [('default_leave_allocation', '>', 0)])

        current_yr_date = self.get_date(datetime.today().date())
        start_date = current_yr_date.get('start_date', False)
        end_date = current_yr_date.get('end_date', False)
        for holiday in h_status_rec:
            for employee in self.env['hr.employee'].search([
                ('active', '=', True), ('user_id', '!=', 1)]):
                leave_dict = {
                    'name': 'Assign Default Allocation ' + str(holiday.code),
                    'employee_id': employee.id,
                    'holiday_type': 'employee',
                    'holiday_status_id': holiday.id,
                    'number_per_interval': holiday.default_leave_allocation,
                    'start_date': start_date,
                    'end_date': end_date,
                    'state': 'confirm'
                }
                leaves = self.create(leave_dict)
                leaves.sudo().action_approve()
                leaves.sudo().action_validate()
        return True

    @api.model
    def assign_carry_forward_leave(self):
        """Assign carry forward leave.

        This method will be called by scheduler which will assign
        carry forward leave on end of the year.
        @self: Current Record Set
        @api.model: The decorator of model
        @return: True
        """
        cr = self._cr
        context = dict(self.env.context) or {}
        holiday_ids_lst = []
        leave_all_obj = self.env['hr.leave.allocation']

        crnt_yr_date = self.get_date(datetime.now().date())
        crnt_start_date = crnt_yr_date.get('start_date', False)
        crnt_end_date = crnt_yr_date.get('end_date', False)
        crnt_start_utc_date = _offset_format_timestamp1(
            crnt_start_date, '%Y-%m-%d', DSDF, context=context)
        crnt_end_utc_date = _offset_format_timestamp1(
            crnt_end_date, '%Y-%m-%d', DSDF, context=context)

        previous_year_date = datetime.now() - relativedelta(years=1)
        prv_yr_date = self.get_date(previous_year_date)
        prv_start_date = prv_yr_date.get('start_date', False)
        prv_end_date = prv_yr_date.get('end_date', False)
        start_date_str = datetime.strptime(prv_start_date, DSDF) + timedelta(
            hours=0, minutes=0, seconds=0)
        end_date_str = datetime.strptime(prv_end_date, DSDF) + timedelta(
            hours=23, minutes=59, seconds=59)
        prv_start_utc_date = _offset_format_timestamp1(
            start_date_str, '%Y-%m-%d %H:%M:%S', DSDTF, context=context)
        prv_end_utc_date = _offset_format_timestamp1(
            end_date_str, '%Y-%m-%d %H:%M:%S', DSDTF, context=context)

        empl_ids = self.env['hr.employee'].search([('active', '=', True),
                                                   ('user_id', '!=', 1)])
        holiday_status_ids = self.env['hr.leave.type'
                                      ].search([('cry_frd_leave', '>', 0)])
        for holiday in holiday_status_ids:
            for employee in empl_ids:
                add = remove = 0.0
                cr.execute("""SELECT sum(number_of_days) FROM
                hr_leave_allocation where employee_id=%d and state='validate'
                and holiday_status_id = %d and date_from >= '%s' and
                date_to <= '%s'""" % (employee.id, holiday.id,
                                      crnt_start_utc_date, crnt_end_utc_date))
                all_datas = cr.fetchone()
                if all_datas and all_datas[0]:
                    add += all_datas[0]
                cr.execute("""SELECT sum(number_of_days) FROM hr_leave where
                employee_id=%d and state='validate' and holiday_status_id = %d
                and request_date_from >= '%s' and request_date_to <= '%s'
                """ % (employee.id, holiday.id,
                       prv_start_utc_date, prv_end_utc_date))
                leave_datas = cr.fetchone()
                if leave_datas and leave_datas[0]:
                    remove += leave_datas[0]
                final = add - remove
                final = holiday.cry_frd_leave if \
                    final > holiday.cry_frd_leave else final
                if final > 0.0:
                    cleave_dict = {
                        'name': 'Default Carry Forward Leave Allocation',
                        'employee_id': employee.id,
                        'holiday_type': 'employee',
                        'holiday_status_id': holiday.id,
                        'number_of_days': final,
                        'carry_forward': True,
                        'start_date': crnt_start_date,
                        'end_date': crnt_end_date,
                    }
                    new_leave = leave_all_obj.create(cleave_dict)
                    holiday_ids_lst.append(new_leave)
        mail_server_ids = self.env['ir.mail_server'].search([], limit=1)
        if mail_server_ids and mail_server_ids.smtp_user and \
                mail_server_ids.smtp_user:
            temp_id = self.env.ref('sg_hr_holiday.sg10_email_temp_hr_holiday')
            for holiday_id in holiday_ids_lst:
                temp_id.send_mail(holiday_id.id, force_send=True)
        return True


class IrCron(models.Model):
    """Model describing cron jobs (also called actions or tasks)."""

    _inherit = "ir.cron"

    @api.model
    def change_scheduler_time(self, annual_carry_forward_leave=None,
                              all_other_annual_leaves=None,
                              approve_auto_carry_forward_leaves=None):
        """Change The Scheduler time."""
        context = dict(self.env.context) or {}
        context.update({'tz': self.env.user.tz})
        if annual_carry_forward_leave:
            cron_data = self.browse(annual_carry_forward_leave)
            c_date = _offset_format_timestamp1(cron_data.nextcall,
                                               '%Y-%m-%d %H:%M:%S',
                                               DSDTF, context=context)
            self._cr.execute("UPDATE ir_cron SET nextcall=%s WHERE id=%s",
                             (c_date, annual_carry_forward_leave))
        if all_other_annual_leaves:
            cron_data1 = self.browse(all_other_annual_leaves)
            cdate1 = _offset_format_timestamp1(cron_data1.nextcall,
                                               '%Y-%m-%d %H:%M:%S',
                                               DSDTF, context=context)
            self._cr.execute("UPDATE ir_cron SET nextcall=%s WHERE id=%s",
                             (cdate1, all_other_annual_leaves))
        if approve_auto_carry_forward_leaves:
            cron_data2 = self.browse(approve_auto_carry_forward_leaves)
            cdate2 = _offset_format_timestamp1(cron_data2.nextcall,
                                               '%Y-%m-%d %H:%M:%S',
                                               DSDTF, context=context)
            self._cr.execute("UPDATE ir_cron SET nextcall=%s WHERE id=%s",
                             (cdate2, approve_auto_carry_forward_leaves))
        return True
