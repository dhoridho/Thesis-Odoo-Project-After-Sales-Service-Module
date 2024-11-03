from odoo import models


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    # override equip3_manuf_masterdata
    def _get_workcenter(self):
        self.ensure_one()
        if self.workcenter_type == 'with_group':
            group_workcenters = self.workcenter_group_id.workcenter_ids
            not_blocked_workcenters = group_workcenters.filtered(lambda w: w.state != 'blocked')

            # all workcenters is blocked
            if not not_blocked_workcenters:
                return group_workcenters[0]

            # exact 1 workcenter isn't blocked
            if len(not_blocked_workcenters) == 1:
                return not_blocked_workcenters[0]

            available_workcenters = not_blocked_workcenters.filtered(lambda w: w.state == 'available')

            # has available workcenter
            if available_workcenters:
                return available_workcenters[0]
            
            # shortest time waiting
            finish_time = {}
            for workcenter in not_blocked_workcenters:
                sorted_orders = sorted(workcenter.order_ids.filtered(lambda o: o.date_planned_finished), key=lambda w: w.date_planned_finished)
                if not sorted_orders:
                    return workcenter
                finish_time[workcenter] = sorted_orders[-1] # last finished order
            return sorted(finish_time.items(), key=lambda o: o[1].date_planned_finished)[0][0] # early finished
        
        return self.workcenter_id
