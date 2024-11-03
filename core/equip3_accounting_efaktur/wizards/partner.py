import base64
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

FK_HEAD_LIST = ['LT', 'NPWP', 'NAMA', 'JALAN', 'BLOK', 'NOMOR', 'RT', 'RW', 'KECAMATAN', 'KELURAHAN', 'KABUPATEN', 'PROPINSI', 'KODE_POS', 'NOMOR_TELEPON']

def _csv_row(data, delimiter=',', quote='"'):
    return quote + (quote + delimiter + quote).join([str(x).replace(quote, '\\' + quote) for x in data]) + quote + '\n'

class ResPartner(models.TransientModel):
    _name = "export.partner.csv"
    _description = "Export Partner"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _mail_post_access = 'read'

    name = fields.Char()
    product_id_attachment_id = fields.Many2one('ir.attachment', readonly=True, copy=False)
    product_id_csv_created = fields.Boolean('CSV Created', compute='_compute_csv_created', copy=False)

    @api.depends('product_id_attachment_id')
    def _compute_csv_created(self):
        for record in self:
            record.product_id_csv_created = bool(record.product_id_attachment_id)

    def download_csv(self):
        action = {
            'type': 'ir.actions.act_url',
            'url': "web/content/?model=ir.attachment&id=" + str(
                self.product_id_attachment_id.id) + "&filename_field=name&field=datas&download=true&name=" + self.product_id_attachment_id.name,
            'target': 'self',
        }
        return action

    def download_efaktur(self):
        """Collect the data and execute function _generate_efaktur."""
        self._generate_efaktur(',')
        return self.download_csv()

    def _generate_efaktur(self, delimiter):
        output_head = self._generate_efaktur_invoice(delimiter)
        my_utf8 = output_head.encode("utf-8")
        out = base64.b64encode(my_utf8)

        attachment = self.env['ir.attachment'].create({
            'datas': out,
            'name': 'partner.csv',
            'type': 'binary',
        })

        for record in self:
            record.message_post(attachment_ids=[attachment.id])
        self.product_id_attachment_id = attachment.id
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _generate_efaktur_invoice(self, delimiter):
        """Generate E-Faktur for customer invoice."""
        # Invoice of Customer
        output_head = '%s' % (
            _csv_row(FK_HEAD_LIST, delimiter)
        )

        partners = self.env['res.partner'].search([('name', 'like', '%')],
            order='name asc')

        for partner in partners:
            val = {}
            # print(move)

            val['LT'] = 'LT' if partner.country_id.name == 'Indonesia' else ''
            val['NPWP'] = partner.vat if partner.vat != False else ''
            val['NAMA'] = partner.name if partner.name != False else ''
            val['JALAN'] = partner.street if partner.street != False else ''
            val['BLOK'] = partner.blok if partner.blok != False else ''
            val['NOMOR'] = partner.street_number if partner.street_number != False else ''
            val['RT'] = partner.rukun_tetangga if partner.rukun_tetangga != False else ''
            val['RW'] = partner.rukun_warga if partner.rukun_warga != False else ''
            val['KECAMATAN'] = partner.kecamatan if partner.kecamatan != False else ''
            val['KELURAHAN'] = partner.kelurahan if partner.kelurahan != False else ''
            val['KABUPATEN'] = partner.city if partner.city != False else ''
            val['PROPINSI'] = partner.state_id.name if partner.state_id.name != False else ''
            val['KODE_POS'] = partner.zip if partner.zip != False else ''
            val['NOMOR_TELEPON'] = partner.phone if partner.phone != False else ''

            fk_values_list = [val[f] for f in FK_HEAD_LIST[0:]]

            output_head += _csv_row(fk_values_list, delimiter)
        return output_head