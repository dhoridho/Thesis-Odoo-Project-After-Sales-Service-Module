from odoo import models, fields, api
from collections import defaultdict


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    def write(self, vals):
        if self.env.context.get('is_gantt', False):
            if 'date_planned_start' in vals:
                date_planned_start = fields.Datetime.from_string(vals['date_planned_start'])
                
                to_dates = []
                for workorder in self:
                    workcenter = workorder.workcenter_id
                    from_date, to_date = workcenter._get_first_available_slot(date_planned_start, workorder.duration_expected)
                    if to_date:
                        to_dates += [to_date]
                if to_dates:
                    vals['date_planned_finished'] = max(to_dates)
        return super(MrpWorkorder, self).write(vals)

    @api.depends('location_id')
    def _compute_warehouse_id(self):
        for record in self:
            record.warehouse_id = False
            location_id = record.location_id
            if location_id:
                record.warehouse_id = location_id.get_warehouse()

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', compute=_compute_warehouse_id, store=True)
