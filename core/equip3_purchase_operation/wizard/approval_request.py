
from odoo import _, api, fields, models
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class ApprovalRequestReject(models.TransientModel):
    _name = "approval.request.reject"
    _description = 'Approval Request Reject'

    reason = fields.Text(string="Reason", required=True)

    def action_reject(self):
        purchase_request_id = self.env['purchase.request'].browse(self._context.get('active_ids'))
        user = self.env.user
        is_email_notification_req = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.is_email_notification_req')
        is_whatsapp_notification_req = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.is_whatsapp_notification_req')
        approving_matrix_line = sorted(purchase_request_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        action_id = self.env.ref('purchase_request.purchase_request_form_action')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=' + str(purchase_request_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=purchase.request'
        rejected_template_id = self.env.ref('equip3_purchase_operation.email_template_purchase_req_approval_rejected')
        wa_rejected_template_id = self.env.ref('equip3_purchase_operation.email_template_purchase_req_approval_rejected_wa')
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected" % (user.name)
            else:
                name += "• %s: Rejected" % (user.name)
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'approver_state': 'refuse'})
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : purchase_request_id.request_partner_id.email,
                'date': date.today(),
                'url' : url,
            }
            if is_email_notification_req:
                rejected_template_id.sudo().with_context(ctx).send_mail(purchase_request_id.id, True)
            if is_whatsapp_notification_req:
                phone_num = str(purchase_request_id.request_partner_id.mobile) or str(purchase_request_id.request_partner_id.phone)
                # purchase_request_id._send_whatsapp_message_approval(wa_rejected_template_id, purchase_request_id.request_partner_id, phone_num, url)
                purchase_request_id._send_qiscus_whatsapp_approval(wa_rejected_template_id,
                                                                    purchase_request_id.request_partner_id, phone_num,
                                                                    url)
        purchase_request_id.write({'state' : 'rejected'})
