from odoo import api, fields, models, _



class HashmicroSurveyInputLine(models.Model):
    _inherit = "survey.user_input.line"
    applicant_id = fields.Many2one('hr.applicant')
