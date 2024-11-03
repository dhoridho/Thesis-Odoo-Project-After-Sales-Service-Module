from odoo import fields, models, api

class PapikostickParameterRoot(models.Model):
    _name = 'papikostick.parameter.root'
    _order = 'sequence'
    _rec_name = 'parameter'
    sequence = fields.Integer("Sequence")
    parameter = fields.Char()
    parameter_ids = fields.One2many('papikostick.parameter.line','papikostick_parameter_root')


class PapikostickParameterLine(models.Model):
    _name = 'papikostick.parameter.line'
    parameter_line = fields.Char()
    code = fields.Char()
    description = fields.Char()
    papikostick_parameter_root = fields.Many2one('papikostick.parameter.root')
