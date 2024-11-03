# -*- coding: utf-8 -*-

from odoo import fields, models, api

class POSConfig(models.Model):
    _inherit = 'pos.config'
    
    order_summery = fields.Boolean('Order Summery')
    product_summery = fields.Boolean('Product Summery')
    product_categ_summery = fields.Boolean('Product product Summery')
    loc_summery = fields.Boolean('Audit Report')
    payment_summery = fields.Boolean('Payment Summery')

    @api.model
    def action_analytic_pos_dashboard_redirect(self):        
        return self.env.ref('equip3_pos_report.tag_analytic_pos_dashboard').read()[0]