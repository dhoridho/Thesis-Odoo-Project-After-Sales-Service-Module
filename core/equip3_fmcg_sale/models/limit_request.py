from odoo import models,fields,api,_
from odoo.exceptions import ValidationError


class LimitRequestInherit(models.Model):
    _inherit = 'limit.request'

    bank_guarantee_amount = fields.Float(string='Last Bank Guarantee Amount')
    new_bank_guarantee_amount = fields.Float(string='New Bank Guarantee Amount')
    is_increase_credit_limit = fields.Boolean(string='Increase Credit Limit', related="partner_id.is_increase_credit_limit")
    last_expiration_date = fields.Date(string='Last Expiration Date')
    new_expiration_date = fields.Date(string='New Expiration Date')

    @api.onchange('partner_id')
    def set_product_brand_ids(self):
        for record in self:
            if record.partner_id:
                record.new_expiration_date = record.last_expiration_date = record.partner_id.bank_guarantee_exp_date
                record.bank_guarantee_amount = record.partner_id.bank_guarantee_amount
                line_ids = []
                if record.is_credit_limit_brand and record.limit_type == 'credit_limit_brand':
                    for limit_brand in record.partner_id.product_brand_ids:
                        line_ids.append(
                            (0,0, {'sequence': limit_brand.sequence, 'brand_id': limit_brand.brand_id.id, 'last_credit_limit_amount': limit_brand.customer_credit_limit, 'last_request_allocation_bank_guarantee_amount': limit_brand.allocation_bank_guarantee_amount}),
                        )
                record.product_brand_ids = [(6, 0, [])]
                record.product_brand_ids = line_ids

    @api.depends('partner_id', 'limit_type')
    def _compute_last_limit(self):
        for record in self:
            record.last_credit_limit = 0
            record.last_max_invoice = 0
            record.last_open_inv_no = 0
            if record.partner_id:
                record.last_credit_limit = record.partner_id.cust_credit_limit
                record.last_max_invoice = record.partner_id.customer_max_invoice_overdue
                record.last_open_inv_no = record.partner_id.no_open_inv_limit
                line_ids = []
                if record.limit_type != 'credit_limit_brand':
                    record.product_brand_ids = [(6, 0, [])]
                if not record.product_brand_ids:
                    if record.is_credit_limit_brand and record.limit_type == 'credit_limit_brand':
                        for limit_brand in record.partner_id.product_brand_ids:
                            line_ids.append(
                                (0,0, {'sequence': limit_brand.sequence, 'brand_id': limit_brand.brand_id.id, 'last_credit_limit_amount': limit_brand.customer_credit_limit, 'last_request_allocation_bank_guarantee_amount': limit_brand.allocation_bank_guarantee_amount}),
                            )
                    record.product_brand_ids = [(6, 0, [])]
                    record.product_brand_ids = line_ids


    @api.constrains('is_increase_credit_limit','bank_guarantee_amount','product_brand_ids','product_brand_ids.request_allocation_bank_guarantee_amount')
    def _constrains_bank_guarantee_amount_per_brand(self):
        for i in self:
            if i.is_increase_credit_limit:
                if i.is_credit_limit_brand: 
                    bank_guarantee_amount = i.product_brand_ids and sum(i.product_brand_ids.mapped('request_allocation_bank_guarantee_amount')) or 0
                    if bank_guarantee_amount != i.new_bank_guarantee_amount:
                        raise ValidationError(_("Total of the New Allocation Bank Guarantee can’t be less/exceeds then the New Bank Guarantee Amount"))

    # @api.model
    # def create(self, vals):
    #     res = super().create(vals)
    #     if res.is_increase_credit_limit:
    #         bank_guarantee_amount = res.product_brand_ids and sum(res.product_brand_ids.mapped('request_allocation_bank_guarantee_amount')) or 0
    #         if bank_guarantee_amount != res.new_bank_guarantee_amount:
    #             raise ValidationError(_("Total of the New Allocation Bank Guarantee can’t be less/exceeds then the New Bank Guarantee Amount"))
    #     return res

    def update_partner_product_brand_bank_guarantee(self):
        if self.state == 'confirmed' and self.is_increase_credit_limit:
            for product_brand in self.product_brand_ids:
                partner_product_brand = self.partner_id.product_brand_ids.filtered(lambda b,product_brand=product_brand:b.brand_id.id == product_brand.brand_id.id)
                if partner_product_brand:
                    partner_product_brand.request_allocation_bank_guarantee_amount = product_brand.request_allocation_bank_guarantee_amount
            self.partner_id.write({
                'bank_guarantee_amount': self.new_bank_guarantee_amount,
                'bank_guarantee_exp_date': self.new_expiration_date
            })

    def request_approve(self):
        res = super(LimitRequestInherit,self).request_approve()
        self.update_partner_product_brand_bank_guarantee()
        return res
        

    def request_confirm(self):
        res = super(LimitRequestInherit,self).request_confirm()
        self.update_partner_product_brand_bank_guarantee()
        return res