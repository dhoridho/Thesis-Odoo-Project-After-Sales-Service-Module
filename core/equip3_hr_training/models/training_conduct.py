from datetime import datetime
from odoo import SUPERUSER_ID, api, fields, models, _
from odoo.exceptions import ValidationError
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
from dateutil.relativedelta import relativedelta
from datetime import date
import base64
from odoo.exceptions import UserError, Warning
from lxml import etree
import requests
from odoo.tools.safe_eval import safe_eval
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

headers = {'content-type': 'application/json'}


class TrainingConduct(models.Model):
    _name = 'training.conduct'
    _description = 'Training Conduct for Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    AVAILABLE_PRIORITIES = [
        ('0', 'Normal'),
        ('1', 'Good'),
        ('2', 'Very Good'),
        ('3', 'Excellent')
    ]

    @api.model
    def create(self, vals):
        now = datetime.now(timezone(self.env.user.tz))
        sequence = self.env['ir.sequence'].search([('code', '=', 'training.conduct')])
        if not sequence:
            raise ValidationError("Sequence For Training Conduct Not Found")
        split_sequence = str(sequence.next_by_id()).split("/")
        used_sequence = f"{split_sequence[0]}/{split_sequence[1]}/{now.month}/{now.day}/{split_sequence[2]}"
        vals['name'] = used_sequence.replace(" ", "")
        return super(TrainingConduct, self).create(vals)

    @api.onchange('course_id')
    def onchange_course_id(self):
        if self.course_id:
            self.conduct_line_ids = False
            for course in self.env['hr.job'].search([('course_ids', '=', self.course_id.id)]):
                for employee in self.env['hr.employee'].search([('job_id', '=', course.id)]):
                    self.conduct_line_ids.create({
                        'conduct_id': self.id,
                        'employee_id': employee.id,
                    })

    def _default_employee(self):
        return self.env.user.employee_id

    name = fields.Char(string='Name', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', default=_default_employee)
    employee_ids = fields.Many2many('hr.employee', 'training_employee_rel', string='Trainer')
    external_trainer = fields.Char(string='External Trainer')
    state = fields.Selection(
        [('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'), ('cancelled', 'Cancelled'),
         ('rejected', 'Rejected')],
        string='State', tracking=True, default='draft')
    current_stage = fields.Char(string='current stage', compute='_compute_current_stage')
    stage_id = fields.Many2one('training.stages', copy=False, index=True,
                               group_expand='_read_group_stage_ids')
    stage_course_id = fields.Many2one('training.courses.stages', domain="[('id','in',stage_course_domain_ids)]")
    stage_course_domain_ids = fields.Many2many('training.courses.stages', compute='_domain_stage_ids')
    trainer_type = fields.Selection([('internal', 'Internal'), ('external', 'External')], default='internal',
                                    string='Trainer type',
                                    tracking=True)
    estimated_currency = fields.Selection(
        [('idr', 'IDR'), ('eur', 'EUR'), ('usd', 'USD')], string='Estimated Currency', tracking=True, default='idr')
    estimated_cost = fields.Float(string='Estimated Cost', tracking=True)
    course_id = fields.Many2one('training.courses', string='Training Courses', required=True)
    start_date = fields.Date('Date Start', tracking=True)
    end_date = fields.Date('Date Completed', tracking=True)
    category_id = fields.Many2one('training.category', string='Training Category')
    minimal_score = fields.Float('Minimal Score', tracking=True)
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, tracking=True)
    created_date = fields.Date(string='Created Date', default=fields.Datetime.now, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', tracking=True, default=lambda self: self.env.company)
    conduct_line_ids = fields.One2many('training.conduct.line', 'conduct_id', string='Training Conduct Line')
    venue_id = fields.Many2one('res.partner', string='Venue', tracking=True)
    responsible_ids = fields.Many2many('hr.employee', 'responsible_rel', string='Responsible')
    color = fields.Integer("Color Index", default=0)
    priority = fields.Selection(AVAILABLE_PRIORITIES, "Appreciation", default='0')
    participations_count = fields.Integer(compute="_get_participations_count")
    sequence = fields.Integer("Sequence")
    is_next_stage_hide = fields.Boolean('Hide Move to Next Button', default=False)
    certificate_hide = fields.Boolean('Hide Certificate Button', default=False)
    is_approved = fields.Boolean('Hide Approve/Reject Button', default=False)
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    training_approver_user_ids = fields.One2many('training.conduct.approver.user', 'emp_training_id', string='Approver')
    approvers_ids = fields.Many2many('res.users', 'emp_training_conduct_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    # Certificate Template
    certificate = fields.Boolean(string="Certificate")
    certificate_template = fields.Many2one('hr.certificate.template')
    #pre/post test
    edit_score = fields.Boolean('Edit Score Based on Approves', compute='_compute_edit_score')
    is_next_stage_executed = fields.Boolean(default=False)
    training_level_id = fields.Many2one('training.level', string='Training Level', tracking=True, required=True)
    is_training_approval_matrix = fields.Boolean("Is Training Approval Matrix", compute='_compute_is_training_approval_matrix')
    state1 = fields.Many2one('training.courses.stages', compute='_compute_state1')
    
    
    @api.onchange('training_level_id')
    def _onchange_training_level_id(self):
        for data in self:
            data.minimal_score = data.training_level_id.target
        

    @api.depends('stage_course_id')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.stage_course_id

    def _compute_is_training_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.training_approval_matrix')
            rec.is_training_approval_matrix = setting


    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(TrainingConduct, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_training_manager') and not self.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_training_director'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_training_director'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)

        return res

    @api.onchange('trainer_type')
    def onchange_trainer_type(self):
        for rec in self:
            if rec.trainer_type == 'internal':
                rec.venue_id = False
                rec.external_trainer = ''
                rec.responsible_ids = [(5,0,0)]
            elif rec.trainer_type == 'external':
                rec.employee_ids = [(5,0,0)]

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

    @api.onchange('conduct_line_ids')
    def onchange_conduct_line(self):
        if self.conduct_line_ids:
            if self.conduct_line_ids.employee_id:
                domain = [data.id for data in self.conduct_line_ids.employee_id]
                for rec in self.conduct_line_ids:
                    rec.employee_domain_ids = [(6,0,domain)]

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
        app_list = []
        approval_matrix = self.env['hr.training.approval.matrix'].search(
            [('apply_to', '=', 'by_employee'), ('applicable_to', '=', 'training_conduct')])
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
                [('apply_to', '=', 'by_job_position'), ('applicable_to', '=', 'training_conduct')])
            matrix = approval_matrix.filtered(lambda line: training.employee_id.job_id.id in line.job_ids.ids)
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
                    [('apply_to', '=', 'by_department'), ('applicable_to', '=', 'training_conduct')])
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

    @api.depends('stage_course_id')
    def _compute_current_stage(self):
        for training in self:
            if training.stage_course_id:
                training.current_stage = training.stage_course_id.stage_id.name
            else:
                training.current_stage = ''

    @api.depends('state', 'employee_id')
    def _compute_can_approve(self):
        for training in self:
            if training.approvers_ids and training.state != 'draft':
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

    @api.depends('state')
    def _compute_edit_score(self):
        for rec in self:
            current_user = rec.env.user
            if rec.state == 'draft':
                rec.edit_score = True
            elif current_user in rec.approvers_ids and rec.state in ('draft', 'to_approve', 'approved'):
                rec.edit_score = True
            else:
                rec.edit_score = False

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'training.conduct.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':True},
            'name': "Confirmation Message",
            'target': 'new',
        }
        
        
    def wizard_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'training.conduct.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':False,
                       'default_is_reject':True},
            'name': "Confirmation Message",
            'target': 'new',
        }

    def _get_participations_count(self):
        for record in self:
            count = 0
            survey_user_input = self.env['survey.user_input'].search([('training_id', '=', record.id)])
            if survey_user_input:
                for data in survey_user_input:
                    count += 1
            record.participations_count = count

    def get_participations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Participations'),
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('training_id', '=', self.id)],
            'context': {'search_default_group_by_employee': True, 'search_default_group_by_test_type': True}

        }

    @api.model
    def ir_cron_move_stage(self):
        # now = datetime.now(timezone(self.env.user.tz))
        now = datetime.now(timezone(self.env.user.tz) if self.env.user.tz else timezone('UTC'))
        start_stage_ref = self.env.ref('equip3_hr_training.course_stage_3').id
        approved_stage_ref = self.env.ref('equip3_hr_training.course_stage_2').id
        complete_stage_ref = self.env.ref('equip3_hr_training.course_stage_4').id
        conduct_start = self.env['training.conduct'].search(
            [('start_date', '<=', now.date()), ('stage_id', '=', approved_stage_ref)])

        conduct_end = self.env['training.conduct'].search(
            [('end_date', '<=', now.date()), ('stage_id', '=', start_stage_ref)])
        if conduct_end:
            for data_end in conduct_end:
                end_stage = data_end.course_id.stage_ids.filtered(lambda line: line.stage_id.id == complete_stage_ref)
                if end_stage:
                    data_end.stage_course_id = end_stage.id
                    data_end.stage_id = end_stage.stage_id.id

        if conduct_start:
            for data_start in conduct_start:
                start_stage = data_start.course_id.stage_ids.filtered(lambda line: line.stage_id.id == start_stage_ref)
                if start_stage:
                    data_start.stage_course_id = start_stage.id
                    data_start.stage_id = start_stage.stage_id.id

        # Expiry State Update
        today = date.today()
        for rec in self.env['training.histories'].search(
                [('state', '!=', 'expired'), ('expiry_date', '<=', today)]):
            if rec.expiry_date:
                rec.state = 'expired'
            else:
                rec.state = rec.state
        # Failed state Update
        for training_failed_rec in self.env['training.history.line'].search(
                [('state', '!=', 'failed'), ('training_conduct_line_id.status', '=', 'Failed'),
                 ('created_by_model', 'not in', ['by_failed'])]):
            if training_failed_rec:
                # Instead up updating a 'Failed' state, creating a new row

                self.env['training.history.line'].create({
                    'training_conduct_id': training_failed_rec.training_conduct_id.id,
                    'training_conduct_line_id': training_failed_rec.training_conduct_line_id.id,
                    'course_id': training_failed_rec.course_id.id,
                    'employee_id': training_failed_rec.employee_id.id,
                    'state': training_failed_rec.state,
                    'created_by_model': 'by_failed',
                })
                training_failed_rec.state = 'failed'
                training_failed_rec.created_by_model = 'by_failed'
            else:
                training_failed_rec.state = training_failed_rec.state
        # Expiry State Update
        for training_rec in self.env['training.history.line'].search(
                [('state', '!=', 'expired'), ('expiry_date', '<=', today), ('created_by_model', '!=', 'by_expiry')]):
            if training_rec.expiry_date:
                # Instead up updating a 'Expired' state, creating a new row
                self.env['training.history.line'].create({
                    'training_conduct_id': training_rec.training_conduct_id.id,
                    'training_conduct_line_id': training_rec.training_conduct_line_id.id,
                    'expiry_date': training_rec.expiry_date,
                    'course_id': training_rec.course_id.id,
                    'employee_id': training_rec.employee_id.id,
                    'state': training_rec.state,
                    'created_by_model': 'by_expiry',
                })
                training_rec.state = 'expired'
                training_rec.created_by_model = 'by_expiry'
            else:
                training_rec.state = training_rec.state

        # Update Training Histories by job
        self.update_histories_by_job()
        self.update_history_by_job()
        self.delete_by_job()

    # Update Training Histories by job
    def update_histories_by_job(self):
        histories = self.env['training.histories'].search([])
        if len(histories) == 0:
            for employee in self.env['hr.employee'].search(
                    [('job_id', '!=', False), ('job_id.course_ids', '!=', False)]):
                course_len = len(employee.job_id.course_ids)
                if course_len == 1:
                    self.env['training.histories'].create({
                        'course_ids': employee.job_id.course_ids.ids,
                        'employee_id': employee.id,
                        'training_required': 'yes',
                        'created_by_model': 'by_job',
                    })
                else:
                    for course_counts in employee.job_id.course_ids:
                        self.env['training.histories'].create({
                            'course_ids': course_counts,
                            'employee_id': employee.id,
                            'training_required': 'yes',
                            'created_by_model': 'by_job',
                        })
        # Don't delete this code
        # else:
        #     for employee in self.env['hr.employee'].search(
        #             [('job_id', '!=', False), ('job_id.course_ids', '!=', False)]):
        #         histories = self.env['training.histories'].search(
        #             [('course_ids', 'in', employee.job_id.course_ids.ids), ('employee_id', '=', employee.id)], limit=1)
        #         if not histories:
        #             course_len = len(employee.job_id.course_ids)
        #             if course_len == 1:
        #                 self.env['training.histories'].create({
        #                     'course_ids': employee.job_id.course_ids.ids,
        #                     'employee_id': employee.id,
        #                     'created_by_model': 'by_job',
        #                 })
        #             else:
        #                 for course_counts in employee.job_id.course_ids:
        #                     self.env['training.histories'].create({
        #                         'course_ids': course_counts,
        #                         'employee_id': employee.id,
        #                         'created_by_model': 'by_job',
        #                     })
        else:
            for employee in self.env['hr.employee'].search(
                    [('job_id', '!=', False), ('job_id.course_ids', '!=', False)]):
                course_len = len(employee.job_id.course_ids)
                if course_len == 1:
                    histories = self.env['training.histories'].search(
                        [('course_ids', 'in', employee.job_id.course_ids.ids), ('employee_id', '=', employee.id)],
                        limit=1)
                    if not histories:
                        self.env['training.histories'].create({
                            'course_ids': employee.job_id.course_ids.ids,
                            'employee_id': employee.id,
                            'training_required': 'yes',
                            'created_by_model': 'by_job',
                        })
                else:
                    for course_counts in employee.job_id.course_ids:
                        histories = self.env['training.histories'].search(
                            [('course_ids', 'in', course_counts.id), ('employee_id', '=', employee.id)], limit=1)
                        if not histories:
                            self.env['training.histories'].create({
                                'course_ids': course_counts,
                                'employee_id': employee.id,
                                'training_required': 'yes',
                                'created_by_model': 'by_job',
                            })

    def update_history_by_job(self):
        for employee in self.env['hr.employee'].search([('job_id', '!=', False), ('job_id.course_ids', '!=', False)]):
            if len(employee.training_history_ids) == 0:
                for course_counts in employee.job_id.course_ids:
                    self.env['training.history.line'].create({
                        'course_id': course_counts.id,
                        'employee_id': employee.id,
                        'state': 'to_do',
                        'created_by_model': 'by_job',
                    })
            else:
                if len(employee.job_id.course_ids) == 1:
                    history = self.env['training.history.line'].search(
                        [('course_id', 'in', employee.job_id.course_ids.ids), ('employee_id', '=', employee.id)],
                        limit=1)
                    if not history:
                        self.env['training.history.line'].create({
                            'course_id': employee.job_id.course_ids.id,
                            'employee_id': employee.id,
                            'state': 'to_do',
                            'created_by_model': 'by_job',
                        })
                else:
                    for course_counts in employee.job_id.course_ids:
                        history = self.env['training.history.line'].search(
                            [('course_id', '=', course_counts.id), ('employee_id', '=', employee.id)], limit=1)
                        if not history:
                            self.env['training.history.line'].create({
                                'course_id': course_counts.id,
                                'employee_id': employee.id,
                                'state': 'to_do',
                                'created_by_model': 'by_job',
                            })

    def delete_by_job(self):
        # Training Histories
        for by_job_histories in self.env['training.histories'].search([('created_by_model', '=', 'by_job')]):
            if not by_job_histories.job_id.course_ids or by_job_histories.course_ids not in by_job_histories.job_id.course_ids:
                by_job_histories.unlink()

        # Training History
        for by_job_history in self.env['training.history.line'].search([('created_by_model', '=', 'by_job')]):
            if not by_job_history.employee_id.job_id.course_ids or by_job_history.course_id not in by_job_history.employee_id.job_id.course_ids:
                by_job_history.unlink()

    def write(self, vals):
        if 'stage_id' in vals:

            send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.send_by_wa_training')
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')

            stage_course_id = self.course_id.stage_ids.filtered(lambda line: line.stage_id.id == vals['stage_id'])
            template = self.env.ref('equip3_hr_training.mail_template_invite_test', raise_if_not_found=False)
            if stage_course_id:
                self.stage_course_id = stage_course_id.id
                if stage_course_id.survey_pre_test_id:
                    for employee in self.conduct_line_ids:
                        survey_pretest = self.env['survey.invite'].create(
                            {'survey_id': stage_course_id.survey_pre_test_id.id,
                             'emails': str(employee.employee_id.work_email), 'template_id': template.id})
                        context = self.env.context = dict(self.env.context)
                        survey_url = survey_pretest.survey_start_url + f"?surveyId={stage_course_id.survey_pre_test_id.id}&trainingId={self.id}&employeeId={employee.employee_id.id}&testType=1"
                        context.update({
                            'email_to': employee.employee_id.work_email,
                            'name': employee.employee_id.name,
                            'url_test': survey_url,
                            'title': stage_course_id.survey_pre_test_id.title,
                            'test_type': "Pre-test",
                            'test_name': stage_course_id.survey_pre_test_id.title

                        })
                        template.send_mail(self.id, force_send=True)
                        template.with_context(context)
                        if send_by_wa:
                            wa_template = self.env.ref('equip3_hr_training.training_conduct_invite_wa_template')
                            if wa_template:
                                string_test = str(wa_template.message)
                                if "${name}" in string_test:
                                    string_test = string_test.replace("${name}", employee.employee_id.name)
                                if "${test_type}" in string_test:
                                    string_test = string_test.replace("${test_type}", "Pre-test")
                                if "${test_name}" in string_test:
                                    string_test = string_test.replace("${test_name}",
                                                                      stage_course_id.survey_pre_test_id.title)
                                if "${course_name}" in string_test:
                                    string_test = string_test.replace("${course_name}", self.course_id.name)
                                if "${br}" in string_test:
                                    string_test = string_test.replace("${br}", f"\n")
                                if "${url}" in string_test:
                                    string_test = string_test.replace("${url}", survey_url)
                                phone_num = str(employee.employee_id.mobile_phone)
                                if "+" in phone_num:
                                    phone_num = int(phone_num.replace("+", ""))
                                param = {'body': string_test, 'phone': phone_num}
                                domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                                token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                                try:
                                    request_server = requests.post(f'{domain}/sendMessage?token={token}',
                                                                   params=param,
                                                                   headers=headers, verify=True)
                                except ConnectionError:
                                    raise ValidationError(
                                        "Not connect to API Chat Server. Limit reached or not active")
                if stage_course_id.survey_post_test_id:
                    for employee in self.conduct_line_ids:
                        survey_post_test = self.env['survey.invite'].create(
                            {'survey_id': stage_course_id.survey_post_test_id.id,
                             'emails': str(employee.employee_id.work_email), 'template_id': template.id})
                        context = self.env.context = dict(self.env.context)
                        survey_url = survey_post_test.survey_start_url + f"?surveyId={stage_course_id.survey_pre_test_id.id}&trainingId={self.id}&employeeId={employee.employee_id.id}&testType=2"
                        context.update({
                            'email_to': employee.employee_id.work_email,
                            'name': employee.employee_id.name,
                            'url_test': survey_url,
                            'title': stage_course_id.survey_post_test_id.title,
                            'test_type': "Post-test",
                            'test_name': stage_course_id.survey_post_test_id.title
                        })
                        template.send_mail(self.id, force_send=True)
                        template.with_context(context)
                        if send_by_wa:
                            wa_template = self.env.ref('equip3_hr_training.training_conduct_invite_wa_template')
                            if wa_template:
                                string_test = str(wa_template.message)
                                if "${name}" in string_test:
                                    string_test = string_test.replace("${name}", employee.employee_id.name)
                                if "${test_type}" in string_test:
                                    string_test = string_test.replace("${test_type}", "Post-test")
                                if "${test_name}" in string_test:
                                    string_test = string_test.replace("${test_name}",
                                                                      stage_course_id.survey_post_test_id.title)
                                if "${course_name}" in string_test:
                                    string_test = string_test.replace("${course_name}", self.course_id.name)
                                if "${br}" in string_test:
                                    string_test = string_test.replace("${br}", f"\n")
                                if "${url}" in string_test:
                                    string_test = string_test.replace("${url}", survey_url)
                                phone_num = str(employee.employee_id.mobile_phone)
                                if "+" in phone_num:
                                    phone_num = int(phone_num.replace("+", ""))
                                param = {'body': string_test, 'phone': phone_num}
                                domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                                token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                                try:
                                    request_server = requests.post(f'{domain}/sendMessage?token={token}',
                                                                   params=param,
                                                                   headers=headers, verify=True)
                                except ConnectionError:
                                    raise ValidationError(
                                        "Not connect to API Chat Server. Limit reached or not active")



            else:
                stage = self.env['training.stages'].search([('id', '=', vals['stage_id'])])
                if stage:
                    raise ValidationError(f"Course {self.course_id.name} dont have stage {stage.name}")
        res = super(TrainingConduct, self).write(vals)
        return res

    def get_menu(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Training Conduct',
            'res_model': 'training.conduct',
            'view_mode': 'tree,kanban,form,calendar',
            'domain': [],
            'context': {}

        }

    def get_menu_by_course(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Training Conduct',
            'res_model': 'training.conduct',
            'view_mode': 'kanban,form,calendar',
            'domain': [],
            'context': {'search_default_course_id': self.env.context.get('active_id'),
                        'default_course_id': self.env.context.get('active_id')}

        }

    @api.depends('course_id')
    def _domain_stage_ids(self):
        for record in self:
            domain_stages = []
            domain_second_stages = []
            if record.course_id:
                if record.course_id.stage_ids:
                    domain_stages.extend(data.id for data in record.course_id.stage_ids)
                    domain_second_stages.extend(data.stage_id.id for data in record.course_id.stage_ids)
                record.stage_course_domain_ids = [(6, 0, domain_stages)]
            else:
                record.stage_course_domain_ids = False

    @api.onchange('course_id')
    def _onchange_course_id(self):
        for record in self:
            if record.stage_course_domain_ids:
                record.stage_course_id = record.stage_course_domain_ids[0]._origin.id
                record.stage_id = record.stage_course_domain_ids[0]._origin.stage_id.id

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = []
        stage_course_ids = []
        course_id = self._context.get('default_course_id')
        if course_id:
            course = self.env['training.courses'].search([('id', '=', course_id)])
            if course:
                if course.stage_ids:
                    stage_course_ids.extend(data.stage_id.id for data in course.stage_ids)
            search_domain = [('id', 'in', stage_course_ids)]
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        if stage_course_ids:
            return stages.browse(stage_course_ids)
        return stages.browse(stage_ids)

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.send_by_wa_training')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if send_by_wa:
            template = self.env.ref('equip3_hr_training.training_conduct_approver_wa_template')
            wa_sender = waParam()
            if template:
                url = self.get_url(self)
                if self.training_approver_user_ids:
                    matrix_line = sorted(self.training_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.training_approver_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            emp_list = []
                            for employee in self.employee_ids:
                                emp_list.append(employee.name)
                            listToStr = ' '.join([str(elem) for elem in emp_list])
                            string_test = string_test.replace("${employee_name}", listToStr)
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.name)
                        if "${course_name}" in string_test:
                            string_test = string_test.replace("${course_name}", self.course_id.name)
                        if "${start_date}" in string_test:
                            string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                                self.start_date).strftime('%d/%m/%Y'))
                        if "${end_date}" in string_test:
                            string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                                self.end_date).strftime('%d/%m/%Y'))
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
                        #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                        #                                    headers=headers, verify=True)
                        # except ConnectionError:
                        #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.send_by_wa_training')
        if send_by_wa:
            template = self.env.ref('equip3_hr_training.training_conduct_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.training_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
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
            template = self.env.ref('equip3_hr_training.training_conduct_rejected_wa_template')
            url = self.get_url(self)
            wa_sender = waParam()
            if template:
                if self.training_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
                    if "${course_name}" in string_test:
                        string_test = string_test.replace("${course_name}", self.course_id.name)
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)

                    wa_sender.set_wa_string(string_test,template._name,template_id=template)
                    wa_sender.send_wa(phone_num)

                    # if "+" in phone_num:
                    #     phone_num = int(phone_num.replace("+", ""))
                    # param = {'body': string_test, 'phone': phone_num}
                    # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                    # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                    # try:
                    #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                    #                                    headers=headers, verify=True)
                    # except ConnectionError:
                    #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def action_confirm(self):
        setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.training_approval_matrix')
        if setting:
            self.write({'state': 'to_approve'})
            approved_stage_ref = self.env.ref('equip3_hr_training.course_stage_7').id
            stages = self.env['training.stages'].search([('id', '=', approved_stage_ref)], limit=1)
            stage_course = self.env['training.courses.stages'].search(
                [('course_id', '=', self.course_id.id), ('stage_id', '=', stages.id)], limit=1)
            self.write({'stage_id': stages.id, 'stage_course_id': stage_course.id, 'sequence': stages.sequence})
            self.approver_mail()
            self.approver_wa_template()
            for line in self.training_approver_user_ids:
                line.write({'approver_state': 'draft'})
        else:
            approved_stage_ref = self.env.ref('equip3_hr_training.course_stage_2').id
            stages = self.env['training.stages'].search([('id', '=', approved_stage_ref)], limit=1)
            stage_course = self.env['training.courses.stages'].search(
                [('course_id', '=', self.course_id.id), ('stage_id', '=', stages.id)], limit=1)
            self.write({'stage_id': stages.id, 'stage_course_id': stage_course.id, 'is_approved': True, 'sequence': stages.sequence})
            self.write({'state': 'approved'})


    def action_approve(self):
        sequence_matrix = [data.name for data in self.training_approver_user_ids]
        sequence_approval = [data.name for data in self.training_approver_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.training_approver_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        approved_stage_ref = self.env.ref('equip3_hr_training.course_stage_2').id
        stages = self.env['training.stages'].search([('id', '=', approved_stage_ref)], limit=1)
        stage_course = self.env['training.courses.stages'].search(
            [('course_id', '=', self.course_id.id), ('stage_id', '=', stages.id)], limit=1)

        for record in self:
            current_user = self.env.uid
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.training_type_approval')
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            date_approved = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_approved_obj = datetime.strptime(date_approved, DEFAULT_SERVER_DATE_FORMAT)
            if setting == 'employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.training_approver_user_ids:
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
                        matrix_line = sorted(
                            record.training_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.write({'state': 'approved'})
                            self.write({'stage_id': stages.id, 'stage_course_id': stage_course.id, 'is_approved': True,
                                        'sequence': stages.sequence})
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
                            self.write({'stage_id': stages.id, 'stage_course_id': stage_course.id, 'is_approved': True,
                                        'sequence': stages.sequence})
                            self.approved_mail()
                            self.approved_wa_template()
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

        for line in self.conduct_line_ids:
            if self.course_id.renewable > 0:
                # Training Histories
                for training_histories_rec1 in self.env['training.histories'].search(
                        [('course_ids', 'in', self.course_id.id), ('employee_id', '=', line.employee_id.id)],
                ):
                    if training_histories_rec1:
                        training_histories_rec1.update({
                            'training_conduct_id': self.id,
                            'training_conduct_line_id': line.id,
                            'expiry_date': self.end_date + relativedelta(months=self.course_id.renewable),
                            'created_by_model': 'by_update_from_conduct',
                        })
                        training_histories_rec1.update_state()
                        # training_histories_rec1.required_update()
                histories_1 = self.env['training.histories'].search(
                    [('course_ids', 'in', self.course_id.id), ('employee_id', '=', line.employee_id.id)], limit=1)
                if not histories_1:
                    training_histories1 = self.env['training.histories'].create({
                        'training_conduct_id': self.id,
                        'training_conduct_line_id': line.id,
                        'course_ids': self.course_id,
                        'employee_id': line.employee_id.id,
                        'expiry_date': self.end_date + relativedelta(months=self.course_id.renewable),
                        'created_by_model': 'by_conduct',
                    })
                    training_histories1.update_state()
                    # training_histories1.required_update()
                # Training History
                for training_history_line_rec1 in self.env['training.history.line'].search(
                        [('course_id', '=', self.course_id.id), ('employee_id', '=', line.employee_id.id)],
                ):
                    if training_history_line_rec1 and not (
                            training_history_line_rec1.training_conduct_id or training_history_line_rec1.training_conduct_id == self.id):
                        training_history_line_rec1.update({
                            'training_conduct_id': self.id,
                            'training_conduct_line_id': line.id,
                            'expiry_date': self.end_date + relativedelta(months=self.course_id.renewable),
                            'created_by_model': 'by_update_from_conduct',
                        })
                        training_history_line_rec1.update_state()
                history_1 = self.env['training.history.line'].search(
                    [('course_id', '=', self.course_id.id), ('employee_id', '=', line.employee_id.id),
                     ('training_conduct_id', '=', self.id)], limit=1)
                if not history_1:
                    training_history1 = self.env['training.history.line'].create({
                        'training_conduct_id': self.id,
                        'training_conduct_line_id': line.id,
                        'course_id': self.course_id.id,
                        'employee_id': line.employee_id.id,
                        'date_completed': self.end_date,
                        'expiry_date': self.end_date + relativedelta(months=self.course_id.renewable),
                        'created_by_model': 'by_conduct',
                    })
                    training_history1.update_state()
            else:
                # Training Histories
                for training_histories_rec2 in self.env['training.histories'].search(
                        [('course_ids', 'in', self.course_id.id), ('employee_id', '=', line.employee_id.id)]):
                    if training_histories_rec2:
                        training_histories_rec2.update({
                            'training_conduct_id': self.id,
                            'training_conduct_line_id': line.id,
                            'created_by_model': 'by_update_from_conduct',
                        })
                        training_histories_rec2.update_state()
                        # training_histories_rec2.required_update()
                histories_2 = self.env['training.histories'].search(
                    [('course_ids', 'in', self.course_id.id), ('employee_id', '=', line.employee_id.id)], limit=1)
                if not histories_2:
                    training_histories2 = self.env['training.histories'].create({
                        'training_conduct_id': self.id,
                        'training_conduct_line_id': line.id,
                        'course_ids': self.course_id,
                        'employee_id': line.employee_id.id,
                        'created_by_model': 'by_conduct',
                    })
                    training_histories2.update_state()
                    # training_histories2.required_update()

                # Training History
                for training_history_line_rec2 in self.env['training.history.line'].search(
                        [('course_id', '=', self.course_id.id), ('employee_id', '=', line.employee_id.id)]):
                    if training_history_line_rec2 and not (
                            training_history_line_rec2.training_conduct_id or training_history_line_rec2.training_conduct_id == self.id):
                        training_history_line_rec2.update({
                            'training_conduct_id': self.id,
                            'training_conduct_line_id': line.id,
                            'created_by_model': 'by_update_from_conduct',
                        })
                        training_history_line_rec2.update_state()
                history_2 = self.env['training.history.line'].search(
                    [('course_id', '=', self.course_id.id), ('employee_id', '=', line.employee_id.id),
                     ('training_conduct_id', '=', self.id)], limit=1)
                if not history_2:
                    training_history2 = self.env['training.history.line'].create({
                        'training_conduct_id': self.id,
                        'training_conduct_line_id': line.id,
                        'course_id': self.course_id.id,
                        'employee_id': line.employee_id.id,
                        'date_completed': self.end_date,
                        'created_by_model': 'by_conduct',
                    })
                    training_history2.update_state()

    def action_move_next_stage(self):
        next_sequence = self.sequence + 1
        stage_course = self.env['training.courses.stages'].search(
            [('course_id', '=', self.course_id.id), ('sequence', '=', next_sequence)], limit=1)
        self.write({'stage_id': stage_course.stage_id.id, 'stage_course_id': stage_course.id, 'is_approved': True,
                    'sequence': stage_course.sequence})
        training_histories = self.env['training.histories'].search(
            [('training_conduct_id', '=', self.id), ('state', '!=', 'expired')])
        if training_histories:
            for rec in training_histories:
                rec.update_state()
        training_history_line = self.env['training.history.line'].search(
            [('training_conduct_id', '=', self.id), ('state', '!=', 'expired')])
        if training_history_line:
            for rec_his in training_history_line:
                rec_his.update_state()
        for rec in self:
            rec.is_next_stage_executed = True
            if rec.stage_course_id.stage_id.name == 'Completed':
                rec.is_next_stage_hide = True
                rec.certificate_hide = True
            else:
                rec.is_next_stage_hide = False
        
        for line in self.conduct_line_ids:
            emp_tpl = self.env['employee.training.plan.line'].search([
                    ('employee_id', '=', line.employee_id.id),
                    ('course_ids', '=', self.course_id.id)
            ])

            if emp_tpl:
                for emp in emp_tpl.course_ids:
                    if emp.id == self.course_id.id:
                        emp_tpl.training_score = line.post_test

    def action_reject(self):
        rejected_stage_ref = self.env.ref('equip3_hr_training.course_stage_5').id
        stages = self.env['training.stages'].search([('id', '=', rejected_stage_ref)], limit=1)
        stage_course = self.env['training.courses.stages'].search(
            [('course_id', '=', self.course_id.id), ('stage_id', '=', stages.id)], limit=1)
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
            record.write({'state': 'rejected',
                          'is_next_stage_hide': True})
            self.write({'stage_id': stages.id, 'stage_course_id': stage_course.id, 'is_approved': True})
            self.reject_mail()
            self.rejected_wa_template()

    def action_certificate(self):
        for rec in self:
            for line in rec.conduct_line_ids:
                line.update_certificate()
            rec.certificate_hide = False

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise Warning("You can delete Training Conduct only state Draft.")
            return super(TrainingConduct, rec).unlink()

    # Emails
    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_training', 'sub_menu_all_training_conduct')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_training', 'action_training_kanban_conduct')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=training.conduct&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def get_trainer_name(self, employee_ids):
        return str([emp.name for emp in employee_ids]).replace('[', '').replace(']', '').replace("'", '')

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
                            'email_template_training_conduct_approval')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(self)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': user.email,
                        'url': url,
                        'approver_name': user.name,
                    })
                    if self.start_date:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(self.start_date).strftime('%d/%m/%Y')})
                    if self.end_date:
                        ctx.update(
                            {'date_to': fields.Datetime.from_string(self.end_date).strftime('%d/%m/%Y')})
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id, force_send=True)
                break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            try:
                template_id = ir_model_data.get_object_reference(
                    'equip3_hr_training',
                    'email_template_training_conduct_approved')[1]
            except ValueError:
                template_id = False
            ctx = self._context.copy()
            ctx.update({
                'email_from': self.env.user.email,
                'email_to': self.employee_id.user_id.email,
                'emp_name': self.employee_id.name,
            })
            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                      force_send=True)
            break

    def reject_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            try:
                template_id = ir_model_data.get_object_reference(
                    'equip3_hr_training',
                    'email_template_training_conduct_rejection')[1]
            except ValueError:
                template_id = False
            ctx = self._context.copy()
            ctx.update({
                'email_from': self.env.user.email,
                'email_to': self.employee_id.user_id.email,
                'emp_name': self.employee_id.name,
            })
            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                      force_send=True)
            break

    # def approved_mail(self):
    #     for rec in self:
    #         for liaaaaaane in rec.conduct_line_ids:
    #             line.approved_mail()
    #
    # def reject_mail(self):
    #     for rec in self:
    #         for line in rec.conduct_line_ids:
    #             line.reject_mail()

    def emp_add_select_btn(self):
        if self:
            for data in self:
                view = data.env.ref(
                    'equip3_hr_training.emp_add_wizard_form_view'
                )
                ori_arch = """
                    <form string="Select Employees" create="false" edit="false">
                        <notebook>
                            <page string="List">
                                <field name="training_id" invisible="1"/>
                                <field name="course_id" invisible="1"/>
                                <field name="training_histories_ids" options="{'no_create_edit':True,'no_open': True}">
                                    <tree create="false" editable='bottom'>
                                        <field name="course_ids" widget="many2many_tags" readonly="1"/>
                                        <field name="employee_id" readonly="1" options="{'no_create_edit':True,'no_open': True}"/>
                                        <field name="job_id" readonly="1" options="{'no_create_edit':True,'no_open': True}"/>
                                        <field name="start_date" readonly="1"/>
                                        <field name="end_date" readonly="1"/>
                                        <field name="expiry_date" readonly="1"/>
                                        <field name="training_required" readonly="1"/>
                                        <field name="state" readonly="1"/>
                                    </tree>
                                 </field>
                            </page>
                        </notebook>
                        <footer>
                            <button name="emp_add_select_btn" string="Select List" type="object" class="oe_highlight"/>
                            <button name="reset_list" string="Reset List" type="object" class="oe_highlight"/>
                            <button string="Cancel" class="oe_link" special="cancel"/>
                        </footer>
                    </form>
                """
                histories_model_id = self.env[
                    'ir.model'
                ].sudo().search([
                    ('model', '=', 'employee.add.wizard')
                ], limit=1)
                if histories_model_id:
                    str_obj = ori_arch
                    first_str = """<?xml version="1.0"?>
                        <form string="Select Employees">
                    """
                    no_create_str = """ options="{'no_create': True }" """
                    middle_str = ''

                    #button start here
                    last_str = str_obj.split(">",1)[1]
                    final_arch = first_str + middle_str + last_str

                    if view:
                        view.sudo().write({'arch': final_arch})

                return {
                    'name': 'Select Employee',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'employee.add.wizard',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'context': {'default_training_id': self.id},
                }

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_training = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.number_of_repetitions_training'))
        training_conduct_approve = self.search([('state', '=', 'to_approve')])
        for rec in training_conduct_approve:
            if rec.training_approver_user_ids:
                matrix_line = sorted(rec.training_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.training_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_training',
                            'email_template_training_conduct_approval')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(rec)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': user.email,
                        'url': url,
                        'approver_name': user.name,
                    })
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_training - 1
                        query_statement = """UPDATE training_conduct_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE training_conduct_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)

class TrainingConductLine(models.Model):
    _name = 'training.conduct.line'
    _description = 'Training Conduct Line'

    conduct_id = fields.Many2one('training.conduct', string='Training Conduct')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    employee_domain_ids = fields.Many2many('hr.employee')
    attended = fields.Boolean(string='Attended', default=True)
    remarks = fields.Char(string='Remarks')
    attachment = fields.Binary(string='Attachment')
    certificate_attachment = fields.Binary(string='Certificate Attachment')
    certificate_attachment_fname = fields.Char('Certificate Name')
    pre_test = fields.Float()
    post_test = fields.Float()
    final_score = fields.Float(string="Final Score")
    # status = fields.Char()
    status = fields.Selection([('Failed', 'Failed'), ('Success', 'Success')], string='Status')
    # for calendar view(Dashboard)
    name = fields.Char('Name', related='conduct_id.name')
    start_date = fields.Date('Date Start', related='conduct_id.start_date')
    end_date = fields.Date('Date Completed', related='conduct_id.end_date')
    course_id = fields.Many2one('training.courses', string='Training Courses', related='conduct_id.course_id')
    edit_score = fields.Boolean('Edit Score Based on Approves', related='conduct_id.edit_score')
    is_next_stage_executed = fields.Boolean(related='conduct_id.is_next_stage_executed')

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(TrainingConductLine, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.context.get('is_calendar'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res
 
    @api.onchange('post_test', 'attended')
    def onchange_post_test(self):
        for rec in self:
            if rec.conduct_id.state != 'draft':
                if rec.attended:
                    if rec.post_test != 0:
                        if rec.conduct_id.minimal_score <= rec.post_test:
                            rec.update({'status': 'Success'})
                        else:
                            rec.update({'status': 'Failed'})
                    else:
                        rec.update({'status': ''})
                else:
                    rec.update({'status': 'Failed'})
            else:
                rec.update({'status': ''})

    def get_certificate_template(self):
        for rec in self:
            parent_record = rec.conduct_id
            if parent_record.certificate and parent_record.certificate_template:
                temp = parent_record.certificate_template.certificate_content
                certificate_content_replace = parent_record.certificate_template.certificate_content
                if "$(name)" in certificate_content_replace:
                    if not parent_record.name:
                        raise ValidationError("Certificate Name is empty")
                    certificate_content_replace = str(certificate_content_replace).replace("$(name)",
                                                                                           parent_record.name)
                if "$(employee_id)" in certificate_content_replace:
                    if not rec.employee_id.name:
                        raise ValidationError("Employee Name is empty")
                    certificate_content_replace = str(certificate_content_replace).replace("$(employee_id)",
                                                                                           rec.employee_id.name)
                if "$(course_id)" in certificate_content_replace:
                    if not parent_record.course_id.name:
                        raise ValidationError("Course is empty")
                    certificate_content_replace = str(certificate_content_replace).replace("$(course_id)",
                                                                                           parent_record.course_id.name)
                if "$(post_test)" in certificate_content_replace:
                    if not rec.post_test:
                        raise ValidationError("Post Test is empty")
                    certificate_content_replace = str(certificate_content_replace).replace("$(post_test)",
                                                                                           str(rec.post_test))
                if "$(start_date)" in certificate_content_replace:
                    if not parent_record.start_date:
                        raise ValidationError("Start Date is empty")
                    s_date = parent_record.start_date
                    s_date_format = s_date.strftime('%m/%d/%Y')
                    certificate_content_replace = str(certificate_content_replace).replace("$(start_date)",
                                                                                           str(s_date_format))
                if "$(end_date)" in certificate_content_replace:
                    if not parent_record.end_date:
                        raise ValidationError("End Date is empty")
                    e_date = parent_record.end_date
                    e_date_format = e_date.strftime('%m/%d/%Y')
                    certificate_content_replace = str(certificate_content_replace).replace("$(end_date)",
                                                                                           str(e_date_format))
                if "$(employee_ids)" in certificate_content_replace:
                    if parent_record.employee_ids and parent_record.trainer_type == 'internal':
                        # for trainers in parent_record.employee_ids:
                        #     trainers_name = str(trainers.name)
                        trainers_name = str([emp.name for emp in parent_record.employee_ids]).replace('[', '').replace(
                            ']', '').replace(
                            "'", '')
                        certificate_content_replace = str(certificate_content_replace).replace("$(employee_ids)",
                                                                                               trainers_name)
                    if parent_record.external_trainer and parent_record.trainer_type == 'external':
                        certificate_content_replace = str(certificate_content_replace).replace("$(employee_ids)",
                                                                                               parent_record.external_trainer)
                parent_record.certificate_template.certificate_content = certificate_content_replace
                data = parent_record.certificate_template.certificate_content
                parent_record.certificate_template.certificate_content = temp
                return data

    def update_certificate(self):
        for rec in self:
            if rec.conduct_id.certificate and rec.conduct_id.certificate_template and rec.status == 'Success':
                pdf = self.env.ref('equip3_hr_training.equip3_hr_certificate_template')._render_qweb_pdf([rec.id])
                attachment = base64.b64encode(pdf[0])
                rec.certificate_attachment = attachment
                rec.certificate_attachment_fname = f"{rec.employee_id.name}_{rec.conduct_id.course_id.name}"
                rec.certificate_mail(attachment)
            else:
                rec.certificate_attachment = False
                rec.certificate_attachment_fname = ""

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'hr', 'menu_hr_employee_user')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'hr', 'open_view_employee_list_my')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            self.employee_id.id) + "&view_type=form&model=hr.employee&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def certificate_mail(self,base64file):
        ir_model_data = self.env['ir.model.data']
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.send_by_wa_training')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        ir_values = {
            'name': self.certificate_attachment_fname + '.pdf',
            'type': 'binary',
            'datas': self.certificate_attachment,
            'store_fname': self.certificate_attachment_fname,
            'mimetype': 'application/x-pdf',
        }
        data_id = self.env['ir.attachment'].create(ir_values)
        if send_by_wa:
            wa_template = self.env.ref('equip3_hr_training.training_conduct_completed_wa_template')
            if wa_template:
                string_test = str(wa_template.message)
                if "${employee_name}" in string_test:
                    string_test = string_test.replace("${employee_name}", self.employee_id.name)
                if "${course_name}" in string_test:
                    string_test = string_test.replace("${course_name}", self.course_id.name)
                if "${start_date}" in string_test:
                    string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                        self.start_date).strftime('%d/%m/%Y'))
                if "${end_date}" in string_test:
                    string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                        self.end_date).strftime('%d/%m/%Y'))
                if "${br}" in string_test:
                    string_test = string_test.replace("${br}", f"\n")
                phone_num = str(self.employee_id.mobile_phone)
                if "+" in phone_num:
                    phone_num = int(phone_num.replace("+", ""))
                strfile = base64file
                param = {'body': string_test, 'phone': phone_num}
                param_file = {'body': "data:application/pdf;base64," + strfile.decode('ascii') , 'phone': phone_num,'filename':self.certificate_attachment_fname + '.pdf'}
                domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                
                
                try:
                    request_server = requests.post(f'{domain}/sendMessage?token={token}',
                                                   params=param,
                                                   headers=headers, verify=True)
                    send_file = requests.post(f'{domain}/sendFile?token={token}',
                                                   json=param_file,
                                                   headers=headers, verify=True)
                except ConnectionError:
                    raise ValidationError(
                        "Not connect to API Chat Server. Limit reached or not active")
        for rec in self:
            try:
                template_id = ir_model_data.get_object_reference(
                    'equip3_hr_training',
                    'email_template_completed_training')[1]
            except ValueError:
                template_id = False
            ctx = self._context.copy()
            url = self.get_url(self)
            ctx.update({
                'url': url,
            })
            if self.conduct_id.start_date:
                ctx.update(
                    {'date_from': fields.Datetime.from_string(self.conduct_id.start_date).strftime('%d/%m/%Y')})
            if self.conduct_id.end_date:
                ctx.update(
                    {'date_to': fields.Datetime.from_string(self.conduct_id.end_date).strftime('%d/%m/%Y')})

            template = self.env['mail.template'].browse(template_id)
            template.attachment_ids = [(6, 0, [data_id.id])]
            template.with_context(ctx).send_mail(rec.id, force_send=True)
            template.attachment_ids = [(3, data_id.id)]
            break

    @api.onchange('pre_test', 'post_test')
    def _onchange_final_score(self):
        for rec in self:
            if not rec.conduct_id.course_id:
                raise ValidationError("Please fill the Training Courses data before adding the Training Conduct Line")
            rec.final_score = 0.0
            formula = rec.conduct_id.course_id.final_score_formula
            localdict = {"pre_test": rec.pre_test, "post_test": rec.post_test, "total": 0.0}
            safe_eval(formula, localdict, mode='exec', nocopy=True)
            rec.final_score = localdict["total"]



class TrainingConductApproverUser(models.Model):
    _name = 'training.conduct.approver.user'

    emp_training_id = fields.Many2one('training.conduct', string="Employee Training Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'emp_training_conduct_user_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    # Auto follow
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    #parent status
    state = fields.Selection(string='Parent Status', related='emp_training_id.state')

    @api.depends('emp_training_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.emp_training_id.training_approver_user_ids:
            sl = sl + 1
            line.name = sl
