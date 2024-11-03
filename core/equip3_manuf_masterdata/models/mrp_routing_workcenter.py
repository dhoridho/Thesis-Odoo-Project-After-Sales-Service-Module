from odoo import models, fields, api
from odoo.exceptions import ValidationError, AccessError

class WorkCenterOperation(models.Model):
    _inherit = 'mrp.routing.workcenter'

    @api.depends('workcenter_type', 'workcenter_group_id', 'workcenter_id')
    def _compute_operation_name(self):
        for record in self:
            name = ''
            if record.workcenter_type == 'with_group':
                name = record.workcenter_group_id.name
            else:
                if record.workcenter_id:
                    name = record.workcenter_id.name
            record.operation_name = name

    def _compute_workcenters(self):
        for record in self:
            workcenter_ids = record.workcenter_id
            if record.workcenter_type == 'with_group':
                workcenter_ids = record.workcenter_group_id.workcenter_ids
            record.workcenter_ids = [(6, 0, workcenter_ids.ids)]
    
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], required=True)
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center', required=False, domain="['|', ('branch_id', '=', False), ('branch_id', '=', branch_id), '|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    workcenter_ids = fields.Many2many('mrp.workcenter', string='Work Centers', compute=_compute_workcenters)
    location_id = fields.Many2one(related='workcenter_id.location_id')
    workcenter_type = fields.Selection([
        ('with_group', 'With Group'),
        ('without_group', 'Without Group'),
    ], string='Type', default='without_group')
    is_branch_filled = fields.Boolean('Branch Check', default=True)

    @api.onchange('is_branch_filled')
    def onchange_branch_filled(self):
        self.is_branch_filled = False
        if not self.bom_id.branch_id:
            raise ValidationError('Please fill the Branch field')


    workcenter_group_id = fields.Many2one('mrp.workcenter.group', string='Work Center Group', domain="['|', ('branch_id', '=', False), ('branch_id', '=', branch_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    operation_name = fields.Char(compute=_compute_operation_name)

    def _get_workcenter(self):
        self.ensure_one()
        if self.workcenter_type == 'with_group':
            workcenter_ids = self.workcenter_group_id.workcenter_ids
            workorder_id = self.env['mrp.workorder'].search([
                ('workcenter_id', 'in', workcenter_ids.ids),
                ('date_planned_finished', '!=', False)
            ], order='date_planned_finished desc', limit=1)
            return workorder_id and workorder_id.workcenter_id or workcenter_ids[0]
        return self.workcenter_id

    @api.onchange('workcenter_type')
    def _onchange_workcenter_type(self):
        if self.workcenter_type == 'with_group':
            self.workcenter_id = False
