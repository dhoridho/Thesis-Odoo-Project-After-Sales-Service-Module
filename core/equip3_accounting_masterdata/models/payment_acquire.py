from odoo import models


class PaymentAcquire(models.Model):
    _inherit = "payment.acquirer"

    def recompute_and_go(self):
        action = self.env['ir.actions.actions']._for_xml_id('payment.action_payment_acquirer')
        action['domain'] = [('id', '!=', self.env.ref('payment.payment_acquirer_odoo_by_adyen').id)]
        return action
