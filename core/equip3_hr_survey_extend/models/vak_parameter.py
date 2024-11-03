from odoo import fields, models, api

class VakParameter(models.Model):
    _name = 'vak.parameter'
    _description = 'VAK Parameter'
    _order = 'sequence'

    sequence = fields.Integer("Sequence")
    name = fields.Char(string='Learning Style')
    description = fields.Text(string='Description')
    strengths = fields.Text(string='Strengths')
    learning_preferences = fields.Text(string='Learning Preferences')
    challenges = fields.Text(string='Challenges')
    vak_code = fields.Char("VAK Code")