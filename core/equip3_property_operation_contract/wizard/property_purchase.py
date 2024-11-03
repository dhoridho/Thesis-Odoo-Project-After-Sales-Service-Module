# -*- coding: utf-8 -*-

from odoo import models,fields,api,_
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class PropertyBuy(models.TransientModel):
    _name = "property.buy.contract"
    _description = "Buy New Propery"
    
    contract_id = fields.Many2one('agreement',string="Contract Template", required=True, domain=[("is_template", "=", True), ("invoice_type", "=", "non_recurring")])
    property_id = fields.Many2one('product.product', required=True, domain=[('is_property','=',True)])
    name = fields.Text(string="Contract Title", required=True)
    purchaser_id = fields.Many2one('res.partner')
    property_price = fields.Float(string="Price")
    state = fields.Selection([('avl','Available'),('sold','Sold')], string="Status", default='avl')

    @api.model
    def default_get(self,default_fields):
        res = super(PropertyBuy, self).default_get(default_fields)
        ctx = self._context
        property_data = {
            'property_id':ctx.get('property_id'),
            'purchaser_id':ctx.get('purchaser_id'),
            'property_price':ctx.get('property_price')
        }
        res.update(property_data)
        return res

    def create_buy_contract(self):
        self.ensure_one()
        res = self.contract_id.create_new_agreement()
        agreement = self.env[res["res_model"]].browse(res["res_id"])
        agr = agreement.write(
            {
                "name": self.name,
                "description": self.name,
                "template_id": self.contract_id.id,
                "partner_id": self.purchaser_id.id,
                "property_id": self.property_id.id,
                "line_ids": [(0, 0, {
                    "product_id": self.property_id.id,
                    "uom_id": self.property_id.uom_id.id,
                    "name": self.property_id.name,
                    "qty": 1
                })],
            }
        )
        if agr:
            self.property_id.write({'state':'sold','user_id':self.env.user.id,'is_sold':True})
        return res