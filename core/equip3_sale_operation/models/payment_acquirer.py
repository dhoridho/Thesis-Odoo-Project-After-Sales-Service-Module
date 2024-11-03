from odoo import models, fields, api, _


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    def xendit_form_generate_values(self, values):
        self.ensure_one()
        payment = self.env['payment.transaction'].search(
            [('reference', '=', values['reference'])])
        values.update({
            'external_id'	: payment,
            'payer_email'	: values.get('partner_email') or values.get('billing_partner_email'),
            'description'	: values['reference'],
            'amount'		: payment.amount,
        })
        values['invoice_url'] = self.create_xendit_invoice(values)
        return values