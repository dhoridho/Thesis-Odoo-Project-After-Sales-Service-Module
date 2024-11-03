
from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class ApprovalMatrixBoReject(models.TransientModel):
    _name = 'bo.request.matrix.reject'
    _description = "Approval Matrix Bo Reject"

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        is_email_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_email_notification_bo')
        is_whatsapp_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_whatsapp_notification_bo')
        # is_email_notification_tender = self.env.company.is_email_notification_bo
        # is_whatsapp_notification_tender = self.env.company.is_whatsapp_notification_bo
        bo_id = self.env['purchase.requisition'].browse([self._context.get('active_id')])
        user = self.env.user
        approving_matrix_line = sorted(bo_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id='+ str(bo_id.id) + '&view_type=form&model=purchase.agreement'
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected" % (user.name)
            else:
                name += "• %s: Rejected" % (user.name)
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'approver_state': 'refuse'})
            bo_id.state = 'rejected'
            template_id = self.env.ref('equip3_purchase_other_operation.email_template_bo_approval_rejected')
            if is_email_notification_tender:
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : bo_id.user_id.partner_id.email,
                    'date': date.today(),
                    'url' : url,
                }
                template_id.sudo().with_context(ctx).send_mail(bo_id.id, True)
            if is_whatsapp_notification_tender:
                req_wa_template_id = self.env.ref('equip3_purchase_other_operation.email_template_bo_approval_rejected_wa')
                phone_num = str(bo_id.user_id.partner_id.mobile) or str(bo_id.user_id.partner_id.phone)
                # bo_id._send_whatsapp_message_approval(req_wa_template_id, bo_id.partner_id, phone_num, url, False)
                bo_id._send_qiscus_whatsapp_approval(req_wa_template_id, bo_id.partner_id, phone_num, url, False)
