# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class equip3_general_products(models.Model):
#     _name = 'equip3_general_products.equip3_general_products'
#     _description = 'equip3_general_products.equip3_general_products'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
