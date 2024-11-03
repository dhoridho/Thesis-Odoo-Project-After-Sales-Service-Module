from odoo import models, fields, api


class MrpPlan(models.Model):
    _inherit = 'mrp.plan'

    consumption_ids = fields.One2many('mrp.consumption', 'manufacturing_plan', string='Production Records', readonly=True)
