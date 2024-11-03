
import math
from odoo import api, fields, models, _


class SaleCouponApplyCode(models.TransientModel):
    _inherit = 'sale.coupon.apply.code'
    
    
    def process_coupon(self):
        context = dict(self.env.context) or {}
        sales_order = self.env['sale.order'].browse(context.get('active_id'))
        order_line_before = sales_order.order_line
        res = super(SaleCouponApplyCode, self).process_coupon()
        coupon_id = self.env['coupon.coupon'].search([
            ('code', '=', self.coupon_code)
        ])
        if coupon_id and coupon_id.program_id.reward_type == "product" and coupon_id.program_id.promo_applicability == 'on_next_order':
            record = coupon_id.program_id
            order_lines = coupon_id.order_id.order_line.filtered(lambda r: not r.is_reward_line)
            max_qty = sum(order_lines.mapped('product_uom_qty')) - sum(order_lines.mapped('line_reward_product_quantity'))
            order_line = sales_order.order_line.filtered(lambda x:x.product_id.id == coupon_id.program_id.reward_product_id.id)
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
                price_unit = order_line.price_unit
            elif not order_line:
                sales_order.order_line.create({
                        'product_id': coupon_id.program_id.reward_product_id.id,
                        'product_template_id': coupon_id.program_id.reward_product_id.id,
                        'name': coupon_id.program_id.reward_product_id.name,
                        'discount_method': "fix",
                        'is_reward_line': True,
                        'price_unit': price_unit,
                        'product_uom_qty': coupon_id.program_id.reward_product_quantity,
                        'product_uom': coupon_id.program_id.reward_product_uom_id.id,
                        'order_id': sales_order.id
                    })
            discount_product_id = sales_order.order_line.filtered(lambda x:x.product_id.id == coupon_id.program_id.discount_line_product_id.id)
            if discount_product_id:
                discount_product_id.product_uom_qty = qty_cal
                discount_product_id.price_unit = - (price_unit)
            else:
                order_line_before.create({
                    'product_id': coupon_id.program_id.discount_line_product_id.id,
                    'product_template_id': coupon_id.program_id.discount_line_product_id.id,
                    'name': coupon_id.program_id.discount_line_product_id.name,
                    'discount_method': "fix",
                    'product_uom_qty': qty_cal,
                    'price_unit': - (price_unit),
                    'product_uom': coupon_id.program_id.reward_product_uom_id.id,
                    'order_id': sales_order.id
                })
        return res
