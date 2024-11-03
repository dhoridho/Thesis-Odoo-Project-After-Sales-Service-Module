from odoo import _, api, fields, models

# depracated
# dont use this table, gonna erase in future
class GroupOfProductMessage(models.TransientModel):
    _name = 'group.of.product.wizard.message'
    _description = 'Form to add products to group of product Message'

    def add_products(self):
        group_of_product_data_id = self._context['group_of_product_data']
        group_of_product_data = self.env['group.of.product'].search([('id', '=', group_of_product_data_id)])
        selected_product_id = self.env.context.get('active_ids', [])
        selected_product = list()
        for product in selected_product_id:
            selected_product += self.env['group.of.product.wizard'].search([('id', '=', product)])

        for product in selected_product:
            temp_product = product.product_id
            temp_product.write({
                    'group_of_product' : group_of_product_data
                })

        # Add products to group of product's product line
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
