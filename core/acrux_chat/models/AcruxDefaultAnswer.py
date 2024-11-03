# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AcruxChatDefaultAnswer(models.Model):
    _inherit = 'acrux.chat.base.message'
    _name = 'acrux.chat.default.answer'
    _description = 'Chat Default Answer'
    _order = 'sequence'

    name = fields.Char('Name', required=True)
    sequence = fields.Integer('Sequence')
    file_attach = fields.Binary("Attachment", compute='_compute_attach', inverse='_inverse_attach',
                                store=True, attachment=False)
    file_attach_name = fields.Char('File Name')

    @api.constrains('file_attach', 'ttype')
    def _constrain_status(self):
        for rec in self:
            if rec.ttype not in ['text', 'location', 'info'] and not rec.file_attach:
                raise ValidationError(_('File is required.'))

    @api.onchange('ttype')
    def onchanges(self):
        if self.ttype in ['text', 'location', 'info']:
            self.file_attach = False
            self.res_model = False
            self.res_id = False
        else:
            self.text = False

    def _compute_attach(self):
        pass

    def _inverse_attach(self):
        Att = self.env['ir.attachment'].sudo()
        for rec in self:
            if rec.res_id and not rec.file_attach_name:
                Att.search([('res_model', '=', self._name), ('id', '=', rec.res_id)]).unlink()
            if rec.file_attach:
                # Att.search([('res_model', '=', self._name), ('res_id', '=', rec.id)]).unlink()
                attac_id = Att.create({'name': rec.file_attach_name,
                                       'type': 'binary',
                                       'datas': rec.file_attach,
                                       'store_fname': rec.file_attach_name,
                                       'res_model': self._name,
                                       'res_id': rec.id})
                rec.write({'res_model': 'ir.attachment',
                           'res_id': attac_id.id})
            else:
                rec.write({'res_model': False,
                           'res_id': False})
