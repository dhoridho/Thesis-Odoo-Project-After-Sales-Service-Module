from odoo import models, fields, api, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    mps_production_id = fields.Many2one('equip.mps.production', string='MPS Production')
    mps_start_date = fields.Date(string='MPS Start Date')
    mps_end_date = fields.Date(string='MPS End Date')
