from odoo import models,api,fields,_

class IstScoringGesamt(models.Model):
    _name = 'ist.scoring.gesamt'
    
    name = fields.Char()
    age_from = fields.Integer('Age From')
    age_to = fields.Integer('Age To')
    line_ids = fields.One2many('ist.scoring.gesamt.line','parent_id')

class IstScoringGesamtLine(models.Model):
    _name = 'ist.scoring.gesamt.line'
    
    parent_id = fields.Many2one('ist.scoring.gesamt')
    row_score = fields.Integer()
    score = fields.Float()