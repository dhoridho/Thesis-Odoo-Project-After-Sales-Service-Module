from odoo import models, fields, api


class MrpLaborAssign(models.Model):
    _name = 'mrp.labor.assign'
    _description = 'MRP Labor Assign'

    @api.depends('production_id')
    def _compute_allowed_workorder_ids(self):
        for record in self:
            workorder_ids = record.production_id.workorder_ids
            allowed_workorder_ids = workorder_ids.filtered(lambda w: w.state not in ('done', 'cancel'))
            record.allowed_workorder_ids = [(6, 0, allowed_workorder_ids.ids)]

    plan_id = fields.Many2one('mrp.plan', string='Production Plan', readonly=True)
    production_id = fields.Many2one('mrp.production', string='Production Order', readonly=True)
    allowed_workorder_ids = fields.One2many('mrp.workorder', compute=_compute_allowed_workorder_ids)
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order', required=True, domain="[('id', 'in', allowed_workorder_ids)]", readonly=True)
    labor_id = fields.Many2one('hr.employee', string='Labor', required=True, domain="[('active', '=', True)]", readonly=True)
    workorder_state = fields.Selection(related='workorder_id.state')
