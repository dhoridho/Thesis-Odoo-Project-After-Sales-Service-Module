from odoo import models, fields, api


class MiningProductionRecord(models.Model):
    _inherit = 'mining.production.record'

    operation_type = fields.Selection(related='mining_operation_id.operation_type_id', string='Operation Type', store=True, depends=['mining_operation_id'])
