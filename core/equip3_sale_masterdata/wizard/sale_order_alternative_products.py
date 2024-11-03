
from odoo import api , models, fields 


class SaleOrderAlternativeProduct(models.TransientModel):
    _name = 'sale.order.alternative.product'
    _description = 'Sale Order Alternative Product'

    alter_product_ids = fields.Many2many('product.product', string="Alternative Products")
    product_id = fields.Many2one('product.product', string="Product")
    sale_line_id = fields.Many2one('sale.order.line', string="Sale Line")
    selected_product_id = fields.Many2one('product.product', string="Selected Product", domain="[('id', 'in', alter_product_ids)]")

    @api.onchange('product_id')
    def get_product_id(self):
        alternative = self.product_id.alternative_product_ids.ids
        alternative.extend(self.product_id.product_tmpl_id.alternative_product_ids.ids)
        self.alter_product_ids = alternative
        return{
            'domain' : {'alter_product_ids' : [('id', 'in' , alternative)]}
        }
    
    def action_replace(self):
        data = []
        data.append((0, 0, {
                    'product_id' : self.selected_product_id.id,
                    'name' : self.selected_product_id.display_name,
                    'product_uom_qty' : 1,
                    'sale_line_sequence' : self.sale_line_id.sale_line_sequence,
                    'product_uom' : self.selected_product_id.uom_id.id,
                    'price_unit' : self.selected_product_id.lst_price,
                }))
        self.sale_line_id.order_id.order_line = data
        self.sale_line_id.unlink()
