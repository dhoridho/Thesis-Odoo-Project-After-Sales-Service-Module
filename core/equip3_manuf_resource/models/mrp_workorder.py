from odoo import models, fields, api, _


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    @api.depends('leave_id')
    def _compute_dates_planned(self):
        super(MrpWorkorder, self)._compute_dates_planned()
        for workorder in self:
            workorder.date_planned_start = workorder.leave_id.datetime_from
            workorder.date_planned_finished = workorder.leave_id.datetime_to

    def _set_dates_planned(self):
        super(MrpWorkorder, self)._set_dates_planned()
        date_from = self[0].date_planned_start
        date_to = self[0].date_planned_finished
        self.mapped('leave_id').sudo().write({
            'datetime_from': date_from,
            'datetime_to': date_to
        })
