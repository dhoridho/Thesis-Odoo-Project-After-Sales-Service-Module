from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = 'product.product'

    last_sales_price = fields.Float(string="Last Sales Price")
    last_sales_date = fields.Date(string="Last Sales Date")
    last_customer_id = fields.Many2one(comodel_name="res.partner", string="Last Customer")
    product_product_label_line_ids = fields.One2many('customer.product.template.line', 'product_id', string='Product Label')

    def set_product_last_sales(self, order_id=False):
        for product in self:
            list_product = []
            if product.id not in list_product:
                self.env.cr.execute("""
                    SELECT l.price_unit, l.product_uom, l.order_id, o.date_order, o.partner_id
                    FROM sale_order_line as l
                    INNER JOIN sale_order as o
                    ON l.order_id = o.id
                    WHERE l.product_id = %s and o.state in ('sale','done')
                    ORDER BY l.order_id DESC LIMIT 1
                """ % (product.id))
                line_id = self.env.cr.fetchall()
                list_product.append(product.id)
            else:
                continue

            if line_id:
                date_order = None if line_id[0][3] == 'False' else line_id[0][3]
                last_customer = line_id[0][4]
                price_unit_uom = line_id[0][0]
            else:
                date_order = None
                last_customer = None
                price_unit_uom = 0
            self._cr.execute("""UPDATE product_product SET last_sales_date=%s, last_sales_price=%s, last_customer_id=%s WHERE id = %s""", (date_order, price_unit_uom, last_customer, product.id))
            self._cr.commit()
            self._cr.execute("""UPDATE product_template SET last_sales_date=%s, last_sales_price=%s, last_customer_id=%s WHERE id = %s""", (date_order, price_unit_uom, last_customer, product.product_tmpl_id.id))
            self._cr.commit()

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_label_line_ids = fields.One2many('customer.product.template.line', 'product_template_id', string='Product Label')
    
    show_customer_product_label = fields.Boolean('Show Customer Product Label Configuration', compute="_compute_show_customer_product_label")
    last_sales_price = fields.Float(string="Last Sales Price")
    last_sales_date = fields.Date(string="Last Sales Date")
    last_customer_id = fields.Many2one(comodel_name="res.partner", string="Last Customer")

    def _compute_show_customer_product_label(self):
        self.show_customer_product_label = self.env['ir.config_parameter'].sudo().get_param('show_customer_product_label', False)