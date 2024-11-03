# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrConfigSettings(models.Model):
    _name = 'hr.config.settings'
    _description = 'HR Config Settings'

    name = fields.Char(string="Name")
    application_session_timeout = fields.Integer(string="Application Session Timeout (In days)", default=3, help="A user's maximum session time before being automatically logged out. A session timeout must be for at least one (1) day")
    face_distance_limit = fields.Float(string="Face Distance Limit", default=0.4, help="Used as face resemblance limitation parameter")
    use_attendance_formula = fields.Boolean(string="Use Attendance Formula", help="Used to define formulation Attendance on Payroll Calculation")
    applicant_blacklist = fields.Boolean(default=False,help="Automatically Reject new applicant data that has been blacklisted")
    bl_email = fields.Boolean(default=True)
    bl_id_card_number = fields.Boolean(default=True)
    bl_phone_number = fields.Boolean(default=True)
    web_kiosk_pin = fields.Boolean(default=True, help="Used to using Pin on Kiosk Web Attendance")
    split_bank_transfer_approval_matrix = fields.Boolean(string="Split Bank Transfer Approval Matrix", default=True, help="Used to define Approval Matrix Method for Split Bank Transfer Feature")
    sbt_approval_method = fields.Selection(
        [('approval_matrix', 'By Approval Matrix'),('hierarchy', 'By Employee Hierarchy')], default='approval_matrix', string="SBT Approval Method")
    sbt_approval_levels = fields.Integer(string="SBT Approval Levels")

    @api.onchange("application_session_timeout")
    def _onchange_application_session_timeout(self):
        if self.application_session_timeout == 0:
            raise ValidationError(_("Please set value for Application session timeout Field greather than 0"))
        elif self.application_session_timeout < 0:
            raise ValidationError(_("Please only use an Integer value for Application session timeout Field"))
        
    @api.onchange("face_distance_limit")
    def _onchange_face_distance_limit(self):
        if self.face_distance_limit == 0:
            raise ValidationError(_("Please set value for Face Distance Limit Field greather than 0"))
        elif self.face_distance_limit < 0.1:
            raise ValidationError(_("Cannot input Face Distance Limit lower than 0.1"))
        elif self.face_distance_limit > 0.9:
            raise ValidationError(_("Cannot input Face Distance Limit greather than 0.9"))
    
    @api.onchange("sbt_approval_levels")
    def _onchange_sbt_approval_levels(self):
        if self.sbt_approval_levels < 1:
            self.sbt_approval_levels = 1
