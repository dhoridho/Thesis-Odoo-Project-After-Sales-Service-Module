from odoo import models, fields, api


class MrpWorkcenterProductivity(models.Model):
    _inherit = 'mrp.workcenter.productivity'

    @api.depends('production_id', 'production_id.warehouse_id', 'workorder_id', 'workorder_id.warehouse_id')
    def _compute_warehouse_id(self):
        for record in self:
            record.warehouse_id = False
            production_id = record.production_id
            workorder_id = record.workorder_id
            if workorder_id:
                if workorder_id.warehouse_id:
                    record.warehouse_id = workorder_id.warehouse_id.id
            if production_id:
                if production_id.warehouse_id:
                    record.warehouse_id = production_id.warehouse_id.id

    warehouse_id = fields.Many2one('stock.warehouse', string='Warhouse', compute=_compute_warehouse_id, store=True)
