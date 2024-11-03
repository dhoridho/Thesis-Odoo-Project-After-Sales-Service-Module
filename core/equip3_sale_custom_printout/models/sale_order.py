
from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = "sale.order"

    def quotation_send_report(self):
        context = dict(self.env.context) or {}
        return {
            'name': "Print Report",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.report.wizard',
            'target': 'new',
            'context': context,
        }
