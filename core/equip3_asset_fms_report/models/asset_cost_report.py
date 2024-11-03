
from odoo import api, fields, models


class AssetCostReport(models.Model):
    _inherit = 'maintenance.equipment'

    total_price = fields.Float(string="Total Price")
    maintenance_work_order = fields.Many2one('maintenance.work.order', string="Maintenance Work Order",
    store=True, tracking=True)
    maintenance_repair_order = fields.Many2one('maintenance.repair.order', string="Maintenance Repair Order",
                                               store=True, tracking=True)


class VehicleCostReport(models.Model):
    _inherit = 'maintenance.equipment'

    total_price = fields.Float(string="Total Price")