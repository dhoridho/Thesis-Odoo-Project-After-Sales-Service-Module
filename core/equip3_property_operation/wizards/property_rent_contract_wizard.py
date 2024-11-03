# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date,datetime
from dateutil.relativedelta import relativedelta
import json

class PropertyBook(models.TransientModel):
    _name = 'property.rent.contract'
    _description = "Reserve Rental Property"
    
    contract_id = fields.Many2one('agreement',string="Contract Template", required=True, domain="[('is_template','=',True), ('invoice_type','=','recurring'), ('agreement_type_id.name','=','Contract')]")
    property_id = fields.Many2one('product.product', required=True, domain=[('is_property','=',True)])
    recurring_invoice_id = fields.Many2one('agreement.recurring.invoice', string="Recurring Invoice")
    recurring_type = fields.Selection(string='Recurring Type', related='recurring_invoice_id.recurring_type')
    name = fields.Text(string="Contract Title", required=True)
    agent_id = fields.Many2one(comodel_name='res.users', string='Agent')
    renter_id = fields.Many2one('res.users','Renter')
    deposite = fields.Float(string="Monthly Rent", required=True)
    deposite_daily = fields.Float(string='Daily Rent')
    deposite_yearly = fields.Float(string='Yearly Rent')
    start_date = fields.Date(string='Start Date', default=fields.Date.today())
    state = fields.Selection([('avl','Available'),('reserve','Reserve')], string="Status", default='avl')
    discount = fields.Float(string='Allow Discount (%)')
    total_price = fields.Float(string='Total Price', compute='_compute_discount')

    @api.onchange('property_id')
    def domain_agent_id(self):
        return {'domain':{'agent_id':f"[('id','in',{[x.user_id.id for x in self.property_id.user_commission_ids]})]"}}

    @api.depends('contract_id','discount')
    def _compute_discount(self):
        self.total_price = 0
        if self.contract_id:
            if self.recurring_type == 'daily':
                duration = self.contract_id.duration_daily
                if self.discount > 0:
                    self.deposite_daily = self.deposite_daily - (self.deposite_daily * self.discount / 100)
                    self.total_price = self.deposite_daily * duration
                else:
                    self.deposite_daily = self.property_id.daily_rent
                    self.total_price = self.property_id.daily_rent * duration

            elif self.recurring_type == 'monthly':
                duration = self.contract_id.duration_monthly
                if self.discount > 0:
                    self.deposite = self.property_id.deposite - (self.deposite * self.discount / 100)
                    self.total_price = self.deposite * duration
                else:
                    self.deposite = self.property_id.deposite
                    self.total_price = self.property_id.deposite * duration

            elif self.recurring_type == 'yearly':
                duration = self.contract_id.duration_yearly
                if self.discount > 0:
                    self.deposite_yearly = self.property_id.rent_price - (self.deposite_yearly * self.discount / 100)
                    self.total_price = self.deposite_yearly * duration
                else:
                    self.deposite_yearly = self.property_id.rent_price
                    self.total_price = self.property_id.rent_price * duration


    
    # get rent Property details.
    @api.model
    def default_get(self,default_fields):
        res = super(PropertyBook, self).default_get(default_fields)
        ctx = self._context
        property_data = {
            'property_id':ctx.get('property_id'),
            'renter_id':ctx.get('renter_id'),
            'deposite':ctx.get('deposite'),
            'deposite_daily':ctx.get('deposite_daily'),
            'deposite_yearly':ctx.get('deposite_yearly'),
        }
        res.update(property_data)
        return res

    def create_rent_contract(self):
        self.ensure_one()
        res = self.contract_id.create_new_agreement()
        agreement = self.env[res["res_model"]].browse(res["res_id"])
        if self.recurring_invoice_id.recurring_type == 'daily':
            freq = relativedelta(days=self.contract_id.duration_daily)
            unit_price = self.deposite_daily
        elif self.recurring_invoice_id.recurring_type == 'monthly':
            freq = relativedelta(months=self.contract_id.duration_monthly)
            unit_price = self.deposite
        elif self.recurring_invoice_id.recurring_type == 'yearly':
            freq = relativedelta(years=self.contract_id.duration_yearly)
            unit_price = self.deposite_yearly

        agr = agreement.write(
            {
                "name": self.name,
                "assigned_user_id": self.agent_id.id,
                "description": self.name,
                'payment_type': self.recurring_type,
                "template_id": self.contract_id.id,
                "expected_revenue": self.total_price,
                "partner_id": self.renter_id.partner_id.id,
                "property_id": self.property_id.id,
                "start_date": self.start_date,
                "end_date": self.start_date + freq,
                "property_book_for": "rent",
                "stage_id": self.env['agreement.stage'].search([('name','=','Active')], limit=1).id,
                "line_ids": [(0, 0, {
                    "product_id": self.property_id.id,
                    "uom_id": self.property_id.uom_id.id,
                    "name": self.property_id.name,
                    "qty": 1,
                    "taxes_id": False if self.property_id.property_book_for == 'rent' else [(6, 0, self.property_id.taxes_id.ids)],
                    "unit_price": unit_price

                })],
            }
        )
        if agr:
            self.env['product.product'].browse(self.property_id.id).write({'state':'reserve', 'is_reserved':True, 'user_id':self.renter_id.id})
        return res

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        if self.contract_id:
            self.recurring_invoice_id = self.contract_id.recurring_invoice_id.id