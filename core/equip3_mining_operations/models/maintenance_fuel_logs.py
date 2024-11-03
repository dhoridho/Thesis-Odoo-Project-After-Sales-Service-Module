from odoo import models, fields


class MaintenanceFuelLogs(models.Model):
    _inherit = 'maintenance.fuel.logs'

    mining_prod_act_id = fields.Many2one(comodel_name='mining.production.actualization', string='Mining Production Actualization')
    mining_fuel_id = fields.Many2one(comodel_name='mining.production.plan.fuel', string='Mining Fuel')
