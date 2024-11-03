# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class EmployeeChangeRequestConfig(models.Model):
    _name = 'employee.change.request.config'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Employee Change Request Config"
    _order = 'create_date desc'

    name = fields.Char('Name')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    level = fields.Integer(compute="_get_level")
    approval_config_ids = fields.One2many('employee.change.request.config.line', 'config_id')

    def write(self, vals):
        res = super(EmployeeChangeRequestConfig, self).write(vals)
        for rec in self:
            line_ids = len(rec.approval_config_ids)
            if line_ids == 0:
                raise ValidationError(_("Approval User Lines cannot be empty!"))
        return res

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeChangeRequestConfig, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeChangeRequestConfig, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.depends('approval_config_ids')
    def _get_level(self):
        for record in self:
            if record.approval_config_ids:
                record.level = len(record.approval_config_ids)
            else:
                record.level = 0

    @api.onchange('approval_config_ids')
    def _onchange_approval_config_line(self):
        sl = 0
        for line in self.approval_config_ids:
            sl = sl + 1
            line.sequence = sl

class EmployeeChangeRequestConfigLine(models.Model):
    _name = 'employee.change.request.config.line'

    config_id = fields.Many2one('employee.change.request.config', ondelete="cascade")
    sequence = fields.Integer('Sequence')
    approvers = fields.Many2many('res.users')
    minimum_approver = fields.Integer(default=1)
    approver_types = fields.Selection(
        [('by_hierarchy', 'By Hierarchy'),
         ('specific_approver', 'Specific Approver')], default="specific_approver", string="Approver Types")

    @api.onchange("approver_types")
    def _onchange_approver_types(self):
        if self.approver_types == 'by_hierarchy':
            self.approvers = False

    @api.model
    def default_get(self, fields):
        res = super(EmployeeChangeRequestConfigLine, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if 'approval_config_ids' in context_keys:
                if len(self.env.context.get('approval_config_ids')) > 0:
                    next_sequence = len(self.env.context.get('approval_config_ids')) + 1
        res.update({'sequence': next_sequence})
        return res
