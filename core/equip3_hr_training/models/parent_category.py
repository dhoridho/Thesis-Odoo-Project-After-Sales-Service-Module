from odoo import api, fields, models


class ParentCategory(models.Model):
    _name = 'parent.category'
    _description = 'Parent Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', tracking=True, required=True)
    create_by = fields.Many2one('res.users', 'Created by', default=lambda self: self.env.user)
    create_date = fields.Date('Created on', default=fields.date.today())
    company_id = fields.Many2one('res.company', string='Company', tracking=True, default=lambda self: self.env.company)
