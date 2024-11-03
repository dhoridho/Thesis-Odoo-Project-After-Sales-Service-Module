from odoo import models, fields, api, _


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    resource_calendar_id = fields.Many2one(
        'resource.calendar', default=lambda self: self.env.company.mrp_resource_calendar_id)
