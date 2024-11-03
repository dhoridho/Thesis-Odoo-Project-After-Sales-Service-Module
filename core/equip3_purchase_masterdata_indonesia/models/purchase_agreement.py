# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class ShPurchaseAgreement(models.Model):
    _inherit = 'purchase.agreement'

    legal_documents_ids = fields.One2many('purchase.agreement.legal.document', 'legal_document_id', string='Vendor Legal Document')

    @api.onchange('partner_ids')
    def set_legal_documents(self):
        for res in self:
            legal_documents_ids = []
            for vendor in res.partner_ids:
                vals = {
                    'partner_id': vendor.id.origin,
                    'nomor_induk_berusaha': vendor.file_siup,
                    'salinan_anggaran_dasar': vendor.salinan_anggaran_dasar,
                    'surat_persetujuan_dirjen_ahu': vendor.surat_persetujuan_dirjen_ahu,
                    'akta_perubahan_pengurus_terakhir': vendor.akta_perubahan_pengurus_terakhir,
                    'surat_keterangan_tidak_kena_pajak': vendor.surat_keterangan_tidak_kena_pajak,
                    'surat_pernyataan_dan_kuasa': vendor.surat_pernyataan_dan_kuasa,
                }
                legal_documents_ids.append((0, 0, vals))

            self.legal_documents_ids = None
            self.legal_documents_ids = legal_documents_ids

class ShPurchaseAgreementDocument(models.Model):
    _name = 'purchase.agreement.legal.document'
    _description = 'Purchase Agreement Legal Document'

    legal_document_id = fields.Many2one(comodel_name='purchase.agreement', string='Vendor Legal Document')
    partner_id = fields.Many2one('res.partner', 'Vendor')
    nomor_induk_berusaha = fields.Boolean("Nomor Induk Berusaha (NIB)")
    salinan_anggaran_dasar = fields.Boolean(string='Salinan Anggaran Dasar')
    surat_persetujuan_dirjen_ahu = fields.Boolean(string='Surat Persetujuan Dirjen AHU')
    akta_perubahan_pengurus_terakhir = fields.Boolean(string='Akta Perubahan Pengurus Terakhir')
    surat_keterangan_tidak_kena_pajak = fields.Boolean(string='Surat Keterangan Tidak Kena Pajak')
    surat_pernyataan_dan_kuasa = fields.Boolean(string='Surat Pernyataan dan Kuasa')

    def download_vendor_attachments(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        return {"type": "ir.actions.act_url",
                "url": base_url + "/download_attachments?res_id={}".format(self.partner_id.id),
                }