from odoo import models,fields,api

class Equip3RecExtendSurveyQuestion(models.Model):
    _inherit = 'survey.question'
    is_start_date = fields.Boolean(default=False)
    is_end_date = fields.Boolean(default=False)
    is_company_name = fields.Boolean(default=False)
    is_position = fields.Boolean(default=False)
    is_reason_leaving_company  = fields.Boolean(default=False)
    is_how_much_previous_salary = fields.Boolean(default=False)
    is_old_company_phone_number = fields.Boolean(default=False)