from odoo import models, fields, api, _


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    bom_product_tmpl_id = fields.Many2one(related='bom_id.product_tmpl_id')
    max_production = fields.Float(compute='_compute_max_production', string='Max Production')

    @api.depends_context('dayofweek')
    @api.depends('workcenter_id', 'workcenter_id.time_start', 'workcenter_id.time_stop', 'time_cycle_manual', 
    'workcenter_id.resource_calendar_id', 'workcenter_id.resource_calendar_id.hours_per_day', 'workcenter_id.resource_calendar_id.attendance_ids', 'workcenter_id.resource_calendar_id.attendance_ids.dayofweek', 'workcenter_id.resource_calendar_id.attendance_ids.hour_from', 'workcenter_id.resource_calendar_id.attendance_ids.hour_to')
    def _compute_max_production(self):
        for record in self:
            workcenter = record.workcenter_id
            resource = workcenter.resource_calendar_id
            cycle_time = record.time_cycle_manual

            max_production = 0
            if cycle_time:
                dayofweek = self.env.context.get('dayofweek', False)
                if dayofweek:
                    attendances = resource.attendance_ids.filtered(lambda o: o.dayofweek == str(dayofweek))
                    total_hours = 0
                    if attendances:
                        total_hours = sum(att.hour_to - att.hour_from for att in attendances)
                else:
                    total_hours = resource.hours_per_day
                max_production = ((total_hours * 60) - (workcenter.time_start + workcenter.time_stop)) / cycle_time
            record.max_production = int(max_production)
