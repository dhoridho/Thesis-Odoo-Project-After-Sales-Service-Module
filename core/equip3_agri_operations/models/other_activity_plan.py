from odoo import models, fields, api, _


class OtherActivityPlan(models.Model):
    _inherit = 'agriculture.daily.activity'

    daily_activity_type = fields.Selection(selection_add=[('other', 'Other Activity')], ondelete={'other': 'cascade'})
