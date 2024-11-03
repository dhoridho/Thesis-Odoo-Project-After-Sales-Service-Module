# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PosCouponGenerateWizard(models.TransientModel):
    _name = 'pos.coupon.generate.wizard'
    _description = 'Generate Pos Coupon Wizard'

    no_of_coupon = fields.Integer('No of Coupon', help='Number of coupons to be generated', default=1)
    coupon_program_id = fields.Many2one('pos.coupon.program', string='Coupon Program')


    def action_confirm(self):
        self.ensure_one()
        program = self.coupon_program_id
        if not program:
            raise UserError(_('Coupon Program is undefined'))
        if self.no_of_coupon <= 0:
            raise UserError(_('No of Coupon must be greater than 0'))
        
        coupon_ids = []
        for count in range(1, self.no_of_coupon + 1):
            values = {
                'coupon_program_id': program.id,
                'name': program.coupon_name,
                'type_apply': program.type_apply,
                'minimum_purchase_quantity': program.minimum_purchase_quantity,
                'sequence_generate_method': program.sequence_generate_method,
                'manual_input_sequence': program.manual_input_sequence,
                'start_date': program.start_date,
                'end_date': program.end_date,
                'no_of_usage': program.no_of_usage,
                'no_of_used': program.no_of_used,
                'company_id': program.company_id and program.company_id.id or False,
                'state': 'active',
                'reward_type': program.reward_type,
                'reward_quantity': program.reward_quantity,
                'reward_discount_type': program.reward_discount_type,
                'reward_discount_amount': program.reward_discount_amount,
                'reward_max_discount_amount': program.reward_max_discount_amount,
            }

            if program.sequence_generate_method == 'Manual Input':
                values['number'] = program.manual_input_sequence
            if program.sequence_generate_method == 'EAN13':
                values['number'] = ''

            if program.base_on_product_id:
                values['product_ids'] = [(6, 0, [program.base_on_product_id.id])]
            if program.reward_product_id:
                values['reward_product_ids'] = [(6, 0, [program.reward_product_id.id])]

            coupon = self.env['pos.coupon'].create(values)
            coupon_ids += [coupon.id]

        if coupon_ids:
            program.write({ 'state': 'active' })

        return {
            'name': _('Coupons'),
            'view_mode': 'tree,form',
            'res_model': 'pos.coupon',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', coupon_ids)],
            'context': {}
        }