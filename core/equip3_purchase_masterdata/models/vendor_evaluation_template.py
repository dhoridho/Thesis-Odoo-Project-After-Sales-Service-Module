# -*- coding: utf-8 -*-

from odoo import fields, models


class VendorEvaluationTemplate(models.Model):
    _name = 'vendor.evaluation.template'
    _description = 'Vendor Evaluation Template'

    name = fields.Char(string='Name', required=True)
    evaluation_lines = fields.One2many('vendor.evaluation.template.line', 'evaluation_template_id', string='Vendor Evaluation Template Line')

class VendorEvaluationTemplateLine(models.Model):
    _name = 'vendor.evaluation.template.line'
    _description = 'Details Vendor Evaluation Template'

    evaluation_template_id = fields.Many2one('vendor.evaluation.template', string='Evaluation Template', ondelete="cascade")
    name = fields.Char(string='Name', required=True)
