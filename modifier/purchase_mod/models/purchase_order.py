from odoo import models

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def action_cancel(self):
        for line in self:
            line.write({'state': 'cancel'})
        return True

    def write(self, values):
        for line in self:
            super(PurchaseOrderLine, line).write(values)
        return True