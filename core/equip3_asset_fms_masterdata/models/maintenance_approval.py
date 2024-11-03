from odoo import api, fields, models
from datetime import datetime

class MaintenanceApprovalWo(models.Model):
    _name = 'maintenance.approval.wo'
    _description = 'Maintenance Approval Wo'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    company_id = fields.Many2one(comodel_name='res.company', string='Company')
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch')
    createon = fields.Date(string='Create On',default=datetime.today().date())
    approval_ids = fields.One2many(comodel_name='approval.line', inverse_name='approval_wo_line', string='Approval Line')
    createby = fields.Many2one(comodel_name='res.users', string='Create By', default=lambda self: self.env.user)

class MaintenanceApprovalRo(models.Model):
    _name = 'maintenance.approval.ro'
    _description = 'Maintenance Approval Ro'

    name = fields.Char(string='Name')
    company_id = fields.Many2one(comodel_name='res.company', string='Company')
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch')
    createon = fields.Date(string='Create On',default=datetime.today().date())
    approval_ids = fields.One2many(comodel_name='approval.line', inverse_name='approval_ro_line', string='Approval Line')
    createby = fields.Many2one(comodel_name='res.users', string='Create By', default=lambda self: self.env.user)

class ApprovalLine(models.Model):
    _name = 'approval.line'
    _description = 'Approval Line'

    no_wo_sequence = fields.Integer(string='NO', default=1)
    userwo_line_id = fields.Many2one(comodel_name='res.users', string='User')
    approval_wo_id = fields.Many2one(comodel_name='res.users', string='Approval')
    approval_wo_line = fields.Many2one(comodel_name='maintenance.approval.wo', string='Approv')
    minimum_wo = fields.Integer(string='Minimum Approval')
    no_ro_sequence = fields.Integer(string='NO', default=1)
    userro_line_id = fields.Many2one(comodel_name='res.users', string='User')
    approval_ro_id = fields.Many2one(comodel_name='res.users', string='Approval')
    approval_ro_line = fields.Many2one(comodel_name='maintenance.approval.ro', string='Approv')
    minimum_ro = fields.Integer(string='Minimum Approval')

    @api.model
    def default_get(self, fields):
        res = super(ApprovalLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_ids' in context_keys:
               if len(self._context.get('approval_ids')) > 0:
                    next_sequence = len(self._context.get('approval_ids')) + 1
            res.update({'no_wo_sequence': next_sequence})
            res.update({'no_ro_sequence': next_sequence})
        return res
