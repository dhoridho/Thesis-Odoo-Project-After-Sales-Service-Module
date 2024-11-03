from odoo import fields, models, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    lock_order_line = fields.Boolean()

    def _is_reward_in_order_lines(self, program):
        self.ensure_one()
        if self.env.context.get('should_force_qty', False):
            return True
        return super(SaleOrder, self)._is_reward_in_order_lines(program)
    
    def _get_reward_values_product(self, program):
        if program:
            order_lines = (self.order_line - self._get_reward_lines()).filtered(lambda x: program._get_valid_products(x.product_id))
            max_product_qty = sum(order_lines.mapped('product_uom_qty')) or 1
            total_qty = sum(self.order_line.filtered(lambda x: x.product_id == program.reward_product_id).mapped('product_uom_qty'))
            # Remove needed quantity from reward quantity if same reward and rule product
            if program._get_valid_products(program.reward_product_id):
                # number of times the program should be applied
                program_in_order = max_product_qty // (program.rule_min_quantity + program.reward_product_quantity)
                # multipled by the reward qty
                reward_product_qty = program.reward_product_quantity * program_in_order
                # do not give more free reward than products
                reward_product_qty = min(reward_product_qty, total_qty)
                if program.rule_minimum_amount:
                    order_total = sum(order_lines.mapped('price_total')) - (program.reward_product_quantity * program.reward_product_id.lst_price)
                    if order_total <= 0:
                        reward_product_qty = program.reward_product_quantity
                    else:
                        reward_product_qty = min(reward_product_qty, order_total // program.rule_minimum_amount)
            else:
                reward_product_qty = min(program.reward_product_quantity, total_qty)

            reward_qty = min(int(int(max_product_qty / program.rule_min_quantity) * program.reward_product_quantity), reward_product_qty)
            # Take the default taxes on the reward product, mapped with the fiscal position
            taxes = program.reward_product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
            taxes = self.fiscal_position_id.map_tax(taxes)
            return {
                'product_id': program.discount_line_product_id.id,
                'price_unit': 0,
                'product_uom_qty': reward_qty,
                'is_reward_line': True,
                'name': _("Free Product") + " - " + program.reward_product_id.name,
                'product_uom': program.reward_product_id.uom_id.id,
                'tax_id': [(4, tax.id, False) for tax in taxes],
            }
        else:
            return super(SaleOrder, self)._get_reward_values_product(program)

    def _get_applicable_programs_equip(self):
        self.ensure_one()
        programs_filtered = self.env['coupon.program']
        total_qty = self.order_line and sum(self.order_line.mapped('product_uom_qty')) or 0
        total_amount = self.amount_untaxed
        programs = self.env['coupon.program'].search([
            ('company_id', 'in', [self.company_id.id, False]),
            ('is_sale_promotion', '=', True),
            ('promo_code_usage', '=', 'no_code_needed')
        ], order="sequence asc")._filter_programs_from_common_rules_equip(self)
        is_multi_promo = False
        promo = ""
        for program in programs:
            if program.promotion_type == 'single':
                if promo == 'single':
                    programs_filtered |= program
                    break
                if not promo:
                    promo = program.promotion_type
                    programs_filtered |= program
                    break
            elif program.promotion_type == 'multilevel':
                if promo == 'multilevel':
                    if total_amount >= program.rule_minimum_amount and total_qty >= program.rule_min_quantity:
                        total_amount -= program.rule_minimum_amount
                        total_qty -= program.rule_min_quantity
                        programs_filtered |= program
                if not promo:
                    promo = program.promotion_type
                    if total_amount >= program.rule_minimum_amount and total_qty >= program.rule_min_quantity:
                        total_amount -= program.rule_minimum_amount
                        total_qty -= program.rule_min_quantity
                        programs_filtered |= program
            elif program.promotion_type == 'multi':
                if promo == 'multi':
                    if total_amount >= program.rule_minimum_amount and total_qty >= program.rule_min_quantity:
                        programs_filtered |= program
                if not promo:
                    promo = program.promotion_type
                    if total_amount >= program.rule_minimum_amount and total_qty >= program.rule_min_quantity:
                        programs_filtered |= program
            elif program.promotion_type == 'multiple':
                if promo == 'multiple':
                    if total_amount >= program.rule_minimum_amount and total_qty >= program.rule_min_quantity:
                        programs_filtered |= program
                if not promo:
                    promo = program.promotion_type
                    if total_amount >= program.rule_minimum_amount and total_qty >= program.rule_min_quantity:
                        programs_filtered |= program
        return programs_filtered

    def _get_rewarded_quantity(self, program):
        program_product_ids = self.env['product.product'].search(eval(program.rule_products_domain))
        to_reward_lines = self.order_line.filtered(
            lambda line: not line.is_reward_line and \
                line.product_id.id in program_product_ids.ids)
        to_reward_qty = sum(to_reward_lines.mapped('product_uom_qty')) - sum(to_reward_lines.mapped('reward_quantity'))
        to_reward_qty = (to_reward_qty // program.rule_min_quantity) * program.reward_product_quantity
        return to_reward_qty

    def _get_rewarded_price_unit(self, program):
        to_reward_lines = self.order_line.filtered(
            lambda line: line.product_id == program.reward_product_id)
        if to_reward_lines:
            return sum(to_reward_lines.mapped('price_unit')) / len(to_reward_lines)
        return program.reward_product_id.product_tmpl_id.list_price

    def _reset_reward_lines(self):
        self.ensure_one()
        to_remove = self.order_line.filtered(lambda l: l.is_reward_line)
        line_values = [(2, line.id) for line in to_remove]

        to_reset = self.order_line.filtered(lambda l: not l.is_reward_line)
        for line in to_reset:
            line_values += [(1, line.id, {
                'product_uom_qty': line.product_uom_qty - line.reward_quantity,
                'reward_quantity': 0.0
            })]

        self.order_line = line_values

        applied_coupons = self.applied_coupon_ids
        if applied_coupons:
            self.applied_coupon_ids = [(5,)]
            applied_coupons.write({'state': 'reserved'})

    def _get_reward_values_discount_percentage_per_line(self, program, line):
        self.env.context = dict(self._context)
        res = super()._get_reward_values_discount_percentage_per_line(program, line)
        total_disc = res
        if self.env.context.get('promo_discount'):
            if program.promotion_type == 'multiple':
                res = ((line.product_uom_qty * line.price_reduce) - self.env.context.get('promo_discount')) * (program.discount_percentage / 100)
            total_disc = res + self.env.context.get('promo_discount')
        self.env.context.update({'promo_discount': total_disc})
        return res

    def _create_product_reward_line(self, program, qty):
        self.ensure_one()
        sale_order_line_obj = self.env['sale.order.line']
        price_unit = program.reward_product_id.product_tmpl_id.list_price
        taxes = program.reward_product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        multiple_do_date_new = fields.datetime.now()
        warehouse_new_id = self.warehouse_new_id.id
        if self.is_single_delivery_date:
            multiple_do_date_new = self.commitment_date
        if program.reward_type == 'product' and program.reward_product_id:
            sale_order_line_obj.create({
                'order_id': self.id,
                'sequence': str(len(self.order_line) + 1),
                'sale_line_sequence': str(len(self.order_line) + 1),
                'product_id': program.reward_product_id.id,
                'price_unit': 0,
                'product_uom_qty': qty,
                'name': program.reward_product_id.name,
                'product_uom': program.reward_product_id.uom_id.id,
                'account_tag_ids': [(6, 0, self.account_tag_ids.ids)],
                'delivery_address_id': self.partner_id.id,
                'multiple_do_date_new': multiple_do_date_new,
                'line_warehouse_id_new': warehouse_new_id,
                'is_reward_line': True,
                'tax_id': [(4, tax.id, False) for tax in taxes],
                'is_promotion_product_line': True
            })
        else:
            values = self._get_reward_line_values(program)
            if values:
                values = list(values)[0]
                price_unit = values.get('price_unit')
                qty = values.get('product_uom_qty')
            sale_order_line_obj.create({
                'order_id': self.id,
                'sequence': str(len(self.order_line) + 1),
                'sale_line_sequence': str(len(self.order_line) + 1),
                'product_id': program.discount_line_product_id.id,
                'price_unit': price_unit,
                'product_uom_qty': qty,
                'name': program.name,
                'product_uom': program.discount_line_product_id.uom_id.id,
                'account_tag_ids': [(6, 0, self.account_tag_ids.ids)],
                'delivery_address_id': self.partner_id.id,
                'multiple_do_date_new': multiple_do_date_new,
                'line_warehouse_id_new': warehouse_new_id,
                'is_reward_line': True,
                'tax_id': [(4, tax.id, False) for tax in taxes],
                'is_promotion_product_line': True,
                'is_promotion_disc_product_line': True if program.reward_type == 'discount' else False
            })

    def _create_reward_product_line_if_not_exists(self, program, origin=None):
        self.ensure_one()
        if not origin:
            origin = self
        to_reward_qty = origin._get_rewarded_quantity(program)
        reward_line = self.order_line.filtered(lambda l: l.product_id == program.reward_product_id and l.price_unit == program.reward_product_id.product_tmpl_id.list_price and l.product_uom.id == program.reward_product_id.uom_id.id and l.is_reward_line == True)
        if not reward_line:
            self._create_product_reward_line(program, to_reward_qty)
        else:
            for line in reward_line:
                line.product_uom_qty += to_reward_qty
        to_reward_price_unit = self._get_rewarded_price_unit(program)
        return to_reward_qty, to_reward_price_unit

    def _create_reward_line_equip(self, program, qty, price_unit):
        self.ensure_one()
        order = self
        multiple_do_date_new = fields.datetime.now()
        warehouse_new_id = self.warehouse_new_id.id
        if self.is_single_delivery_date:
            multiple_do_date_new = self.commitment_date
        if program.reward_type == 'product':
            product_line = order.order_line.filtered(lambda l: l.product_id == program.reward_product_id)
            taxes = product_line.mapped('tax_id').filtered(lambda t: t.company_id.id == order.company_id.id)
            line_to_add = [(0, 0, {
                'sale_line_sequence': str(len(order.order_line) + 1),
                'product_id': program.discount_line_product_id.id,
                'price_unit': - price_unit,
                'product_uom_qty': qty,
                'is_reward_line': True,
                'name': program.name,
                'product_uom': program.reward_product_id.uom_id.id,
                'tax_id': [(4, tax.id, False) for tax in taxes],
                'account_tag_ids': [(6, 0, order.account_tag_ids.ids)],
                'delivery_address_id': order.partner_id.id,
                'multiple_do_date_new': multiple_do_date_new,
                'line_warehouse_id_new': warehouse_new_id,
                'is_promotion_product_line': True
            })]

            line_to_update = [
                (1, line.id, {
                    'reward_quantity': qty,
                    'product_uom_qty': line.product_uom_qty + qty
                })
                for line in order.order_line.filtered(lambda l: not l.is_reward_line and l.product_id == program.reward_product_id)
            ]
            order.order_line = line_to_add + line_to_update

        else:
            # not implemented yet
            pass

    def recompute_coupon_lines_equip(self):
        self.ensure_one()
        order = self
        order._reset_reward_lines()
        programs = order._get_applicable_programs_equip()
        for program in programs:
            if program.promo_applicability == 'on_next_order':
                if order.state != 'cancel':
                    order._create_reward_coupon(program)
            else:
                order._create_reward_product_line_if_not_exists(program)
                # qty, price_unit = order._create_reward_product_line_if_not_exists(program)
                # order._create_reward_line_equip(program, qty, price_unit)
                order.lock_order_line = True

    def action_confirm(self):
        self.generated_coupon_ids.write({'state': 'new'})
        self.applied_coupon_ids.write({'state': 'used'})
        self._send_reward_coupon_mail()
        return super(SaleOrder, self).action_confirm()

    def action_cancel_promo(self):
        self.ensure_one()
        self._reset_reward_lines()
        if self.code_promo_program_id:
            self.code_promo_program_id = False
        self.lock_order_line = False


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    reward_quantity = fields.Float(string='Reward Quantity')
