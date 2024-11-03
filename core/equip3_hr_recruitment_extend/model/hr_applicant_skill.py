from odoo import fields,models,api

class HrApplicantSkill(models.Model):
    _name = 'hr.applicant.skill'

    skill_type_id = fields.Many2one("hr.skill.type","Skill Type")
    skill_id = fields.Many2one("hr.skill","Skill")
    skill_level_id = fields.Many2one("hr.skill.level","Skill Level")
    applicant_id = fields.Many2one("hr.applicant","Applicant")


