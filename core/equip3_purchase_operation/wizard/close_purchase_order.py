from odoo import _, api, fields, models


class ClosePurchaseOrder(models.TransientModel):
    _name = "close.purchase.order"
    _description = "Close Purchase Order"

    purchase_id = fields.Many2one('purchase.order', string="Purchase Order")

    def close_purchase_order(self):
        for rec in self:
            rec.purchase_id.close_purchase_order()