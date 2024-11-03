# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
import re
from odoo.exceptions import AccessError, UserError, ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    
    id_number = fields.Char("ID Number",size=16)
    civil = fields.Selection([
        ('pns', 'PNS'),
        ('non_pns', 'Non PNS'),
        ('tni', 'TNI'),
        ('polri', 'Polri'),
        ('bumn', 'BUMN'),
        ('bumd', 'BUMD'),
        ('lainnya', 'Lainnya'),
    ], 'Civil Employee Status')
    employee_number = fields.Text("Employee Number")
    file_name = fields.Char('File Name', help='File name')
    file_siup = fields.Binary("Nomor Induk Berusaha (NIB)")
    npwp = fields.Char("NPWP")

    salinan_anggaran_dasar = fields.Binary(string='Salinan Anggaran Dasar', help="Akta Pendirian/Akta Penyesuaian beserta  seluruh Akta Perubahan Anggaran Dasar")
    surat_persetujuan_dirjen_ahu = fields.Binary(string='Surat Persetujuan Dirjen AHU')
    akta_perubahan_pengurus_terakhir = fields.Binary(string='Akta Perubahan Pengurus Terakhir')
    sppkp = fields.Binary(string='Surat Pengukuhan Pengusaha Kena Pajak (SPPKP)')
    surat_keterangan_tidak_kena_pajak = fields.Binary(string='Surat Keterangan Tidak Kena Pajak')
    surat_pernyataan_dan_kuasa = fields.Binary(string='Surat Pernyataan dan Kuasa', help="Apabila Nama Pemilik Rekening dan/atau yang menandatangani berbeda")

    @api.onchange('id_number')
    def check_id_number(self):
        for res in self:
            if res.id_number:
                if bool(re.match('^[0-9]+$', str(res.id_number))):
                    if len(str(res.id_number)) != 16:
                        raise ValidationError("ID Number for vendor must be 16 digits")
                else:
                    raise ValidationError("ID Number for vendor must be a number")

    # OVERRIDE
    def find_partner_similiar_indo(self, name, phone='', mobile='', id_number='', vat='', my_id=False):
        where_params = ''
        id_params = ''
        query = """
SELECT id, name
FROM res_partner
WHERE (lower(name) = lower('{}'){}){}
        """
        if phone:
            where_params += " or phone = '{}'".format(phone)
        if mobile:
            where_params += " or mobile = '{}'".format(mobile)
        if id_number:
            where_params += " or id_number = '{}'".format(id_number)
        if vat:
            where_params += " or vat = '{}'".format(vat)
        if my_id:
            id_params += " and id != {}".format(my_id)
        self.env.cr.execute(query.format(name, where_params, id_params))
        query_result = self.env.cr.dictfetchall()
        return query_result

    @api.depends('name','phone','mobile','id_number','vat')
    def _compute_is_similiar_indo(self):
        for i in self:
            is_similiar = False
            similiar_partner_count = 0
            get_partners = self.find_partner_similiar_indo(i.name,i.phone,i.mobile,i.id_number,i.vat,my_id=i.id)
            if len(get_partners) > 0:
                is_similiar = True
                similiar_partner_count = len(get_partners)
            i.is_similiar = is_similiar
            i.similiar_partner_count = similiar_partner_count

    # OVERRIDE
    def action_open_similiar_partner_indo(self):
        get_partners = self.find_partner_similiar_indo(self.name,self.phone,self.mobile,self.id_number,self.vat,my_id=self.id,)
        partner_ids = []
        for partner in get_partners:
            partner_ids.append(partner['id'])
        action = {
            'name': _('Similar Vendor'),
            'view_mode': 'tree,form',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', partner_ids)],
        }
        return action

    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
        for child in res.child_ids:
            child.check_id_number()
        return res

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        for child in self.child_ids:
            child.check_id_number()
        return res



