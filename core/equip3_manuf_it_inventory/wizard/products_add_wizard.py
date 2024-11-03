from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessDenied, UserError
import logging

_logger = logging.getLogger(__name__)


class ProductAddWizard(models.TransientModel):
    _name = 'ceisa.products.wizard'
    _description = 'Ceisa Product Wizard'


    name = fields.Char('Name')
    code = fields.Char('Kode')
    product_id = fields.Many2one('product.product')
    product_qty = fields.Float('Jumlah Satuan')
    product_hs = fields.Char(string='HS')
    product_uom = fields.Many2one('ceisa.product.unit', string='Kode Satuan')
    product_price = fields.Float('Harga Satuan')
    export_price = fields.Float('Harga Ekspor')
    estimation_price = fields.Float('Harga Patokan')
    package_qty = fields.Float('Kemasan')
    package_type = fields.Many2one('ceisa.package.type', string='Jenis Kemasan')
    fob_price = fields.Float('Harga FOB')
    volume = fields.Float('Volume')
    netto_weight = fields.Float('Berat Bersih (Kg)')
    fob_uom_price = fields.Float('Harga Satuan FOB')
    merk = fields.Char('Merek')
    product_type = fields.Char('Tipe Barang')
    product_size = fields.Char('Ukuran')
    origin_country = fields.Many2one('res.country', string='Negara Asal Barang')
    origin_city = fields.Many2one('res.country.city', string='Daerah Asal Barang')
    document_line_id = fields.One2many('ceisa.documents.line', compute='_compute_document_line', string='Lampiran Dokumen')
    export_document_line_id = fields.One2many('ceisa.documents.line', 'export_document_id',
                                       string='Lampiran Daftar Dokumen Ekspor')
    import_document_line_id = fields.One2many('ceisa.documents.line', 'import_document_id',
                                              string='Lampiran Daftar Dokumen Impor')
    export_document_id = fields.Many2one('ceisa.export.documents')
    import_document_id = fields.Many2one('ceisa.import.documents')
    bc23_document_line_id = fields.One2many('ceisa.documents.line', 'bc23_document_id',
                                              string='Lampiran Daftar Dokumen BC-2.3')
    bc23_document_id = fields.Many2one('ceisa.documents.bc23')
    bc25_document_line_id = fields.One2many('ceisa.documents.line', 'bc25_document_id',
                                              string='Lampiran Daftar Dokumen BC-2.5')
    bc25_document_id = fields.Many2one('ceisa.documents.bc25')
    bc27_document_line_id = fields.One2many('ceisa.documents.line', 'bc27_document_id',
                                              string='Lampiran Daftar Dokumen BC-2.7')
    bc27_document_id = fields.Many2one('ceisa.documents.bc27')
    bc261_document_line_id = fields.One2many('ceisa.documents.line', 'bc261_document_id',
                                              string='Lampiran Daftar Dokumen BC-2.6.1')
    bc261_document_id = fields.Many2one('ceisa.documents.bc261')
    bc262_document_line_id = fields.One2many('ceisa.documents.line', 'bc262_document_id',
                                              string='Lampiran Daftar Dokumen BC-2.6.2')
    bc262_document_id = fields.Many2one('ceisa.documents.bc262')
    bc40_document_line_id = fields.One2many('ceisa.documents.line', 'bc40_document_id',
                                              string='Lampiran Daftar Dokumen BC-4.0')
    bc40_document_id = fields.Many2one('ceisa.documents.bc40')
    bc41_document_line_id = fields.One2many('ceisa.documents.line', 'bc41_document_id',
                                              string='Lampiran Daftar Dokumen BC-4.1')
    bc41_document_id = fields.Many2one('ceisa.documents.bc41')

    def _compute_document_line(self):
        models_id = self._context.get('active_id', False)
        if self.env.context['active_model'] == 'ceisa.export.documents':
            doc_line = self.env['ceisa.documents.line'].search([('export_document_id', '=', models_id)])
            self.document_line_id = doc_line or False
        elif self.env.context['active_model'] == 'ceisa.documents.bc23':
            doc_line = self.env['ceisa.documents.line'].search([('bc23_document_id', '=', models_id)])
            self.document_line_id = doc_line or False
        elif self.env.context['active_model'] == 'ceisa.documents.bc25':
            doc_line = self.env['ceisa.documents.line'].search([('bc25_document_id', '=', models_id)])
            self.document_line_id = doc_line or False
        elif self.env.context['active_model'] == 'ceisa.documents.bc261':
            doc_line = self.env['ceisa.documents.line'].search([('bc261_document_id', '=', models_id)])
            self.document_line_id = doc_line or False
        elif self.env.context['active_model'] == 'ceisa.documents.bc262':
            doc_line = self.env['ceisa.documents.line'].search([('bc262_document_id', '=', models_id)])
            self.document_line_id = doc_line or False
        elif self.env.context['active_model'] == 'ceisa.documents.bc27':
            doc_line = self.env['ceisa.documents.line'].search([('bc27_document_id', '=', models_id)])
            self.document_line_id = doc_line or False
        elif self.env.context['active_model'] == 'ceisa.documents.bc40':
            doc_line = self.env['ceisa.documents.line'].search([('bc40_document_id', '=', models_id)])
            self.document_line_id = doc_line or False
        elif self.env.context['active_model'] == 'ceisa.documents.bc41':
            doc_line = self.env['ceisa.documents.line'].search([('bc41_document_id', '=', models_id)])
            self.document_line_id = doc_line or False
        else:
            doc_line = self.env['ceisa.documents.line'].search([('import_document_id', '=', models_id)])
            self.document_line_id = doc_line or False


    @api.model
    def create(self, vals):
        result = super(ProductAddWizard, self).create(vals)
        return result

    def write(self, vals):
        result = super(ProductAddWizard, self).write(vals)
        return result

    def submit_products_wizard(self):
        models_id = self._context.get('active_id', False)
        product_line = {}
        product_line_ids = []
        if not models_id:
            raise UserError(
                _("Programming error: wizard action executed without active_''ids in context."))
        if self.env.context['active_model'] == 'ceisa.export.documents':
            self.export_document_id = models_id
            ceisa_documents = self.env['ceisa.export.documents'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc23':
            self.bc23_document_id = models_id
            ceisa_documents = self.env['ceisa.documents.bc23'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc25':
            self.bc25_document_id = models_id
            ceisa_documents = self.env['ceisa.documents.bc25'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc261':
            self.bc261_document_id = models_id
            ceisa_documents = self.env['ceisa.documents.bc261'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc262':
            self.bc262_document_id = models_id
            ceisa_documents = self.env['ceisa.documents.bc262'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc27':
            self.bc27_document_id = models_id
            ceisa_documents = self.env['ceisa.documents.bc27'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc40':
            self.bc40_document_id = models_id
            ceisa_documents = self.env['ceisa.documents.bc40'].browse(models_id)
        elif self.env.context['active_model'] == 'ceisa.documents.bc41':
            self.bc41_document_id = models_id
            ceisa_documents = self.env['ceisa.documents.bc41'].browse(models_id)
        else:
            self.import_document_id = models_id
            ceisa_documents = self.env['ceisa.import.documents'].browse(models_id)

        company = self.env['res.company'].browse(self.env.user.company_id.id)
        for rec in self:
            product_line = {
                'name': rec.name,
                'code': rec.code,
                'product_hs': rec.product_hs,
                'product_uom': rec.product_uom,
                'product_price': rec.product_price,
                'export_price': rec.export_price,
                'product_id': rec.product_id.id,
                'product_qty': rec.product_qty,
                'origin_country': company.country_id.id,
                'origin_city': company.city_id.id,
                'fob_price': rec.fob_price,
                'fob_uom_price': rec.fob_uom_price,
                'estimation_price': rec.estimation_price,
                'package_qty': rec.package_qty,
                'package_type': rec.package_type,
                'product_type': rec.product_type,
                'volume': rec.volume,
                'netto_weight': rec.netto_weight,
                'merk': rec.merk,
                'product_size': rec.product_size,
            }
            if self.env.context['active_model'] == 'ceisa.export.documents':
                product_line.update({'export_document_line_id': rec.export_document_line_id})
            elif self.env.context['active_model'] == 'ceisa.documents.bc23':
                product_line.update({'bc23_document_line_id': rec.bc23_document_line_id})
            elif self.env.context['active_model'] == 'ceisa.documents.bc25':
                product_line.update({'bc25_document_line_id': rec.bc25_document_line_id})
            elif self.env.context['active_model'] == 'ceisa.documents.bc261':
                product_line.update({'bc261_document_line_id': rec.bc261_document_line_id})
            elif self.env.context['active_model'] == 'ceisa.documents.bc262':
                product_line.update({'bc262_document_line_id': rec.bc262_document_line_id})
            elif self.env.context['active_model'] == 'ceisa.documents.bc27':
                product_line.update({'bc27_document_line_id': rec.bc27_document_line_id})
            elif self.env.context['active_model'] == 'ceisa.documents.bc40':
                product_line.update({'bc40_document_line_id': rec.bc40_document_line_id})
            elif self.env.context['active_model'] == 'ceisa.documents.bc41':
                product_line.update({'bc41_document_line_id': rec.bc41_document_line_id})
            elif self.env.context['active_model'] == 'ceisa.import.documents':
                product_line.update({'import_document_line_id': rec.import_document_line_id})

            product_line_ids.append((0, 0, product_line))
        ceisa_documents.product_line_ids = product_line_ids