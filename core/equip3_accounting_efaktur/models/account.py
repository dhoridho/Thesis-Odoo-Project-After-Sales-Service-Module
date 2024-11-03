# -*- coding: utf-8 -*-
import logging
import base64
import io
from odoo import api, fields, models, _
from lxml import etree
import xml.etree.ElementTree as ET
from odoo.exceptions import UserError, ValidationError
import base64, requests, inspect, os, re
import json

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')

FK_HEAD_LIST = ['FK', 'KD_JENIS_TRANSAKSI', 'FG_PENGGANTI', 'NOMOR_FAKTUR', 'MASA_PAJAK', 'TAHUN_PAJAK', 'TANGGAL_FAKTUR', 'NPWP', 'NAMA', 'ALAMAT_LENGKAP', 'JUMLAH_DPP', 
                'JUMLAH_PPN', 'JUMLAH_PPNBM', 'ID_KETERANGAN_TAMBAHAN', 'FG_UANG_MUKA', 'UANG_MUKA_DPP', 'UANG_MUKA_PPN', 'UANG_MUKA_PPNBM', 'REFERENSI', 'KODE_DOKUMEN_PENDUKUNG', '@']

LT_HEAD_LIST = ['LT', 'NPWP', 'NAMA', 'JALAN', 'BLOK', 'NOMOR', 'RT', 'RW', 'KECAMATAN', 'KELURAHAN', 'KABUPATEN', 'PROPINSI', 'KODE_POS', 'NOMOR_TELEPON']

OF_HEAD_LIST = ['OF', 'KODE_OBJEK', 'NAMA', 'HARGA_SATUAN', 'JUMLAH_BARANG', 'HARGA_TOTAL', 'DISKON', 'DPP', 'PPN', 'TARIF_PPNBM', 'PPNBM']


RK_HEAD_LIST = ['RK','NPWP','NAMA','KD_JENIS_TRANSAKSI','FG_PENGGANTI','NOMOR_FAKTUR','TANGGAL_FAKTUR','NOMOR_DOKUMEN_RETUR',
                     'TANGGAL_DOKUMEN_RETUR','MASA_PAJAK_RETUR','TAHUN_PAJAK_RETUR','NILAI_RETUR_DPP','NILAI_RETUR_PPN','NILAI_RETUR_PPNBM']

RM_HEAD_LIST = ['RM','NPWP','NAMA','KD_JENIS_TRANSAKSI','FG_PENGGANTI','NOMOR_FAKTUR','TANGGAL_FAKTUR','NOMOR_DOKUMEN_RETUR',
                     'TANGGAL_DOKUMEN_RETUR','MASA_PAJAK_RETUR','TAHUN_PAJAK_RETUR','NILAI_RETUR_DPP','NILAI_RETUR_PPN','NILAI_RETUR_PPNBM']

def _csv_row(data, delimiter=',', quote='"'):
    return quote + (quote + delimiter + quote).join([str(x).replace(quote, '\\' + quote) for x in data]) + quote + '\n'

class AccountMove(models.Model):
    _inherit = "account.move"

   
    status_code = fields.Selection(selection=[
                  ('0', '0 - Normal'),
                  ('1', '1 - Pengganti')
                  ], string='Kode Status')
    nomor_seri = fields.Many2one('account.efaktur', string="Nomor Seri E-Faktur")
    ebupot_id = fields.Many2one('account.ebupot', string="E-Bupot")
    code = fields.Char(string='Country Code', compute='check_code')
    check = fields.Boolean(string='Check field', compute='check_code')
    check_invisible = fields.Boolean(string='Check invis', compute='check_code')
    total_tax_ppn = fields.Monetary(string="Taxes", readonly=True, store=True, compute='_compute_invoice_taxes_ppn')
    total_inv_ppn = fields.Monetary(string="Subtotal", readonly=True, store=True, compute='_compute_invoice_taxes_ppn')
    subtotal_inv_ppn = fields.Monetary(string="Total", readonly=True, store=True, compute='_compute_invoice_taxes_ppn')
    tax_number_bupot = fields.Char(string='Nomor e-BupotUnifikasi')
    kode_dokumen = fields.Selection(selection=[
                  ('1', '1'),
                  ('2', '2')
                  ], string='Kode Dokumen')
    kode_seri = fields.Char(string='Kode Seri')
    nomor_seri_bupot = fields.Many2one('account.ebupot', string="Nomor Seri Bukti e-BupotUnifikasi")
    check_invisible_ebupot = fields.Boolean(string='Check invis Bupot', compute='check_code')
    ebupot_template = fields.Binary('Template', compute="_get_template")
    l10n_id_replace_invoice_id = fields.Many2one('account.move', string="Replace Invoice")
    l10n_id_kode_transaksi = fields.Selection([
            ('01', '01 Kepada Pihak yang Bukan Pemungut PPN (Customer Biasa)'),
            ('02', '02 Kepada Pemungut Bendaharawan (Dinas Kepemerintahan)'),
            ('03', '03 Kepada Pemungut Selain Bendaharawan (BUMN)'),
            ('04', '04 DPP Nilai Lain (PPN 1%)'),
            ('05', '05 Besaran Tertentu (Pasal 9A ayat (1) UU PPN)'),
            ('06', '06 Penyerahan Lainnya (Turis Asing)'),
            ('07', '07 Penyerahan yang PPN-nya Tidak Dipungut (Kawasan Ekonomi Khusus/ Batam)'),
            ('08', '08 Penyerahan yang PPN-nya Dibebaskan (Impor Barang Tertentu)'),
            ('09', '09 Penyerahan Aktiva ( Pasal 16D UU PPN )'),
        ], string='Kode Transaksi', help='Dua digit pertama nomor pajak',
       )
    is_upload_djp =  fields.Boolean()
    is_upload_djp_cn =  fields.Boolean()
    pajak_express_id = fields.Integer(string="Faktur ID",copy=False)
    approval_url = fields.Char()
    efaktur_url = fields.Char()
    nomor_dokumen_pendukung = fields.Char()
    hide_button_upload = fields.Boolean(compute='_compute_hide_button_upload')
    hide_button_upload_cn = fields.Boolean(compute='_compute_hide_button_upload_cn')
    hide_button_upload_pajak_masukan = fields.Boolean(compute='_compute_hide_button_upload_pajak_masukan')
    hide_button_upload_pajak_masukan_retur = fields.Boolean(compute='_compute_hide_button_upload_pajak_masukan_retur')
    tipe_pembayaran = fields.Selection([('0','0-Normal'),('1','1-Uang Muka'),('2','2-Pelunasan')],default="0")
    keterangan_tambahan = fields.Many2one('account.keterangan.tambahan')
    uang_muka = fields.Float()
    uang_muka_ppn = fields.Float()
    uang_muka_ppnbm = fields.Float()
    signature_country_id = fields.Many2one('res.country', string='Signature Country')
    signature_city_id = fields.Many2one('res.country.city', string='Signature City')
    nomor_seri_domain = fields.Char(string='Nomor Seri Domain', compute='_compute_nomor_seri_domain')
    # nomor_seri_010 = fields.Char(string='Nomor Seri', default='010')
    kode_objek_pajak_id = fields.Many2many('kode.objek.pajak', string='Kode Objek Pajak')
    kode_approval = fields.Char()
    is_upload_pajak_masukkan = fields.Boolean(default=False)
    is_upload_pajak_masukkan_retur = fields.Boolean(default=False)

    # @api.depends('invoice_line_ids', 'invoice_line_ids.tax_ids', 'invoice_line_ids.tax_ids.pph_type')
    # def _compute_kode_objek_pajak_domain(self):
    #     for record in self:
    #         domain = []
    #         pph_pasal = []
    #         # Example logic to build domain based on pph_type
    #         pph_types = record.line_ids.mapped('tax_ids.is_pph')
    #         for pph in pph_types:
    #             pph_pasal.append(pph.pph_type)
    #         domain.append(('pph_pasal', 'in', pph_pasal))
    #         # if pph_types:
    #         #     domain = [('pph_pasal', 'in', pph_types)]
    #         # Convert domain to string as domain on fields can't use lambda directly
    #         record.kode_objek_pajak_domain = str(domain)

    # def _get_kode_objek_pajak_domain(self):
    #     domain = []
    #     for rec in self:
    #         # Example logic to build domain based on attributes of each record
    #         if rec.kode_objek_pajak_domain:
    #             domain.append(('pph_type', 'in', rec.invoice_line_ids.mapped('tax_ids.pph_type')))
    #     return domain

    @api.onchange('invoice_line_ids')
    def _onchange_tax_ids(self):
        for record in self:
            domain = []
            pph_pasal = []
            if record.invoice_line_ids:
                pph_type = record.invoice_line_ids.tax_ids.filtered(lambda x: x.is_pph)
                for pph in pph_type:
                    pph_pasal.append(pph.pph_type)
                domain.append(('pph_pasal', 'in', pph_pasal))
                # if pph_type:
                #     domain.append(('pph_pasal','=',pph_type.pph_type))
                record.kode_objek_pajak_id = False
                return {'domain': {'kode_objek_pajak_id': domain}}

    def action_approve(self):
        res = super(AccountMove, self).action_approve()
        if self.l10n_id_replace_invoice_id:
            self.l10n_id_replace_invoice_id.action_cancel()
        return res
    
    @api.onchange('l10n_id_replace_invoice_id')
    def _onchange_l10n_id_replace_invoice_id(self):
        for record in self:
            if record.l10n_id_replace_invoice_id:
                record.status_code = '1'
                record.l10n_id_kode_transaksi = record.l10n_id_replace_invoice_id.l10n_id_kode_transaksi
                record.nomor_seri = record.l10n_id_replace_invoice_id.nomor_seri.id
                record.tipe_pembayaran = record.l10n_id_replace_invoice_id.tipe_pembayaran
                record.l10n_id_tax_number = record.l10n_id_replace_invoice_id.l10n_id_tax_number

    @api.depends('l10n_id_kode_transaksi','l10n_id_replace_invoice_id')
    def _compute_cek_status(self):
        for record in self:
            if record.l10n_id_replace_invoice_id:
                record.status_code = '1'
            else:
                record.status_code = '0'

    @api.onchange('signature_country_id')
    def _onchange_signature_country_id(self):
        for record in self:
            if record.signature_country_id:
                state_obj = self.env['res.country.state'].search([('country_id','=',record.signature_country_id.id)])
                state_ids = []
                for state in state_obj:
                    state_ids.append(state.id)
                if record.signature_city_id:
                    if record.signature_city_id.state_id.id not in state_ids:
                        record.signature_city_id = False
                return {'domain': {'signature_city_id': [('state_id','in',state_ids)]}}
            else:
                return {'domain': {'signature_city_id': [('id','in',[])]}}
    
    @api.onchange('signature_city_id')
    def _onchange_signature_city_id(self):
        for record in self:
            if record.signature_city_id:
                record.signature_country_id = record.signature_city_id.state_id.country_id.id
                if record.signature_country_id:
                    state_obj = self.env['res.country.state'].search([('country_id','=',record.signature_country_id.id)])
                    state_ids = []
                    for state in state_obj:
                        state_ids.append(state.id)
                    return {'domain': {'signature_city_id': [('state_id','in',state_ids)]}}
            
    @api.constrains('uang_muka','uang_muka_ppn','uang_muka_ppnbm')
    def _constrain_uang_muka(self):
        for record in self:
            if record.tipe_pembayaran in ['1','2']:
                if record.uang_muka <= 0 or record.uang_muka_ppn <= 0 or record.uang_muka_ppnbm <= 0 :
                    raise ValidationError("Uang Muka, Uang Muka PPN, Uang Muka PPNBM harus lebih dari 0")
                
    def open_pk(self):
        for record in self:
            pajak_express_transaction_url = self.pajak_express_transaction_url()
            login  = self.login()
            if login.status_code == 200:
                response = login.json()
                token = response['data']['token']
                x_token = record.company_id.pjap_x_token
                if not x_token:
                    raise ValidationError(_('You need to generate x-token first in Company.'))
                header_x = {"Authorization": f"Bearer {token}",
                            "x-token":x_token
                            }
                pajak_keluaran_cetak = requests.get(pajak_express_transaction_url + f"/efaktur/pk/cetak?id={record.pajak_express_id}",headers=header_x)
                pajak_pk_response =  pajak_keluaran_cetak.json()
                record.efaktur_url = pajak_pk_response['data']
            return {
                    'name'     : 'wa website',
                    'res_model': 'ir.actions.act_url',
                    'type'     : 'ir.actions.act_url',
                    'target'   : '_blank',
                    'url'      : f"{record.efaktur_url}"
                }
            
    def open_pk_retur(self):
        for record in self:
            pajak_express_transaction_url = self.pajak_express_transaction_url()
            login  = self.login()
            if login.status_code == 200:
                response = login.json()
                token = response['data']['token']
                x_token = record.company_id.pjap_x_token
                if not x_token:
                    raise ValidationError(_('You need to generate x-token first in Company.'))
                header_x = {"Authorization": f"Bearer {token}",
                            "x-token":x_token
                            }
                pajak_keluaran_cetak = requests.get(pajak_express_transaction_url + f"/efaktur/pk/cetak?id={record.pajak_express_id}",headers=header_x)
                pajak_pk_response =  pajak_keluaran_cetak.json()
                record.efaktur_url = pajak_pk_response['data']
            return {
                    'name'     : 'wa website',
                    'res_model': 'ir.actions.act_url',
                    'type'     : 'ir.actions.act_url',
                    'target'   : '_blank',
                    'url'      : f"{record.efaktur_url}"
                }
        
    
    def open_approval(self):
        for record in self:
            return {
                'name'     : 'wa website',
                'res_model': 'ir.actions.act_url',
                'type'     : 'ir.actions.act_url',
                'target'   : '_blank',
                'url'      : f"{record.approval_url}"
            }

    
    
    @api.depends('period_id')
    def _compute_hide_button_upload(self):
        for record in self:
            if  self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration'):
                if record.state == 'posted' and not record.is_upload_djp:
                    record.hide_button_upload = False
                else:
                    record.hide_button_upload = True
            else:
                record.hide_button_upload = True
                
    @api.depends('period_id')
    def _compute_hide_button_upload_cn(self):
        for record in self:
            if  self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration'):
                if record.state == 'posted' and not record.is_upload_djp_cn:
                    record.hide_button_upload_cn = False
                else:
                    record.hide_button_upload_cn = True
            else:
                record.hide_button_upload_cn = True
                
    @api.depends('period_id')
    def _compute_hide_button_upload_pajak_masukan(self):
        for record in self:
            if  self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration'):
                if record.state == 'posted' and not record.is_upload_pajak_masukkan:
                    record.hide_button_upload_pajak_masukan = False
                else:
                    record.hide_button_upload_pajak_masukan = True
            else:
                record.hide_button_upload_pajak_masukan = True
                
    @api.depends('period_id')
    def _compute_hide_button_upload_pajak_masukan_retur(self):
        for record in self:
            if  self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration'):
                if record.state == 'posted' and not record.is_upload_pajak_masukkan_retur:
                    record.hide_button_upload_pajak_masukan_retur = False
                else:
                    record.hide_button_upload_pajak_masukan_retur = True
            else:
                record.hide_button_upload_pajak_masukan_retur = True


    
    def generate_api_secret(self,url,npwp,token):
        header = {"Authorization": f"Bearer {token}",
                   "npwp":npwp
                   }
        api_secret = requests.get(url + '/api/client-store',headers=header)
        secret_response =  api_secret.json()
        header_x = {"Authorization": f"Bearer {token}",
                    "X-Tenant":"foo",
                    "api-key":secret_response['data']['api_key'],
                    "api-secret":secret_response['data']['api_secret']
                   }
        x_token = requests.post(url+"/api/client-token",headers=header_x)
        x_token_response = x_token.json()
        return x_token_response['data']['token']
    
    def pajak_express_url(self):
        pajak_express_url = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_url')
        return pajak_express_url
    
    def pajak_express_transaction_url(self):
        pajak_express_transaction_url = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_transaction_url')
        return pajak_express_transaction_url
        
   
    def login(self):
       pajak_express_url = self.pajak_express_url()
       pajak_express_username = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_username')
       pajak_express_password = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_password')
       payload = {'email':pajak_express_username,'password':pajak_express_password}
       login = requests.post(pajak_express_url + '/api/login',data=payload)
       return login
   
   
    def button_upload_pajak_masukkan_retur(self):
        self.ensure_one()
        pajak_express_transaction_url = self.pajak_express_transaction_url()
        login  = self.login()
        if login.status_code == 200:
            response = login.json()
            token = response['data']['token']
            x_token = self.company_id.pjap_x_token
            if not self.l10n_id_tax_number:
                raise ValidationError(_('Faktur Pajak is Empty!'))
            if not x_token:
                raise ValidationError(_('You need to generate x-token first in Company.'))
            header_x = {"Authorization": f"Bearer {token}",
                        "x-token":x_token
                        }
            obj_faktur = [{
                "diskon":(data.unit_price_fnct *  (data.discount_amount/100)) if data.discount_method == "per" and data.discount_method else data.discount_amount,
                "dpp":(data.unit_price_fnct - (data.unit_price_fnct *  (data.discount_amount/100))) if data.discount_method == "per" and data.discount_method  else data.unit_price_fnct -  data.discount_amount,
                "hargaSatuan":data.price_unit,
                "hargaTotal":data.unit_price_fnct,
                "jumlahBarang":data.quantity,
                "keterangan":data.name,
                "localId":1,
                "kodeObjek":"",
                "nama":data.product_id.name,
                "ppn":data.price_tax,
                "ppnbm":0,
                "tarifPpnbm":0
                }for data in self.invoice_line_ids
                          ]
            npwpPenjual = str(self.partner_id.vat).replace('.','')
            npwpPenjual = str(npwpPenjual).replace('-','')
            payload = {
                        "nomorDokumenRetur":self.name,
                        "masaPajakRetur": self.invoice_date.strftime('%m').lstrip('0'),
                        "nilaiReturDpp": sum([data['dpp'] for data in obj_faktur]),
                        "nilaiReturPpn": self.amount_tax,
                        "nilaiReturPpnbm": self.uang_muka_ppnbm,
                        "fakturPm":{"nomorFaktur": f"{self.l10n_id_tax_number[3:16]}"},
                        "tahunPajakRetur": self.invoice_date.strftime('%Y'),
                        "tanggalRetur": self.invoice_date.strftime('%Y%m%d'),
                        "tarifPpn": 11
                    }
            pajak_masukkan_retur = requests.post(pajak_express_transaction_url + "/efaktur/pm/retur/upload",headers=header_x,json=payload)
            pajak_masukkan_response_retur =  pajak_masukkan_retur.json()
            try:
                if pajak_masukkan_response_retur['data']['kodeApproval']:
                    self.is_upload_pajak_masukkan_retur = True
                    self.kode_approval = pajak_masukkan_response_retur['data']['kodeApproval']

                    
            except TypeError:
                raise ValidationError(f"{pajak_masukkan_response_retur['message']}\n"
                                      f"request: {payload}"
                                      )
    def button_upload_pajak_masukkan(self):
        self.ensure_one()
        pajak_express_transaction_url = self.pajak_express_transaction_url()
        login  = self.login()
        if login.status_code == 200:
            response = login.json()
            token = response['data']['token']
            x_token = self.company_id.pjap_x_token
            if not self.l10n_id_tax_number:
                raise ValidationError(_('Faktur Pajak is Empty!'))
            if not x_token:
                raise ValidationError(_('You need to generate x-token first in Company.'))
            header_x = {"Authorization": f"Bearer {token}",
                        "x-token":x_token
                        }
            obj_faktur = [{
                "diskon":(data.unit_price_fnct *  (data.discount_amount/100)) if data.discount_method == "per" and data.discount_method else data.discount_amount,
                "dpp":(data.unit_price_fnct - (data.unit_price_fnct *  (data.discount_amount/100))) if data.discount_method == "per" and data.discount_method  else data.unit_price_fnct -  data.discount_amount,
                "hargaSatuan":data.price_unit,
                "hargaTotal":data.unit_price_fnct,
                "jumlahBarang":data.quantity,
                "keterangan":data.name,
                "localId":1,
                "kodeObjek":"",
                "nama":data.product_id.name,
                "ppn":data.price_tax,
                "ppnbm":0,
                "tarifPpnbm":0
                }for data in self.invoice_line_ids
                          ]
            npwpPenjual = str(self.partner_id.vat).replace('.','')
            npwpPenjual = str(npwpPenjual).replace('-','')
            payload = {
                        "fgPengganti": f"{self.l10n_id_tax_number[2]}",
                        "isCreditable": "0",
                        "kdJenisTransaksi": f"{self.l10n_id_tax_number[:2]}",
                        "masaPajak": self.invoice_date.strftime('%m').lstrip('0'),
                        "nilaiDpp": sum([data['dpp'] for data in obj_faktur]),
                        "nilaiPpn": self.amount_tax,
                        "nilaiPpnbm": self.uang_muka_ppnbm,
                        "nomorFaktur": f"{self.l10n_id_tax_number[3:16]}",
                        "npwpPenjual": npwpPenjual,
                        "tahunPajak": self.invoice_date.strftime('%Y'),
                        "tanggalFaktur": self.invoice_date.strftime('%Y%m%d'),
                        "tarifPpn": 11
                    }
            pajak_masukkan = requests.post(pajak_express_transaction_url + "/efaktur/pm/upload",headers=header_x,json=payload)
            pajak_masukkan_response =  pajak_masukkan.json()
            try:
                if pajak_masukkan_response['data']['kodeApproval']:
                    self.is_upload_pajak_masukkan = True
                    self.kode_approval = pajak_masukkan_response['data']['kodeApproval']

                    
            except TypeError:
                raise ValidationError(f"{pajak_masukkan_response['message']}\n"
                                      f"request: {payload}"
                                      )
        
        
        
    def button_upload_djp_cn(self):
        self.ensure_one()
        pajak_express_transaction_url = self.pajak_express_transaction_url()
        login  = self.login()
        if login.status_code == 200:
            response = login.json()
            token = response['data']['token']
            x_token = self.company_id.pjap_x_token
            if not x_token:
                raise ValidationError(_('You need to generate x-token first in Company.'))
            header_x = {"Authorization": f"Bearer {token}",
                        "x-token":x_token
                        }
            obj_faktur = [{
                                "diskon":(data.unit_price_fnct *  (data.discount_amount/100)) if data.discount_method == "per" and data.discount_method else data.discount_amount,
                                "dpp":(data.unit_price_fnct - (data.unit_price_fnct *  (data.discount_amount/100))) if data.discount_method == "per" and data.discount_method  else data.unit_price_fnct -  data.discount_amount,
                                "hargaSatuan":data.price_unit,
                                "hargaTotal":data.unit_price_fnct,
                                "jumlahBarang":data.quantity,
                                "keterangan":data.name,
                                "localId":1,
                                "kodeObjek":"",
                                "nama":data.product_id.name,
                                "ppn":data.price_tax,
                                "ppnbm":0,
                                "tarifPpnbm":0
                                
                                    }for data in self.invoice_line_ids
                                ]
            json_request = {
                                "masaPajakRetur":self.invoice_date.strftime('%m').lstrip('0'),
                                "nilaiReturDpp":sum([data['dpp'] for data in obj_faktur]),
                                "nilaiReturPpn":self.amount_tax,
                                "nilaiReturPpnbm":0,
                                "nomorDokumenRetur":self.name,
                                "tahunPajakRetur":self.invoice_date.strftime('%Y'),
                                "tanggalRetur":self.invoice_date.strftime('%Y%m%d'),
                                "tarifPpn":11,
                                "faktur":{"nomorFaktur":str(self.nomor_seri.name).replace('-','')}
                                
                                }

            pajak_keluaran_cn = requests.post(pajak_express_transaction_url + "/efaktur/pk/retur/upload",headers=header_x,json=json_request)
            pajak_response =  pajak_keluaran_cn.json()
            try:
                if pajak_response['data']['id']:
                    self.is_upload_djp_cn = True
                    self.pajak_express_id = pajak_response['data']['id']
                    self.approval_url = pajak_response['data']['kodeApproval']
                    pajak_keluaran_cn_cetak = requests.get(pajak_express_transaction_url + f"/efaktur/pk/cetak?id={pajak_response['data']['id']}",headers=header_x)
                    pajak_pk_cn_response =  pajak_keluaran_cn_cetak.json()
                    self.efaktur_url = pajak_pk_cn_response['data']

                    
            except TypeError:
                raise ValidationError(f"{pajak_response['message']}\n"
                                      f"request: {json_request}"
                                      )
    
    
    def button_upload_djp(self):
        self.ensure_one()
        pajak_express_transaction_url = self.pajak_express_transaction_url()
        login  = self.login()
        if login.status_code == 200:
            response = login.json()
            token = response['data']['token']
            x_token = self.company_id.pjap_x_token
            if not x_token:
                raise ValidationError(_('You need to generate x-token first in Company.'))
            header_x = {"Authorization": f"Bearer {token}",
                        "x-token":x_token
                        }
            npwpPembeli = str(self.partner_id.vat).replace('.','')
            npwpPembeli = str(npwpPembeli).replace('-','')

            npwpPenjual = str(self.company_id.vat).replace('.','')
            npwpPenjual = str(npwpPenjual).replace('-','')

            obj_faktur = [{
                            "diskon":(data.unit_price_fnct *  (data.discount_amount/100)) if data.discount_method == "per" and data.discount_method else data.discount_amount,
                            "dpp":(data.unit_price_fnct - (data.unit_price_fnct *  (data.discount_amount/100))) if data.discount_method == "per" and data.discount_method  else data.unit_price_fnct -  data.discount_amount,
                            "hargaSatuan":data.price_unit,
                            "hargaTotal":data.unit_price_fnct,
                            "jumlahBarang":data.quantity,
                            "keterangan":data.name,
                            "localId":1,
                            "kodeObjek":"",
                            "nama":data.product_id.name,
                            "ppn":data.price_tax,
                            "ppnbm":0,
                            "tarifPpnbm":0
                            
                                }for data in self.invoice_line_ids
                            ]
            alamat = ''
            
            if self.partner_id.street:
                alamat += f" {self.partner_id.street}"
                
            if self.partner_id.street_number:
                alamat += f" {self.partner_id.street_number}"
                
            if self.partner_id.rukun_tetangga:
                alamat += f", {self.partner_id.rukun_tetangga}"
                
            if self.partner_id.kelurahan:
                alamat += f", {self.partner_id.kelurahan}"
                
            if self.partner_id.kecamatan:
                alamat += f" {self.partner_id.kecamatan}"
                
            if self.partner_id.kecamatan:
                alamat += f" {self.partner_id.kecamatan}"
                
            if self.partner_id.city:
                alamat += f", {self.partner_id.city}"
                
            if self.partner_id.state_id:
                alamat += f" {self.partner_id.state_id.name}"
                
            if self.partner_id.country_id:
                alamat += f" {self.partner_id.country_id.name}"

            alamat_penjual = ''

            if self.company_id.street:
                alamat_penjual += f" {self.company_id.street}"

            if self.company_id.city_id:
                alamat_penjual += f", {self.company_id.city_id.name}"
            
            if self.company_id.state_id:
                alamat_penjual += f" {self.company_id.state_id.name}"
                
            if self.company_id.country_id:
                alamat_penjual += f" {self.company_id.country_id.name}"
                
            json_request = {"alamatLengkapPembeli":alamat,
                            "alamatPenjual":alamat_penjual,
                            "fgPengganti": str(self.status_code),
                            "fgUangMuka":"0",
                            "jenisWp":"0",
                            "totalPpn":0,
                            "totalPpnbm":0,
                            "jumlahDpp":sum([data['dpp'] for data in obj_faktur]),
                            "totalDpp":sum([data['dpp'] for data in obj_faktur]),
                            "keterangan":"Approval Sukses",
                            "keteranganTambahan":self.keterangan_tambahan.name if self.keterangan_tambahan else "",
                            "idKeteranganTambahan":self.keterangan_tambahan.angka if self.keterangan_tambahan else "",
                            "jumlahPpn":self.amount_tax,
                            "jumlahPpnbm":0,
                            "namaPenjual":self.company_id.name,
                            "kdJenisTransaksi":str(self.l10n_id_kode_transaksi),
                            "masaPajak":self.invoice_date.strftime('%m').lstrip('0'),
                            "namaPembeli":self.partner_id.name,
                            "nomorFaktur":str(self.nomor_seri.name).replace('-',''),
                            "npwpPembeli":npwpPembeli,
                            "npwpPenjual":npwpPenjual,
                            "penandatangan":self.signature if self.signature else "",
                            "referensi":self.ref if self.ref else "",
                            "tahunPajak":self.invoice_date.strftime('%Y'),
                            "tanggalFaktur":self.invoice_date.strftime('%Y%m%d'),
                            "tempatPenandatanganan":self.signature_city_id.name if self.signature_city_id else "",
                            "uangMuka":self.uang_muka,
                            "uangMukaPpn":self.uang_muka_ppn,
                            "uangMukaPpnbm":self.uang_muka_ppnbm,
                            "nomorDokumenPendukung":self.nomor_dokumen_pendukung,
                            "tarifPpn":11,
                            "objekFakturs":obj_faktur
                            
                            }
            pajak_keluaran = requests.post(pajak_express_transaction_url + "/efaktur/pk/upload",headers=header_x,json=json_request)
            pajak_response =  pajak_keluaran.json()
            try:
                if pajak_response['data']['id']:
                    self.is_upload_djp = True
                    self.pajak_express_id = pajak_response['data']['id']
                    self.approval_url = pajak_response['data']['kodeApproval']
                    pajak_keluaran_cetak = requests.get(pajak_express_transaction_url + f"/efaktur/pk/cetak?id={pajak_response['data']['id']}",headers=header_x)
                    pajak_pk_response =  pajak_keluaran_cetak.json()
                    self.efaktur_url = pajak_pk_response['data']
                    self.nomor_seri.is_used_pjap = True
                    faktur_ids =  self.env['nsfp.registration'].search([('is_use','=',True)])
                    if faktur_ids:
                        for data in faktur_ids:
                            data.syncron_djp()
                    
            except TypeError:
                raise ValidationError(f"{pajak_response['message']}\n"
                                      f"request:{json_request}"
                                      )
                    
    
    def _generate_efaktur_invoice_custom(self, delimiter):
        """Generate E-Faktur for customer invoice."""
        # Invoice of Customer
        company_id = self.company_id
        dp_product_id = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')

        output_head = '%s%s%s' % (
            _csv_row(FK_HEAD_LIST, delimiter),
            _csv_row(LT_HEAD_LIST, delimiter),
            _csv_row(OF_HEAD_LIST, delimiter),
        )

        for move in self.filtered(lambda m: m.state == 'posted'):
            eTax = move._prepare_etax()

            nik = str(move.partner_id.l10n_id_nik) if not move.partner_id.vat else ''

            if move.l10n_id_replace_invoice_id:
                number_ref = str(move.l10n_id_replace_invoice_id.name) + " replaced by " + str(move.name) + " " + nik
            else:
                number_ref = str(move.name) + " " + nik

            street = ', '.join([x for x in (move.partner_id.street, move.partner_id.street2) if x])

            invoice_npwp = '000000000000000'
            if move.partner_id.vat and len(move.partner_id.vat) >= 12:
                invoice_npwp = move.partner_id.vat
            elif (not move.partner_id.vat or len(move.partner_id.vat) < 12) and move.partner_id.l10n_id_nik:
                invoice_npwp = move.partner_id.l10n_id_nik
            invoice_npwp = invoice_npwp.replace('.', '').replace('-', '')

            # Here all fields or columns based on eTax Invoice Third Party
            eTax['KD_JENIS_TRANSAKSI'] = move.l10n_id_tax_number[0:2] or 0
            eTax['FG_PENGGANTI'] = move.l10n_id_tax_number[2:3] or 0
            eTax['NOMOR_FAKTUR'] = move.l10n_id_tax_number[3:] or 0
            eTax['MASA_PAJAK'] = move.invoice_date.month
            eTax['TAHUN_PAJAK'] = move.invoice_date.year
            eTax['TANGGAL_FAKTUR'] = '{0}/{1}/{2}'.format(move.invoice_date.day, move.invoice_date.month, move.invoice_date.year)
            eTax['NPWP'] = invoice_npwp
            eTax['NAMA'] = move.partner_id.name if eTax['NPWP'] == '000000000000000' else move.partner_id.l10n_id_tax_name or move.partner_id.name
            eTax['ALAMAT_LENGKAP'] = move.partner_id.contact_address.replace('\n', '') if eTax['NPWP'] == '000000000000000' else move.partner_id.l10n_id_tax_address or street
            eTax['JUMLAH_DPP'] = int(round(move.amount_untaxed, 0)) # currency rounded to the unit
            eTax['JUMLAH_PPN'] = int(round(move.amount_tax, 0))
            eTax['ID_KETERANGAN_TAMBAHAN'] = '1' if move.l10n_id_kode_transaksi == '07' else ''
            eTax['REFERENSI'] = number_ref

            lines = move.line_ids.filtered(lambda x: x.product_id.id == int(dp_product_id) and x.price_unit < 0 and not x.display_type)
            eTax['FG_UANG_MUKA'] = 0
            eTax['UANG_MUKA_DPP'] = int(abs(sum(lines.mapped('price_subtotal'))))
            eTax['UANG_MUKA_PPN'] = int(abs(sum(lines.mapped(lambda l: l.price_total - l.price_subtotal))))

            company_npwp = company_id.partner_id.vat or '000000000000000'

            fk_values_list = ['FK'] + [eTax[f] for f in FK_HEAD_LIST[1:]]
            eTax['JALAN'] = company_id.partner_id.l10n_id_tax_address or company_id.partner_id.street
            eTax['NOMOR_TELEPON'] = company_id.phone or ''

            lt_values_list = ['FAPR', company_npwp, company_id.name] + [eTax[f] for f in LT_HEAD_LIST[3:]]

            # HOW TO ADD 2 line to 1 line for free product
            free, sales = [], []

            for line in move.line_ids.filtered(lambda l: not l.exclude_from_invoice_tab and not l.display_type):
                # *invoice_line_unit_price is price unit use for harga_satuan's column
                # *invoice_line_quantity is quantity use for jumlah_barang's column
                # *invoice_line_total_price is bruto price use for harga_total's column
                # *invoice_line_discount_m2m is discount price use for diskon's column
                # *line.price_subtotal is subtotal price use for dpp's column
                # *tax_line or free_tax_line is tax price use for ppn's column
                free_tax_line = tax_line = bruto_total = total_discount = 0.0

                for tax in line.tax_ids:
                    if tax.amount > 0:
                        tax_line += line.price_subtotal * (tax.amount / 100.0)

                invoice_line_unit_price = line.price_unit

                invoice_line_total_price = invoice_line_unit_price * line.quantity

                line_dict = {
                    'KODE_OBJEK': line.product_id.default_code or '',
                    'NAMA': line.product_id.name or '',
                    'HARGA_SATUAN': int(invoice_line_unit_price),
                    'JUMLAH_BARANG': line.quantity,
                    'HARGA_TOTAL': int(invoice_line_total_price),
                    'DPP': int(line.price_subtotal),
                    'product_id': line.product_id.id,
                }

                if line.price_subtotal < 0:
                    for tax in line.tax_ids:
                        free_tax_line += (line.price_subtotal * (tax.amount / 100.0)) * -1.0

                    line_dict.update({
                        'DISKON': int(invoice_line_total_price - line.price_subtotal),
                        'PPN': int(free_tax_line),
                    })
                    free.append(line_dict)
                elif line.price_subtotal != 0.0:
                    invoice_line_discount_m2m = invoice_line_total_price - line.price_subtotal

                    line_dict.update({
                        'DISKON': int(invoice_line_discount_m2m),
                        'PPN': int(tax_line),
                    })
                    sales.append(line_dict)

            sub_total_before_adjustment = sub_total_ppn_before_adjustment = 0.0

            # We are finding the product that has affected
            # by free product to adjustment the calculation
            # of discount and subtotal.
            # - the price total of free product will be
            # included as a discount to related of product.
            for sale in sales:
                for f in free:
                    if f['product_id'] == sale['product_id']:
                        sale['DISKON'] = sale['DISKON'] - f['DISKON'] + f['PPN']
                        sale['DPP'] = sale['DPP'] + f['DPP']

                        tax_line = 0

                        for tax in line.tax_ids:
                            if tax.amount > 0:
                                tax_line += sale['DPP'] * (tax.amount / 100.0)

                        sale['PPN'] = int(tax_line)

                        free.remove(f)

                sub_total_before_adjustment += sale['DPP']
                sub_total_ppn_before_adjustment += sale['PPN']
                bruto_total += sale['DISKON']
                total_discount += round(sale['DISKON'], 2)

            output_head += _csv_row(fk_values_list, delimiter)
            output_head += _csv_row(lt_values_list, delimiter)
            for sale in sales:
                of_values_list = ['OF'] + [str(sale[f]) for f in OF_HEAD_LIST[1:-2]] + ['0', '0']
                output_head += _csv_row(of_values_list, delimiter)

        return output_head
    
    def _generate_efaktur_retur_pajak_keluaran(self, delimiter):
        """Generate E-Faktur for Retur Pajak Keluaran."""
        # Invoice of Customer
        company_id = self.company_id
        dp_product_id = self.env['ir.config_parameter'].sudo().get_param('sale.default_deposit_product_id')

        if self.filtered(lambda x: x.move_type == 'out_refund'):
            output_head = '%s' % (
                    _csv_row(RK_HEAD_LIST, delimiter),
                )
        if self.filtered(lambda x: x.move_type == 'in_refund'):
            output_head = '%s' % (
                    _csv_row(RM_HEAD_LIST, delimiter),
                )
            
        for move in self.filtered(lambda m: m.state == 'posted'):
            eTax = move._prepare_etax()

            nik = str(move.partner_id.l10n_id_nik) if not move.partner_id.vat else ''

            if move.l10n_id_replace_invoice_id:
                number_ref = str(move.l10n_id_replace_invoice_id.name) + " replaced by " + str(move.name) + " " + nik
            else:
                number_ref = str(move.name) + " " + nik

            street = ', '.join([x for x in (move.partner_id.street, move.partner_id.street2) if x])

            invoice_npwp = '000000000000000'
            if move.partner_id.vat and len(move.partner_id.vat) >= 12:
                invoice_npwp = move.partner_id.vat
            elif (not move.partner_id.vat or len(move.partner_id.vat) < 12) and move.partner_id.l10n_id_nik:
                invoice_npwp = move.partner_id.l10n_id_nik
            invoice_npwp = invoice_npwp.replace('.', '').replace('-', '')

            if move.move_type in ['out_refund', 'in_refund']:
            # Here all fields or columns based on eTax Invoice Third Party
                # eTax['RK'] = 'RK',
                eTax['NPWP'] = invoice_npwp
                eTax['NAMA'] = move.partner_id.name if eTax['NPWP'] == '000000000000000' else move.partner_id.l10n_id_tax_name or move.partner_id.name
                eTax['KD_JENIS_TRANSAKSI'] = move.l10n_id_kode_transaksi or 0,
                eTax['FG_PENGGANTI'] =  move.l10n_id_tax_number[2:3] if isinstance(move.l10n_id_tax_number, str) else '0',
                eTax['NOMOR_FAKTUR'] = move.nomor_seri.name or 0,
                eTax['TANGGAL_FAKTUR'] = '{0}/{1}/{2}'.format(move.invoice_date.day, move.invoice_date.month, move.invoice_date.year)
                eTax['NOMOR_DOKUMEN_RETUR'] = move.name
                eTax['TANGGAL_DOKUMEN_RETUR'] = '{0}/{1}/{2}'.format(move.invoice_date.day, move.invoice_date.month, move.invoice_date.year)
                eTax['MASA_PAJAK_RETUR'] = move.invoice_date.month
                eTax['TAHUN_PAJAK_RETUR'] = move.invoice_date.year
                eTax['NILAI_RETUR_DPP'] = int(round(move.amount_total, 0)) # currency rounded to the unit
                eTax['NILAI_RETUR_PPN'] = int(round(move.amount_tax, 0))
                eTax['NILAI_RETUR_PPNBM'] = int(round(move.amount_untaxed, 0))
                # eTax['ID_KETERANGAN_TAMBAHAN'] = '1' if move.l10n_id_kode_transaksi == '07' else ''
                # eTax['REFERENSI'] = number_ref

                # lines = move.line_ids.filtered(lambda x: x.product_id.id == int(dp_product_id) and x.price_unit < 0 and not x.display_type)
                # eTax['FG_UANG_MUKA'] = 0
                # eTax['UANG_MUKA_DPP'] = int(abs(sum(lines.mapped('price_subtotal'))))
                # eTax['UANG_MUKA_PPN'] = int(abs(sum(lines.mapped(lambda l: l.price_total - l.price_subtotal))))

            # company_npwp = company_id.partner_id.vat or '000000000000000'

            # fk_values_list = ['FK'] + [eTax[f] for f in FK_HEAD_LIST[1:]]
            if move.filtered(lambda x: x.move_type == 'out_refund'):
                fk_values_list = ['RK'] + [eTax[f][0] if isinstance(eTax[f], tuple) else eTax[f] for f in RK_HEAD_LIST[1:]]
            if move.filtered(lambda x: x.move_type == 'in_refund'):
                fk_values_list = ['RM'] + [eTax[f][0] if isinstance(eTax[f], tuple) else eTax[f] for f in RM_HEAD_LIST[1:]]

            output_head += _csv_row(fk_values_list, delimiter)

        return output_head

    
    def _generate_efaktur(self, delimiter):
        if self.filtered(lambda x: x.move_type in [ 'out_invoice']):
            if self.filtered(lambda x: not x.l10n_id_kode_transaksi):
                raise UserError(_('Some documents don\'t have a transaction code'))
        # if self.filtered(lambda x: x.move_type != 'out_invoice'):
        #     raise UserError(_('Some documents are not Customer Invoices'))
        
        output_head = ''
        if self.filtered(lambda x: x.move_type in ['in_invoice', 'out_invoice']):
            output_head = self._generate_efaktur_invoice_custom(delimiter)
        if self.filtered(lambda x: x.move_type in ['in_refund', 'out_refund']):
            output_head = self._generate_efaktur_retur_pajak_keluaran(delimiter)

        # output_head = self._generate_efaktur_invoice_custom(delimiter)
        
        my_utf8 = output_head.encode("utf-8")
        out = base64.b64encode(my_utf8)
        # Get the current UTC time
        utc_now = fields.Datetime.now()

        # Convert UTC time to local time based on the user's timezone
        local_datetime = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(utc_now))

        # Format the local datetime to the desired format for the filename
        datetime_str = fields.Datetime.to_string(local_datetime).replace(" ", "-").replace(":", ".")
        datetime_str = datetime_str.rsplit(".", 1)[0]  # Remove the seconds part

        attachment = self.env['ir.attachment'].create({
            'datas': out,
            'name': 'efaktur_%s.csv' % (fields.Datetime.to_string(fields.Datetime.now()).replace(" ", "_")),
            'type': 'binary',
        })

        if self.filtered(lambda x: x.move_type == 'out_refund'):
            attachment.name = 'RK_%s.csv' % (datetime_str)
        elif self.filtered(lambda x: x.move_type == 'in_refund'):
            attachment.name = 'RM_%s.csv' % (datetime_str)

        for record in self:
            record.message_post(attachment_ids=[attachment.id])
            record.l10n_id_attachment_id = attachment.id
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def _generate_efaktur_retur_pajak(self):
        
        header = []
        if self.move_type == 'in_refund':
            header =['RM','NPWP','NAMA','KD_JENIS_TRANSAKSI','FG_PENGGANTI','NOMOR_FAKTUR','TANGGAL_FAKTUR','IS_CREDITABLE','NOMOR_DOKUMEN_RETUR',
                     'TANGGAL_DOKUMEN_RETUR','MASA_PAJAK_RETUR','TAHUN_PAJAK_RETUR','NILAI_RETUR_DPP','NILAI_RETUR_PPN','NILAI_RETUR_PPNBM']
        elif self.move_type == 'out_refund':
            header =['RK','NPWP','NAMA','KD_JENIS_TRANSAKSI','FG_PENGGANTI','NOMOR_FAKTUR','TANGGAL_FAKTUR','NOMOR_DOKUMEN_RETUR',
                     'TANGGAL_DOKUMEN_RETUR','MASA_PAJAK_RETUR','TAHUN_PAJAK_RETUR','NILAI_RETUR_DPP','NILAI_RETUR_PPN','NILAI_RETUR_PPNBM']
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)
        no = 1
        for record in self:
            if record.move_type == 'in_refund':
                row = [
                    'RM',
                    "'" + record.partner_id.vat.replace('.', '').replace('-', '') if record.partner_id.vat else '',
                    record.partner_id.name,
                    record.l10n_id_kode_transaksi or 0,
                    record.l10n_id_tax_number[2:3] if isinstance(record.l10n_id_tax_number, str) else '0',
                    record.nomor_seri.name or 0,
                    record.invoice_date.strftime('%m/%d/%Y'),
                    '0',
                    record.name,
                    record.invoice_date.strftime('%m/%d/%Y'),
                    record.invoice_date.month,
                    record.invoice_date.year,
                    int(record.amount_total),
                    int(record.amount_untaxed),
                    int(record.amount_tax),
                ]
                writer.writerow(row)
            elif record.move_type == 'out_refund':
                row = [
                    'RK',
                    "'" + record.partner_id.vat.replace('.', '').replace('-', '') if record.partner_id.vat else '',
                    record.partner_id.name,
                    record.l10n_id_kode_transaksi or 0,
                    record.l10n_id_tax_number[2:3] if isinstance(record.l10n_id_tax_number, str) else '0',
                    record.nomor_seri.name or 0,
                    record.invoice_date.strftime('%m/%d/%Y'),
                    record.name,
                    record.invoice_date.strftime('%m/%d/%Y'),
                    record.invoice_date.month,
                    record.invoice_date.year,
                    int(record.amount_total),
                    int(record.amount_untaxed),
                    int(record.amount_tax),
                ]
                writer.writerow(row)
                
        file = base64.b64encode(output.getvalue().encode())
        get_date = fields.Datetime.to_string(fields.Datetime.now()).replace(" ", "_")
        prefix = 'RK_' if self.move_type == 'out_refund' else 'RM_'

        # Create the attachment with the appropriate name
        attachment = self.env['ir.attachment'].create({
            'name': f'{prefix}{get_date}.csv',
            'datas': file,
            'type': 'binary',
        })
        return attachment
    
    def _prepare_etax(self):
        # These values are never set
        return {'JUMLAH_PPNBM': 0, 'UANG_MUKA_PPNBM': 0, 'BLOK': '', 'NOMOR': '', 'RT': '', 'RW': '', 'KECAMATAN': '', 'KELURAHAN': '', 
                    'KABUPATEN': '', 'PROPINSI': '', 'KODE_POS': '', 'JUMLAH_BARANG': 0, 'TARIF_PPNBM': 0, 'PPNBM': 0,
                    'KODE_DOKUMEN_PENDUKUNG': '', '@': '',}


    def _get_template(self):
        dir_name = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        static_path = os.path.dirname(dir_name)
        css_path = os.path.join(static_path, 'static/src/file/FORMAT_UPLOAD_EBUPOT_UNIFIKASI.xls')
        self.ebupot_template = base64.b64encode(open(css_path, "rb").read())

    def download_efaktur(self):
        """Collect the data and execute function _generate_efaktur."""
        # if self.move_type in ['in_invoice', 'out_invoice']:
        #     self._generate_efaktur(',')    
        #     return self.download_csv()
        
        # if self.move_type in ['in_refund', 'out_refund']:
        #     return self.download_efaktur_csv()

        self._generate_efaktur(',')    
        return self.download_csv()

    
    def download_efaktur_csv(self):
        attachement = self._generate_efaktur_retur_pajak()

        action = {
            'name': _('Download CSV'),
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % (attachement.id),
            'target': 'self',
        }
        return action

    def download_ebupot(self):
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return ''
        for moveid in active_ids:
            return {
                    'type': 'ir.actions.act_url',
                    'name': 'ebupot',
                    'url': '/web/content/account.move/%s/ebupot_template/FORMAT_UPLOAD_EBUPOT_UNIFIKASI.xls?download=true' %(moveid),
                    }

    @api.onchange('kode_dokumen', 'kode_seri', 'nomor_seri_bupot')
    def _onchange_ebupot(self):
        for rec in self:
            if rec.code:
                if rec.move_type == 'in_invoice':
                    rec.tax_number_bupot = str(rec.kode_dokumen or '') + str(rec.kode_seri or '') + '-' + str(rec.nomor_seri_bupot.name or '')

    @api.depends('partner_id')
    def _compute_need_kode_transaksi(self):
        for move in self:
            move.l10n_id_need_kode_transaksi = False

    # @api.onchange('partner_id','partner_id.faktur_pajak_gabungan')
    # def _onchange_domain(self):
    #     res={}
    #     if self.move_type != 'entry':
    #         is_pjap_integration = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration')
    #         if is_pjap_integration:
    #             domain_line = "[('is_pjap','=',True),('is_used_pjap','=',False),('invoice_id','=', False)]"
    #             if self.partner_id.faktur_pajak_gabungan:
    #                 domain_line = "[('is_pjap','=',True),('is_used_pjap','=',False)]"
    #         else:
    #             if self.partner_id.faktur_pajak_gabungan == True:
    #                 domain_line = "['|', ('invoice_id','=', False),'&', ('invoice_id', '!=', False), ('partner_id', '=', partner_id)]"
    #             else:
    #                 domain_line = "[('invoice_id', '=', False)]"
    #         res['domain'] = {'nomor_seri' : domain_line}
    #     return res

    @api.depends('partner_id','partner_id.faktur_pajak_gabungan')
    def _compute_nomor_seri_domain(self):
        for move in self:
            if move.move_type != 'entry':
                # is_pjap_integration = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration')
                # if is_pjap_integration:
                #     if move.partner_id.faktur_pajak_gabungan:
                #         move.nomor_seri_domain = json.dumps([('is_pjap','=',True),('is_used_pjap','=',False)])
                #     else:
                #         move.nomor_seri_domain = json.dumps([('is_pjap','=',True),('is_used_pjap','=',False),('invoice_id','=', False)])
                # else:
                if move.partner_id.faktur_pajak_gabungan:
                    move.nomor_seri_domain = json.dumps(['|', ('invoice_id','=', False),('company_id','=',move.company_id.id), '&', ('invoice_id', '!=', False), ('partner_id', '=', move.partner_id.id)])
                else:
                    move.nomor_seri_domain = json.dumps([('invoice_id', '=', False),('company_id','=',move.company_id.id)])
            else:
                move.nomor_seri_domain = json.dumps([('company_id','=',move.company_id.id)])


    @api.onchange('partner_id')
    def check_code(self):   
        for rec in self:
            if rec.partner_id:
                rec.code=rec.partner_id.country_id.code 
                if rec.move_type != 'entry':
                    if rec.code == 'ID':
                        if rec.move_type in ['out_invoice']:
                            rec.check = False
                            rec.check_invisible = False
                            rec.check_invisible_ebupot = True

                            if rec.partner_id.l10n_id_pkp == True or rec.partner_id.faktur_pajak_gabungan == True:
                                rec.check = False
                                rec.check_invisible = False
                            else:
                                rec.check = True
                                rec.check_invisible = True
                        elif rec.move_type in ['in_invoice']:
                            rec.check = True
                            rec.check_invisible = True
                            rec.check_invisible_ebupot = False
                        else:
                            rec.check = True
                            rec.check_invisible = True
                            rec.check_invisible_ebupot = True
                    else:
                        rec.check = True
                        rec.check_invisible = True
                        rec.check_invisible_ebupot = True
                else:
                    rec.check = True
                    rec.check_invisible = True
                    rec.check_invisible_ebupot = True
            else:
                rec.code = False
                rec.check = True
                rec.check_invisible = True
                rec.check_invisible_ebupot = True

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(AccountMove, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(result['arch'])
            tax_field = doc.xpath("//field[@name='l10n_id_tax_number']")
            ebupot_field = doc.xpath("//field[@name='tax_number_bupot']")
            move_type = self._context.get('default_move_type')

            if move_type in ['in_invoice'] and tax_field:
                tax_field[0].set("placeholder", "xxx-xxx-xx-xxxxxxxx")
                tax_field[0].set("widget", "mask")
                tax_field[0].set("data-inputmask", "'mask': '999-999-99-99999999'")
                result['arch'] = etree.tostring(doc, encoding='unicode')

            if move_type in ['out_invoice'] and ebupot_field:
                ebupot_field[0].set("placeholder", "x-xx-xxxxxxxx")
                ebupot_field[0].set("widget", "mask")
                ebupot_field[0].set("data-inputmask", "'mask': '9-99-99999999'")
                result['arch'] = etree.tostring(doc, encoding='unicode')

        return result

    @api.onchange('status_code', 'nomor_seri','l10n_id_kode_transaksi')
    def country_tax_number(self):
        for rec in self:
            if rec.move_type != 'entry':
                if rec.code:
                    rec.l10n_id_tax_number = str(rec.l10n_id_kode_transaksi or '') + str(rec.status_code or '') + '-' + str(rec.nomor_seri.name or '')

    @api.constrains('l10n_id_kode_transaksi', 'line_ids')
    def _constraint_kode_ppn(self):
        ppn_tag = self.env.ref('l10n_id.ppn_tag')
        for move in self.filtered(lambda m: m.l10n_id_kode_transaksi != '08'):
            if any(ppn_tag.id in line.tax_tag_ids.ids for line in move.line_ids if line.exclude_from_invoice_tab is False and not line.display_type) \
                    and any(ppn_tag.id not in line.tax_tag_ids.ids for line in move.line_ids if line.exclude_from_invoice_tab is False and not line.display_type):
                # raise UserError(_('Cannot mix VAT subject and Non-VAT subject items in the same invoice with this kode transaksi.'))
                pass
        for move in self.filtered(lambda m: m.l10n_id_kode_transaksi == '08'):
            if any(ppn_tag.id in line.tax_tag_ids.ids for line in move.line_ids if line.exclude_from_invoice_tab is False and not line.display_type):
                raise UserError('Kode transaksi 08 is only for non VAT subject items.')

    def _post(self, soft=True):
        """Set E-Faktur number after validation."""
        for move in self:
            # if move.partner_id.l10n_id_pkp:
            #     if not move.partner_id.faktur_pajak_gabungan:
            #         if len(move.nomor_seri.invoice_id.ids) > 1:
            #             raise UserError('This tax serial number has been used')
            if move.l10n_id_need_kode_transaksi:
                # if not move.l10n_id_kode_transaksi:
                #     raise ValidationError(_('You need to put a Kode Transaksi for this partner.'))
                if move.l10n_id_replace_invoice_id.l10n_id_tax_number:
                    if not move.l10n_id_replace_invoice_id.l10n_id_attachment_id:
                        raise ValidationError(_('Replacement invoice only for invoices on which the e-Faktur is generated. '))
                    rep_efaktur_str = move.l10n_id_replace_invoice_id.l10n_id_tax_number
                    move.l10n_id_tax_number = '%s1%s' % (move.l10n_id_kode_transaksi, rep_efaktur_str[3:])
                else:
                    efaktur = self.env['l10n_id_efaktur.efaktur.range'].pop_number(move.company_id.id)
                    # if not efaktur:
                    #     raise ValidationError(_('There is no Efaktur number available.  Please configure the range you get from the government in the e-Faktur menu. '))
                    try:
                        move.l10n_id_tax_number = '%s0%013d' % (str(move.l10n_id_kode_transaksi), efaktur)
                    except:
                        move.l10n_id_tax_number = move.l10n_id_tax_number
                        

        return super()._post(soft)


    @api.depends('invoice_line_ids.quantity','invoice_line_ids.price_unit','invoice_line_ids.tax_ids', 'invoice_line_ids.tax_ids_ppn', 'state')
    def _compute_invoice_taxes_ppn(self):
        for sheet in self:
            sheet.subtotal_inv_ppn = sum(sheet.invoice_line_ids.mapped('price_total_ppn'))
            sheet.total_tax_ppn = sum(sheet.invoice_line_ids.mapped('taxes_ppn'))
            sheet.total_inv_ppn = sum(sheet.invoice_line_ids.mapped('amount_ppn'))

    @api.onchange('branch_id','partner_id')
    def compute_nomor_seri(self):   
        for rec in self:
            if rec.move_type != 'entry':
                if rec.move_type not in ['in_invoice', 'in_refund'] and rec.partner_id.l10n_id_pkp:
                    domain = [('is_cancel','=',True),('invoice_id','=',False)]
                    if not rec.company_id.is_centralized_efaktur:
                        domain += [('branch_id','=',rec.branch_id.id)]
                    else:
                        domain += [('branch_id','=',False)]
                    efaktur_id = self.env['account.efaktur'].search(domain, order='create_date desc', limit=1)
                    if not efaktur_id:
                        domain.remove(('is_cancel','=',True))
                        efaktur_id = self.env['account.efaktur'].search(domain, order='create_date desc', limit=1)
                    rec.nomor_seri = efaktur_id.id
                    rec.country_tax_number()
                else:
                    rec.nomor_seri = False
                    rec.l10n_id_tax_number = False
            else:
                rec.nomor_seri = False
                rec.l10n_id_tax_number = False

    def reset_efaktur(self):
        result = super(AccountMove, self).reset_efaktur()
        for move in self:
            if move.nomor_seri:
                move.nomor_seri.is_cancel = True
                move.nomor_seri = False
        return result

    @api.constrains('l10n_id_tax_number')
    def _constrains_l10n_id_tax_number(self):
        for record in self.filtered('l10n_id_tax_number'):
            if record.l10n_id_tax_number != re.sub(r'\D', '', record.l10n_id_tax_number):
                record.l10n_id_tax_number = re.sub(r'\D', '', record.l10n_id_tax_number)
            # if record.move_type != 'entry':
            #     if len(record.l10n_id_tax_number) != 16:
            #         raise UserError(_('A tax number should have 16 digits'))
            #     elif record.l10n_id_tax_number[:2] not in dict(self._fields['l10n_id_kode_transaksi'].selection).keys():
            #         raise UserError(_('A tax number must begin by a valid Kode Transaksi'))
            #     elif record.l10n_id_tax_number[2] not in ('0', '1'):
            #         raise UserError(_('The third digit of a tax number must be 0 or 1'))

    # @api.model_create_multi
    # def create(self, vals_list):
    #     if 'nomor_seri' in vals_list:
    #         efaktur_id = self.env['account.efaktur'].browse(vals_list['nomor_seri'])
    #         if efaktur_id:
    #             for rec in self:
    #                 if rec.partner_id.l10n_id_pkp:
    #                     if not rec.partner_id.faktur_pajak_gabungan:
    #                         if rec.nomor_seri:
    #                             if rec.nomor_seri.is_used:
    #                                 raise UserError('This tax serial number has been used')
    #         else:
    #             raise UserError('This tax serial number does not exist')
    #     rslt = super(AccountMove, self).create(vals_list)
    #     return rslt

    # def write(self, vals):
    #     for rec in self:
    #         if rec.move_type != 'entry':
    #             if rec.partner_id.l10n_id_pkp:
    #                 if rec.nomor_seri:
    #                     efaktur_id = self.env['account.efaktur'].browse(rec.nomor_seri)
    #                     if not efaktur_id:
    #                         raise UserError('This tax serial number does not exist')
    #     res = super(AccountMove, self).write(vals)
    #     return res


    def _add_nomor_seri_efaktur(self):
        filled_tax_number = []
        active_ids = self.env.context.get('active_ids')
        moves = self.env['account.move'].browse(active_ids)
        for move in moves:
            # Now move is a record, and you can check its fields
            if move.l10n_id_tax_number and move.l10n_id_tax_number != '0':
                filled_tax_number.append(move.name)
        if filled_tax_number:
            raise UserError('Some documents already have a tax number')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Nomor Seri Efaktur',
            'res_model': 'nomor.seri.efaktur.wizard',
            'view_mode': 'form',
            'views': [(self.env.ref('equip3_accounting_efaktur.view_add_nomor_seri_efaktur_wizard_form').id, 'form')],
            'target': 'new',
            'context': {'active_ids': active_ids, 'active_model': 'account.move'}
        }
        

class AccountTax(models.Model):
    _inherit = "account.tax"

    is_ppn = fields.Boolean(string='Is PPN')
    is_pph = fields.Boolean(string='Is PPH')
    pph_type = fields.Selection([('PPH23','PPh 23'),('PPH4-2','PPh 4-2'),('PPH26','PPh 26'),('PPH22','PPh 22'),('PPH15','PPh 15')], string='PPh Type')
    
class AccountKeteranganTambahan(models.Model):
    _name = 'account.keterangan.tambahan'
    
    angka = fields.Char()
    name  = fields.Text()
    jenis_transaksi = fields.Selection([('07','07'),('08','08')])
    
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "{}: {}".format(record.angka, record.name)))
        return result
    

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    tax_ids_ppn = fields.Many2many(comodel_name='account.tax', string="Taxes", compute='_get_tax_id', default=False)
    price_total_ppn = fields.Monetary(string="Total", readonly=True, store=True)
    amount_ppn = fields.Monetary(string="Subtotal", readonly=True, store=True)
    taxes_ppn = fields.Monetary(string="Tax", readonly=True, store=True)


    @api.depends('quantity', 'price_unit', 'tax_ids', 'price_tax','price_subtotal', 'tax_ids_ppn')
    def _get_tax_id(self):
        for sheet in self:
            sheet.tax_ids_ppn = False
            if self._context.get('default_move_type') != 'entry':
                if sheet.tax_ids:
                    for ppn in sheet.tax_ids:
                        if ppn.is_ppn == True:
                            sheet.tax_ids_ppn += ppn
                rec = self._get_price_total_and_subtotal_ppn_model(price_unit=sheet.price_unit, quantity=sheet.quantity, currency=sheet.currency_id, product=sheet.product_id, partner=sheet.partner_id, taxes=sheet.tax_ids_ppn)
                sheet.amount_ppn = rec['amount_ppn']
                sheet.price_total_ppn = rec['price_total_ppn']
                sheet.taxes_ppn = rec['taxes_ppn']
            
    def _get_price_total_and_subtotal_ppn_model(self, price_unit, quantity, currency, product, partner, taxes):
        res = {}
        # Compute 'price_subtotal'.
        line_discount_price_unit = price_unit
        subtotal = quantity * line_discount_price_unit
        # Compute 'price_total'.
        if taxes:
            force_sign = 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit,
                                                                                      quantity=quantity,
                                                                                      currency=currency,
                                                                                      product=product, partner=partner)
            res['amount_ppn'] = taxes_res['total_excluded']
            res['price_total_ppn'] = taxes_res['total_included']
            res['taxes_ppn'] = taxes_res['total_included'] - taxes_res['total_excluded']
        else:
            res['price_total_ppn'] = res['amount_ppn'] = subtotal
            res['taxes_ppn'] = 0

        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res