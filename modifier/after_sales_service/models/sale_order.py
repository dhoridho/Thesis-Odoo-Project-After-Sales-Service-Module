from datetime import timedelta
from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """Override the confirm method to create warranty notifications."""
        result = super(SaleOrder, self).action_confirm()
        for order in self:
            for line in order.order_line:
                product = line.product_id.product_tmpl_id
                product_id = line.product_id

                if product.has_warranty:
                    warranty_end_date = fields.Date.today() + timedelta(days=product.warranty_period_id.duration)
                    self.env['warranty.notification'].sudo().create({
                        'partner_id': order.partner_id.id,
                        'product_id': product_id.id,
                        'warranty_end_date': warranty_end_date,
                        'notification_status': 'no',
                    })
        return result

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warranty_expire_date = fields.Date(string='Warranty Expire Date', compute='_compute_warranty_expire_date', store=True, readonly=True)

    @api.depends('order_id.date_order', 'product_id.warranty_period_id')
    def _compute_warranty_expire_date(self):
        for line in self:
            if line.product_id and line.product_template_id.warranty_period_id:
                line.warranty_expire_date = line.order_id.date_order + timedelta(days=line.product_template_id.warranty_period_id.duration)
            else:
                line.warranty_expire_date = False

