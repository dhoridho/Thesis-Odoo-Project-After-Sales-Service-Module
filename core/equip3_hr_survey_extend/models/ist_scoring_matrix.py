from odoo import models,api,_,fields


class Equip3SurveyIstScoringMatrix(models.Model):
    _name = 'ist.scoring.matrix'
    
    code = fields.Integer()
    age = fields.Char()
    age_from = fields.Integer('Age From')
    age_to = fields.Integer('Age To')
    ist_age_line_ids = fields.One2many('ist.age.line','scoring_parent_id')
    
    
    
class Equip3SurveyIstAgeLine(models.Model):
    _name = 'ist.age.line'
    
    scoring_parent_id = fields.Many2one('ist.scoring.matrix', ondelete='cascade')
    score = fields.Integer()
    satzerganzng = fields.Float()
    worthausuahi = fields.Float()
    analogien = fields.Float()
    gmeisamkeiten = fields.Float()
    rachen_aufgaben = fields.Float()
    zahlen_reihen = fields.Float()
    form_ausuahi = fields.Float()
    wurfal_augaben = fields.Float()
    merk_aufgaben = fields.Float()
