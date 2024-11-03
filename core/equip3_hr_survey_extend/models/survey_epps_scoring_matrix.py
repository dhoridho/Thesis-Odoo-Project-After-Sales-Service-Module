from odoo import models,api,_,fields


class Equip3SurveyEppsScoringMatrix(models.Model):
    _name = 'survey.epps.scoring.matrix'
    
    code = fields.Integer()
    name = fields.Char()
    scoring_matrix_line_ids = fields.One2many('survey.epps.scoring.matrix.line','scoring_parent_id')
    
    
    
class Equip3SurveyEppsScoringMatrixLine(models.Model):
    _name = 'survey.epps.scoring.matrix.line'
    
    scoring_parent_id = fields.Many2one('survey.epps.scoring.matrix')
    score = fields.Integer()
    achievement = fields.Integer()
    deference = fields.Integer()
    order = fields.Integer()
    exhibition = fields.Integer()
    autonomy = fields.Integer()
    affiliation = fields.Integer()
    intraception = fields.Integer()
    succorance = fields.Integer()
    dominance = fields.Integer()
    abasement = fields.Integer()
    nurturance = fields.Integer()
    change = fields.Integer()
    endurance = fields.Integer()
    heterosextuality = fields.Integer()
    aggression = fields.Integer()
    consistency = fields.Integer()
    