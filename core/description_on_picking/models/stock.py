# Copyright 2014-2018 Tecnativa - Pedro M. Baeza


from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = "stock.move"


    product_description = fields.Char(string="Product Description"
                                      , compute='_compute_total_packages'
                                      )
    @api.depends('product_id','product_description')
    def _compute_total_packages(self):
        for line in self:
            if line.picking_code == 'incoming':
                print("picking_type_id : ", line.picking_code)
                if line.product_id.description_pickingin == False:
                    print("sono in if: ")
                    print("line name: ", line.name)
                    line.product_description = line.name
                else:
                    print("sono in ELSE: ")
                    print("line name: ", line.name)
                    line.product_description = line.name + ' ' + (
                        line.product_id.description_pickingin)

            if line.picking_code == 'outgoing':
                if line.product_id.description_pickingout == False:
                    line.product_description = line.name
                else:
                    line.product_description = line.name + ' ' + (
                        line.product_id.description_pickingout)
            if line.picking_code == 'internal':
                if line.description_picking == False:
                    line.product_description = line.name
                else:
                    line.product_description = line.name + ' ' + (
                        line.description_picking)