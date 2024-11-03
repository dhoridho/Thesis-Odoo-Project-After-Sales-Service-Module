from odoo import api, fields, models


class IstScoringFinalResult(models.Model):
    _name = 'ist.scoring.final.result'

    survey_user_input = fields.Many2one('survey.user_input', ondelete='cascade')
    total_rw = fields.Integer()
    gesamt_score = fields.Integer()
    iq_score = fields.Integer()
    iq_category = fields.Char("Category")
    dominance = fields.Char("Dominance")
    mindset = fields.Char("")
    
