# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from .tools import hddecrypt, log_request_error
import base64
import sys
import requests
import json
import datetime
import logging
_logger = logging.getLogger(__name__)



class ManufCeisaDocumentsBC27(models.Model):
    _inherit = 'ceisa.documents.bc27'
    _description = 'CEISA Documents TPB BC-27'

    @api.model
    def default_get(self, fields):
        res = super(ManufCeisaDocumentsBC27, self).default_get(fields)
        # ceisa_inventory = self.env["ir.config_parameter"].sudo().get_param("is_ceisa_it_inventory")
        ceisa_inventory = self.env.company.is_ceisa_it_inventory
        if ceisa_inventory:
            res.update({'is_ceisa_it_inventory': ceisa_inventory})
        else:
            res.update({'is_ceisa_it_inventory': False})
        return res

    def _compute_value_ceisa(self):
        for res in self:
            # ceisa_inventory = self.env["ir.config_parameter"].sudo().get_param("is_ceisa_it_inventory")
            ceisa_inventory = self.env.company.is_ceisa_it_inventory
            if ceisa_inventory:
                res.is_ceisa_it_inventory = ceisa_inventory
            else:
                res.is_ceisa_it_inventory = False

    # is_ceisa_it_inventory = fields.Boolean(string='Set Ceisa 4.0', compute='_compute_value_ceisa', store=False)
    is_ceisa_it_inventory = fields.Boolean(string='Set Ceisa 4.0')

    def action_ceisa_send_document_bc27(self):
        self.check_required_fields()
        res_import = self._send_document_bc27('import_document')
        return res_import

    def _send_document_bc27(self, path):
        # username = self.env['ir.config_parameter'].get_param('ceisa_user', False)
        # password = self.env['ir.config_parameter'].get_param('ceisa_password', False)
        # user_token = self.env['ir.config_parameter'].get_param('ceisa_user_token', False)
        username = self.env.company.ceisa_user
        password = self.env.company.ceisa_password
        user_token = self.env.company.ceisa_user_token
        if username and password:
            if not user_token:
                user_token = self.user_login()
            self._api_ceisa_document_bc27(user_token)
        else:
            raise ValidationError(
                'Username or Password not found. Go to General Settings -> Manufacturing -> CEISA 4.0')
            # form_view = self.env.ref('equip3_manuf_ceisa.ceisa_wizard_login_form')
            # return {
            #     'name': _('User Login to CEISA'),
            #     'type': 'ir.actions.act_window',
            #     'res_model': 'res.users.ceisa',
            #     'views': [(form_view.id, 'form')],
            #     'view_id': form_view.id,
            #     'view_mode': 'form',
            #     'view_type': 'form',
            #     'target': 'new',
            #     'context': {
            #         'default_path_target': path
            #     },
            # }

    def _api_ceisa_document_bc27(self, user_token=False):
        # raise ValueError('This is still underdevelopment')
        company = self.env['res.company'].browse(self.env.user.company_id.id)
        username = self.env['ir.config_parameter'].get_param('ceisa_user', False)
        bankDevisa = self._get_bank_devisa()
        package = self._get_packages()
        container = self._get_containers()
        documents = self._get_documents()
        products = self._get_products()
        entitas = self._get_entitas()
        transports = self._get_transportation()
        url = self.env['ir.config_parameter'].get_param('ceisa.api.url')
        header = {
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Accept': '*/*',
            'Content-Type': 'application/json',
        }
        if user_token:
            header.update({'Authorization': 'Bearer %s' % user_token})
        payload = {
            "nomorAju": self.no_aju,
            "tanggalAju": self.aju_date.strftime('%Y-%m-%d') if self.aju_date else '',
            "asuransi": self.insurance_value if self.insurance_value else 0,
            "bruto": self.weight_bruto_kgm,
            "disclaimer": self.disclaimer if self.disclaimer else '',
            "freight": self.freight,
            "kodeKantor": self.origin_beacukai_office.code if self.origin_beacukai_office else '',
            "kodeTps": self.storehouse_location.code if self.storehouse_location else '',
            "kodeValuta": self.valuta_id.name if self.valuta_id else '',
            "ndpbm": self.ndpbm,
            "netto": self.weight_netto_kg,
            "idPengguna": username if username else '',
            "kotaTtd": self.place_statement if self.place_statement else '',
            "namaTtd": self.name_statement if self.name_statement else '',
            "jabatanTtd": self.job_statement if self.job_statement else '',
            "tanggalTtd": self.date_statement.strftime('%Y-%m-%d') if self.date_statement else '',
            "barang": products,
            "entitas": entitas,
            "kemasan": package,
            "kontainer": container,
            "dokumen": documents,
            "pengangkut": transports,
            "asalData": "S",
            "jumlahKontainer": 1,
            "seri": 1,
            #### Document BC-27
            "kodeDokumen": "27",
            'cif': self.cif_value,
            'hargaPenyerahan': self.submission_price,
            "kodeTps": self.storehouse_location.code if self.storehouse_location else '',
            'biayaPengurang': self.deduction_cost,
            'biayaTambahan': self.additional_cost,
            'vd': self.valuntary_value,
            'kodeJenisTpb': self.tpb_type_id.code if self.tpb_type_id else '',
            'kodeKantorTujuan': self.destination_pabean_office.code if self.destination_pabean_office else '',
            'kodeTujuanPengiriman': self.trade_purpose if self.trade_purpose else '',
            'kodeTujuanTpb': self.destination_tpb_type_id.code if self.destination_tpb_type_id else '',
            'nik': self.nik,
            'nilaiBarang': self.incoterm_value if self.incoterm_value else 0,
            'uangMuka': self.downpayment,
            'nilaiJasa': 0.01,
            "pungutan": self._get_tax_pungutan_line(),
            'ppnPajak': self.ppn_tax,
            'ppnbmPajak': self.ppnbm_tax,
            'tarifPpnPajak': self.tarif_ppn_tax,
            'tarifPpnbmPajak': self.tarif_ppnbm_tax,
        }
        data = json.dumps(payload)
        response_data_auth = []
        try:
            doc_post = requests.post(f'%s/openapi/document' % url, data=data, headers=header, timeout=40, verify=True)
            response_data_auth = json.loads(doc_post.content)
        except requests.exceptions.SSLError as _err:
            self.log_request_error(['SSLError'])
            raise UserError(_('Error! Could not connect to Ceisa server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout as _err:
            self.log_request_error(['ConnectTimeout'])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as _err:
            self.log_request_error(['requests'])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Error! Could not connect to Ceisa account.\n%s') % ex_type)
        if 'errors' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['errors']))
        elif 'Exception' in response_data_auth:
            # raise ValidationError('%s' % (response_data_auth['Exception']))
            if 'Token' in response_data_auth['Exception']:
                new_token = self.user_login()
                if new_token:
                    return self._api_ceisa_document_bc27(new_token)
                else:
                    raise ValidationError('Unknown Error...')
            else:
                raise ValidationError('%s' % (response_data_auth['Exception']))
        elif 'status' in response_data_auth:
            if 'login error' in response_data_auth['status']:
                # return self.show_confirmation_dialog(response_data_auth['message'])
                raise UserError('Username or password is incorrect. Please check your setting!')
            elif 'false' in response_data_auth['status']:
                raise ValidationError(
                    'Status: %s\n\nMessage: %s' % (response_data_auth['status'], response_data_auth['message']))
            elif 'failed' in response_data_auth['status'] or 'FAILED' in response_data_auth['status']:
                raise ValidationError(
                    'Status: %s\n\nMessage: %s' % (response_data_auth['status'], response_data_auth['message']))
            else:
                title = 'Message:'
                msg = response_data_auth['message']
                substatus = response_data_auth['status']
                message = 'Status: %s' % (substatus or '-')
                detail = '<b>%s</b><br/>%s' % (title, msg)
                self.sent_state = True
                return self.env['ceisa.pop.message'].message(message, detail) if message else True
        return response_data_auth

    def _get_products(self):
        products = []
        iprod = 1
        if self.product_line_id:
            for prod in self.product_line_id:
                products.append({
                    "fob": prod.fob_price,
                    "hargaPatokan": prod.estimation_price,
                    "hargaSatuan": prod.product_price,
                    "jumlahKemasan": prod.package_qty,
                    "jumlahSatuan": prod.product_qty,
                    "kodeBarang": prod.code,
                    "kodeDaerahAsal": prod.origin_city.city_code if prod.origin_city else '',
                    "kodeDokumen": "30",
                    "kodeJenisKemasan": prod.package_type.code if prod.package_type else '',
                    "kodeNegaraAsal": prod.origin_country.code if prod.origin_country else '',
                    "kodeSatuanBarang": prod.product_uom.code if prod.product_uom else '',
                    "merk": prod.merk if prod.merk else '',
                    "ndpbm": self.ndpbm,
                    "netto": prod.netto_weight,
                    "nilaiBarang": 0,
                    "nilaiDanaSawit": 0,
                    "posTarif": "0",
                    "seriBarang": iprod,
                    "spesifikasiLain": "-",
                    "tipe": prod.product_type,
                    "ukuran": prod.product_size,
                    "uraian": prod.product_id.name if prod.product_id else '',
                    "volume": prod.volume,
                    "barangDokumen": [
                        {
                            "seriDokumen": 1
                        }
                    ],
                    "barangPemilik": [],
                    "barangTarif": [],
                    # "cif": 0,
                    # "cifRupiah": 0,
                    # "hargaEkspor": 0,
                    # "hargaPerolehan": 0,
                    # "kodeAsalBahanBaku": "0",
                })
                iprod += 1
        return products


    def _get_entitas(self):
        entitases = []
        entitases.append({
            "alamatEntitas": self.exim_address if self.exim_address else '',
            "kodeEntitas": '3',
            "kodeJenisIdentitas": self.exim_identity_type if self.exim_identity_type else '',
            "namaEntitas": self.exim_partner_id.display_name if self.exim_partner_id else '',
            "nomorIdentitas": self.exim_identity_number if self.exim_identity_number else '',
            "nomorIjinEntitas": self.exim_permit_number if self.exim_permit_number else '',
            "seriEntitas": 1,
            "tanggalIjinEntitas": self.exim_permit_date.strftime('%Y-%m-%d') if self.exim_permit_date else ''
        })
        ### PEMILIK
        entitases.append({
            "alamatEntitas": self.owner_address if self.owner_address else '',
            "kodeEntitas": '7',
            "kodeJenisIdentitas": self.owner_identity_type if self.owner_identity_type else '',
            "namaEntitas": self.owner_partner_id.display_name if self.owner_partner_id else '',
            "kodeJenisApi": self.owner_codeapi if self.owner_codeapi else '',
            "kodeStatus": self.owner_status_code.code if self.owner_status_code else '',
            "nomorIdentitas": self.owner_identity_number if self.owner_identity_number else '',
            "seriEntitas": 2
        })
        ### PENERIMA / RECIPIENT
        entitases.append({
            "alamatEntitas": self.recipient_address if self.recipient_address else '',
            "kodeEntitas": '8',
            "kodeJenisIdentitas": self.recipient_identity_type if self.recipient_identity_type else '',
            "namaEntitas": self.recipient_partner_id.display_name if self.recipient_partner_id else '',
            "kodeJenisApi": self.recipient_codeapi if self.recipient_codeapi else '',
            "kodeStatus": self.recipient_status_code.code if self.recipient_status_code else '',
            "nomorIdentitas": self.recipient_identity_number if self.recipient_identity_number else '',
            "nomorIjinEntitas": self.recipient_permit_number if self.recipient_permit_number else '',
            "seriEntitas": 3,
            "tanggalIjinEntitas": self.recipient_permit_date.strftime('%Y-%m-%d') if self.recipient_permit_date else ''
        })
        inti = 4
        if self.entitas_line_id:
            for enti in self.entitas_line_id:
                if enti.code.code == '4' or enti.code.code == '7' or enti.code.code == '11':
                    entitases.append({
                        "alamatEntitas": enti.address if enti.address else '',
                        "kodeEntitas": enti.code.code if enti.code else '',
                        "kodeJenisIdentitas": enti.identity_type if enti.identity_type else '',
                        "namaEntitas": enti.name if enti.name else '',
                        "nomorIdentitas": enti.number if enti.number else '',
                        "seriEntitas": inti
                    })
                else:
                    entitases.append({
                        "alamatEntitas": enti.address if enti.address else '',
                        "kodeEntitas": enti.code.code if enti.code else '',
                        "kodeNegara": enti.country_id.code if enti.country_id else '',
                        "namaEntitas": enti.name if enti.name else '',
                        "seriEntitas": inti
                    })
                inti += 1
        return entitases

    def _get_tax_pungutan_line(self):
        pungutan = []
        itax = 1
        if self.tax_line_id:
            for rawtax in self.tax_line_id:
                pungutan.append({
                    "idPungutan": itax,
                    "kodeFasilitasTarif": rawtax.tax_facilities_fee.code if rawtax.tax_facilities_fee else '',
                    "kodeJenisPungutan": rawtax.tax_type.code if rawtax.tax_type else '',
                    "nilaiPungutan": rawtax.tax_value if rawtax.tax_value else 0.01,
                })
                itax += 1
        return pungutan

    def _get_transportation(self):
        transports = []
        itrans = 1
        if self.transportation_line_id:
            for trans in self.transportation_line_id:
                transports.append({
                    "kodeBendera": trans.country_id.code if trans.country_id else '',
                    "namaPengangkut": trans.name,
                    "nomorPengangkut": trans.number,
                    "kodeCaraAngkut": trans.transport_type if trans.transport_type else '',
                    "seriPengangkut": itrans
                })
                itrans += 1
        return transports

    def _get_documents(self):
        documents = []
        idoc = 1
        if self.document_line_id:
            for doc in self.document_line_id:
                documents.append({
                    "idDokumen": idoc,
                    "kodeDokumen": doc.type.code if doc.type else '',
                    "nomorDokumen": doc.number,
                    "seriDokumen": idoc,
                    "tanggalDokumen": doc.doc_date.strftime('%Y-%m-%d') if doc.doc_date else '' ,
                })
                idoc += 1
        return documents

    def _get_containers(self):
        containers = []
        icon = 1
        if self.container_line_id:
            for cont in self.container_line_id:
                containers.append({
                    "kodeTipeKontainer": cont.type.code if cont.type else '',
                    "kodeUkuranKontainer": cont.size.code if cont.size else '',
                    "nomorKontainer": cont.number,
                    "seriKontainer": icon,
                    "kodeJenisKontainer": cont.category if cont.category else ''
                })
                icon += 1
        return containers

    def _get_packages(self):
        packages = []
        ipa = 1
        if self.package_line_id:
            for pack in self.package_line_id:
                packages.append({
                    "jumlahKemasan": pack.value,
                    "kodeJenisKemasan": pack.package_id.code if pack.package_id else '',
                    "merkKemasan": pack.merek,
                    "seriKemasan": ipa
                })
                ipa += 1
        return packages

    def _get_bank_devisa(self):
        banks = []
        iba = 1
        banks.append({
            "kodeBank": self.bank_payment_id.code if self.bank_payment_id else '',
            "seriBank": iba,
        })
        return banks

    def update_ndpbm(self):
        company = self.env['res.company'].browse(self.env.user.company_id.id)
        # username = company.ceisa_user
        # password = company.ceisa_password
        # user_token = company.ceisa_token
        username = self.env['ir.config_parameter'].get_param('ceisa_user', False)
        password = self.env['ir.config_parameter'].get_param('ceisa_password', False)
        user_token = self.env['ir.config_parameter'].get_param('ceisa_token', False)
        if username and password:
            if self.valuta_id:
                data_kurs = self.cek_valuta_asing(self.valuta_id.name, user_token)
                if 'Exception' in data_kurs:
                    if 'Token' in data_kurs['Exception']:
                        new_token = self.refresh_user_token()
                        if new_token:
                            data_kurs2 = self.cek_valuta_asing(self.valuta_id.name, new_token)
                            if 'Exception' in data_kurs2:
                                raise ValidationError('%s' % (data_kurs2['Exception']))
                        else:
                            return {'name': 'User Login to CEISA',
                                    'type': 'ir.actions.act_window',
                                    'res_model': 'res.users.ceisa',
                                    'view_id': False,
                                    'view_mode': 'form',
                                    'view_type': 'form',
                                    'target': 'new',
                                    'context': {
                                        'error_message': 'Token specified is invalid or has expired.',
                                        'default_path_target': 'ndpbm'
                                    },
                            }
                    else:
                        raise ValidationError('%s' % (data_kurs['Exception']))
            else:
                raise ValidationError('Valuta tidak ditemukan')
        else:
            return {
                'name': 'User Login to CEISA',
                'type': 'ir.actions.act_window',
                'res_model': 'res.users.ceisa',
                'view_id': False,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {
                    'default_path_target': 'ndpbm'
                },
            }

    def update_storehouse_location(self):
        company = self.env['res.company'].browse(self.env.user.company_id.id)
        # username = company.ceisa_user
        # password = company.ceisa_password
        # user_token = company.ceisa_token
        username = self.env['ir.config_parameter'].get_param('ceisa_user', False)
        password = self.env['ir.config_parameter'].get_param('ceisa_password', False)
        user_token = self.env['ir.config_parameter'].get_param('ceisa_token', False)
        if username and password:
            if self.origin_beacukai_office:
                data_port = self.get_gudang_penimbunan(self.origin_beacukai_office.code, user_token)
                if 'Exception' in data_port:
                    if 'Token' in data_port['Exception']:
                        new_token = self.refresh_user_token()
                        if new_token:
                            data_port2 = self.get_gudang_penimbunan(self.origin_beacukai_office.code, new_token)
                            if 'Exception' in data_port2:
                                raise ValidationError('%s' % (data_port2['Exception']))
                        else:
                            return {'name': 'User Login to CEISA',
                                   'type': 'ir.actions.act_window',
                                   'res_model': 'res.users.ceisa',
                                   'view_id': False,
                                   'view_mode': 'form',
                                   'view_type': 'form',
                                   'target': 'new',
                                   'context': {
                                       'error_message': 'Token specified is invalid or has expired.',
                                       'default_path_target': 'storehouse_location'
                                   },
                            }
                    else:
                        raise ValidationError('%s' % (data_port['Exception']))
            else:
                raise ValidationError('Kantor pabean tidak ditemukan')
        else:
            return {
                'name': 'User Login to CEISA',
                'type': 'ir.actions.act_window',
                'res_model': 'res.users.ceisa',
                'view_id': False,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {
                    'default_path_target': 'storehouse_location'
                },
            }

    def update_origin_port_export(self):
        owner_country = False
        if self.entitas_line_id:
            for owner in self.entitas_line_id:
                if owner.code == '7':
                    owner_country = owner.country_id.code

        company = self.env['res.company'].browse(self.env.user.company_id.id)
        # username = company.ceisa_user
        # password = company.ceisa_password
        # user_token = company.ceisa_token
        username = self.env['ir.config_parameter'].get_param('ceisa_user', False)
        password = self.env['ir.config_parameter'].get_param('ceisa_password', False)
        user_token = self.env['ir.config_parameter'].get_param('ceisa_token', False)
        if username and password:
            if self.origin_beacukai_office:
                data_port = self.get_pelabuhan_pabean_by_beacukai_office(self.origin_beacukai_office.code, owner_country, user_token)
                if 'Exception' in data_port:
                    if 'Token' in data_port['Exception']:
                        new_token = self.refresh_user_token()
                        if new_token:
                            data_port2 = self.get_pelabuhan_pabean_by_beacukai_office(self.origin_beacukai_office.code, owner_country, new_token)
                            if 'Exception' in data_port2:
                                raise ValidationError('%s' % (data_port2['Exception']))
                        else:
                            return {'name': 'User Login to CEISA',
                                    'type': 'ir.actions.act_window',
                                    'res_model': 'res.users.ceisa',
                                    'view_id': False,
                                    'view_mode': 'form',
                                    'view_type': 'form',
                                    'target': 'new',
                                    'context': {
                                        'error_message': 'Token specified is invalid or has expired.',
                                        'default_path_target': 'origin_port'
                                    },
                            }
                    else:
                        raise ValidationError('%s' % (data_port['Exception']))
            else:
                raise ValidationError('Kantor pabean tidak ditemukan')
        else:
            return {
                'name': 'User Login to CEISA',
                'type': 'ir.actions.act_window',
                'res_model': 'res.users.ceisa',
                'view_id': False,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {
                    'default_path_target': 'origin_port'
                },
            }

    def update_import_destination_port_by_country(self):
        ###diambil dari negara penerima
        for cust in self.entitas_line_id:
            if cust.code == '8':
                cust_country = cust.country_id.code
            else:
                raise ValidationError('Negara Penerima pada Entitas tidak ditemukan')
        company = self.env['res.company'].browse(self.env.user.company_id.id)
        # username = company.ceisa_user
        # password = company.ceisa_password
        # user_token = company.ceisa_token
        username = self.env['ir.config_parameter'].get_param('ceisa_user', False)
        password = self.env['ir.config_parameter'].get_param('ceisa_password', False)
        user_token = self.env['ir.config_parameter'].get_param('ceisa_token', False)
        if username and password:
            if cust_country:
                data_port = self.get_pelabuhan_pabean_by_kode_negara(cust_country, user_token)
                if 'Exception' in data_port:
                    if 'Token' in data_port['Exception']:
                        new_token = self.refresh_user_token()
                        if new_token:
                            data_port2 = self.get_pelabuhan_pabean_by_kode_negara(cust_country, new_token)
                            if 'Exception' in data_port2:
                                raise ValidationError('%s' % (data_port2['Exception']))
                        else:
                            return {'name': 'User Login to CEISA',
                                    'type': 'ir.actions.act_window',
                                    'res_model': 'res.users.ceisa',
                                    'view_id': False,
                                    'view_mode': 'form',
                                    'view_type': 'form',
                                    'target': 'new',
                                    'context': {
                                        'error_message': 'Token specified is invalid or has expired.',
                                        'default_path_target': 'port_by_country'
                                    },
                            }
                    else:
                        raise ValidationError('%s' % (data_port['Exception']))
            else:
                raise ValidationError('Kantor pabean tidak ditemukan')
        else:
            return {
                'name': 'User Login to CEISA',
                'type': 'ir.actions.act_window',
                'res_model': 'res.users.ceisa',
                'view_id': False,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'new',
                'context': {
                    'default_path_target': 'port_by_country'
                },
            }

    def cek_valuta_asing(self, kodeValuta, user_token=False):
        url = self.env['ir.config_parameter'].get_param('ceisa.api.url')
        header = {
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Accept': '*/*',
            'Content-Type': 'application/json',
        }
        if user_token:
            header.update({'Authorization': 'Bearer %s' % user_token})

        # payload = {
        #     'kodeValuta': self.valuta_id.name,
        #     'tanggal': datetime.datetime.now().strftime('%Y-%m-%d')
        # }
        # data = json.dumps(payload)
        response_data_auth = []
        try:
            kurs = requests.get(f'%s/openapi/kurs/%s' % (url, kodeValuta), headers=header, timeout=40, verify=True)
            response_data_auth = json.loads(kurs.content)
        except requests.exceptions.SSLError as _err:
            self.log_request_error(['SSLError'])
            raise UserError(_('Error! Could not connect to Ceisa server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout as _err:
            self.log_request_error(['ConnectTimeout'])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as _err:
            self.log_request_error(['requests'])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Error! Could not connect to Ceisa account.\n%s') % ex_type)

        if 'errors' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['errors']))
        elif 'status' in response_data_auth and 'error' in str(response_data_auth['status']):
            if 'login error' in str(response_data_auth['status']):
                # return self.show_confirmation_dialog(response_data_auth['message'])
                raise UserError('Username or password is incorrect. Please check your setting!')
            else:
                raise ValidationError(
                    'Status: %s\nMessage: %s' % (response_data_auth['status'], response_data_auth['message']))
        elif 'data' in response_data_auth:
            if not response_data_auth['data']:
                raise ValidationError('Data Valuta Asing: %s - tidak ditemukan' %
                                      kodeValuta)
            for kurs in response_data_auth['data']:
                self.ndpbm = kurs['nilaiKurs']
        return response_data_auth

    def get_gudang_penimbunan(self, kodeoffice, user_token=False):
        _context = self.env.context
        url = self.env['ir.config_parameter'].get_param('ceisa.api.url')
        company = self.env['res.company'].browse(self.env.user.company_id.id)
        office_obj = self.env['ceisa.beacukai.office'].browse(kodeoffice)
        storehouse = self.env['ceisa.storehouse.location']
        refresh_token = company.ceisa_token
        header = {
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Accept': '*/*',
            'Content-Type': 'application/json',
        }
        if user_token:
            header.update({'Authorization': 'Bearer %s' % user_token})

        payload = {
            'kodeKantor': self.origin_beacukai_office.code
        }
        data = json.dumps(payload)
        response_data_auth = []

        try:
            kurs = requests.get(f'%s/openapi/gudangTPS/kodeKantor/%s' % (url, kodeoffice), headers=header, timeout=40, verify=True)
            response_data_auth = json.loads(kurs.content)
        except requests.exceptions.SSLError as _err:
            self.log_request_error(['SSLError'])
            raise UserError(_('Error! Could not connect to Ceisa server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout as _err:
            self.log_request_error(['ConnectTimeout'])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as _err:
            self.log_request_error(['requests'])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Error! Could not connect to Ceisa account.\n%s') % ex_type)

        if 'errors' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['errors']))
        elif 'status' in response_data_auth and 'error' in str(response_data_auth['status']):
            if 'login error' in str(response_data_auth['status']):
                # return self.show_confirmation_dialog(response_data_auth['message'])
                raise UserError('Username or password is incorrect. Please check your setting!')
            else:
                raise ValidationError(
                    'Status: %s\nMessage: %s' % (response_data_auth['status'], response_data_auth['message']))
        elif 'data' in response_data_auth:
            if not response_data_auth['data']:
                office_obj.write({'state': True})
                raise ValidationError('Data Tempat Penimbunan Sementara - %s: %s - tidak ditemukan' %
                                      (kodeoffice, self.origin_beacukai_office.name))
            for tps in response_data_auth['data']:
                search_tps = storehouse.search([('code', '=', tps['kodeGudang'])], limit=1)
                if not search_tps:
                    storehouse.create({
                        'name': tps['namaGudang'],
                        'code': tps['kodeGudang'],
                        'beacukai_office_id': self.origin_beacukai_office.id,
                    })
                    office_obj.write({'state': True})
        return response_data_auth

    def get_pelabuhan_pabean_by_beacukai_office(self, kodeoffice, country_id, user_token=False):
        url = self.env['ir.config_parameter'].get_param('ceisa.api.url')
        country_id = self.env['res.country'].browse(country_id)
        port_office = self.env['ceisa.pabean.office']
        header = {
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Accept': '*/*',
            'Content-Type': 'application/json',
        }
        if user_token:
            header.update({'Authorization': 'Bearer %s' % user_token})
        response_data_auth = []
        count = 2
        try:
            kurs = requests.get(f'%s/openapi/pelabuhan/kodeKantor/%s' % (url, kodeoffice), headers=header, timeout=40, verify=True)
            response_data_auth = json.loads(kurs.content)
        except requests.exceptions.SSLError as _err:
            self.log_request_error(['SSLError'])
            raise UserError(_('Error! Could not connect to Ceisa server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout as _err:
            self.log_request_error(['ConnectTimeout'])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as _err:
            self.log_request_error(['requests'])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Error! Could not connect to Ceisa account.\n%s') % ex_type)
        if 'errors' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['errors']))
        elif 'status' in response_data_auth and 'error' in str(response_data_auth['status']):
            if 'login error' in str(response_data_auth['status']):
                # return self.show_confirmation_dialog(response_data_auth['message'])
                raise UserError('Username or password is incorrect. Please check your setting!')
            else:
                raise ValidationError(
                    'Status: %s\nMessage: %s' % (response_data_auth['status'], response_data_auth['message']))
        elif 'data' in response_data_auth:
            if not response_data_auth['data']:
                raise ValidationError('Data pelabuhan - %s: %s - tidak ditemukan' % (
                self.origin_beacukai_office.code, self.origin_beacukai_office.name))
            for port in response_data_auth['data']:
                search_port = port_office.search([('code', '=', port['kodePelabuhan'])], limit=1)
                if not search_port:
                    port_office.create({
                        'name': port['namaPelabuhan'],
                        'code': port['kodePelabuhan'],
                        'beacukai_office_id': self.origin_beacukai_office.id,
                        'country_id': country_id.id
                    })
        return response_data_auth

    def get_pelabuhan_pabean_by_kode_negara(self, kodenegara, user_token=False):
        url = self.env['ir.config_parameter'].get_param('ceisa.api.url')
        country_id = self.env['res.country'].browse(kodenegara)
        port_office = self.env['ceisa.pabean.office']
        header = {
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Accept': '*/*',
            'Content-Type': 'application/json',
        }
        if not kodenegara:
            raise ValidationError('Negara Penerima pada Entitas tidak ditemukan')
        if user_token:
            header.update({'Authorization': 'Bearer %s' % user_token})
        response_data_auth = []
        try:
            kurs = requests.get(f'%s/openapi/pelabuhan/kata/%s' % (url, kodenegara), headers=header, timeout=40, verify=True)
            response_data_auth = json.loads(kurs.content)
        except requests.exceptions.SSLError as _err:
            self.log_request_error(['SSLError'])
            raise UserError(_('Error! Could not connect to Ceisa server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout as _err:
            self.log_request_error(['ConnectTimeout'])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as _err:
            self.log_request_error(['requests'])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Error! Could not connect to Ceisa account.\n%s') % ex_type)

        if 'errors' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['errors']))
        elif 'status' in response_data_auth and 'error' in str(response_data_auth['status']):
            if 'login error' in str(response_data_auth['status']):
                # return self.show_confirmation_dialog(response_data_auth['message'])
                raise UserError('Username or password is incorrect. Please check your setting!')
            else:
                raise ValidationError(
                    'Status: %s\nMessage: %s' % (response_data_auth['status'], response_data_auth['message']))
        elif 'data' in response_data_auth:
            if not response_data_auth['data']:
                country_id.write({'ceisa_state': True})
                raise ValidationError('Data pelabuhan: %s - tidak ditemukan' %
                    kodenegara)
            for port in response_data_auth['data']:
                search_port = port_office.search([('code', '=', port['kodePelabuhan'])], limit=1)
                if not search_port:
                    port_office.create({
                        'name': port['namaPelabuhan'],
                        'code': port['kodePelabuhan'],
                        'country_id': country_id.id
                    })
                    country_id.write({'ceisa_state': True})
        return response_data_auth

    def refresh_user_token(self):
        url = self.env['ir.config_parameter'].get_param('ceisa.api.url')
        company = self.env['res.company'].browse(self.env.user.company_id.id)

        refresh_token = company.ceisa_refresh_token
        header = {
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Accept': '*/*',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % refresh_token
        }
        response_data_auth = []
        new_token = ''
        try:
            auth_user = requests.post(f'%s/auth-amws/v1/user/update-token' % url, headers=header, timeout=40, verify=True)
            response_data_auth = json.loads(auth_user.content)
        except requests.exceptions.SSLError as _err:
            self.log_request_error(['SSLError'])
            raise UserError(_('Error! Could not connect to Ceisa server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout as _err:
            self.log_request_error(['ConnectTimeout'])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as _err:
            self.log_request_error(['requests'])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Error! Could not connect to Ceisa account.\n%s') % ex_type)

        if 'errors' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['errors']))
        elif 'Exception' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['Exception']))
        elif 'status' in response_data_auth and 'error' in str(response_data_auth['status']):
            if 'login error' in str(response_data_auth['status']):
                return False
            elif 'update token error' in str(response_data_auth['status']):
                return False
            else:
                raise ValidationError(
                    'Status: %s\nMessage: %s' % (response_data_auth['status'], response_data_auth['message']))
        elif 'item' in response_data_auth:
            company.sudo().write({
                'ceisa_token': response_data_auth['item']['access_token'],
                'ceisa_refresh_token': response_data_auth['item']['refresh_token'],
                'ceisa_id_token': response_data_auth['item']['id_token'],
                'ceisa_token_type': response_data_auth['item']['token_type'],
                'ceisa_status': True
            })
            new_token = response_data_auth['item']['access_token']
        return new_token

    def user_login(self):
        url = self.env['ir.config_parameter'].get_param('ceisa.api.url')
        login_path = self.env['ir.config_parameter'].get_param('ceisa.login.path.api.url')
        # company = self.env['res.company'].browse(self.env.user.company_id.id)
        # ceisa_user = self.env['ir.config_parameter'].get_param('ceisa_user')
        # ceisa_password = self.env['ir.config_parameter'].get_param('ceisa_password')
        # ceisa_user_key = self.env['ir.config_parameter'].get_param('ceisa_user_key')
        ceisa_user = self.env.company.ceisa_user
        ceisa_password = self.env.company.ceisa_password
        ceisa_user_key = self.env.company.ceisa_user_key
        if ceisa_password and ceisa_user_key:
            password = hddecrypt(ceisa_password, ceisa_user_key)
        else:
            password = None
        header = {
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Accept': '*/*',
            'Content-Type': 'application/json'
        }

        payload = {'username': ceisa_user,
                   'password': password
        }
        data = json.dumps(payload)
        response_data_auth = []
        try:
            auth_user = requests.post(f'%s/%s' % (url, login_path), data=data, headers=header, timeout=40,
                                      verify=True)
            response_data_auth = json.loads(auth_user.content)
        except requests.exceptions.SSLError as _err:
            log_request_error(['SSLError'])
            raise UserError(_('Error! Could not connect to Ceisa server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout as _err:
            log_request_error(['ConnectTimeout'])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as _err:
            log_request_error(['requests'])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Error! Could not connect to Ceisa account.\n%s') % ex_type)
        if 'errors' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['errors']))
        elif 'status' in response_data_auth and 'login error' in response_data_auth['status']:
            raise UserError('Username or password is incorrect. Please check your setting!')
        elif 'Exception' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['Exception']))
        elif 'status' in response_data_auth and 'success' in response_data_auth['status']:
            if 'item' in response_data_auth:
                if response_data_auth['item'] == None:
                    raise ValidationError('No Response from the Server. Please contact your Administrator!')
                else:
                    ceisa_token = response_data_auth['item']['access_token']
                    ceisa_refresh_token = response_data_auth['item']['refresh_token']
                    return ceisa_token
        return response_data_auth

    def check_required_fields(self):
        if not self.no_aju:
            raise ValidationError('Error! Nomor Pengajuan is not found.')
        if not self.valuta_id:
            raise ValidationError('Error! Valuta is not found.')
        if not self.origin_pabean_export_office:
            raise ValidationError('Error! Kantor Pabean Muat Ekspor is not found.')
        if not self.disclaimer:
            raise ValidationError('Error! Persetujuan Pengiriman is not found.')
        if not self.payment_term:
            raise ValidationError('Error! Cara Pembayaran is not found.')
        if not self.freight:
            raise ValidationError('Error! Freight is not found.')
        if not self.insurance_type:
            raise ValidationError('Error! Jenis Asuransi is not found.')
        if not self.insurance_value:
            raise ValidationError('Error! Nilai Asuransi is not found.')
        if not self.weight_bruto_kgm:
            raise ValidationError('Error! Berat Kotor (Kgm) is not found.')
        if not self.weight_netto_kg:
            raise ValidationError('Error! Berat Bersih (Kg) is not found.')
        if not self.place_statement:
            raise ValidationError('Error! Lokasi Pembuatan Pernyataan is not found.')
        if not self.date_statement:
            raise ValidationError('Error! Tanggal Pembuatan Pernyataan is not found.')
        if not self.name_statement:
            raise ValidationError('Error! Nama Pembuat Pernyataan is not found.')
        if not self.job_statement:
            raise ValidationError('Error! Jabatan Pembuat Pernyataan is not found.')
        # if not self.origin_beacukai_office:
        #     raise ValidationError('Error! Kantor Pabean Pemuatan is not found.')
        # if not self.destination_port_office:
        #     raise ValidationError('Error! Pelabuhan Tujuan is not found.')
        if not self.import_type:
            raise ValidationError('Error! Jenis Impor is not found.')
        if not self.additional_cost:
            raise ValidationError('Error! Biaya Penambah is not found.')
        if not self.deduction_cost:
            raise ValidationError('Error! Biaya Pengurang is not found.')
        if not self.cif_value:
            raise ValidationError('Error! Nilai Pabean is not found.')
        if not self.maklon_value:
            raise ValidationError('Error! Nilai Maklon is not found.')
        if not self.exim_date_estimation:
            raise ValidationError('Error! Perkiraan Tanggal Tiba is not found.')
        if not self.storehouse_location:
            raise ValidationError('Error! Tempat Penimbunan Sementara is not found.')
        if not self.exim_identity_type:
            raise ValidationError('Error! Jenis Identitas Pengusaha is not found.')
        if not self.exim_identity_number:
            raise ValidationError('Error! Nomor Identitas Pengusaha is not found.')
        if not self.exim_partner_id:
            raise ValidationError('Error! Partner ID Pengusaha is not found.')
        if not self.exim_address:
            raise ValidationError('Error! Alamat Pengusaha is not found.')
        if not self.exim_country:
            raise ValidationError('Error! Negara Pengguna is not found.')
        if not self.exim_permit_number:
            raise ValidationError('Error! Nomor Izin Pengusaha is not found.')
        if not self.exim_permit_date:
            raise ValidationError('Error! Tanggal Izin Pengusaha is not found.')
        if not self.owner_partner_id:
            raise ValidationError('Error! Nama Pemilik is not found.')
        if not self.owner_identity_type:
            raise ValidationError('Error! Jenis Identitas Pemilik is not found.')
        if not self.owner_identity_number:
            raise ValidationError('Error! Nomor Identitas Pemilik is not found.')
        if not self.owner_codeapi:
            raise ValidationError('Error! Kode API Pemilik is not found.')
        if not self.owner_status_code:
            raise ValidationError('Error! Status Kode Pemilik is not found.')
        if not self.owner_address:
            raise ValidationError('Error! Alamat Pemilik is not found.')
        if not self.recipient_partner_id:
            raise ValidationError('Error! Nama Penerima is not found.')
        if not self.recipient_identity_number:
            raise ValidationError('Error! Nomor Identitas Penerima is not found.')
        if not self.recipient_permit_number:
            raise ValidationError('Error! Nomor Izin Penerima is not found.')
        if not self.recipient_permit_date:
            raise ValidationError('Error! Tanggal Izin Penerima is not found.')
        if not self.recipient_address:
            raise ValidationError('Error! Alamat Penerima is not found.')
        if not self.recipient_status_code:
            raise ValidationError('Error! Status Kode Penerima is not found.')
        if not self.recipient_codeapi:
            raise ValidationError('Error! Jenis API Penerima is not found.')


    def show_confirmation_dialog(self, error_msg):
        actions = { 'name': 'User Login to CEISA',
                    'type': 'ir.actions.act_window',
                    'res_model': 'res.users.ceisa',
                    'view_id': False,
                    'view_mode': 'form',
                    'view_type': 'form',
                    'target': 'new',
                    'context': {
                        'error_message': error_msg,
                        'default_path_target': 'refresh_token'
                    },
        }
        return actions
