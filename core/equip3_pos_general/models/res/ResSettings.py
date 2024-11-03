# -*- coding: utf-8 -*-

from odoo import api, models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_order_rounding = fields.Boolean("Order Rounding",related="company_id.is_order_rounding",readonly=False)
    order_rounding_type = fields.Selection([('Up','Up'), ('Down','Down'), ('Half Up','Half Up')], string="Order Rounding Type  (Not Used)",related="company_id.order_rounding_type",readonly=False)
    rounding_multiplier = fields.Selection([('0.05','0.05'), ('0.1','0.1'), ('0.5','0.5'), ('1','1'), ('10','10'), ('100','100'), ('500','500'), ('1000','1000')], string="Order Rounding Multiplier  (Not Used)",related="company_id.rounding_multiplier",readonly=False)
    pos_product_discount1_id = fields.Many2one("product.product", "POS Product Discount", related="company_id.pos_product_discount1_id",readonly=False)
    apply_rounding_type = fields.Selection([('All Payment','All Payment'), ('Cash Payment','Cash Payment')], string="Apply Rounding", related="company_id.apply_rounding_type",readonly=False)
    rounding_method_id = fields.Many2one('account.cash.rounding','Rounding Method', related="company_id.rounding_method_id",readonly=False)
    pos_def_receipt_template_id = fields.Many2one('pos.receipt.template','POS Default Receipt Template', related="company_id.pos_def_receipt_template_id",readonly=False,domain="[('company_id', '=', company_id)]")
    is_pos_receivable = fields.Boolean('Receivable', related='company_id.is_pos_receivable', readonly=False)