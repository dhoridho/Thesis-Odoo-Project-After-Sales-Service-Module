from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
from odoo.exceptions import UserError, Warning
from lxml import etree
import requests

headers = {'content-type': 'application/json'}


class HrTrainingConductCancellation(models.Model):
    _name = 'hr.training.conduct.cancellation'
    _description = 'Training Conduct Cancellation for Employee'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    @api.model
    def _multi_company_training_conduct_domain(self):
        return [('company_id','=', self.env.company.id),('stage_course_id.stage_id.name','=','Approved')]
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('hr.training.conduct.cancellation') or 'New'
        return super(HrTrainingConductCancellation, self).create(vals)

    name = fields.Char(string='Name')
    training_conduct_id = fields.Many2one('training.conduct', string='Training Conduct', required=True,
                                          domain=_multi_company_training_conduct_domain)
    course_id = fields.Many2one('training.courses', string='Training Courses', related='training_conduct_id.course_id')
    trainer_type = fields.Selection(string='Trainer type',
                                    related='training_conduct_id.trainer_type')
    employee_ids = fields.Many2many('hr.employee', 'training_conduct_cancel_employee_rel', string='Trainer',
                                    related='training_conduct_id.employee_ids')
    external_trainer = fields.Char(string='Trainer', related='training_conduct_id.external_trainer')
    estimated_cost = fields.Float(string='Estimated Cost', related='training_conduct_id.estimated_cost')
    start_date = fields.Date('Date Start', related='training_conduct_id.start_date')
    end_date = fields.Date('Date Completed', related='training_conduct_id.end_date')
    minimal_score = fields.Float('Minimal Score', related='training_conduct_id.minimal_score')
    created_by = fields.Many2one('res.users', string='Created By', related='training_conduct_id.created_by')
    created_date = fields.Date(string='Created Date', related='training_conduct_id.created_date')
    conduct_cancell_line_ids = fields.One2many('hr.training.conduct.cancellation.line', 'conduct_cancell_id',
                                               string='Training Conduct Line')
    state = fields.Selection(
        [('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        string='State', tracking=True, default='draft')

    employee_id = fields.Many2one('hr.employee', 'Employee')
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    training_conduct_cancel_approver_user_ids = fields.One2many('training.conduct.cancel.approver.user', 'emp_training_conduct_cancel_id',
                                                        string='Approver')
    approvers_ids = fields.Many2many('res.users', 'emp_training_conduct_cancel_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    is_training_approval_matrix = fields.Boolean("Is Training Approval Matrix", compute='_compute_is_training_approval_matrix')
    state1 = fields.Selection(
        [('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Submitted'), ('rejected', 'Rejected')],
        string='State', default='draft', tracking=False, copy=False, store=True, compute='_compute_state1')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrTrainingConductCancellation, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrTrainingConductCancellation, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_is_training_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.training_approval_matrix')
            rec.is_training_approval_matrix = setting
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrTrainingConductCancellation, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_training_manager') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_training_director'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        elif  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_training_director'):
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

    @api.onchange('training_conduct_id')
    def onchange_training_conduct(self):
        data_conduct = []
        for rec in self:
            employee = rec.env['hr.employee'].search([('user_id', '=', rec.training_conduct_id.created_by.id)],limit=1)
            rec.employee_id = employee.id
            rec.onchange_approver_user()
            if rec.conduct_cancell_line_ids:
                remove = []
                for line in rec.conduct_cancell_line_ids:
                    remove.append((2, line.id))
                rec.conduct_cancell_line_ids = remove
            for line in rec.training_conduct_id.conduct_line_ids:
                data_conduct.append((0, 0, {'employee_id': line.employee_id,
                                            'attended': line.attended,
                                            'remarks': line.remarks,
                                            'attachment': line.attachment,
                                            'post_test': line.post_test,
                                            'status': line.status,
                                            }))
            rec.conduct_cancell_line_ids = data_conduct

    def onchange_approver_user(self):
        for training_conduct_cancel in self:
            training_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.training_approval_matrix')
            if training_setting:
                if training_conduct_cancel.training_conduct_cancel_approver_user_ids:
                    remove = []
                    for line in training_conduct_cancel.training_conduct_cancel_approver_user_ids:
                        remove.append((2, line.id))
                    training_conduct_cancel.training_conduct_cancel_approver_user_ids = remove
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_training.training_type_approval')
                if setting == 'employee_hierarchy':
                    training_conduct_cancel.training_conduct_cancel_approver_user_ids = self.training_conduct_cancel_emp_by_hierarchy(
                        training_conduct_cancel)
                    self.app_list_training_conduct_cancel_emp_by_hierarchy()
                if setting == 'approval_matrix':
                    self.training_conduct_cancel_approval_by_matrix(training_conduct_cancel)

    def training_conduct_cancel_emp_by_hierarchy(self, training_conduct_cancel):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(training_conduct_cancel, training_conduct_cancel.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, training_conduct_cancel, employee_manager, data, approval_ids, seq):
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
                self.get_manager(training_conduct_cancel, employee_manager['parent_id'], data, approval_ids, seq)
                break
        return approval_ids

    def get_manager_hierarchy(self, training_conduct_cancel, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(training_conduct_cancel, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def app_list_training_conduct_cancel_emp_by_hierarchy(self):
        for training_conduct_cancel in self:
            app_list = []
            for line in training_conduct_cancel.training_conduct_cancel_approver_user_ids:
                app_list.append(line.user_ids.id)
            training_conduct_cancel.approvers_ids = app_list

    def training_conduct_cancel_approval_by_matrix(self, training_conduct_cancel):
        app_list = []
        approval_matrix = self.env['hr.training.approval.matrix'].search(
            [('apply_to', '=', 'by_employee'), ('applicable_to', '=', 'training_conduct')])
        matrix = approval_matrix.filtered(lambda line: training_conduct_cancel.employee_id.id in line.employee_ids.ids)
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
                    approvers = self.get_manager_hierarchy(training_conduct_cancel, training_conduct_cancel.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            training_conduct_cancel.approvers_ids = app_list
            training_conduct_cancel.training_conduct_cancel_approver_user_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.training.approval.matrix'].search(
                [('apply_to', '=', 'by_job_position'), ('applicable_to', '=', 'training_conduct')])
            matrix = approval_matrix.filtered(lambda line: training_conduct_cancel.job_id.id in line.job_ids.ids)
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
                        approvers = self.get_manager_hierarchy(training_conduct_cancel,
                                                               training_conduct_cancel.employee_id, data, manager_ids,
                                                               seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                training_conduct_cancel.approvers_ids = app_list
                training_conduct_cancel.training_conduct_cancel_approver_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.training.approval.matrix'].search(
                    [('apply_to', '=', 'by_department'), ('applicable_to', '=', 'training_conduct')])
                matrix = approval_matrix.filtered(
                    lambda line: training_conduct_cancel.department_id.id in line.department_ids.ids)
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
                            approvers = self.get_manager_hierarchy(training_conduct_cancel,
                                                                   training_conduct_cancel.employee_id, data,
                                                                   manager_ids,
                                                                   seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    training_conduct_cancel.approvers_ids = app_list
                    training_conduct_cancel.training_conduct_cancel_approver_user_ids = data_approvers

    @api.depends('state', 'employee_id')
    def _compute_can_approve(self):
        for training_conduct_cancel in self:
            if training_conduct_cancel.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_training.training_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_training.training_level')
                app_level = int(setting_level)
                current_user = training_conduct_cancel.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(
                        training_conduct_cancel.training_conduct_cancel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(training_conduct_cancel.training_conduct_cancel_approver_user_ids)
                    if app < app_level and app < a:
                        if current_user in training_conduct_cancel.training_conduct_cancel_approver_user_ids[app].user_ids:
                            training_conduct_cancel.is_approver = True
                        else:
                            training_conduct_cancel.is_approver = False
                    else:
                        training_conduct_cancel.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(
                        training_conduct_cancel.training_conduct_cancel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(training_conduct_cancel.training_conduct_cancel_approver_user_ids)
                    if app < a:
                        for line in training_conduct_cancel.training_conduct_cancel_approver_user_ids[app]:
                            if current_user in line.user_ids:
                                training_conduct_cancel.is_approver = True
                            else:
                                training_conduct_cancel.is_approver = False
                    else:
                        training_conduct_cancel.is_approver = False

                else:
                    training_conduct_cancel.is_approver = False
            else:
                training_conduct_cancel.is_approver = False

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.send_by_wa_training')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if send_by_wa:
            template = self.env.ref('equip3_hr_training.training_conduct_cancel_approver_wa_template')
            if template:
                url = self.get_url(self)
                if self.training_conduct_cancel_approver_user_ids:
                    matrix_line = sorted(self.training_conduct_cancel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.training_conduct_cancel_approver_user_ids[len(matrix_line)]
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
                        param = {'body': string_test, 'phone': phone_num}
                        domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                        token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                        try:
                            request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                                                           headers=headers, verify=True)
                        except ConnectionError:
                            raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.send_by_wa_training')
        if send_by_wa:
            template = self.env.ref('equip3_hr_training.training_conduct_cancel_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if template:
                if self.training_conduct_cancel_approver_user_ids:
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
                    param = {'body': string_test, 'phone': phone_num}
                    domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                    token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                    try:
                        request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                                                       headers=headers, verify=True)
                    except ConnectionError:
                        raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def rejected_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.send_by_wa_training')
        if send_by_wa:
            template = self.env.ref('equip3_hr_training.training_conduct_cancel_rejected_wa_template')
            url = self.get_url(self)
            if template:
                if self.training_conduct_cancel_approver_user_ids:
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
                    # if "+" in phone_num:
                    #     phone_num = int(phone_num.replace("+", ""))
                    param = {'body': string_test, 'phone': phone_num}
                    domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                    token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                    try:
                        request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                                                       headers=headers, verify=True)
                    except ConnectionError:
                        raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def action_confirm(self):
        setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.training_approval_matrix')
        if setting:
            for rec in self:
                rec.write({'state': 'to_approve'})
                for line in rec.training_conduct_cancel_approver_user_ids:
                    line.write({'approver_state': 'draft'})
            self.approver_mail()
            self.approver_wa_template()
        else:
            self.action_conduct_del_approve()

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'training.conduct.cancel.request.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':True},
            'name': "Confirmation Message",
            'target': 'new',
        }
        
    def wizard_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'training.conduct.cancel.request.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':False,
                       'default_is_reject':True},
            'name': "Confirmation Message",
            'target': 'new',
        }

    def action_approve(self):
        sequence_matrix = [data.name for data in self.training_conduct_cancel_approver_user_ids]
        sequence_approval = [data.name for data in self.training_conduct_cancel_approver_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.training_conduct_cancel_approver_user_ids.filtered(
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
                        for user in record.training_conduct_cancel_approver_user_ids:
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
                            record.training_conduct_cancel_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            # record.write({'state': 'approved'})
                            record.action_conduct_del_approve()
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
                        for line in record.training_conduct_cancel_approver_user_ids:
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
                            record.training_conduct_cancel_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            # record.write({'state': 'approved'})
                            record.action_conduct_del_approve()
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

    def action_reject(self):
        for record in self:
            for user in record.training_conduct_cancel_approver_user_ids:
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

    def action_conduct_del_approve(self):
        for rec in self:
            if rec.training_conduct_id:
                training_con = rec.training_conduct_id
                training_con.update({'state': 'cancelled',
                                     'is_next_stage_hide': True})
                cancelled_stage_ref = self.env.ref('equip3_hr_training.course_stage_6').id
                stages = self.env['training.stages'].search([('id', '=', cancelled_stage_ref)], limit=1)
                stage_course = self.env['training.courses.stages'].search(
                    [('course_id', '=', self.course_id.id), ('stage_id', '=', stages.id)], limit=1)
                training_con.write({'stage_id': stages.id, 'stage_course_id': stage_course.id, 'is_approved': True})
                training_histories = self.env['training.histories'].search(
                    [('training_conduct_id', '=', rec.training_conduct_id.id)])
                if training_histories:
                    for histories in training_histories:
                        histories.unlink()
                training_history = self.env['training.history.line'].search(
                    [('training_conduct_id', '=', rec.training_conduct_id.id)])
                if training_history:
                    for history in training_history:
                        history.unlink()
                rec.write({'state': 'approved'})

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise Warning("You can delete My Training Cancellation only state Draft.")
            return super(HrTrainingConductCancellation, rec).unlink()

    # Emails
    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_training', 'sub_menu_training_conduct_cancellation')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_training', 'action_training_conduct_cancellation')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.training.conduct.cancellation&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def get_trainer_name(self, employee_ids):
        return str([emp.name for emp in employee_ids]).replace('[', '').replace(']', '').replace("'", '')

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.training_conduct_cancel_approver_user_ids:
                matrix_line = sorted(rec.training_conduct_cancel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.training_conduct_cancel_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_training',
                            'email_template_training_conduct_cancellation_approval')[1]
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
                    'email_template_training_conduct_cancellation_approved')[1]
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
                    'email_template_training_conduct_cancellation_rejection')[1]
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

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_training = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_training.number_of_repetitions_training'))
        training_conduct_cancel_approve = self.search([('state', '=', 'to_approve')])
        for rec in training_conduct_cancel_approve:
            if rec.training_conduct_cancel_approver_user_ids:
                matrix_line = sorted(rec.training_conduct_cancel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.training_conduct_cancel_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_training',
                            'email_template_training_conduct_cancellation_approval')[1]
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
                        query_statement = """UPDATE training_conduct_cancel_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE training_conduct_cancel_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)

class TrainingConductLine(models.Model):
    _name = 'hr.training.conduct.cancellation.line'
    _description = 'Training Conduct Cancellation Line'

    conduct_cancell_id = fields.Many2one('hr.training.conduct.cancellation', string='Training Conduct')
    employee_id = fields.Many2one('hr.employee', string='Employee', )
    attended = fields.Boolean(string='Attended')
    remarks = fields.Char(string='Remarks')
    attachment = fields.Binary(string='Attachment')
    pre_test = fields.Float()
    post_test = fields.Float()
    status = fields.Char()


class TrainingConductCancelApproverUser(models.Model):
    _name = 'training.conduct.cancel.approver.user'

    emp_training_conduct_cancel_id = fields.Many2one('hr.training.conduct.cancellation', string="Employee Training Cancel Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'emp_training_conduct_cancel_user_ids', string="Approved user")
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
    state = fields.Selection(string='Parent Status', related='emp_training_conduct_cancel_id.state')

    @api.depends('emp_training_conduct_cancel_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.emp_training_conduct_cancel_id.training_conduct_cancel_approver_user_ids:
            sl = sl + 1
            line.name = sl