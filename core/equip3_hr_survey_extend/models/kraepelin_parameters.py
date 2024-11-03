from odoo import fields, models, api


class KraepelinPankerScoring(models.Model):
    _name = 'kraepelin.panker.parameter'
    _description = 'Kraepelin Panker Scoring'

    name = fields.Char(string='Name')
    description = fields.Text(string='Description')
    score_from = fields.Float(string='Score From')
    score_to = fields.Float(string='Score To')


class KraepelinTiankerScoring(models.Model):
    _name = 'kraepelin.tianker.parameter'
    _description = 'Kraepelin Tianker Scoring'

    name = fields.Char(string='Name')
    description = fields.Text(string='Description')
    score_from = fields.Float(string='Score From')
    score_to = fields.Float(string='Score To')


class KraepelinJankerScoring(models.Model):
    _name = 'kraepelin.janker.parameter'
    _description = 'Kraepelin Janker Scoring'

    name = fields.Char(string='Name')
    description = fields.Text(string='Description')
    score_from = fields.Float(string='Score From')
    score_to = fields.Float(string='Score To')


class KraepelinHankerScoring(models.Model):
    _name = 'kraepelin.hanker.parameter'
    _description = 'Kraepelin Hanker Scoring'

    name = fields.Char(string='Name')
    description = fields.Text(string='Description')
    score_from = fields.Float(string='Score From')
    score_to = fields.Float(string='Score To')
