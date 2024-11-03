
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleCouponApplyCode(models.TransientModel):
    _inherit = 'sale.coupon.apply.code'

    def process_coupon(self):
        context = dict(self.env.context) or {}
        active_model = context.get('active_model')
        if active_model == 'purchase.order':
            purchase_order = self.env['purchase.order'].browse(self.env.context.get('active_id'))
            error_status = self.apply_purchase_coupon(purchase_order, self.coupon_code)
            if error_status.get('error', False):
                raise UserError(error_status.get('error', False))
            if error_status.get('not_found', False):
                raise UserError(error_status.get('not_found', False))
        else:
            program = self.env['coupon.program'].search([('promo_code', '=', self.coupon_code), ('is_vendor_promotion', '=', True)], limit=1)
            if program:
                raise UserError(_('Coupon Code Is Invalid.'))
            return super(SaleCouponApplyCode, self).process_coupon()

    def apply_purchase_coupon(self, order, coupon_code):
        error_status = {}
        program = self.env['coupon.program'].search([('promo_code', '=', coupon_code), ('is_vendor_promotion', '=', True)])
        if program:
            error_status = program._check_purchase_promo_code(order, coupon_code)
            if not error_status:
                if program.promo_applicability == 'on_next_order':
                    if program.discount_line_product_id.id not in order.generated_coupon_ids.filtered(lambda coupon: coupon.state in ['new', 'reserved']).mapped('discount_line_product_id').ids:
                        coupon = order._create_reward_coupon(program)
                        return {
                            'generated_coupon': {
                                'reward': coupon.program_id.discount_line_product_id.name,
                                'code': coupon.code,
                            }
                        }
                else:
                    order._create_reward_line(program)
                    order.code_promo_program_id = program
        else:
            coupon = self.env['coupon.coupon'].search([('code', '=', coupon_code), ('program_id.is_vendor_promotion', '=', True)], limit=1)
            if coupon:
                error_status = coupon._check_coupon_code_purchase(order)
                if not error_status:
                    order._create_reward_line(coupon.program_id)
                    order.applied_coupon_ids += coupon
                    coupon.write({'state': 'used'})
            else:
                error_status = {'not_found': _('This coupon is invalid (%s).') % (coupon_code)}
        return error_status
