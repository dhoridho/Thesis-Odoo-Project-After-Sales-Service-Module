
import base64
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

FK_HEAD_LIST = ['OB', 'KODE_OBJEK', 'NAMA', 'HARGA_SATUAN']

def _csv_row(data, delimiter=',', quote='"'):
    return quote + (quote + delimiter + quote).join([str(x).replace(quote, '\\' + quote) for x in data]) + quote + '\n'

class ProductTemplate(models.Model):
    _name = "export.product.csv"
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
            'url': "web/content/?model=ir.attachment&id=" + str(self.product_id_attachment_id.id) + "&filename_field=name&field=datas&download=true&name=" + self.product_id_attachment_id.name,
            'target': 'self',
        }        
        print(self.env['ir.attachment'].search([('id', '=', self.product_id_attachment_id.id )]))
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
            'name': 'product.csv',
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

        list_product = self.env['product.template'].search([('name', 'like', '%')],
            order='default_code asc')

        for move in list_product:
            eTax = {}
            print(move)

            eTax['KODE_OBJEK'] = move.default_code if move.default_code != False else '' 
            eTax['NAMA'] = move.name
            eTax['HARGA_SATUAN'] = move.list_price

            fk_values_list = ['OB'] + [eTax[f] for f in FK_HEAD_LIST[1:]]

            output_head += _csv_row(fk_values_list, delimiter)
        return output_head


	
