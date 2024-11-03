from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


# depracated
# dont use this table, gonna erase in future
class GroupOfProduct(models.TransientModel):
    _name = 'group.of.product.wizard'
    _description = 'Form to add products to group of product'

    test_field = fields.Char(string='A')
    product_id = fields.Many2one('product.template', string='Product')
    product_name = fields.Char(string='Product Name')
    sales_price = fields.Float(string='Sales Price')
    cost = fields.Float(string='Cost')
    last_purchase_price = fields.Float(string='Last Purchase Price')
    qty_on_hand = fields.Float(string='Quantity on Hand')
    uom = fields.Many2one(comodel_name='uom.uom', string='Unit of Measure')
    group_of_product = fields.Many2one('group.of.product', 'Group Of Product')

    def add_products(self):
        group_of_product_data_id = self._context['group_of_product_data']
        group_of_product_data = self.env['group.of.product'].search([('id', '=', group_of_product_data_id)])
        selected_product = list()
        exist_group = []
        for product in self.ids:
            selected_product += self.env['group.of.product.wizard'].search([('id', '=', product)])
        for product in selected_product:
            temp_product = product.product_id
            if not temp_product.group_of_product:
                temp_product.write({
                        'group_of_product' : group_of_product_data
                    })
                self.gop_product_line(group_of_product_data)
            else:
                exist_group.append(product.id)
        if exist_group:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Confirmation',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'active_model': 'group.of.product.wizard',
                    'active_ids': exist_group,
                },
                'res_model': 'group.of.product.wizard.message',
            }

    def delete_products(self):    
        selected_product_id = self.env.context.get('active_ids', [])
        selected_product = list()
        for product in selected_product_id:
            selected_product += self.search([('id', '=', product)])
        
        for product in selected_product:
            temp_product = product.product_id
            temp_product.write({
                    'group_of_product' : None
                })

        # Refresh group of product's product line
        group_of_product_data_id = self._context['group_of_product_data']
        group_of_product_data = self.env['group.of.product'].search([('id', '=', group_of_product_data_id)])
        self.gop_product_line(group_of_product_data)

    
    def gop_product_line(self, gop_data):
        products = []
        for rec in gop_data:
            products_ids = self.env['product.template'].search([('group_of_product', '=', rec.id)])
            for rec in products_ids:
                res = (0, 0,{
                    'product_name': rec.id,
                    'sales_price':rec.list_price,
                    'cost':rec.standard_price,
                    'last_purchase_price':rec.last_purchase_price,
                    'qty_on_hand':rec.qty_available,
                    'uom':rec.uom_id.id,
                })
                products.append(res)
        gop_data.product_line_ids = [(6, 0, [])]
        gop_data.write({'product_line_ids': products})
            

        
