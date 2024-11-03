import logging
import requests
import pprint
import json
from requests.exceptions import HTTPError
from werkzeug import urls

from odoo import api, exceptions, fields, models, _, SUPERUSER_ID
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PaymentAcquirerxendit(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('xendit', 'xendit')], ondelete={
                                'xendit': 'set default'})
    xendit_secret_key = fields.Char(
        required_if_provider='xendit', string="Secret key", groups='base.group_user', help="Please Input your xendit api secret key")
    xendit_verification_token = fields.Char(
        required_if_provider='xendit', string="Verification token", groups='base.group_user', help="Please Input your xendit callback verification token")
    xendit_image_url = fields.Char(
        "Checkout Image URL", groups='base.group_user',
        help="A relative or absolute URL pointing to a square image of your "
             "brand or product. As defined in your xendit profile. See: "
             "https://www.xendit.co/")

    def create_xendit_invoice(self, xendit_session_data):
        url = self._get_xendit_api_url()
        user = self.xendit_secret_key
        base_url = self.get_base_url()
        data = {
            'external_id'	: xendit_session_data['external_id'].id,
            'payer_email'	: xendit_session_data['payer_email'],
            'description'	: xendit_session_data['description'],
            'amount'		: xendit_session_data['amount'],
            'success_redirect_url':  urls.url_join(base_url, '/payment/process'),
            'failure_redirect_url':  urls.url_join(base_url, '/payment/process'),
        }
        act = requests.post(url, data=data, auth=(user, ''))
        res = json.loads(act.text)
        if 'error_code' in res:
            raise UserError(res['message'])

        payment = xendit_session_data['external_id']
        payment.xendit_invoice_url = res['invoice_url']
        payment.xendit_id = res['id']
        # return payment
        return res['invoice_url']

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
        for order in payment.sale_order_ids:
            email_act = order.action_quotation_send()
            email_ctx = email_act.get('context', {})
            order.with_context(
                **email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
            order.state = 'sent'
            order._compute_website_order_line()
            order.with_context(send_email=True).action_confirm()
            order._create_invoices()

        return values

    def _get_xendit_api_url(self):
        return "https://api.xendit.co/v2/invoices"


class PaymentTransactionStripe(models.Model):
    _inherit = 'payment.transaction'

    xendit_id = fields.Char(string='Xendit ID', readonly=True)
    xendit_invoice_url = fields.Char(
        string='Xendit invoice url', readonly=True)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _get_payment_chatter_link(self):
        self.ensure_one()
        return '<a href=# data-oe-model=account.payment data-oe-id=%d>%s</a>' % (self.id, self.name)
