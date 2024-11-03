from odoo import models, fields, api, _
from datetime import date,datetime
from dateutil.relativedelta import relativedelta
import json

class CreateAgreementWizard(models.TransientModel):
    _inherit = 'create.agreement.wizard'

    template_id_domain = fields.Char(string='Template Domain', compute='_compute_template_id_domain')
    property_id = fields.Many2one('product.product', string='Property', default=lambda self: self._context.get('active_id'))
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer')
    property_book_for = fields.Selection(related='property_id.property_book_for')
    recurring_type = fields.Selection(related='template_id.recurring_invoice_id.recurring_type')
    property_price = fields.Float(string='Price')
    daily_price = fields.Float(string='Daily Price')
    monthly_price = fields.Float(string='Monthly Price')
    yearly_price = fields.Float(string='Yearly Price')
    recurring_invoice_id = fields.Many2one(comodel_name='agreement.recurring.invoice', string='Recurring Invoice')
    start_date = fields.Date(string='Start Date', default=fields.Date.today())
    discount = fields.Float(string='Allow Discount (%)')
    total_price = fields.Float(string='Total Price')
    agent_id = fields.Many2one(comodel_name='res.users', string='Agent')

    @api.onchange('property_id')
    def domain_agent_id(self):
        return {'domain':{'agent_id':f"[('id','in',{[x.user_id.id for x in self.property_id.user_commission_ids]})]"}}

    @api.onchange('template_id','discount')
    def _onchange_discount(self):
        property_id = self.env['product.product'].browse(self._context.get('active_id'))
        if property_id and property_id.property_book_for == 'rent':
            if self.template_id:
                if self.recurring_type == 'daily':
                    duration = self.template_id.duration_daily
                    if self.discount > 0:
                        self.daily_price = self.daily_price - (self.daily_price * self.discount / 100)
                        self.total_price = self.daily_price * duration
                    else:
                        self.daily_price = self.property_id.daily_rent
                        self.total_price = self.property_id.daily_rent * duration
                elif self.recurring_type == 'monthly':
                    duration = self.template_id.duration_monthly
                    if self.discount > 0:
                        self.monthly_price = self.monthly_price - (self.monthly_price * self.discount / 100)
                        self.total_price = self.monthly_price * duration
                    else:
                        self.monthly_price = self.property_id.deposite
                        self.total_price = self.property_id.deposite * duration
                elif self.recurring_type == 'yearly':
                    duration = self.template_id.duration_yearly
                    if self.discount > 0:
                        self.yearly_price = self.yearly_price - (self.yearly_price * self.discount / 100)
                        self.total_price = self.yearly_price * duration
                    else:
                        self.yearly_price = self.property_id.rent_price
                        self.total_price = self.property_id.rent_price * duration



    @api.depends('property_id')
    def _compute_template_id_domain(self):
        if self.property_id:
            if self.property_id.property_book_for == 'rent':
                self.template_id_domain = json.dumps([('is_template','=', True), ('invoice_type', '=', 'recurring'), ('agreement_type_id.name', '=', 'Contract')])
            else:
                self.template_id_domain = json.dumps([('is_template','=', True), ('invoice_type', '=', 'non_recurring'), ('agreement_type_id.name', '=', 'Agreement')])
        else:
            self.template_id_domain = json.dumps([('is_template','=', True)])
        return True

    def default_get(self, fields):
        res = super(CreateAgreementWizard, self).default_get(fields)
        if self._context.get('active_model') == 'product.product':
            property_id = self.env['product.product'].browse(self._context.get('active_id'))
            res.update({
                'partner_id': self.env.user.partner_id.id,
                })
        return res

    @api.onchange('template_id', 'recurring_type')
    def onchange_template_id(self):
        property_id = self.env['product.product'].browse(self._context.get('active_id'))
        if self.property_book_for == 'rent':
            self.recurring_invoice_id = self.template_id.recurring_invoice_id
            if self.recurring_type == 'daily':
                self.daily_price = property_id.daily_rent
            elif self.recurring_type == 'monthly':
                self.monthly_price = property_id.deposite
            elif self.recurring_type == 'yearly':
                self.yearly_price = property_id.rent_price
        else:
            self.property_price = property_id.property_price

    def create_agreement(self):
        res = super(CreateAgreementWizard, self).create_agreement()
        if self._context.get('active_model') == 'product.product':
            if self.property_book_for == 'rent':
                agreement = self.env[res["res_model"]].browse(res["res_id"])
                if self.recurring_type == 'daily':
                    freq = relativedelta(days=self.template_id.duration_daily)
                    unit_price = self.daily_price
                elif self.recurring_type == 'monthly':
                    freq = relativedelta(months=self.template_id.duration_monthly)
                    unit_price = self.monthly_price
                elif self.recurring_type == 'yearly':
                    freq = relativedelta(years=self.template_id.duration_yearly)
                    unit_price = self.yearly_price
                else:
                    unit_price = 0
                
                agreement.write({
                        'property_id': self.property_id.id,
                        'property_book_for': self.property_book_for,
                        'payment_type': self.recurring_type,
                        'assigned_user_id': self.agent_id,
                        'partner_id': self.partner_id.id,
                        'expected_revenue': self.total_price,
                        'start_date': self.start_date,
                        'end_date': self.start_date + freq,
                        'line_ids': [(0, 0, {
                                        "product_id": self.property_id.id,
                                        "uom_id": self.property_id.uom_id.id,
                                        "name": self.property_id.name,
                                        "qty": 1,
                                        "taxes_id": False,
                                        "unit_price": unit_price,
                                    })],
                        'stage_id': self.env['agreement.stage'].search([('name', '=', 'Active')]).id,
                        })
            else:
                agreement = self.env[res["res_model"]].browse(res["res_id"])
                agreement.write({
                        'property_id': self.property_id.id,
                        'property_book_for': self.property_book_for,
                        'partner_id': self.partner_id.id,
                        'expected_revenue': self.property_price,
                        'line_ids': [(0, 0, {
                                        "product_id": self.property_id.id,
                                        "uom_id": self.property_id.uom_id.id,
                                        "name": self.property_id.name,
                                        "qty": 1,
                                        "taxes_id": False if self.property_id.property_book_for == 'rent' else [(6, 0, self.property_id.taxes_id.ids)],
                                        "unit_price": self.total_price if self.property_id.property_book_for == 'rent' else self.property_price,
                                    })],
                        })
        return res

