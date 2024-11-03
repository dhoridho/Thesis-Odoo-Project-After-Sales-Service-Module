# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime 
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class AccountingMatrixReject(models.TransientModel):
    _name = "voucher.matrix.reject"
    _description = 'Voucher Matrix Reject'

    reason = fields.Text(string="Reason")

    def action_reject(self):
        voucher_id = self.env['account.voucher'].browse([self._context.get('active_id')])
        user = self.env.user
        approving_matrix_line = sorted(voucher_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            else:
                name += "• %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
            if voucher_id.voucher_type == 'sale':
                action_id = self.env.ref('account.action_move_out_invoice_type')
                template_id = self.env.ref('equip3_accounting_operation.email_template_other_income_rejected_matrix')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rejected_other_income')
                invoice_name = 'Draft Other Income' if voucher_id.state != 'posted' else voucher_id.name
            elif voucher_id.voucher_type == 'purchase':
                action_id = self.env.ref('account.action_move_in_invoice_type')
                template_id = self.env.ref('equip3_accounting_operation.email_template_other_expense_rejected_matrix')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rejected_other_expense')
                invoice_name = 'Draft Other Expense' if voucher_id.state != 'posted' else voucher_id.name
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')       
            url = base_url + '/web#id='+ str(voucher_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.voucher'
            email_to = voucher_id.request_partner_id.email
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : email_to,
                'rejected_name' : self.env.user.name,
                'feedback' : self.reason,
                'url' : url,
                'create_date': voucher_id.create_date.date(),
                'invoice_name': invoice_name,
                'date': voucher_id.create_date.date(),
                'partner_name': voucher_id.request_partner_id.name,

            }
            template_id.with_context(ctx).send_mail(voucher_id.id, True)
            if voucher_id.is_allowed_to_wa_notification:
                voucher_id._send_wa_reject_other_income_expense(voucher_id.request_partner_id.name, voucher_id.request_partner_id.mobile, voucher_id.create_date.date(), self.env.user.name, self.reason)
            voucher_id.state = 'rejected'