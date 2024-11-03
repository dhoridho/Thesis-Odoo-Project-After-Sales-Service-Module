# -*- coding: utf-8 -*-

from odoo import models, fields, api

class QuantitativeLines(models.TransientModel):
    _name = 'wiz.qc.quantitative.lines'
    _description = 'Quantitative Lines'

    sequence = fields.Integer("No")
    dimansion_id = fields.Many2one('checksheet.dimensions', string="Dimensions")
    norm_qc = fields.Float(string="Norm")
    tolerance_from_qc = fields.Float(string="Tolerance From")
    tolerance_to_qc = fields.Float(string="Tolerance To")
    actual_value = fields.Float(string="Actual")
    text = fields.Char(string="Text")
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')])
    wiz_line_id = fields.Many2one('sh.stock.move.global.check', string="Wiz Line")
    is_result = fields.Boolean(string='Is Result', related='wiz_line_id.is_result')

class QuantitativeLines(models.TransientModel):
    _name = 'wiz.qc.qualitative.lines'
    _description = 'Qualitative Lines'

    sequence = fields.Integer("No")
    item_id = fields.Many2one('qc.checksheet.items', string="Item")
    answer = fields.Many2one('qc.checksheet.answer', string="Answer", domain="[('item_id', '=', item_id)]")
    text = fields.Char(string="Text")
    status = fields.Selection([('pass', 'Passed'), ('fail', 'Failed')])
    wiz_line_id = fields.Many2one('sh.stock.move.global.check', string="Wiz Line")
    is_result = fields.Boolean(string='Is Result', related='wiz_line_id.is_result')
