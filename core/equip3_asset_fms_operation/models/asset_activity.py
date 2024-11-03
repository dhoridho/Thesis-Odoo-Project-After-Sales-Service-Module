from odoo import models, fields, api, _

class AssetActivity(models.Model):
    _name = 'asset.activity'
    _description = 'Asset Activity'

    name = fields.Char(string='Activity Name', required=True)
    activity_type = fields.Selection(string='Activity Type', selection=[('operative', 'Operative'), ('idle', 'Idle'), ('breakdown', 'Breakdown'), ('maintenance', 'Maintenance'),  ('standby', 'Standby')], required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    branch_id = fields.Many2one(comodel_name='res.branch', string="Branch", tracking=True, required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                domain=lambda self: [('id', 'in', self.env.branches.ids)])
