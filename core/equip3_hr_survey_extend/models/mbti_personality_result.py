from odoo import fields, models, api

class MbtiPersonalityResult(models.Model):
    _name = 'mbti.personality.result'
    _description = 'MBTI Personality Result'

    survey_user_input = fields.Many2one('survey.user_input', ondelete='cascade')
    name = fields.Char(string='Personality')
    code = fields.Selection(string='Code', selection=[
        ('e', 'E'),
        ('f', 'F'),
        ('i', 'I'),
        ('j', 'J'),
        ('n', 'N'),
        ('p', 'P'),
        ('s', 'S'),
        ('t', 'T'),
    ])
    description = fields.Text(string='Description')
