from odoo import models, fields, api


class MrpLaborGroup(models.Model):
    _name = 'mrp.labor.group'
    _description = 'MRP Labor Group'

    name = fields.Char(required=True)
    head_id = fields.Many2one('hr.employee', string='Head of Group', required=True, domain="[('active', '=', True)]")
    labor_ids = fields.Many2many('hr.employee', string='Labors', required=True, domain="[('active', '=', True)]")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    is_branch_required = fields.Boolean(related='company_id.show_branch')
