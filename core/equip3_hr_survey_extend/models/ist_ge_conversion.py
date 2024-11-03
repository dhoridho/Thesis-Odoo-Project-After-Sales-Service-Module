from odoo import api, fields, models


class IstGeConversion(models.Model):
    _name = 'ist.ge.conversion'

    name = fields.Char(string='Name')
    ist_ge_conversion_line_ids = fields.One2many('ist.ge.conversion.line', 'score_parent_id')

class IstGeConvertionLine(models.Model):
    _name = 'ist.ge.conversion.line'

    score_parent_id = fields.Many2one('ist.ge.conversion')
    actual_score = fields.Float()
    converted_score = fields.Float()
