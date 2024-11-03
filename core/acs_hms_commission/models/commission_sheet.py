# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp

class AcsCommissionSheet(models.Model):
    _name = 'acs.commission.sheet'
    _description = 'Commission Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _payment_status(self):
        for rec in self:
            if not rec.payment_invoice_id:
                rec.payment_status = 'not_inv'
            elif rec.payment_invoice_id.state=='draft':
                rec.payment_status = 'draft'
            elif rec.payment_invoice_id.state=='cancel':
                rec.payment_status = 'cancel'
            elif rec.payment_invoice_id.invoice_payment_state=='paid':
                rec.payment_status = 'paid'
            else:
                rec.payment_status = 'open'

    @api.depends('commission_line_ids','commission_line_ids.commission_amount')
    def _amount_all(self):
        for record in self:
            commission_amount = 0
            for line in record.commission_line_ids:
                commission_amount += line.commission_amount
            record.amount_total = commission_amount

    STATES = {'done': [('readonly', True)], 'cancel': [('readonly', True)]}

    name = fields.Char(string='Name', readonly=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed','Confirmed'),
        ('done', 'done'),
    ], string='Status', copy=False, default='draft', tracking=True, states=STATES)
    partner_id = fields.Many2one('res.partner', string='Partner', index=True, required=True, states=STATES, tracking=True)
    date_from = fields.Date(states=STATES, required=True, default=fields.Date.today)
    date_to = fields.Date(states=STATES, required=True, default=fields.Date.today)
    user_id = fields.Many2one('res.users', string='User', states=STATES, default=lambda self: self.env.user.id, required=True, tracking=True)
    commission_line_ids = fields.One2many('acs.hms.commission', 'commission_sheet_id', 
        string='Lines', states=STATES)
    payment_invoice_id = fields.Many2one('account.move', string='Payment Invoice', readonly=True)
    payment_status = fields.Selection([
        ('not_inv', 'Not Paid'),
        ('draft', 'Draft Payment'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('cancel', 'Canceled'), 
    ], string='Payment Status', copy=False, default='not_inv', readonly=True, compute="_payment_status")    
    note = fields.Text("Note")
    company_id = fields.Many2one('res.company', states=STATES,
        string='Hospital', default=lambda self: self.env.user.company_id.id)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id",
        string='Currency')
    amount_total = fields.Float(compute="_amount_all", string="Total")

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an record which is not draft or cancelled.'))
        return super(AcsCommissionSheet, self).unlink()

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('acs.commission.sheet')
        return super(AcsCommissionSheet, self).create(values)

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    def get_data(self):
        self.commission_line_ids.write({'commission_sheet_id': False})
        commission_lines = self.env['acs.hms.commission'].search([
            ('partner_id','=',self.partner_id.id),
            ('create_date','>=',self.date_from),
            ('create_date','<=',self.date_to),
            ('commission_sheet_id','=',False)])
        commission_lines.write({'commission_sheet_id': self.id})

    def create_payment_bill(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_commission.action_view_commission_invoice")
        action['context'] = {
            'active_model':'acs.hms.commission', 
            'active_ids': self.commission_line_ids.ids, 
            'commission_sheet_id': self.id,
            'default_hide_groupby_partner': True,
        }
        return action