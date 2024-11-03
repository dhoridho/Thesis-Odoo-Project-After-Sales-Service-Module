from odoo import models, fields, api, _


class OtherActivityRecord(models.Model):
    _inherit = 'agriculture.daily.activity.record'

    daily_activity_type = fields.Selection(selection_add=[('other', 'Other Activity')], ondelete={'other': 'cascade'})
