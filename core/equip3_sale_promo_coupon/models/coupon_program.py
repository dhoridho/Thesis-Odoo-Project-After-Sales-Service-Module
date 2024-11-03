
from odoo import api, fields, models, _

class CouponProgram(models.Model):
    _inherit = 'coupon.program'

    is_sale_promotion = fields.Boolean(string="Sales Promotions")

    customers_selection = fields.Selection(
        selection=[
            ('all_customers', "All Customers"), 
            ('customer_category', "Customer Category"), 
            ('selected_customers', "Selected Customers")
        ], 
        default="all_customers", 
        string="Based On Customers")

    products_selection = fields.Selection(
        selection=[
            ('all_products', "All Products"), 
            ('product_category', "Product Category"), 
            ('selected_products', "Selected Products")
        ], 
        default="all_products", 
        string="Based On Products")

    customer_category_ids = fields.Many2many('customer.category', string="Customer Category")
    product_category_ids = fields.Many2many('product.category', string="Product Category")
    selected_customers_ids = fields.Many2many('res.partner', string="Selected Customers")
    selected_products_ids = fields.Many2many('product.product', 'coupon_program_product_product_sale', string="Selected Products")
    single_promotion = fields.Boolean(string='Single Promotion', default=True)
    promotion_type = fields.Selection(
        selection=[
            ('single', "Single Promotion"),
            ('multi', "Multi Promotion"),
            ('multiple', "Multiple Promotion")
        ],
        default="single",
        string="Promotion Type")

    # TODO: delete this once modul upgraded
    @api.model
    def update_partner_product_domain(self):
        records = self.env['coupon.program'].sudo().search([])
        for record in records:
            record._onchange_customers_selection()
            record._onchange_products_selection()
            
    @api.onchange('customers_selection', 'customer_category_ids', 'selected_customers_ids')
    def _onchange_customers_selection(self):
        domain = '[["id", "in", []]]'
        if self.customers_selection == 'all_customers':
            domain = '[]'
        elif self.customers_selection == 'customer_category':
            domain = '[["customer_category", "in", %s]]' % self.customer_category_ids.ids
        elif self.customers_selection == 'selected_customers':
            domain = '[["id", "in", %s]]' % self.selected_customers_ids.ids
        self.rule_partners_domain = domain

    @api.onchange('products_selection', 'product_category_ids', 'selected_products_ids')
    def _onchange_products_selection(self):
        domain = '[["id", "in", []]]'
        if self.products_selection == 'all_products':
            domain = '[]'
        elif self.products_selection == 'product_category':
            domain = '[["categ_id", "in", %s]]' % self.product_category_ids.ids
        elif self.products_selection == 'selected_products':
            domain = '[["id", "in", %s]]' % self.selected_products_ids.ids
        self.rule_products_domain = domain

    @api.model
    def _filter_on_mimimum_amount_equip(self, order):
        program_ids = []
        for program in self:
            amount = order.amount_untaxed if program.rule_minimum_amount_tax_inclusion == 'tax_excluded' else order.amount_total
            if amount >= program.rule_minimum_amount:
                program_ids.append(program.id)
        return self.browse(program_ids)

    @api.model
    def _filter_on_validity_dates_equip(self, order):
        return self.filtered(lambda program:
            (not program.rule_date_from or program.rule_date_from <= order.date_order)
            and
            (not program.rule_date_to or program.rule_date_to >= order.date_order)
        )

    def _filter_unexpired_programs_equip(self, order):
        return self.filtered(lambda program: program.maximum_use_number == 0 or program.order_count <= program.maximum_use_number)

    def _filter_programs_on_partners_equip(self, order):
        return self.filtered(lambda program: program._is_valid_partner(order.partner_id))

    def _filter_programs_on_products_equip(self, order):
        program_ids = []
        for program in self:
            domain = eval(program.rule_products_domain)
            program_product_ids = self.env['product.product'].search(domain).ids
            rewarded_lines = order.order_line.filtered(lambda l: l.product_id.id in program_product_ids)
            if sum(rewarded_lines.mapped('product_uom_qty')) >= program.rule_min_quantity:
                program_ids.append(program.id)
        return self.browse(program_ids)

    def _filter_programs_on_same_reward_product(self, order):
        program_ids = []
        added_current_reward_product_ids = []
        added_next_reward_product_ids = []
        for program in self:
            if program.promo_applicability == 'on_current_order' and program.reward_product_id.id not in added_current_reward_product_ids:
                program_ids.append(program.id)
                # Jangan tambahkan ke list jika program.reward_product_id.id = False
                if program.reward_product_id.id:
                    added_current_reward_product_ids.append(program.reward_product_id.id)
            elif program.promo_applicability == 'on_next_order' and program.reward_product_id.id not in added_next_reward_product_ids:
                program_ids.append(program.id)
                # Jangan tambahkan ke list jika program.reward_product_id.id = False
                if program.reward_product_id.id:
                    added_next_reward_product_ids.append(program.reward_product_id.id)
        return self.browse(program_ids)

    @api.model
    def _filter_programs_from_common_rules_equip(self, order):
        programs = self
        programs = programs and programs._filter_on_mimimum_amount_equip(order)
        programs = programs and programs._filter_on_validity_dates_equip(order)
        programs = programs and programs._filter_unexpired_programs_equip(order)
        programs = programs and programs._filter_programs_on_partners_equip(order)
        programs = programs and programs._filter_programs_on_products_equip(order)
        programs = programs and programs._filter_programs_on_products_equip(order)
        programs = programs and programs._filter_programs_on_same_reward_product(order)
        return programs

    def action_view_sales_orders(self):
        action = super(CouponProgram, self).action_view_sales_orders()
        orders = self.env['sale.order.line'].search([('product_id', '=', self.discount_line_product_id.id)]).mapped('order_id')
        action['domain'] = [('id', 'in', orders.ids)]
        return action

    def _get_discount_product_values(self):
        res = super()._get_discount_product_values()
        res.update({
            'categ_id': self.env.ref('equip3_sale_promo_coupon.product_category_product_rewards').id,
        })
        return res

    @api.model
    def create(self, vals):
        vals['discount_line_product_id'] = self.env.ref('equip3_sale_promo_coupon.product_template_promotion_programs').product_variant_id.id
        program = super(CouponProgram, self).create(vals)
        if program.reward_type != 'product' and program.discount_line_product_id:
            program_reward_categ_id = self.env.ref('equip3_sale_promo_coupon.product_category_product_rewards').id
            if program_reward_categ_id != program.discount_line_product_id.categ_id.id:
                program.discount_line_product_id.write({
                    'categ_id': program_reward_categ_id,
                })
        return program
    
    def _check_promo_code(self, order, coupon_code):
        if coupon_code:
            message = {}
            if self.maximum_use_number != 0 and self.order_count >= self.maximum_use_number:
                message = {'error': _('Promo code %s has been expired.') % (coupon_code)}
            elif not self._filter_on_mimimum_amount(order):
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
            elif self.promo_applicability == 'on_current_order' and self.reward_type == 'product' and not order._is_reward_in_order_lines(self) and not coupon_code:
                message = {'error': _('The reward products should be in the sales order lines to apply the discount.')}
            elif not self._is_valid_partner(order.partner_id):
                message = {'error': _("The customer doesn't have access to this reward.")}
            elif not self._filter_programs_on_products(order) and not coupon_code:
                message = {'error': _("You don't have the required product quantities on your sales order. If the reward is same product quantity, please make sure that all the products are recorded on the sales order (Example: You need to have 3 T-shirts on your sales order if the promotion is 'Buy 2, Get 1 Free'.")}
            elif self.promo_applicability == 'on_current_order' and not self.env.context.get('applicable_coupon') and not coupon_code:
                applicable_programs = order._get_applicable_programs()
                if self not in applicable_programs:
                    message = {'error': _('At least one of the required conditions is not met to get the reward!')}
            return message
        else:
            return super(CouponProgram, self)._check_promo_code(order, coupon_code)
