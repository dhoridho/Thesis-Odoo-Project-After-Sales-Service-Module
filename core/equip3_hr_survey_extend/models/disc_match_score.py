from odoo import fields,models,api



class DiscPersonalityRoot(models.Model):
    _name = 'disc.match.score'
    
    
    
    name = fields.Char()
    match_score = fields.Integer()
    user_input_id = fields.Many2one('survey.user_input')
   