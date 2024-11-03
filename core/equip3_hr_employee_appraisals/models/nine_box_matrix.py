# from attr import field
from odoo import models,api,fields


class nineBoxMatrix(models.Model):
    _name = 'nine.box.matrix'
    _order = 'sequence'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'category'
    
    sequence = fields.Integer()
    category = fields.Char()
    min_performance_score = fields.Float()
    max_performance_score = fields.Float()
    performance_level = fields.Selection([('low','Low'),('medium','Medium'),('high','High')])
    min_competency_score = fields.Float()
    max_competency_score = fields.Float()
    competency_level = fields.Selection([('low','Low'),('medium','Medium'),('high','High')])
    description = fields.Text()
    suggestion_action = fields.Text()
    number_analysis = fields.Integer("Number Analysis")
    color = fields.Char("Color")