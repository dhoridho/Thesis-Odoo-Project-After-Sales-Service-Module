from odoo import models,api,_,fields


class equip3SurveyEppsPersonality(models.Model):
    _name = 'survey.epps_personality'
    
    sequence = fields.Integer()
    code = fields.Char()
    personality = fields.Char()
    description = fields.Text()