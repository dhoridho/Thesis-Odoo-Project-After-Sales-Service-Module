
from odoo import models, fields, api, tools, _
from datetime import datetime,timedelta,date
from odoo.exceptions import ValidationError, Warning
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, float_compare, float_round
import requests
import logging
_logger = logging.getLogger(__name__)

headers = {'content-type': 'application/json'}

class ApprovalMatrixsaleReject(models.TransientModel):
    _name = 'bo.approval.matrix.sale.reject'
    _description = "BO Approval Matrix Sale Reject"

    reason = fields.Text(string="Reason")

    def action_confirm_bo(self):
        bo_sale_order_id = self.env['saleblanket.saleblanket'].browse([self._context.get('active_id')])
        bo_sale_order_id.write(dict(state='rejected'))
        user = self.env.user
        approving_matrix_line = sorted(bo_sale_order_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.state_char or ''
            if name != '':
                name += "\n • %s: Rejected" % (user.name)
            else:
                name += "• %s: Rejected" % (user.name)
            matrix_line.write({'state_char': name, 'approver_state': 'refuse', 'time_stamp': datetime.now(), 'feedback': self.reason, 'last_approved': self.env.user})
            bo_sale_order_id.state = 'rejected'

            get_bo_approval = self.env['ir.config_parameter'].get_param(
                'equip3_sale_other_operation_cont.bo_approval_email_notify')
            get_bo_approval_wa = self.env['ir.config_parameter'].get_param(
                'equip3_sale_other_operation_cont.bo_approval_wa_notify')
            if get_bo_approval or get_bo_approval_wa:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(bo_sale_order_id.id) + '&view_type=form&model=saleblanket.saleblanket'

                ctx = {
                    'requester_name': bo_sale_order_id.user_id.partner_id.name,
                    'email_to': bo_sale_order_id.user_id.partner_id.email,
                    'date': date.today(),
                    'url': url
                }
                if get_bo_approval:
                    template_id = self.env.ref(
                    'equip3_sale_other_operation_cont.email_template_bo_approval_has_been_rejected').id
                    template = self.env['mail.template'].browse(template_id)
                    template.with_context(ctx).send_mail(bo_sale_order_id.id, True)


                if get_bo_approval_wa:
                    last_approver = ''
                    subject = 'Reminder for Blanket Order Approval has been Rejected'
                    wa_template_id = self.env.ref('equip3_sale_other_operation_cont.email_template_bo_approval_has_been_rejected_wa')

                    phone_num = str(bo_sale_order_id.user_id.partner_id.mobile) or str(bo_sale_order_id.user_id.partner_id.phone)
                    # bo_sale_order_id._send_whatsapp_message_approval(wa_template_id, bo_sale_order_id.user_id.partner_id, last_approver, subject, phone_num, url,
                    #                                        submitter=bo_sale_order_id.partner_id.name)
                    bo_sale_order_id._send_qiscus_whatsapp_approval(wa_template_id, bo_sale_order_id.user_id.partner_id, last_approver, subject, phone_num, url,
                                                           submitter=bo_sale_order_id.partner_id.name)

    def _send_whatsapp_message_approval(self, template_id, approver, last_approver, subject, phone, url, submitter=False):
        record = self.env['saleblanket.saleblanket'].browse([self._context.get('active_id')])
        string_test = str(tools.html2plaintext(template_id.body_html))
        if "${date}" in string_test:
            string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
        if "${subject}" in string_test:
            string_test = string_test.replace("${subject}", subject)
        if "${requester_name}" in string_test:
            string_test = string_test.replace("${requester_name}", record.user_id.partner_id.name)
        if "${approver_name}" in string_test:
            string_test = string_test.replace("${approver_name}", approver.name)
        if "${name}" in string_test:
            string_test = string_test.replace("${name}", record.name)
        if "${partner_name}" in string_test:
            string_test = string_test.replace("${partner_name}", record.user_id.partner_id.name)
        if "${last_approved}" in string_test:
            if last_approver:
                string_test = string_test.replace("${last_approved}", last_approver)
            else:
                string_test = string_test.replace("${last_approved}",  f"\n")
        if "${submitter_name}" in string_test:
            string_test = string_test.replace("${submitter_name}", submitter)
        if "${br}" in string_test:
            string_test = string_test.replace("${br}", f"\n")
        if "${url}" in string_test:
            string_test = string_test.replace("${url}", url)
        phone_num = phone
        if "+" in phone_num:
            phone_num = phone_num.replace("+", "")
        param = {'body': string_test, 'phone': phone_num, 'previewBase64': '', 'title': ''}
        domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
        token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
        try:
            request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
        except ConnectionError:
            raise ValidationError("Not connect to API Chat Server. Limit reached or not active")
                # connector_id.ca_request('post', 'sendMessage', param)

    def _send_qiscus_whatsapp_approval(self, template_id, approver, last_approver, subject, phone, url, submitter=False):
        self.ensure_one()
        for record in self:
            broadcast_template_id = self.env['qiscus.wa.template.content'].search([
                ('language', '=', 'en'),
                ('template_id.name', '=', 'hm_sale_notification_1')
            ], limit=1)
            if not broadcast_template_id:
                raise ValidationError(_("Cannot find Whatsapp template with name = 'hm_sale_notification_1'!"))
            domain = self.env['ir.config_parameter'].get_param('qiscus.api.url')
            token = self.env['ir.config_parameter'].get_param('qiscus.api.secret_key')
            app_id = self.env['ir.config_parameter'].get_param('qiscus.api.appid')
            channel_id = self.env['ir.config_parameter'].get_param('qiscus.api.channel_id')

            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${subject}" in string_test:
                string_test = string_test.replace("${subject}", subject)
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.user_id.partner_id.name)
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.user_id.partner_id.name)
            if "${last_approved}" in string_test:
                if last_approver:
                    string_test = string_test.replace("${last_approved}", last_approver)
                else:
                    string_test = string_test.replace("${last_approved}", "")
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", submitter)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            # message = re.sub(r'\n+', ', ', string_test)
            messages = string_test.split(f'\n')
            message_obj = []
            for pesan in messages:
                message_obj.append({
                    'type': 'text',
                    'text': pesan
                })
            phone_num = phone
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "").replace(" ", "").replace("-", "")
            headers = {
                'content-type': 'application/json',
                'Qiscus-App-Id': app_id,
                'Qiscus-Secret-Key': token
            }
            url = f'{domain}{app_id}/{channel_id}/messages'
            params = {
                "to": phone_num,
                "type": "template",
                "template": {
                    "namespace": broadcast_template_id.template_id.namespace,
                    "name": broadcast_template_id.template_id.name,
                    "language": {
                        "policy": "deterministic",
                        "code": 'en'
                    },
                    "components": [{
                        "type": "body",
                        "parameters": message_obj
                    }]
                }
            }
            try:
                request_server = requests.post(url, json=params, headers=headers, verify=True)
                _logger.info("\nNotification Whatsapp --> Request for Approval:\n-->Header: %s \n-->Parameter: %s \n-->Result: %s" % (headers, params, request_server.json()))
                # if request_server.status_code != 200:
                #     data = request_server.json()
                #     raise ValidationError(f"""{data["error"]["error_data"]["details"]}""")
            except ConnectionError:
                raise ValidationError("Not connect to API Chat Server. Limit reached or not active!")
