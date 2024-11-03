# -*- coding: utf-8 -*-
from odoo import api, fields, models

class PosDiscount(models.Model):

    _name = "pos.global.discount"
    _description = "Management Global Discount"

    name = fields.Char('Name', required=1)
    amount = fields.Float('Discount Amount', required=1)
    product_id = fields.Many2one(
        'product.product',
        'Global Discount',
        domain=[
            ('sale_ok', '=', True),
            ('available_in_pos', '=', True)
        ],
        required=1)
    reason = fields.Char('Reason', required=1)
    type = fields.Selection([
        ('percent', '%'),
        ('fixed', 'Fixed Amount')
    ],
        string='Type',
        default='percent',
        required=1
    )
    branch_ids = fields.Many2many(
        'res.branch',
        'pos_global_discount_branch_rel',
        'discount_id',
        'branch_id',
        default=lambda self: [(4, self.env.branch.id)] if len(self.env.branches) == 1 else False, 
        domain=lambda self: [('id', 'in', self.env.branches.ids)],
        string='Branchs'
    )
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)

    @api.model
    def default_get(self, default_fields):
        res = super(PosDiscount, self).default_get(default_fields)
        products = self.env['product.product'].search([('name', '=', 'Discount')])
        if products:
            res.update({'product_id': products[0].id})
        return res
