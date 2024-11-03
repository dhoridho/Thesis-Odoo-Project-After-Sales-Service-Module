# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrNaturaCategory(models.Model):
    _name = 'hr.natura.category'
    _description = 'Natura Tax Categories'

    name = fields.Char('Name')
    schema_type = fields.Selection([('monthly','Monthly'),('yearly','Yearly')], default='', string="Schema Type")
    max_amount = fields.Float('Maximum Amount')