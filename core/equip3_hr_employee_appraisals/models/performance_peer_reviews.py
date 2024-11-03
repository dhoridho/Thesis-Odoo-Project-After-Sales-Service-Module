# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PerformancePeerReviews(models.Model):
    _name = 'performance.peer.reviews'
    _description = 'Performance Reviews'

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
    peer_feedback_template_id = fields.Many2one('survey.survey', string="Feedback Template", domain="[('survey_type','=','peer_review')]")
    peer_weightage = fields.Float("Weightage")
    peer_max_reviewer = fields.Integer("Maximal Reviewer")
    ## External ##
    is_included_external = fields.Boolean("Is Included")
    external_feedback_template_id = fields.Many2one('survey.survey', string="Feedback Template", domain="[('survey_type','=','peer_review')]")
    external_weightage = fields.Float("Weightage")
    external_max_reviewer = fields.Integer("Maximal Reviewer")

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