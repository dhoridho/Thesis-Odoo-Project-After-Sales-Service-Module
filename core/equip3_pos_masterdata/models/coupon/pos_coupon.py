# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PosCoupon(models.Model):
    _name = 'pos.coupon'
    _description = 'POS Coupon'

    active = fields.Boolean('Active', default=True)
    name = fields.Char(string='Coupon Name', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    number = fields.Char('Number')
    code = fields.Char('Ean13')
    type_apply = fields.Selection([('Specific Product','Specific Product')], string='Type Apply', required=True)
    product_ids = fields.Many2many(
        'product.product',
        'pos_coupon_product_product_as_specific_product_rel',
        'pos_coupon_id',
        'product_id',
        domain=[('available_in_pos', '=', True)],
        string='Products',
    )

    minimum_purchase_quantity = fields.Integer('Minimum Purchase Quantity', default=1)
    sequence_generate_method = fields.Selection([
        ('Manual Input','Manual Input'),
        ('EAN13','EAN13'),
    ], string='Sequence Generate Method', required=True, help='If coupon sequence generate method = EAN13, then automatically generate')
    manual_input_sequence = fields.Char('Manual Input Sequence')

    start_date = fields.Datetime('Start Date')
    end_date = fields.Datetime('Expired Date')
    no_of_usage = fields.Integer('No of Usage', help='The number of each coupon usage, if 0 = unlimited') # IF 0 then it's unlimited used
    no_of_used = fields.Integer('No Of Used', compute='_compute_get_no_of_used')
    coupon_program_id = fields.Many2one('pos.coupon.program', string='Source Document')
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    state = fields.Selection([('active','Active'), ('expired','Expired')], string='Status', default='active')

    reward_type = fields.Selection([
        ('Discount','Discount'),
        ('Free Item','Free Item'),
    ], string='Reward Type', required=True,
    help='Discount = Reward will be provided as discount\nFree item = Reward will be provided as free product')
    reward_product_ids = fields.Many2many(
        'product.product',
        'pos_coupon_product_product_as_reward_product_rel',
        'pos_coupon_id',
        'product_id',
        domain=[('available_in_pos', '=', True)],
        string='Product Gift',
    )
    reward_quantity = fields.Integer('Reward Quantity')
    reward_discount_type = fields.Selection([('Fixed','Fixed'),('Percentage','Percentage')], string='Discount Type')
    reward_discount_amount = fields.Integer('Reward Discount Amount')
    reward_max_discount_amount = fields.Float('Reward Max. Discount Amount')

    use_history_ids = fields.One2many('pos.coupon.use.history', 'coupon_id', string='Histories Used', readonly=1)

    product_display_name = fields.Char('Product (Display Name)', compute='_compute_product_display_name')
    reward_product_display_name = fields.Char('Reward Product (Display Name)', compute='_compute_reward_product_display_name')

    def _compute_get_no_of_used(self):
        for rec in self:
            rec.no_of_used = len(rec.use_history_ids.ids)

    @api.model
    def create(self, vals):
        res = super(PosCoupon, self).create(vals)

        code = res.randomEan13() 
        new_vals = { 'code': code }
        if res.sequence_generate_method == 'EAN13':
            new_vals['number'] = code
        res.write(new_vals)
        
        return res

    def unlink(self):
        for rec in self:
            coupon_used = self.env['pos.order.line'].search_read([('pos_coupon_id','=',rec.id)], ['id'], limit=1)
            if coupon_used:
                raise UserError(_('You cannot delete a Coupon . Because Coupon have exsting in POS Order Lines'))
        return super(PosCoupon, self).unlink()

    def randomEan13(self):
        self.ensure_one()
        format_code = "%s%s%s" % ('999', self.id, datetime.now().strftime("%d%m%y%H%M"))
        return self.env['barcode.nomenclature'].sanitize_ean(format_code)

    def _compute_product_display_name(self):
        for rec in self:
            rec.product_display_name = ', '.join([p.name for p in rec.product_ids])

    def _compute_reward_product_display_name(self):
        for rec in self:
            rec.reward_product_display_name = ', '.join([p.name for p in rec.reward_product_ids])
    
    def get_data(self):
        return self.env[self._name].with_context(active_test=False).search_read([('id', '=', self.id)], ['name', 'no_of_usage', 'no_of_used', 'state', 'active'])

class PosCouponProgramUseHistory(models.Model):
    _name = 'pos.coupon.use.history'
    _description = 'Pos Coupon Program Use History'

    coupon_id = fields.Many2one('pos.coupon', required=1, string='Coupon', ondelete='cascade')
    pos_order_id = fields.Many2one('pos.order', string='Order')
    cashier_id = fields.Many2one('res.users', 'Cashier Added')
    used_date = fields.Datetime('Used Date', required=1)
    payment_id = fields.Many2one('pos.payment', string='Payment')
    value = fields.Float('Value Redeem', required=0)