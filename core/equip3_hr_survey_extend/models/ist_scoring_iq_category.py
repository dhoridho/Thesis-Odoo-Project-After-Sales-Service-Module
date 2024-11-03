from odoo import api, fields, models


class IstScoringIqCategory(models.Model):
    _name = 'ist.scoring.iq.category'

    name = fields.Char(string='Category')
    score_from = fields.Integer()
    score_to = fields.Integer()
    
