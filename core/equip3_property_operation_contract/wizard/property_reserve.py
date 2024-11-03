# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date,datetime
from dateutil.relativedelta import relativedelta

class PropertyBook(models.TransientModel):
    _name = 'property.rent.contract'
    _description = "Reserve Rental Property"

    contract_id = fields.Many2one('agreement',string="Contract Template", required=True, domain=[("is_template", "=", True), ("invoice_type", "=", "recurring")])
    property_id = fields.Many2one('product.product', required=True, domain=[('is_property','=',True)])
    name = fields.Text(string="Contract Title", required=True)
    renter_id = fields.Many2one('res.users','Renter')
    deposite = fields.Float(string="Monthly Rent", required=True)
    state = fields.Selection([('avl','Available'),('reserve','Reserve')], string="Status", default='avl')
    
    # get rent Property details.
    @api.model
    def default_get(self,default_fields):
        res = super(PropertyBook, self).default_get(default_fields)
        ctx = self._context
        property_data = {
            'property_id':ctx.get('property_id'),
            'renter_id':ctx.get('renter_id'),
            'deposite':ctx.get('deposite')
        }
        res.update(property_data)
        return res

    def create_rent_contract(self):
        self.ensure_one()
        res = self.contract_id.create_new_agreement()
        agreement = self.env[res["res_model"]].browse(res["res_id"])
        agr = agreement.write(
            {
                "name": self.name,
                "description": self.name,
                "template_id": self.contract_id.id,
                "partner_id": self.renter_id.partner_id.id,
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
            self.env['product.product'].browse(self.property_id.id).write({'state':'reserve', 'is_reserved':True, 'user_id':self.renter_id.id})
        return res

