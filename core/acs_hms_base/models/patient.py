# -*- coding: utf-8 -*-

from odoo import api, fields, models ,_
from odoo.exceptions import UserError
from datetime import datetime
from odoo.osv import expression


class ACSPatient(models.Model):
    _name = 'hms.patient'
    _description = 'Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin', 'acs.documnt.mixin']
    _inherits = {
        'res.partner': 'partner_id',
    }

    def _rec_count(self):
        Invoice = self.env['account.move']
        for rec in self:
            rec.invoice_count = Invoice.sudo().search_count([('partner_id','=',rec.partner_id.id)])

    def _acs_get_attachemnts(self):
        AttachmentObj = self.env['ir.attachment']
        attachments = AttachmentObj.search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id)])
        return attachments

    def _acs_attachemnt_count(self):
        AttachmentObj = self.env['ir.attachment']
        for rec in self:
            attachments = rec._acs_get_attachemnts()
            rec.attach_count = len(attachments)
            rec.attachment_ids = [(6,0,attachments.ids)]

    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', auto_join=True,
        string='Related Partner', help='Partner-related data of the Patient')
    gov_code = fields.Char(string='Government Identity', copy=False, tracking=True)
    marital_status = fields.Selection([
        ('single', 'Single'), 
        ('married', 'Married')], string='Marital Status', default="single")
    is_corpo_tieup = fields.Boolean(string='Corporate Tie-Up', 
        help="If not checked, these Corporate Tie-Up Group will not be visible at all.")
    corpo_company_id = fields.Many2one('res.partner', string='Corporate Company', 
        domain="[('is_company', '=', True),('customer_rank', '>', 0)]", ondelete='restrict')
    emp_code = fields.Char(string='Employee Code')
    user_id = fields.Many2one('res.users', string='Related User', ondelete='cascade', 
        help='User-related data of the patient')
    primary_doctor = fields.Many2one('hms.physician', 'Primary Care Doctor')

    invoice_count = fields.Integer(compute='_rec_count', string='# Invoices')
    occupation = fields.Char("Occupation")
    religion = fields.Char("Religion")
    caste = fields.Char("Tribe")

    @api.model
    def create(self, values):
        if values.get('code','/')=='/':
            values['code'] = self.env['ir.sequence'].next_by_code('hms.patient') or ''
        values['customer_rank'] = True
        return super(ACSPatient, self).create(values)

    def view_invoices(self):
        invoices = self.env['account.move'].search([('partner_id','=',self.partner_id.id)])
        action = self.acs_action_view_invoice(invoices)
        action['context'].update({
            'default_partner_id': self.partner_id.id,
            'default_patient_id': self.id,
        })
        return action

    @api.model
    def send_birthday_email(self): 
        wish_template_id = self.env.ref('acs_hms_base.email_template_birthday_wish', raise_if_not_found=False)
        user_cmp_template = self.env.user.company_id.birthday_mail_template_id
        today = datetime.now()
        today_month_day = '%-' + today.strftime('%m') + '-' + today.strftime('%d')
        patient_ids = self.search([('birthday', 'like', today_month_day)])
        for patient_id in patient_ids:
            if patient_id.email:
                wish_temp = patient_id.company_id.birthday_mail_template_id or user_cmp_template or wish_template_id
                wish_temp.sudo().send_mail(patient_id.id, force_send=True)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: