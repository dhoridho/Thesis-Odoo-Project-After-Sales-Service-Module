from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError, Warning
from pytz import all_timezones  

class AccessRightsProfile(models.Model):
    _inherit = 'access.rights.profile'

    ip_address_login_toggle = fields.Boolean(default=False, string="Enable Login Restriction")
    ip_address_ids = fields.One2many('ip.address.arp', 'access_rights_profile_id', string='Allowed IP')
    time_restricted = fields.Boolean(default=False, string="Allowed Time")
    day_restricted_ids = fields.One2many('day.restricted.arp', 'access_rights_profile_id', string='Allowed Days')
    user_tz = fields.Selection(
            selection='_tz_get',
            string='Timezone',
            default=lambda self: self._context.get('tz'),
            help="When printing documents and exporting/importing data, time values are computed according to this timezone.\n"
                "If the timezone is not set, UTC (Coordinated Universal Time) is used.\n"
                "Anywhere else, time values are computed according to the time offset of your web client."
        )

    def _tz_get(self):
        return [(tz, tz) for tz in all_timezones]

    def enable_ip_validation(self):
        for rec in self:
            if not rec.ip_address_login_toggle:
                rec.ip_address_login_toggle = True


    def disable_ip_validation(self):
        for rec in self:
            if rec.ip_address_login_toggle:
                rec.ip_address_login_toggle = False

    def disable_setting_to_all_user(self):
        user_list = []
        user_list_arp = self.env['res.users'].search([('access_rights_profile_id', '=', self.id)])
        for user in user_list_arp:
            user_list.append(user.id)
        for rec in self:
            if user_list:
                user_list = self.env['res.users'].search([('id', 'in', user_list)])
                for user in user_list:
                    user.ip_address_login_toggle = False
                    user.time_restricted = False
                    user.ip_address_ids = [(5, 0, 0)]
                    user.day_restricted_ids = [(5, 0, 0)]

    def apply_setting_to_all_user(self):
        user_list = []
        user_list_arp = self.env['res.users'].search([('access_rights_profile_id', '=', self.id)])
        for user in user_list_arp:
            user_list.append(user.id)
        for rec in self:
            if user_list:
                user_list = self.env['res.users'].search([('id', 'in', user_list)])
                for user in user_list:
                    user.ip_address_login_toggle = rec.ip_address_login_toggle
                    user.time_restricted = rec.time_restricted
                    user.tz = rec.user_tz
                    user.ip_address_ids = [(5, 0, 0)]
                    user.day_restricted_ids = [(5, 0, 0)]

                    allowed_ip = []
                    day_restricted = []
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

                    user.ip_address_ids = allowed_ip
                    user.day_restricted_ids = day_restricted
        
    def apply_setting_to_all_user_same_profile(self):
        for rec in self:
            if rec.user_ids:
                for user in rec.user_ids:
                    user.ip_address_login_toggle = rec.ip_address_login_toggle
                    user.time_restricted = rec.time_restricted
                    user.tz = rec.user_tz
                    user.ip_address_ids = [(5, 0, 0)]
                    user.day_restricted_ids = [(5, 0, 0)]

                    allowed_ip = []
                    day_restricted = []
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

                    user.ip_address_ids = allowed_ip
                    user.day_restricted_ids = day_restricted


class IpAddressArp(models.Model):
    _name = 'ip.address.arp'

    name = fields.Char(string="Description")
    ip_address = fields.Char(string="IP Address")
    access_rights_profile_id = fields.Many2one('access.rights.profile')


class DayRestrictedArp(models.Model):
    _name = 'day.restricted.arp'

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
    access_rights_profile_id = fields.Many2one('access.rights.profile')