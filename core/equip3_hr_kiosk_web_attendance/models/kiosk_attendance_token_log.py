from odoo import api, fields, models, _

class KioskAttendanceTokenLog(models.Model):
    _name = 'kiosk.attendance.token.log'

    token = fields.Char('Token')
    user_id = fields.Many2one('res.users', 'User')
    is_used = fields.Boolean(string="Is Used")
    expired_date = fields.Datetime(string="Expired")