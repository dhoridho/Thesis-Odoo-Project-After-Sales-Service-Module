# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)


class ITICeisaDocumentsBC261(models.Model):
    _name = 'ceisa.documents.bc261'
    _description = 'CEISA Documents TPB BC-261'

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
        default='import'
    )
    sent_state = fields.Boolean('Status', default=False)
    document_type_id = fields.Many2one('ceisa.document.type', string='Jenis Dokumen')
    picking_id = fields.Many2one('stock.picking', string='Picking ID')
    internal_transfer_id = fields.Many2one('internal.transfer', string='Internal Transfer ID')
    user_id = fields.Many2one('res.users', string='User ID', default=lambda self: self.env.user.id)
    company_id = fields.Many2one('res.company', string='Company ID', default=lambda self: self.env.company)
    ceisa_account = fields.Char('CEISA Account')
    no_aju = fields.Char('Nomor Pengajuan')
    aju_date = fields.Date('Tanggal Pengajuan', default=fields.Date.context_today)
    no_register = fields.Char('Nomor Register')
    register_date = fields.Date('Tanggal Register', default=fields.Date.context_today)
    entitas_line_id = fields.One2many('ceisa.entitas.line', 'bc261_document_id', string='Entitas')
    disclaimer = fields.Selection(
        string='Setuju Pengiriman Dokumen?',
        selection=[
            ('1', 'Ya'),
            ('0', 'Tidak'),
        ],
    )
    exim_entitas_id = fields.Many2one('ceisa.entitas.type', string='Jenis Entitas Pengusaha')
    exim_partner_id = fields.Many2one('res.partner')
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
    exim_permit_number = fields.Char('Nomor Izin Pengusaha')
    exim_permit_date = fields.Date('Tanggal Izin Pengusaha', default=fields.Date.context_today)
    exim_status_code = fields.Many2one('ceisa.business.status', string='Kode Status Pengusaha')
    exim_codeapi = fields.Selection(string='Kode Jenis API Pengusaha',
                                    selection=[
                                        ('01', 'Angka Pengenal Importir Umum (APIU)'),
                                        ('02', 'Angka Pengenal Importir Perseroan (APIP)'),
                                        ('04', 'Angka Pengenal Importir Terbatas (APIT)'),
                                    ],
                                    )

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
    owner_status_code = fields.Many2one('ceisa.business.status', string='Kode Status Pemilik')
    owner_name = fields.Char('Nama Pemilik')
    owner_address = fields.Char('Alamat Pemilik')
    owner_country = fields.Many2one('res.country', string='Kode Negara Pemilik')
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
    recipient_status_code = fields.Many2one('ceisa.business.status', string='Kode Status Penerima')
    recipient_name = fields.Char('Nama Penerima')
    recipient_address = fields.Char('Alamat Penerima')
    recipient_country = fields.Many2one('res.country', string='Kode Negara Penerima')

    origin_beacukai_office = fields.Many2one('ceisa.beacukai.office', string='Kantor Pabean Pemuatan')
    origin_pabean_export_office = fields.Many2one('ceisa.pabean.office', string='Kantor Pabean Muat Ekspor')
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
    document_line_id = fields.One2many('ceisa.documents.line', 'bc261_document_id', string='Lampiran Dokumen BC-2.6.1')
    transportation_line_id = fields.One2many('ceisa.transportation.line', 'bc261_document_id', string='Sarana Angkut')
    ###tempat penimbunan dan pemeriksaan
    exim_date_estimation = fields.Date('Tanggal Perkiraan Ekspor', default=fields.Date.context_today)
    storehouse_location = fields.Many2one('ceisa.storehouse.location', string='Tempat Penimbunan')
    # origin_port_office = fields.Many2one('ceisa.pabean.office', string='Pelabuhan Muat Asal')
    origin_port_office = fields.Many2one('ceisa.beacukai.office', string='Pelabuhan Muat Asal')
    origin_port_export = fields.Many2one('ceisa.pabean.office', string='Pelabuhan Muat Ekspor')
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
    bank_payment_id = fields.Many2one('res.bank', string='Bank Devisa')
    #barang dari stock.picking
    product_line_id = fields.One2many('ceisa.products.line', 'bc261_document_id', string='Rincian Barang O2M')
    product_line_ids = fields.Many2many('ceisa.products.line', 'bc261_document_id', string='Rincian Barang')
    ###pungutan
    tax_type = fields.Many2one('ceisa.tax.type', string='Jenis Pungutan')
    rates_type = fields.Selection(
        string='Jenis Tarif',
        selection=[
            ('1', 'Advalorum'),
            ('2', 'Spesifik'),
        ],
    )
    tax_line_id = fields.One2many('ceisa.tax.line', 'bc261_document_id', string='Pungutan')
    tax_value = fields.Char('Nilai Pungutan')
    payment_tax = fields.Float('Dibayar')
    government_tax = fields.Float('Ditanggung Pemerintah')
    pending_tax = fields.Float('Ditunda')
    untax_value = fields.Float('Tidak Dipungut')
    free_tax = fields.Float('Dibebaskan')
    paid_tax = fields.Float('Sudah Dilunasi')
    ###Package and Container
    package_line_id = fields.One2many('ceisa.package.line', 'bc261_document_id', string='Kemasan')
    container_line_id = fields.One2many('ceisa.container.line', 'bc261_document_id', string='Peti Kemas')
    ###Jaminan
    guarantee_line_id = fields.One2many('ceisa.guarantee.line', 'bc261_document_id', string='Jaminan')
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
    facility_kite = fields.Char('Fasilitas KITE')
    zoning_kite = fields.Many2one('ceisa.beacukai.office', string='Zoning KITE')
    pic_name = fields.Char('Nama PIC')
    pic_address = fields.Char('Alamat Siap Diperiksa')
    pic_phone = fields.Char('Telepon PIC')
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
    transport_type_id = fields.Selection(
        string='Cara Pengangkutan',
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
    procedure_type_id = fields.Many2one('ceisa.procedure.type', string='Jenis PIB')
    close_pu = fields.Selection(
        string='Tutup PU',
        selection=[
            ('11', 'BC 1.1'),
            ('12', 'BC 1.2'),
            ('14', 'BC 1.4'),
        ],
    )
    transit_port = fields.Many2one('ceisa.pabean.office', string='Pelabuhan Transit')
    import_type = fields.Selection(
        string='Jenis Impor',
        selection=[
            ('1', 'Untuk Dipakai'),
            ('2', 'Sementara'),
            ('5', 'Pelayanan Segera'),
            ('9', 'Dipakai Sementara'),
        ],
    )
    submission_price = fields.Float('Harga Penyerahan', default=0.01)
    incoterm_value = fields.Float('Nilai Incoterm', default=0.01)
    maklon_value = fields.Float('Nilai Maklon', default=0.01)
    valuntary_value = fields.Float('Nilai Valuntary', default=0.01)
    valuntary_flag = fields.Selection(
        string='Valuntary Declaration',
        selection=[
            ('Y', 'Ya'),
            ('T', 'Tidak'),
        ],
    )
    downpayment = fields.Integer('Jumlah Tanda Pengaman', default=0)
    additional_cost = fields.Float('Biaya Tambahan', default=0.01)
    deduction_cost = fields.Float('Biaya Pengurang', default=0.01)
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
            doc_type = self.env['ceisa.document.type'].search([('code', '=', '261')], limit=1)
            vals['document_type_id'] = doc_type.id
        result = super(ITICeisaDocumentsBC261, self).create(vals)
        return result

    def write(self, vals):
        if not 'document_type_id' in vals:
            doc_type = self.env['ceisa.document.type'].search([('code', '=', '261')], limit=1)
            vals['document_type_id'] = doc_type.id
        result = super(ITICeisaDocumentsBC261, self).write(vals)
        return result

    @api.onchange('internal_transfer_id')
    def _onchange_transfer_request(self):
        if self.product_line_ids:
            raise ValidationError('You have selected transfer request before, please remove list of products before you change it.')
        product_line = []
        user_partner = self.env['res.partner'].browse(self.env.user.partner_id.id)
        transfer_obj = self.env['internal.transfer'].browse(self.internal_transfer_id.id)
        for trans in transfer_obj:
            if trans.product_line_ids:
                for prod in trans.product_line_ids:
                    prod_template = prod.product_id.product_tmpl_id
                    qty = prod.qty
                    product_line.append((0, 0, {
                        'product_id': prod.product_id.id,
                        'product_qty': prod.qty,
                        'origin_country': trans.company_id.country_id.id,
                        'origin_city': trans.company_id.city_id.id,
                        'fob_price': prod_template.list_price * qty,
                        'fob_uom_price': prod_template.list_price * qty
                    }))

            self.name_statement = user_partner.name
            self.job_statement = user_partner.function
            self.place_statement = user_partner.city
            self.date_statement = fields.Date.today()
            self.valuta_id = trans.company_id.currency_id.id
            self.internal_transfer_id = trans.id
            self.product_line_ids = product_line

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
