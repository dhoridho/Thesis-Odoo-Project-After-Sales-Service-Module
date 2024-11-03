# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import uuid


class PatientLabTest(models.Model):
    _name = "patient.laboratory.test"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin', 'portal.mixin', 'acs.documnt.mixin', 'acs.qrcode.mixin']
    _description = "Patient Laboratory Test"
    _order = 'date_analysis desc, id desc'

    @api.model
    def _get_disclaimer(self):
        return self.env.user.sudo().company_id.acs_laboratory_disclaimer or ''

    STATES = {'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    name = fields.Char(string='Test ID', help="Lab result ID", readonly="1",copy=False, index=True, tracking=True)
    test_id = fields.Many2one('acs.lab.test', string='Test', required=True, ondelete='restrict', states=STATES, tracking=True)
    patient_id = fields.Many2one('hms.patient', string='Patient', required=True, ondelete='restrict', states=STATES, tracking=True)
    user_id = fields.Many2one('res.users',string='Lab User', default=lambda self: self.env.user, states=STATES)
    physician_id = fields.Many2one('hms.physician',string='Prescribing Doctor', help="Doctor who requested the test", ondelete='restrict', states=STATES)
    diagnosis = fields.Text(string='Diagnosis', states=STATES)
    critearea_ids = fields.One2many('lab.test.critearea', 'patient_lab_id', string='Test Cases', copy=True, states=STATES)
    date_requested = fields.Datetime(string='Request Date', states=STATES)
    date_analysis = fields.Date(string='Test Date', default=fields.Date.context_today, states=STATES)
    request_id = fields.Many2one('acs.laboratory.request', string='Lab Request', ondelete='restrict', states=STATES)
    laboratory_id = fields.Many2one('acs.laboratory', related="request_id.laboratory_id", string='Laboratory', readonly=True, store=True)
    report = fields.Text(string='Test Report', states=STATES)
    note = fields.Text(string='Extra Info', states=STATES)
    sample_ids = fields.Many2many('acs.patient.laboratory.sample', 'test_lab_sample_rel', 'test_id', 'sample_id', string='Test Samples', states=STATES)
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Company',default=lambda self: self.env.user.company_id.id, states=STATES)
    state = fields.Selection([
        ('draft','Draft'),
        ('done','Done'),
        ('cancel','Cancel'),
    ], string='State',readonly=True, default='draft', tracking=True)
    consumable_line_ids = fields.One2many('hms.consumable.line', 'patient_lab_test_id',
        string='Consumable Line', states=STATES)
    disclaimer = fields.Text("Dislaimer", states=STATES, default=_get_disclaimer)
    collection_center_id = fields.Many2one('acs.laboratory', string='Collection Center', related="request_id.collection_center_id", states=STATES)

    #Just to make object selectable in selction field this is required: Waiting Screen
    acs_show_in_wc = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique (name,company_id)', 'Test Name must be unique per company !')
    ]

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('patient.laboratory.test')
        res = super(PatientLabTest, self).create(vals)
        res.unique_code = uuid.uuid4()
        return res

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise UserError(_("Lab Test can be delete only in Draft state."))
        return super(PatientLabTest, self).unlink()

    @api.onchange('request_id')
    def onchange_request_id(self):
        if self.request_id and self.request_id.date:
            self.date_requested = self.request_id.date

    @api.onchange('test_id')
    def on_change_test(self):
        test_lines = []
        if self.test_id:
            gender = self.patient_id.gender
            for line in self.test_id.critearea_ids:
                test_lines.append((0,0,{
                    'sequence': line.sequence,
                    'name': line.name,
                    'normal_range': line.normal_range_female if gender=='female' else line.normal_range_male,
                    'lab_uom_id': line.lab_uom_id and line.lab_uom_id.id or False,
                    'remark': line.remark,
                    'display_type': line.display_type,
                }))
            self.critearea_ids = test_lines

    def action_done(self):
        self.consume_lab_material()
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def consume_lab_material(self):
        for rec in self:
            if not rec.company_id.laboratory_usage_location:
                raise UserError(_('Please define a location where the consumables will be used during the Laboratory test in company.'))
            if not rec.company_id.laboratory_stock_location:
                raise UserError(_('Please define a Laboratory location from where the consumables will be taken.'))
 
            dest_location_id  = rec.company_id.laboratory_usage_location.id
            source_location_id  = rec.company_id.laboratory_stock_location.id
            for line in rec.consumable_line_ids.filtered(lambda s: not s.move_id):
                move = self.consume_material(source_location_id, dest_location_id,
                    {
                        'product': line.product_id,
                        'qty': line.qty,
                    })
                move.lab_test_id = rec.id
                line.move_id = move.id

    def _compute_access_url(self):
        super(PatientLabTest, self)._compute_access_url()
        for rec in self:
            rec.access_url = '/my/lab_results/%s' % (rec.id)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: