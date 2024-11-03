import base64
import os
from odoo import api, fields, models, _


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.model
    def default_get(self, fields):
        folder_path = os.path.dirname(os.path.abspath(__file__))
        file = False
        with open('%s/PEPPOL LOA Form.docx' % folder_path, 'rb+') as reader:
            file = base64.encodestring(reader.read())
            reader.close()
        res = super(MailComposer, self).default_get(fields)
        if 'image_download' in fields:
            res['image_download'] = file
        if 'name_download' in fields:
            res['name_download'] = "Peppol LOA Form.docx"
        return res

    name_loa_form = fields.Char(string='Name')
    image_loa_form = fields.Binary(string='PEPPOL LOA Form')
    name_acra_file = fields.Char(string='File')
    image_acra_file = fields.Binary(string='ACRA Biz File')
    name_download = fields.Char(string='Form')
    image_download = fields.Binary('PEPPOL LOA Download')

    # @api.multi
    def download_document(self):
        return {
            'name': 'PEPPOL LOA FORM',
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=mail.compose.message&field=image_download&id=%s&filename=Peppol_LOA_Form.docx&filename_field=name_download&download=true' % (self.id),
            'target': 'new',
            'target_type': 'public',
            'res_id': self.id,
        }

    # @api.multi
    def peppol_onboarding_sent_email(self):
        attachment = self.env['ir.attachment'].create(
            {'name': 'PEPPOL LOA Form.docx',
             'datas_fname': 'PEPPOL LOA Form.docx',
             'datas': str(self.name_loa_form).encode('base64')}
        )

        attachment2 = self.env['ir.attachment'].create(
            {'name': 'ACRA Biz File.pdf',
             'datas_fname': 'ACRA Biz File.pdf',
             'datas': str(self.name_acra_file).encode('base64')}
        )

        template_id = self.env.ref('hm_peppol.peppol_email_template').id
        template = self.env['mail.template'].browse(template_id)

        # Add Attachment
        template.attachment_ids = [(6, 0, [attachment.id, attachment2.id])]

        if template.attachment_ids:
            template.send_mail(self.env.user.company_id.id, force_send=True)
