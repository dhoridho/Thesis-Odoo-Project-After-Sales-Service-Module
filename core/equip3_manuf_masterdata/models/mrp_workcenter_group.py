from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class MrpWorkCenterGroup(models.Model):
    _name = 'mrp.workcenter.group'
    _description = 'Work Center Group'
    _inherit = 'mail.thread'

    code = fields.Char('Group Code', required=True, tracking=True)
    name = fields.Char('Group Name', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, tracking=True, default=lambda self: self.env.company)
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], tracking=True)
    workcenter_ids = fields.Many2many('mrp.workcenter', string='Workcenters')
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    next_workcenter_id = fields.Many2one('mrp.workcenter', string='Next Workcenter', compute='_compute_next_workceter')

    @api.depends('workcenter_ids')
    def _compute_next_workceter(self):
        for record in self:
            next_workcenter = record.workcenter_ids._get_first_available()
            record.next_workcenter_id = next_workcenter.id or next_workcenter._origin.id

    @api.constrains('workcenter_ids')
    def _constrains_workcenters(self):
        for group in self:
            if not group.workcenter_ids:
                raise ValidationError(_('The list of work centers can not be empty!'))
