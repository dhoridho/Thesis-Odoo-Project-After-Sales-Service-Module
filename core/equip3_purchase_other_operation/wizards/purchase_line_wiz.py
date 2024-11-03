from odoo import fields, models


class PurchaseLineWiz(models.TransientModel):
    _name = 'purchase.line.wiz'
    _description = 'Purchase Line Wizard'

    purchase_order_line_id = fields.Many2one(comodel_name='purchase.order.line', string='Purchase Order Line')
    name = fields.Char(string='Reason', required=True)


    def action_reject(self):
        self.purchase_order_line_id.action_cancel()
        self.purchase_order_line_id.feedback = self.name
