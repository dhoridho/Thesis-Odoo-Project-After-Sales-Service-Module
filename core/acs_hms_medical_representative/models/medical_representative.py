# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError

class MedicalRepresentative(models.Model):
    _name = 'medical.representative'
    _description = "Medical Representative"
    _inherits = {
        'res.partner': 'partner_id',
    }
    _inherit = ['mail.thread']

    partner_id = fields.Many2one('res.partner', 'Partner', required=True, ondelete='restrict')

    @api.model
    def create(self, values):
        if values.get('code', '/') == '/':
            values['code'] = self.env['ir.sequence'].next_by_code('medical.representative') or ''
        return super(MedicalRepresentative, self).create(values)

    def action_mr_visit(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_medical_representative.action_medical_representative_visit")
        action['domain'] = [('medical_representative_id', '=', self.id)]
        action['context'] = {'default_medical_representative_id': self.id}
        return action


class MedicalVisit(models.Model):
    _name = 'acs.mr.visit'
    _description = 'Medical Visit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(size=256, string='Name', tracking=True)
    activity_name = fields.Char('Purpose', required="True")
    date_visit = fields.Datetime('Date', default=fields.Datetime.now)
    medical_representative_id = fields.Many2one('medical.representative','MR', help="Name of the Mr")
    physician_id = fields.Many2one('hms.physician','Doctor', help="Name of the Doctor")
    state = fields.Selection([
        ('draft','Draft'),
        ('approved','Approved'),
        ('cancelled','Cancelled'),
        ('done','Done')], 'Status', default="draft") 
    remark = fields.Text('Dr Remark')
    product_description = fields.Text('Product Description')

    @api.model
    def create(self, values):
        if values.get('name', '') == '':
            values['name'] = self.env['ir.sequence'].next_by_code('acs.mr.visit') or ''
        return super(MedicalVisit, self).create(values)

    def action_approve(self):
        self.date_visit = datetime.now()
        self.state = 'approved'

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def unlink(self):
        for data in self:
            if data.state in ['done']:
                raise UserError(('You can only delete in draft'))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

