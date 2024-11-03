
from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class ApprovalMatrixVendorReject(models.TransientModel):
    _name = 'approval.matrix.vendor.reject'
    _description = "Approval Matrix Vendor Reject"


    reason = fields.Text(string="Reason")

    def action_confirm(self):
        vendor_request_id = self.env['res.partner'].browse([self._context.get('active_id')])
        user = self.env.user
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_vendor_approval_email = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_approval_email')
        is_vendor_approval_whatsapp = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_approval_whatsapp')
        approving_matrix_line = sorted(vendor_request_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        action_id = self.env.ref('equip3_purchase_masterdata.action_vendor_to_approval')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=' + str(vendor_request_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=res.partner'
        rejected_template_id = self.env.ref('equip3_purchase_masterdata.email_template_vendor_approval_rejected')
        wa_rejected_template_id = self.env.ref('equip3_purchase_masterdata.whatsapp_vendor_template_rejected')
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected" % (user.name)
            else:
                name += "• %s: Rejected" % (user.name)
            matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'approver_state': 'refuse', 'feedback': self.reason})
            vendor_request_id.state = 'rejected'
            vendor_request_id.active = False
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : vendor_request_id.request_partner_id.email,
                'date': date.today(),
                'url' : url,
            }
            if is_vendor_approval_email:
                rejected_template_id.sudo().with_context(ctx).send_mail(vendor_request_id.id, True)
            if is_vendor_approval_whatsapp:
                phone_num = str(vendor_request_id.request_partner_id.mobile) or str(vendor_request_id.request_partner_id.phone)
                # vendor_request_id._send_whatsapp_message_approval(wa_rejected_template_id, vendor_request_id.request_partner_id, phone_num, url)
                vendor_request_id._send_qiscus_whatsapp_approval(wa_rejected_template_id,
                                                                  vendor_request_id.request_partner_id, phone_num, url)
