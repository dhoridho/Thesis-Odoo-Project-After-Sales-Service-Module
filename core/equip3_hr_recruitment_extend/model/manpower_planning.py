from ast import Try
from dataclasses import field
from datetime import datetime, timedelta
import imp
from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError
import calendar
from dateutil.relativedelta import relativedelta
from pytz import timezone
from lxml import etree


class equip3ManPowerPlanning(models.Model):
    _name = "manpower.planning"
    _description = "Manpower Planning"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_employee(self):
        return self.env.user.employee_id

    name = fields.Char()
    state = fields.Selection(
        [('draft', 'Draft'), ('selected', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='draft')
    employee_id = fields.Many2one('hr.employee', 'Employee', default=_default_employee)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    approvers_ids = fields.Many2many('res.users', 'man_plan_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    mpp_year = fields.Many2one('hr.years')
    mpp_type = fields.Many2one('manpower.planning.type', "MPP Type")
    mpp_type_domain = fields.Many2many('manpower.planning.type', "MPP Type domain",compute='_compute_mpp_type_domain')
    mpp_period = fields.Many2one('manpower.planning.period', "MPP Period")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    all_department = fields.Boolean()
    department_ids = fields.Many2many('hr.department',domain="[('company_id', '=', company_id)]")
    work_location_ids = fields.Many2many('work.location.object', string="Work Location",domain="[('company_id', '=', company_id)]")
    manpower_line_ids = fields.One2many('manpower.planning.line', 'manpower_id')
    manpower_matrix_line_ids = fields.One2many('manpower.planning.matrix', 'manpower_id')
    is_create_manual = fields.Boolean()
    is_readonly_line =  fields.Boolean(compute='_compute_is_readonly_line')
    is_hide_button = fields.Boolean(compute='_compute_is_hide_button')
    is_mpp_approval_matrix = fields.Boolean("Is MPP Approval Matrix", compute='_compute_is_mpp_approval_matrix')
    state1 = fields.Selection(
        [('draft', 'Draft'), ('selected', 'Submitted'), ('approved', 'Submitted'), ('rejected', 'Rejected')],
        string='State', default='draft', tracking=False, copy=False, store=True, compute='_compute_state1')
    

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(equip3ManPowerPlanning, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(equip3ManPowerPlanning, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    

    
    @api.constrains('work_location_ids','department_ids')
    def _constrain_work_location_ids(self):
        for data in self:
            if data.work_location_ids and data.manpower_line_ids:
                for line in data.manpower_line_ids:
                    if line.work_location_id.id not in data.work_location_ids.ids and line.department_id.id not in data.department_ids.ids:
                        raise ValidationError("The Department and Work Location data you provided in the MPP lines does not match what is on the entry form.")
                    if line.work_location_id.id not in data.work_location_ids.ids:
                        raise ValidationError("The Work Location data you provided in the MPP lines does not match what is on the entry form.")
                    if line.department_id.id not in data.department_ids.ids:
                        raise ValidationError("The Department data you provided in the MPP lines does not match what is on the entry form.")
                    
    @api.constrains('manpower_line_ids')
    def _constrain_manpower_line_ids(self):
        for data in self:
            if not data.manpower_line_ids:
                raise ValidationError("You have not filled in the data needed in MPP Lines")
                   
                
    
    
    
    @api.onchange('mpp_year')
    def _onchange_mpp_year(self):
        for data in self:
            if data.mpp_year:
                if data.mpp_type:
                    if data.mpp_type.id not in data.mpp_type_domain.ids:
                        data.mpp_type = False
    
    @api.depends('mpp_year')
    def _compute_mpp_type_domain(self):
        for data in self:
            mpp_type = []
            if data.mpp_year:
                period = self.env['manpower.planning.period'].sudo().search(([('mpp_year','=',data.mpp_year.id)]))
                if period:
                    for line in period:
                        mpp_type.append(line.mpp_type.id)
            data.mpp_type_domain = [(6,0,mpp_type)]
                
                
        
    
    @api.onchange('department_ids','work_location_ids')
    def _onchange_department_ids_work_location_ids(self):
        for data in self:
            if data.department_ids or data.work_location_ids:
                if data.manpower_line_ids:
                    for line in data.manpower_line_ids:
                        line._use_mpp_line()

    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_is_mpp_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.mpp_approval_matrix')
            rec.is_mpp_approval_matrix = setting
    
    
    @api.depends('create_date')
    def _compute_is_hide_button(self):
        for record in self:
            if not record.is_approver or record.state != 'selected' or not self.env.context.get('is_to_approve'):
                record.is_hide_button = True
            else:
                record.is_hide_button = False
    
    
    
    
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(equip3ManPowerPlanning, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=True)
        if  self.env.context.get('is_to_approve'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res
    
    
    @api.depends('state')
    def _compute_is_readonly_line(self):
        for record in self:
            if record.state  not in ['draft']:
                record.is_readonly_line = True
            else:
                record.is_readonly_line = False
    
    
    
    @api.onchange('employee_id', 'mpp_type')
    def onchange_approver_user(self):
        for man_power in self:
            mpp_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.mpp_approval_matrix')
            if mpp_setting:
                if man_power.manpower_matrix_line_ids:
                    remove = []
                    for line in man_power.manpower_matrix_line_ids:
                        remove.append((2, line.id))
                    man_power.manpower_matrix_line_ids = remove
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_recruitment_extend.man_power_type_approval')
                if setting == 'employee_hierarchy':
                    man_power.manpower_matrix_line_ids = self.mpp_emp_by_hierarchy(man_power)
                    self.app_list_mpp_emp_by_hierarchy()
                if setting == 'approval_matrix':
                    self.man_power_approval_by_matrix(man_power)

    def mpp_emp_by_hierarchy(self, man_power):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(man_power, man_power.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, man_power, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.man_power_level')
        if not setting_level:
            raise ValidationError("Level not set")
        if not employee_manager['parent_id']['user_id']:
            return approval_ids
        while data < int(setting_level):
            approval_ids.append(
                (0, 0, {'user_ids': [(4, employee_manager['parent_id']['user_id']['id'])]}))
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager(man_power, employee_manager['parent_id'], data, approval_ids, seq)
                break
        return approval_ids

    def app_list_mpp_emp_by_hierarchy(self):
        for man_power in self:
            app_list = []
            for line in man_power.manpower_matrix_line_ids:
                app_list.append(line.user_ids.id)
            man_power.approvers_ids = app_list

    def man_power_approval_by_matrix(self, man_power):
        app_list = []
        approval_matrix = self.env['hr.recruitment.approval.matrix'].search([('apply_to', '=', 'by_employee'),('man_power_type','=','man_power_plan')])
        matrix = approval_matrix.filtered(lambda line: man_power.employee_id.id in line.employee_ids.ids)
        if matrix:
            data_approvers = []
            for line in matrix[0].approval_matrix_ids:
                if line.approver_type == 'specific_approver':
                        data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                    'user_ids': [(6, 0, line.approvers.ids)]}))
                else:
                    data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                'user_ids': [(6, 0, self.approval_by_hierarchy_approval_type(man_power))]}))
                for approvers in line.approvers:
                    app_list.append(approvers.id)
            man_power.approvers_ids = app_list
            man_power.manpower_matrix_line_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.recruitment.approval.matrix'].search([('apply_to', '=', 'by_job_position'),('man_power_type','=','man_power_plan')])
            matrix = approval_matrix.filtered(lambda line: man_power.job_id.id in line.job_ids.ids)
            if matrix:
                for line in matrix[0].approval_matrix_ids:
                    if line.approver_type == 'specific_approver':
                        data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                    'user_ids': [(6, 0, line.approvers.ids)]}))
                    else:
                        data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                    'user_ids': [(6, 0, self.approval_by_hierarchy_approval_type(man_power))]}))
                    for approvers in line.approvers:
                            app_list.append(approvers.id)
                man_power.approvers_ids = app_list
                man_power.manpower_matrix_line_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.recruitment.approval.matrix'].search(
                    [('apply_to', '=', 'by_department'),('man_power_type','=','man_power_plan')])
                matrix = approval_matrix.filtered(lambda line: man_power.department_id.id in line.department_ids.ids)
                if matrix:
                    for line in matrix[0].approval_matrix_ids:
                        if line.approver_type == 'specific_approver':
                            data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                        'user_ids': [(6, 0, line.approvers.ids)]}))
                        else:
                            data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                        'user_ids': [(6, 0, self.approval_by_hierarchy_approval_type(man_power))]}))
                        for approvers in line.approvers:
                            app_list.append(approvers.id)
                    man_power.approvers_ids = app_list
                    man_power.manpower_matrix_line_ids = data_approvers
                    
                    
    def approval_by_hierarchy_approval_type(self,record):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager_by_approver(record,record.employee_id,data,approval_ids,seq)
        return line
        
        
    def get_manager_by_approver(self,record,employee_manager,data,approval_ids,seq):
        try:
            if not employee_manager['parent_id']['user_id']:
                    return approval_ids
            while employee_manager:
                approval_ids.append(employee_manager['parent_id']['user_id']['id'])
                data += 1
                seq +=1
                if employee_manager['parent_id']['user_id']['id']:
                    self.get_manager_by_approver(record,employee_manager['parent_id'],data,approval_ids,seq)
                    break
            return approval_ids
        except RecursionError:
            pass

    @api.depends('mpp_type', 'employee_id')
    def _compute_can_approve(self):
        for man_power in self:
            if man_power.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_recruitment_extend.man_power_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_recruitment_extend.man_power_level')
                app_level = int(setting_level)
                current_user = self.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(man_power.manpower_matrix_line_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(man_power.manpower_matrix_line_ids)
                    if app < app_level and app < a:
                        if current_user in man_power.manpower_matrix_line_ids[app].user_ids:
                            man_power.is_approver = True
                        else:
                            man_power.is_approver = False
                    else:
                        man_power.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(man_power.manpower_matrix_line_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(man_power.manpower_matrix_line_ids)
                    if app < a:
                        for line in man_power.manpower_matrix_line_ids[app]:
                            if current_user in line.user_ids:
                                man_power.is_approver = True
                            else:
                                man_power.is_approver = False
                    else:
                        man_power.is_approver = False

                else:
                    man_power.is_approver = False
            else:
                man_power.is_approver = False

    def action_submit(self):
        setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.mpp_approval_matrix')
        if setting:
            self.write({'state': 'selected'})
            for line in self.manpower_matrix_line_ids:
                line.write({'approver_state': 'draft'})
        else:
            self.write({'state': 'approved'})
            self.assign_mpp()
            

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.man.plan.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':True,'default_state':'approved'},
            'target': 'new',
        }
        
    def assign_mpp(self):
        for record in self:
            if record.manpower_line_ids:
                for line_job in record.manpower_line_ids:
                    line_job.job_position_id._is_use_mpp()

    def action_approve(self):
        for record in self:
            current_user = self.env.uid
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_recruitment_extend.man_power_type_approval')
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            if setting == 'employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.manpower_matrix_line_ids:
                            if current_user == user.user_ids.id:
                                user.is_approve = True
                                user.timestamp = fields.Datetime.now()
                                user.approver_state = 'approved'
                                string_approval = []
                                if user.approval_status:
                                    string_approval.append(f"{self.env.user.name}:Approved")
                                    user.approval_status = "\n".join(string_approval)
                                    string_timestammp = [user.approved_time]
                                    string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                    user.approved_time = "\n".join(string_timestammp)
                                    if record.feedback_parent:
                                        feedback_list = [user.feedback,
                                                         f"{self.env.user.name}:{record.feedback_parent}"]
                                        final_feedback = "\n".join(feedback_list)
                                        user.feedback = f"{final_feedback}"
                                    elif user.feedback and not record.feedback_parent:
                                        user.feedback = user.feedback
                                    else:
                                        user.feedback = ""
                                else:
                                    user.approval_status = f"{self.env.user.name}:Approved"
                                    user.approved_time = f"{self.env.user.name}:{dateformat}"
                                    if record.feedback_parent:
                                        user.feedback = f"{self.env.user.name}:{record.feedback_parent}"
                                    else:
                                        user.feedback = ""
                                record.approved_user_ids = [(4, current_user)]
                        matrix_line = sorted(record.manpower_matrix_line_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.write({'state': 'approved'})
                            self.env.cr.commit()
                            record.assign_mpp()
                        else:
                            record.approved_user = self.env.user.name + ' ' + 'has been approved the Request!'
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved'
                    ))
            elif setting == 'approval_matrix':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for line in record.manpower_matrix_line_ids:
                            for user in line.user_ids:
                                if current_user == user.user_ids.id:
                                    # line.timestamp = fields.Datetime.now()
                                    record.approved_user_ids = [(4, current_user)]
                                    var = len(line.approved_employee_ids) + 1
                                    if line.minimum_approver <= var:
                                        line.approver_state = 'approved'
                                        string_approval = []
                                        string_approval.append(line.approval_status)
                                        if line.approval_status:
                                            string_approval.append(f"{self.env.user.name}:Approved")
                                            line.approval_status = "\n".join(string_approval)
                                            string_timestammp = [line.approved_time]
                                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                            line.approved_time = "\n".join(string_timestammp)
                                            if record.feedback_parent:
                                                feedback_list = [line.feedback,
                                                                 f"{self.env.user.name}:{record.feedback_parent}"]
                                                final_feedback = "\n".join(feedback_list)
                                                line.feedback = f"{final_feedback}"
                                            elif line.feedback and not record.feedback_parent:
                                                line.feedback = line.feedback
                                            else:
                                                line.feedback = ""
                                        else:
                                            line.approval_status = f"{self.env.user.name}:Approved"
                                            line.approved_time = f"{self.env.user.name}:{dateformat}"
                                            if record.feedback_parent:
                                                line.feedback = f"{self.env.user.name}:{record.feedback_parent}"
                                            else:
                                                line.feedback = ""
                                        line.is_approve = True
                                    else:
                                        line.approver_state = 'pending'
                                        if line.approval_status:
                                            string_approval.append(f"{self.env.user.name}:Approved")
                                            line.approval_status = "\n".join(string_approval)
                                            string_timestammp = [line.approved_time]
                                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                                            line.approved_time = "\n".join(string_timestammp)
                                            if record.feedback_parent:
                                                feedback_list = [line.feedback,
                                                                 f"{self.env.user.name}:{record.feedback_parent}"]
                                                final_feedback = "\n".join(feedback_list)
                                                line.feedback = f"{final_feedback}"
                                            elif line.feedback and not record.feedback_parent:
                                                line.feedback = line.feedback
                                            else:
                                                line.feedback = ""
                                        else:
                                            line.approval_status = f"{self.env.user.name}:Approved"
                                            line.approved_time = f"{self.env.user.name}:{dateformat}"
                                            if record.feedback_parent:
                                                line.feedback = f"{self.env.user.name}:{record.feedback_parent}"
                                            else:
                                                line.feedback = ""
                                    line.approved_employee_ids = [(4, current_user)]

                        matrix_line = sorted(record.manpower_matrix_line_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            record.write({'state': 'approved'})
                            self.env.cr.commit()
                            record.assign_mpp()
                        else:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved!'
                    ))
            else:
                raise ValidationError(_(
                    'Already approved!'
                ))

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.man.plan.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_reject':True, 'default_state':'rejected'},
            'target': 'new',
        }
        
    def action_to_reject(self):
        for record in self:
            for user in record.manpower_matrix_line_ids:
                for check_user in user.user_ids:
                    now = datetime.now(timezone(self.env.user.tz))
                    dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
                    if self.env.uid == check_user.id:
                        user.timestamp = fields.Datetime.now()
                        user.approver_state = 'refuse'
                        string_approval = []
                        string_approval.append(user.approval_status)
                        if user.approval_status:
                            string_approval.append(f"{self.env.user.name}:Refused")
                            user.approval_status = "\n".join(string_approval)
                            string_timestammp = [user.approved_time]
                            string_timestammp.append(f"{self.env.user.name}:{dateformat}")
                            user.approved_time = "\n".join(string_timestammp)
                            if record.feedback_parent:
                                user.feedback = f"{self.env.user.name}:{record.feedback_parent}"
                        else:
                            user.approval_status = f"{self.env.user.name}:Refused"
                            user.approved_time = f"{self.env.user.name}:{dateformat}"
                            if record.feedback_parent:
                                user.feedback = f"{self.env.user.name}:{record.feedback_parent}"
            record.approved_user = self.env.user.name + ' ' + 'has been Rejected!'
            record.write({'state': 'rejected'})

    def get_mpp_line(self):
        mpp_line = self.env['manpower.planning.line'].search([]).filtered(
            lambda line: line.manpower_id.name == self.name)
        data_line = []
        if mpp_line:
            ids = [data.id for data in mpp_line]
            data_line.extend(ids)
        return {
            'type': 'ir.actions.act_window',
            'name': 'MPP Lines',
            'res_model': 'manpower.planning.line',
            'view_mode': 'tree',
            # 'context':{'search_default_month':True},
            'domain': [('id', 'in', data_line)]
        }

    @api.onchange('mpp_year')
    def _onchange_mpp_year(self):
        for record in self:
            if record.mpp_year:
                if record.mpp_period:
                    if record.mpp_period.mpp_year.id != record.mpp_year.id:
                        record.mpp_period = False

    def diff_month(self, d1, d2):
        return (d1.year - d2.year) * 12 + d1.month - d2.month

    def append_department_to_line(self, all_department, department_ids, mpp):
        line_ids = []
        if all_department:
            job = self.env['hr.job'].search([])
            if job:
                for record in job:
                    line_ids.append((0, 0, {'department_id': record.department_id.id,
                                            'job_position_id': record.id

                                            }))

        if not all_department and department_ids:
            job = self.env['hr.job'].search([('department_id', 'in', department_ids)])
            if job:
                for record in job:
                    line_ids.append((0, 0, {'department_id': record.department_id.id,
                                            'job_position_id': record.id

                                            }))

        mpp.manpower_line_ids = line_ids

    def delete_line(self):
        for record in self:
            if record.manpower_line_ids:
                line_to_delete_ids = []
                for data in record.manpower_line_ids:
                    line_to_delete_ids.append((2, data.id))
                record.manpower_line_ids = line_to_delete_ids

    def append_all_job(self, work_location):
        job_list = []
        job = self.env['hr.job'].search([])
        if job:
            for data in job:
                job_list.append((0, 0, {'department_id': data.department_id.id,
                                        'job_position_id': data.id,
                                        'work_location_id': work_location,
                                        }))
        return job_list

    def append_job_with_specific_department(self, work_location):
        job_list = []
        department = self.department_ids.ids
        job = self.env['hr.job'].search([('department_id', 'in', department)])
        if job:
            for data in job:
                job_list.append((0, 0, {'department_id': data.department_id.id,
                                        'job_position_id': data.id,
                                        'work_location_id': work_location,
                                        }))
        return job_list

    # @api.onchange('department_ids', 'all_department', 'work_location_ids')
    # def _onchange_department(self):
    #     for record in self:
    #         line_ids = []
    #         if record.department_ids or record.all_department or record.work_location_ids:
    #             record.delete_line()
    #             if record.work_location_ids and record.all_department:
    #                 for work_location in record.work_location_ids.ids:
    #                     line_ids.extend(self.append_all_job(work_location))
    #                 record.manpower_line_ids = line_ids
    #             elif record.department_ids and record.work_location_ids and not record.all_department:
    #                 for work_location in record.work_location_ids.ids:
    #                     line_ids.extend(self.append_job_with_specific_department(work_location))
    #                 record.manpower_line_ids = line_ids

    @api.model
    def create(self, values):
        res = super(equip3ManPowerPlanning, self).create(values)
        # sequence = self.env['ir.sequence'].search([('code', '=', res._name)])
        sequence = self.env['ir.sequence'].next_by_code(res._name)
        if not sequence:
            raise ValidationError("Sequence for Manpower Planning not found")
        # now = datetime.now()
        # split_sequence = str(sequence.next_by_id()).split('/')
        # mpp_number = F"{split_sequence[0]}/{now.year}{now.month}{now.day}/{split_sequence[1]}"
        mpp_number = sequence
        # diff_for_loop = 0
        # diff = 0
        # if res.mpp_period and not res.is_create_manual:
        #     start_period= datetime.strptime(str(res.mpp_period.start_period),"%Y-%m-%d")
        #     end_period= datetime.strptime(str(res.mpp_period.end_period),"%Y-%m-%d")
        #     diff = self.diff_month(end_period,start_period)

        if not res.is_create_manual:
            res.name = mpp_number
            # res.date_start = start_period
            # res.date_end = datetime.strptime(f"{start_period.year}-{start_period.month}-{calendar.monthrange(start_period.year, start_period.month)[1]}","%Y-%m-%d")

        # for month in range(diff):
        #     diff_for_loop +=1
        #     start = start_period + relativedelta(months=diff_for_loop)
        #     end = start_period + relativedelta(months=diff_for_loop)
        #     end_date = datetime.strptime(f"{end.year}-{end.month}-{calendar.monthrange(end.year, end.month)[1]}","%Y-%m-%d")
        #     mpp = self.env['manpower.planning'].create({
        #         # 'date_start':start,'date_end':end_date,
        #                                                 'is_create_manual':True,
        #                                                 'name':mpp_number,'mpp_period':res.mpp_period.id,
        #                                                 'mpp_year':res.mpp_year.id,'mpp_type':res.mpp_type.id,
        #                                                 'department_ids':res.department_ids.ids,
        #                                                 'all_department':res.all_department,
        #                                           })
        #     self.append_department_to_line(res.all_department,res.department_ids.ids,mpp)
        return res


class equip3ManPowerPlanningLine(models.Model):
    _name = "manpower.planning.line"
    _description = "Manpower Planning Line"
    


    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',('department_id.company_id', '=', False),('department_id.company_id', 'in', self.env.companies.ids)])
        return super(equip3ManPowerPlanningLine, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        domain.extend(['|',('department_id.company_id', '=', False),('department_id.company_id', 'in', self.env.companies.ids)])
        return super(equip3ManPowerPlanningLine, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    


    @api.depends('job_position_id')
    def _get_average_wage(self):
        for record in self:
            contract_ids = self.env['hr.contract'].search(
                [('active', '=', True), ('job_id', '=', record.job_position_id.id)])
            if contract_ids:
                total_contract_wage = 0.00
                contract_wage_count = 0.00
                for contract_id in contract_ids:
                    total_contract_wage += contract_id.wage
                    contract_wage_count += 1
                if contract_wage_count > 0.00:
                    average_wage = total_contract_wage / contract_wage_count
                    record.average_wage = average_wage

    @api.depends('job_position_id')
    def _get_total_basic_salary_given(self):
        for record in self:
            contract_ids = self.env['hr.contract'].search(
                [('active', '=', True), ('job_id', '=', record.job_position_id.id)])
            if contract_ids:
                total_contract_wage = 0.00
                for contract_id in contract_ids:
                    total_contract_wage += contract_id.wage
                record.total_basic_salary_given = total_contract_wage
                # if record.basic_salary_budgeted > 0.00:
                #     percentage = record.total_basic_salary_given / record.basic_salary_budgeted
                #     record.percentage_basic_salary = float(percentage) * 100

    @api.depends('job_position_id','total_expected_new_employee','total_fullfillment')
    def _get_percentage_recruited(self):
        for record in self:
            if record.total_expected_new_employee > 0:
                percentage = record.total_fullfillment / record.total_expected_new_employee
                record.per_recruited = float(percentage) * 100

    manpower_id = fields.Many2one('manpower.planning',ondelete='CASCADE')
    mpp_year = fields.Many2one('hr.years', 'MPP Year', related='manpower_id.mpp_year', store=True)
    mpp_type = fields.Many2one('manpower.planning.type', 'MPP Type', related='manpower_id.mpp_type', store=True)
    state = fields.Selection(related="manpower_id.state", string='Status', store=True)
    period_shadow = fields.Integer(compute="_use_mpp_line")
    period = fields.Date()
    department_id = fields.Many2one('hr.department')
    job_position_id = fields.Many2one('hr.job', )
    work_location_id = fields.Many2one('work.location.object')
    current_number_of_employee_shadow = fields.Integer(compute='_set_current_number_of_employee')
    current_number_of_employee = fields.Integer('Current Employee')
    add = fields.Integer()
    replace = fields.Integer()
    total_expected_new_employee = fields.Integer('Expected New Employee')
    total_fullfillment = fields.Integer('Fulfillment')
    total_forecasted_employees = fields.Integer('Forecasted Employee')
    percentage_recruited = fields.Float(string='% Recruited')
    per_recruited = fields.Float(compute='_get_percentage_recruited', string='% Recruited', store=True)
    average_wage = fields.Float(compute='_get_average_wage', group_operator="avg", string='Average Wage', store=True)
    total_basic_salary_given = fields.Float(compute='_get_total_basic_salary_given', string='Total Basic Salary Given',
                                            store=True)

    # fullfilment = fields.Integer()
    department_domain_ids = fields.Many2many('hr.department')
    work_location_ids = fields.Many2many('work.location.object', string="Work Location")
    
    
    @api.onchange('job_position_id','department_id')
    def _onchange_department_department(self):
        for data in self:
            if data.job_position_id or data.department_id:
                if data.job_position_id.department_id.id != data.department_id.id:
                    data.job_position_id = False
    
    
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "{} - {} - {}".format(record.job_position_id.name, record.department_id.name,record.work_location_id.name)))
        return result

    @api.onchange('add', 'replace')
    def _onchange_add_and_replace(self):
        for record in self:
            if record.add or record.replace:
                if record.replace > record.current_number_of_employee:
                    raise ValidationError("Replace cannot greater than Current number of employee")
                record.total_expected_new_employee = record.add + record.replace

    @api.onchange('current_number_of_employee', 'replace', 'add')
    def _onchange_add_and_current_number_of_employee(self):
        for record in self:
            if record.add or record.current_number_of_employee or record.replace:
                record.total_forecasted_employees = record.current_number_of_employee + record.add

    @api.depends('job_position_id','work_location_id')
    def _set_current_number_of_employee(self):
        for record in self:
            if record.job_position_id and record.work_location_id:
                employee = self.env['hr.employee'].search([('job_id', '=', record.job_position_id.id),('location_id','=',record.work_location_id.id)])
                if employee:
                    record.current_number_of_employee = len(employee)
                    record.current_number_of_employee_shadow = len(employee)
                else:
                    record.current_number_of_employee = 0
                    record.current_number_of_employee_shadow = 0
            else:
                record.current_number_of_employee = 0
                record.current_number_of_employee_shadow = 0

    @api.depends('create_date')
    def _use_mpp_line(self):
        for record in self:
            if record.manpower_id:
                # record.period = record.manpower_id.date_start
                record.period_shadow = 1
                domain_ids = []
                if record.manpower_id.all_department:
                    deparment = self.env['hr.department'].search([])
                    department_ids = [data.id for data in deparment]
                    domain_ids.extend(department_ids)
                    record.department_domain_ids = domain_ids
                    print("domain_ids")
                    print(domain_ids)
                else:
                    record.department_domain_ids = record.manpower_id.department_ids.ids

                if record.manpower_id.work_location_ids:
                    record.work_location_ids = record.manpower_id.work_location_ids.ids
                print("record.department_domain_ids")
                print(record.manpower_id.department_ids.ids)
                print(record.department_domain_ids.ids)

            else:
                record.period = False
                record.period_shadow = 0
                record.department_domain_ids = False


class equip3ManPowerPlanningMatrix(models.Model):
    _name = 'manpower.planning.matrix'
    _description = "Manpower Planning Matrix"

    manpower_id = fields.Many2one('manpower.planning')
    sequence = fields.Integer('Sequence', compute="fetch_sl_no")
    approver_id = fields.Many2many('res.users', string="Approvers")
    user_ids = fields.Many2many('res.users', 'man_power_line_user_ids', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'man_power_line_approved_ids', string="Approved user")
    approver_confirm = fields.Many2many('res.users', 'matrix_line_user_manpower_ids', 'user_id',
                                        string="Approvers confirm")
    approval_status = fields.Text()
    timestamp = fields.Text()
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    minimum_approver = fields.Integer(default=1)
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    is_approve = fields.Boolean(string="Is Approve", default=False)
    #parent status
    state = fields.Selection(related='manpower_id.state', string='Parent Status')

    @api.depends('manpower_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.manpower_id.manpower_matrix_line_ids:
            sl = sl + 1
            line.sequence = sl
