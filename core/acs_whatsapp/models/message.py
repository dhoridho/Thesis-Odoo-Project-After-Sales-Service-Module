# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.tools.mimetypes import guess_mimetype
import mimetypes


class AcsWhatsAppMessage(models.Model):
    _name = 'acs.whatsapp.message'
    _description = 'whatsapp'
    _order = 'id desc'

    READONLY_STATES = {'sent': [('readonly', True)], 'error': [('readonly', True)]}

    @api.depends('file_name','message','message_type')
    def _get_name(self):
        for rec in self:
            if rec.message and rec.message_type=='message':
                if len(rec.message)>100:
                    rec.name = rec.message[:100]
                else:
                    rec.name = rec.message or 'Message'
            elif rec.message_type in ['file','file_url']:
                name = "File"
            elif rec.message_type=='link':
                name = "Link"
            else:
                name = rec.file_name or 'Message'

    name = fields.Char(string="Name", compute="_get_name", store=True)
    partner_id = fields.Many2one('res.partner', 'Contact', states=READONLY_STATES)
    file =  fields.Binary(string='File', states=READONLY_STATES)
    file_name =  fields.Char(string='File Name')
    file_url =  fields.Char(string='File URL')
    message =  fields.Text(string='WhatsApp Text', states=READONLY_STATES)
    mobile =  fields.Char(string='Destination Number', required=True, states=READONLY_STATES)
    state =  fields.Selection([
        ('draft', 'Queued'),
        ('sent', 'Sent'),
        ('error', 'Error'),
    ], string='Message Status', index=True, default='draft', states=READONLY_STATES)
    message_type =  fields.Selection([
        ('message', 'Message'),
        ('file', 'File'),
        ('file_url', 'File URL'),
        ('link', 'Link'),
    ], string='Message Type', default='message', states=READONLY_STATES)
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id.id, states=READONLY_STATES)
    error_message = fields.Char("Error Message", states=READONLY_STATES)
    template_id = fields.Many2one("acs.whatsapp.template", string="Template", states=READONLY_STATES)
    whatsapp_announcement_id = fields.Many2one("acs.whatsapp.announcement", string="Announcement", states=READONLY_STATES)
    reply_data = fields.Text(copy=False, states=READONLY_STATES)
    mimetype = fields.Char('Mime Type', readonly=True, states=READONLY_STATES)
    link = fields.Char('Link', states=READONLY_STATES)
 
    def _check_contents(self, values):
        mimetype = None
        if values.get('mimetype'):
            mimetype = values['mimetype']
        if not mimetype and values.get('file_name'):
            mimetype = mimetypes.guess_type(values['file_name'])[0]
        if values.get('file') and (not mimetype or mimetype == 'application/octet-stream'):
            mimetype = guess_mimetype(values['file'].decode('base64'))
        if not mimetype:
            mimetype = 'application/octet-stream'

        values['mimetype'] = mimetype
        xml_like = 'ht' in mimetype or 'xml' in mimetype # hta, html, xhtml, etc.
        force_text = (xml_like and (not self.env.user._is_admin() or
            self.env.context.get('attachments_mime_plainxml')))
        if force_text:
            values['mimetype'] = 'text/plain'
        return values

    @api.model
    def create(self, values):
        values = self._check_contents(values)
        return super(AcsWhatsAppMessage, self).create(values)

    def write(self, vals):
        if 'mimetype' in vals or 'file' in vals:
            vals = self._check_contents(vals)
        return super(AcsWhatsAppMessage, self).write(vals)

    @api.onchange('template_id')
    def onchange_template(self):
        if self.template_id:
            self.message_type = self.template_id.message_type
            self.message = self.template_id.message
            self.file_name = self.template_id.file_name
            self.file_url = self.template_id.file_url
            self.link = self.template_id.link
            #To save memory avoid replication of data file can be avoided.
            self.file = self.template_id.file

    def send_whatsapp_message(self):
        """Hook method to add logic in relatd module"""
        pass

    def action_draft(self):
        self.state = 'draft'

    @api.model
    def complete_queue(self):
        records = self.search([('state', '=', 'draft')], limit=100)
        records.send_whatsapp_message()

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id and self.partner_id.mobile:
            self.mobile = self.partner_id.mobile


class ACSwhatsappMixin(models.AbstractModel):
    _name = "acs.whatsapp.mixin"
    _description = "WhatsApp Mixin"

    @api.model
    def send_whatsapp(self, message, mobile, partner=False, template=False):
        company_id = self._context.get('force_company')
        if not company_id:
            company_id = self.env.user.sudo().company_id.id
        record = self.env['acs.whatsapp.message'].create({
            'message': message,
            'partner_id': partner and partner.id or False,
            'mobile': mobile,
            'message_type': 'message',
            'company_id': company_id,
            'template_id': template and template.id or False,
        })
        if self.env.context.get('force_send'):
            record.send_whatsapp_message()
        return record

    @api.model
    def send_whatsapp_file_url(self, file_url, mobile, partner=False, template=False):
        company_id = self._context.get('force_company')
        if not company_id:
            company_id = self.env.user.sudo().company_id.id
        record = self.env['acs.whatsapp.message'].create({
            'file_url': file_url,
            'partner_id': partner and partner.id or False,
            'mobile': mobile,
            'message_type': 'file_url',
            'company_id': company_id,
            'template_id': template and template.id or False,
        })
        if self.env.context.get('force_send'):
            record.send_whatsapp_message()
        return record

    @api.model
    def send_whatsapp_file(self, filedata, file_name, mobile, partner=False, template=False):
        company_id = self._context.get('force_company')
        if not company_id:
            company_id = self.env.user.sudo().company_id.id
        record = self.env['acs.whatsapp.message'].create({
            'file': filedata,
            'file_name': file_name,
            'message_type': 'file',
            'partner_id': partner and partner.id or False,
            'mobile': mobile,
            'company_id': company_id,
            'template_id': template and template.id or False,
        })
        if self.env.context.get('force_send'):
            record.send_whatsapp_message()
        return record

    def acs_whatsapp_chat_history(self, partner, mobile):
        """Hook method to add logic in relatd module"""
        pass


class whatsappTemplate(models.Model):
    _name = 'acs.whatsapp.template'
    _description = 'whatsapp Template'

    name = fields.Text(string='Name', required=True)
    message_type =  fields.Selection([
        ('message', 'Message'),
        ('file', 'File'),
        ('file_url', 'File URL'),
        ('link', 'Link'),
    ], string='Message Type', default='message')
    message = fields.Text(string='Message')
    file =  fields.Binary(string='File')
    file_name =  fields.Char(string='File Name')
    file_url =  fields.Char(string='File URL')
    link = fields.Char('Link')
    partner_ids = fields.Many2many("res.partner", "partner_whatsapp_template_rel", "partner_id", "whatsapp_template_id", "Partners")
    employee_ids = fields.Many2many("hr.employee", "employee_whatsapp_template_rel", "employee_id", "whatsapp_template_id", "Employees")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: