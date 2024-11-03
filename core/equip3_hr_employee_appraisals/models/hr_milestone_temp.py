# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrMilestoneTemplate(models.Model):
    _name = 'hr.milestone.temp'
    _description = 'HR Milestone Template'

    name = fields.Char('Name')
    predecessor_successor_type = fields.Selection([('start_to_start', 'Start to Start'), ('finish_to_start', 'Finish to Start')], default='start_to_start', string='Predecessor & Successor Type')
    milestone_line_ids = fields.One2many('hr.milestone.temp.line','parent_id', string="Milestone Area")

class HrMilestoneTemplateLine(models.Model):
    _name = 'hr.milestone.temp.line'
    _description = 'HR Milestone Template Line'

    parent_id = fields.Many2one('hr.milestone.temp')
    sequence = fields.Integer("Sequence")
    name = fields.Char('Milestone Name')
    weightage = fields.Float('Weightage')