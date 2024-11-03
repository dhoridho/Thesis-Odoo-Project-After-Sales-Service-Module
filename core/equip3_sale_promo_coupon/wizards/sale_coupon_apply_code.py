from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleCouponApplyCode(models.TransientModel):
    _inherit = 'sale.coupon.apply.code'

    def process_coupon_equip(self):
        """
        Apply the entered coupon code if valid, raise an UserError otherwise.
        """
        sales_order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        error_status = self.apply_coupon_equip(sales_order, self.coupon_code)
        if error_status.get('error', False):
            raise UserError(error_status.get('error', False))
        if error_status.get('not_found', False):
            raise UserError(error_status.get('not_found', False))

    def apply_coupon_equip(self, order, coupon_code):
        error_status = {}
        program = self.env['coupon.program'].search([('promo_code', '=', coupon_code)])
        if program:
            error_status = program._check_promo_code(order, coupon_code)
            if not error_status:
                if program.promo_applicability == 'on_next_order':
                    # Avoid creating the coupon if it already exist
                    if program.discount_line_product_id.id not in order.generated_coupon_ids.filtered(lambda coupon: coupon.state in ['new', 'reserved']).mapped('discount_line_product_id').ids:
                        coupon = order._create_reward_coupon(program)
                        order.lock_order_line = True
                        return {
                            'generated_coupon': {
                                'reward': coupon.program_id.discount_line_product_id.name,
                                'code': coupon.code,
                            }
                        }
                else:
                    # qty = 0
                    # values = order._get_reward_line_values(program)
                    # print('valuesss',values)
                    # if values:
                    #     values = list(values)[0]
                    #     qty = values.get('product_uom_qty')
                    #     print('values eq3_sale_promo_coupon line 39', values.get('product_uom_qty'))
                    # qty, price_unit = order._create_reward_product_line_if_not_exists(coupon.program_id, origin=coupon.order_id)
                    qty = order._get_rewarded_quantity(program)
                    order._create_product_reward_line(program, qty)
                    order.code_promo_program_id = program
                    order.lock_order_line = True
        else:
            coupon = self.env['coupon.coupon'].search([('code', '=', coupon_code)], limit=1)
            if coupon:
                qty, price_unit = order._create_reward_product_line_if_not_exists(coupon.program_id, origin=coupon.order_id)
                error_status = coupon._check_coupon_code(order.with_context(should_force_qty=True))
                if not error_status:
                    order._create_reward_line_equip(coupon.program_id, qty, price_unit)
                    order.applied_coupon_ids += coupon
                    order.lock_order_line = True
                    coupon.write({'state': 'used'})
            else:
                error_status = {'not_found': _('This coupon is invalid (%s).') % (coupon_code)}
        return error_status
