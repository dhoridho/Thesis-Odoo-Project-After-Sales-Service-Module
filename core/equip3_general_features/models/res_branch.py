
from odoo import models, fields, api, _


class ResBranch(models.Model):
    _name = 'res.branch'
    _inherit = ['res.branch', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=True)
    company_id = fields.Many2one(tracking=True)
    telephone = fields.Char(tracking=True)
    address = fields.Text(tracking=True)

    street = fields.Char('Street', tracking=True)
    street_2 = fields.Char('Street2', tracking=True)
    city = fields.Char('City', tracking=True)
    state_id = fields.Many2one('res.country.state',string="State", tracking=True)
    country_id = fields.Many2one('res.country',string="Country", tracking=True)
    zip_code = fields.Char('Zip', tracking=True)
