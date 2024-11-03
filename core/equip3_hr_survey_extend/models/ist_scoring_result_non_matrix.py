from odoo import api, fields, models


class IstScoringResultNonMatrix(models.Model):
    _name = 'ist.scoring.result.nonmatrix'

    survey_user_input = fields.Many2one('survey.user_input')
    score_se = fields.Float()
    score_wa = fields.Float()
    score_an = fields.Float()
    score_ge_converted = fields.Float()
    score_ra = fields.Float()
    score_zr = fields.Float()
    score_fa = fields.Float()
    score_wu = fields.Float()
    score_me = fields.Float()
