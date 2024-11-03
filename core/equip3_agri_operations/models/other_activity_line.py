from odoo import models, fields, api, _


class OtherActivityLine(models.Model):
    _inherit = 'agriculture.daily.activity.line'

    daily_activity_type = fields.Selection(selection_add=[('other', 'Other Activity')], ondelete={'other': 'cascade'})
