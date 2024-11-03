from odoo import api, fields, models, _
from datetime import date, timedelta
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
import requests
from lxml import etree
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

headers = {'content-type': 'application/json'}


class MyLeaveCancelation(models.Model):
    _name = 'hr.leave.cancelation'
    _description = 'My Leave Cancelation'
    _inherit = ['mail.thread']
    _order = 'id desc'

    @api.model
    def default_get(self, fields):
        res = super(MyLeaveCancelation, self).default_get(fields)
        employees = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        res['employee_id'] = employees.id
        return res

    @api.model
    def create(self, vals):
        sequence_no = self.env['ir.sequence'].next_by_code('hr.leave.cancelation')
        vals.update({'name': sequence_no})
        return super(MyLeaveCancelation, self).create(vals)

    name = fields.Char('Name', default='New', copy=False)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True, required=True)
    domain_employee_ids = fields.Many2many('hr.employee', string="Employee Domain", compute='_compute_employee_ids')
    is_readonly = fields.Boolean(compute='_compute_read_only')
    state = fields.Selection(
        [('draft', 'To Submit'), ('confirm', 'To Approve'), ('validate', 'Approved'), ('refuse', 'Rejected')],
        string='Status', default='draft', tracking=True)
    leave_id = fields.Many2one('hr.leave', string='Leave', required=True,
                               domain="[('employee_id', '=', employee_id),('state','=','validate'),('request_date_to', "
                                      "'>=',datetime.datetime.now())]")
    holiday_status_id = fields.Many2one("hr.leave.type", string="Leave Type")
    request_date_from = fields.Date('Start Date',
                                    states={'confirm': [('readonly', True)], 'validate': [('readonly', True)]},
                                    tracking=True)
    request_date_to = fields.Date('End Date',
                                  states={'confirm': [('readonly', True)], 'validate': [('readonly', True)]},
                                  tracking=True)
    number_of_days = fields.Float('Days',
                                  states={'confirm': [('readonly', True)], 'validate': [('readonly', True)]})
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    reason = fields.Text("Reason", states={'confirm': [('readonly', True)], 'validate': [('readonly', True)]},
                         tracking=True)
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company')], string='Cancel Type', default='employee')
    department_id = fields.Many2one('hr.department', string='Department', related="employee_id.department_id",
                                    store=True)

    approvers_ids = fields.Many2many('res.users', 'cancel_approver_users_rel', string='Approvers')
    approved_user = fields.Text(string="Approved User", tracking=True)
    is_approver = fields.Boolean(string="Is Approver", compute="_compute_can_approve")
    approver_user_ids = fields.One2many('leave.cancel.approver.user', 'leave_cancel_id', string='Approver')
    approved_user_ids = fields.Many2many('res.users', string='Approved User')
    line_item_visible = fields.Boolean(string="Line item visible", compute="_compute_line_items")
    current_period = fields.Integer('Current Period', copy=False, store=True, compute='compute_current_period')
    current_year = fields.Integer('Current Year', store=True, compute='compute_current_period')
    feedback_parent = fields.Text(string='Parent Feedback')
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(MyLeaveCancelation, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(MyLeaveCancelation, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_(f'Cannot delete in {rec.state} status'))
        return super(MyLeaveCancelation, self).unlink()

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(MyLeaveCancelation, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.context.get('is_approve'):
            if self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
                root = etree.fromstring(res['arch'])
                root.set('create', 'true')
                root.set('edit', 'true')
                root.set('delete', 'true')
                res['arch'] = etree.tostring(root)
            elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_responsible') and not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
                root = etree.fromstring(res['arch'])
                root.set('create', 'true')
                root.set('edit', 'true')
                root.set('delete', 'false')
                res['arch'] = etree.tostring(root)
            
            else:
                root = etree.fromstring(res['arch'])
                root.set('create', 'false')
                root.set('edit', 'false')
                root.set('delete', 'false')
                res['arch'] = etree.tostring(root)
                
        return res

    @api.depends('employee_id')
    def _compute_read_only(self):
        for record in self:
            if self.env.user.has_group('hr_holidays.group_hr_holidays_responsible') and not self.env.user.has_group(
                    'equip3_hr_employee_access_right_setting.group_responsible' or record.holiday_type == 'employee'):
                record.is_readonly = True
            else:
                record.is_readonly = False

    @api.depends('employee_id')
    def _compute_employee_ids(self):
        for record in self:
            employee_ids = []
            if self.env.user.has_group(
                    'equip3_hr_employee_access_right_setting.group_responsible') and not self.env.user.has_group(
                    'hr_holidays.group_hr_holidays_user'):
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

    def custom_menu(self):
        # views = [(self.env.ref('bi_employee_travel_managment.view_travel_req_tree').id, 'tree'),
        #              (self.env.ref('bi_employee_travel_managment.view_travel_req_form').id, 'form')]
        search_view_id = self.env.ref("equip3_hr_holidays_extend.view_my_leave_cancel_tree")
        search_view_managed_id = self.env.ref("equip3_hr_holidays_extend.view_hr_leave_cancelation_filter")
        if self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_responsible') and not self.env.user.has_group(
                'hr_holidays.group_hr_holidays_user'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Leave Cancelation',
                    'res_model': 'hr.leave.cancelation',
                    'target': 'current',
                    'view_mode': 'tree,form',
                    # 'views':views,
                    'domain': ['|',('employee_id', 'in', employee_ids),('approvers_ids', 'in', self.env.user.ids)],
                    'context': {'default_holiday_type': 'company','search_default_pending_my_approval': 1,'is_approve':True},
                    'help': """<p class="o_view_nocontent_smiling_face">
                        Create a new Leave Cancelation
                    </p>""",
                    # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                    'search_view_id': search_view_managed_id.id,

                }

        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Leave Cancelation',
                'res_model': 'hr.leave.cancelation',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [],
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create a new Leave Cancelation
                </p>""",
                'context': {'default_holiday_type': 'company','search_default_pending_my_approval': 1,'is_approve':True},
                # 'views':views,
                'search_view_id': search_view_managed_id.id,
            }

    @api.depends('employee_id', 'request_date_to')
    def compute_current_period(self):
        for cancel in self:
            if cancel.request_date_to:
                cancel.current_period = cancel.request_date_to.year
                cancel.current_year = date.today().year
            else:
                cancel.current_period = 0
                cancel.current_year = 0

    @api.onchange('leave_id')
    def onchange_number_of_days(self):
        for holiday in self:
            if holiday.leave_id.request_date_from and holiday.leave_id.request_date_to:
                holiday.request_date_from = holiday.leave_id.request_date_from
                holiday.request_date_to = holiday.leave_id.request_date_to
                holiday.number_of_days = holiday.leave_id.number_of_days
                holiday.holiday_status_id = holiday.leave_id.holiday_status_id.id
            else:
                holiday.request_date_from = 0
                holiday.request_date_to = 0
                holiday.number_of_days = 0

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_holidays_extend', 'menu_open_department_leave_cancel')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_holidays_extend', 'hr_leave_cancel_action_department')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.holidays&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.approver_user_ids:
                matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approver_user_ids[len(matrix_line)]
                for user in approver.employee_id:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_holidays_extend',
                            'email_template_leave_cancel_request')[1]
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
                        'holiday_status_name': self.holiday_status_id.name,
                    })
                    if self.request_date_from:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(self.request_date_from).strftime('%d/%m/%Y')})
                    if self.request_date_to:
                        ctx.update({'date_to': fields.Datetime.from_string(self.request_date_to).strftime('%d/%m/%Y')})
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                              force_send=True)
                break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.approver_user_ids:
                for rec in rec.approver_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.employee_id:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_holidays_extend',
                                'email_template_edi_leave_cancel_approved')[1]
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
                            'holiday_status_name': self.holiday_status_id.name,
                        })
                        if self.request_date_from:
                            ctx.update(
                                {'date_from': fields.Datetime.from_string(self.request_date_from).strftime('%d/%m/%Y')})
                        if self.request_date_to:
                            ctx.update(
                                {'date_to': fields.Datetime.from_string(self.request_date_to).strftime('%d/%m/%Y')})
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                    break

    def reject_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.approver_user_ids:
                for rec in rec.approver_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.employee_id:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_holidays_extend',
                                'email_template_edi_leave_cancel_reject')[1]
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
                            'holiday_status_name': self.holiday_status_id.name,
                        })
                        if self.request_date_from:
                            ctx.update(
                                {'date_from': fields.Datetime.from_string(self.request_date_from).strftime('%d/%m/%Y')})
                        if self.request_date_to:
                            ctx.update(
                                {'date_to': fields.Datetime.from_string(self.request_date_to).strftime('%d/%m/%Y')})
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                    break

    def approver_wa_template(self):
        # base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # wa_sender = waParam()
        # template = self.env.ref('equip3_hr_holidays_extend.leave_cancel_approver_wa_template')
        # if template:
        #     if self.approver_user_ids:
        #         matrix_line = sorted(self.approver_user_ids.filtered(lambda r: r.is_approve == True))
        #         approver = self.approver_user_ids[len(matrix_line)]
        #         for user in approver.employee_id:
        #             wa_sender.set_wa_string(template.message,template._name,template_id=template)
        #             wa_sender.set_leave_approver_name(user.name)
        #             wa_sender.set_leave_employee_name(self.employee_id.name)
        #             wa_sender.set_leave_start_date(fields.Datetime.from_string(self.request_date_from).strftime('%d/%m/%Y'))
        #             wa_sender.set_leave_end_date(fields.Datetime.from_string(self.request_date_to).strftime('%d/%m/%Y'))
        #             wa_sender.set_leave_request_name(self.holiday_status_id.name)
        #             wa_sender.set_leave_name(self.name)
        #             wa_sender.set_leave_url(f"{base_url}/leave/{self.id}")
        #             wa_sender.send_wa(user.mobile_phone)
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_wa')
        if send_by_wa:
            # connector = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.connector_id')
            # if connector:
            #     connector_id = self.env['acrux.chat.connector'].search([('id', '=', connector)])
            #     if connector_id.ca_status:
            template = self.env.ref('equip3_hr_holidays_extend.leave_cancel_approver_wa_template')
            # url = self.get_url(self)
            wa_sender = waParam()
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if template:
                if self.approver_user_ids:
                    matrix_line = sorted(self.approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.approver_user_ids[len(matrix_line)]
                    for user in approver.employee_id:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", self.employee_id.name)
                        if "${leave_name}" in string_test:
                            string_test = string_test.replace("${leave_name}", self.holiday_status_id.name)
                        if "${start_date}" in string_test:
                            string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                                self.request_date_from).strftime('%d/%m/%Y'))
                        if "${end_date}" in string_test:
                            string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                                self.request_date_to).strftime('%d/%m/%Y'))
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.name)
                        # if "${survey_url}" in string_test:
                        #     string_test = string_test.replace("${survey_url}", url)
                        if "${br}" in string_test:
                            string_test = string_test.replace("${br}", f"\n")
                        if "${url}" in string_test:
                            string_test = string_test.replace("${url}", f"{base_url}/cancelation/{self.id}")
                        phone_num = str(user.mobile_phone)
                        if "+" in phone_num:
                            phone_num = int(phone_num.replace("+", ""))
                        
                        wa_sender.set_wa_string(string_test,template._name,template_id=template)
                        wa_sender.send_wa(phone_num)

        #                 param = {'body': string_test, 'phone': phone_num}
        #                 domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
        #                 token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
        #                 try:
        #                     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
        #                 except ConnectionError:
        #                     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")


    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_wa')
        if send_by_wa:
            # connector = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.connector_id')
            # if connector:
            #     connector_id = self.env['acrux.chat.connector'].search([('id', '=', connector)])
            #     if connector_id.ca_status:
            template = self.env.ref('equip3_hr_holidays_extend.leave_cancel_approved_wa_template')
            wa_sender = waParam()
            # url = self.get_url(self)
            if template:
                if self.approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${leave_name}" in string_test:
                        string_test = string_test.replace("${leave_name}", self.holiday_status_id.name)
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.request_date_from).strftime('%d/%m/%Y'))
                    if "${end_date}" in string_test:
                        string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                            self.request_date_to).strftime('%d/%m/%Y'))
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
                    # if "${survey_url}" in string_test:
                    #     string_test = string_test.replace("${survey_url}", url)
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
                    #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
                    # except ConnectionError:
                    #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")


    def rejected_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_wa')
        if send_by_wa:
            # connector = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.connector_id')
            # if connector:
            #     connector_id = self.env['acrux.chat.connector'].search([('id', '=', connector)])
            #     if connector_id.ca_status:
            template = self.env.ref('equip3_hr_holidays_extend.leave_cancel_rejected_wa_template')
            wa_sender = waParam()
            # url = self.get_url(self)
            if template:
                if self.approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${leave_name}" in string_test:
                        string_test = string_test.replace("${leave_name}", self.holiday_status_id.name)
                    if "${start_date}" in string_test:
                        string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                            self.request_date_from).strftime('%d/%m/%Y'))
                    if "${end_date}" in string_test:
                        string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                            self.request_date_to).strftime('%d/%m/%Y'))
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
                    # if "${survey_url}" in string_test:
                    #     string_test = string_test.replace("${survey_url}", url)
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
                    #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
                    # except ConnectionError:
                    #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def get_auto_follow_up_approver_wa_template(self, rec):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_wa')
        if send_by_wa:
            template = self.env.ref('equip3_hr_holidays_extend.leave_cancel_approver_wa_template')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if rec.approver_user_ids:
                    matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = rec.approver_user_ids[len(matrix_line)]
                    for user in approver.employee_id:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", rec.employee_id.name)
                        if "${leave_name}" in string_test:
                            string_test = string_test.replace("${leave_name}", rec.holiday_status_id.name)
                        if "${start_date}" in string_test:
                            string_test = string_test.replace("${start_date}", fields.Datetime.from_string(
                                rec.request_date_from).strftime('%d/%m/%Y'))
                        if "${end_date}" in string_test:
                            string_test = string_test.replace("${end_date}", fields.Datetime.from_string(
                                rec.request_date_to).strftime('%d/%m/%Y'))
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", rec.name)
                        # if "${survey_url}" in string_test:
                        #     string_test = string_test.replace("${survey_url}", url)
                        if "${br}" in string_test:
                            string_test = string_test.replace("${br}", f"\n")
                        if "${url}" in string_test:
                            string_test = string_test.replace("${url}", f"{base_url}/cancelation/{rec.id}")
                        phone_num = str(user.mobile_phone)
                        if "+" in phone_num:
                            phone_num = int(phone_num.replace("+", ""))
                        
                        wa_sender.set_wa_string(string_test,template._name,template_id=template)
                        wa_sender.send_wa(phone_num)
                        # param = {'body': string_test, 'phone': phone_num}
                        # domain = rec.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                        # token = rec.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                        # try:
                        #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
                        # except ConnectionError:
                        #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_leave = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.number_of_repetitions_leave'))
        leave_cancel_to_approve = self.search([('state', '=', 'confirm')])
        for rec in leave_cancel_to_approve:
            if rec.approver_user_ids:
                matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approver_user_ids[len(matrix_line)]
                for user in approver.employee_id:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_holidays_extend',
                            'email_template_leave_cancel_request')[1]
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
                        'holiday_status_name': rec.holiday_status_id.name,
                    })
                    if rec.request_date_from:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(rec.request_date_from).strftime('%d/%m/%Y')})
                    if rec.request_date_to:
                        ctx.update({'date_to': fields.Datetime.from_string(rec.request_date_to).strftime('%d/%m/%Y')})
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_leave - 1
                        query_statement = """UPDATE leave_cancel_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                        self.get_auto_follow_up_approver_wa_template(rec)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE leave_cancel_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
                            self.get_auto_follow_up_approver_wa_template(rec)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        leave_cancel_to_approve = self.search([('state', '=', 'confirm')])
        for rec in leave_cancel_to_approve:
            if rec.approver_user_ids:
                matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approver_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_holidays_extend',
                                    'email_template_leave_cancel_request')[1]
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
                                'holiday_status_name': rec.holiday_status_id.name,
                            })
                            if rec.request_date_from:
                                ctx.update(
                                    {'date_from': fields.Datetime.from_string(rec.request_date_from).strftime('%d/%m/%Y')})
                            if rec.request_date_to:
                                ctx.update({'date_to': fields.Datetime.from_string(rec.request_date_to).strftime('%d/%m/%Y')})
                            approver.update({
                                'employee_id': [(4, user.user_delegation_id.id)],
                                'is_delegation_mail_sent': True,
                            })
                            rec.update({
                                'approvers_ids': [(4, user.user_delegation_id.id)],
                            })
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

    def action_confirm(self):
        for rec in self:
            if rec.holiday_status_id.leave_validation_type == 'no_validation':
                rec.leave_id.action_refuse()
                self.approver_wa_template()
                self.approver_mail()
                rec.leave_id.write({'state': 'cancel'})
                rec.write({'state': 'validate'})
            else:
                self.approver_wa_template()
                self.approver_mail()
                rec.write({'state': 'confirm'})
                for line in rec.approver_user_ids:
                    line.write({'approver_state': 'draft'})

    @api.onchange('employee_id', 'holiday_status_id')
    def onchange_approver(self):
        for leave_cancel in self:
            app_list = []
            if leave_cancel.employee_id and leave_cancel.holiday_status_id.leave_validation_type == 'by_employee_hierarchy':
                app_level = leave_cancel.holiday_status_id.approval_level
                employee = leave_cancel.employee_id
                for i in range(app_level):
                    emp = self.env['hr.employee'].search([('id', '=', employee.id)])
                    if emp:
                        parent = self.env['hr.employee'].search([('id', '=', emp.parent_id.id)])
                        employee = parent
                        app_list.append(employee.user_id.id)
            elif leave_cancel.employee_id and leave_cancel.holiday_status_id.leave_validation_type == 'hr':
                responsible = leave_cancel.holiday_status_id.responsible_id
                # emp_responsible = self.env['hr.employee'].search([('user_id', '=', responsible.id)],
                #                                                  limit=1)
                if responsible:
                    app_list.append(responsible.id)
            elif leave_cancel.employee_id and leave_cancel.holiday_status_id.leave_validation_type == 'manager':
                emp_manager = leave_cancel.employee_id.parent_id.user_id
                if emp_manager:
                    app_list.append(emp_manager.id)
            elif leave_cancel.employee_id and leave_cancel.holiday_status_id.leave_validation_type == 'both':
                both_emp_manager = leave_cancel.employee_id.parent_id.user_id
                both_responsible = leave_cancel.holiday_status_id.responsible_id
                # both_emp_responsible = self.env['hr.employee'].search([('user_id', '=', both_responsible.id)],
                #                                                       limit=1)
                if both_emp_manager:
                    app_list.append(both_emp_manager.id)
                if both_responsible:
                    app_list.append(both_responsible.id)
            # elif leave_cancel.holiday_status_id.leave_validation_type == 'by_approval_matrix':
            #     employee_matrix = self.env['hr.leave.approval'].search(
            #         [('employee_ids', 'in', leave_cancel.employee_id.id)],
            #         limit=1)
            #     job_position_matrix = self.env['hr.leave.approval'].search(
            #         [('job_ids', 'in', leave_cancel.employee_id.job_id.id)], limit=1)
            #     department_matrix = self.env['hr.leave.approval'].search(
            #         [('department_ids', 'in', leave_cancel.employee_id.department_id.id)], limit=1)
            #     if employee_matrix:
            #         for line in employee_matrix.leave_approvel_matrix_ids:
            #             for approvers in line.approver_ids:
            #                 app_list.append(approvers.id)
            #     elif job_position_matrix:
            #         for line in job_position_matrix.leave_approvel_matrix_ids:
            #             for approvers in line.approver_ids:
            #                 app_list.append(approvers.id)
            #     elif department_matrix:
            #         for line in department_matrix.leave_approvel_matrix_ids:
            #             for approvers in line.approver_ids:
            #                 app_list.append(approvers.id)
            leave_cancel.approvers_ids = app_list

    def get_manager_hierarchy(self, leave_cancel, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(leave_cancel, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    @api.onchange('holiday_status_id', 'employee_id')
    def onchange_approver_user(self):
        for leave_cancel in self:
            if leave_cancel.approver_user_ids:
                leave_cancel.approver_user_ids.unlink()
                leave_cancel.approved_user_ids = False
            if leave_cancel.employee_id and leave_cancel.holiday_status_id.leave_validation_type == 'by_employee_hierarchy':
                app_level = leave_cancel.holiday_status_id.approval_level
                employee = leave_cancel.employee_id
                for i in range(app_level):
                    emp = self.env['hr.employee'].search([('id', '=', employee.id)])
                    if emp:
                        parent = self.env['hr.employee'].search([('id', '=', emp.parent_id.id)])
                        employee = parent
                        if employee:
                            vals = [(0, 0, {'employee_id': employee.user_id.ids, 'leave_cancel_id': self.id})]
                            leave_cancel.approver_user_ids = vals
            elif leave_cancel.employee_id and leave_cancel.holiday_status_id.leave_validation_type == 'hr':
                responsible = leave_cancel.holiday_status_id.responsible_id
                # emp_responsible = self.env['hr.employee'].search([('user_id', '=', responsible.id)],
                #                                                  limit=1)
                hr_vals = [(0, 0, {'employee_id': responsible, 'leave_cancel_id': self.id})]
                leave_cancel.approver_user_ids = hr_vals
            elif leave_cancel.employee_id and leave_cancel.holiday_status_id.leave_validation_type == 'manager':
                emp_manager = leave_cancel.employee_id.parent_id
                manager_vals = [(0, 0, {'employee_id': emp_manager.user_id.ids, 'leave_cancel_id': self.id})]
                leave_cancel.approver_user_ids = manager_vals
            elif leave_cancel.employee_id and leave_cancel.holiday_status_id.leave_validation_type == 'both':
                emp_manager = leave_cancel.employee_id.parent_id
                both_manager_vals = [(0, 0, {'employee_id': emp_manager.user_id.ids, 'leave_cancel_id': self.id})]
                leave_cancel.approver_user_ids = both_manager_vals
                responsible = leave_cancel.holiday_status_id.responsible_id
                # emp_responsible = self.env['hr.employee'].search([('user_id', '=', responsible.id)],
                #                                                  limit=1)
                both_hr_vals = [(0, 0, {'employee_id': responsible, 'leave_cancel_id': self.id})]
                leave_cancel.approver_user_ids = both_hr_vals
            elif leave_cancel.holiday_status_id.leave_validation_type == 'by_approval_matrix':
                app_list = []
                leave_type_matrix = self.env['hr.leave.approval'].search(
                    [('mode_type', '=', 'leave_type'), ('leave_type_ids', 'in', leave_cancel.holiday_status_id.id), (
                        'applicable_to', 'in', ['leave_request', 'leave_and_allocation_request'])], limit=1)
                employee_matrix = self.env['hr.leave.approval'].search(
                    [('mode_type', '=', 'employee'), ('employee_ids', 'in', leave_cancel.employee_id.id), (
                        'applicable_to', 'in', ['leave_request', 'leave_and_allocation_request'])], limit=1)
                job_position_matrix = self.env['hr.leave.approval'].search(
                    [('mode_type', '=', 'job_position'), ('job_ids', 'in', leave_cancel.employee_id.job_id.id), (
                        'applicable_to', 'in', ['leave_request', 'leave_and_allocation_request'])], limit=1)
                department_matrix = self.env['hr.leave.approval'].search(
                    [('mode_type', '=', 'department'), ('department_ids', 'in', leave_cancel.employee_id.department_id.id), (
                        'applicable_to', 'in', ['leave_request', 'leave_and_allocation_request'])], limit=1)
                if leave_type_matrix:
                    data_approvers = []
                    for line in leave_type_matrix.leave_approvel_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                          'employee_id': [(6, 0, line.approver_ids.ids)]}))
                            for approvers in line.approver_ids:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(leave_cancel, leave_cancel.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'employee_id': [(4, approver)]}))
                                app_list.append(approver)
                    leave_cancel.approvers_ids = app_list
                    leave_cancel.approver_user_ids = data_approvers
                elif employee_matrix:
                    data_approvers = []
                    for line in employee_matrix.leave_approvel_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                          'employee_id': [(6, 0, line.approver_ids.ids)]}))
                            for approvers in line.approver_ids:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(leave_cancel, leave_cancel.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'employee_id': [(4, approver)]}))
                                app_list.append(approver)
                    leave_cancel.approvers_ids = app_list
                    leave_cancel.approver_user_ids = data_approvers
                elif job_position_matrix:
                    data_approvers = []
                    for line in job_position_matrix.leave_approvel_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                          'employee_id': [(6, 0, line.approver_ids.ids)]}))
                            for approvers in line.approver_ids:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(leave_cancel, leave_cancel.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'employee_id': [(4, approver)]}))
                                app_list.append(approver)
                    leave_cancel.approvers_ids = app_list
                    leave_cancel.approver_user_ids = data_approvers
                elif department_matrix:
                    data_approvers = []
                    for line in department_matrix.leave_approvel_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                          'employee_id': [(6, 0, line.approver_ids.ids)]}))
                            for approvers in line.approver_ids:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(leave_cancel, leave_cancel.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'employee_id': [(4, approver)]}))
                                app_list.append(approver)
                    leave_cancel.approvers_ids = app_list
                    leave_cancel.approver_user_ids = data_approvers
            else:
                leave_cancel.approver_user_ids.unlink()
                leave_cancel.approved_user_ids = False

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve(self):
        for holiday in self:
            if holiday.approvers_ids:
                if holiday.holiday_status_id.leave_validation_type == 'by_employee_hierarchy':
                    current_user = holiday.env.user
                    matrix_line = sorted(holiday.approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(holiday.approver_user_ids)
                    if app < holiday.holiday_status_id.approval_level and app < a:
                        if current_user in holiday.approver_user_ids[app].employee_id:
                            holiday.is_approver = True
                        else:
                            holiday.is_approver = False
                    else:
                        holiday.is_approver = False
                elif holiday.holiday_status_id.leave_validation_type == 'hr':
                    current_user = holiday.env.user
                    if current_user in holiday.approvers_ids.user_id:
                        holiday.is_approver = True
                    else:
                        holiday.is_approver = False
                elif holiday.holiday_status_id.leave_validation_type == 'manager':
                    current_user = holiday.env.user
                    if current_user in holiday.approvers_ids.user_id:
                        holiday.is_approver = True
                    else:
                        holiday.is_approver = False
                elif holiday.holiday_status_id.leave_validation_type == 'both':
                    current_user = holiday.env.user
                    matrix_line = sorted(holiday.approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(holiday.approver_user_ids)
                    if app < 2 and app < a:
                        if current_user in holiday.approver_user_ids[len(matrix_line)].employee_id:
                            holiday.is_approver = True
                        else:
                            holiday.is_approver = False
                    else:
                        holiday.is_approver = False
                elif holiday.holiday_status_id.leave_validation_type == 'by_approval_matrix':
                    current_user = holiday.env.user
                    matrix_line = sorted(holiday.approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(holiday.approver_user_ids)
                    if app < a:
                        for line in holiday.approver_user_ids[app]:
                            if current_user in holiday.approved_user_ids:
                                holiday.is_approver = False
                            elif current_user in line.employee_id:
                                holiday.is_approver = True
                            else:
                                holiday.is_approver = False
                    else:
                        holiday.is_approver = False

                else:
                    holiday.is_approver = False
            else:
                holiday.is_approver = False

    def action_approve(self):
        for record in self:
            current_user = self.env.uid
            if record.holiday_status_id.leave_validation_type == 'by_employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.approver_user_ids:
                            for employee in user.employee_id:
                                if current_user == employee.id:
                                    user.is_approve = True
                                    user.timestamp = fields.Datetime.now()
                                    user.approver_state = 'approved'
                                    if user.approval_status:
                                        app_state = user.approval_status + ',' + self.env.user.name + ':' + 'Approved'
                                        app_time = user.approved_time + ',' + self.env.user.name + ':' + str(user.timestamp)
                                    else:
                                        app_state = self.env.user.name + ':' + 'Approved'
                                        app_time = self.env.user.name + ':' + str(user.timestamp)
                                    user.approval_status = app_state
                                    user.approved_time = app_time
                                    record.approved_user_ids = [(4, current_user)]
                        matrix_line = sorted(record.approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            self.approved_wa_template()
                            self.approved_mail()
                            record.leave_id.action_refuse()
                            record.leave_id.write({'state': 'cancel',
                                                   'is_refused_by_leave_cancel_form': True})
                            record.write({'state': 'validate'})
                        else:
                            self.approver_wa_template()
                            self.approver_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved for this Leave!'
                    ))
            elif record.holiday_status_id.leave_validation_type == 'hr':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.approver_user_ids:
                            for employee in user.employee_id:
                                if current_user == employee.id:
                                    user.is_approve = True
                                    user.timestamp = fields.Datetime.now()
                                    user.approver_state = 'approved'
                                    if user.approval_status:
                                        app_state = user.approval_status + ',' + self.env.user.name + ':' + 'Approved'
                                        app_time = user.approved_time + ',' + self.env.user.name + ':' + str(user.timestamp)
                                    else:
                                        app_state = self.env.user.name + ':' + 'Approved'
                                        app_time = self.env.user.name + ':' + str(user.timestamp)
                                    user.approval_status = app_state
                                    user.approved_time = app_time
                                    record.approved_user_ids = [(4, current_user)]
                        matrix_line = sorted(record.approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            self.approved_wa_template()
                            self.approved_mail()
                            record.leave_id.action_refuse()
                            record.leave_id.write({'state': 'cancel',
                                                   'is_refused_by_leave_cancel_form': True})
                            record.write({'state': 'validate'})
                        else:
                            self.approver_wa_template()
                            self.approver_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved for this Leave!'
                    ))
            elif record.holiday_status_id.leave_validation_type == 'manager':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.approver_user_ids:
                            for employee in user.employee_id:
                                if current_user == employee.id:
                                    user.is_approve = True
                                    user.timestamp = fields.Datetime.now()
                                    user.approver_state = 'approved'
                                    if user.approval_status:
                                        app_state = user.approval_status + ',' + self.env.user.name + ':' + 'Approved'
                                        app_time = user.approved_time + ',' + self.env.user.name + ':' + str(user.timestamp)
                                    else:
                                        app_state = self.env.user.name + ':' + 'Approved'
                                        app_time = self.env.user.name + ':' + str(user.timestamp)
                                    user.approval_status = app_state
                                    user.approved_time = app_time
                                    record.approved_user_ids = [(4, current_user)]
                        matrix_line = sorted(record.approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            self.approved_wa_template()
                            self.approved_mail()
                            record.leave_id.action_refuse()
                            record.leave_id.write({'state': 'cancel',
                                                   'is_refused_by_leave_cancel_form': True})
                            record.write({'state': 'validate'})
                        else:
                            self.approver_wa_template()
                            self.approver_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved for this Leave!'
                    ))
            elif record.holiday_status_id.leave_validation_type == 'both':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.approver_user_ids:
                            for employee in user.employee_id:
                                if current_user == employee.id:
                                    user.is_approve = True
                                    user.timestamp = fields.Datetime.now()
                                    user.approver_state = 'approved'
                                    if user.approval_status:
                                        app_state = user.approval_status + ',' + self.env.user.name + ':' + 'Approved'
                                        app_time = user.approved_time + ',' + self.env.user.name + ':' + str(user.timestamp)
                                    else:
                                        app_state = self.env.user.name + ':' + 'Approved'
                                        app_time = self.env.user.name + ':' + str(user.timestamp)
                                    user.approval_status = app_state
                                    user.approved_time = app_time
                                    record.approved_user_ids = [(4, current_user)]
                        matrix_line = sorted(record.approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            self.approved_wa_template()
                            self.approved_mail()
                            record.leave_id.action_refuse()
                            record.leave_id.write({'state': 'cancel',
                                                   'is_refused_by_leave_cancel_form': True})
                            record.write({'state': 'validate'})
                        else:
                            self.approver_wa_template()
                            self.approver_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved for this Leave!'
                    ))
            elif record.holiday_status_id.leave_validation_type == 'by_approval_matrix':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.approver_user_ids:
                            for employee in user.employee_id:
                                if current_user == employee.id:
                                    user.timestamp = fields.Datetime.now()
                                    record.approved_user_ids = [(4, current_user)]
                                    var = len(user.approved_employee_ids) + 1
                                    if user.minimum_approver <= var:
                                        user.approver_state = 'approved'
                                        if user.approval_status:
                                            app_state = user.approval_status + ',' + self.env.user.name + ':' + 'Approved'
                                            app_time = user.approved_time + ',' + self.env.user.name + ':' + str(
                                                user.timestamp)
                                        else:
                                            app_state = self.env.user.name + ':' + 'Approved'
                                            app_time = self.env.user.name + ':' + str(user.timestamp)
                                        user.approval_status = app_state
                                        user.approved_time = app_time
                                        user.is_approve = True
                                    else:
                                        user.approver_state = 'pending'
                                        if user.approval_status:
                                            app_state = user.approval_status + ',' + self.env.user.name + ':' + 'Approved'
                                            app_time = user.approved_time + ',' + self.env.user.name + ':' + str(
                                                user.timestamp)
                                        else:
                                            app_state = self.env.user.name + ':' + 'Approved'
                                            app_time = self.env.user.name + ':' + str(user.timestamp)
                                        user.approval_status = app_state
                                        user.approved_time = app_time
                                    user.approved_employee_ids = [(4, current_user)]

                        matrix_line = sorted(record.approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            self.approved_wa_template()
                            self.approved_mail()
                            record.leave_id.action_refuse()
                            record.leave_id.write({'state': 'cancel',
                                                   'is_refused_by_leave_cancel_form': True})
                            record.write({'state': 'validate'})
                        else:
                            self.approver_wa_template()
                            self.approver_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved for this Leave!'
                    ))
            else:
                record.leave_id.action_refuse()
                record.leave_id.write({'state': 'cancel',
                                       'is_refused_by_leave_cancel_form': True})
                record.write({'state': 'validate'})

    def action_refuse(self):
        for record in self:
            for user in record.approver_user_ids:
                for employee in user.employee_id:
                    if self.env.uid == employee.id:
                        user.timestamp = fields.Datetime.now()
                        user.approver_state = 'refuse'
                        if user.approval_status:
                            app_state = user.approval_status + ',' + self.env.user.name + ':' + 'Refused'
                            app_time = user.approved_time + ',' + self.env.user.name + ':' + str(user.timestamp)
                            if record.feedback_parent:
                                if user.feedback:
                                    feedback = user.feedback + ',' + self.env.user.name + ':' + str(record.feedback_parent)
                                else:
                                    feedback = self.env.user.name + ':' + str(record.feedback_parent)
                            else:
                                feedback = ""
                        else:
                            app_state = self.env.user.name + ':' + 'Refused'
                            app_time = self.env.user.name + ':' + str(user.timestamp)
                            if record.feedback_parent:
                                if user.feedback:
                                    feedback = user.feedback + ',' + self.env.user.name + ':' + str(record.feedback_parent)
                                else:
                                    feedback = self.env.user.name + ':' + str(record.feedback_parent)
                            else:
                                feedback = ""
                        user.approval_status = app_state
                        user.approved_time = app_time
                        user.feedback = feedback
            self.rejected_wa_template()
            self.reject_mail()
            record.approved_user = self.env.user.name + ' ' + 'has Refused the Leave Request!'
            record.write({'state': 'refuse'})
    
    def wizard_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.cancelation.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':False, 'default_state':'rejected'},
            'target': 'new'
        }

    @api.depends('employee_id', 'holiday_status_id')
    def _compute_line_items(self):
        for rec in self:
            if rec.holiday_status_id.leave_validation_type == 'no_validation':
                rec.line_item_visible = True
            else:
                rec.line_item_visible = False


class LeaveCancelApproverUser(models.Model):
    _name = 'leave.cancel.approver.user'

    leave_cancel_id = fields.Many2one('hr.leave.cancelation', string="Leave Cancel")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    employee_id = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'approved_cancel_users_rel', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Char(string="Timestamp")
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    approval_status = fields.Text(string="Approval Status")
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'leave_cancel_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='leave_cancel_id.state')
    feedback = fields.Text(string='Feedback')

    @api.depends('leave_cancel_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.leave_cancel_id.approver_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len(rec.employee_id) < rec.minimum_approver and rec.leave_cancel_id.state == 'draft':
                rec.minimum_approver = len(rec.employee_id)
            if not rec.matrix_user_ids and rec.leave_cancel_id.state == 'draft':
                rec.matrix_user_ids = rec.employee_id
