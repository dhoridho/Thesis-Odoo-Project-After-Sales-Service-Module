from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
from odoo.exceptions import UserError, Warning
from lxml import etree
import requests
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

headers = {'content-type': 'application/json'}


class TrainingRequest(models.Model):
    _name = 'training.request'
    _description = 'Training Request for Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def _default_employee(self):
        return self.env.user.employee_id

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('training.request') or 'New'
        return super(TrainingRequest, self).create(vals)

    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee', 'Employee', default=_default_employee, domain=_multi_company_domain)
    domain_employee_ids = fields.Many2many('hr.employee', string="Employee Domain", compute='_compute_employee_ids')
    is_readonly = fields.Boolean(compute='_compute_read_only')
    state = fields.Selection(
        [('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'), ('cancelled', 'Cancelled'),
         ('rejected', 'Rejected')],
        string='State', tracking=True, default='draft')
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    training_job_id = fields.Many2many('training.courses', string='Training Required', related='job_id.course_ids')
    course_id = fields.Many2one('training.courses', string='Courses', required=True)
    description = fields.Text('Description')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    company_id = fields.Many2one('res.company', string='Company', tracking=True, default=lambda self: self.env.company)
    training_approver_user_ids = fields.One2many('training.approver.user', 'emp_training_id', string='Approver')
    approvers_ids = fields.Many2many('res.users', 'emp_training_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    training_required = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Training Required")
    is_training_approval_matrix = fields.Boolean("Is Training Approval Matrix", compute='_compute_is_training_approval_matrix')
    state1 = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Submitted'), ('cancelled', 'Cancelled'),
         ('rejected', 'Rejected')],
        string='State', default='draft', tracking=False, copy=False, store=True, compute='_compute_state1')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(TrainingRequest, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(TrainingRequest, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_is_training_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.training_approval_matrix')
            rec.is_training_approval_matrix = setting

    def compare_training_required(self):
        for rec in self:
            if rec.course_id in rec.job_id.course_ids:
                rec.update({'training_required': 'yes'})
            else:
                rec.update({'training_required': 'no'})

    @api.depends('employee_id')
    def _compute_read_only(self):
        for record in self:
            if self.env.user.has_group(
                    'equip3_hr_employee_access_right_setting.group_hr_training_self_service') and not self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_training_supervisor'):
                record.is_readonly = True
            else:
                record.is_readonly = False

    @api.depends('employee_id')
    def _compute_employee_ids(self):
        for record in self:
            employee_ids = []
            if self.env.user.has_group(
                    'equip3_hr_employee_access_right_setting.group_hr_training_supervisor') and not self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_training_manager'):
                my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
                if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(my_employee.id)
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
                record.domain_employee_ids = [(6, 0, employee_ids)]
            else:
                all_employee = self.env['hr.employee'].sudo().search([('company_id','in',self.env.company.ids)])
                for data_employee in all_employee:
                    employee_ids.append(data_employee.id)
                record.domain_employee_ids = [(6, 0, employee_ids)]

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(TrainingRequest, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if self.env.context.get('is_approve_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    def custom_menu_manager(self):
        # views = [(self.env.ref('equip3_hr_training.tree_training_request_to_approve').id, 'tree'),
        #                  (self.env.ref('equip3_hr_training.form_training_request_to_approve').id, 'form')]
        # search_view_id = self.env.ref("hr_contract.hr_contract_view_search")
        search_view_id = self.env.ref("equip3_hr_training.view_hr_training_request_filter")
        if self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_training_supervisor') and not self.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_training_manager'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Training To Approve',
                'res_model': 'training.request',
                'target': 'current',
                'view_mode': 'tree,form',
                # 'views':views,
                'domain': [('employee_id', 'in', employee_ids), ('state', '=', 'to_approve')],
                'context': {'is_approve_manager': True,'search_default_pending_my_approval': 1},
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create a new Training Request
                </p>""",
                # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                # 'search_view_id':search_view_id.id,
                'search_view_id': search_view_id.id,

            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Training Request To Approve',
                'res_model': 'training.request',
                'target': 'current',
                'view_mode': 'tree,form',
                # 'views':views,
                'domain': [('state', '=', 'to_approve')],
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create a new Training Request
                </p>""",
                'context': {'is_approve_manager': True,'search_default_pending_my_approval': 1},
                'search_view_id': search_view_id.id,
            }

    def custom_menu(self):
        # search_view_id = self.env.ref("hr_contract.hr_contract_view_search")
        if self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_training_self_service') and not self.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_training_manager'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'My Training Request',
                'res_model': 'training.request',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                'help': """<p class="o_view_nocontent_smiling_face">
                  Create a new Training Request
                </p>"""
                # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                # 'search_view_id':search_view_id.id,

            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'My Training Request',
                'res_model': 'training.request',
                'target': 'current',
                'view_mode': 'tree,form',
                'help': """<p class="o_view_nocontent_smiling_face">
                  Create a new Training Request
                </p>"""
                # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                # 'search_view_id':search_view_id.id,
            }

    @api.onchange('employee_id', 'course_id')
    def onchange_approver_user(self):
        for training in self:
            training_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.training_approval_matrix')
            if training_setting:
                if training.training_approver_user_ids:
                    remove = []
                    for line in training.training_approver_user_ids:
                        remove.append((2, line.id))
                    training.training_approver_user_ids = remove
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_training.training_type_approval')
                if setting == 'employee_hierarchy':
                    training.training_approver_user_ids = self.training_emp_by_hierarchy(training)
                    self.app_list_training_emp_by_hierarchy()
                if setting == 'approval_matrix':
                    self.training_approval_by_matrix(training)

    def training_emp_by_hierarchy(self, training):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(training, training.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, training, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.training_level')
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
                self.get_manager(training, employee_manager['parent_id'], data, approval_ids, seq)
                break
        return approval_ids

    def get_manager_hierarchy(self, training, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(training, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def app_list_training_emp_by_hierarchy(self):
        for training in self:
            app_list = []
            for line in training.training_approver_user_ids:
                app_list.append(line.user_ids.id)
            training.approvers_ids = app_list

    def training_approval_by_matrix(self, training):
        self.compare_training_required()
        app_list = []
        approval_matrix = self.env['hr.training.approval.matrix'].search(
            [('apply_to', '=', 'by_employee'), ('applicable_to', '=', 'training_request'), ('training_required', '=', training.training_required)])
        matrix = approval_matrix.filtered(lambda line: training.employee_id.id in line.employee_ids.ids)
        if matrix:
            data_approvers = []
            for line in matrix[0].approval_matrix_ids:
                if line.approver_types == "specific_approver":
                    data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                  'user_ids': [(6, 0, line.approvers.ids)]}))
                    for approvers in line.approvers:
                        app_list.append(approvers.id)
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data = 0
                    approvers = self.get_manager_hierarchy(training, training.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            training.approvers_ids = app_list
            training.training_approver_user_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.training.approval.matrix'].search(
                [('apply_to', '=', 'by_job_position'), ('applicable_to', '=', 'training_request'), ('training_required', '=', training.training_required)])
            matrix = approval_matrix.filtered(lambda line: training.job_id.id in line.job_ids.ids)
            if matrix:
                for line in matrix[0].approval_matrix_ids:
                    if line.approver_types == "specific_approver":
                        data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                      'user_ids': [(6, 0, line.approvers.ids)]}))
                        for approvers in line.approvers:
                            app_list.append(approvers.id)
                    elif line.approver_types == "by_hierarchy":
                        manager_ids = []
                        seq = 1
                        data = 0
                        approvers = self.get_manager_hierarchy(training, training.employee_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                training.approvers_ids = app_list
                training.training_approver_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.training.approval.matrix'].search(
                    [('apply_to', '=', 'by_department'), ('applicable_to', '=', 'training_request'), ('training_required', '=', training.training_required)])
                matrix = approval_matrix.filtered(lambda line: training.department_id.id in line.department_ids.ids)
                if matrix:
                    for line in matrix[0].approval_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                          'user_ids': [(6, 0, line.approvers.ids)]}))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(training, training.employee_id, data, manager_ids,
                                                                   seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    training.approvers_ids = app_list
                    training.training_approver_user_ids = data_approvers

    @api.depends('state', 'employee_id')
    def _compute_can_approve(self):
        for training in self:
            if training.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_training.training_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_training.training_level')
                app_level = int(setting_level)
                current_user = training.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(training.training_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(training.training_approver_user_ids)
                    if app < app_level and app < a:
                        if current_user in training.training_approver_user_ids[app].user_ids:
                            training.is_approver = True
                        else:
                            training.is_approver = False
                    else:
                        training.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(training.training_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(training.training_approver_user_ids)
                    if app < a:
                        for line in training.training_approver_user_ids[app]:
                            if current_user in line.user_ids:
                                training.is_approver = True
                            else:
                                training.is_approver = False
                    else:
                        training.is_approver = False

                else:
                    training.is_approver = False
            else:
                training.is_approver = False

    def action_confirm(self):
        setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.training_approval_matrix')
        for rec in self:
            histories = self.env['training.histories'].search(
                [('course_ids', 'in', rec.course_id.id), ('employee_id', '=', rec.employee_id.id)], limit=1)
            if histories:
                raise ValidationError(_(
                    'Can’t be able to Create My Training Request, when Employee and Course, has exist in Training '
                    'Histories. '
                ))
            if setting:
                self.approver_mail()
                self.approver_wa_template()
                self.write({'state': 'to_approve'})
                for line in rec.training_approver_user_ids:
                    line.write({'approver_state': 'draft'})
            else:
                self.write({'state': 'approved'})
                self.env['training.histories'].create({
                    'training_req_id': self.id,
                    'employee_id': self.employee_id.id,
                    'course_ids': self.course_id,
                    'created_by_model': 'by_request',
                })

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'training.request.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':True},
            'target': 'new',
        }
        
        
    def wizard_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'training.request.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':False,
                       'default_is_reject':True},
            'target': 'new',
        }

    def action_approve(self):
        sequence_matrix = [data.name for data in self.training_approver_user_ids]
        sequence_approval = [data.name for data in self.training_approver_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.training_approver_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        for record in self:
            current_user = self.env.uid
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_training.training_type_approval')
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            date_approved = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_approved_obj = datetime.strptime(date_approved, DEFAULT_SERVER_DATE_FORMAT)
            if setting == 'employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.training_approver_user_ids:
                            for hie_user in user.user_ids:
                                if current_user == hie_user.id:
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
                        matrix_line = sorted(
                            record.training_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            self.env['training.histories'].create({
                                'training_req_id': self.id,
                                'employee_id': self.employee_id.id,
                                'course_ids': self.course_id,
                                'created_by_model': 'by_request',
                            })
                            # for course in self.course_ids:
                            #     self.env['training.history.line'].create({
                            #         'employee_id': self.employee_id.id,
                            #         'course_id': course.id
                            #     })
                            record.write({'state': 'approved'})
                            self.approved_mail()
                            self.approved_wa_template()

                        else:
                            record.approved_user = self.env.user.name + ' ' + 'has been approved the Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
                                self.approver_mail()
                                self.approver_wa_template()
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
                        for line in record.training_approver_user_ids:
                            for user in line.user_ids:
                                if current_user == user.user_ids.id:
                                    line.timestamp = fields.Datetime.now()
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

                        matrix_line = sorted(
                            record.training_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            record.write({'state': 'approved'})
                            self.approved_mail()
                            self.approved_wa_template()
                            self.env['training.histories'].create({
                                'training_req_id': self.id,
                                'employee_id': self.employee_id.id,
                                'course_ids': self.course_id,
                                'created_by_model': 'by_request',
                            })
                            # for course in self.course_ids:
                            #     self.env['training.history.line'].create({
                            #         'employee_id': self.employee_id.id,
                            #         'course_id': course.id
                            #     })

                        else:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
                                self.approver_mail()
                                self.approver_wa_template()
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
        for record in self:
            for user in record.training_approver_user_ids:
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
            self.reject_mail()
            self.rejected_wa_template()

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise Warning("You can delete My Training Request only state Draft.")
            return super(TrainingRequest, rec).unlink()

    # Emails
    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_training', 'sub_menu_training_request_manager')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_training', 'action_training_request_manager')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=training.request&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.training_approver_user_ids:
                matrix_line = sorted(rec.training_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.training_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_training',
                            'email_template_training_request_approval')[1]
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
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id, force_send=True)
                break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.training_approver_user_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_training',
                        'email_template_training_request_approved')[1]
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
            if rec.training_approver_user_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_training',
                        'email_template_training_request_rejection')[1]
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
                self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                          force_send=True)
            break

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.send_by_wa_training')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if send_by_wa:
            template = self.env.ref('equip3_hr_training.training_request_approver_wa_template')
            wa_sender = waParam()
            if template:
                url = self.get_url(self)
                if self.training_approver_user_ids:
                    matrix_line = sorted(self.training_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.training_approver_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", self.employee_id.name)
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.name)
                        if "${course_name}" in string_test:
                            string_test = string_test.replace("${course_name}", self.course_id.name)
                        if "${br}" in string_test:
                            string_test = string_test.replace("${br}", f"\n")
                        if "${url}" in string_test:
                            string_test = string_test.replace("${url}", url)
                        phone_num = str(user.mobile_phone)
                        if "+" in phone_num:
                            phone_num = int(phone_num.replace("+", ""))
                        
                        wa_sender.set_wa_string(string_test,template._name,template_id=template)
                        wa_sender.send_wa(phone_num)

                        print("============= TEST ===========")
                        print(string_test)
                        
                        # param = {'body': string_test, 'phone': phone_num}
                        # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                        # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                        # try:
                        #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                        #                                    headers=headers, verify=True)
                        # except ConnectionError:
                        #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.send_by_wa_training')
        if send_by_wa:
            template = self.env.ref('equip3_hr_training.training_request_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.training_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${leave_name}" in string_test:
                        string_test = string_test.replace("${leave_name}", self.holiday_status_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
                    if "${course_name}" in string_test:
                        string_test = string_test.replace("${course_name}", self.course_id.name)
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)
                    if "+" in phone_num:
                        phone_num = int(phone_num.replace("+", ""))
                    if "${url}" in string_test:
                        string_test = string_test.replace("${url}", url)
                    
                    wa_sender.set_wa_string(string_test,template._name,template_id=template)
                    wa_sender.send_wa(phone_num)

                    print("============= TEST ===========")
                    print(string_test)
                    
                    # param = {'body': string_test, 'phone': phone_num}
                    # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                    # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                    # try:
                    #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                    #                                    headers=headers, verify=True)
                    # except ConnectionError:
                    #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def rejected_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.send_by_wa_training')
        if send_by_wa:
            template = self.env.ref('equip3_hr_training.training_request_rejected_wa_template')
            url = self.get_url(self)
            wa_sender = waParam()
            if template:
                if self.training_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${leave_name}" in string_test:
                        string_test = string_test.replace("${leave_name}", self.holiday_status_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
                    if "${course_name}" in string_test:
                        string_test = string_test.replace("${course_name}", self.course_id.name)
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)
                    # if "+" in phone_num:
                    #     phone_num = int(phone_num.replace("+", ""))
                    
                    wa_sender.set_wa_string(string_test,template._name,template_id=template)
                    wa_sender.send_wa(phone_num)

                    print("============= TEST ===========")
                    print(string_test)
                    
                    # param = {'body': string_test, 'phone': phone_num}
                    # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                    # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                    # try:
                    #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                    #                                    headers=headers, verify=True)
                    # except ConnectionError:
                    #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_training = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.number_of_repetitions_training'))
        training_approve = self.search([('state', '=', 'to_approve')])
        for rec in training_approve:
            if rec.training_approver_user_ids:
                matrix_line = sorted(rec.training_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.training_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_training',
                            'email_template_training_request_approval')[1]
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
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_training - 1
                        query_statement = """UPDATE training_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE training_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        training_approve = self.search([('state', '=', 'to_approve')])
        for rec in training_approve:
            if rec.training_approver_user_ids:
                matrix_line = sorted(rec.training_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.training_approver_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_training',
                                    'email_template_training_request_approval')[1]
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
                            approver.update({
                                'user_ids': [(4, user.user_delegation_id.id)],
                                'is_delegation_mail_sent': True,
                            })
                            rec.update({
                                'approvers_ids': [(4, user.user_delegation_id.id)],
                            })
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

class TrainingApproverUser(models.Model):
    _name = 'training.approver.user'

    emp_training_id = fields.Many2one('training.request', string="Employee Training Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'emp_training_user_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    #Auto follow
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'training_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='emp_training_id.state')


    @api.depends('emp_training_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.emp_training_id.training_approver_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.emp_training_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.emp_training_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids
