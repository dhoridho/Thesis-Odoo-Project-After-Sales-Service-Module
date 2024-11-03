# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class equip3_accounting_settings(models.Model):
#     _name = 'equip3_accounting_settings.equip3_accounting_settings'
#     _description = 'equip3_accounting_settings.equip3_accounting_settings'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
