# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ResBranch(models.Model):
    _inherit = 'res.branch'
    
    branch_npwp = fields.Char('Branch NPWP')
    tax_cutter_name = fields.Many2one('res.users', string='Tax Cutter Name')
    tax_cutter_npwp = fields.Char('Tax Cutter NPWP')