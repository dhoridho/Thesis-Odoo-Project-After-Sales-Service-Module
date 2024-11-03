from odoo import api, fields, models, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        for line in self.order_line:
            if line.product_id.is_pack:
                vals = []
                for pack in line.product_id.bi_pack_ids:
                    vals.append(pack.product_id.id)
                for i in vals:
                    qty_done = 0
                    qty_per_pack = 0
                    qty_per_uom = 0
                    done = 0
                    products = self.env['stock.move'].search([('purchase_line_id', '=', line.id), ('product_id', '=', i), ('state', '=', 'done')])
                    for i in products:
                        qty_per_uom = i.purchase_line_id.product_uom_qty / i.purchase_line_id.product_qty
                        qty_done += i.quantity_done
                        qty_per_pack = i.qty_pack * qty_per_uom
                    if qty_per_pack > 0:
                        done = qty_done // qty_per_pack
                    if line.qty_received == 0:
                        line.qty_received = done
                    else:
                        if line.qty_received >= done:
                            line.qty_received = done
        return res