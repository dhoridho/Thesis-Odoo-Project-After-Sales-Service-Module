from odoo import fields, models, api

class MbtiFinalResult(models.Model):
    _name = 'mbti.final.result'
    _description = 'MBTI Final Result'

    survey_user_input = fields.Many2one('survey.user_input', ondelete='cascade')
    name = fields.Char(string='Personality')
    description = fields.Text(string='Description')
    advice_and_self_development = fields.Text(string='Advice and Self Development')
    suitable_profession = fields.Char(string='Suitable Profession')
    famous_figure = fields.Char(string='Famous Figure')
    job_position = fields.Many2many(comodel_name='hr.job', string='Job Suggestions')
    population = fields.Char(string='Population')
    representation = fields.Binary(string='Representation')
    