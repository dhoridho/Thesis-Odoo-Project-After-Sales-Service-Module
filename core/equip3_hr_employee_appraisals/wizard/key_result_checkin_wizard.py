# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
import statistics

class HrKeyResulCheckinWizardt(models.TransientModel):
    _name = 'hr.key.result.checkin.wizard'
    _description = 'HR Key Result Checkin Wizard'

    key_result_id = fields.Many2one('hr.key.result', string="Key Result", readonly=True)
    key_result_type = fields.Selection(related='key_result_id.key_result_type')
    goal_title_id = fields.Many2one('hr.goals', string="Goal Title", readonly=True)
    milestone_template_id = fields.Many2one('hr.milestone.temp', string="Milestone Template")
    milestone_id = fields.Many2one('hr.milestone.temp.line', string="Milestone Name", domain="[('parent_id','=',milestone_template_id)]")
    key_result_target = fields.Float('Target', readonly=True)
    actual = fields.Float('Actual')
    achievement = fields.Float('Achievement %', compute="compute_achievement")
    priority = fields.Selection([('high', 'High'), ('low', 'Low'), ('medium', 'Medium')], string='Priority')
    state = fields.Selection([('pending', 'Pending'), ('on_progress', 'On Progress'), ('done', 'Done'), ('hold', 'Hold'),
                              ('canceled', 'Canceled')], string='Status')
    notes = fields.Text('Notes')
    attachment_file = fields.Binary('Attachment')
    attachment_name = fields.Char('Attachment Name')

    @api.onchange('milestone_template_id')
    def _onchange_milestone_template_id(self):
        for rec in self:
            if rec.milestone_template_id:
                milestone_line = [data.name.id for data in self.key_result_id.key_result_milestone_ids.filtered(
                        lambda line: line.actual < line.weightage)]
                return {
                    'domain': {'milestone_id': [('parent_id','=',rec.milestone_template_id.id),('id','in',milestone_line)]},
                }

    @api.onchange('milestone_id')
    def _onchange_milestone_id(self):
        for rec in self:
            if rec.milestone_id:
                rec.key_result_target = rec.milestone_id.weightage
                
                if self.milestone_template_id.predecessor_successor_type == 'finish_to_start':
                    sequence = [data.sequence for data in self.key_result_id.key_result_milestone_ids.filtered(
                        lambda line: line.actual < line.weightage)]
                    if sequence:
                        minimum_sequence = min(sequence)
                        milestone = self.key_result_id.key_result_milestone_ids.filtered(lambda line: line.sequence == minimum_sequence and line.name == self.milestone_id)
                        if not milestone:
                            return {'warning': {'title': 'Warning', 'message': 'Tahap sebelumnya belum 100% (belum selesai)'}}

    @api.depends('key_result_target','actual')
    def compute_achievement(self):
        for rec in self:
            rec.achievement = (rec.actual / rec.key_result_target) * 100 if rec.key_result_target > 0 else 0

    @api.onchange('actual')
    def onchange_actual(self):
        for rec in self:
            if rec.actual >= rec.key_result_target:
                rec.state = 'done'
            elif rec.actual > 0:
                rec.state = 'on_progress'

    def action_save(self):
        history = ""
        if self.key_result_type == "milestone" and self.milestone_id:
            milestone = self.key_result_id.key_result_milestone_ids.filtered(lambda line: line.name == self.milestone_id)
            milestone.actual = self.actual

            history += "Milestone Name: " + self.milestone_id.name + "\n"
            history += "Target: " + str(self.milestone_id.weightage) + "\n"
        if self.key_result_id.actual != self.actual:
            history += "Actual: " + str(self.key_result_id.actual) + " -> " + str(self.actual)
        if self.key_result_id.priority != self.priority:
            history += "\n" + "Priority: " + self.key_result_id.priority + " -> " + self.priority
        if self.key_result_id.state != self.state:
            history += "\n" + "Status: " + self.key_result_id.state + " -> " + self.state
        if self.notes:
            history += "\n" + "Notes: " + self.notes
        if history:
            logbook = [(0, 0, {
                                'history': history,
                                'timestamp': datetime.now(),
                                'actual': self.actual,
                                'attachment_file': self.attachment_file,
                                'attachment_name': self.attachment_name
                                })]
            self.key_result_id.logbook_ids = logbook

        self.key_result_id.actual = self.actual
        self.key_result_id.priority = self.priority
        self.key_result_id.state = self.state
        self.key_result_id.notes = self.notes

        sum_data = sum(self.goal_title_id.key_result_area_ids.mapped("achievement"))

        data_achievement = []
        for data in self.goal_title_id.key_result_area_ids:
            data_achievement.append(data.achievement)
        
        if self.goal_title_id.formula == 'average':
            count = len(self.goal_title_id.key_result_area_ids)
            self.goal_title_id.achievement_score = sum_data / count if count > 0 else 0
        elif self.goal_title_id.formula == 'sum':
            self.goal_title_id.achievement_score = sum_data
        elif self.goal_title_id.formula == 'max':
            self.goal_title_id.achievement_score = max(data_achievement)
        elif self.goal_title_id.formula == 'min':
            self.goal_title_id.achievement_score = min(data_achievement)
        elif self.goal_title_id.formula == 'median':
            self.goal_title_id.achievement_score = statistics.median(data_achievement)

        if self.goal_title_id.goals_parent_id:
            child = self.env['hr.goals.child'].search([('goals_id','=',self.goal_title_id.goals_parent_id.id),('goals_child_id','=',self.goal_title_id.id),('key_result_area_id','=',self.goal_title_id.key_result_area_parent_id.id)], limit=1)
            child.write({'achievement_score': self.goal_title_id.achievement_score})
            goal_child = self.goal_title_id.goals_parent_id.mapped("goal_child_ids").filtered(lambda r: r.key_result_area_id == self.goal_title_id.key_result_area_parent_id)
            sum_score = sum(goal_child.mapped("score"))
            self.goal_title_id.key_result_area_parent_id.write({'actual': sum_score})

            sum_data = sum(self.goal_title_id.goals_parent_id.key_result_area_ids.mapped("achievement"))

            data_achievement = []
            for data in self.goal_title_id.goals_parent_id.key_result_area_ids:
                data_achievement.append(data.achievement)
            
            if self.goal_title_id.goals_parent_id.formula == 'average':
                count = len(self.goal_title_id.goals_parent_id.key_result_area_ids)
                self.goal_title_id.goals_parent_id.achievement_score = sum_data / count if count > 0 else 0
            elif self.goal_title_id.goals_parent_id.formula == 'sum':
                self.goal_title_id.goals_parent_id.achievement_score = sum_data
            elif self.goal_title_id.goals_parent_id.formula == 'max':
                self.goal_title_id.goals_parent_id.achievement_score = max(data_achievement)
            elif self.goal_title_id.goals_parent_id.formula == 'min':
                self.goal_title_id.goals_parent_id.achievement_score = min(data_achievement)
            elif self.goal_title_id.goals_parent_id.formula == 'median':
                self.goal_title_id.goals_parent_id.achievement_score = statistics.median(data_achievement)

            parents = self.env['hr.goals'].get_parent_goal(self.goal_title_id)
            for parent in parents:
                parent_obj = self.env['hr.goals'].search([('id','=',parent)])
                for rec in parent_obj:
                    if rec.goals_parent_id:
                        child = self.env['hr.goals.child'].search([('goals_id','=',rec.goals_parent_id.id),('goals_child_id','=',rec.id),('key_result_area_id','=',rec.key_result_area_parent_id.id)], limit=1)
                        child.write({'achievement_score': rec.achievement_score})
                        goal_child = rec.goals_parent_id.mapped("goal_child_ids").filtered(lambda r: r.key_result_area_id == rec.key_result_area_parent_id)
                        sum_score = sum(goal_child.mapped("score"))
                        rec.key_result_area_parent_id.write({'actual': sum_score})

                        sum_data = sum(rec.goals_parent_id.key_result_area_ids.mapped("achievement"))

                        data_achievement = []
                        for data in rec.goals_parent_id.key_result_area_ids:
                            data_achievement.append(data.achievement)
                            
                        if rec.goals_parent_id.formula == 'average':
                            count = len(rec.goals_parent_id.key_result_area_ids)
                            rec.goals_parent_id.achievement_score = sum_data / count if count > 0 else 0
                        elif rec.goals_parent_id.formula == 'sum':
                            rec.goals_parent_id.achievement_score = sum_data
                        elif rec.goals_parent_id.formula == 'max':
                            rec.goals_parent_id.achievement_score = max(data_achievement)
                        elif rec.goals_parent_id.formula == 'min':
                            rec.goals_parent_id.achievement_score = min(data_achievement)
                        elif rec.goals_parent_id.formula == 'median':
                            rec.goals_parent_id.achievement_score = statistics.median(data_achievement)
                        else:
                            continue