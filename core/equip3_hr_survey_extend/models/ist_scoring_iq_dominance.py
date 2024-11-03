from odoo import api, fields, models


class IstScoringIqDominance(models.Model):
    _name = 'ist.scoring.iq.dominance'

    name = fields.Char(string='Name')
    description = fields.Char()
    score_from = fields.Integer()
    score_to = fields.Integer()
    
