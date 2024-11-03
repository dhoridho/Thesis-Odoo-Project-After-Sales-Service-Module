# -*- coding: utf-8 -*-
from odoo import fields, models, api, _

    
class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    
    signature_to_confirm = fields.Boolean()

    @api.model
    def create(self, vals):
        if self.env.context.get('res_partner_search_mode') == 'customer':
            vals['is_customer'] = True
        elif self.env.context.get('res_partner_search_mode') == 'supplier':
            vals['is_vendor'] = True

        result = super(ResPartner, self).create(vals)
        return result