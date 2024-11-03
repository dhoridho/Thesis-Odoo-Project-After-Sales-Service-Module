# -*- coding: utf-8 -*-

from odoo import models, fields, api


class QuantitativeLines(models.Model):
    _name = 'qc.quantitative.lines'
    _description = 'Quantitative Lines'

    sequence = fields.Integer("No")
    dimansion_id = fields.Many2one(
        'checksheet.dimensions', string="Dimensions")
    norm_qc = fields.Float(string="Norm")
    tolerance_from_qc = fields.Float(string="Tolerance From")
    tolerance_to_qc = fields.Float(string="Tolerance To")
    actual_value = fields.Float(string="Actual")
    text = fields.Char(string="Text")
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')])
    quantitative_lines_ids = fields.Many2one(
        'sh.quality.check', string="Check Line")


class QuantitativeLines(models.Model):
    _name = 'qc.qualitative.lines'
    _description = 'Qualitative Lines'

    sequence = fields.Integer("No")
    item_id = fields.Many2one('qc.checksheet.items', string="Item")
    answer = fields.Many2one(
        'qc.checksheet.answer', string="Answer", domain="[('item_id', '=', item_id)]")
    text = fields.Char(string="Text")
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')])
    qualitative_lines_ids = fields.Many2one(
        'sh.quality.check', string="Check Line Quality")
