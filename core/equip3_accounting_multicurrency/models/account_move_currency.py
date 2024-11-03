from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    manual_currency_exchange_inverse_rate = fields.Float(string='Inverse Rate', digits=(12, 12))
    manual_currency_exchange_rate = fields.Float(string='Manual Currency Exchange Rate', digits=(12, 12), default=0.0)

    @api.onchange('manual_currency_exchange_inverse_rate')
    def _oncange_rate_conversion(self):
        if self.manual_currency_exchange_inverse_rate:
            self.manual_currency_exchange_rate = 1 / self.manual_currency_exchange_inverse_rate
    
    @api.onchange('manual_currency_exchange_rate')
    def _oncange_rate(self):
        if self.manual_currency_exchange_rate:
            self.manual_currency_exchange_inverse_rate = 1 / self.manual_currency_exchange_rate
