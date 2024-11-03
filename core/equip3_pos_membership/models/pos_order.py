# -*- coding: utf-8 -*-

import json
import math
import copy

from datetime import datetime
from odoo import api, fields, models, tools, _, registry

class PosOrder(models.Model):
    _inherit = 'pos.order'

    customer_deposit_id = fields.Many2one('customer.deposit', 'Customer Deposit')
    customer_deposit_amount = fields.Float(compute='_compute_customer_deposit_amount', string='Customer Deposit Amount')
    point_ids = fields.One2many('pos.loyalty.point', 'order_id', 'Points')
    plus_point = fields.Float('Plus Point', readonly=1)
    redeem_point = fields.Float('Redeem Point', readonly=1)

    build_plus_point_rules = fields.Text('Build Plus Point Rules', 
        help='Store Loyalty Rules for Build Plus Point')
    

    @api.model
    def create(self, vals):
        order = super(PosOrder, self).create(vals)
        if order.plus_point or order.redeem_point:
            order.pos_compute_loyalty_point() 

        return_order = order.return_order_id
        if return_order and (return_order.plus_point or return_order.redeem_point) and not order.void_order_id: 
            order.pos_compute_loyalty_point_return_order() 

        void_order = order.void_order_id
        if void_order and (void_order.plus_point or void_order.redeem_point) and order.void_state == 'Void':
            order.pos_compute_loyalty_point_void_order()
        return order


    @api.model
    def _process_order(self, order, draft, existing_order):
        order_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        if order_id:
            pos_order = self.browse(order_id)
            if pos_order.customer_deposit_id:
                pos_order.update_member_deposit()
        return order_id

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder,self)._order_fields(ui_order)
        res.update({
            'plus_point': ui_order.get('plus_point', 0) or 0,
            'redeem_point': ui_order.get('redeem_point', 0) or 0,
            'customer_deposit_id': ui_order.get('customer_deposit_id', False) or False,
        })
        if ui_order.get('build_plus_point_rules'):
            res['build_plus_point_rules'] = json.dumps(ui_order['build_plus_point_rules'])

        return res

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        res = super(PosOrder,self)._payment_fields(order, ui_paymentline)
        res.update({
            'customer_deposit_id': ui_paymentline.get('customer_deposit_id') or False,
        })
        return res

    def _compute_customer_deposit_amount(self):
        for rec in self:
            amounts = rec.payment_ids.filtered(lambda x: x.customer_deposit_id).mapped('amount')
            rec.customer_deposit_amount = sum(amounts)

    def update_member_deposit(self):
        self.ensure_one()
        if self.customer_deposit_id:
            order_amounts = self.payment_ids.filtered(lambda x: x.customer_deposit_id).mapped('amount')
            self.customer_deposit_id.remaining_amount -= sum(order_amounts)

    def get_pos_rounding(self, ttype, multiplier, value):
        self.ensure_one()
        if ttype == 'Down':
            value = math.floor(value)
            if multiplier:
               value = math.floor(value / float(multiplier)) * float(multiplier)

        if ttype == 'Up':
            value = math.ceil(value)
            if multiplier:
               value = math.ceil(value / float(multiplier)) * float(multiplier)

        if ttype == 'Half Up':
            value = round(value)
            if multiplier:
               value = round(value / float(multiplier)) * float(multiplier)
        return value

    def get_plus_point_rounding(self, value):
        self.ensure_one()
        company = self.company_id
        if company.membership_pluspoint_rounding:
            if company.membership_pluspoint_rounding_type and company.membership_pluspoint_rounding_multiplier:
                value = self.get_pos_rounding(
                    company.membership_pluspoint_rounding_type,
                    company.membership_pluspoint_rounding_multiplier,
                    value)
        return value

    def get_order_amount_without_loyalty(self):
        self.ensure_one()
        amount = 0;
        for line in self.lines:
            if not line.is_product_redeemed:
                amount += line.price_subtotal_incl
        return amount;

    def _prepare_value_for_pluspoint_product_category(self, rules):
        self.ensure_one()
        order = self
        lines = self.lines
        order_amount = self.get_order_amount_without_loyalty()
        rules = rules.filtered(lambda r: order_amount >= r.min_amount)
        values = []

        for line in lines:
            total_point = 0
            total_point_no_rounding = 0
            for rule in rules:
                plus_point = line.price_subtotal_incl * rule['coefficient']
                is_type_products = rule.type == 'products' and (line.product_id.id in rule.product_ids.ids)
                is_type_categories = rule.type == 'categories' and (line.product_id.pos_categ_id and line.product_id.pos_categ_id.id in rule.category_ids.ids or False)
                if is_type_products or is_type_categories:
                    point = self.get_plus_point_rounding(plus_point)
                    point_no_rounding = plus_point
                    total_point += point
                    total_point_no_rounding += point_no_rounding
                    values += [{
                        'loyalty_rule_id': rule.id,
                        'loyalty_id': rule.loyalty_id.id,
                        'order_id': order.id,
                        'partner_id': order.partner_id.id,
                        'is_return': order.is_return if order.is_return else False, 
                        'state': 'ready',
                        'type': 'plus',
                        'point': point,
                        'point_no_rounding': point_no_rounding,
                    }]

            line.write({
                'plus_point': total_point,
                'plus_point_no_rounding': total_point_no_rounding,
            })

        return values

    def _prepare_value_for_pluspoint_total_amount(self, rules):
        self.ensure_one()
        order = self
        lines = self.lines
        order_amount = self.get_order_amount_without_loyalty()
        rules = rules.filtered(lambda r: order_amount >= r.min_amount)
        values = []

        vals_point = {
            'loyalty_rule_id': False,
            'loyalty_id': False,
            'order_id': order.id,
            'partner_id': order.partner_id.id,
            'state': 'ready',
            'is_return': order.is_return if order.is_return else False, 
            'point': 0,
            'type': 'plus',
        }

        rules_A = rules.filtered(lambda r: r.calc_point_without_point_as_payment == False);
        if rules_A:
            for rule in rules_A:
                plus_point = order_amount * rule.coefficient;
                value = copy.deepcopy(vals_point)
                value.update({
                    'point': self.get_plus_point_rounding(plus_point),
                    'point_no_rounding': plus_point,
                    'loyalty_id': rule.loyalty_id.id,
                    'loyalty_rule_id': rule.id,
                })
                values += [value]

        rules_B = rules.filtered(lambda r: r.calc_point_without_point_as_payment == True);
        if rules_B:
            redeem_point = order.redeem_point
            for rule in rules_B:
                plus_point = order_amount * rule.coefficient;
                if redeem_point:
                    plus_point = (order_amount - redeem_point) * rule.coefficient;

                value = copy.deepcopy(vals_point)
                value.update({
                    'point': self.get_plus_point_rounding(plus_point),
                    'point_no_rounding': plus_point,
                    'loyalty_id': rule.loyalty_id.id,
                    'loyalty_rule_id': rule.id,
                })
                values += [value]

        plus_point = sum([x['point'] for x in values if x['type'] == 'plus'])
        plus_point_no_rounding = sum([x['point_no_rounding'] for x in values if x['type'] == 'plus'])
        if plus_point:
            for line in self.lines:
                if line.is_product_redeemed:
                    continue
                portion = (line.price_subtotal_incl / order_amount)
                line.write({
                    'plus_point': plus_point * portion,
                    'plus_point_no_rounding': plus_point_no_rounding * portion,
                })

        return values

    def _prepare_value_for_reedem_point(self):
        self.ensure_one()
        order = self
        lines = self.lines
        values = []
        for line in lines:
            if line.is_product_redeemed:
                value = {
                    'loyalty_id': line.reward_id.loyalty_id.id,
                    'order_id': order.id,
                    'partner_id': order.partner_id.id,
                    'state': 'ready',
                    'is_return': order.is_return if order.is_return else False, 
                    'point': line.redeem_point,
                    'type': 'redeem',
                    'loyalty_reward_id': line.reward_id.id,
                    'product_redeemed_ids': [(4, line.product_id.id)]
                }
                values += [value]
        return values

    def pos_compute_loyalty_point(self):
        self.ensure_one()
        values = []
        if self.partner_id and self.config_id.pos_loyalty_ids:
            if self.plus_point and self.build_plus_point_rules:
                loyalty_rules = self.env['pos.loyalty.rule'].search([('id', 'in', json.loads(self.build_plus_point_rules))])
                # Type: Selected Product, Selected Category
                rules = loyalty_rules.filtered(lambda r: r.type in ['products', 'categories'])
                if rules:
                    values += self._prepare_value_for_pluspoint_product_category(rules)
                # Type: Total Amount
                rules = loyalty_rules.filtered(lambda r: r.type in ['order_amount'])
                if rules:
                    values += self._prepare_value_for_pluspoint_total_amount(rules)

            if self.redeem_point:
                values += self._prepare_value_for_reedem_point()

        for value in values:
            self.env['pos.loyalty.point'].create(value)
        return True

    def pos_compute_loyalty_point_return_order(self):
        self.ensure_one()
        return_order = self
        origin_order = return_order.return_order_id
        values = []
        if not origin_order:
            return False
        if not origin_order.plus_point:
            return False

        loyalty_id = False
        for loyalty in origin_order.point_ids:
            loyalty_id = loyalty.loyalty_id
            break

        for line in return_order.lines:
            qty_return = abs(line.qty)
            origin_line = line.original_line_id
            if origin_line and origin_line.plus_point:
                # TODO: Return Plus Point
                point_unit = origin_line.plus_point / origin_line.qty
                point_no_rounding_unit = origin_line.plus_point_no_rounding / origin_line.qty
                point = point_unit * qty_return
                point_no_rounding = point_no_rounding_unit * qty_return
                values += [{
                    'description': 'Return Order',
                    'loyalty_rule_id': False, 
                    'loyalty_id': loyalty_id and loyalty_id.id or False, 
                    'order_id': return_order.id, 
                    'partner_id': origin_order.partner_id.id, 
                    'state': 'ready',
                    'type': 'return', 
                    'point': point, 
                    'point_no_rounding': point_no_rounding
                }]

        for value in values:
            self.env['pos.loyalty.point'].create(value)
        return True

    def pos_compute_loyalty_point_void_order(self):
        self.ensure_one()
        void_order = self
        origin_order = void_order.return_order_id
        values = []
        if not origin_order:
            return False
        if not origin_order.plus_point:
            return False

        for loyalty in origin_order.point_ids:
            # TODO: Void Plus Point
            if loyalty.type == 'plus':
                values += [{
                    'description': 'Void Order',
                    'loyalty_rule_id': loyalty.loyalty_rule_id.id, 
                    'loyalty_id': loyalty.loyalty_id.id, 
                    'order_id': void_order.id, 
                    'partner_id': loyalty.partner_id.id, 
                    'state': 'ready', 
                    'type': 'void', 
                    'point': loyalty.point,
                    'point_no_rounding': loyalty.point_no_rounding
                }]

        for value in values:
            self.env['pos.loyalty.point'].create(value)
        return True

    """ #POS VOID Online Mode#
    def pos_compute_loyalty_point_void_order(self):
        self.ensure_one()
        values = []
        void_order = self
        origin_order = void_order.void_order_id
        for loyalty in origin_order.point_ids:
            # TODO: Void Plus Point
            if loyalty.type == 'plus':
                values += [{
                    'description': 'Void Order',
                    'loyalty_rule_id': loyalty.loyalty_rule_id.id, 
                    'loyalty_id': loyalty.loyalty_id.id, 
                    'order_id': void_order.id, 
                    'partner_id': loyalty.partner_id.id, 
                    'state': 'ready', 
                    'type': 'void', 
                    'point': loyalty.point,
                    'point_no_rounding': loyalty.point_no_rounding
                }]

        for value in values:
            self.env['pos.loyalty.point'].create(value)
        return True

    def _prepare_void_order_vals(self, order, vals):
        values = super(PosOrder,self)._prepare_void_order_vals(order=order, vals=vals)

        values['plus_point'] = order.plus_point
        values['redeem_point'] = order.redeem_point
        values['customer_deposit_id'] = order.customer_deposit_id and order.customer_deposit_id.id or False

        return values

    def create_void_order(self, vals):
        res = super(PosOrder,self).create_void_order(vals)
        if res.get('void_order_id'):
            void_order = self.env['pos.order'].browse(res['void_order_id'])
            if void_order and (void_order.plus_point or void_order.redeem_point):
                void_order.pos_compute_loyalty_point_void_order()
        
        return res
    """

class POSOrderLine(models.Model):
    _inherit = "pos.order.line"

    reward_id = fields.Many2one('pos.loyalty.reward', 'Reward')
    is_product_redeemed = fields.Boolean('Is Product Redeemed?')
    plus_point = fields.Float('Plus Point', readonly=1)
    plus_point_no_rounding = fields.Float('Plus Point - No Rounding', readonly=1)
    redeem_point = fields.Float('Redeem Point', readonly=1)
    redeem_point_no_rounding = fields.Float('Redeem Point - No Rounding', readonly=1)
