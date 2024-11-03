# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_marketplace_selection = [
    ('tokopedia', 'Tokopedia'),
    ('shopee', 'Shopee'),
    ('blibli', 'Blibli'),
    ('lazada', 'Lazada'),
    ('shopify', 'Shopify'),
]


class MPPromotionProgram(models.Model):
    _name = 'mp.promotion.program'
    _description = 'Marketplace Coupon/Promotion Program'
    _inherit = ['mp.base']

    PROMOTION_STATES = [
        ("draft", "Draft"),
        ("wait", "Waiting"),
        ("run", "Running"),
        ("stop", "Stopped")
    ]

    READONLY_STATES = {
        'wait': [('readonly', True)],
        'run': [('readonly', True)],
        'done': [('readonly', True)],
    }

    name = fields.Char(string='Promotion Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    promotion_type = fields.Many2one(comodel_name='mp.promotion.program.type',
                                     string='Promotion Type', states=READONLY_STATES)
    code = fields.Char(related='promotion_type.code')
    company_id = fields.Many2one(related="mp_account_id.company_id")
    # active = fields.Boolean('Active', default=True)
    state = fields.Selection(selection=PROMOTION_STATES,
                             string='Promotion State', default='draft')
    date_start = fields.Datetime(string='Start Date', default=lambda self: self._get_start_date())
    date_end = fields.Datetime(string='End Date', default=lambda self: self._get_end_date())
    is_uploaded = fields.Boolean(default=False)
    product_discount_ids = fields.One2many(
        comodel_name='mp.promotion.program.line', inverse_name='promotion_id', string='Product Discount Line')

    @api.onchange('date_start', 'date_end')
    def validasi_form(self):
        # Validasi rentan waktu pada field 'date_start' dan 'date_end'
        if self.date_end < self.date_start:
            return {
                'warning': {
                    'title': 'Interval Warning',
                    'message': 'Date end must be higher from date start',
                }
            }

    @api.model
    def _get_start_date(self):
        start_date = fields.Datetime.from_string(fields.Datetime.now() + timedelta(minutes=30))
        return start_date

    @api.model
    def _get_end_date(self):
        end_date = fields.Datetime.from_string(fields.Datetime.now() + timedelta(days=1))
        return end_date

    def action_submit(self):
        for promotion in self:
            if hasattr(promotion, '%s_upload_promotion' % promotion.marketplace):
                getattr(promotion, '%s_upload_promotion' % promotion.marketplace)()

    def action_stop(self):
        for promotion in self:
            if hasattr(promotion, '%s_stop_promotion' % promotion.marketplace):
                getattr(promotion, '%s_stop_promotion' % promotion.marketplace)()

    def action_update(self):
        for promotion in self:
            if hasattr(promotion, '%s_update_promotion' % promotion.marketplace):
                getattr(promotion, '%s_update_promotion' % promotion.marketplace)()

    def action_sync(self):
        for promotion in self:
            if hasattr(promotion, '%s_sync_promotion' % promotion.marketplace):
                getattr(promotion, '%s_sync_promotion' % promotion.marketplace)()

    def action_delete(self):
        for promotion in self:
            if hasattr(promotion, '%s_delete_promotion' % promotion.marketplace):
                getattr(promotion, '%s_delete_promotion' % promotion.marketplace)()


class MPPromotionProgramType(models.Model):
    _name = 'mp.promotion.program.type'
    _description = 'Marketplace Coupon/Promotion Program Type'

    name = fields.Char('Name')
    code = fields.Char('Code')
    marketplace = fields.Selection(string="Marketplace", selection=_marketplace_selection, required=True)


class MPPromotionProduct(models.Model):
    _name = 'mp.promotion.program.line'
    _description = 'Marketplace Coupon/Promotion Lines'
    _inherit = ['mp.base']

    promotion_id = fields.Many2one(comodel_name='mp.promotion.program', string='Promotion', ondelete='cascade')
    mp_account_id = fields.Many2one(comodel_name='mp.account', related='promotion_id.mp_account_id', store=True)
    mp_product_id = fields.Many2one(comodel_name='mp.product', string='MP Product')
    mp_product_variant_count = fields.Integer(related='mp_product_id.mp_product_variant_count')
    mp_product_variant_id = fields.Many2one(comodel_name='mp.product.variant',
                                            string='MP Product Variant')
    item_original_price = fields.Float(string='Original Price', readonly=True,
                                       compute='_get_original_price', store=True,)
    purchase_limit = fields.Integer(string='Purchase Limit', default=0)
    price_mode = fields.Selection([("percentage", "Percentage Price"),
                                  ("fixed", "Fixed Price")], string='Price Mode', default='percentage')
    item_price = fields.Float(string='Discount Price')
    item_stock = fields.Integer(string='Discount Stock', default=1)
    final_item_price = fields.Float(string='Final Price', compute='_get_price_final', store=True,)
    mp_product_name = fields.Char(string='Item Name', index=True)

    @api.depends('mp_product_id', 'item_original_price', 'mp_product_variant_id')
    def _get_original_price(self):
        for rec in self:
            if not rec.mp_product_id:
                rec.item_original_price = 0
            else:
                if rec.mp_product_variant_id:
                    rec.item_original_price = rec.mp_product_variant_id.list_price
                else:
                    rec.item_original_price = rec.mp_product_id.list_price

    @api.depends('item_original_price', 'price_mode', 'item_price', 'final_item_price')
    def _get_price_final(self):
        for rec in self:
            if rec.item_original_price == 0:
                rec.final_item_price = 0
            else:
                if rec.price_mode == 'percentage':
                    rec.final_item_price = rec.item_original_price - (rec.item_original_price*rec.item_price/100)
                elif rec.price_mode == 'fixed':
                    rec.final_item_price = rec.item_price
