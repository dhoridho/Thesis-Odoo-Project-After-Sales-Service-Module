from odoo import fields,api, models, _
from odoo.exceptions import ValidationError
from operator import itemgetter
from datetime import datetime, date

class CrmTarget(models.Model):
    _inherit = 'crm.target'

    percentage_target = fields.Float("Percentage (%)", compute="_get_percentage", store=True)

    @api.depends('main_target','current_achievement')
    def _get_percentage(self):
        for rec in self:
            percentage = 0
            if rec.main_target:
                percentage = (rec.current_achievement * 100) / rec.main_target
            rec.percentage_target = percentage