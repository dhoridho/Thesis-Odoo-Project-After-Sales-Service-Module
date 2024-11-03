from odoo import api, fields, models


class IstScoringIq(models.Model):
    _name = 'ist.scoring.iq'

    survey_user_input = fields.Many2one('survey.user_input', ondelete='cascade')
    score = fields.Integer(string='')
    iq = fields.Integer(string='')
    
