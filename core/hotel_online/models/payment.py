from datetime import datetime

from odoo import models, fields, api, _
from odoo.tools.float_utils import float_compare
import logging
import pprint
from . import reservation as res

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    sale_order_id = fields.Many2one('hotel.reservation', 'Sale Order')

    def _check_or_create_sale_tx(self, order, acquirer, payment_token=None, tx_type='form', add_tx_values=None, reset_draft=True):
        # print("\n\n\n\n _check_or_create_sale_tx=======self,acquirer==", self, acquirer)
        tx = self
        if not tx:
            tx = self.search([('reference', '=', order.name)], limit=1)

        if tx.state in ['error', 'cancel']:  # filter incorrect states
            tx = False
        if (tx and tx.acquirer_id != acquirer) or (tx and tx.sale_order_id != order):  # filter unmatching
            tx = False
        if tx and payment_token and tx.payment_token_id and payment_token != tx.payment_token_id:  # new or distinct token
            tx = False

        # still draft tx, no more info -> rewrite on tx or create a new one depending on parameter
        if tx and tx.state == 'draft':
            if reset_draft:
                tx.write(dict(
                    # self.on_change_partner_id(order.partner_id.id).get('value', {}),
                    amount=order.total_cost1 if isinstance(
                        order, res.hotel_reservation) else order.amount_total,
                    type=tx_type)
                )
            else:
                tx = False

        reference = "VALIDATION-%s-%s" % (self.id,
                                          datetime.now().strftime('%y%m%d_%H%M%S'))
        if not tx:
            tx_values = {
                'acquirer_id': acquirer.id,
                'type': tx_type,
                'amount': order.total_cost1 if isinstance(order, res.hotel_reservation) else order.amount_total,
                'currency_id': order.pricelist_id.currency_id.id,
                'partner_id': order.partner_id.id,
                'partner_country_id': order.partner_id.country_id.id,
                'reference': reference,
                'sale_order_id': order.id,
            }
            # print("\n\n\n tx_valueesssssssss:", tx_values)
            if add_tx_values:
                tx_values.update(add_tx_values)
            if payment_token and payment_token.sudo().partner_id == order.partner_id:
                tx_values['payment_token_id'] = payment_token.id

            tx = self.create(tx_values)
            # print("\n\n\n\n tx=====", tx)

        # update quotation
        order.write({
            'payment_tx_id': tx.id,
        })

        return tx

    def render_sale_button(self, invoice, return_url, submit_txt=None, render_values=None):
        values = {
            'return_url': return_url,
            'partner_id': invoice.partner_id.id,
            'type':'form',
        }
        if render_values:
            values.update(render_values)
        # print("\n\n\n\nrender_sale_button---,self.reference, invoice.total_cost1, invoice.currency_id,values  ",
        #       self.reference, invoice.total_cost1, invoice.currency_id, values)

        return self.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
            self.reference,
            invoice.total_cost1,
            invoice.currency_id.id,
            values=values,
        )

    def _confirm_so(self):
        """ Check tx state, confirm the potential SO """
        self.ensure_one()
        if self.sale_order_id.state not in ['draft', 'sent', 'sale']:
            _logger.warning('<%s> transaction STATE INCORRECT for order %s (ID %s, state %s)',
                            self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id, self.sale_order_id.state)
            return 'pay_sale_invalid_doc_state'
        if not float_compare(self.amount, self.sale_order_id.total_cost1, 2) == 0:
            _logger.warning('<%s> transaction AMOUNT MISMATCH for order %s (ID %s)',
                            self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
            return 'pay_sale_tx_amount'

        if self.state == 'authorized' and self.acquirer_id.capture_manually:
            _logger.info('<%s> transaction authorized, auto-confirming order %s (ID %s)',
                         self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
            if self.sale_order_id.state in ('draft', 'sent'):
                self.sale_order_id.with_context(
                    send_email=True).action_confirm()

        if self.state == 'done':
            _logger.info('<%s> transaction completed, auto-confirming order %s (ID %s) and generating invoice',
                         self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
            if self.sale_order_id.state in ('draft', 'sent'):
                self.sale_order_id.with_context(
                    send_email=True).action_confirm()
            self._generate_and_pay_invoice()
        elif self.state not in ['cancel', 'error'] and self.sale_order_id.state == 'draft':
            _logger.info('<%s> transaction pending/to confirm manually, sending quote email for order %s (ID %s)',
                         self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
#             self.sale_order_id.force_quotation_send()
        else:
            _logger.warning('<%s> transaction MISMATCH for order %s (ID %s)',
                            self.acquirer_id.provider, self.sale_order_id.name, self.sale_order_id.id)
            return 'pay_sale_tx_state'
        return True
