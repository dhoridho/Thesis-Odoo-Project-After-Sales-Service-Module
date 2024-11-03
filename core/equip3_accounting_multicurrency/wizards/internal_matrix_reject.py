# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class AccountingMatrixReject(models.TransientModel):
    _inherit = "internal.matrix.reject"

    def action_reject(self):     
        internal_cash_id = self.env['account.internal.transfer'].browse([self._context.get('active_id')])
        if internal_cash_id.type_curr == "purchase_currency":
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
                action_id = self.env.ref('equip3_accounting_multicurrency.action_int_trans_pur_currency')
                template_id = self.env.ref('equip3_accounting_multicurrency.email_template_purchase_currency_approval_rejected_matrix')
                wa_template_id = self.env.ref('equip3_accounting_multicurrency.wa_template_purchase_currency_rejected')
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
                internal_cash_id._send_wa_message_purchase_currency(wa_template_id, internal_cash_id.request_partner_id.user_ids, url=url, reason=self.reason)
                internal_cash_id.state = 'rejected'
        else:
            return super(AccountingMatrixReject, self).action_reject()
