from odoo import fields,models


class equip3ManPowerPlanningType(models.Model):
    _name = "manpower.planning.type"
    _description = "Manpower Plan Type"
    _inherit = ['mail.thread','mail.activity.mixin']
    
    name = fields.Char()