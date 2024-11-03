from odoo import models, fields, api, _


class AgricultureWorkerGroup(models.Model):
    _name = 'agriculture.worker.group'
    _description = 'Worker Group'

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.branch.id if len(self.env.branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids)]
    
    name = fields.Char(required=True)
    head_id = fields.Many2one('hr.employee', string='Head of Group', required=True, domain="[('is_agri_worker', '=', True)]")
    worker_ids = fields.Many2many('hr.employee', string='Workers', required=True, domain="[('is_agri_worker', '=', True)]")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch)
