# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class bi_wizard_product_bundle(models.TransientModel):
    _name = 'wizard.product.bundle.bi'
    _description = 'Wizard Product Bundle BI'
    product_id = fields.Many2one('product.product',string='Bundle',required=True)
    product_qty = fields.Integer('Quantity',required=True ,default=1)
    bi_pack_ids = fields.One2many('bi.product.pack', related='product_id.bi_pack_ids', string="Select Products",readonly=False)

    def button_add_product_bundle_bi(self):
        if self.bi_pack_ids:
            for pack in self.bi_pack_ids:
                sale_order_id = self.env['sale.order.line'].search([('order_id','=', self._context['active_id']),('product_id','=',pack.product_id.id)])
                if sale_order_id and  sale_order_id[0] :
                     sale_order_line_obj = sale_order_id[0]
                     sale_order_line_obj.write({'product_uom_qty': sale_order_line_obj.product_uom_qty + (pack.qty_uom * self.product_qty)})


                else:
                     self.env['sale.order.line'].create({'order_id':self._context['active_id'],
                                                    'product_id':pack.product_id.id,
                                                    'name':pack.product_id.name,
                                                    'price_unit':pack.product_id.list_price,
                                                    'product_uom':pack.uom_id.id,
                                                    'product_uom_qty':pack.qty_uom * self.product_qty
                                                    })

        return True
