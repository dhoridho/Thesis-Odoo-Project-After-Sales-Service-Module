# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class MultipulReceiptPaymentMatrixReject(models.TransientModel):
    _name = "multi.receipt.matrix.reject"
    _description = 'Receipt Payment Matrix Reject'

    reason = fields.Text(string="Reason")

    def action_reject(self):
        multi_receipt_id = self.env['account.multipayment'].browse([self._context.get('active_id')])
        user = self.env.user
        approving_matrix_line = sorted(multi_receipt_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            else:
                name += "• %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
            if multi_receipt_id.partner_type == "supplier":
                action_id = self.env.ref('equip3_accounting_operation.action_account_multipayment_vendor')
                template_id = self.env.ref('equip3_accounting_operation.email_template_payment_giro_rejected_matrix')
                wa_notification = multi_receipt_id.is_allowed_to_wa_notification_multi_payment
                # wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rjct_payment_giro_wa')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rejected_for_payment_giro')
            else:
                action_id = self.env.ref('equip3_accounting_operation.action_account_multipayment_customer')
                template_id = self.env.ref('equip3_accounting_operation.email_template_receipt_giro_rejected_matrix')
                wa_notification = multi_receipt_id.is_allowed_to_wa_notification_multi_receipt
                # wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rjct_receipt_giro_wa')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rejected_for_receipt_giro')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id='+ str(multi_receipt_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.multipayment'

            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : multi_receipt_id.request_partner_id.email,
                'rejected_name' : self.env.user.name,
                'feedback' : self.reason,
                'url' : url,
                'create_date': multi_receipt_id.create_date.date(),
                'date': multi_receipt_id.create_date.date(),
            }
            template_id.with_context(ctx).send_mail(multi_receipt_id.id, True)
            phone_num = str(multi_receipt_id.request_partner_id.mobile) or str(multi_receipt_id.request_partner_id.mobile)
            if multi_receipt_id.payment_type == 'payment':
                if wa_notification:
                    if multi_receipt_id.partner_type == "supplier":
                        multi_receipt_id._send_wa_reject_multi_payment(multi_receipt_id.request_partner_id.name, phone_num, multi_receipt_id.create_date.date(), self.env.user.name, self.reason)
                    else:
                        multi_receipt_id._send_wa_reject_multi_receipt(multi_receipt_id.request_partner_id.name, phone_num, multi_receipt_id.create_date.date(), self.env.user.name, self.reason)
            else:
                multi_receipt_id._send_whatsapp_message(wa_template_id, multi_receipt_id.request_partner_id, url=url, reason=self.reason)

            multi_receipt_id.state = 'rejected'
