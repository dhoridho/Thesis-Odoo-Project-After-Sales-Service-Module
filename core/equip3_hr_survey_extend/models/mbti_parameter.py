from odoo import fields, models, api

class MbtiParameterRoot(models.Model):
    _name = 'mbti.parameter.root'
    _description = 'MBTI Parameter Root'
    _order = 'sequence'

    sequence = fields.Integer("Sequence")
    name = fields.Char(string='Personality')
    description = fields.Text(string='Description')
    advice_and_self_development = fields.Text(string='Advice and Self Development')
    suitable_profession = fields.Char(string='Suitable Profession')
    famous_figure = fields.Text(string='Famous Figure')
    representation = fields.Image(string='Representation')
    frequency_in_population = fields.Float(string='Population')
    job_position = fields.Many2many('hr.job', string='Job Suggestions')

class MbtiVariable(models.Model):
    _name = 'mbti.variable'
    _description = 'MBTI Variables'
    _order = 'sequence'

    sequence = fields.Integer("Sequence")
    name = fields.Char(string='Variable')
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
