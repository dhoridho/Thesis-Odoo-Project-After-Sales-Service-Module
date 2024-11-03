# -*- coding: utf-8 -*-

from odoo import _, api, models, fields
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta

class AcsHmsSubscription(models.Model):
    _name = 'acs.hms.subscription'
    _description = "HMS Subscription"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin']
    _order = 'id desc'

    STATES = {'active': [('readonly', True)], 'done': [('readonly', True)], 'cancel': [('readonly', True)]}

    @api.depends('res_model_id')
    def _data_count(self):
        Invoice = self.env['account.move']
        record_ids = 0
        for rec in self:
            if rec.res_model_id and rec.res_model_id.model:
                record_ids = self.env[rec.res_model_id.model].search_count([('subscription_id','=',rec.id)])
            rec.record_count = record_ids
            rec.remaining_service = rec.allowed_no_service - record_ids
            rec.invoice_count = Invoice.search_count([('subscription_id', '=', rec.id)])

    number = fields.Char(string='Number', required=True, readonly=True, default="/", tracking=True)
    name = fields.Char(string='Name', related="contract_id.name", readonly=True, default="/", tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('done', 'Closed'),
        ('cancel', 'Cancelled'),
    ], string='Status', copy=False, default='draft', states=STATES, tracking=True)

    note = fields.Text('Description', states=STATES)
    patient_id = fields.Many2one('hms.patient', string='Patient', states=STATES, ondelete="cascade", required=True)
    allowed_no_service = fields.Integer("Allowed No of Services", states=STATES)
    remaining_service = fields.Integer("Remaining No of Services", compute="_data_count")
    contract_id = fields.Many2one("acs.hms.contract", string="Contract", required=True, states=STATES)
    product_id = fields.Many2one("product.product", related="contract_id.product_id", string="Product",readonly=True)
    start_date = fields.Datetime("Start Date", states=STATES, default=fields.Datetime.now)
    end_date = fields.Datetime("End Date", required=True, states=STATES, default=fields.Datetime.now)
    invoice_count = fields.Integer(string='# of Invoices', compute='_data_count', readonly=True)
    invoice_ids = fields.One2many("account.move", "subscription_id", string='Invoices', copy=False)
    user_id = fields.Many2one('res.users', string='User', states=STATES, default=lambda self: self.env.user.id)

    res_model_id = fields.Many2one('ir.model', related="contract_id.res_model_id", string='Model', readonly=True)
    record_count = fields.Integer(string='# of Operations', compute='_data_count', readonly=True)
    company_id = fields.Many2one('res.company', ondelete='restrict', states=STATES, 
        string='Company',default=lambda self: self.env.user.company_id.id)
    acs_type = fields.Selection([
        ('full', 'Full In Advance'),
        ('discount', 'Price-list Based Discount'),
    ], string='Offer Type', copy=False, default='full', states=STATES, tracking=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', check_company=True, 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.model
    def create(self, values):
        values['number'] = self.env['ir.sequence'].next_by_code('acs.hms.subscription') or '/'
        return super(AcsHmsSubscription, self).create(values)

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an record which is not draft or canceled.'))
        return super(AcsHmsSubscription, self).unlink()

    def name_get(self):
        res = []
        for record in self:
            name = " [%(number)s] %(name)s (%(count)s)" % {
                'name': record.name,
                'number': record.number,
                'count': _('%g remaining out of %g') % (record.remaining_service or 0.0, record.allowed_no_service or 0.0)
            }
            res.append((record.id, name))
        return res

    def action_confirm(self):
        self.state = 'active'

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    @api.onchange("contract_id")
    def onchange_contract_id(self):
        if self.contract_id:
            self.allowed_no_service = self.contract_id.no_service
            self.acs_type = self.contract_id.acs_type
            self.pricelist_id = self.contract_id.pricelist_id and self.contract_id.pricelist_id.id or False

    def action_view_related_records(self):
        record_ids = self.env[self.res_model_id.model].search([('subscription_id','=',self.id)])
        return {
            'name':'Records',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': self.res_model_id.model,
            'target': 'current',
            'type': 'ir.actions.act_window',
            'domain': [('id','in', record_ids.ids)],
            'nodestroy': True,
        }

    def action_invoice_create(self):
        product_id = self.product_id
        if not product_id:
            raise UserError(_("Please Set proper contract first."))
        product_data = [{
            'product_id': product_id,
            'name': product_id.name + '\n' + 'Subscription No: ' + self.number,
            'price_unit': self.contract_id.price,
        }]
        inv_data = {}
        invoice = self.acs_create_invoice(partner=self.patient_id.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        invoice.subscription_id = self.id

    def action_view_invoice(self):
        invoices = self.invoice_ids
        action = self.acs_action_view_invoice(invoices)
        return action

    #This is lazy option to close subscriptions
    @api.model
    def close_subscriptions(self):
        subscriptions = self.search([('state','=','active'),('end_date','<=',fields.Datetime.now())])
        for subscription in subscriptions:
            subscription.action_done()

        subscriptions = self.search([('state','=','active'),('end_date','>=',fields.Datetime.now())])
        for subscription in subscriptions:
            if subscription.remaining_service <= 0:
                subscription.action_done()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: