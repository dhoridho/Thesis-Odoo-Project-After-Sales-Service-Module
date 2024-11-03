
from odoo import _, api, fields, models
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class CashAdvanceReject(models.TransientModel):
    _name = "cash.advance.reject"

    reason = fields.Text(string="Reason", required=True)

    def action_reject(self):
        vendor_deposit_id = self.env['vendor.deposit'].browse(self._context.get('active_ids'))
        user = self.env.user
        approving_matrix_line = sorted(vendor_deposit_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected" % (user.name)
            else:
                name += "• %s: Rejected" % (user.name)
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason})
            action_id = self.env.ref('equip3_accounting_cash_advance.action_account_cash_advance')
            template_id = self.env.ref('equip3_accounting_cash_advance_extd.email_template_cash_advance_rejected_matrix')
            wa_template_id = self.env.ref('equip3_accounting_cash_advance_extd.wa_template_accounting_cash_advance_rejected')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(vendor_deposit_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=vendor.deposit'
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : vendor_deposit_id.request_partner_id.email,
                'rejected_name' : self.env.user.name,
                'feedback' : self.reason,
                'url' : url,
                'create_date': vendor_deposit_id.create_date.date(),
                'date': vendor_deposit_id.create_date.date(),
            }
            template_id.with_context(ctx).send_mail(vendor_deposit_id.id, True)
            vendor_deposit_id._send_whatsapp_message_cash_advance(wa_template_id, vendor_deposit_id.request_partner_id.user_ids, url=url, reason=self.reason)
            vendor_deposit_id.write({'state' : 'rejected'})
