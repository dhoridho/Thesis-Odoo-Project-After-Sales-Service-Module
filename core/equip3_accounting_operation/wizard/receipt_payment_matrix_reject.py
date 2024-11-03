# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class ReceiptPaymentMatrixReject(models.TransientModel):
    _name = "receipt.payment.matrix.reject"
    _description = 'Receipt Payment Matrix Reject'

    reason = fields.Text(string="Reason")

    def action_reject(self):
        receipt_id = self.env['account.payment'].browse([self._context.get('active_id')])
        user = self.env.user
        approving_matrix_line = sorted(receipt_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            else:
                name += "• %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
            if receipt_id.payment_type == 'inbound':
                action_id = self.env.ref('account.action_account_payments')
                template_id = self.env.ref('equip3_accounting_operation.email_template_receipt_rejected_matrix')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rejected_receipt')
                invoice_name = 'Draft Receipt' if receipt_id.state != 'posted' else receipt_id.name
            else:
                action_id = self.env.ref('account.action_account_payments_payable')
                template_id = self.env.ref('equip3_accounting_operation.email_template_payment_rejected_matrix')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rejected_payment')
                invoice_name = 'Draft Payment' if receipt_id.state != 'posted' else receipt_id.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')    
            url = base_url + '/web#id='+ str(receipt_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.payment'
            email_to = receipt_id.request_partner_id.email
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : email_to,
                'rejected_name' : self.env.user.name,
                'feedback' : self.reason,
                'url' : url,
                'create_date': receipt_id.create_date.date(),
                'invoice_name': invoice_name,
                'date': receipt_id.create_date.date(),
                'partner_name': receipt_id.request_partner_id.name,

            }
            template_id.with_context(ctx).send_mail(receipt_id.id, True)
            receipt_id._send_whatsapp_message(wa_template_id, receipt_id.request_partner_id.user_ids, url=url, reason=self.reason)
            receipt_id.state = 'rejected'
            receipt_id.approval_invoice_id.is_register_payment_done = False
