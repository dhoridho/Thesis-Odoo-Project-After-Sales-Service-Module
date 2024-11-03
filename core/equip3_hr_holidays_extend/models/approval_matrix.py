# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from lxml import etree
from odoo.exceptions import ValidationError


class HrLeaveApprovalMatrix(models.Model):
    _name = "hr.leave.approval"

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    @api.model
    def _leave_type_company_domain(self):
        return [('company_id','=', self.env.company.id),('leave_validation_type_clone','=','by_approval_matrix')]
    
    name = fields.Char(string='Name')
    level = fields.Integer('Level', compute='_compute_get_level')
    mode_type = fields.Selection([
        ('leave_type', 'By Leave Type'),
        ('employee', 'By Employee'),
        ('job_position', 'By Job Position'),
        ('department', 'By Department')],
        string='Mode', help='Leave Request /Leave Cancel')
    # leave_type_ids = fields.Many2many('hr.leave.type', string='Leave Type', domain="[('leave_validation_type_clone','=','by_approval_matrix')]")
    leave_type_ids = fields.Many2many('hr.leave.type', string='Leave Type', domain=_leave_type_company_domain)
    employee_ids = fields.Many2many('hr.employee', string='Employee', domain=_multi_company_domain)
    department_ids = fields.Many2many('hr.department', string='Department', domain=_multi_company_domain)
    job_ids = fields.Many2many('hr.job', string='Job Position')
    leave_approvel_matrix_ids = fields.One2many('hr.leave.approval.line', 'leave_approvel_matrix_line_id',
                                                string='Approver')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    applicable_to = fields.Selection([('leave_request', 'Leave Request'),
                                      ('allocation_request', 'Allocation Request'),
                                      ('leave_and_allocation_request', 'Leave Request & Allocation Request')],
                                     default='leave_and_allocation_request', string="Applicable To", required=True)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrLeaveApprovalMatrix, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrLeaveApprovalMatrix, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def _compute_get_level(self):
        if self:
            for rec in self:
                approval_line = self.env['hr.leave.approval.line'].search(
                    [('leave_approvel_matrix_line_id', '=', rec.id)])
                rec.level = len(approval_line.ids)
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrLeaveApprovalMatrix, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res

    @api.onchange('leave_approvel_matrix_ids')
    def _onchange_approval_matrix_line(self):
        sl = 0
        for line in self.leave_approvel_matrix_ids:
            sl = sl + 1
            line.name = sl

    @api.constrains('leave_approvel_matrix_ids')
    def _constrains_leave_approvel_matrix(self):
        for rec in self:
            if len(rec.leave_approvel_matrix_ids.filtered(lambda r: r.approver_types == "by_hierarchy")) > 1:
                raise ValidationError("You Only Able to set One Lines of  Approver Type with By Hierarchy type")

class HrLeaveApprovalMatrixLine(models.Model):
    _name = 'hr.leave.approval.line'

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    leave_approvel_matrix_line_id = fields.Many2one('hr.leave.approval', string="Matrix Line")
    name = fields.Integer('Sequence')
    approver_ids = fields.Many2many('res.users', string="Approvers", domain=_multi_company_domain)
    minimum_approver = fields.Integer(string="Minimum Approver", default="1")
    approver_types = fields.Selection(
        [('by_hierarchy', 'By Hierarchy'),
         ('specific_approver', 'Specific Approver')], default="specific_approver", string="Approver Types")

    @api.onchange("approver_types")
    def _onchange_approver_types(self):
        if self.approver_types == 'by_hierarchy':
            self.approver_ids = False

    @api.model
    def default_get(self, fields):
        res = super(HrLeaveApprovalMatrixLine, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if 'leave_approvel_matrix_ids' in context_keys:
                if len(self.env.context.get('leave_approvel_matrix_ids')) > 0:
                    next_sequence = len(self.env.context.get('leave_approvel_matrix_ids')) + 1
        res.update({'name': next_sequence})
        return res
