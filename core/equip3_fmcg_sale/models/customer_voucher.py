from odoo import models,fields,api,_
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta

class CustomerVoucher(models.Model):
    _inherit = 'customer.voucher'

    is_claimed = fields.Boolean("Is Claimed")
    reward_amount = fields.Float("Reward Amount", compute='_compute_reward_amount')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
                                          readonly=True, store=True,
                                          help='Utility field to express amount currency')
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')

    # @api.depends('sale_order_line_ids')
    def _compute_reward_amount(self):
        for rec in self:
            amount = 0
            order_id = False
            if rec.sale_order_line_ids:
                for line in rec.sale_order_line_ids:
                    if line.is_reward_line or rec.discount_line_product_id.product_tmpl_id.id == line.product_template_id.id:
                        amount += abs(line.price_total)
                        if not order_id:
                            order_id = line.order_id.id
            rec.sale_order_id = order_id
            rec.reward_amount = amount

