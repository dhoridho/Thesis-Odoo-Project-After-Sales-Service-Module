
from email.policy import default
from odoo.tools.misc import formatLang
from odoo import api , fields , models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_valid_coupon = fields.Boolean(string="Valid Coupon", default=False)
    applied_coupon_ids = fields.One2many('coupon.coupon', 'purchases_order_id', string="Applied Coupons", copy=False)
    generated_coupon_ids = fields.One2many('coupon.coupon', 'purchase_id', string="Offered Coupons", copy=False)
    no_code_promo_program_ids = fields.Many2many('coupon.program', string="Applied Immediate Promo Programs",
        domain="[('promo_code_usage', '=', 'no_code_needed'), '|', ('company_id', '=', False), ('company_id', '=', company_id), ('is_vendor_promotion', '=', True)]", copy=False)
    code_promo_program_id = fields.Many2one('coupon.program', string="Applied Promo Program",
        domain="[('promo_code_usage', '=', 'code_needed'), '|', ('company_id', '=', False), ('company_id', '=', company_id), ('is_vendor_promotion', '=', True)]", copy=False)
    promo_code = fields.Char(related='code_promo_program_id.promo_code', help="Applied program code", readonly=False)
    
    
    def _get_no_effect_on_threshold_lines(self):
        self.ensure_one()
        free_delivery_product = self.env['coupon.program'].search([('reward_type', '=', 'free_shipping'), ('is_vendor_promotion', '=', True)]).mapped('discount_line_product_id')
        lines = self.order_line.filtered(lambda line: line.product_id in free_delivery_product)
        return lines
    
    def _is_global_discount_already_applied(self):
        applied_programs = self.no_code_promo_program_ids + \
                           self.code_promo_program_id + \
                           self.applied_coupon_ids.mapped('program_id')
        return applied_programs.filtered(lambda program: program._is_global_discount_program())
    
    def _is_reward_in_order_lines(self, program):
        self.ensure_one()
        order_quantity = sum(self.order_line.filtered(lambda line:
            line.product_id == program.reward_product_id).mapped('product_uom_qty'))
        return order_quantity >= program.reward_product_quantity
    
    def _get_applicable_programs(self):
        self.ensure_one()
        programs = self.env['coupon.program'].with_context(
            no_outdated_coupons=True,
        ).search([
            ('company_id', 'in', [self.company_id.id, False]),
            ('is_vendor_promotion', '=', True),
            '|', ('rule_date_from', '=', False), ('rule_date_from', '<=', self.date_order),
            '|', ('rule_date_to', '=', False), ('rule_date_to', '>=', self.date_order),
        ], order="id")._filter_programs_from_common_rules_purchase(self)
        return programs
    
    def _get_base_order_lines(self, program):
        return self.order_line.filtered(lambda x: not (x.is_reward_line and x.product_id == program.discount_line_product_id))
    
    def _get_paid_order_lines(self):
        free_reward_product = self.env['coupon.program'].search([('reward_type', '=', 'product'), ('is_vendor_promotion', '=', True)]).mapped('discount_line_product_id')
        return self.order_line.filtered(lambda x: not x.is_reward_line or x.product_id in free_reward_product)

    def _get_reward_values_discount_fixed_amount(self, program):
        total_amount = sum(self._get_base_order_lines(program).mapped('price_total'))
        fixed_amount = program._compute_program_amount('discount_fixed_amount', self.currency_id)
        if total_amount < fixed_amount:
            return total_amount
        else:
            return fixed_amount
        
    def _get_reward_values_discount_percentage_per_line(self, program, line):
        discount_amount = line.product_qty * line.price_unit * (program.discount_percentage / 100)
        return discount_amount
    
    def _get_reward_values_discount(self, program):
        if program.discount_type == 'fixed_amount':
            taxes = program.discount_line_product_id.taxes_id
            if self.fiscal_position_id:
                taxes = self.fiscal_position_id.map_tax(taxes)
            return [{
                'name': _("Discount: %s", program.name),
                'product_id': program.discount_line_product_id.id,
                'price_unit': - self._get_reward_values_discount_fixed_amount(program),
                'product_uom_qty': 1.0,
                'product_uom': program.discount_line_product_id.uom_id.id,
                'is_reward_line': True,
                'taxes_id': [(4, tax.id, False) for tax in taxes],
            }]
        reward_dict = {}
        lines = self._get_paid_order_lines()
        amount_total = sum(self._get_base_order_lines(program).mapped('price_subtotal'))
        if program.discount_apply_on == 'cheapest_product':
            line = self._get_cheapest_line()
            if line:
                discount_line_amount = min(line.price_reduce * (program.discount_percentage / 100), amount_total)
                if discount_line_amount:
                    taxes = self.fiscal_position_id.map_tax(line.taxes_id)

                    reward_dict[line.taxes_id] = {
                        'name': _("Discount: %s", program.name),
                        'product_id': program.discount_line_product_id.id,
                        'price_unit': - discount_line_amount if discount_line_amount > 0 else 0,
                        'product_uom_qty': 1.0,
                        'product_uom': program.discount_line_product_id.uom_id.id,
                        'is_reward_line': True,
                        'taxes_id': [(4, tax.id, False) for tax in taxes],
                    }
        elif program.discount_apply_on in ['specific_products', 'on_order']:
            if program.discount_apply_on == 'specific_products':
                free_product_lines = self.env['coupon.program'].search([('reward_type', '=', 'product'), ('reward_product_id', 'in', program.discount_specific_product_ids.ids), ('is_vendor_promotion', '=', True)]).mapped('discount_line_product_id')
                lines = lines.filtered(lambda x: x.product_id in (program.discount_specific_product_ids | free_product_lines))
            currently_discounted_amount = 0
            for line in lines:
                discount_line_amount = min(self._get_reward_values_discount_percentage_per_line(program, line), amount_total - currently_discounted_amount)

                if discount_line_amount:

                    if line.taxes_id in reward_dict:
                        reward_dict[line.taxes_id]['price_unit'] -= discount_line_amount
                    else:
                        taxes = self.fiscal_position_id.map_tax(line.taxes_id)

                        reward_dict[line.taxes_id] = {
                            'name': _(
                                "Discount: %(program)s - On product with following taxes: %(taxes)s",
                                program=program.name,
                                taxes=", ".join(taxes.mapped('name')),
                            ),
                            'product_id': program.discount_line_product_id.id,
                            'price_unit': - discount_line_amount if discount_line_amount > 0 else 0,
                            'product_uom_qty': 1.0,
                            'product_uom': program.discount_line_product_id.uom_id.id,
                            'is_reward_line': True,
                            'taxes_id': [(4, tax.id, False) for tax in taxes],
                        }
                        currently_discounted_amount += discount_line_amount
        max_amount = program._compute_program_amount('discount_max_amount', self.currency_id)
        if max_amount > 0:
            amount_already_given = 0
            for val in list(reward_dict):
                amount_to_discount = amount_already_given + reward_dict[val]["price_unit"]
                if abs(amount_to_discount) > max_amount:
                    reward_dict[val]["price_unit"] = - (max_amount - abs(amount_already_given))
                    add_name = formatLang(self.env, max_amount, currency_obj=self.currency_id)
                    reward_dict[val]["name"] += "( " + _("limited to ") + add_name + ")"
                amount_already_given += reward_dict[val]["price_unit"]
                if reward_dict[val]["price_unit"] == 0:
                    del reward_dict[val]
        return reward_dict.values()
    
    def _get_reward_values_product(self, program):
        price_unit = self.order_line.filtered(lambda line: program.reward_product_id == line.product_id)[0].price_reduce
        order_lines = (self.order_line - self._get_reward_lines()).filtered(lambda x: program._get_valid_products_purchase(x.product_id))
        max_product_qty = sum(order_lines.mapped('product_qty')) or 1
        total_qty = sum(self.order_line.filtered(lambda x: x.product_id == program.reward_product_id).mapped('product_qty'))
        if program._get_valid_products_purchase(program.reward_product_id):
            program_in_order = max_product_qty // (program.rule_min_quantity + program.reward_product_quantity)
            reward_product_qty = program.reward_product_quantity * program_in_order
            reward_product_qty = min(reward_product_qty, total_qty)
            if program.rule_minimum_amount:
                order_total = sum(order_lines.mapped('price_total')) - (program.reward_product_quantity * program.reward_product_id.lst_price)
                reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
        else:
            reward_product_qty = min(program.reward_product_quantity, total_qty)

        reward_qty = min(int(int(max_product_qty / program.rule_min_quantity) * program.reward_product_quantity), reward_product_qty)
        taxes = program.reward_product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes = self.fiscal_position_id.map_tax(taxes)
        return {
            'product_id': program.discount_line_product_id.id,
            'price_unit': - price_unit,
            'product_uom_qty': reward_qty,
            'is_reward_line': True,
            'name': _("Free Product") + " - " + program.reward_product_id.name,
            'product_uom': program.reward_product_id.uom_id.id,
            'taxes_id': [(4, tax.id, False) for tax in taxes],
        }
    
    def _get_reward_line_values(self, program):
        self.ensure_one()
        self = self.with_context(lang=self.partner_id.lang)
        program = program.with_context(lang=self.partner_id.lang)
        if program.reward_type == 'discount':
            return self._get_reward_values_discount(program)
        elif program.reward_type == 'product':
            return [self._get_reward_values_product(program)]

    def _create_reward_line(self, program):
        self.write({'order_line': [(0, False, value) for value in self._get_reward_line_values(program)], 'is_valid_coupon': True})
    
    def _get_reward_lines(self):
        self.ensure_one()
        return self.order_line.filtered(lambda line: line.is_reward_line)

    def recompute_purchase_coupon_lines(self):
        for order in self:
            order._remove_invalid_reward_lines()
            order._create_new_no_code_promo_reward_lines()
            order._update_existing_reward_lines()
            if order.order_line.filtered(lambda r:r.is_reward_line):
                order.is_valid_coupon = True
 
    def _get_applied_programs_with_rewards_on_current_order(self):
        return self.no_code_promo_program_ids.filtered(lambda p: p.promo_applicability == 'on_current_order') + \
               self.applied_coupon_ids.mapped('program_id') + \
               self.code_promo_program_id.filtered(lambda p: p.promo_applicability == 'on_current_order')

    def _update_existing_reward_lines(self):
        def update_line(order, lines, values):
            lines_to_remove = self.env['purchase.order.line']
            if values['product_uom_qty'] and values['price_unit']:
                lines.write(values)
            else:
                if program.reward_type != 'free_shipping':
                    lines_to_remove += lines
                else:
                    values.update(price_unit=0.0)
                    lines.write(values)
            return lines_to_remove

        self.ensure_one()
        order = self
        applied_programs = order._get_applied_programs_with_rewards_on_current_order()
        for program in applied_programs:
            values = order._get_reward_line_values(program)
            lines = order.order_line.filtered(lambda line: line.product_id == program.discount_line_product_id)
            if program.reward_type == 'discount' and program.discount_type == 'percentage':
                lines_to_remove = lines
                for value in values:
                    value_found = False
                    for line in lines:
                        if not len(set(line.taxes_id.mapped('id')).symmetric_difference(set([v[1] for v in value['taxes_id']]))):
                            value_found = True
                            lines_to_remove -= line
                            lines_to_remove += update_line(order, line, value)
                            continue
                    if not value_found:
                        order.write({'order_line': [(0, False, value)]})
                lines_to_remove.unlink()
            else:
                update_line(order, lines, values[0]).unlink()
                
    def _get_applicable_no_code_promo_program(self):
        self.ensure_one()
        programs = self.env['coupon.program'].with_context(
            no_outdated_coupons=True,
            applicable_coupon=True,
        ).search([
            ('promo_code_usage', '=', 'no_code_needed'),
            ('is_vendor_promotion', '=', True),
            ('active', '=', True),
            '|', ('rule_date_from', '=', False), ('rule_date_from', '<=', self.date_order),
            '|', ('rule_date_to', '=', False), ('rule_date_to', '>=', self.date_order),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False),
        ])._filter_programs_from_common_rules_purchase(self)
        return programs
    
    def _create_reward_coupon(self, program):
        coupon = self.env['coupon.coupon'].search([
            ('program_id', '=', program.id),
            ('state', '=', 'expired'),
            ('partner_id', '=', self.partner_id.id),
            ('purchase_id', '=', self.id),
            ('discount_line_product_id', '=', program.discount_line_product_id.id),
        ], limit=1)
        if coupon:
            coupon.write({'state': 'reserved'})
        else:
            coupon = self.env['coupon.coupon'].sudo().create({
                'program_id': program.id,
                'state': 'reserved',
                'partner_id': self.partner_id.id,
                'purchase_id': self.id,
                'discount_line_product_id': program.discount_line_product_id.id
            })
        self.generated_coupon_ids |= coupon
        return coupon

    def _create_new_no_code_promo_reward_lines(self):
        self.ensure_one()
        order = self
        programs = order._get_applicable_no_code_promo_program()
        programs = programs._keep_only_most_interesting_auto_applied_global_discount_program()
        for program in programs:
            error_status = program._check_purchase_promo_code(order, False)
            if not error_status.get('error'):
                if program.promo_applicability == 'on_next_order':
                    order.state != 'cancel' and order._create_reward_coupon(program)
                elif program.discount_line_product_id.id not in self.order_line.mapped('product_id').ids:
                    self.write({'order_line': [(0, False, value) for value in self._get_reward_line_values(program)]})
                order.no_code_promo_program_ids |= program
 
    def _get_applied_programs(self):
        return self.code_promo_program_id + self.no_code_promo_program_ids + self.applied_coupon_ids.mapped('program_id')
    
    def _get_valid_applied_coupon_program(self):
        self.ensure_one()
        programs = self.applied_coupon_ids.mapped('program_id').filtered(lambda p: p.promo_applicability == 'on_next_order')._filter_programs_from_common_rules_purchase(self, True)
        programs += self.applied_coupon_ids.mapped('program_id').filtered(lambda p: p.promo_applicability == 'on_current_order')._filter_programs_from_common_rules_purchase(self)
        return programs

    def _remove_invalid_reward_lines(self):
        self.ensure_one()
        order = self

        applied_programs = order._get_applied_programs()
        applicable_programs = self.env['coupon.program']
        if applied_programs:
            applicable_programs = order._get_applicable_programs() + order._get_valid_applied_coupon_program()
            applicable_programs = applicable_programs._keep_only_most_interesting_auto_applied_global_discount_program()
        programs_to_remove = applied_programs - applicable_programs

        reward_product_ids = applied_programs.discount_line_product_id.ids
        invalid_lines = order.order_line.filtered(lambda line: line.is_reward_line and line.product_id.id not in reward_product_ids)

        if programs_to_remove:
            product_ids_to_remove = programs_to_remove.discount_line_product_id.ids

            if product_ids_to_remove:
                self.generated_coupon_ids.filtered(lambda coupon: coupon.program_id.discount_line_product_id.id in product_ids_to_remove).write({'state': 'expired'})

            coupons_to_remove = order.applied_coupon_ids.filtered(lambda coupon: coupon.program_id in programs_to_remove)
            coupons_to_remove.write({'state': 'new'})

            order.no_code_promo_program_ids -= programs_to_remove
            order.code_promo_program_id -= programs_to_remove

            if coupons_to_remove:
                order.applied_coupon_ids -= coupons_to_remove

            if product_ids_to_remove:
                invalid_lines |= order.order_line.filtered(lambda line: line.product_id.id in product_ids_to_remove)

        invalid_lines.unlink()

    def action_cancel_promo(self):
        self.order_line.filtered(lambda r:r.is_reward_line).unlink()
        self.write({'is_valid_coupon': False})

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    is_reward_line = fields.Boolean(string="Reward Line", default=False)
    price_reduce = fields.Float(compute='_get_price_reduce', string='Price Reduce', digits='Product Price', readonly=True, store=True)
    
    @api.depends('price_unit', 'discount_amount')
    def _get_price_reduce(self):
        for line in self:
            line.price_reduce = line.price_unit * (1.0 - line.discount_amount / 100.0)
