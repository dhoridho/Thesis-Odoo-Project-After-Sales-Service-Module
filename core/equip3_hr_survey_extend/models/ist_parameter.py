from odoo import fields, models, api

class IstParameterRoot(models.Model):
    _name = 'ist.parameter.root'
    _order = 'sequence'
    _rec_name = 'parameter'
    sequence = fields.Integer("Sequence")
    parameter = fields.Char()
    code = fields.Char()
    description = fields.Char()
