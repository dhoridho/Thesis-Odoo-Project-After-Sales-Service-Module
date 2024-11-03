from odoo import api, fields, models


class IstMindsetProfileResult(models.Model):
    _name = 'ist.mindset.profile.result'

    survey_user_input = fields.Many2one('survey.user_input', ondelete='cascade')
    category = fields.Char("")
    result = fields.Char("")
    description = fields.Char("")
    
