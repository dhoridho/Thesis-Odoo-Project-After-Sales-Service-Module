# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee','acs.whatsapp.mixin']


class WhatsappAnnouncement(models.Model):
    _name = 'acs.whatsapp.announcement'
    _inherit = ['acs.whatsapp.mixin']
    _description = 'whatsapp Announcement'
    _rec_name = 'message'

    READONLY_STATES = {'sent': [('readonly', True)]}

    name = fields.Char("Name", states=READONLY_STATES)
    message = fields.Text(string='Announcement', states=READONLY_STATES)
    message_type =  fields.Selection([
        ('message', 'Message'),
        ('file', 'File'),
        ('file_url', 'File URL'),
        ('link', 'Link'),
    ], string='Message Type', default='message', states=READONLY_STATES)
    file =  fields.Binary(string='File', states=READONLY_STATES)
    file_name =  fields.Char(string='File Name')
    file_url =  fields.Char(string='File URL')
    link = fields.Char('Link', states=READONLY_STATES)
    date = fields.Date(string='Date', states=READONLY_STATES)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'), 
    ], string='Status', copy=False, default='draft', states=READONLY_STATES)
    announcement_type = fields.Selection([
        ('contacts', 'Contacts'),
        ('employees', 'Employees'),
    ], string='Announcement Type', copy=False, default='contacts', states=READONLY_STATES, required=True)
    employee_selection_type = fields.Selection([
        ('all', 'All'),
        ('department', 'Department'),
        ('employees', 'Employees'),
    ], string='Type', copy=False, default='all', states=READONLY_STATES, required=True)
    employee_ids = fields.Many2many("hr.employee", "whatsapp_employee_announement_rel", "employee_id", "announcement_id", "Employees", states=READONLY_STATES)
    department_id = fields.Many2one("hr.department", "Department", states=READONLY_STATES)
    partner_ids = fields.Many2many("res.partner", "whatsapp_partner_announement_rel", "partner_id", "announcement_id", "Contacts", states=READONLY_STATES)
    template_id = fields.Many2one("acs.whatsapp.template", "Template", states=READONLY_STATES)
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id.id, states=READONLY_STATES)

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
            self.employee_ids = [(6, 0, self.template_id.employee_ids.ids + self.employee_ids.ids)]
            self.partner_ids = [(6, 0, self.template_id.partner_ids.ids + self.partner_ids.ids)]

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft'):
                raise UserError(_('You cannot delete an record which is not draft.'))
        return super(Announcement, self).unlink()

    def acs_create_message(self, mobile, partner=False):
        if self.message_type=='message':
            self.send_whatsapp(self.message, mobile, partner)
        elif self.message_type=='file_url':
            self.send_whatsapp_file_url(self.file_url, mobile, partner)
        elif self.message_type=='file':
            self.send_whatsapp_file(self.file, self.file_name, mobile, partner)

    def send_message(self):
        if self.announcement_type=='contacts':
            for partner in self.partner_ids:
                if partner.mobile:
                    self.acs_create_message(partner.mobile, partner)
        else:
            if self.employee_selection_type=='employees':
                employees = self.employee_ids
            elif self.employee_selection_type=='department':
                employees = self.env['hr.employee'].search([('department_id','=',self.department_id.id)])
            else:
                employees = self.env['hr.employee'].search([])
            for employee in employees:
                partner = employee.user_id and employee.user_id.partner_id
                mobile = partner.mobile or employee.mobile_phone
                if mobile:
                    self.acs_create_message(mobile)

        self.state = 'sent'
        self.date = fields.Datetime.now()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: