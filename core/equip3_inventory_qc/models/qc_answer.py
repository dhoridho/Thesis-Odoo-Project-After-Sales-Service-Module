# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ChecksheetDimensions(models.Model):
    _name = 'qc.checksheet.answer'
    _description = 'Checksheet Answer'

    name = fields.Char('Answer Name')
    is_answer = fields.Boolean('Correct Answer')
    item_id = fields.Many2one('qc.checksheet.items', string='Item')
