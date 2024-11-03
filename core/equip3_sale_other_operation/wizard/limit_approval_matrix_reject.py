
from odoo import api , models, fields
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class ApprovalMatrixsaleReject(models.TransientModel):
    _name = 'limit.approval.matrix.sale.reject'
    _Description = "Limit Approval Matrix Sale Reject"

    reason = fields.Text(string="Reason")

    def action_confirm(self):
        sale_order_id = self.env['sale.order'].browse([self._context.get('active_id')])
        user = self.env.user
        is_email_overlimit_approval = self.env['ir.config_parameter'].sudo().get_param('is_email_overlimit_approval', False)
        is_wa_overlimit_approval = self.env['ir.config_parameter'].sudo().get_param('is_wa_overlimit_approval', False)
        approving_matrix_line = sorted(sale_order_id.approved_matrix_limit_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        action_id = self.env.ref('sale.action_quotations_with_onboarding')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=' + str(sale_order_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order'
        rejected_template_id = self.env.ref('equip3_sale_other_operation.email_template_sale_order_overlimit_rejected')
        wa_rejected_template_id = self.env.ref('equip3_sale_other_operation.email_template_sale_order_overlimit_rejected_wa')
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected" % (user.name)
            else:
                name += "• %s: Rejected" % (user.name)
            matrix_line.write({'state_char': name, 'approver_state': 'refuse', 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
            sale_order_id.write({
                'reject_reason' : self.reason,
                'state' : 'over_limit_reject',
            })
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : sale_order_id.user_id.partner_id.email,
                'date': date.today(),
                'url' : url,
            }
            if is_email_overlimit_approval:
                rejected_template_id.sudo().with_context(ctx).send_mail(sale_order_id.id, True)
            if is_wa_overlimit_approval:
                phone_num = str(sale_order_id.user_id.partner_id.mobile) or str(sale_order_id.user_id.partner_id.phone)
                # sale_order_id._send_whatsapp_message_approval(wa_rejected_template_id, sale_order_id.user_id.partner_id, phone_num, url)
                sale_order_id._send_qiscus_whatsapp_approval(wa_rejected_template_id, sale_order_id.user_id.partner_id, phone_num, url)
