# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp

class AcsCommissionRole(models.Model):
    _name = 'acs.commission.role'
    _description = 'Commission Role'

    name = fields.Char(string='Name', required=True)
    description = fields.Text("Description")
    commission_rule_ids = fields.One2many("acs.commission.rule", "role_id", string="Commission Rules")


class AcsCommissionRole(models.Model):
    _name = 'acs.commission.rule'
    _description = 'Commission Rule'
    _order = "sequence"

    sequence = fields.Integer(string='Sequence', default=50)
    rule_type = fields.Selection([
        ('role', 'Role'),
        ('user', 'User'),
    ], string='Rule Type', copy=False, default='role', required=True)
    role_id = fields.Many2one('acs.commission.role', string='Role')
    user_id = fields.Many2one('res.users', string='User')
    partner_id = fields.Many2one('res.partner', string='Partner')
    physician_id = fields.Many2one('res.partner', string='Physician')
    rule_on = fields.Selection([
        ('product_category', 'Product Category'),
        ('product', 'Product'),
    ], string='Rule On', copy=False, default='product_category', required=True)
    product_category_id = fields.Many2one('product.category', string='Product Category')
    product_id = fields.Many2one('product.template', string='Product')
    percentage = fields.Float('Commission Percentage')
    description = fields.Text("Description")


class HMSCommission(models.Model):
    _name = 'acs.hms.commission'
    _description = 'HMS Commission'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _payment_status(self):
        for rec in self:
            if not rec.payment_invoice_id:
                rec.payment_status = 'not_inv'
            elif rec.payment_invoice_id.state=='draft':
                rec.payment_status = 'draft'
            elif rec.payment_invoice_id.state=='cancel':
                rec.payment_status = 'cancel'
            elif rec.payment_invoice_id.payment_state=='paid':
                rec.payment_status = 'paid'
            else:
                rec.payment_status = 'open'

    STATES = {'done': [('readonly', True)], 'cancel': [('readonly', True)]}

    name = fields.Char(string='Name',readonly=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
    ], string='Status', copy=False, default='draft', tracking=True, states=STATES)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True, states=STATES, tracking=True)
    invoice_id = fields.Many2one('account.move', 'Invoice', states=STATES, copy=False)
    commission_on = fields.Float('Commission On', states=STATES)
    commission_amount = fields.Float('Commission Amount', states=STATES)
    invoice_line_id = fields.Many2one('account.move.line', 'Payment Invoice Line', states=STATES)
    payment_invoice_id = fields.Many2one('account.move', related="invoice_line_id.move_id", string='Payment Invoice', readonly=True)
    payment_status = fields.Selection([
        ('not_inv', 'Not Paid'),
        ('draft', 'Draft Payment'),
        ('open', 'Open'),
        ('paid', 'Paid'),
        ('cancel', 'Canceled'), 
    ], string='Payment Status', copy=False, default='not_inv', readonly=True, compute="_payment_status")    
    note = fields.Text("Note")
    commission_sheet_id = fields.Many2one('acs.commission.sheet', 'Sheet', states=STATES)
    company_id = fields.Many2one('res.company', related="invoice_id.company_id", 
        string='Hospital', store=True)

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an record which is not draft or cancelled.'))
        return super(HMSCommission, self).unlink()

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('acs.hms.commission')
        return super(HMSCommission, self).create(values)

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'
