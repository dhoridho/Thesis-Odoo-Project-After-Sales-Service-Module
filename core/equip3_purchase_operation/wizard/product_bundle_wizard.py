
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class bi_wizard_product_bundle(models.TransientModel):
    _inherit = 'wizard.product.bundle.bi'

    def button_add_product_bundle_bi_purchase(self):
        if self.bi_pack_ids:
            for pack in self.bi_pack_ids:
                purchase_order_id = self.env['purchase.order.line'].search([('order_id','=', self._context['active_id']),('product_id','=',pack.product_id.id)])
                if purchase_order_id and  purchase_order_id[0]:
                    purchase_order_line_obj = purchase_order_id[0]
                    purchase_order_line_obj.write({'product_qty': purchase_order_line_obj.product_qty + (pack.qty_uom * self.product_qty)})
                else:
                    self.env['purchase.order.line'].create({'order_id': self._context['active_id'],
                                                        'product_id':pack.product_id.id,
                                                        'name':pack.product_id.name,
                                                        'price_unit':pack.product_id.list_price,
                                                        'product_uom':pack.uom_id.id,
                                                        'product_qty':pack.qty_uom * self.product_qty})
        return True
