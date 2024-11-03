# -*- coding: utf-8 -*

from odoo import models, fields, api

class MaintenanceRequestCustomLines(models.Model):
    _name = 'maintenance.request.custom.lines'
    _description = "Maintenance Request Custom Lines"
    
    maint_request_custom_id = fields.Many2one(
        'maintenance.request',
        string="Maintenance Request"
    )
    product_id = fields.Many2one(
        'product.product',
        string="Product",
        required=True
    )
    qty = fields.Float(
        string = "Quantity",
        default=1.0,
        required=True
    )
    product_uom = fields.Many2one(
        'uom.uom',
        string="UOM",
        required=True
    )
    price = fields.Float(
        string = "Price",
        required=True
    )
    notes = fields.Text(
       string="Description", 
    )
    is_so_line_created = fields.Boolean(
        string='Is Quotation Created ?',
    )
     
    @api.onchange('product_id')
    def product_id_change(self):
        for rec in self:
            rec.product_uom = rec.product_id.uom_id.id
            rec.price = rec.product_id.lst_price
