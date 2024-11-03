# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError, RedirectWarning, Warning

class InsuranceClaim(models.Model):
    _name = 'hms.insurance.claim'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin']
    _description = 'Claim'

    @api.depends('amount_requested', 'amount_pass')
    def _get_diff(self):
        for claim in self:
            claim.amount_difference = claim.amount_requested - claim.amount_pass

    @api.model
    def _default_insu_checklist(self):
        vals = []
        checklists = self.env['hms.insurance.checklist.template'].search([('active', '=', True)])
        for checklist in checklists:
            vals.append((0, 0, {
                'name': checklist.name,
            }))
        return vals

    @api.depends('checklist_ids')
    def _compute_checklist_ids_marked(self):
        for rec in self:
            done_checklist = rec.checklist_ids.filtered(lambda x: x.is_done)
            if len(rec.checklist_ids)>=1:
                rec.checklist_marked = (len(done_checklist)* 100)/len(rec.checklist_ids)

    STATES={'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    name = fields.Char('Claim Number', required=True, default="/", states=STATES, tracking=True)
    patient_id = fields.Many2one('hms.patient', 'Patient', required=True, states=STATES, tracking=True)
    insurance_id = fields.Many2one('hms.patient.insurance', 'Insurance Policy', required=True, states=STATES, tracking=True)
    appointment_id = fields.Many2one('hms.appointment', 'Appointment', states=STATES)
    insurance_company_id = fields.Many2one('hms.insurance.company', related="insurance_id.insurance_company_id", string='Insurance Company', readonly=True, store=True)
    amount_requested = fields.Float('Total Claim Amount', states=STATES)
    amount_pass = fields.Float('Passed Amount', states=STATES)
    amount_received = fields.Float('Received Amount', states=STATES)
    amount_difference = fields.Float(compute='_get_diff', string='Difference Amount', states=STATES)
    date = fields.Datetime(string='Claim Date', default=fields.Datetime.now, states=STATES)
    date_received = fields.Date('Claim Received Date', states=STATES)
    tpa_id = fields.Many2one('insurance.tpa', 'TPA', states=STATES)
    req_document_ids = fields.Many2many('hms.insurance.req.doc', 'hms_insurance_req_doc_rel', 'claim_id', 'doc_id', 'Required Documents', states=STATES)
    question = fields.Text('Question', states=STATES)
    answer = fields.Text('Answer', states=STATES)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('sent', 'Sent For Approval'),
        ('approve', 'Approved'),
        ('received', 'Received'),
        ('cancel', 'Canceled'),
        ('done', 'Done')], 'State', default='draft', tracking=True)
    doc_ids = fields.One2many(comodel_name='ir.attachment', inverse_name='claim_id', string='Document', states=STATES)
    checklist_ids = fields.One2many('hms.insurance.checklist', 'claim_id', string='Checklist', default=lambda self: self._default_insu_checklist(), states=STATES)
    package_id = fields.Many2one('hospitalization.package', string='Package', states=STATES)
    checklist_marked = fields.Float('Checklist Progress', compute='_compute_checklist_ids_marked',store=True, states=STATES)
    claim_for = fields.Selection([
        ('appointment', 'Appointment'),
        ('other', 'Other')], string='Claim Type', default='appointment')
    invoice_ids = fields.One2many('account.move', 'claim_id', string='Invoices', states=STATES)
    payment_ids = fields.One2many('account.payment', 'claim_id', string='Payments', states=STATES)
    company_id = fields.Many2one('res.company', 'Hospital', default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one("res.currency", related='company_id.currency_id', string="Currency", readonly=True, required=True)
    total_invoice_amount = fields.Float(compute="_get_amounts", string="Total Invoices")
    total_payment_amount = fields.Float(compute="_get_amounts", string="Total Payments")

    def _get_amounts(self):
        for rec in self:
            rec.total_invoice_amount = sum(rec.invoice_ids.mapped('amount_total'))
            rec.total_payment_amount = sum(rec.payment_ids.mapped('amount'))

    def unlink(self):
        for data in self:
            if data.state in ['done']:
                raise UserError(('You can not delete record in done state'))
        return super(InsuranceClaim, self).unlink()

    @api.onchange('package_id')
    def onchange_package_id(self):
        if self.package_id:
            self.amount_requested = self.package_id.amount_total

    def action_draft(self):
        self.state = 'draft'

    def action_confirm(self):
        if self.name=='/':
            self.name = self.env['ir.sequence'].next_by_code('hms.insurance.claim') or 'New Claim'
        self.state = 'confirm'

    def action_sent(self):
        self.state = 'sent'

    def action_approve(self):
        self.state = 'approve'

    def action_received(self):
        self.state = 'received'

    def action_done(self):
        self.date_received = fields.Date.today()
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def action_view_invoice(self):
        invoices = self.env['account.move'].search([('claim_id', '=', self.id)])
        action = self.with_context(acs_open_blank_list=True).acs_action_view_invoice(invoices)
        partner_id = self.patient_id.partner_id.id
        if self.insurance_company_id and self.insurance_company_id.partner_id:
            partner_id = self.insurance_company_id.partner_id.id
        action['context'] = {
            'default_claim_id': self.id,
            'default_move_type': 'out_invoice',
            'default_patient_id': self.patient_id.id,
            'default_partner_id': partner_id}
        return action

    def get_relate_invoices(self):
        invoices = []
        if self.claim_for=='appointment':
            invoices = self.env['account.move'].search([('appointment_id', '=', self.appointment_id.id)])
        return invoices

    def action_view_record_invoice(self):
        invoices = self.get_relate_invoices()
        action = self.acs_action_view_invoice(invoices)
        partner_id = self.patient_id.partner_id.id
        if self.insurance_company_id and self.insurance_company_id.partner_id:
            partner_id = self.insurance_company_id.partner_id.id
        action['context'] = {
            'default_claim_id': self.id,
            'default_move_type': 'out_invoice',
            'default_patient_id': self.patient_id.id,
            'default_partner_id': partner_id}
        return action

    def action_payments(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_payments_payable")
        action['domain'] = [('claim_id','=',self.id)]
        partner_id = self.patient_id.partner_id.id
        if self.insurance_company_id and self.insurance_company_id.partner_id:
            partner_id = self.insurance_company_id.partner_id.id
        action['context'] = {
            'default_claim_id': self.id,
            'default_payment_type': 'inbound',
            'default_partner_id': partner_id}
        return action
