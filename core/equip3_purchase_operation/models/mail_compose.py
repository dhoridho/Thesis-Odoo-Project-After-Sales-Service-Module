from odoo import api, fields, models, _
from datetime import datetime, time, timedelta
import base64
import random
import html2text
from PyPDF2 import PdfFileWriter, PdfFileReader
import io

class SsccreatoreportWiz(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.model
    def default_get(self, default_fields):
        res = super(SsccreatoreportWiz, self).default_get(default_fields)
        context = dict(self.env.context) or {}
        if context.get('active_model') == 'purchase.order' and context.get('picking_type_code') != 'incoming':
            purchase_order_id = self.env['purchase.order'].browse(context.get('active_ids'))
            template_id = self.env['ir.model.data'].xmlid_to_res_id('sh_all_in_one_purchase_tools.email_template_edi_purchase_custom', raise_if_not_found=False)
            template_values = self.env['mail.template'].browse(template_id).generate_email(purchase_order_id.ids, ['attachment_ids'])
            attachment_ids = []
            Attachment = self.env['ir.attachment']
            data_attach = {
                'name': purchase_order_id.name,
                'datas': base64.b64encode(self.env.ref('purchase.action_report_purchase_order')._render_qweb_pdf(purchase_order_id.id)[0]),
                'expiry_date': datetime.now(),
                'res_model': 'purchase.order',
                'res_id': purchase_order_id.id,
                'type': 'binary',  # override default_type from context, possibly meant for another model!
            }
            attachment_id = Attachment.create(data_attach)
            attachment_id.generate_access_token()
            attachment_ids.append(attachment_id.id)
            res['attachment_ids'] = [(6, 0, attachment_ids)]
        return res


    def action_send_wp(self):
        text = html2text.html2text(self.body)
        phone = self.partner_ids[0].mobile
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        if self.attachment_ids:
            text += '%0A%0A Other Attachments :'
            random_num = random.randint(111111111, 999999999)
            for attachment in self.attachment_ids:
                attachment.generate_access_token()
                text += '%0A%0A'
                text += base_url+'/web/content/ir.attachment/' + \
                        str(attachment.id)+'/datas?access_token=' + \
                        attachment.access_token
        context = dict(self._context or {})
        active_id = context.get('active_id', False)
        active_model = context.get('active_model', False)

        if text and active_id and active_model:
            message = str(text).replace('*', '').replace('_', '').replace('%0A',
                                                                          '<br/>').replace('%20', ' ').replace('%26', '&')
            if active_model == 'sale.order' and self.env['sale.order'].browse(
                    active_id).company_id.display_in_message:
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': 'sale.order',
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': message or False,
                    'message_type': 'comment',
                })
            if active_model == 'purchase.order' and self.env['purchase.order'].browse(
                    active_id).company_id.purchase_display_in_message:
                if self.attachment_ids:
                    url = '\n'
                    msg = message.split('Report :')[0] + ": "
                    msg += message.split('Report :')[1].split('<br/><br/> Other Attachments :<br/><br/>')[1]
                    msg2 = text.split('Report* :')[0] + ": "
                    msg2 += text.split('Report* :')[1].split('%0A%0A Other Attachments :%0A%0A')[1] + "%0A%0A"
                    random_num = random.randint(111111111, 999999999)
                    for attachment in self.attachment_ids:
                        password_attachment = self.generate_password_pdf(attachment, random_num)
                        final_url = base_url + '/attachment/download/%d'%(password_attachment.id)
                        url += final_url + '\n'
                    msg += '\npassword: %d' %(random_num)
                    msg2 += "%0A%0A" + 'password: %d' %(random_num) + "%0A%0A"
                    text = msg2
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': 'purchase.order',
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': msg or False,
                    'message_type': 'comment',
                })
            if (active_model == 'account.move' and self.env['account.move'].browse(active_id).company_id.invoice_display_in_message) or (active_model == 'account.payment' and self.env['account.payment'].browse(active_id).company_id.invoice_display_in_message):
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': active_model,
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': message or False,
                    'message_type': 'comment',
                })

            if active_model == 'stock.picking' and self.env['stock.picking'].browse(
                    active_id).company_id.inventory_display_in_message:
                self.env['mail.message'].create({
                    'partner_ids': [(6, 0, self.partner_ids.ids)],
                    'model': 'stock.picking',
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': message or False,
                    'message_type': 'comment',
                })

        return {
            'type': 'ir.actions.act_url',
            'url': "https://web.whatsapp.com/send?l=&phone="+phone+"&text=" + text,
            'target': 'new',
        }


    def generate_password_pdf(self, attachment, password):
        output_pdf = PdfFileWriter()
        in_buff = io.BytesIO(base64.b64decode(attachment.datas))
        pdf = PdfFileReader(in_buff)
        output_pdf.appendPagesFromReader(pdf)
        output_pdf.encrypt(str(password), owner_pwd=None, use_128bit=True)
        buff = io.BytesIO()
        output_pdf.write(buff)
        value = buff.getvalue()
        attachment.write({
            'datas': base64.b64encode(value),
        })
        return attachment

    def action_send_mail(self):
        res = super(SsccreatoreportWiz, self).action_send_mail()
        context = dict(self.env.context) or {}
        if context.get('active_model') == "purchase.order":
            purchase_order_id = self.env['purchase.order'].browse(context.get('active_ids'))
            is_purchase_order_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_purchase_order_approval_matrix', False)
            # is_purchase_order_approval_matrix = self.env.company.is_purchase_order_approval_matrix
            if is_purchase_order_approval_matrix and purchase_order_id.approval_matrix_id and purchase_order_id.state != 'purchase':
                purchase_order_id.write({'state' : 'sent'})
        return res
