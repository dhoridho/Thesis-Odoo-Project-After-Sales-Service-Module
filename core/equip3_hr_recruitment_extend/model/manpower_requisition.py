from ast import Try
from dataclasses import field
from datetime import datetime, timedelta, date
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
import calendar
from dateutil.relativedelta import relativedelta
from pytz import timezone
from ...equip3_general_features.models.approval_matrix import approvalMatrix,approvalMatrixUser
from lxml import etree


class equip3ManPowerRequisition(models.Model):
    _name = "manpower.requisition"
    _description = "Manpower Requisition"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'number'
    _order = 'id desc'
    
    
    def _default_employee(self):
        return self.env.user.employee_id
    
    number = fields.Char()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    employee_id = fields.Many2one('hr.employee',default=_default_employee)
    request_type = fields.Selection([('man_power_plan','Manpower Plan'),('replacement','Replacement'),('other','Other')],default='man_power_plan')
    man_power_plan_id = fields.Many2one('manpower.planning', domain="[('company_id', '=', company_id),('state', '=', 'approved')]")
    man_power_plan_line_id = fields.Many2one('manpower.planning.line')
    replacement_position_id = fields.Many2one('hr.job',domain="[('company_id', '=', company_id)]")
    replacement_for_id = fields.Many2one('hr.employee')
    request_reason = fields.Text()
    expected_join_date = fields.Date()
    department_id = fields.Many2one('hr.department',domain="[('company_id', '=', company_id)]")
    job_id = fields.Many2one('hr.job')
    work_location_id = fields.Many2one('work.location.object')
    current_employee = fields.Integer()
    expected_new_employee = fields.Integer()
    fulfillment = fields.Integer()
    number_of_applicant = fields.Integer()
    note = fields.Text()
    company_id = fields.Many2one('res.company',default=lambda self:self.env.company.id)
    user_approval_ids = fields.Many2many('res.users',compute="_is_hide_approve")
    approval_matrix_ids = fields.One2many('requisition.matrix.line','requisition_id')
    is_hide_reject = fields.Boolean(default=True,compute='_get_is_hide')
    is_hide_approve = fields.Boolean(default=True,compute='_get_is_hide')
    is_mpp_approval_matrix = fields.Boolean("Is MPP Approval Matrix", compute='_compute_is_mpp_approval_matrix')
    state1 = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Submitted'),
            ('rejected', 'Rejected'),
        ],
        string='Status', default='draft', tracking=False, copy=False, store=True, compute='_compute_state1')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(equip3ManPowerRequisition, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(equip3ManPowerRequisition, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    

    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_is_mpp_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.mpp_approval_matrix')
            rec.is_mpp_approval_matrix = setting
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(equip3ManPowerRequisition, self).fields_view_get(
            view_id=view_id, view_type=view_type)
        if self.env.context.get('is_to_approve'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res
    
    
    @api.depends('approval_matrix_ids')
    def _is_hide_approve(self):
        for record in self:
            approval = approvalMatrixUser(record)
            approval.get_approval_user()
    
    
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            mpp_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.mpp_approval_matrix')
            if mpp_setting:
                if record.employee_id:
                    approval_matrix = approvalMatrix('hr.recruitment.approval.matrix',record,'equip3_hr_recruitment_extend.man_power_type_approval','equip3_hr_recruitment_extend.man_power_level')
                    apply = [{'apply_to':"""[('apply_to','=','by_employee'),('man_power_type','=','man_power_requisition')]""",
                                                'filter':"""lambda line:record.employee_id.id in line.employee_ids.ids""",
                                                    'order':"""'create_date desc'""",
                                                    'limit':1

                                                },

                            {'apply_to':"""[('apply_to','=','by_job_position'),('man_power_type','=','man_power_requisition')]""",
                                                'filter':"""lambda line: record.employee_id.job_id.id in line.job_ids.ids""",
                                                'order':"""'create_date desc'""",
                                                'limit':1

                                                },
                            {'apply_to':"""[('apply_to','=','by_department'),('man_power_type','=','man_power_requisition')]""",
                                                'filter':"""lambda line: record.employee_id.department_id.id in line.department_ids.ids""",
                                                'order':"""'create_date desc'""",
                                                'limit':1

                                                }
                            ]

                    approval_matrix.set_apply_to(apply)
                    approval_matrix.get_approval_matrix(is_approver_by_type=True)
    
    
    @api.depends('user_approval_ids')
    def _get_is_hide(self):
        for record in self:
            if not record.user_approval_ids or record.state != 'submitted' or not self.env.context.get('is_to_approve'):
                record.is_hide_approve = True
                record.is_hide_reject = True
            else:
                record.is_hide_approve = False
                record.is_hide_reject = False
    
    def action_confirm(self):
        for record in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.mpp_approval_matrix')
            if setting:
                record.write({'state': 'submitted'})
            else:
                record.write({'state': 'approved'})
    

    
    def action_generate(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'manpower.approve.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_requisition_id':self.id,'default_state':'approved'},
        }
        
    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'manpower.approve.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_requisition_id':self.id,'default_state':'rejected'},
        }
    
    @api.onchange('request_type')
    def _onchange_request_type(self):
        for record in self:
            if record.request_type:
                record.department_id = False
                record.job_id = False
                record.work_location_id = False
                record.replacement_for_id = False
                record.replacement_position_id = False
            if record.request_type == 'replacement':
                record.number_of_applicant = 1
    
    @api.onchange('replacement_for_id')
    def _onchange_replacement_for_id(self):
        for record in self:
            if record.replacement_for_id:
                record.department_id = record.replacement_for_id.department_id.id
                record.job_id = record.replacement_for_id.job_id.id
                record.work_location_id = record.replacement_for_id.location_id.id
    
    @api.onchange('man_power_plan_line_id')
    def _onchange_man_power_plan_line_id(self):
        for record in self:
            if record.man_power_plan_line_id:
                if record.request_type == 'man_power_plan':
                    record.current_employee = record.man_power_plan_line_id.current_number_of_employee
                    record.expected_new_employee = record.man_power_plan_line_id.total_expected_new_employee
                    record.fulfillment = record.man_power_plan_line_id.total_fullfillment
                    record.department_id = record.man_power_plan_line_id.department_id.id
                    record.job_id = record.man_power_plan_line_id.job_position_id.id
                    record.work_location_id = record.man_power_plan_line_id.work_location_id.id
    
    @api.model
    def create(self, vals_list):
        res = super(equip3ManPowerRequisition,self).create(vals_list)
        sequence = self.env['ir.sequence'].next_by_code(res._name)
        if not sequence:
            raise ValidationError("Sequence for Manpower Requisition not found")
        res.number = sequence
        
        if res.number_of_applicant < 1:
            raise ValidationError("Number of Applicant must be at least 1")
        
        return res
    
    @api.constrains('number_of_applicant')
    def _check_number_of_applicant(self):
        for record in self:
            is_invalid = (
                record.number_of_applicant > record.expected_new_employee and
                record.request_type == 'man_power_plan'
            )
            if is_invalid:
                raise ValidationError(
                    _(
                        "You may not submit requests for more employees than the planned number." + 
                        "The number you proposed during planning was %d employees."
                    ) % (self.expected_new_employee)
                )

    def cron_update_fullfillment_data(self):
        data_approved = self.search([('expected_join_date','>=',date.today()),('request_type','=','man_power_plan'),('state','=','approved')])
        if data_approved:
            for rec in data_approved:
                rec.current_employee = rec.man_power_plan_line_id.current_number_of_employee
                rec.expected_new_employee = rec.man_power_plan_line_id.total_expected_new_employee
                rec.fulfillment = rec.man_power_plan_line_id.total_fullfillment


class equip3RequisitionApprovalMatrix(models.Model):
    _name = 'requisition.matrix.line'
    _description="Requisition Approval Matrix"
    requisition_id = fields.Many2one('manpower.requisition')
    sequence = fields.Integer()
    approver_id = fields.Many2many('res.users',string="Approvers")
    approver_confirm = fields.Many2many('res.users','requisition_line_user_approve_ids','user_id',string="Approvers confirm")
    approval_status = fields.Text()
    timestamp = fields.Text()
    feedback = fields.Text()
    minimum_approver = fields.Integer(default=1)
    is_approve = fields.Boolean(string="Is Approve", default=False)
