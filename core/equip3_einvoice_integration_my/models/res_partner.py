# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

    
class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    
    partner_tin = fields.Char()
    partner_brn = fields.Char()
    partner_ttx = fields.Char()
    partner_sst = fields.Char()