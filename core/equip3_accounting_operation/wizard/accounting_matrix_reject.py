# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class AccountingMatrixReject(models.TransientModel):
    _name = "accounting.matrix.reject"
    _description = 'Accounting Matrix Reject'

    reason = fields.Text(string="Reason")

    def action_reject(self):
        move_id = self.env['account.move'].browse([self._context.get('active_id')])
        user = self.env.user
        approving_matrix_line = sorted(move_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            else:
                name += "• %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user, 'approver_state': 'refuse'})
            if move_id.move_type == "out_refund":
                action_id = self.env.ref('account.action_move_out_refund_type')
                template_id = self.env.ref('equip3_accounting_operation.email_template_credit_notes_rejected_matrix')
                # wa_template_id = self.env.ref('equip3_accounting_operation.email_template_rjct_credit_note_wa')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rejected_credit_note')
            elif move_id.move_type == "in_refund":
                action_id = self.env.ref('account.action_move_in_refund_type')
                template_id = self.env.ref('equip3_accounting_operation.email_template_refunds_rejected_matrix')
                # wa_template_id = self.env.ref('equip3_accounting_operation.email_template_rjct_refund_wa')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rejected_refund')
            elif move_id.move_type == "in_invoice":
                action_id = self.env.ref('account.action_move_in_invoice_type')
                template_id = self.env.ref('equip3_accounting_operation.email_template_rejected_bill_matrix')
                # wa_template_id = self.env.ref('equip3_accounting_operation.email_template_rjct_bill_wa')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rejected_bill')
            else:
                action_id = self.env.ref('account.action_move_out_invoice_type')
                template_id = self.env.ref('equip3_accounting_operation.email_template_rejected_matrix')
                # wa_template_id = self.env.ref('equip3_accounting_operation.email_template_inv_wa_reject')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rejection_of_invoice')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            invoice_name = 'Draft Invoice' if move_id.state != 'posted' else move_id.name
            url = base_url + '/web#id='+ str(move_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.move'
            if move_id.move_type in ("out_refund", "in_refund"):
                email_to = move_id.request_partner_id.email
            else:
                email_to = move_id.partner_id.email
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : email_to,
                'rejected_name' : self.env.user.name,
                'feedback' : self.reason,
                'url' : url,
                'create_date': move_id.create_date.date(),
                'invoice_name': invoice_name,
                'date': move_id.create_date.date(),
            }
            template_id.with_context(ctx).send_mail(move_id.id, True)
            move_id._send_whatsapp_message(wa_template_id, move_id.request_partner_id.user_ids, url=url, reason=self.reason)
            move_id.state = 'rejected'
            move_id.approved_user_ids = [(4, self.env.user.id)]