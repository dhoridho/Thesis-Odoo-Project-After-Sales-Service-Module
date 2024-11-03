# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = "res.partner"

    faktur_pajak_gabungan = fields.Boolean(string='Faktur Pajak Gabungan')
    blok = fields.Char()
    kelurahan = fields.Char()
    kecamatan = fields.Char()
    rukun_tetangga = fields.Char(string="RT")
    rukun_warga = fields.Char(string="RW")
    street_number = fields.Char(string="Nomor")
    street_number2 = fields.Char(string="Nomor2")
    overpayment_processed_by = fields.Selection(selection=[
            ('pemotong', 'Pemotong'),
            ('pemindahbukuan', 'Pemindahbukuan'),
        ], string='LB Diproses Oleh')

    def check_vat(self, country_code):
        pass

    @api.constrains('l10n_id_pkp', 'faktur_pajak_gabungan')
    def _constrain_id_pkp_and_faktur_pajak_gabungan(self):
        for rec in self:
            if rec.l10n_id_pkp and rec.faktur_pajak_gabungan:
                raise ValidationError(_("please deactivate ID PKP or Faktur Pajak Gabungan"))

    @api.onchange('l10n_id_pkp')
    def _onchange_l10n_id_pkp(self):
        for rec in self:
            if rec.l10n_id_pkp:
                rec.faktur_pajak_gabungan = False
            else:
                rec.faktur_pajak_gabungan = True