# -*- coding: utf-8 -*-
import time
import urllib
from urllib.request import urlopen
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AcsSms(models.Model):
    _name = 'acs.sms'
    _description = 'SMS'
    _rec_name = 'msg'

    def _get_url(self):
        for rec in self:
            prms = {
                rec.company_id.user_name_param: rec.company_id.user_name,
                rec.company_id.password_param: rec.company_id.password,
                rec.company_id.sender_param: rec.company_id.sender_id,
                rec.company_id.receiver_param: rec.mobile,
                rec.company_id.message_param: rec.msg
            }
            params = urllib.parse.urlencode(prms)
            rec.name = rec.company_id.url + "?" + params + (rec.company_id.extra_param or '')

    READONLY_STATES = {'sent': [('readonly', True)], 'error': [('readonly', True)]}

    #ACS: Odoo14 It can be model and res_id no need of partner (can check more possibility)
    partner_id = fields.Many2one('res.partner', 'Partner', states=READONLY_STATES)
    name = fields.Text(string='SMS Request URl', compute="_get_url", states=READONLY_STATES)
    msg =  fields.Text(string='SMS Text',required=True, states=READONLY_STATES)
    mobile =  fields.Char(string='Destination Number', required=True, states=READONLY_STATES)
    state =  fields.Selection([
        ('draft', 'Queued'),
        ('sent', 'Sent'),
        ('error', 'Error'),
    ], string='Message Status', default='draft')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id.id, states=READONLY_STATES)
    error_msg = fields.Char("Error Message/MSG ID", states=READONLY_STATES)
    template_id = fields.Many2one("acs.sms.template", "Template", states=READONLY_STATES)

    @api.onchange('template_id')
    def onchange_template(self):
        if self.template_id:
            self.msg = self.template_id.message

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft'):
                raise UserError(_('You cannot delete an record which is not draft.'))
        return super(AcsSms, self).unlink()

    def send_sms(self):
        for rec in self:
            try:
                rep = urlopen(rec.name)
                rec.state = 'sent'
                rec.error_msg = rep.read()
            except Exception as e:
                rec.state = 'error'
                rec.error_msg = Exception

    def action_draft(self):
        self.state = 'draft'

    @api.model
    def _check_queue(self):
        records = self.search([('state', '=', 'draft')], limit=100)
        records.send_sms()
 

class ACSSmsMixin(models.AbstractModel):
    _name = "acs.sms.mixin"
    _description = "SMS Mixin"

    @api.model
    def create_sms(self, msg, mobile, partner=False):
        company_id = self._context.get('force_company')
        if not company_id:
            company_id = self.env.user.sudo().company_id.id
        record = self.env['acs.sms'].create({
            'msg': msg,
            'partner_id': partner and partner.id or False,
            'mobile': mobile,
            'company_id': company_id,
        })
        if self.env.context.get('force_send'):
            record.send_sms()
        return record


class SMSTemplate(models.Model):
    _name = 'acs.sms.template'
    _description = 'SMS Template'

    name = fields.Text(string='Name', required=True)
    message = fields.Text(string='Message', required=True)
    partner_ids = fields.Many2many("res.partner", "partner_sms_template_rel", "partner_id", "sms_template_id", "Partners")
    employee_ids = fields.Many2many("hr.employee", "employee_sms_template_rel", "employee_id", "sms_template_id", "Employees")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: