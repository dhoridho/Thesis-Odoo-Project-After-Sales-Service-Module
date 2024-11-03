from odoo import models, fields, api, _


class MrpEstimatedCost(models.Model):
    _inherit = 'mrp.estimated.cost'

    type = fields.Selection(selection_add=[
        ('subcontracting', 'Subcontracting')
    ], ondelete={'subcontracting': 'cascade'})
