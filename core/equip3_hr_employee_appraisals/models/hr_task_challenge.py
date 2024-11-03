# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrTaskChallenge(models.Model):
    _name = 'hr.task.challenge'

    name = fields.Char('Name')
    line_ids = fields.One2many('hr.task.challenge.line','parent_id', string="Tasks/Challenges")

class HrTaskChallengeLine(models.Model):
    _name = 'hr.task.challenge.line'

    parent_id = fields.Many2one('hr.task.challenge')
    task_challenge_id = fields.Many2one('survey.survey', string="Tasks/Challenges")
    weightage = fields.Float('Weightage')
    target_score = fields.Float('Target Score')