
from odoo import api , fields , models, _
import ast

class CouponRule(models.Model):
    _inherit = 'coupon.program'
    
    is_vendor_promotion = fields.Boolean(string="Vendor Promotions")
    rule_purchase_product_domain = fields.Char(string="Based on Products", default=[['purchase_ok', '=', True]], help="On Purchase of selected product, reward will be given")
    rule_vendors_domain = fields.Char(string="Based on Vendors", default=[['is_vendor', '=', True]], help="Coupon program will work for selected customers only")
    vendors_selection = fields.Selection([('all_vendors', "All Vendors"), ('selected_vendors', "Selected vendors")], default="all_vendors", string="Based On Vendors")
    purchase_order_count = fields.Integer(string="Purchases", compute="_compute_purcahse_order_count")
    promo_code_usage = fields.Selection(default="no_code_needed")

    # renamed fields (to differentiate with equip3_sale_promo_coupon)
    purchase_products_selection = fields.Selection([('all_products', "All Products"), ('product_category', "Product Category"), ('selected_products', "Selected Products")], default="all_products", string="Based On Products")
    purchase_product_category_ids = fields.Many2many('product.category', 'product_category_coupon_program_purchase_rel', string="Product Category")
    purchase_selected_customers_ids = fields.Many2many('res.partner', 'res_partner_coupon_program_purchase_rel', string="Selected Vendors")
    purchase_selected_products_ids = fields.Many2many('product.product', 'product_product_coupon_program_purchase_rel', string="Selected Products")

    def _compute_purcahse_order_count(self):
        product_data = self.env['purchase.order.line'].read_group([('product_id', 'in', self.mapped('discount_line_product_id').ids)], ['product_id'], ['product_id'])
        mapped_data = dict([(m['product_id'][0], m['product_id_count']) for m in product_data])
        for program in self:
            program.purchase_order_count = mapped_data.get(program.discount_line_product_id.id, 0)
    
    def action_view_purchase_orders(self):
        self.ensure_one()
        orders = self.env['purchase.order.line'].search([('product_id', '=', self.discount_line_product_id.id)]).mapped('order_id')
        return {
            'name': _('Purchases Orders'),
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', orders.ids)],
        }

    @api.model
    def _filter_on_mimimum_amount_purchase(self, order):
        no_effect_lines = order._get_no_effect_on_threshold_lines()
        order_amount = {
            'amount_untaxed' : order.amount_untaxed - sum(line.price_subtotal for line in no_effect_lines),
            'amount_tax' : order.amount_tax - sum(line.price_tax for line in no_effect_lines)
        }
        program_ids = list()
        for program in self:
            if program.reward_type != 'discount':
                lines = self.env['purchase.order.line']
            else:
                lines = order.order_line.filtered(lambda line:
                    line.product_id == program.discount_line_product_id or
                    line.product_id == program.reward_id.discount_line_product_id or
                    (program.program_type == 'promotion_program' and line.is_reward_line)
                )
            untaxed_amount = order_amount['amount_untaxed'] - sum(line.price_subtotal for line in lines)
            tax_amount = order_amount['amount_tax'] - sum(line.price_tax for line in lines)
            program_amount = program._compute_program_amount('rule_minimum_amount', order.currency_id)
            if program.rule_minimum_amount_tax_inclusion == 'tax_included' and program_amount <= (untaxed_amount + tax_amount) or program_amount <= untaxed_amount:
                program_ids.append(program.id)
        return self.browse(program_ids)

    def _check_purchase_promo_code(self, order, coupon_code):
        message = {}
        if self.maximum_use_number != 0 and self.purchase_order_count >= self.maximum_use_number:
            message = {'error': _('Promo code %s has been expired.') % (coupon_code)}
        elif not self._filter_on_mimimum_amount_purchase(order):
            message = {'error': _(
                'A minimum of %(amount)s %(currency)s should be purchased to get the reward',
                amount=self.rule_minimum_amount,
                currency=self.currency_id.name
            )}
        elif self.promo_code and self.promo_code == order.promo_code:
            message = {'error': _('The promo code is already applied on this order')}
        elif not self.promo_code and self in order.no_code_promo_program_ids:
            message = {'error': _('The promotional offer is already applied on this order')}
        elif not self.active:
            message = {'error': _('Promo code is invalid')}
        elif self.rule_date_from and self.rule_date_from > order.date_order or self.rule_date_to and order.date_order > self.rule_date_to:
            message = {'error': _('Promo code is expired')}
        elif order.promo_code and self.promo_code_usage == 'code_needed':
            message = {'error': _('Promotionals codes are not cumulative.')}
        elif self._is_global_discount_program() and order._is_global_discount_already_applied():
            message = {'error': _('Global discounts are not cumulative.')}
        elif self.promo_applicability == 'on_current_order' and self.reward_type == 'product' and not order._is_reward_in_order_lines(self):
            message = {'error': _('The reward products should be in the purchase order lines to apply the discount.')}
        elif not self._is_valid_partner_purchase(order.partner_id):
            message = {'error': _("The customer doesn't have access to this reward.")}
        elif not self._filter_programs_on_products_purchase(order):
            message = {'error': _("You don't have the required product quantities on your purchase order. If the reward is same product quantity, please make sure that all the products are recorded on the sales order (Example: You need to have 3 T-shirts on your sales order if the promotion is 'Buy 2, Get 1 Free'.")}
        elif self.promo_applicability == 'on_current_order' and not self.env.context.get('applicable_coupon'):
            applicable_programs = order._get_applicable_programs()
            if self not in applicable_programs:
                message = {'error': _('At least one of the required conditions is not met to get the reward!')}
        return message
    
    
    def _filter_unexpired_programs_purchase(self, order):
        return self.filtered(lambda program: program.maximum_use_number == 0 or program.purchase_order_count <= program.maximum_use_number)
    
    def _is_valid_partner_purchase(self, partner):
        if self.rule_vendors_domain and self.rule_vendors_domain != '[]':
            domain = ast.literal_eval(self.rule_vendors_domain) + [('id', '=', partner.id)]
            return bool(self.env['res.partner'].search_count(domain))
        else:
            return True
    
    def _filter_programs_on_partners_purchase(self, order):
        return self.filtered(lambda program: program._is_valid_partner_purchase(order.partner_id))
    
    def _get_valid_products_purchase(self, products):
        if self.rule_purchase_product_domain:
            domain = ast.literal_eval(self.rule_purchase_product_domain)
            return products.filtered_domain(domain)
        return products
    
    def _filter_programs_on_products_purchase(self, order):
        order_lines = order.order_line.filtered(lambda line: line.product_id) - order._get_reward_lines()
        products = order_lines.mapped('product_id')
        products_qties = dict.fromkeys(products, 0)
        for line in order_lines:
            products_qties[line.product_id] += line.product_qty
        valid_program_ids = list()
        for program in self:
            if not program.rule_purchase_product_domain:
                valid_program_ids.append(program.id)
                continue
            valid_products = program._get_valid_products_purchase(products)
            if not valid_products:
                continue
            ordered_rule_products_qty = sum(products_qties[product] for product in valid_products)
            if program.promo_applicability == 'on_current_order' and \
               program.reward_type == 'product' and program._get_valid_products_purchase(program.reward_product_id):
                ordered_rule_products_qty -= program.reward_product_quantity
            if ordered_rule_products_qty >= program.rule_min_quantity:
                valid_program_ids.append(program.id)
        return self.browse(valid_program_ids)
    
    @api.model
    def _filter_programs_from_common_rules_purchase(self, order, next_order=False):
        programs = self
        if not next_order:
            programs = programs and programs._filter_on_mimimum_amount_purchase(order)
        if not self.env.context.get("no_outdated_coupons"):
            programs = programs and programs._filter_on_validity_dates(order)
        programs = programs and programs._filter_unexpired_programs_purchase(order)
        programs = programs and programs._filter_programs_on_partners_purchase(order)
        if not next_order:
            programs = programs and programs._filter_programs_on_products_purchase(order)
        programs_curr_order = programs.filtered(lambda p: p.promo_applicability == 'on_current_order')
        programs = programs.filtered(lambda p: p.promo_applicability == 'on_next_order')
        if programs_curr_order:
            programs += programs_curr_order._filter_not_ordered_reward_programs(order)
        return programs