from odoo import api, fields, models
from odoo.exceptions import UserError


class ParentProperty(models.Model):
    _name = 'parent.property'
    _description = 'Parent Property'

    name = fields.Char(string='Name', required=True)
