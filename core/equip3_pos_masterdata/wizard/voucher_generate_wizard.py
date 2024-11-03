# -*- coding: utf-8 -*-
from turtle import pos
from odoo import api, fields, models
from odoo.exceptions import UserError

class GeneratePosVoucherWizard(models.TransientModel):
    _name = 'generate.pos.voucher.wizard'
    _description = 'Generate Pos Voucher Wizard'

    no_of_voucher = fields.Integer('No Of Vouchers',default=1)
    amount_of_usage = fields.Integer('Amount Of Usage', default=1)

    def action_confirm(self):
        new_vouchers = self.env['pos.voucher']
        pos_obj = self.env['generate.pos.voucher'].browse(self.env.context.get('active_id'))
        vals={}

        if pos_obj:
            for count in range(0,self.no_of_voucher):
                vals['start_date'] = pos_obj.start_date
                vals['method'] = pos_obj.method
                vals['minimum_purchase_amount'] = pos_obj.minimum_purchase_amount
                vals['maximum_discount_amount'] = pos_obj.maximum_discount_amount
                vals['state'] = pos_obj.state
                vals['use_date'] = pos_obj.use_date
                vals['receipt_template_id'] = self.env.context.get('receipt_template_id')
                vals['end_date'] = pos_obj.end_date
                vals['apply_type'] = pos_obj.apply_type
                vals['value'] = pos_obj.value
                vals['source'] = pos_obj.source

                vals['limit_restrict_product_ids'] = pos_obj.limit_restrict_product_ids
                vals['pos_category_ids'] = pos_obj.pos_category_ids
                if pos_obj.user_id:
                    vals['user_id'] = pos_obj.user_id.id 

                vals['generated_source_id'] = pos_obj.id
                vals['is_generate_voucher'] = True
                vals['source_document_id'] = self.env.context.get('active_id')

                vals['is_customize_sequence'] = pos_obj.is_customize_sequence
                vals['sequence_generate_method'] = pos_obj.sequence_generate_method
                vals['manual_input_sequence'] = pos_obj.manual_input_sequence
                vals['running_number_prefix'] = pos_obj.running_number_prefix
                vals['running_number_digit'] = pos_obj.running_number_digit

                if pos_obj.brand_ids:
                    vals['brand_ids'] = [(6,0,pos_obj.brand_ids.ids)]

                if self.amount_of_usage>1:
                    created_obj = self.env['pos.voucher'].create(vals)
                    new_vouchers |= created_obj
                    for count in range(1,self.amount_of_usage):
                        vals['code'] = created_obj.code
                        vals['number'] = created_obj.number
                        new_vouchers |= self.env['pos.voucher'].create(vals)
                else:
                    new_vouchers |= self.env['pos.voucher'].create(vals)
        return new_vouchers

GeneratePosVoucherWizard()