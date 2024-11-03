# -*- encoding: utf-8 -*-
from odoo import models, fields, api,_
from datetime import date, datetime, timedelta as td
from odoo.exceptions import UserError

class AcsCreateWAMsg(models.TransientModel):
    _name = "acs.send.whatsapp"
    _description = "Send WhatsApp Message"

    partner_id = fields.Many2one ('res.partner','Contact', required=True)
    mobile =  fields.Char(string='Destination Number', required=True)
    message_type =  fields.Selection([
        ('message', 'Message'),
        ('file', 'File'),
        ('file_url', 'File URL'),
        ('link', 'Link'),
    ], string='Message Type', default='message')
    link = fields.Char('Link')
    file =  fields.Binary(string='File')
    file_name =  fields.Char(string='File Name')
    file_url =  fields.Char(string='File URL')
    message =  fields.Text(string='WhatsApp Text')

    @api.model
    def default_get(self,fields):
        context = self._context or {}
        res = super(AcsCreateWAMsg, self).default_get(fields)
        if context.get('active_model')=='res.partner':
            partner = self.env['res.partner'].browse(context.get('active_ids', []))
            res.update({
                'partner_id': partner.id,
                'mobile': partner.mobile,
            })
        return res

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id and self.partner_id.mobile:
            self.mobile = self.partner_id.mobile

    def send_message(self):
        record = self.env['acs.whatsapp.message'].create({
            'file_url': self.file_url,
            'partner_id': self.partner_id.id,
            'mobile': self.mobile,
            'message_type': self.message_type,
            'file': self.file,
            'file_name': self.file_name,
            'message': self.message,
            'link': self.link,
        })
        record.with_context(force_send=True).send_whatsapp_message()
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
