from odoo import fields, models, api

class MbtiDimensionalScore(models.Model):
    _name = 'mbti.dimensional.score'
    _description = 'MBTI Dimensional Score'

    name = fields.Char(string='Personality')
    score = fields.Float(string='Score')
    survey_user_input = fields.Many2one(
        comodel_name='survey.user_input',
        ondelete='cascade',
        string="User Input"
    )
    
