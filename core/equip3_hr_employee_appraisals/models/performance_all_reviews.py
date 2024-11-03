# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from lxml import etree

class PerformanceAllReviews(models.Model):
    _name = 'performance.all.reviews'
    _description = 'All Reviews'

    name = fields.Char("Name")
    ## Manager ##
    is_included_manager = fields.Boolean("Is Included")
    manager_feedback_template_id = fields.Many2one('survey.survey', string="Feedback Template", domain="[('survey_type','=','peer_review')]")
    manager_weightage = fields.Float("Weightage")
    manager_max_reviewer = fields.Integer("Maximal Reviewer")
    ## Subordinate ##
    is_included_subordinate = fields.Boolean("Is Included")
    subordinate_feedback_template_id = fields.Many2one('survey.survey', string="Feedback Template", domain="[('survey_type','=','peer_review')]")
    subordinate_weightage = fields.Float("Weightage")
    subordinate_max_reviewer = fields.Integer("Maximal Reviewer")
    ## Peer ##
    is_included_peer = fields.Boolean("Is Included")
    peer_weightage = fields.Float("Weightage")
    peer_max_reviewer = fields.Integer("Maximal Reviewer")
    peer_reviewer_position_ids = fields.One2many('performance.all.reviews.peer.reviewer','parent_id')
    ## External ##
    is_included_external = fields.Boolean("Is Included")
    external_feedback_template_id = fields.Many2one('survey.survey', string="Feedback Template", domain="[('survey_type','=','peer_review')]")
    external_weightage = fields.Float("Weightage")
    external_max_reviewer = fields.Integer("Maximal Reviewer")
    
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(PerformanceAllReviews, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)   
        elif self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res
    
    

    @api.constrains('is_included_manager','manager_weightage','is_included_subordinate','subordinate_weightage','is_included_peer','peer_weightage','is_included_external','external_weightage')
    def _check_weightage(self):
        for rec in self:
            total_weightage = 0
            if rec.is_included_manager and rec.manager_weightage > 0:
                total_weightage += rec.manager_weightage
            if rec.is_included_subordinate and rec.subordinate_weightage > 0:
                total_weightage += rec.subordinate_weightage
            if rec.is_included_peer and rec.peer_weightage > 0:
                total_weightage += rec.peer_weightage
            if rec.is_included_external and rec.external_weightage > 0:
                total_weightage += rec.external_weightage
            
            if total_weightage > 100:
                raise ValidationError(_('Total Weightage must be no more than 100%!'))
    
    @api.constrains('is_included_manager','manager_max_reviewer')
    def _check_manager_max_reviewer(self):
        for rec in self:
            if rec.is_included_manager and rec.manager_max_reviewer < 1:
                raise ValidationError(_('There must be at least 1 person for Maximal Reviewer for [Manager]!'))
    
    @api.constrains('is_included_subordinate','subordinate_max_reviewer')
    def _check_subordinate_max_reviewer(self):
        for rec in self:
            if rec.is_included_subordinate and rec.subordinate_max_reviewer < 1:
                raise ValidationError(_('There must be at least 1 person for Maximal Reviewer for [Subordinate]!'))
    
    @api.constrains('is_included_peer','peer_max_reviewer')
    def _check_peer_max_reviewer(self):
        for rec in self:
            if rec.is_included_peer and rec.peer_max_reviewer < 1:
                raise ValidationError(_('There must be at least 1 person for Maximal Reviewer for [Peer]!'))
    
    @api.constrains('is_included_external','external_max_reviewer')
    def _check_external_max_reviewer(self):
        for rec in self:
            if rec.is_included_external and rec.external_max_reviewer < 1:
                raise ValidationError(_('There must be at least 1 person for Maximal Reviewer for [External]!'))

class PerformanceAllReviewsPeerReviewer(models.Model):
    _name = 'performance.all.reviews.peer.reviewer'

    parent_id = fields.Many2one('performance.all.reviews')
    job_position_ids = fields.Many2many('hr.job', string="Job Position")
    feedback_template_id = fields.Many2one('survey.survey', string="Feedback Template", domain="[('survey_type','=','peer_review')]")