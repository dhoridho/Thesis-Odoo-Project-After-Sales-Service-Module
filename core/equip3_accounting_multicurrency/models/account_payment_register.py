from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    spot_rate = fields.Float(string='Spot rate', digits=(12, 12))
    exchange_spot_rate = fields.Float(string='Exchange rate')
    spot_rate_boolean = fields.Boolean(string="spot_rate", default=False)


    def _create_payments(self):
        payments = super(AccountPaymentRegister, self)._create_payments()
        if payments.move_id.state == 'posted' and payments.state != 'posted':
        	payments.write({'state' : 'posted'})
	        domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
	        inv_id = self.env['account.move'].search([('name', '=', payments.ref)])
	        if inv_id:
		        payment_lines = payments.move_id.line_ids.filtered_domain(domain)
		        lines = payment_lines
		        lines += inv_id.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
		        lines.reconcile()
        return payments



