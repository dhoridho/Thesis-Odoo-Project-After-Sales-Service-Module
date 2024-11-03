# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class AccountingMatrixReject(models.TransientModel):
    _name = "internal.matrix.reject"
    _description = 'Internal Matrix Reject'

    reason = fields.Text(string="Reason")

    def action_reject(self):
        internal_cash_id = self.env['account.internal.transfer'].browse([self._context.get('active_id')])
        user = self.env.user
        approving_matrix_line = sorted(internal_cash_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            else:
                name += "• %s: Rejected - %s" % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
            action_id = self.env.ref('equip3_accounting_operation.action_account_internal_transfer')
            template_id = self.env.ref('equip3_accounting_operation.email_template_internal_cb_rejected_matrix')
            # wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rjct_internal_transfer_wa')
            wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_rejected_for_internal_transfer')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id='+ str(internal_cash_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.internal.transfer'

            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : internal_cash_id.request_partner_id.email,
                'rejected_name' : self.env.user.name,
                'feedback' : self.reason,
                'url' : url,
                'create_date': internal_cash_id.create_date.date(),
                'date': internal_cash_id.create_date.date(),
            }

            template_id.with_context(ctx).send_mail(internal_cash_id.id, True)
            internal_cash_id._send_whatsapp_message(wa_template_id, internal_cash_id.request_partner_id.user_ids, url=url, reason=self.reason)
            internal_cash_id.state = 'rejected'