
import math
from odoo import fields, models, api, _
from odoo.tools import formatLang


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_valid_coupon = fields.Boolean(string="Valid Coupon", default=False)

    def _create_new_no_code_promo_reward_lines(self):
        res = super(SaleOrder, self)._create_new_no_code_promo_reward_lines()
        for record in self:
            if record.order_line.filtered(lambda r:r.is_reward_line):
                record.is_valid_coupon = True
        return res

    def _create_reward_line(self, program):
        res = super(SaleOrder, self)._create_reward_line(program)
        for record in self:
            record.is_valid_coupon = True
        return res

    def action_cancel_promo(self):
        program_ids = self.no_code_promo_program_ids
        if self.applied_coupon_ids:
            program_ids |= self.applied_coupon_ids.mapped('program_id')
        if program_ids:
            for record in program_ids:
                if record.reward_type == "product":
                    lines = self.order_line.filtered(lambda x:x.product_id.id == record.reward_product_id.id)
                    for line in lines:
                        line.product_uom_qty -= line.line_reward_product_quantity
                        line.line_reward_product_quantity = 0
                        if line.product_uom_qty == 0:
                            line.unlink()
                    discount_product_id = self.order_line.filtered(lambda x:x.product_id.id == record.discount_line_product_id.id)
                    if discount_product_id:
                        discount_product_id.unlink()
        self.order_line.filtered(lambda r:r.is_reward_line).unlink()
        self.write({'is_valid_coupon': False})

    def _is_reward_in_order_lines(self, program):
        self.ensure_one()
        order_line = self.order_line.filtered(lambda line:
            line.product_id == program.reward_product_id)
        if not order_line:
            self.order_line.create({
                'product_id': program.reward_product_id.id,
                'product_template_id': program.reward_product_id.id,
                'name': program.reward_product_id.name,
                'discount_method': "fix",
                'product_uom_qty': program.reward_product_quantity,
                'product_uom': program.reward_product_uom_id.id,
                'order_id': self.id
            })
            return True
        else:
            return super(SaleOrder, self)._is_reward_in_order_lines(program=program)

    def _get_applicable_no_code_promo_program(self):
        self.ensure_one()
        programs = self.env['coupon.program'].with_context(
            no_outdated_coupons=True,
            applicable_coupon=True,
        ).search([
            ('promo_code_usage', '=', 'no_code_needed'),
            ('is_sale_promotion', '=', True),
            ('active', '=', True),
            '|', ('rule_date_from', '=', False), ('rule_date_from', '<=', self.date_order),
            '|', ('rule_date_to', '=', False), ('rule_date_to', '>=', self.date_order),
            '|', ('company_id', '=', self.company_id.id), ('company_id', '=', False),
        ])._filter_programs_from_common_rules(self)
        return programs
    
    def _action_confirm(self):
        res = super(SaleOrder, self)._action_confirm()
        for record in self:
            if record.generated_coupon_ids:
                coupon_ids = record.generated_coupon_ids.filtered(lambda x:x.state == "reserved")
                coupon_ids.write({
                        'state': 'new'
                    })
        return res

    def _update_existing_reward_lines(self):
        applied_programs = self._get_applied_programs()
        res = super(SaleOrder, self)._update_existing_reward_lines()
        self.no_code_promo_program_ids += applied_programs
        return res

    # inherited from \basic\delivery\models\sale_order.py
    def recompute_coupon_lines(self):
        order_line_before = self.order_line
        max_qty = sum(order_line_before.mapped('product_uom_qty'))
        res = super(SaleOrder, self).recompute_coupon_lines()
        if self.no_code_promo_program_ids:
            for record in self.no_code_promo_program_ids:
                if record.reward_type == "product" and record.promo_applicability == 'on_current_order':
                    order_line = self.order_line.filtered(lambda x:x.product_id.id == record.reward_product_id.id)
                    qty_cal = record.reward_product_quantity
                    price_unit = 0
                    if order_line:
                        product_line = order_line_before.filtered(lambda r: r.product_id.id == order_line.product_id.id)
                        qty_cal = math.floor(max_qty / record.rule_min_quantity)
                        qty_cal *= record.reward_product_quantity
                        order_line.line_reward_product_quantity = qty_cal
                        if not product_line:
                            order_line.product_uom_qty = qty_cal
                        else:
                            order_line.product_uom_qty += qty_cal
                        # if not product_line:
                        #     max_qty = sum(order_line_before.mapped('product_uom_qty')) - sum(order_line_before.mapped('line_reward_product_quantity'))
                        #     qty_cal = math.floor(max_qty / record.rule_min_quantity)
                        #     if not record.is_free_purchase:
                        #         qty_cal *= record.reward_product_quantity
                        #     order_line.product_uom_qty = qty_cal
                        #     order_line.line_reward_product_quantity = qty_cal
                        # else:
                        #     max_qty = sum(product_line.mapped('product_uom_qty'))
                        #     qty_cal = math.floor(max_qty / record.rule_min_quantity)
                        #     if not record.is_free_purchase:
                        #         qty_cal *= record.reward_product_quantity
                        #     order_line.line_reward_product_quantity = qty_cal
                        #     order_line.product_uom_qty += qty_cal
                        price_unit = order_line.price_unit
                    elif not order_line:
                        self.order_line.create({
                            'product_id': record.reward_product_id.id,
                            'product_template_id': record.reward_product_id.id,
                            'name': record.reward_product_id.name,
                            'discount_method': "fix",
                            'is_reward_line': True,
                            'product_uom_qty': record.reward_product_quantity,
                            'product_uom': record.reward_product_uom_id.id,
                            'order_id': self.id,
                            'price_unit': price_unit,
                        })
                    discount_product_id = self.order_line.filtered(lambda x:x.product_id.id == record.discount_line_product_id.id)
                    if discount_product_id:
                        discount_product_id.product_uom_qty = qty_cal
                        discount_product_id.price_unit = - (price_unit)
                    else:
                        self.order_line.create({
                            'product_id': record.discount_line_product_id.id,
                            'product_template_id': record.discount_line_product_id.id,
                            'name': record.discount_line_product_id.name,
                            'discount_method': "fix",
                            'product_uom_qty': qty_cal,
                            'product_uom': record.reward_product_uom_id.id,
                            'order_id': self.id,
                            'price_unit': - (price_unit)
                        })
                    print (">>>\n\n")
            SaleOrderLine = self.env['sale.order.line']
            SaleOrderLine_recs = SaleOrderLine.search([('order_id', '=', self.id)])
            next_num = 1
            for line_rec in SaleOrderLine_recs:
                line_rec.write({'sale_line_sequence': next_num})
                next_num += 1
        return res


    # inherited from \basic\sale_coupon\models\sale_order.py
    def _get_base_order_lines(self, program):
        """ Returns the sale order lines not linked to the given program.
        """
        return self.order_line.filtered(lambda x: not (x.is_reward_line and x.product_id == program.discount_line_product_id))

    # inherited from \basic\sale_coupon\models\sale_order.py
    def _get_reward_values_discount(self, program):
        SaleOrderLine = self.env['sale.order.line']
        SaleOrderLine_rec = SaleOrderLine.search([('order_id', '=', self.id)], limit=1)

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
                'tax_id': [(4, tax.id, False) for tax in taxes],
                'line_warehouse_id_new': SaleOrderLine_rec.line_warehouse_id_new.id,
                'delivery_address_id': SaleOrderLine_rec.delivery_address_id.id,
                'multiple_do_date_new': SaleOrderLine_rec.multiple_do_date_new,
                'account_tag_ids': SaleOrderLine_rec.account_tag_ids.ids,
            }]
        reward_dict = {}
        lines = self._get_paid_order_lines()
        amount_total = sum(self._get_base_order_lines(program).mapped('price_subtotal'))
        if program.discount_apply_on == 'cheapest_product':
            line = self._get_cheapest_line()
            if line:
                discount_line_amount = min(line.price_reduce * (program.discount_percentage / 100), amount_total)
                if discount_line_amount:
                    taxes = self.fiscal_position_id.map_tax(line.tax_id)

                    reward_dict[line.tax_id] = {
                        'name': _("Discount: %s", program.name),
                        'product_id': program.discount_line_product_id.id,
                        'price_unit': - discount_line_amount if discount_line_amount > 0 else 0,
                        'product_uom_qty': 1.0,
                        'product_uom': program.discount_line_product_id.uom_id.id,
                        'is_reward_line': True,
                        'tax_id': [(4, tax.id, False) for tax in taxes],
                        'line_warehouse_id_new': SaleOrderLine_rec.line_warehouse_id_new.id,
                        'delivery_address_id': SaleOrderLine_rec.delivery_address_id.id,
                        'multiple_do_date_new': SaleOrderLine_rec.multiple_do_date_new,
                        'account_tag_ids': SaleOrderLine_rec.account_tag_ids.ids,
                    }
        elif program.discount_apply_on in ['specific_products', 'on_order']:
            if program.discount_apply_on == 'specific_products':
                # We should not exclude reward line that offer this product since we need to offer only the discount on the real paid product (regular product - free product)
                free_product_lines = self.env['coupon.program'].search([('reward_type', '=', 'product'), ('reward_product_id', 'in', program.discount_specific_product_ids.ids)]).mapped('discount_line_product_id')
                lines = lines.filtered(lambda x: x.product_id in (program.discount_specific_product_ids | free_product_lines))

            # when processing lines we should not discount more than the order remaining total
            currently_discounted_amount = 0
            for line in lines:
                discount_line_amount = min(self._get_reward_values_discount_percentage_per_line(program, line), amount_total - currently_discounted_amount)

                if discount_line_amount:

                    if line.tax_id in reward_dict:
                        reward_dict[line.tax_id]['price_unit'] -= discount_line_amount
                    else:
                        taxes = self.fiscal_position_id.map_tax(line.tax_id)

                        reward_dict[line.tax_id] = {
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
                            'tax_id': [(4, tax.id, False) for tax in taxes],
                            'line_warehouse_id_new': SaleOrderLine_rec.line_warehouse_id_new.id,
                            'delivery_address_id': SaleOrderLine_rec.delivery_address_id.id,
                            'multiple_do_date_new': SaleOrderLine_rec.multiple_do_date_new,
                            'account_tag_ids': SaleOrderLine_rec.account_tag_ids.ids,
                        }
                        currently_discounted_amount += discount_line_amount

        # If there is a max amount for discount, we might have to limit some discount lines or completely remove some lines
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

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    line_reward_product_quantity = fields.Float(string='Reward Product Qty')

    @api.onchange('product_id')
    def product_id_change(self):
        res = super(SaleOrderLine, self).product_id_change()
        if self.product_id:
            self.line_reward_product_quantity = 0
        return res
