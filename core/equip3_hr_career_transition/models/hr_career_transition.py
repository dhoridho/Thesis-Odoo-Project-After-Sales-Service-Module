from typing import Sequence
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import requests
headers = {'content-type': 'application/json'}
import base64
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

class Equip3CareerTransition(models.Model):
    _name = 'hr.career.transition'
    _rec_name = 'number'
    _description="Career Transition"
    _order ='create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
        
    number = fields.Char()
    employee_id = fields.Many2one('hr.employee',"Employee",domain=_multi_company_domain)
    career_transition = fields.Char()
    career_transition_type = fields.Many2one('career.transition.type')
    transition_date = fields.Date()
    description = fields.Text()
    status = fields.Selection([('draft','Draft'),('to_approve','To Approve'),('approve','Approved'),('rejected','Rejected')],default="draft")
    company_id = fields.Many2one('res.company',default=lambda self:self.env.company ,readonly=True)
    company_address = fields.Char(related='company_id.street')
    is_hide_confirm = fields.Boolean()
    is_hide_renew = fields.Boolean(default=True)
    is_hide_reject = fields.Boolean(default=True,compute='_get_is_hide')
    is_hide_approve = fields.Boolean(default=True,compute='_get_is_hide')
    employee_number_id = fields.Char()
    same_as_previous = fields.Boolean()
    contract_id = fields.Many2one('hr.contract')
    contract_type_id = fields.Many2one('hr.contract.type',related='contract_id.type_id')
    job_id = fields.Many2one('hr.job')
    employee_grade_id = fields.Many2one('employee.grade')
    department_id = fields.Many2one('hr.department')
    work_location_id = fields.Many2one('work.location.object')
    new_employee_number_id = fields.Char()
    new_contract_type_id = fields.Many2one('hr.contract.type')
    new_contract_id = fields.Char() 
    new_job_id = fields.Many2one('hr.job', domain="['|','&',('company_id', '=', False),('department_id','=',new_department_id),'&',('company_id', '=', new_company_id),('department_id','=',new_department_id)]")
    transition_type_name = fields.Char(related='career_transition_type.name')
    new_employee_grade_id = fields.Many2one('employee.grade')
    new_department_id = fields.Many2one('hr.department', domain="['|', ('company_id', '=', False), ('company_id', '=', new_company_id)]")
    new_work_location_id = fields.Many2one('work.location.object')
    allowed_company_ids = fields.Many2many('res.company', related='employee_id.user_id.company_ids')
    new_company_id = fields.Many2one('res.company', domain="[('id', 'in', allowed_company_ids)]")
    approval_matrix_ids = fields.One2many('hr.career.transition.matrix','career_transition_id')
    is_employee_sequence_number = fields.Boolean()
    user_approval_ids = fields.Many2many('res.users',compute="_is_hide_approve")
    date_of_joining = fields.Date(related="employee_id.date_of_joining")
    years_of_service = fields.Integer(related='employee_id.years_of_service')
    months = fields.Integer(related='employee_id.months')
    days = fields.Integer(related='employee_id.days')
    year = fields.Char(related='employee_id.year',string=' ', default='year(s) -')
    month = fields.Char(related='employee_id.month',string=' ', default='month(s) -')
    day = fields.Char(related='employee_id.day',string=' ', default='day(s)')
    transition_category_domain_ids = fields.Many2many('career.transition.category',compute="_is_category")
    transition_type_domain_ids = fields.Many2many('career.transition.type',compute="_is_type")
    transition_category_id = fields.Many2one('career.transition.category')
    is_readonly_employee = fields.Boolean()
    transition_wizard_state = fields.Char('Transition Wizard State')
    career_transition_template = fields.Many2one('hr.career.transition.letter', string='Career Transition Template')
    career_transition_attachment = fields.Binary(string='Career Transition Attachment')
    career_transition_attachment_fname = fields.Char('Career Transition Name')
    approvers_ids = fields.Many2many('res.users', 'career_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', 'career_overtime_approved_user_rel', string='Approved by User')

    
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(Equip3CareerTransition, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(Equip3CareerTransition, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def custom_menu(self):
        views = [(self.env.ref('equip3_hr_career_transition.hr_career_transition_tree_view').id, 'tree'),
                        (self.env.ref('equip3_hr_career_transition.hr_career_transition_form_view').id, 'form')]
        if self.env.user.has_group('equip3_hr_career_transition.career_transition_self_service') and not self.env.user.has_group('equip3_hr_career_transition.career_transition_team_approver'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Career Transition Request',
                'res_model': 'hr.career.transition',
                'view_mode': 'tree,form',
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                'context':{'search_default_career_transition_type_group_by': 1},
                'views':views,
                'help':"""<p class="oe_view_nocontent_create">
                    There is no examples click here to add new Career Transition Request.
                </p>"""
                
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Career Transition Request',
                'res_model': 'hr.career.transition',
                'view_mode': 'tree,form',
                'context':{'search_default_career_transition_type_group_by': 1},
                'views':views,
                'help':"""<p class="oe_view_nocontent_create">
                    There is no examples click here to add new Career Transition Request.
                </p>"""
                
            }

    
    
    
    
    @api.depends('company_id')
    def _is_category(self):
        for record in self:
            ids = []
            if self.env.user.has_group('equip3_hr_career_transition.career_transition_self_service') and not self.env.user.has_group('equip3_hr_career_transition.career_transition_team_approver'):
                group_ids = self.env['career.transition.category'].search([]).filtered(lambda line: self.env.ref('equip3_hr_career_transition.career_transition_self_service').id in line.group_ids.ids)
            if self.env.user.has_group('equip3_hr_career_transition.career_transition_team_approver') and not self.env.user.has_group('equip3_hr_career_transition.career_transition_all_approver'):
                group_ids = self.env['career.transition.category'].search([]).filtered(lambda line: self.env.ref('equip3_hr_career_transition.career_transition_team_approver').id in line.group_ids.ids)
            if self.env.user.has_group('equip3_hr_career_transition.career_transition_all_approver') and not self.env.user.has_group('equip3_hr_career_transition.career_transition_administrator'):
                group_ids = self.env['career.transition.category'].search([]).filtered(lambda line: self.env.ref('equip3_hr_career_transition.career_transition_all_approver').id in line.group_ids.ids)
            if  self.env.user.has_group('equip3_hr_career_transition.career_transition_administrator'):
                group_ids = self.env['career.transition.category'].search([]).filtered(lambda line: self.env.ref('equip3_hr_career_transition.career_transition_administrator').id in line.group_ids.ids) 
            if group_ids:
                data_id = [data.id for data in group_ids]
                ids.extend(data_id)
                record.transition_category_domain_ids = [(6,0,ids)]
            else:
                record.transition_category_domain_ids = False
                
                  
    @api.depends('company_id')
    def _is_type(self):
        for record in self:
            ids = []
            if self.env.user.has_group('equip3_hr_career_transition.career_transition_self_service') and not self.env.user.has_group('equip3_hr_career_transition.career_transition_team_approver'):
                group_ids = self.env['career.transition.type'].search([]).filtered(lambda line: self.env.ref('equip3_hr_career_transition.career_transition_self_service').id in line.group_ids.ids)
            if self.env.user.has_group('equip3_hr_career_transition.career_transition_team_approver') and not self.env.user.has_group('equip3_hr_career_transition.career_transition_all_approver'):
                group_ids = self.env['career.transition.type'].search([]).filtered(lambda line: self.env.ref('equip3_hr_career_transition.career_transition_team_approver').id in line.group_ids.ids)
            if self.env.user.has_group('equip3_hr_career_transition.career_transition_all_approver') and not self.env.user.has_group('equip3_hr_career_transition.career_transition_administrator'):
                group_ids = self.env['career.transition.type'].search([]).filtered(lambda line: self.env.ref('equip3_hr_career_transition.career_transition_all_approver').id in line.group_ids.ids)
            if  self.env.user.has_group('equip3_hr_career_transition.career_transition_administrator'):
                group_ids = self.env['career.transition.type'].search([]).filtered(lambda line: self.env.ref('equip3_hr_career_transition.career_transition_administrator').id in line.group_ids.ids) 
            if group_ids:
                data_id = [data.id for data in group_ids]
                ids.extend(data_id)
                record.transition_type_domain_ids = [(6,0,ids)]
            else:
                record.transition_type_domain_ids = False  
            
       
    
    @api.onchange('transition_category_id')
    def _onchange_transition_category_id(self):
        for record in self:
            if record.transition_category_id:
                record.career_transition = str(record.transition_category_id.name).lower()
    
    
    def unlink(self):
        for record in self:
            if record.status != "draft":
                raise ValidationError("Only career transition type status draft can be deleted")
        res =  super(Equip3CareerTransition, self).unlink()
        return res
    
  
    
    
    @api.depends('approval_matrix_ids')
    def _is_hide_approve(self):
        for record in self:
            if record.approval_matrix_ids:
                sequence = [data.sequence for data in record.approval_matrix_ids.filtered(lambda line:  len(line.approver_confirm.ids) != line.minimum_approver )]
                if sequence:
                    minimum_sequence = min(sequence)
                    approve_user= record.approval_matrix_ids.filtered(lambda line: self.env.user.id in line.approver_id.ids and self.env.user.id not in  line.approver_confirm.ids and line.sequence == minimum_sequence)
                    if approve_user:
                        record.user_approval_ids = [(6,0,[self.env.user.id])]
                    else:
                        record.user_approval_ids = False
                else:
                    record.user_approval_ids = False
            else:
                    record.user_approval_ids = False
    
    @api.depends('user_approval_ids')
    def _get_is_hide(self):
        for record in self:
            if not record.user_approval_ids:
                record.is_hide_approve = True
                record.is_hide_reject = True
            else:
                record.is_hide_approve = False
                record.is_hide_reject = False
                
                    
                        
    
    def print_on_page(self):
        for record in self:
            transition_date = datetime.strptime(str(record.transition_date), "%Y-%m-%d")
            transition_date_string = datetime(transition_date.year, transition_date.month,
                                                transition_date.day).strftime("%d %B %Y")
            create_date = datetime.strptime(str(record.create_date), "%Y-%m-%d %H:%M:%S.%f")
            create_date_string = datetime(create_date.year, create_date.month,
                                                create_date.day).strftime("%d %B %Y")
            if not record.career_transition_type.letter_id:
                raise ValidationError("Letter not set in transition type")        
            temp = record.career_transition_type.letter_id.letter_content
            letter_content_replace = record.career_transition_type.letter_id.letter_content
            if "$(company_id)" in letter_content_replace:
                if not record.company_id:
                    raise ValidationError("Company is empty")
                letter_content_replace = str(letter_content_replace).replace("$(company_id)", record.company_id.name)
            if "$(company_address)" in letter_content_replace:
                if not record.company_address:
                    raise ValidationError("Company address is empty")
                letter_content_replace = str(letter_content_replace).replace("$(company_address)", record.company_address)
            if "$(number)" in letter_content_replace:
                if not record.number:
                    raise ValidationError("Number is empty")               
                letter_content_replace = str(letter_content_replace).replace("$(number)", record.number)
            if "$(employee_id)" in letter_content_replace:
                if not record.employee_id:
                    raise ValidationError("Employee is empty")
                letter_content_replace = str(letter_content_replace).replace("$(employee_id)", record.employee_id.name)
            if "$(employee_number_id)" in letter_content_replace:
                if not record.employee_number_id:
                    raise ValidationError("Employee number is empty")
                letter_content_replace = str(letter_content_replace).replace("$(employee_number_id)", record.employee_number_id)
            if "$(job_id)" in letter_content_replace:
                if not record.job_id:
                    raise ValidationError("Job is empty")
                letter_content_replace = str(letter_content_replace).replace("$(job_id)", record.job_id.name)
            if "$(department_id)" in letter_content_replace:
                if not record.department_id:
                    raise ValidationError("Department is empty")
                letter_content_replace = str(letter_content_replace).replace("$(department_id)", record.department_id.name)
            if "$(work_location_id)" in letter_content_replace:
                if not record.work_location_id:
                    raise ValidationError("Work Location is empty")
                letter_content_replace = str(letter_content_replace).replace("$(work_location_id)", record.work_location_id.name)
            if "$(new_job_id)" in letter_content_replace:
                if not record.new_job_id:
                    raise ValidationError("New job is empty")
                letter_content_replace = str(letter_content_replace).replace("$(new_job_id)", record.new_job_id.name)
            if "$(new_department_id)" in letter_content_replace:
                if not record.new_department_id:
                    raise ValidationError("New department is empty")
                letter_content_replace = str(letter_content_replace).replace("$(new_department_id)", record.new_department_id.name)
            if "$(new_work_location_id)" in letter_content_replace:
                if not record.new_work_location_id:
                    raise ValidationError("New Work Location is empty")
                letter_content_replace = str(letter_content_replace).replace("$(new_work_location_id)", record.new_work_location_id.name)
            if "$(transition_date)" in letter_content_replace:
                if not record.transition_date:
                    raise ValidationError("Transition date is empty")
                letter_content_replace = str(letter_content_replace).replace("$(transition_date)", transition_date_string)
            if "$(create_date)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(create_date)", create_date_string)
            if "$(new_contract_type_id)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(new_contract_type_id)", record.new_contract_type_id.name)
            if "$(contract_id)" in letter_content_replace:
                if not record.contract_id:
                    raise ValidationError("Contract is empty")
                letter_content_replace = str(letter_content_replace).replace("$(contract_id)", record.contract_id.name)
            if "$(new_contract_id)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(new_contract_id)", record.new_contract_id)
            if "$(employee_grade_id)" in letter_content_replace:
                if not record.new_employee_grade_id:
                    raise ValidationError("Employee grade empty")
                letter_content_replace = str(letter_content_replace).replace("$(employee_grade_id)", record.employee_grade_id.name)
            if "$(new_employee_number_id)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(new_employee_number_id)", record.new_employee_number_id)
            if "$(new_employee_grade_id)" in letter_content_replace:
                if not record.new_employee_grade_id:
                    raise ValidationError("New employee grade empty")
                letter_content_replace = str(letter_content_replace).replace("$(new_employee_grade_id)", record.new_employee_grade_id.name)
            record.career_transition_type.letter_id.letter_content = letter_content_replace
            data = record.career_transition_type.letter_id.letter_content
            record.career_transition_type.letter_id.letter_content = temp
            
            return data
    
    
    @api.onchange('transition_category_id')
    def _onchange_career_transition(self):
        for record in self:
            if record.transition_category_id:
                if record.career_transition_type:
                    if record.career_transition_type.career_transition_category_id.id != record.transition_category_id.id:
                        record.career_transition_type = False
        
    
    @api.model
    def default_get(self, fields):
        res = super(Equip3CareerTransition, self).default_get(fields)
        emp_seq = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.emp_seq')
        if emp_seq:
            res['is_employee_sequence_number'] = emp_seq
            
        if self.env.user.has_group('equip3_hr_career_transition.career_transition_self_service') and not self.env.user.has_group('equip3_hr_career_transition.career_transition_team_approver'):
            employee_id = self.env['hr.employee'].search([('user_id','=',self.env.user.id)],limit=1)
            if not employee_id:
                raise ValidationError(f"Employee not set for User {self.env.user.name}")
            res['employee_id']= employee_id.id
            res['is_readonly_employee']= True
        
        return res
    
    @api.model
    def create(self,values):
        res= super(Equip3CareerTransition, self).create(values)
        sequence = self.env['ir.sequence'].search([('code','=',res._name)])
        if not sequence:
            raise ValidationError("Sequence for Transition not found")
        contract = self.env['hr.contract'].search([('employee_id','=',res.employee_id.id),('state','=','open')],limit=1)
        if not contract:
            raise ValidationError(_('This %s do not have running contract') % res.employee_id.name)
        if contract.date_end and contract.date_end <= date.today():
            raise ValidationError(_('This %s running contract is expired') % res.employee_id.name)
        now = datetime.now()
        split_sequence = str(sequence.next_by_id()).split('/')
        transition_number = F"CTR/{split_sequence[0]}/{now.month}/{now.day}/{split_sequence[1]}"
        res.number = transition_number
        return res
    
    def write(self, vals):
        res = super(Equip3CareerTransition, self).write(vals)
        for rec in self:
            contract = self.env['hr.contract'].search([('employee_id','=',rec.employee_id.id),('state','=','open')],limit=1)
            if not contract:
                raise ValidationError(_('This %s do not have running contract') % rec.employee_id.name)
            if contract.date_end and contract.date_end <= date.today():
                raise ValidationError(_('This %s running contract is expired') % rec.employee_id.name)
        return res
    
    def get_approval_ids(self):
        for record in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_career_transition.type_approval')
            if record.approval_matrix_ids:
                    remove = []
                    for line in record.approval_matrix_ids:
                        remove.append((2,line.id))
                    record.approval_matrix_ids =  remove
            if setting == 'employee_hierarchy':
                record.approval_matrix_ids = self.approval_by_hierarchy(record)
                self.app_list_career_emp_by_hierarchy()
            else:
                self.approval_by_matrix(record)
            
            
    
    @api.onchange('employee_id','career_transition_type')
    def _onchange_employee_id(self):
        for record in self:
            if record.employee_id and record.career_transition_type:
                record.employee_number_id = record.employee_id.sequence_code
                record.work_location_id = record.employee_id.location_id
                record.department_id = record.employee_id.department_id
                record.job_id = record.employee_id.job_id
                record.employee_grade_id = record.employee_id.grade_id

                contract = self.env['hr.contract'].search([('employee_id','=',record.employee_id.id),('state','=','open')],limit=1)
                if contract:
                    record.contract_id = contract.id
                    record.new_employee_number_id = False
                    record.new_contract_type_id = False
                    record.new_job_id = False
                    record.new_employee_grade_id = False
                    record.new_department_id = False
                    record.new_work_location_id = False
                    record.new_company_id = False
                    record.same_as_previous = False
                
                else:
                    record.same_as_previous = True
                    record.new_employee_number_id = record.employee_number_id
                    record.new_contract_type_id = record.contract_type_id
                    record.new_job_id = record.job_id
                    record.new_employee_grade_id = record.employee_grade_id
                    record.new_department_id = record.department_id
                    record.new_work_location_id = record.work_location_id
                    record.new_company_id = record.company_id
                if record.career_transition_type.letter_id:
                    record.career_transition_template = record.career_transition_type.letter_id
                self.get_approval_ids()
                

    def app_list_career_emp_by_hierarchy(self):
        for career in self:
            app_list = []
            for line in career.approval_matrix_ids:
                app_list.append(line.approver_id.id)
            career.approvers_ids = app_list
    
    def approval_by_matrix(self,record):
        app_list = []
        approval_matrix = self.env['hr.career.transition.approval.matrix'].search([('apply_to','=','by_employee')])
        matrix = approval_matrix.filtered(lambda line: record.employee_id.id in line.employee_ids.ids and record.career_transition_type.id  in line.career_transition_type.ids )
    
        if matrix:
            data_approvers = []
            for line in matrix[0].approval_matrix_ids:
                if line.approver_types == "specific_approver":
                    data_approvers.append((0,0,{'sequence':line.sequence,'minimum_approver':line.minimum_approver,'approver_id':[(6,0,line.approvers.ids)]}))
                    for approvers in line.approvers:
                        app_list.append(approvers.id)
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data = 0
                    approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                        app_list.append(approver)
            record.approvers_ids = app_list
            record.approval_matrix_ids = data_approvers
        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.career.transition.approval.matrix'].search([('apply_to','=','by_job_position')])
            matrix = approval_matrix.filtered(lambda line: record.job_id.id in line.job_ids.ids and record.career_transition_type.id  in line.career_transition_type.ids)
            if matrix:   
                for line in matrix[0].approval_matrix_ids:
                    if line.approver_types == "specific_approver":
                        data_approvers.append((0,0,{'sequence':line.sequence,'minimum_approver':line.minimum_approver,'approver_id':[(6,0,line.approvers.ids)]}))
                        for approvers in line.approvers:
                            app_list.append(approvers.id)
                    elif line.approver_types == "by_hierarchy":
                        manager_ids = []
                        seq = 1
                        data = 0
                        approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                            line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                            app_list.append(approver)
                record.approvers_ids = app_list
                record.approval_matrix_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.career.transition.approval.matrix'].search([('apply_to','=','by_department')])
                matrix = approval_matrix.filtered(lambda line: record.department_id.id in line.deparment_ids.ids and record.career_transition_type.id  in line.career_transition_type.ids)
                if matrix:
                    for line in matrix[0].approval_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0,0,{'sequence':line.sequence,'minimum_approver':line.minimum_approver,'approver_id':[(6,0,line.approvers.ids)]}))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                                line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                                app_list.append(approver)
                    record.approvers_ids = app_list
                    record.approval_matrix_ids = data_approvers
            
    def approval_by_hierarchy(self,record):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(record,record.employee_id,data,approval_ids,seq)
        return line
        
        
    def get_manager(self,record,employee_manager,data,approval_ids,seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_career_transition.level')
        if not setting_level:
            raise ValidationError("level not set")
        if not employee_manager['parent_id']['user_id']:
                return approval_ids
        while data < int(setting_level):
            approval_ids.append( (0,0,{'sequence':seq,'approver_id':[(4,employee_manager['parent_id']['user_id']['id'])]}))
            data += 1
            seq +=1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager(record,employee_manager['parent_id'],data,approval_ids,seq)
                break
        
        return approval_ids
    
    def get_manager_hierarchy(self, transition, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(transition, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids
        
        
           
                
    def renew_contract(self):
        return {
        'type': 'ir.actions.act_window',
        'name': 'Contract',
        'res_model': 'hr.contract',
        'view_type': 'form',
        'view_id': False,
        'target':'new',
        'view_mode': 'form',
        'context':{'default_name':self.new_contract_id,
                   'default_employee_id':self.employee_id.id,
                   'default_type_id':self.new_contract_type_id.id,
                   'default_company_id': self.new_company_id.id,
                   'default_job_id':self.new_job_id.id,
                   'default_department_id':self.new_department_id.id,
                   'default_work_location_id':self.new_work_location_id.id,
                   'default_career_transition_id':self.id,
                   'default_date_start':self.transition_date,
                   },
        }         
            
            
            
            
        
                       
                    
    @api.onchange('same_as_previous')
    def _onchange_same_as_previous(self):
        for record in self:
            if record.same_as_previous:
                record.new_employee_number_id = record.employee_number_id
                record.new_contract_type_id = record.contract_type_id
                record.new_job_id = record.job_id
                record.new_employee_grade_id = record.employee_grade_id
                record.new_department_id = record.department_id
                record.new_work_location_id = record.work_location_id
                record.new_company_id = record.company_id
            else:
                record.new_employee_number_id = False
                record.new_contract_type_id = False
                record.new_job_id = False
                record.new_employee_grade_id = False
                record.new_department_id = False
                record.new_work_location_id = False
                record.new_company_id = False
    
    @api.onchange('new_company_id')
    def _onchange_new_company_id(self):
        for rec in self:
            rec.new_department_id = False
            rec.new_job_id = False
    
    @api.onchange('new_department_id')
    def _onchange_new_department_id(self):
        for rec in self:
            rec.new_job_id = False
    
    def set_confirm(self):
        for record in self:
            if not record.approval_matrix_ids:
                record.status = "approve"
                record.is_hide_confirm = True
                record.approved_mail()
                record.approved_wa_template()
                if record.contract_id:
                    transition_date = datetime.strptime(str(record.transition_date), "%Y-%m-%d") + timedelta(days=-1)
                    record.contract_id.date_end = transition_date 
            else:
                record.status = "to_approve"
                record.is_hide_confirm = True
                record.is_hide_reject = False
                record.approver_mail()
                record.approver_wa_template()
                for line in record.approval_matrix_ids:
                    line.write({'approver_state': 'draft'})
   
    def approve(self):
        self.update({
            'transition_wizard_state': 'approve',
        })
        self.approval_matrix_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'career.transition.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_transition_id':self.id,},
        }
    
    def reject(self):
        self.update({
            'transition_wizard_state': 'rejected',
        })
        self.approval_matrix_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'career.transition.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_transition_id':self.id,
                       'default_state':self.transition_wizard_state},
        }

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_career_transition', 'hr_career_transition_menu_to_approve_root')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_career_transition', 'hr_career_transition_to_approve_act_window')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.career.transition&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.approval_matrix_ids:
                matrix_line = sorted(rec.approval_matrix_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approval_matrix_ids[len(matrix_line)]
                for user in approver.approver_id:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_career_transition',
                            'email_template_approver_of_career_transition')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(self)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': user.email,
                        'url': url,
                        'approver_name': user.name,
                        'emp_name': self.employee_id.name,
                    })
                    if self.transition_date:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(self.transition_date).strftime('%d/%m/%Y')})
                    rec.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.approval_matrix_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_career_transition',
                        'email_template_approved_career_transition')[1]
                except ValueError:
                    template_id = False
                ctx = self._context.copy()
                url = self.get_url(self)
                ctx.update({
                    'email_from': self.env.user.email,
                    'email_to': self.employee_id.user_id.email,
                    'url': url,
                    'emp_name': self.employee_id.name,
                })
                self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                          force_send=True)
            break

    def reject_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.approval_matrix_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_career_transition',
                        'email_template_rejection_of_career_transition')[1]
                except ValueError:
                    template_id = False
                ctx = self._context.copy()
                ctx.pop('default_state')
                url = self.get_url(self)
                ctx.update({
                    'email_from': self.env.user.email,
                    'email_to': self.employee_id.user_id.email,
                    'url': url,
                    'emp_name': self.employee_id.name,
                })
                self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                          force_send=True)
            break

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_career_transition.send_by_wa_career_transition')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(self)
        if send_by_wa:
            template = self.env.ref('equip3_hr_career_transition.career_transition_approver_wa_template')
            wa_sender = waParam()
            if template:
                if self.approval_matrix_ids:
                    matrix_line = sorted(self.approval_matrix_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.approval_matrix_ids[len(matrix_line)]
                    for user in approver.approver_id:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", self.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.number)
                        if "${career_transition}" in string_test:
                            string_test = string_test.replace("${career_transition}", self.transition_category_id.name)
                        if "${type}" in string_test:
                            string_test = string_test.replace("${type}", self.career_transition_type.name)
                        if "${start_date}" in string_test:
                            string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                                self.transition_date).strftime('%d/%m/%Y'))
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${br}" in string_test:
                            string_test = string_test.replace("${br}", f"\n")
                        if "${url}" in string_test:
                            string_test = string_test.replace("${url}", url)
                        phone_num = str(user.mobile_phone)
                        if "+" in phone_num:
                            phone_num = int(phone_num.replace("+", ""))
                        
                        wa_sender.set_wa_string(string_test,template._name,template_id=template)
                        wa_sender.send_wa(phone_num)
                        
                        # param = {'body': string_test, 'phone': phone_num}
                        # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                        # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                        # try:
                        #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
                        # except ConnectionError:
                        #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_career_transition.send_by_wa_career_transition')
        if send_by_wa:
            template = self.env.ref('equip3_hr_career_transition.career_transition_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.approval_matrix_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.number)
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)
                    if "+" in phone_num:
                        phone_num = int(phone_num.replace("+", ""))
                    if "${url}" in string_test:
                        string_test = string_test.replace("${url}", url)
                    
                    wa_sender.set_wa_string(string_test,template._name,template_id=template)
                    wa_sender.send_wa(phone_num)
                
                    # param = {'body': string_test, 'phone': phone_num}
                    # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                    # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                    # try:
                    #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                    #                                    headers=headers, verify=True)
                    # except ConnectionError:
                    #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def rejected_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_career_transition.send_by_wa_career_transition')
        if send_by_wa:
            template = self.env.ref('equip3_hr_career_transition.career_transition_rejected_wa_template')
            wa_sender = waParam()
            url = self.get_url(self)
            if template:
                if self.approval_matrix_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.number)
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)
                    if "+" in phone_num:
                        phone_num = int(phone_num.replace("+", ""))
                    
                    wa_sender.set_wa_string(string_test,template._name,template_id=template)
                    wa_sender.send_wa(phone_num)
                    
                    # param = {'body': string_test, 'phone': phone_num}
                    # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                    # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                    # try:
                    #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                    #                                    headers=headers, verify=True)
                    # except ConnectionError:
                    #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def get_career_transition_letter(self):
        for record in self:
            transition_date = datetime.strptime(str(record.transition_date), "%Y-%m-%d")
            transition_date_string = datetime(transition_date.year, transition_date.month,
                                              transition_date.day).strftime("%d %B %Y")
            create_date = datetime.strptime(str(record.create_date), "%Y-%m-%d %H:%M:%S.%f")
            create_date_string = datetime(create_date.year, create_date.month,
                                          create_date.day).strftime("%d %B %Y")
            if not record.career_transition_template:
                raise ValidationError("Letter not set in transition type")
            temp = record.career_transition_template.letter_content
            letter_content_replace = record.career_transition_template.letter_content
            if "$(company_id)" in letter_content_replace:
                if not record.company_id:
                    raise ValidationError("Company is empty")
                letter_content_replace = str(letter_content_replace).replace("$(company_id)", record.company_id.name)
            # if "$(company_address)" in letter_content_replace:
            #     if not record.company_address:
            #         raise ValidationError("Company address is empty")
            #     letter_content_replace = str(letter_content_replace).replace("$(company_address)",
            #                                                                  record.company_address)
            if "$(number)" in letter_content_replace:
                if not record.number:
                    raise ValidationError("Number is empty")
                letter_content_replace = str(letter_content_replace).replace("$(number)", record.number)
            if "$(employee_id)" in letter_content_replace:
                if not record.employee_id:
                    raise ValidationError("Employee is empty")
                letter_content_replace = str(letter_content_replace).replace("$(employee_id)", record.employee_id.name)
            if "$(employee_number_id)" in letter_content_replace:
                if not record.employee_number_id:
                    raise ValidationError("Employee number is empty")
                letter_content_replace = str(letter_content_replace).replace("$(employee_number_id)",
                                                                             record.employee_number_id)
            if "$(job_id)" in letter_content_replace:
                if not record.job_id:
                    raise ValidationError("Job is empty")
                letter_content_replace = str(letter_content_replace).replace("$(job_id)", record.job_id.name)
            if "$(department_id)" in letter_content_replace:
                if not record.department_id:
                    raise ValidationError("Department is empty")
                letter_content_replace = str(letter_content_replace).replace("$(department_id)",
                                                                             record.department_id.name)
            if "$(work_location_id)" in letter_content_replace:
                if not record.work_location_id:
                    raise ValidationError("Work Location is empty")
                letter_content_replace = str(letter_content_replace).replace("$(work_location_id)",
                                                                             record.work_location_id.name)
            if "$(new_job_id)" in letter_content_replace:
                if not record.new_job_id:
                    raise ValidationError("New job is empty")
                letter_content_replace = str(letter_content_replace).replace("$(new_job_id)", record.new_job_id.name)
            if "$(new_department_id)" in letter_content_replace:
                if not record.new_department_id:
                    raise ValidationError("New department is empty")
                letter_content_replace = str(letter_content_replace).replace("$(new_department_id)",
                                                                             record.new_department_id.name)
            if "$(new_work_location_id)" in letter_content_replace:
                if not record.new_work_location_id:
                    raise ValidationError("New Work Location is empty")
                letter_content_replace = str(letter_content_replace).replace("$(new_work_location_id)",
                                                                             record.new_work_location_id.name)
            if "$(transition_date)" in letter_content_replace:
                if not record.transition_date:
                    raise ValidationError("Transition date is empty")
                letter_content_replace = str(letter_content_replace).replace("$(transition_date)",
                                                                             transition_date_string)
            if "$(create_date)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(create_date)", create_date_string)
            if "$(new_contract_type_id)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(new_contract_type_id)",
                                                                             record.new_contract_type_id.name)
            if "$(contract_id)" in letter_content_replace:
                if not record.contract_id:
                    raise ValidationError("Contract is empty")
                letter_content_replace = str(letter_content_replace).replace("$(contract_id)", record.contract_id.name)
            if "$(new_contract_id)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(new_contract_id)",
                                                                             record.new_contract_id)
            if "$(employee_grade_id)" in letter_content_replace:
                if not record.new_employee_grade_id:
                    raise ValidationError("Employee grade empty")
                letter_content_replace = str(letter_content_replace).replace("$(employee_grade_id)",
                                                                             record.employee_grade_id.name)
            if "$(new_employee_number_id)" in letter_content_replace:
                letter_content_replace = str(letter_content_replace).replace("$(new_employee_number_id)",
                                                                             record.new_employee_number_id)
            if "$(new_employee_grade_id)" in letter_content_replace:
                if not record.new_employee_grade_id:
                    raise ValidationError("New employee grade empty")
                letter_content_replace = str(letter_content_replace).replace("$(new_employee_grade_id)",
                                                                             record.new_employee_grade_id.name)
            record.career_transition_template.letter_content = letter_content_replace
            data = record.career_transition_template.letter_content
            record.career_transition_template.letter_content = temp

            return data

    def update_career_transition_letter(self):
        for rec in self:
            if not rec.career_transition_template:
                raise ValidationError("Career Transition Template not set.")
            if rec.career_transition_template:
                pdf = self.env.ref('equip3_hr_career_transition.equip3_attachment_hr_career_transition_letter')._render_qweb_pdf([rec.id])
                attachment = base64.b64encode(pdf[0])
                rec.career_transition_attachment = attachment
                rec.career_transition_attachment_fname = 'Career Transition' +' - ' + f"{rec.employee_id.name}"
            else:
                rec.career_transition_attachment = False
                rec.career_transition_attachment_fname = ""

    def career_transition_letter_mail(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        self.update_career_transition_letter()
        try:
            template_id = ir_model_data.get_object_reference(
                'equip3_hr_career_transition',
                'email_template_of_career_transition_letter')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ir_values = {
            'name': self.career_transition_attachment_fname + '.pdf',
            'type': 'binary',
            'datas': self.career_transition_attachment,
            'store_fname': self.career_transition_attachment_fname,
            'mimetype': 'application/x-pdf',
        }
        data_id = self.env['ir.attachment'].create(ir_values)
        lang = self.env.context.get('lang')
        template = self.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'hr.career.transition',
            'active_model': 'hr.career.transition',
            'default_res_id': self.id,
            'default_partner_ids': [self.employee_id.user_id.partner_id.id],
            'active_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'custom_layout': " ",
            'default_attachment_ids': (data_id.id,),
            'force_email': True,
            'model_description': 'Career transition Letter',
        }
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    @api.constrains('transition_date')
    def check_transition_date(self):
        for rec in self:
            if rec.career_transition_type.notice_period and rec.career_transition_type.day_count_by == 'calendar_day':
                minimum_days = date.today() + relativedelta(days=rec.career_transition_type.notice_period_days)
                if not rec.transition_date >= minimum_days:
                    raise ValidationError(
                        _('You can only request %s at least %s days before the transition date') % (rec.career_transition_type.name, rec.career_transition_type.notice_period_days))
            elif rec.career_transition_type.notice_period and rec.career_transition_type.day_count_by == 'work_day':
                current_date = date.today()
                weekend = 0
                while current_date <= rec.transition_date:
                    if current_date.weekday() in (5, 6):
                        weekend += 1
                    current_date += relativedelta(days=1)
                minimum_days_weekend = date.today() + relativedelta(days=rec.career_transition_type.notice_period_days)
                minimum_days = minimum_days_weekend + relativedelta(days=weekend)
                if not rec.transition_date >= minimum_days:
                    raise ValidationError(
                        _('You can only request %s at least %s days before the transition date') % (rec.career_transition_type.name, rec.career_transition_type.notice_period_days))

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_career = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_career_transition.number_of_repetitions_career'))
        career_approve = self.search([('status', '=', 'to_approve')])
        for rec in career_approve:
            if rec.approval_matrix_ids:
                matrix_line = sorted(rec.approval_matrix_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approval_matrix_ids[len(matrix_line)]
                for user in approver.approver_id:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_career_transition',
                            'email_template_approver_of_career_transition')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(rec)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': user.email,
                        'url': url,
                        'approver_name': user.name,
                        'emp_name': rec.employee_id.name,
                    })
                    if rec.transition_date:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(rec.transition_date).strftime('%d/%m/%Y')})
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_career - 1
                        query_statement = """UPDATE hr_career_transition_matrix set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approver_confirm and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE hr_career_transition_matrix set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        career_approve = self.search([('status', '=', 'to_approve')])
        for rec in career_approve:
            if rec.approval_matrix_ids:
                matrix_line = sorted(rec.approval_matrix_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approval_matrix_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in approver.approver_confirm.ids and user.user_delegation_id.id not in approver.approver_confirm.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_career_transition',
                                    'email_template_approver_of_career_transition')[1]
                            except ValueError:
                                template_id = False
                            ctx = self._context.copy()
                            url = self.get_url(rec)
                            ctx.update({
                                'email_from': self.env.user.email,
                                'email_to': user.user_delegation_id.email,
                                'url': url,
                                'approver_name': user.user_delegation_id.name,
                                'emp_name': rec.employee_id.name,
                            })
                            if rec.transition_date:
                                ctx.update(
                                    {'date_from': fields.Datetime.from_string(rec.transition_date).strftime('%d/%m/%Y')})
                            approver.update({
                                'approver_id': [(4, user.user_delegation_id.id)],
                                'is_delegation_mail_sent': True,
                            })
                            rec.update({
                                'approvers_ids': [(4, user.user_delegation_id.id)],
                            })
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)

class Equip3CareerTransitionApprovalMatrix(models.Model):
    _name = 'hr.career.transition.matrix'
    _description="Career Transition Approval Matrix"
    career_transition_id = fields.Many2one('hr.career.transition')
    sequence = fields.Integer(compute="fetch_sl_no")
    approver_id = fields.Many2many('res.users',string="Approvers")
    approver_confirm = fields.Many2many('res.users','matrix_line_user_approve_ids','user_id',string="Approvers confirm")
    approval_status = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    timestamp = fields.Text()
    feedback = fields.Text()
    minimum_approver = fields.Integer(default=1)
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'career_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    status = fields.Selection(string='Parent Status', related='career_transition_id.status')

    @api.depends('career_transition_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.career_transition_id.approval_matrix_ids:
            sl = sl + 1
            line.sequence = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len(rec.approver_id) < rec.minimum_approver and rec.career_transition_id.status == 'draft':
                rec.minimum_approver = len(rec.approver_id)
            if not rec.matrix_user_ids and rec.career_transition_id.status == 'draft':
                rec.matrix_user_ids = rec.approver_id

    def update_approver_state(self):
        for rec in self:
            if rec.career_transition_id.status == 'to_approve':
                if not rec.approver_confirm:
                    rec.approver_state = 'draft'
                elif rec.approver_confirm and rec.minimum_approver == len(rec.approver_confirm):
                    rec.approver_state = 'approved'
                else:
                    rec.approver_state = 'pending'

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    transition_line_ids = fields.One2many('employee.transition', 'career_employee_id', string="Transition History")

    def _compute_contracts_count(self):
        super(HrEmployee, self)._compute_contracts_count()
        self._compute_transisiton_list()

    def _compute_transisiton_list(self):
        for transition in self:
            if transition.transition_line_ids:
                transition.transition_line_ids = False
            transition_data = self.env['hr.career.transition'].search(
                [('employee_id', 'in', transition.ids), ('status', '=', 'approve')], order="id desc")
            for tra_data in transition_data:
                transition.transition_line_ids = [
                    (0, 0, {'emp_transition_id': tra_data.id, 'career_employee_id': transition.id})]



class EmployeeCarrerTransition(models.Model):
    _name = 'employee.transition'
    _description = 'Career Transition History'

    career_employee_id = fields.Many2one('hr.employee', string="Employee")
    emp_transition_id = fields.Many2one('hr.career.transition', string="Career Transition")
    transition_category_id = fields.Many2one('career.transition.category',
                                             related='emp_transition_id.transition_category_id')
    career_transition_type = fields.Many2one('career.transition.type',
                                             related='emp_transition_id.career_transition_type')
    transition_date = fields.Date(related='emp_transition_id.transition_date')
    description = fields.Text(related='emp_transition_id.description')
    company_id = fields.Many2one('res.company', related='emp_transition_id.company_id')
    career_transition_attachment = fields.Binary(string='Career Transition Attachment', related='emp_transition_id.career_transition_attachment')
    career_transition_attachment_fname = fields.Char('Career Transition Name', related='emp_transition_id.career_transition_attachment_fname')
