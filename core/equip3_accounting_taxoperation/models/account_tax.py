from odoo.exceptions import UserError
from odoo import api, fields, models, _

class AccountTax(models.Model):
    _inherit = 'account.tax'

    tax_paid_account = fields.Many2one('account.account', string='Tax Paid Account', tracking=True)
    price_include_total = fields.Boolean(string="Included in Price Based on Total Amount", tracking=True)
    pay_separately = fields.Boolean(string="To Pay Separately", tracking=True)

    def write(self, vals):
        if 'amount' in vals and 'price_include_total' in vals and vals['price_include_total']:
            if vals['amount'] >= 0:
                raise UserError(_('For Included in Price Based on Total Amount, Amount must be Negative'))
        return super(AccountTax, self).write(vals)

    @api.model
    def create(self, vals):
        if 'amount' in vals and 'price_include_total' in vals and vals['price_include_total']:
            if vals['amount'] >= 0:
                raise UserError(_('For Included in Price Based on Total Amount, Amount must be Negative'))
        return super(AccountTax, self).create(vals)
