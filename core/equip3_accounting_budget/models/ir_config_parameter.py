# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"


    # @api.model
    # def set_param(self, key, value):
    #     param = self.search([('key', '=', key)])
    #     if param:
    #         old = param.value
    #         if value is not False and value is not None:
    #             pass
    #         else:
    #             if key == 'is_allow_purchase_budget':
    #                 self.env.cr.execute(
    #                     "UPDATE product_template SET is_use_purchase_budget = FALSE WHERE is_use_purchase_budget = TRUE"
    #                 )
    #                 # product_template = self.env['product.template'].search([('is_use_purchase_budget','=',True)])
    #                 # for product in product_template:
    #                 #     product.write({'is_use_purchase_budget': False})
    #     else:
    #         if value is not False and value is not None:
    #             if key == 'is_allow_purchase_budget':
    #                 self.env.cr.execute(
    #                     "UPDATE product_template SET is_use_purchase_budget = TRUE WHERE is_use_purchase_budget = FALSE"
    #                 )
    #                 # product_template = self.env['product.template'].search([('is_use_purchase_budget','=',False)])
    #                 # for product in product_template:
    #                 #     product.write({'is_use_purchase_budget': True})

    #     res = super(IrConfigParameter, self).set_param(key, value)
    #     return res