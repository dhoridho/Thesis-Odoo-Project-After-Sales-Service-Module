from odoo import api, fields, models


class IstScoringResult(models.Model):
    _name = 'ist.scoring.result'

    survey_user_input = fields.Many2one('survey.user_input', ondelete='cascade')
    parameter = fields.Char("Parameter")
    code = fields.Char("Code")
    rw = fields.Integer()
    sw = fields.Integer()
    description = fields.Text("Description")
    category = fields.Char()