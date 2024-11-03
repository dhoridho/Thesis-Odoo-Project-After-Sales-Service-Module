
from odoo import _, api, fields, models
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class AssetsApprovalReject(models.TransientModel):
    _name = "assets.approval.reject"

    reason = fields.Text(string="Reason")

    def action_reject(self):
        account_asset_asset_id = self.env['account.asset.asset'].browse(self._context.get('active_ids'))
        user = self.env.user
        approving_matrix_line = sorted(account_asset_asset_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected" % (user.name)
            else:
                name += "• %s: Rejected" % (user.name)
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason})
            action_id = self.env.ref('om_account_asset.action_account_asset_asset_form')
            template_id = self.env.ref('equip3_accounting_asset.email_template_asset_rejected_matrix')
            wa_template_id = self.env.ref('equip3_accounting_asset.email_template_rjct_asset_wa')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(account_asset_asset_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.asset.asset'
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : account_asset_asset_id.request_partner_id.email,
                'rejected_name' : self.env.user.name,
                'feedback' : self.reason,
                'url' : url,
                'create_date': account_asset_asset_id.create_date.date(),
                'date': account_asset_asset_id.create_date.date(),
            }
            template_id.with_context(ctx).send_mail(account_asset_asset_id.id, True)
            account_asset_asset_id._send_whatsapp_message(wa_template_id, account_asset_asset_id.request_partner_id.user_ids, url=url, reason=self.reason)
            account_asset_asset_id.write({'state' : 'reject'})
