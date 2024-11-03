from odoo import fields, models, api, _

class allow_ip(models.Model):
    _name = 'allow.ip'
    _description = "Allow IP"

    user_id = fields.Many2one('res.users', 'User')

    name = fields.Char('IP')
    

    