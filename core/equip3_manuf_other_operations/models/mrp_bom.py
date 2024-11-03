from odoo import models, fields, api, _
from collections import defaultdict


class MrpBoM(models.Model):
    _inherit = 'mrp.bom'

    max_production = fields.Float(compute='_compute_max_duration', string='Max Duration')

    @api.depends_context('dayofweek')
    def _compute_max_duration(self):
        dayofweek = self.env.context.get('dayofweek', False)
        if not dayofweek:
            self.max_production = 0
            return
        
        for record in self:
            group = defaultdict(lambda: self.env['mrp.bom.line'])
            for bom_line  in record.bom_line_ids:
                operation = bom_line.operation_id
                workcenter = operation._get_workcenter()
                group[workcenter] |= bom_line

            wc_max_production = []
            for workcenter, bom_lines in group.items():
                attendances = workcenter.resource_calendar_id.attendance_ids.filtered(lambda o: o.dayofweek == dayofweek)
                total_hours = 0.0
                if attendances:
                    total_hours = sum(att.hour_to - att.hour_from for att in attendances)
                total_minutes = total_hours * 60

                minutes_left = total_minutes
                count = 0
                while True:
                    for bom_line  in bom_lines:
                        duration = bom_line.operation_id.time_cycle_manual
                        minutes_left -= duration
                    if minutes_left < 0.0:
                        break
                    count += 1
                wc_max_production += [count]

            record.max_production = wc_max_production and min(wc_max_production) or 0.0
