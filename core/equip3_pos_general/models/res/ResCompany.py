# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError

class Company(models.Model):
    _inherit = 'res.company'

    is_order_rounding = fields.Boolean("Order Rounding")
    order_rounding_type = fields.Selection([('Up','Up'), ('Down','Down'), ('Half Up','Half Up')], string="Order Rounding Type (Not Used)")
    rounding_multiplier = fields.Selection([('0.05','0.05'), ('0.1','0.1'), ('0.5','0.5'), ('1','1'), ('10','10'), ('100','100'), ('500','500'), ('1000','1000')], string="Order Rounding Multiplier  (Not Used)")
    apply_rounding_type = fields.Selection([('All Payment','All Payment'), ('Cash Payment','Cash Payment')], string="Apply Rounding")
    rounding_method_id = fields.Many2one('account.cash.rounding','Rounding Method')
    pos_def_receipt_template_id = fields.Many2one('pos.receipt.template','POS Default Receipt Template',domain="[('company_id', '=', company_id)]")
    
    is_pos_receivable = fields.Boolean('Receivable')

    def default_pos_product_discount_id(self):
        product = False
        pt = self.env.ref('equip3_pos_masterdata.discount_service_product_data')
        if pt:
            product = self.env['product.template'].browse(pt.id).product_variant_ids[0].id
        return product

    pos_product_discount1_id = fields.Many2one("product.product", "POS Product Discount", default=default_pos_product_discount_id)

    @api.constrains('pos_product_discount1_id')
    def check_pos_product_discount_id(self):
        if self.pos_product_discount1_id and self.pos_product_discount1_id.categ_id:
            if not self.pos_product_discount1_id.categ_id.property_account_expense_categ_id:
                raise ValidationError(_( "Define product category “(the Discount Service’s product category)” expense account for ("+self.name+")."))
