from odoo import api , models, fields


class ConfirmationRetentionPurchase(models.TransientModel):
    _name = 'confirm.retention.purchase'
    _description = 'Confirmation Not Use Retention '

    txt = fields.Text(string="Confirmation",default="Are you sure you don't want to use retention on this contract?")

    def action_confirm(self):
        purchase = self.env['purchase.order'].browse([self._context.get('active_id')])
        purchase.write({'use_retention': False})
        if purchase.is_subcontracting:
            return purchase.button_confirm()

    