from odoo import models, fields
from odoo.exceptions import ValidationError, AccessDenied, UserError


class LogLogin(models.Model):
    _name = 'log.login'
    _order = 'time_login desc'

    ip_address = fields.Char(string="IP Address")
    user_id = fields.Many2one('res.users', string="User")
    state = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="State")
    time_login = fields.Datetime(string="Time Login")





