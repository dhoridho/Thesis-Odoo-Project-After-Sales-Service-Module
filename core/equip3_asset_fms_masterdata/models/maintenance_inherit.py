from odoo import api, fields, models

class inherit_plan(models.Model):
    _inherit = 'maintenance.plan'

    maintenance_p_id = fields.Many2one(
        string="Maintenance Plan", comodel_name="maintenance.facilities.area", ondelete="restrict"
    )

