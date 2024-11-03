
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def print_purchase_order(self):
        self.ensure_one()
        context = dict(self.env.context) or {}
        context.update({
            'default_purchase_order_id': self.id,
        })
        return {
            'name': _('Print Report'),
            'res_model': 'print.purchase.report',
            'type': 'ir.actions.act_window',
            "view_mode": 'form',
            "target": "new",
            'context': context,
        }

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    analytic_tag_ids = fields.Many2many(string='Analytic Group')
    image_256 = fields.Binary(string='Image', related="product_id.image_256")
    
