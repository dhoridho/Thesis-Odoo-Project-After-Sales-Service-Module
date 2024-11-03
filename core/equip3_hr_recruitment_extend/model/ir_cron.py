from odoo import fields, models, api
from datetime import datetime, timedelta


class hashMicroInheritIrCron(models.Model):
    _inherit = 'ir.cron'
    survey_id = fields.Many2one('survey.survey')
    stage_id = fields.Many2one('hr.recruitment.stage')
    