from odoo import api, fields, models


class IstScoringCategory(models.Model):
    _name = 'ist.scoring.category'

    name = fields.Char(string='Name')
    score_from = fields.Integer()
    score_to = fields.Integer()

    
