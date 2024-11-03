# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from collections import OrderedDict
import io
import logging
import base64
import xlsxwriter
_logger = logging.getLogger(__name__)


class ITICeisaExportDocuments(models.Model):
    _name = 'ceisa.export.documents'
    _description = 'CEISA Export Documents'

    name = fields.Char('Name')
    type = fields.Selection(
        string='Document Type',
        selection=[
            ('export', 'Export Document'),
            ('import', 'Import Document'),
            ('bc23', 'Document TPB - BC2.3'),
            ('bc25', 'Document TPB - BC2.5'),
            ('bc261', 'Document TPB - BC2.6.1'),
            ('bc262', 'Document TPB - BC2.6.2'),
            ('bc27', 'Document TPB - BC2.7'),
            ('bc40', 'Document TPB - BC4.0'),
            ('bc41', 'Document TPB - BC4.1'),
        ],
        default='export'
    )
    sent_state = fields.Boolean('Status', default=False)
    document_type_id = fields.Many2one('ceisa.document.type', string='Jenis Dokumen')
    picking_id = fields.Many2one('stock.picking', string='Picking ID')
    user_id = fields.Many2one('res.users', string='User ID', default=lambda self: self.env.user.id)
    company_id = fields.Many2one('res.company', string='Company ID', default=lambda self: self.env.company)
    ceisa_account = fields.Char('CEISA Account')
    no_aju = fields.Char('Nomor Pengajuan')
    aju_date = fields.Date('Tanggal Pengajuan', default=fields.Date.context_today)
    no_register = fields.Char('Nomor Register')
    register_date = fields.Date('Tanggal Register', default=fields.Date.context_today)
    entitas_line_id = fields.One2many('ceisa.entitas.line', 'export_document_id', string='Entitas')
    disclaimer = fields.Selection(
        string='Setuju Pengiriman Dokumen?',
        selection=[
            ('1', 'Ya'),
            ('0', 'Tidak'),
        ],
    )
    exim_entitas_id = fields.Many2one('ceisa.entitas.type', string='Jenis Entitas Pengusaha')
    exim_partner_id = fields.Many2one('res.partner', string='Nama Partner Pengusaha')
    exim_identity_type = fields.Selection(
        string='Jenis Identitas Pengusaha',
        selection=[
            ('5', 'NPWP 15 Digit'),
            ('0', 'NPWP 12 Digit'),
            ('1', 'NPWP 10 Digit'),
            ('2', 'Paspor'),
            ('3', 'KTP'),
            ('4', 'Lainnya'),
        ],
    )
    exim_identity_number = fields.Char('Nomor Identitas Pengusaha')
    exim_name = fields.Char('Nama Pengusaha')
    exim_address = fields.Char('Alamat Pengusaha')
    exim_country = fields.Many2one('res.country', string='Kode Negara Pengusaha')
    exim_nib_entitas = fields.Char('NIB Entitas Pengusaha')
    exim_status_code = fields.Many2one('ceisa.business.status', string='Kode Status Pengusaha')
    ###Owner Entitas
    owner_partner_id = fields.Many2one('res.partner', string='Nama Partner Pemilik')
    owner_identity_type = fields.Selection(
        string='Jenis Identitas Pemilik',
        selection=[
            ('5', 'NPWP 15 Digit'),
            ('0', 'NPWP 12 Digit'),
            ('1', 'NPWP 10 Digit'),
            ('2', 'Paspor'),
            ('3', 'KTP'),
            ('4', 'Lainnya'),
        ],
    )
    owner_identity_number = fields.Char('Nomor Identitas Pemilik')
    owner_name = fields.Char('Nama Pemilik')
    owner_address = fields.Char('Alamat Pemilik')
    owner_country = fields.Many2one('res.country', string='Kode Negara Pemilik')
    #### Penbeli Entitas
    buyer_partner_id = fields.Many2one('res.partner', string='Nama Partner')
    buyer_identity_type = fields.Selection(
        string='Jenis Identitas Pembeli',
        selection=[
            ('5', 'NPWP 15 Digit'),
            ('0', 'NPWP 12 Digit'),
            ('1', 'NPWP 10 Digit'),
            ('2', 'Paspor'),
            ('3', 'KTP'),
            ('4', 'Lainnya'),
        ],
    )
    buyer_identity_number = fields.Char('Nomor Identitas Pembeli')
    buyer_name = fields.Char('Nama Pembeli')
    buyer_address = fields.Char('Alamat Pembeli')
    buyer_country = fields.Many2one('res.country', string='Kode Negara Pembeli')
    #### Penerima Entitas
    recipient_partner_id = fields.Many2one('res.partner', string='Nama Partner Penerima')
    recipient_identity_type = fields.Selection(
        string='Jenis Identitas Penerima',
        selection=[
            ('5', 'NPWP 15 Digit'),
            ('0', 'NPWP 12 Digit'),
            ('1', 'NPWP 10 Digit'),
            ('2', 'Paspor'),
            ('3', 'KTP'),
            ('4', 'Lainnya'),
        ],
    )
    recipient_identity_number = fields.Char('Nomor Identitas Penerima')
    recipient_name = fields.Char('Nama Penerima')
    recipient_address = fields.Char('Alamat Penerima')
    recipient_country = fields.Many2one('res.country', string='Kode Negara Penerima')
    origin_beacukai_office = fields.Many2one('ceisa.beacukai.office', string='Kantor Pabean Pemuatan')
    origin_pabean_export_office = fields.Many2one('ceisa.pabean.office', string='Kantor Pabean Muat Ekspor')
    export_type = fields.Selection(
        string='Jenis Ekspor',
        selection=[
            ('1', 'Biasa'),
            ('2', 'Berkala'),
            ('3', 'Fasilitas'),
            ('4', 'Re-Impor'),
            ('5', 'Re-Ekspor'),
            ('6', 'Ex Impor Sementara'),
        ],
    )
    export_category = fields.Many2one('ceisa.export.category', string='Kategori Ekspor')
    procedure_type_id = fields.Many2one('ceisa.procedure.type', string='Jenis PIB')
    trade_way_id = fields.Many2one('ceisa.trade.way', string='Cara Perdagangan')
    payment_term = fields.Many2one('ceisa.payment.term', string='Cara Pembayaran')
    payment_code = fields.Char('Kode Pembayaran')
    payment_location = fields.Selection(
        string='Lokasi Pembayaran',
        selection=[
            ('1', 'Bank'),
            ('2', 'Kantor Pos'),
            ('3', 'Kantor Pabean'),
            ('4', 'NTPN'),
        ],
    )
    origin_location_id = fields.Many2one('res.country.city', string='Daerah Asal Barang')
    flag_curah = fields.Char('Flag Curah')
    flag_komoditi = fields.Char('Flag Komoditi')
    curah = fields.Selection(
        string='Curah',
        selection=[
            ('1', 'Curah'),
            ('2', 'Non Curah'),
        ],
    )
    komoditi = fields.Selection(
        string='Komoditi',
        selection=[
            ('1', 'Migas'),
            ('2', 'Non Migas'),
        ],
    )
    document_line_id = fields.One2many('ceisa.documents.line', 'export_document_id', string='Lampiran Dokumen Ekspor')
    transportation_line_id = fields.One2many('ceisa.transportation.line', 'export_document_id', string='Sarana Angkut')
    ###tempat penimbunan dan pemeriksaan
    exim_date_estimation = fields.Date('Tanggal Perkiraan Ekspor', default=fields.Date.context_today)
    storehouse_location = fields.Many2one('ceisa.storehouse.location', string='Tempat Penimbunan')
    origin_port_office = fields.Many2one('ceisa.beacukai.office', string='Pelabuhan Muat Asal')
    origin_port_export = fields.Many2one('ceisa.beacukai.office', string='Pelabuhan Muat Ekspor')
    destination_pabean_office = fields.Many2one('ceisa.beacukai.office', string='Kantor Pabean')
    destination_unloading_port = fields.Many2one('ceisa.pabean.office', string='Pelabuhan Bongkar')
    destination_port_office = fields.Many2one('ceisa.pabean.office', string='Pelabuhan Tujuan')
    destination_country = fields.Many2one('res.country', string='Negara Tujuan Ekspor')
    inspection_location = fields.Many2one('ceisa.locations', string='Lokasi Pemeriksaan')
    inspection_date = fields.Date('Tanggal Periksa', default=fields.Date.context_today)
    inspection_office = fields.Many2one('ceisa.beacukai.office', string='Kantor Pemeriksaan')
    ###transaksi
    valuta_id = fields.Many2one('res.currency', string='Valuta')
    ndpbm = fields.Float('NDPBM', default=1.00)
    cara_penyerahan = fields.Many2one('ceisa.incoterm', string="Cara Penyerahan")
    nilai_export = fields.Float('Nilai Export', default=0.01)
    freight = fields.Float('Freight', default=0.01)
    insurance_type = fields.Selection(
        string='Asuransi',
        selection=[
            ('LN', 'Luar Negeri'),
            ('DN', 'Dalam Negeri'),
        ],
    )
    insurance_value = fields.Float('Nilai Asuransi', default=0.01)
    weight_bruto_kgm = fields.Float('Berat Kotor (KGM)', default=0.01)
    weight_bruto_kg = fields.Float('Berat Kotor (Kg)', default=0.01)
    weight_netto_kg = fields.Float('Berat Bersih (Kg)', default=0.01)
    maklon_value = fields.Float('Nilai Maklon', default=0.01)
    bea_out_value = fields.Float('Nilai Bea Keluar', default=0.01)
    pph_bea_keluar = fields.Float('Nilai PPh', default=0.01)
    sawit_tax_value = fields.Float('Nilai Pungutan Sawit', default=0.01)
    bank_payment_id = fields.Many2one('res.bank', string='Bank Devisa')
    #barang dari stock.picking
    product_line_id = fields.One2many('ceisa.products.line', 'export_document_id', string='Rincian Barang')
    product_line_ids = fields.Many2many('ceisa.products.line', 'export_document_id', string='Rincian Daftar Barang')
    ###pungutan
    tax_type = fields.Many2one('ceisa.tax.type', string='Jenis Pungutan')
    rates_type = fields.Selection(
        string='Jenis Tarif',
        selection=[
            ('1', 'Advalorum'),
            ('2', 'Spesifik'),
        ],
    )
    tax_line_id = fields.One2many('ceisa.tax.line', 'export_document_id', string='Daftar Pungutan')
    tax_value = fields.Char('Nilai Pungutan')
    payment_tax = fields.Float('Dibayar')
    government_tax = fields.Float('Ditanggung Pemerintah')
    pending_tax = fields.Float('Ditunda')
    untax_value = fields.Float('Tidak Dipungut')
    free_tax = fields.Float('Dibebaskan')
    paid_tax = fields.Float('Sudah Dilunasi')
    ###Package and Container
    package_line_id = fields.One2many('ceisa.package.line', 'export_document_id', string='Kemasan')
    container_line_id = fields.One2many('ceisa.container.line', 'export_document_id', string='Peti Kemas')

    ###pernyataan
    place_statement = fields.Char('Tempat')
    date_statement = fields.Date('Tanggal Pernyataan', default=fields.Date.context_today)
    name_statement = fields.Char('Nama')
    job_statement = fields.Char('Jabatan')
    ###PKB
    product_type = fields.Selection(
        string='Jenis Barang',
        selection=[
            ('1', 'Barang Ekspor Gabungan'),
            ('2', 'Bahan/Barang Asal Impor Fasilitas'),
        ],
    )
    warehouse_type = fields.Selection(
        string='Jenis Gudang',
        selection=[
            ('1', 'Gudang Veem'),
            ('2', 'Gudang Pabrik'),
            ('3', 'Gudang Konsolidasi'),
            ('4', 'Lainnya'),
        ],
    )
    facility_kite = fields.Char('Fasilitas KITE')
    zoning_kite = fields.Many2one('ceisa.beacukai.office', string='Zoning KITE')
    pic_name = fields.Char('Nama PIC')
    pic_address = fields.Char('Alamat Siap Diperiksa')
    pic_phone = fields.Char('Telepon PIC')
    container_20 = fields.Integer('Jumlah Kontainer 20 Feet')
    container_40 = fields.Integer('Jumlah Kontainer 40 Feet')
    pic_location = fields.Char('Lokasi Siap Periksa')
    container_way = fields.Many2one('ceisa.container.type', string='Cara Stuffing')
    partof_type = fields.Selection(
        string='Jenis Part of',
        selection=[
            ('1', 'Gabungan Kemudahan Ekspor'),
            ('2', 'Gabungan ke/non ke'),
        ]
    )
    pkb_date = fields.Datetime('Tanggal Pemeriksaan Kesiapan Barang', default=fields.Date.context_today)
    investigate_date = fields.Datetime('Waktu Barang Siap Periksa', default=fields.Date.context_today)
    komoditi_cukai = fields.Selection(
        string='Komoditi Cukai',
        selection=[
            ('1', 'Hasil Tembakau'),
            ('2', 'MMEA'),
            ('3', 'EA'),
            ('4', 'Test'),
        ],
    )
    no_bc11 = fields.Char('Nomor BC 1.1')
    bc11_date = fields.Date('Tanggal BC 1.1', default=fields.Date.context_today)
    bc11_office = fields.Char('Pos/Sub Pos')
    bc11_pos = fields.Char('Nomor Pos')
    bc11_subpos = fields.Char('Nomor SubPos')
    cif_value = fields.Float('Nilai Pabean', default=0.01)
    trade_transaction_type = fields.Many2one('ceisa.trade.transaction.type', string='Jenis Transaksi')
    ### OTHERS
    volume = fields.Float('Volume', default=0.01)
    ppn_tax = fields.Float('Pajak PPn', default=0.01)
    ppnbm_tax = fields.Float('Pajak PPnBM', default=0.01)
    tarif_ppn_tax = fields.Float('Tarif Pajak PPn', default=0.01)
    tarif_ppnbm_tax = fields.Float('Tarif Pajak PPnBM', default=0.01)
    destination_unloading_office = fields.Many2one('ceisa.beacukai.office', string='Kantor Tujuan Bongkar')
    tpb_type_id = fields.Many2one('ceisa.tpb.type', string='Jenis TPB')
    destination_tpb_type_id = fields.Many2one('ceisa.tpb.type', string='Tujuan TPB')
    nik = fields.Char('NIK')

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            entitas_line = []
            if 'aju_date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['aju_date']))
            vals['name'] = self.env['ir.sequence'].next_by_code('ceisa.documents', sequence_date=seq_date) or _('New')
        if not 'document_type_id' in vals:
            doc_type = self.env['ceisa.document.type'].search([('code', '=', '30')], limit=1)
            vals['document_type_id'] = doc_type.id
        result = super(ITICeisaExportDocuments, self).create(vals)
        return result

    def write(self, vals):
        if not 'document_type_id' in vals:
            doc_type = self.env['ceisa.document.type'].search([('code', '=', '30')], limit=1)
            vals['document_type_id'] = doc_type.id
        result = super(ITICeisaExportDocuments, self).write(vals)
        return result

    @api.onchange('picking_id')
    def _onchange_delivery_orders(self):
        ceisa_value = []
        product_line = []
        user_partner = self.env['res.partner'].browse(self.env.user.partner_id.id)
        picking_obj = self.env['stock.picking'].browse(self.picking_id.id)
        for pick in picking_obj:
            if pick.move_ids_without_package:
                for prod in pick.move_ids_without_package:
                    prod_template = prod.product_id.product_tmpl_id
                    qty = prod.product_uom_qty
                    product_line.append((0, 0, {
                        'product_id': prod.product_id.id,
                        'product_qty': prod.product_uom_qty,
                        'origin_country': self.company_id.country_id.id,
                        'origin_city': self.company_id.city_id.id,
                        'fob_price': prod_template.list_price * qty,
                        'fob_uom_price': prod_template.list_price * qty
                    }))

            self.name_statement = user_partner.name
            self.job_statement = user_partner.function
            self.place_statement = user_partner.city
            self.date_statement = fields.Date.today()
            self.valuta_id = pick.company_id.currency_id.id
            self.picking_id = pick.id
            self.product_line_ids = product_line
            self.owner_partner_id = pick.company_id.id
            self.owner_identity_number = pick.company_id.vat
            self.owner_address = pick.company_id.city_id.name
            self.owner_country = pick.company_id.country_id.id
            self.buyer_partner_id = pick.partner_id.id
            self.buyer_address = pick.partner_id.city  ###pick.partner_id.city_id.name
            self.buyer_country = pick.partner_id.country_id.id
            self.recipient_partner_id = pick.partner_id.id
            self.recipient_address = pick.partner_id.city  ###pick.partner_id.city_id.name
            self.recipient_country = pick.partner_id.country_id.id


    def action_add_new_product(self):
        return {
            'name': 'Add New Products Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'ceisa.products.wizard',
            'view_id': False,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }



class CeisaProductsLine(models.Model):
    _name = 'ceisa.products.line'
    _description = 'CEISA Products Line'

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
    document_line_id = fields.One2many('ceisa.documents.line', compute='_compute_document_line', string='Lampiran Daftar Dokumen')
    export_document_line_id = fields.One2many('ceisa.documents.line', 'export_document_id',
                                       string='Lampiran Dokumen Ekspor')
    import_document_line_id = fields.One2many('ceisa.documents.line', 'import_document_id',
                                              string='Lampiran Dokumen Impor')
    export_document_id = fields.Many2one('ceisa.export.documents')
    import_document_id = fields.Many2one('ceisa.import.documents')
    bc23_document_line_id = fields.One2many('ceisa.documents.line', 'bc23_document_id',
                                              string='Lampiran Dokumen BC-2.3')
    bc23_document_id = fields.Many2one('ceisa.documents.bc23')
    bc25_document_line_id = fields.One2many('ceisa.documents.line', 'bc25_document_id',
                                              string='Lampiran Dokumen BC-2.5')
    bc25_document_id = fields.Many2one('ceisa.documents.bc25')
    bc27_document_line_id = fields.One2many('ceisa.documents.line', 'bc27_document_id',
                                              string='Lampiran Dokumen BC-2.7')
    bc27_document_id = fields.Many2one('ceisa.documents.bc27')
    bc261_document_line_id = fields.One2many('ceisa.documents.line', 'bc261_document_id',
                                              string='Lampiran Dokumen BC-2.6.1')
    bc261_document_id = fields.Many2one('ceisa.documents.bc261')
    bc262_document_line_id = fields.One2many('ceisa.documents.line', 'bc262_document_id',
                                              string='Lampiran Dokumen BC-2.6.2')
    bc262_document_id = fields.Many2one('ceisa.documents.bc262')
    bc40_document_line_id = fields.One2many('ceisa.documents.line', 'bc40_document_id',
                                              string='Lampiran Dokumen BC-4.0')
    bc40_document_id = fields.Many2one('ceisa.documents.bc40')
    bc41_document_line_id = fields.One2many('ceisa.documents.line', 'bc41_document_id',
                                              string='Lampiran Dokumen BC-4.1')
    bc41_document_id = fields.Many2one('ceisa.documents.bc41')

    def _compute_document_line(self):
        for lin in self:
            lin.export_document_id = None



class ITICeisaDocumentsLine(models.Model):
    _name = 'ceisa.documents.line'
    _description = 'CEISA Documents Line'

    type = fields.Many2one('ceisa.document.type', string='Jenis')
    number = fields.Char('Nomor')
    doc_date = fields.Date('Tanggal', default=fields.Date.context_today)
    facility = fields.Char('Fasilitas')
    izin = fields.Char('Izin')
    office = fields.Char('Kantor')
    file = fields.Char('File')
    export_document_id = fields.Many2one('ceisa.export.documents')
    import_document_id = fields.Many2one('ceisa.import.documents')
    bc23_document_id = fields.Many2one('ceisa.documents.bc23')
    bc25_document_id = fields.Many2one('ceisa.documents.bc25')
    bc27_document_id = fields.Many2one('ceisa.documents.bc27')
    bc261_document_id = fields.Many2one('ceisa.documents.bc261')
    bc262_document_id = fields.Many2one('ceisa.documents.bc262')
    bc40_document_id = fields.Many2one('ceisa.documents.bc40')
    bc41_document_id = fields.Many2one('ceisa.documents.bc41')


class CeisaTransportationLine(models.Model):
    _name = 'ceisa.transportation.line'
    _description = 'CEISA Transportation Line'

    name = fields.Char('Nama')
    number = fields.Char('Nomor')
    transport_type = fields.Selection(
        string='Jenis Transportasi',
        selection=[
            ('1', 'Laut'),
            ('2', 'Kereta Api'),
            ('3', 'Darat'),
            ('4', 'Udara'),
            ('5', 'Pos'),
            ('6', 'Multimoda'),
            ('7', 'Instalasi/Pipa'),
            ('8', 'Perairan'),
            ('9', 'Lainnya'),
        ],
    )
    country_id = fields.Many2one('res.country')
    export_document_id = fields.Many2one('ceisa.export.documents')
    import_document_id = fields.Many2one('ceisa.import.documents')
    bc23_document_id = fields.Many2one('ceisa.documents.bc23')
    bc25_document_id = fields.Many2one('ceisa.documents.bc25')
    bc27_document_id = fields.Many2one('ceisa.documents.bc27')
    bc261_document_id = fields.Many2one('ceisa.documents.bc261')
    bc262_document_id = fields.Many2one('ceisa.documents.bc262')
    bc40_document_id = fields.Many2one('ceisa.documents.bc40')
    bc41_document_id = fields.Many2one('ceisa.documents.bc41')


class CeisaPackageLine(models.Model):
    _name = 'ceisa.package.line'
    _description = 'CEISA Package Line'

    name = fields.Char('Name')
    value = fields.Integer('Jumlah')
    package_id = fields.Many2one('ceisa.package.type', string='Jenis')
    merek = fields.Char('Merek')
    export_document_id = fields.Many2one('ceisa.export.documents')
    import_document_id = fields.Many2one('ceisa.import.documents')
    bc23_document_id = fields.Many2one('ceisa.documents.bc23')
    bc25_document_id = fields.Many2one('ceisa.documents.bc25')
    bc27_document_id = fields.Many2one('ceisa.documents.bc27')
    bc261_document_id = fields.Many2one('ceisa.documents.bc261')
    bc262_document_id = fields.Many2one('ceisa.documents.bc262')
    bc40_document_id = fields.Many2one('ceisa.documents.bc40')
    bc41_document_id = fields.Many2one('ceisa.documents.bc41')


class CeisaPackageLine(models.Model):
    _name = 'ceisa.container.line'
    _description = 'CEISA Container Line'

    name = fields.Char('Name')
    number = fields.Char('Nomor')
    size = fields.Many2one('ceisa.container', string='Ukuran')
    category = fields.Selection(
        string='Jenis',
        selection=[
            ('4', 'Empty'),
            ('7', 'LCL'),
            ('8', 'FCL'),
        ],
    )
    type = fields.Many2one('ceisa.container.type', string='Tipe')
    export_document_id = fields.Many2one('ceisa.export.documents')
    import_document_id = fields.Many2one('ceisa.import.documents')
    bc23_document_id = fields.Many2one('ceisa.documents.bc23')
    bc25_document_id = fields.Many2one('ceisa.documents.bc25')
    bc27_document_id = fields.Many2one('ceisa.documents.bc27')
    bc261_document_id = fields.Many2one('ceisa.documents.bc261')
    bc262_document_id = fields.Many2one('ceisa.documents.bc262')
    bc40_document_id = fields.Many2one('ceisa.documents.bc40')
    bc41_document_id = fields.Many2one('ceisa.documents.bc41')


class CeisaEntitasLine(models.Model):
    _name = 'ceisa.entitas.line'
    _description = 'CEISA Entitas Line'

    name = fields.Char('Nama')
    code = fields.Many2one('ceisa.entitas.type', string='Jenis Entitas')
    identity_type = fields.Selection(
        string='Jenis Identitas',
        selection=[
            ('5', 'NPWP 15 Digit'),
            ('0', 'NPWP 12 Digit'),
            ('1', 'NPWP 10 Digit'),
            ('2', 'Paspor'),
            ('3', 'KTP'),
            ('4', 'Lainnya'),
        ],
    )
    nib_number = fields.Char('NIB Number')
    number = fields.Char('Nomor Identitas')
    country_id = fields.Many2one('res.country', string='Negara')
    address = fields.Char('Alamat')
    export_document_id = fields.Many2one('ceisa.export.documents')
    import_document_id = fields.Many2one('ceisa.import.documents')
    exim_codeapi = fields.Selection(string='Kode Jenis API',
                                    selection=[
                                        ('01', 'Angka Pengenal Importir Umum (APIU)'),
                                        ('02', 'Angka Pengenal Importir Perseroan (APIP)'),
                                        ('04', 'Angka Pengenal Importir Terbatas (APIT)'),
                                    ],
                                    )
    bc23_document_id = fields.Many2one('ceisa.documents.bc23')
    bc25_document_id = fields.Many2one('ceisa.documents.bc25')
    bc27_document_id = fields.Many2one('ceisa.documents.bc27')
    bc261_document_id = fields.Many2one('ceisa.documents.bc261')
    bc262_document_id = fields.Many2one('ceisa.documents.bc262')
    bc40_document_id = fields.Many2one('ceisa.documents.bc40')
    bc41_document_id = fields.Many2one('ceisa.documents.bc41')


class CeisaTaxLine(models.Model):
    _name = 'ceisa.tax.line'
    _description = 'CEISA Tax Line'

    name = fields.Char('Name')
    tax_value = fields.Char('Nilai Pungutan')
    payment_tax = fields.Float('Dibayar')
    government_tax = fields.Float('Ditanggung Pemerintah')
    pending_tax = fields.Float('Ditunda')
    untax_value = fields.Float('Tidak Dipungut')
    free_tax = fields.Float('Dibebaskan')
    paid_tax = fields.Float('Sudah Dilunasi')
    tax_facilities_fee = fields.Many2one('ceisa.facilities.fee', string='Fasilitas Tarif')
    tax_type = fields.Many2one('ceisa.tax.type', string='Jenis Pungutan')
    export_document_id = fields.Many2one('ceisa.export.documents')
    import_document_id = fields.Many2one('ceisa.import.documents')
    bc23_document_id = fields.Many2one('ceisa.documents.bc23')
    bc25_document_id = fields.Many2one('ceisa.documents.bc25')
    bc27_document_id = fields.Many2one('ceisa.documents.bc27')
    bc261_document_id = fields.Many2one('ceisa.documents.bc261')
    bc262_document_id = fields.Many2one('ceisa.documents.bc262')
    bc40_document_id = fields.Many2one('ceisa.documents.bc40')
    bc41_document_id = fields.Many2one('ceisa.documents.bc41')


class CeisaGuaranteeLine(models.Model):
    _name = 'ceisa.guarantee.line'
    _description = 'CEISA Guarantee Line'

    name = fields.Char('Nama Penjamin')
    guarantee_id = fields.Char('ID Jaminan')
    no_bpj = fields.Char('Nomor BPJ')
    date_bpj = fields.Date('Tanggal Izin BPJ', default=fields.Date.context_today)
    guarantee_value = fields.Float('Nilai Jaminan')
    guarantee_type = fields.Char('Kode Jenis Jaminan')
    guarantee_no = fields.Char('Nomor Jaminan')
    guarantee_date = fields.Date('Tanggal Jaminan', default=fields.Date.context_today)
    guarantee_limit_date = fields.Date('Tanggal Jatuh Tempo', default=fields.Date.context_today)
    export_document_id = fields.Many2one('ceisa.export.documents')
    import_document_id = fields.Many2one('ceisa.import.documents')
    bc23_document_id = fields.Many2one('ceisa.documents.bc23')
    bc25_document_id = fields.Many2one('ceisa.documents.bc25')
    bc27_document_id = fields.Many2one('ceisa.documents.bc27')
    bc261_document_id = fields.Many2one('ceisa.documents.bc261')
    bc262_document_id = fields.Many2one('ceisa.documents.bc262')
    bc40_document_id = fields.Many2one('ceisa.documents.bc40')
    bc41_document_id = fields.Many2one('ceisa.documents.bc41')


class CeisaProductTaxLine(models.Model):
    _name = 'ceisa.product.tax.line'
    _description = 'CEISA Product Tax Line'

    export_document_id = fields.Many2one('ceisa.export.documents')
    import_document_id = fields.Many2one('ceisa.import.documents')
    bc23_document_id = fields.Many2one('ceisa.documents.bc23')
    bc25_document_id = fields.Many2one('ceisa.documents.bc25')
    bc27_document_id = fields.Many2one('ceisa.documents.bc27')
    bc261_document_id = fields.Many2one('ceisa.documents.bc261')
    bc262_document_id = fields.Many2one('ceisa.documents.bc262')
    bc40_document_id = fields.Many2one('ceisa.documents.bc40')
    bc41_document_id = fields.Many2one('ceisa.documents.bc41')




class ITICeisaDocuments(models.Model):
    _name = 'ceisa.documents'
    _description = 'CEISA Documents'

