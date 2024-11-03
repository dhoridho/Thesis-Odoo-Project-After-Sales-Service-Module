from odoo import models, fields, api, _
from odoo import SUPERUSER_ID
from odoo.exceptions import AccessDenied, UserError
from odoo import fields
from datetime import datetime, timedelta
import logging
import pytz
from pytz import all_timezones  
from odoo.http import request


_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'


    ip_address_ids = fields.One2many('ip.address', 'res_user_id', string='Allowed IP')
    ip_address_login_toggle = fields.Boolean(default=False, string="Enable IP Address Login Validation")
    current_ip_address = fields.Char(string="Current IP Address")
    ip_address_after_login = fields.Char(string="IP Address After Login")
    last_login = fields.Datetime(string="Last Login", readonly=True)
    time_restricted = fields.Boolean(default=False, string="Allowed Time")
    day_restricted_ids = fields.One2many('day.restricted', 'res_user_id', string='Allowed Days')
    sid = fields.Char('Session ID')
    exp_date = fields.Datetime('Expiry Date')
    logged_in = fields.Boolean('Logged In')
    last_update = fields.Datetime(string="Last Connection Updated")
    should_be_logged_out = fields.Boolean(default=False)
    tz = fields.Char('Timezone')
    

    def _clear_session(self):
        """
            Function for clearing the session details for user
        """
        self.write({'sid': False, 
                    'exp_date': False, 
                    'logged_in': False,
                    'should_be_logged_out': True,
                    'ip_address_after_login': False,
                    'last_update': datetime.now()})
        
    

    def _validate_sessions(self):
        """ Cron job """

        # users = self.env['res.users'].sudo().search([('ip_address_login_toggle', '=', True), ('time_restricted', '=', True)])
        users = self.env['res.users'].sudo().search([('ip_address_login_toggle', '=', True)])
        
        for user in users:
            ip_address_list = []
            ip_address_allowed = self.env['ip.address'].sudo().search([('res_user_id', '=', user.id)])
            for ip_address in ip_address_allowed:
                ip_address_list.append(ip_address.ip_address)

            # if user.ip_address_after_login not in ip_address_list:
            #         users._clear_session()

            if user.ip_address_after_login in ip_address_list:
                if user.time_restricted:
                    day_restricted_list = []
                
                    user_tz = user.tz or 'UTC'
                    local = pytz.timezone(user_tz)
                    current_day = datetime.strftime(pytz.utc.localize(datetime.now()).astimezone(local), "%A")
                    current_hour = datetime.strftime(pytz.utc.localize(datetime.now()).astimezone(local), "%H.%M")
                    current_time = datetime.strptime(current_hour, "%H.%M")
                    formatted_time = current_time.replace(second=0).strftime("%H:%M:%S")
                    current_time = datetime.strptime(formatted_time, "%H:%M:%S")

                    day_restricted = self.env['day.restricted'].sudo().search([('res_user_id', '=', user.id)])
                    for day in day_restricted:
                        if day.day == current_day:
                            day_restricted_list.append(day.day)

                    # if current_day in day_restricted_list:
                    #     for day in day_restricted:
                    #         if day.day == current_day:
                                # Assuming start_time and end_time are in the format 'HH.MM'

                            start_time = day.start_time
                            hour_start = int(start_time)
                            minute_start = int((start_time - hour_start) * 60)
                            start_timedelta = timedelta(hours=hour_start, minutes=minute_start)

                            end_time = day.end_time
                            hour_end = int(end_time)
                            minute_end = int((end_time - hour_end) * 60)
                            end_timedelta = timedelta(hours=hour_end, minutes=minute_end)
                            
                            start_time = datetime.strptime(str(start_timedelta), "%H:%M:%S")
                            end_time = datetime.strptime(str(end_timedelta), "%H:%M:%S")

                            if not start_time <= current_time <= end_time :
                                users._clear_session()

                # else:
                #     users._clear_session() 

            else:
                users._clear_session()

                
        

    def _remove_log_login(self, days):
        """ Cron job """
        # today = datetime.now()
        six_months_ago = datetime.now() - timedelta(days=days)
        log_login_records = self.env['log.login'].search([('time_login', '<', six_months_ago)])
        for log in log_login_records:
            log.unlink()


    def enable_ip_validation(self):
        for rec in self:
            if not rec.ip_address_login_toggle:
                rec.ip_address_login_toggle = True


    def disable_ip_validation(self):
        for rec in self:
            if rec.ip_address_login_toggle:
                rec.ip_address_login_toggle = False


    @api.onchange('access_rights_profile_id')
    def onchange_access_rights_profile_id(self):
        allowed_ip = []
        day_restricted = []
        for rec in self.access_rights_profile_id:
            if self.access_rights_profile_id:
                self.ip_address_ids = [(5, 0, 0)]
                self.day_restricted_ids = [(5, 0, 0)]

                self.ip_address_login_toggle = rec.ip_address_login_toggle
                self.time_restricted = rec.time_restricted
                self.tz = rec.user_tz

                for ip in rec.ip_address_ids:
                    allowed_ip.append((0, 0, {
                        'name': ip.name,
                        'ip_address': ip.ip_address
                    }))
                for day in rec.day_restricted_ids:
                    day_restricted.append((0, 0, {
                        'name': day.name,
                        'day': day.day,
                        'start_time': day.start_time,
                        'end_time': day.end_time
                    }))

                self.ip_address_ids = allowed_ip
                self.day_restricted_ids = day_restricted
            else:
                self.ip_address_login_toggle = False
                self.time_restricted = False
                self.ip_address_ids = False
                self.day_restricted_ids = False

                



class IpAddress(models.Model):
    _name = 'ip.address'

    name = fields.Char(string="Description")
    ip_address = fields.Char(string="IP Address")
    res_user_id = fields.Many2one('res.users')

class DayRestricted(models.Model):
    _name = 'day.restricted'

    name = fields.Char(string="Description")
    day = fields.Selection([
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday')
    ], string="Day")
    start_time = fields.Float(string="Start Time")
    end_time = fields.Float(string="End Time")
    res_user_id = fields.Many2one('res.users')
    tz = fields.Selection('_tz_get', string='Timezone', default=lambda self: self.env.user.tz or 'UTC')

    def _tz_get(self):
        return [(tz, tz) for tz in all_timezones]

    @api.constrains('start_time', 'end_time')
    def _check_start_end_time(self):
        for record in self:
            if record.start_time > record.end_time:
                raise UserError("End Time must be bigger than Start Time")
