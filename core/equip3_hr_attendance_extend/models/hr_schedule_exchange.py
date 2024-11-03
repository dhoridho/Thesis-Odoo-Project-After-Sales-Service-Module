# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta
from pytz import timezone
import requests
headers = {'content-type': 'application/json'}

class WorkingScheduleExchange(models.Model):
    _name = 'schedule.exchange'
    _description = 'Hr Working Schedule Exchange'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def default_get(self, fields):
        res = super(WorkingScheduleExchange, self).default_get(fields)
        employees = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        res['employee_id'] = employees.id
        return res

    @api.model
    def create(self, vals):
        sequence_no = self.env['ir.sequence'].next_by_code('schedule.exchange')
        vals.update({'name': sequence_no})
        return super(WorkingScheduleExchange, self).create(vals)

    @api.onchange('exchange_type')
    def onchange_other_employee(self):
        res = {}
        employee_working_calendar = self.env['employee.working.schedule.calendar'].search([])
        if self.exchange_type == 'other':
            employee_list = []
            for vals in employee_working_calendar:
                employee_list.append(vals.employee_id.id)
            res['domain'] = {'other_employee_id': [('id', 'in', employee_list)]}
        else:
            res['domain'] = {'employee_ids': []}
        return res

    @api.onchange('exchange_type', 'date_from', 'date_to')
    def onchange_schedule_calendar(self):
        res = {}
        employee_working_calendar = self.env['employee.working.schedule.calendar'].search(
            [('date_start', '>=', self.date_from), ('date_start', '<=', self.date_to)])
        employee_list = []
        for vals in employee_working_calendar:
            if self.employee_id == vals.employee_id:
                employee_list.append(vals.id)
        res['domain'] = {'schedule_calendar_ids': [('id', 'in', employee_list)]}
        return res

    @api.onchange('exchange_type', 'date_from', 'date_to', 'other_employee_id')
    def onchange_exchange_schedule(self):
        res = {}
        employee_working_calendar = self.env['employee.working.schedule.calendar'].search(
            [('date_start', '>=', self.date_from), ('date_start', '<=', self.date_to)])
        employee_list = []
        if self.exchange_type == 'own_schedule':
            for vals in employee_working_calendar:
                if self.employee_id == vals.employee_id:
                    employee_list.append(vals.id)
            res['domain'] = {'exchange_schedule_ids': [('id', 'in', employee_list)]}
        else:
            for vals in employee_working_calendar:
                if self.other_employee_id == vals.employee_id:
                    employee_list.append(vals.id)
            res['domain'] = {'exchange_schedule_ids': [('id', 'in', employee_list)]}
        return res

    name = fields.Char(string="Name", readonly=True, required=True, copy=False, default='New')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id',
                                    store=True)
    date_from = fields.Date('Start Date', required=True, tracking=True)
    date_to = fields.Date('End Date', required=True, tracking=True)
    state = fields.Selection([("draft", "Draft"),
                              ("to_approve", "To Approve"),
                              ("approved", "Approved"),
                              ("refused", "Rejected")
                              ], string='Status', default="draft", tracking=True)
    exchange_type = fields.Selection([("own_schedule", "With Own Schedule"),
                                      ("other", "With Other Employee"), ], string='Exchange Type',
                                     default="own_schedule",
                                     tracking=True, required=True)
    other_employee_id = fields.Many2one('hr.employee', string='Other Employee')
    schedule_calendar_ids = fields.Many2many('employee.working.schedule.calendar', 'current_working_schedule_rel',
                                             string='Current Schedule')
    exchange_schedule_ids = fields.Many2many('employee.working.schedule.calendar', 'exchange_working_schedule_rel',
                                             string='Exchange Schedule')
    working_schedule_user_ids = fields.One2many('working.schedule.approver.user', 'working_schedule_app_id',
                                                string='Approver')
    approvers_ids = fields.Many2many('res.users', 'working_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id')
    feedback_parent = fields.Text(string='Parent Feedback')
    is_schedule_exchange_approval_matrix = fields.Boolean("Is Schedule Exchange Approval Matrix",
                                                          compute='_compute_is_schedule_exchange_approval_matrix')
    state1 = fields.Selection([("draft", "Draft"), ("to_approve", "To Approve"), ("approved", "Submitted"),
                               ("refused", "Rejected")], string='Status', default='draft', tracking=False, copy=False,
                              store=True, compute='_compute_state1')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(WorkingScheduleExchange, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(WorkingScheduleExchange, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_is_schedule_exchange_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.attendance_approval_matrix')
            rec.is_schedule_exchange_approval_matrix = setting

    def custom_menu(self):
        views = [(self.env.ref('equip3_hr_attendance_extend.view_hr_working_schedule_exchange_tree').id, 'tree'),
                 (self.env.ref('equip3_hr_attendance_extend.view_hr_working_schedule_exchange_form').id, 'form')]
        if self.env.user.has_group('hr_attendance.group_hr_attendance') and not self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_attendance_hr_manager'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Working Schedule Exchange',
                'res_model': 'schedule.exchange',
                'view_mode': 'tree,form',
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                'views': views
                # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                # 'search_view_id':search_view_id.id,

            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Working Schedule Exchange',
                'res_model': 'schedule.exchange',
                'view_mode': 'tree,form',
                'views': views
                # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                # 'search_view_id':search_view_id.id,

            }

    @api.onchange('employee_id', 'date_from')
    def onchange_approver_user(self):
        for working in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.attendance_approval_matrix')
            if setting:
                if working.working_schedule_user_ids:
                    remove = []
                    for line in working.working_schedule_user_ids:
                        remove.append((2, line.id))
                    working.working_schedule_user_ids = remove
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_attendance_extend.attendance_type_approval')
                if setting == 'employee_hierarchy':
                    working.working_schedule_user_ids = self.working_emp_by_hierarchy(working)
                    self.app_list_working_emp_by_hierarchy()
                if setting == 'approval_matrix':
                    self.working_approval_by_matrix(working)

    def working_emp_by_hierarchy(self, working):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(working, working.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, working, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.attendance_level')
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
                self.get_manager(working, employee_manager['parent_id'], data, approval_ids, seq)
                break

        return approval_ids

    def get_manager_hierarchy(self, working, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(working, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def app_list_working_emp_by_hierarchy(self):
        for working in self:
            app_list = []
            for line in working.working_schedule_user_ids:
                app_list.append(line.user_ids.id)
            working.approvers_ids = app_list

    def working_approval_by_matrix(self, working):
        app_list = []
        approval_matrix = self.env['hr.attendance.approval.matrix'].search(
            [('apply_to', '=', 'by_employee')])
        matrix = approval_matrix.filtered(lambda line: working.employee_id.id in line.employee_ids.ids)
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
                    approvers = self.get_manager_hierarchy(working, working.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            working.approvers_ids = app_list
            working.working_schedule_user_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.attendance.approval.matrix'].search(
                [('apply_to', '=', 'by_job_position')])
            matrix = approval_matrix.filtered(lambda line: working.job_id.id in line.job_ids.ids)
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
                        approvers = self.get_manager_hierarchy(working, working.employee_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                working.approvers_ids = app_list
                working.working_schedule_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.attendance.approval.matrix'].search(
                    [('apply_to', '=', 'by_department')])
                matrix = approval_matrix.filtered(lambda line: working.department_id.id in line.department_ids.ids)
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
                            approvers = self.get_manager_hierarchy(working, working.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    working.approvers_ids = app_list
                    working.working_schedule_user_ids = data_approvers

    @api.depends('state', 'employee_id', 'date_from')
    def _compute_can_approve(self):
        for working in self:
            if working.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_attendance_extend.attendance_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_attendance_extend.attendance_level')
                app_level = int(setting_level)
                current_user = working.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(working.working_schedule_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(working.working_schedule_user_ids)
                    if app < app_level and app < a:
                        if current_user in working.working_schedule_user_ids[app].user_ids:
                            working.is_approver = True
                        else:
                            working.is_approver = False
                    else:
                        working.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(working.working_schedule_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(working.working_schedule_user_ids)
                    if app < a:
                        for line in working.working_schedule_user_ids[app]:
                            if current_user in line.user_ids:
                                working.is_approver = True
                            else:
                                working.is_approver = False
                    else:
                        working.is_approver = False

                else:
                    working.is_approver = False
            else:
                working.is_approver = False

    @api.constrains('exchange_schedule_ids', 'schedule_calendar_ids')
    def _check_schedule_line(self):
        for exchange in self:
            current = len(exchange.schedule_calendar_ids)
            schedule = len(exchange.exchange_schedule_ids)
            if current != schedule or current == 0:
                raise ValidationError(_("The Exchange Schedule in table not meet between each sequence"))

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_attendance_extend', 'working_schedule_exchange_manager_menu')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_attendance_extend', 'working_schedule_exchange_action_manager')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.holidays&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.working_schedule_user_ids:
                matrix_line = sorted(rec.working_schedule_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.working_schedule_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_attendance_extend',
                            'email_template_working_schedule_exchange_approval')[1]
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
                    if self.date_from:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(self.date_from).strftime('%d/%m/%Y')})
                    if self.date_to:
                        ctx.update(
                            {'date_to': fields.Datetime.from_string(self.date_to).strftime('%d/%m/%Y')})
                    var = self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                              force_send=True)
                break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.working_schedule_user_ids:
                for rec in rec.working_schedule_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.user_ids:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_attendance_extend',
                                'email_template_working_schedule_exchange_approved')[1]
                        except ValueError:
                            template_id = False
                        ctx = self._context.copy()
                        url = self.get_url(self)
                        ctx.update({
                            'email_from': self.env.user.email,
                            'email_to': self.employee_id.user_id.email,
                            'url': url,
                            'approver_name': user.name,
                            'emp_name': self.employee_id.name,
                        })
                        if self.date_from:
                            ctx.update(
                                {'date_from': fields.Datetime.from_string(self.date_from).strftime('%d/%m/%Y')})
                        if self.date_to:
                            ctx.update(
                                {'date_to': fields.Datetime.from_string(self.date_to).strftime('%d/%m/%Y')})
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                    break

    def reject_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.working_schedule_user_ids:
                for rec in rec.working_schedule_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.user_ids:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_attendance_extend',
                                'email_template_working_schedule_exchange_reject')[1]
                        except ValueError:
                            template_id = False
                        ctx = self._context.copy()
                        ctx.pop('default_state')
                        url = self.get_url(self)
                        ctx.update({
                            'email_from': self.env.user.email,
                            'email_to': self.employee_id.user_id.email,
                            'url': url,
                            'approver_name': user.name,
                            'emp_name': self.employee_id.name,
                        })
                        if self.date_from:
                            ctx.update(
                                {'date_from': fields.Datetime.from_string(self.date_from).strftime('%d/%m/%Y')})
                        if self.date_to:
                            ctx.update(
                                {'date_to': fields.Datetime.from_string(self.date_to).strftime('%d/%m/%Y')})
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                    break

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(self)
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_extend.schedule_approver_wa_template')
            if template:
                if self.working_schedule_user_ids:
                    matrix_line = sorted(self.working_schedule_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.working_schedule_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", self.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.name)
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${start_date}" in string_test:
                            string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                                self.date_from).strftime('%d/%m/%Y'))
                        if "${end_date}" in string_test:
                            string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                                self.date_to).strftime('%d/%m/%Y'))
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
                            request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
                        except ConnectionError:
                            raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_extend.schedule_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if template:
                if self.working_schedule_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.date_from).strftime('%d/%m/%Y'))
                    if "${end_date}" in string_test:
                        string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                            self.date_to).strftime('%d/%m/%Y'))
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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_extend.schedule_rejected_wa_template')
            url = self.get_url(self)
            if template:
                if self.working_schedule_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.date_from).strftime('%d/%m/%Y'))
                    if "${end_date}" in string_test:
                        string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                            self.date_to).strftime('%d/%m/%Y'))
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)
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

    def get_auto_follow_up_approver_wa_template(self, rec):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.send_by_wa_attendance')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(rec)
        if send_by_wa:
            template = self.env.ref('equip3_hr_attendance_extend.schedule_approver_wa_template')
            if template:
                if rec.working_schedule_user_ids:
                    matrix_line = sorted(rec.working_schedule_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = rec.working_schedule_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", rec.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", rec.name)
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${start_date}" in string_test:
                            string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                                rec.date_from).strftime('%d/%m/%Y'))
                        if "${end_date}" in string_test:
                            string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                                rec.date_to).strftime('%d/%m/%Y'))
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
                            request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
                        except ConnectionError:
                            raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_working = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.number_of_repetitions_attendance'))
        working_confirmed = self.search([('state', '=', 'to_approve')])
        for rec in working_confirmed:
            if rec.working_schedule_user_ids:
                matrix_line = sorted(rec.working_schedule_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.working_schedule_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_attendance_extend',
                            'email_template_working_schedule_exchange_approval')[1]
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
                    if rec.date_from:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(rec.date_from).strftime('%d/%m/%Y')})
                    if rec.date_to:
                        ctx.update(
                            {'date_to': fields.Datetime.from_string(rec.date_to).strftime('%d/%m/%Y')})
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_working - 1
                        query_statement = """UPDATE working_schedule_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                        self.get_auto_follow_up_approver_wa_template(rec)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE working_schedule_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
                            self.get_auto_follow_up_approver_wa_template(rec)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        working_confirmed = self.search([('state', '=', 'to_approve')])
        for rec in working_confirmed:
            if rec.working_schedule_user_ids:
                matrix_line = sorted(rec.working_schedule_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.working_schedule_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_attendance_extend',
                                    'email_template_working_schedule_exchange_approval')[1]
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
                            if rec.date_from:
                                ctx.update(
                                    {'date_from': fields.Datetime.from_string(rec.date_from).strftime('%d/%m/%Y')})
                            if rec.date_to:
                                ctx.update(
                                    {'date_to': fields.Datetime.from_string(rec.date_to).strftime('%d/%m/%Y')})
                            approver.update({
                                'user_ids': [(4, user.user_delegation_id.id)],
                                'is_delegation_mail_sent': True,
                            })
                            rec.update({
                                'approvers_ids': [(4, user.user_delegation_id.id)],
                            })
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

    def action_confirm(self):
        setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_attendance_extend.attendance_approval_matrix')
        for rec in self:
            if setting:
                self.approver_mail()
                rec.write({'state': 'to_approve'})
                self.approver_wa_template()
                for line in rec.working_schedule_user_ids:
                    line.write({'approver_state': 'draft'})
            else:
                rec.write({'state': 'approved'})

    def action_approve(self):
        for rec in self:
            n = 0
            var = len(rec.schedule_calendar_ids)
            current_hour_from = rec.exchange_schedule_ids[n].hour_from
            current_hour_to = rec.exchange_schedule_ids[n].hour_to
            schedule_hour_from = rec.schedule_calendar_ids[n].hour_from
            schedule_hour_to = rec.schedule_calendar_ids[n].hour_to
            for current in rec.schedule_calendar_ids:
                if n < var:
                    rec.schedule_calendar_ids[n].write({'hour_from': current_hour_from,
                                                        'hour_to': current_hour_to})
                    rec.exchange_schedule_ids[n].write({'hour_from': schedule_hour_from,
                                                        'hour_to': schedule_hour_to})
                    n = n + 1
            # rec.write({'state': 'approved'})
            rec.approve_working_schedule_by_list()

    def approve_working_schedule_by_list(self):
        sequence_matrix = [data.name for data in self.working_schedule_user_ids]
        sequence_approval = [data.name for data in self.working_schedule_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.working_schedule_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        for record in self:
            current_user = self.env.uid
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_attendance_extend.attendance_type_approval')
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            if setting == 'employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.working_schedule_user_ids:
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
                        matrix_line = sorted(record.working_schedule_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            self.approved_mail()
                            record.write({'state': 'approved'})
                            self.approved_wa_template()
                        else:
                            self.approver_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has been approved the Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
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
                        for line in record.working_schedule_user_ids:
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
                                    line.approved_employee_ids = [(4, current_user)]

                        matrix_line = sorted(record.working_schedule_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            self.approved_mail()
                            record.write({'state': 'approved'})
                            self.approved_wa_template()
                        else:
                            self.approver_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
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

    def action_refuse(self):
        for record in self:
            for user in record.working_schedule_user_ids:
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
                        else:
                            user.approval_status = f"{self.env.user.name}:Refused"
                            user.approved_time = f"{self.env.user.name}:{dateformat}"
            self.reject_mail()
            record.approved_user = self.env.user.name + ' ' + 'has been Rejected!'
            record.write({'state': 'refused'})
            self.rejected_wa_template()

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.working.sheet.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
                      'context':{'is_approve':True},
            'target': 'new',
        }

    def wizard_refuse(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.working.sheet.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':False, 'default_state': 'rejected'},
            'target': 'new',
        }

    @api.constrains('date_from')
    def _check_date_from(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_attendance_extend.attendance_validation')
            if setting:
                if rec.date_from and rec.date_from <= date.today():
                    raise ValidationError("Cannot request working schedule exchange for the date has been passed ")


class WorkingScheduleApproverUser(models.Model):
    _name = 'working.schedule.approver.user'

    working_schedule_app_id = fields.Many2one('schedule.exchange', string="Advance Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'working_app_emp_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'wk_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='working_schedule_app_id.state')


    @api.depends('working_schedule_app_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.working_schedule_app_id.working_schedule_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.working_schedule_app_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.working_schedule_app_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids