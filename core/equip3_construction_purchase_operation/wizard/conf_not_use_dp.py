from odoo import api , models, fields


class ConfirmationDownPaymentPurchase(models.TransientModel):
    _name = 'confirm.downpayment.purchase'
    _description = 'Confirmation Not Use Down Payment '

    txt = fields.Text(string="Confirmation",default="Are you sure you don't want to use Down Payment on this contract?")

    def action_confirm(self):
        purchase = self.env['purchase.order'].browse([self._context.get('active_id')])
        purchase.write({'use_dp': False, 'use_retention': False})
        if purchase.is_subcontracting:
            return purchase.button_confirm()

    