from email.policy import default
from typing import Sequence
from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import safe_eval


class RecruitmentApprovalMatrix(models.Model):
    _name = 'hr.recruitment.approval.matrix'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Recruitment Approval Matrix"
    _order = 'create_date desc'
    name = fields.Char()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    apply_to = fields.Selection(
        [('by_employee', 'By Employee'), ('by_department', 'By Department'), ('by_job_position', 'By Job Position')])
    employee_ids = fields.Many2many('hr.employee')
    department_ids = fields.Many2many('hr.department',domain="[('company_id', '=', company_id)]")
    job_ids = fields.Many2many('hr.job',domain="[('company_id', '=', company_id)]")
    level = fields.Integer(compute="_get_level")
    approval_matrix_ids = fields.One2many('recruitment.approval.matrix.line', 'approval_matrix_id')
    man_power_type = fields.Selection([('man_power_plan','Manpower Plan'),('man_power_requisition','Manpower Requisition')])
    
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(RecruitmentApprovalMatrix, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(RecruitmentApprovalMatrix, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

   
                
                
    def approval_by_hierarchy(self,record):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(record,record.request_user,data,approval_ids,seq)
        return line
        
        
    def get_manager(self,record,employee_manager,data,approval_ids,seq):
        # setting_level = self.env['ir.config_parameter'].sudo().get_param(self.level_param)
        # if not setting_level:
        #     raise ValidationError("level not set")
        try:
            if not employee_manager['parent_id']['user_id']:
                    return approval_ids
            while employee_manager:
                approval_ids.append( (0,0,{'sequence':seq,'approvers':[(4,employee_manager['parent_id']['user_id']['id'])]}))
                data += 1
                seq +=1
                if employee_manager['parent_id']['user_id']['id']:
                    self.get_manager(record,employee_manager['parent_id'],data,approval_ids,seq)
                    break
            
            return approval_ids
        except RecursionError:
            pass

    @api.depends('approval_matrix_ids')
    def _get_level(self):
        for record in self:
            if record.approval_matrix_ids:
                record.level = len(record.approval_matrix_ids)
            else:
                record.level = 0

    @api.onchange('approval_matrix_ids')
    def _onchange_approval_matrix_line(self):
        sl = 0
        for line in self.approval_matrix_ids:
            sl = sl + 1
            line.sequence = sl

class RecruitmentApprovalMatrixline(models.Model):
    _name = 'recruitment.approval.matrix.line'
    approval_matrix_id = fields.Many2one('hr.recruitment.approval.matrix')
    approver_type = fields.Selection([('by_hierarchy','By Hierarchy'),('specific_approver','Specific Approver')])
    sequence = fields.Integer()
    company_id = fields.Many2one('res.company', related='approval_matrix_id.company_id')
    approvers = fields.Many2many('res.users',domain="[('company_id', '=', company_id)]")
    minimum_approver = fields.Integer(default=1)
    request_user = fields.Many2one('hr.employee',default=lambda self:self.env.user.employee_id.id)
    
    
    @api.onchange('approver_type')
    def _onchange_approver_type(self):
        for record in self:
            if record.approver_type == 'by_hierarchy':
                if record.approvers:
                    for data in record.approvers:
                        record.approvers = [(2,data.id)]
                
                record.approvers = False
                
            if record.approver_type == 'specific_approver':
                if record.approvers:
                    for data in record.approvers:
                        record.approvers = [(2,data.id)]
    
    def approval_by_hierarchy(self,record):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(record,record.request_user,data,approval_ids,seq)
        return line
        
        
    def get_manager(self,record,employee_manager,data,approval_ids,seq):
        try:
            if not employee_manager['parent_id']['user_id']:
                    return approval_ids
            while employee_manager:
                approval_ids.append((4,employee_manager['parent_id']['user_id']['id']))
                data += 1
                seq +=1
                if employee_manager['parent_id']['user_id']['id']:
                    self.get_manager(record,employee_manager['parent_id'],data,approval_ids,seq)
                    break
            return approval_ids
        except RecursionError:
            pass
                
                
                
            

    @api.model
    def default_get(self, fields):
        res = super(RecruitmentApprovalMatrixline, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if 'approval_matrix_ids' in context_keys:
                if len(self.env.context.get('approval_matrix_ids')) > 0:
                    next_sequence = len(self.env.context.get('approval_matrix_ids')) + 1
        res.update({'sequence': next_sequence})
        return res
