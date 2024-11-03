# -*- encoding: utf-8 -*-
from odoo import api, fields, models,_


class ResCompany(models.Model):
    _inherit = "res.company"

    commission_product_id = fields.Many2one('product.product', string='Commission Product')
    commission_on_invoice_amount = fields.Boolean(string="Commission on Invoice Amount")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    commission_product_id = fields.Many2one('product.product', related='company_id.commission_product_id', 
        string='Commission Product', readonly=False)
    commission_on_invoice_amount = fields.Boolean(related='company_id.commission_on_invoice_amount', 
        string="Commission on Invoice Amount", readonly=False)