# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
from dateutil.relativedelta import relativedelta
from lxml import etree
import requests
import math
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
headers = {'content-type': 'application/json'}

class EmployeeLoanDetails(models.Model):
    _inherit = "employee.loan.details"

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    loan_type = fields.Many2one(domain=_multi_company_domain)
    loan_approver_user_ids = fields.One2many('loan.approver.user', 'emp_loan_id', string='Approver')
    approvers_ids = fields.Many2many('res.users', 'emp_loan_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    feedback_parent = fields.Text(string='Parent Feedback')
    #insallment line items
    can_approve_installment = fields.Boolean(compute='_compute_can_approve_installment', string="Installment Approvers")
    is_readonly = fields.Boolean(compute='_compute_readonly')
    domain_employee_ids = fields.Many2many('hr.employee', string="Employee Domain", compute='_compute_employee_ids')
    disburse_method = fields.Selection(
        related='loan_type.disburse_method', 
        string='Disburse Method', 
        store=True
    )
    payslip_id = fields.Many2one('hr.payslip', string="Payslip")
    disburse_payroll = fields.Boolean(compute='_check_disburse_payroll', string='Disburse Payroll Status', store=True)
    is_computed = fields.Boolean()
    disburse_button_hide = fields.Boolean(compute='_check_disburse_button_hide', string='Disburse Button')
    loan_proof_ids = fields.One2many('employee.loan.proof', 'emp_loan_id', string='Loan Proofs')
    is_loan_approval_matrix = fields.Boolean("Is Loan Approval Matrix", compute='_compute_is_loan_approval_matrix')
    state1 = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('applied', 'Applied'),
            ('approved', 'Applied'),
            ('paid', 'Paid'),
            ('disburse', 'Disbursed'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled')],
        string='Status',
        default='draft',
        tracking=False,
        copy=False,
        store=True,
        compute='_compute_state1'
    )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeLoanDetails, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeLoanDetails, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_is_loan_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_approval_matrix')
            rec.is_loan_approval_matrix = setting

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].sudo().get('employee.loan.details') or ' '
        vals['name'] = sequence
        result = super(EmployeeLoanDetails, self).create(vals)
        return result

    def round_up(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.ceil(n * multiplier) / multiplier

    def round_down(self, n, decimals=0):
        multiplier = 10 ** decimals
        return math.floor(n * multiplier) / multiplier
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(EmployeeLoanDetails, self).fields_view_get(
            view_id=view_id, view_type=view_type)
        if self.env.context.get('search_default_toapprove'):
            if self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_finance'):
                root = etree.fromstring(res['arch'])
                root.set('create', 'true')
                root.set('edit', 'true')
                root.set('delete', 'true')
                res['arch'] = etree.tostring(root)
            else :
                root = etree.fromstring(res['arch'])
                root.set('create', 'false')
                root.set('edit', 'false')
                root.set('delete', 'false')
                res['arch'] = etree.tostring(root)
        return res
        
    
    
    def custom_menu(self):
            # views = [(self.env.ref('bi_employee_travel_managment.view_travel_req_tree').id, 'tree'),
        #              (self.env.ref('bi_employee_travel_managment.view_travel_req_form').id, 'form')]
        search_view_id = self.env.ref("hr_employee_loan.view_loan_filter")
        if self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_self_service') and not self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_supervisor'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Loan Requests',
                'res_model': 'employee.loan.details',
                'target': 'current',
                'view_mode': 'tree,form,calendar,graph',
                # 'views':views,
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                # 'context': {'default_holiday_type': 'company'},
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create New Loan
                </p>""",
                'context':{},
                'search_view_id': search_view_id.id,

            }
        elif self.env.user.has_group(
                'equip3_hr_employee_loan_extend.group_loan_supervisor') and not self.env.user.has_group(
                'equip3_hr_employee_loan_extend.group_loan_finance'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Loan Requests',
                    'res_model': 'employee.loan.details',
                    'target': 'current',
                    'view_mode': 'tree,form,calendar,graph',
                    # 'views':views,
                    'domain': [('employee_id', 'in', employee_ids)],
                    'context': {},
                    'help': """<p class="o_view_nocontent_smiling_face">
                    Create New Loan
                    </p>""",
                    'search_view_id': search_view_id.id,

                }

        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Loan Requests',
                'res_model': 'employee.loan.details',
                'target': 'current',
                'view_mode': 'tree,form,calendar,graph',
                'domain': [],
                'context': {},
                'help': """<p class="o_view_nocontent_smiling_face">
                Create New Loan
                </p>""",
                'search_view_id': search_view_id.id,
              
            }
    
    
    
    @api.depends('employee_id')
    def _compute_readonly(self):
        for record in self:
            if self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_self_service') and not self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_supervisor'):
                record.is_readonly = True
            else:
                record.is_readonly = False


    @api.depends('employee_id')
    def _compute_employee_ids(self):
        for record in self:
            employee_ids = []
            if self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_supervisor') and not self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_finance'):
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
   
   
    
    @api.onchange('loan_type')
    def onchange_loan_proof(self):
        for loan in self:
            if loan.loan_proof_ids:
                remove = []
                for line in loan.loan_proof_ids:
                    remove.append((2, line.id))
                loan.loan_proof_ids = remove
            line = []
            for rec in loan.loan_type.loan_proof_ids:
                line.append((0, 0, {'name': rec.name,
                                    'mandatory': rec.mandatory
                                    }))
            loan.loan_proof_ids = line
    
    @api.constrains('loan_proof_ids')
    def _check_attachment(self):
        for rec in self:
            for line in rec.loan_proof_ids:
                if line.mandatory and not line.attachment:
                    raise ValidationError(_("""You must add %s attachment.""") % (line.name))
    
    @api.onchange('employee_id')
    def onchange_loan_policies(self):
        for loan in self:
            if (not loan.employee_id):
                return
            employee_id = loan.employee_id.id
            employee = self.env['hr.employee'].sudo().browse(employee_id)
        
            policies_on_categ = []
            policies_on_empl = []
            for categ in employee.sudo().category_ids:
                if categ.loan_policy:
                    policies_on_categ += map(lambda x:x.id, categ.loan_policy)
            if employee.loan_policy:
                policies_on_empl += map(lambda x:x.id, employee.loan_policy)
            loan_policy_ids = list(set(policies_on_categ + policies_on_empl))
            loan.update({'loan_policy_ids': [(6, 0, loan_policy_ids)]})
    
    @api.onchange('employee_id', 'loan_type', 'principal_amount')
    def onchange_approver_user(self):
        for loan in self:
            loan_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_approval_matrix')
            if loan_setting:
                if loan.loan_approver_user_ids:
                    remove = []
                    for line in loan.loan_approver_user_ids:
                        remove.append((2, line.id))
                    loan.loan_approver_user_ids = remove
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_employee_loan_extend.loan_type_approval')
                if setting == 'employee_hierarchy':
                    loan.loan_approver_user_ids = self.loan_emp_by_hierarchy(loan)
                    self.app_list_loan_emp_by_hierarchy()
                if setting == 'approval_matrix':
                    self.loan_approval_by_matrix(loan)
                
    @api.model
    def default_get(self, fields):
        res = super(EmployeeLoanDetails, self).default_get(fields)
        employees = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        res['employee_id'] = employees.id
        return res

    def loan_emp_by_hierarchy(self, loan):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(loan, loan.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, loan, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_level')
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
                self.get_manager(loan, employee_manager['parent_id'], data, approval_ids, seq)
                break
        return approval_ids

    def app_list_loan_emp_by_hierarchy(self):
        for loan in self:
            app_list = []
            for line in loan.loan_approver_user_ids:
                app_list.append(line.user_ids.id)
            loan.approvers_ids = app_list

    def get_manager_hierarchy(self, loan, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(loan, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def loan_approval_by_matrix(self, loan):
        app_list = []
        approval_matrix = self.env['hr.loan.approval.matrix'].search(
            [('applicable_to', '=', 'loan_request'), ('apply_to', '=', 'by_employee'), ('maximum_amount', '>=', loan.principal_amount),
             ('minimum_amount', '<=', loan.principal_amount)])
        matrix = approval_matrix.filtered(lambda line: loan.employee_id.id in line.employee_ids.ids)
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
                    approvers = self.get_manager_hierarchy(loan, loan.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            loan.approvers_ids = app_list
            loan.loan_approver_user_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.loan.approval.matrix'].search(
                [('applicable_to', '=', 'loan_request'), ('apply_to', '=', 'by_job_position'), ('maximum_amount', '>=', loan.principal_amount),
                 ('minimum_amount', '<=', loan.principal_amount)])
            matrix = approval_matrix.filtered(lambda line: loan.job_id.id in line.job_ids.ids)
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
                        approvers = self.get_manager_hierarchy(loan, loan.employee_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                loan.approvers_ids = app_list
                loan.loan_approver_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.loan.approval.matrix'].search(
                    [('applicable_to', '=', 'loan_request'), ('apply_to', '=', 'by_department'), ('maximum_amount', '>=', loan.principal_amount),
                     ('minimum_amount', '<=', loan.principal_amount)])
                matrix = approval_matrix.filtered(lambda line: loan.department_id.id in line.department_ids.ids)
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
                            approvers = self.get_manager_hierarchy(loan, loan.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    loan.approvers_ids = app_list
                    loan.loan_approver_user_ids = data_approvers

    @api.depends('state', 'employee_id')
    def _compute_can_approve(self):
        for loan in self:
            if loan.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_employee_loan_extend.loan_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_employee_loan_extend.loan_level')
                app_level = int(setting_level)
                current_user = loan.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(loan.loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(loan.loan_approver_user_ids)
                    if app < app_level and app < a:
                        if current_user in loan.loan_approver_user_ids[app].user_ids:
                            loan.is_approver = True
                        else:
                            loan.is_approver = False
                    else:
                        loan.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(loan.loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(loan.loan_approver_user_ids)
                    if app < a:
                        for line in loan.loan_approver_user_ids[app]:
                            if current_user in line.user_ids:
                                loan.is_approver = True
                            else:
                                loan.is_approver = False
                    else:
                        loan.is_approver = False

                else:
                    loan.is_approver = False
            else:
                loan.is_approver = False

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'hr_employee_loan', 'loan_loans')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'hr_employee_loan', 'action_loan')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=employee.loan.details&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.loan_approver_user_ids:
                matrix_line = sorted(rec.loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.loan_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_employee_loan_extend',
                            'email_template_loan_approval_request')[1]
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
                        'loan_type_name': self.loan_type.name,
                        'principal_amount': self.principal_amount,
                        'duration': self.duration,
                    })
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                              force_send=True)
                break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.loan_approver_user_ids:
                for rec in rec.loan_approver_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.user_ids:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_employee_loan_extend',
                                'email_template_edi_loan_request_approved')[1]
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
            if rec.loan_approver_user_ids:
                for rec in rec.loan_approver_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.user_ids:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_employee_loan_extend',
                                'email_template_edi_loan_request_reject')[1]
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
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                    break

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.send_by_wa_loan')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(self)
        if send_by_wa:
            template = self.env.ref('equip3_hr_employee_loan_extend.loan_approver_wa_template')
            wa_sender = waParam()
            if template:
                if self.loan_approver_user_ids:
                    matrix_line = sorted(self.loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.loan_approver_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", self.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.name)
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${loan_type}" in string_test:
                            string_test = string_test.replace("${loan_type}", self.loan_type.name)
                        if "${currency}" in string_test:
                            string_test = string_test.replace("${currency}", self.currency_id.symbol)
                        if "${amount}" in string_test:
                            string_test = string_test.replace("${amount}", str(self.principal_amount))
                        if "${month}" in string_test:
                            string_test = string_test.replace("${month}", str(self.duration))
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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.send_by_wa_loan')
        if send_by_wa:
            template = self.env.ref('equip3_hr_employee_loan_extend.loan_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.loan_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.send_by_wa_loan')
        if send_by_wa:
            template = self.env.ref('equip3_hr_employee_loan_extend.loan_rejected_wa_template')
            url = self.get_url(self)
            wa_sender = waParam()
            if template:
                if self.loan_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.name)
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

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_loan = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.number_of_repetitions_loan'))
        loan_applied = self.search([('state', '=', 'applied')])
        for rec in loan_applied:
            if rec.loan_approver_user_ids:
                matrix_line = sorted(rec.loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.loan_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_employee_loan_extend',
                            'email_template_loan_approval_request')[1]
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
                        'loan_type_name': rec.loan_type.name,
                        'principal_amount': rec.principal_amount,
                        'duration': rec.duration,
                    })
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_loan - 1
                        query_statement = """UPDATE loan_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE loan_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        loan_applied = self.search([('state', '=', 'applied')])
        for rec in loan_applied:
            if rec.loan_approver_user_ids:
                matrix_line = sorted(rec.loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.loan_approver_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_employee_loan_extend',
                                    'email_template_loan_approval_request')[1]
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
                                'loan_type_name': rec.loan_type.name,
                                'principal_amount': rec.principal_amount,
                                'duration': rec.duration,
                            })
                            approver.update({
                                'user_ids': [(4, user.user_delegation_id.id)],
                                'is_delegation_mail_sent': True,
                            })
                            rec.update({
                                'approvers_ids': [(4, user.user_delegation_id.id)],
                            })
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

    def action_applied_custom(self):
        # res = super(EmployeeLoanDetails, self).action_applied()
        self.check_categ()
        if self.employee_id and self.loan_type:
            if self.loan_type.apply_to == 'years_of_service':
                if self.employee_id.years_of_service < self.loan_type.years_of_service and self.employee_id.months < self.loan_type.months_of_service and self.employee_id.days < self.loan_type.days_of_service:
                    raise ValidationError(_('Employee not qualify'))
        loan_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_approval_matrix')
        for loan in self:
            if loan_setting:
                loan.state = 'applied'
                self.approver_mail()
                self.approver_wa_template()
                for line in self.loan_approver_user_ids:
                    line.write({'approver_state': 'draft'})
            else:
                date_approved = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
                loan.write({'state': 'approved',
                            'date_approved': date_approved})
        # return res

    # @api.multi
    def action_applied(self):
        for loan in self:
            # self.onchange_loan_type(loan.loan_type.id, loan.employee_id.id)
            msg = ''
            if loan.principal_amount <= 0.0:
                msg += 'Principal Amount\n '
            if loan.int_payable and loan.int_rate <= 0.0:
                msg += 'Interest Rate\n '
            if loan.duration <= 0.0:
                msg += 'Duration of Loan'
            if msg:
                raise UserError(_('Please Enter values greater then zero:\n %s ') % (msg))
            status = self.check_employee_loan_qualification(loan)
            if not isinstance(status, bool):
                raise UserError(_('Loan Policies not satisfied :\n %s ') % (_(status)))
            # seq_no = self.env['ir.sequence'].get('employee.loan.details')
            #             self.write({'state':'applied', 'name':seq_no})

            # loan.name = seq_no
        self.action_applied_custom()
        return True

    @api.constrains('loan_type', 'employee_id')
    def constrains_loan_type(self):
        for loan in self:
            self.onchange_loan_type(loan.loan_type.id, loan.employee_id.id)

    def check_categ(self):
        for rec in self:
            if rec.loan_type.apply_to == 'employee_categories':
                categ = self.env['loan.type'].search([('id', '=', rec.loan_type.id), ('employee_categ_ids', 'in', rec.employee_id.category_ids.ids)], limit=1)
                if not categ:
                    raise UserError(_('%s does not Qualify for Loan Type By Employee Categories') % (rec.employee_id.name))

    def action_approved(self):
        sequence_matrix = [data.name for data in self.loan_approver_user_ids]
        sequence_approval = [data.name for data in self.loan_approver_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.loan_approver_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        for record in self:
            current_user = self.env.uid
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_employee_loan_extend.loan_type_approval')
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            date_approved = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_approved_obj = datetime.strptime(date_approved, DEFAULT_SERVER_DATE_FORMAT)
            if setting == 'employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.loan_approver_user_ids:
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
                        matrix_line = sorted(record.loan_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            self.approved_mail()
                            record.write({'state': 'approved',
                                          'date_approved': date_approved})
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
                        for line in record.loan_approver_user_ids:
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

                        matrix_line = sorted(record.loan_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            self.approved_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            record.write({'state': 'approved',
                                          'date_approved': date_approved})
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

    def action_rejected(self):
        for record in self:
            for user in record.loan_approver_user_ids:
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
            self.reject_mail()
            record.approved_user = self.env.user.name + ' ' + 'has been Rejected!'
            record.write({'state': 'rejected'})
            self.rejected_wa_template()

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.loan.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':True},
            'name': "Confirmation Message",
            'target': 'new',
        }
        
        
    def wizard_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.loan.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':False,
                       'default_is_reject':True},
            'name': "Confirmation Message",
            'target': 'new',
        }

    def _calc_max_loan_amt(self):
        res = super(EmployeeLoanDetails, self)._calc_max_loan_amt()
        for rec in self:
            for policy in rec.loan_policy_ids:
                if policy.policy_type == 'maxamt':
                    if policy.max_loan_type == 'salary_percentage':
                        if rec.employee_id.contract_id.wage:
                            rec.max_loan_amt = rec.employee_id.contract_id.wage * policy.policy_value / 100
        return res

    def _compute_can_approve_installment(self):
        current_user = self.env.uid
        for rec in self:
            if rec.approvers_ids and current_user in rec.approvers_ids.ids:
                rec.can_approve_installment = True
            else:
                rec.can_approve_installment = False

    @api.depends('loan_type', 'payslip_id', 'payslip_id.state')
    def _check_disburse_payroll(self):
        payslip_obj = self.env['hr.payslip']
        for loan in self:
            if loan.loan_type:
                if loan.loan_type.disburse_method == 'payroll':
                    if loan.payslip_id:
                        if loan.payslip_id.state == 'done':
                            for line in loan.payslip_id.line_ids:
                                if line.salary_rule_id.code == "LOAN":
                                    loan.disburse_payroll = True
                                    self._cr.execute("update employee_loan_details set state='disburse' where id = %s" % (loan.id))
                                    self._cr.execute("update loan_installment_details set loan_state='disburse' where loan_id = %s" % (loan.id))

    def compute_installments(self):
        res = super(EmployeeLoanDetails, self).compute_installments()
        loan_rounding = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_rounding')
        loan_rounding_type = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_rounding_type')
        loan_rounding_digit = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_rounding_digit')
        for loan in self:
            if loan.installment_lines:
                for install in loan.installment_lines:
                    total_amount = 0
                    amount_digit = len(str(int(install.total))) - 1
                    if int(loan_rounding_digit) >= amount_digit:
                        loan_rounding_digit = amount_digit
                    if loan_rounding:
                        if loan_rounding_type == 'round':
                            total_amount = round(install.total,-abs(int(loan_rounding_digit)))
                        if loan_rounding_type == 'round_up':
                            total_amount = self.round_up(install.total,-abs(int(loan_rounding_digit)))
                        elif loan_rounding_type == 'round_down':
                            total_amount = self.round_down(install.total,-abs(int(loan_rounding_digit)))
                    else:
                        total_amount = install.total
                    install.total = total_amount
                    install.onchange_approver_user()
            loan.is_computed = True
        return True

    @api.depends('disburse_method', 'state')
    def _check_disburse_button_hide(self):
        for rec in self:
            if rec.disburse_method == 'payroll' or rec.state != 'approved' or not rec.is_computed:
                rec.disburse_button_hide = True
            else:
                rec.disburse_button_hide = False

class LoanApproverUser(models.Model):
    _name = 'loan.approver.user'

    emp_loan_id = fields.Many2one('employee.loan.details', string="Employee Loan Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'emp_loan_user_ids', string="Approved user")
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
    matrix_user_ids = fields.Many2many('res.users', 'loan_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='emp_loan_id.state')


    @api.depends('emp_loan_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.emp_loan_id.loan_approver_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.emp_loan_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.emp_loan_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids

class LoanInstallmentDetail(models.Model):
    _inherit = 'loan.installment.details'

    can_approve_installment = fields.Boolean(string="Installment Approvers", related='loan_id.can_approve_installment')
    is_book_interest = fields.Boolean(string="Book Interest Approvers", compute='_compute_is_book_interest')
    deduction_based_period = fields.Selection(
        related='loan_type.deduction_based_period',
        string='Deduction Based On Period',
        store=True,
    )
    payslip_id = fields.Many2one('hr.payslip', string="Payslip")
    paid_payroll = fields.Boolean(compute='_check_paid_payroll', string='Paid Payroll Status', store=True)
    state = fields.Selection(selection_add=[('rejected', 'Rejected')], ondelete={'rejected': 'cascade'},
                             string='State', readonly=True, default='unpaid', tracking=True)
    #Approval Matrix
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    loan_installment_approver_user_ids = fields.One2many('loan.installment.approver.user', 'loan_id', string='Approver')
    approvers_ids = fields.Many2many('res.users', 'loan_installment_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    is_approved = fields.Boolean(string="Is Approved", compute="_compute_is_approved")
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(LoanInstallmentDetail, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(LoanInstallmentDetail, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def custom_menu(self):
            # views = [(self.env.ref('bi_employee_travel_managment.view_travel_req_tree').id, 'tree'),
        #              (self.env.ref('bi_employee_travel_managment.view_travel_req_form').id, 'form')]
        search_view_id = self.env.ref("hr_employee_loan.view_loan_installment_filter")
        if self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_self_service') and not self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_supervisor'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Loan Installments',
                'res_model': 'loan.installment.details',
                'target': 'current',
                'view_mode': 'tree,form,graph',
                # 'views':views,
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                # 'context': {'default_holiday_type': 'company'},
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create New Loan Installments
                </p>""",
                'context':{},
                'search_view_id': search_view_id.id,

            }
        elif self.env.user.has_group(
                'equip3_hr_employee_loan_extend.group_loan_supervisor') and not self.env.user.has_group(
                'equip3_hr_employee_loan_extend.group_loan_finance'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Loan Installments',
                    'res_model': 'loan.installment.details',
                    'target': 'current',
                    'view_mode': 'tree,form,graph',
                    # 'views':views,
                    'domain': [('employee_id', 'in', employee_ids)],
                    'context': {},
                    'help': """<p class="o_view_nocontent_smiling_face">
                    Create New Loan Installments
                    </p>""",
                    'search_view_id': search_view_id.id,

                }

        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Loan Installments',
                'res_model': 'loan.installment.details',
                'target': 'current',
                'view_mode': 'tree,form,graph',
                'domain': [],
                'context': {},
                'help': """<p class="o_view_nocontent_smiling_face">
                Create New Loan Installments
                </p>""",
                'search_view_id': search_view_id.id,
                
            }

    def _compute_is_book_interest(self):
        current_user = self.env.user
        for rec in self:
            if rec.interest_amt == 0 or rec.int_move_id or rec.state != 'paid':
                rec.is_book_interest = True
            else:
                rec.is_book_interest = False

    @api.depends('loan_id', 'loan_id.loan_type', 'payslip_id', 'payslip_id.state')
    def _check_paid_payroll(self):
        payslip_obj = self.env['hr.payslip']
        move_pool = self.env['account.move'] 
        for install in self:
            if install.loan_id:
                if install.loan_id.loan_type.payment_method == 'payroll':
                    if install.payslip_id and not install.paid_payroll:
                        if install.payslip_id.state == 'done':
                            for line in install.payslip_id.line_ids:
                                if line.salary_rule_id.code == "LOAN_DED":
                                    address_id = install.loan_id.employee_id.address_home_id or False
                                    partner_id = address_id  and address_id.id or False

                                    if not partner_id:
                                        raise UserError(_('Please configure Home Address for Employee !'))

                                    move = {
                                        'narration': install.loan_id.name,
                                        'date': install.date_from,
                                        'ref': install.install_no,
                                        'journal_id': install.loan_id.journal_id1.id,
                                    }
                                    if not install.loan_id.journal_id1.default_account_id:
                                        raise UserError(_('Please configure Debit/Credit accounts on the Journal %s ') % (self.journal_id1.name))
                                    debit_line = (0, 0, {
                                            'name': _('EMI of loan %s') % (install.loan_id.name),
                                            'date': install.date_from,
                                            'partner_id': partner_id,
                                            'account_id': install.loan_id.journal_id1.default_account_id.id,
                                            'journal_id': install.loan_id.journal_id1.id,
                                            'debit': install.total,
                                            'credit': 0.0,
                                        })
                                    credit_line = (0, 0, {
                                            'name': _('EMI of loan %s') % (install.loan_id.name),
                                            'date': install.date_from,
                                            'partner_id': partner_id,
                                            'account_id': install.loan_id.employee_loan_account.id,
                                            'journal_id':  install.loan_id.journal_id1.id,
                                            'debit': 0.0,
                                            'credit':install.total,
                                        })
                                    move.update({'line_ids': [debit_line, credit_line]})
                                    move_id = move_pool.create(move)
                                    move_id.action_post()
                                    install.write({'move_id':move_id.id})
                                    install.paid_payroll = True
                                    self._cr.execute("update loan_installment_details set state='paid' where id = %s" % (install.id))

    @api.onchange('employee_id', 'loan_id')
    def onchange_approver_user(self):
        for loan_installment in self:
            if loan_installment.loan_installment_approver_user_ids:
                remove = []
                for line in loan_installment.loan_installment_approver_user_ids:
                    remove.append((2, line.id))
                loan_installment.loan_installment_approver_user_ids = remove
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_employee_loan_extend.loan_type_approval')
            if setting == 'employee_hierarchy':
                loan_installment.loan_installment_approver_user_ids = self.loan_installment_emp_by_hierarchy(loan_installment)
                self.app_list_loan_installment_emp_by_hierarchy()
            if setting == 'approval_matrix':
                self.loan_installment_approval_by_matrix(loan_installment)

    def loan_installment_emp_by_hierarchy(self, loan_installment):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(loan_installment, loan_installment.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, loan_installment, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_level')
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
                self.get_manager(loan_installment, employee_manager['parent_id'], data, approval_ids, seq)
                break
        return approval_ids

    def app_list_loan_installment_emp_by_hierarchy(self):
        for loan_installment in self:
            app_list = []
            for line in loan_installment.loan_installment_approver_user_ids:
                app_list.append(line.user_ids.id)
            loan_installment.approvers_ids = app_list

    def get_manager_hierarchy(self, loan_installment, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(loan_installment, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def loan_installment_approval_by_matrix(self, loan_installment):
        app_list = []
        approval_matrix = self.env['hr.loan.approval.matrix'].search(
            [('applicable_to', '=', 'loan_installment'), ('apply_to', '=', 'by_employee'), ('maximum_amount', '>=', loan_installment.principal_amt),
             ('minimum_amount', '<=', loan_installment.principal_amt)])
        matrix = approval_matrix.filtered(lambda line: loan_installment.employee_id.id in line.employee_ids.ids)
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
                    approvers = self.get_manager_hierarchy(loan_installment, loan_installment.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            loan_installment.approvers_ids = app_list
            loan_installment.loan_installment_approver_user_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.loan.approval.matrix'].search(
                [('applicable_to', '=', 'loan_installment'), ('apply_to', '=', 'by_job_position'), ('maximum_amount', '>=', loan_installment.principal_amt),
                 ('minimum_amount', '<=', loan_installment.principal_amt)])
            matrix = approval_matrix.filtered(lambda line: loan_installment.job_id.id in line.job_ids.ids)
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
                        approvers = self.get_manager_hierarchy(loan_installment, loan_installment.employee_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                loan_installment.approvers_ids = app_list
                loan_installment.loan_installment_approver_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.loan.approval.matrix'].search(
                    [('applicable_to', '=', 'loan_installment'), ('apply_to', '=', 'by_department'), ('maximum_amount', '>=', loan_installment.principal_amt),
                     ('minimum_amount', '<=', loan_installment.principal_amt)])
                matrix = approval_matrix.filtered(lambda line: loan_installment.department_id.id in line.department_ids.ids)
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
                            approvers = self.get_manager_hierarchy(loan_installment, loan_installment.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    loan_installment.approvers_ids = app_list
                    loan_installment.loan_installment_approver_user_ids = data_approvers

    @api.depends('state', 'employee_id')
    def _compute_can_approve(self):
        for loan_installment in self:
            if loan_installment.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_employee_loan_extend.loan_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_employee_loan_extend.loan_level')
                app_level = int(setting_level)
                current_user = loan_installment.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(loan_installment.loan_installment_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(loan_installment.loan_installment_approver_user_ids)
                    if app < app_level and app < a:
                        if current_user in loan_installment.loan_installment_approver_user_ids[app].user_ids:
                            loan_installment.is_approver = True
                        else:
                            loan_installment.is_approver = False
                    else:
                        loan_installment.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(loan_installment.loan_installment_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(loan_installment.loan_installment_approver_user_ids)
                    if app < a:
                        for line in loan_installment.loan_installment_approver_user_ids[app]:
                            if current_user in line.user_ids:
                                loan_installment.is_approver = True
                            else:
                                loan_installment.is_approver = False
                    else:
                        loan_installment.is_approver = False

                else:
                    loan_installment.is_approver = False
            else:
                loan_installment.is_approver = False

    def action_approved(self):
        sequence_matrix = [data.name for data in self.loan_installment_approver_user_ids]
        sequence_approval = [data.name for data in self.loan_installment_approver_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.loan_installment_approver_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        for record in self:
            current_user = self.env.uid
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_employee_loan_extend.loan_type_approval')
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            date_approved = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_approved_obj = datetime.strptime(date_approved, DEFAULT_SERVER_DATE_FORMAT)
            if setting == 'employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.loan_installment_approver_user_ids:
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
                        matrix_line = sorted(record.loan_installment_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            # self.pay_installment()
                            record.write({'state': 'approve'})
                            # self.approved_wa_template()
                            # self.approved_mail()
                        else:
                            record.approved_user = self.env.user.name + ' ' + 'has been approved the Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
                                pass
                                # self.approver_wa_template()
                                # self.approver_mail()
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
                        for line in record.loan_installment_approver_user_ids:
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

                        matrix_line = sorted(record.loan_installment_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            # self.pay_installment()
                            record.write({'state': 'approve'})
                            # self.approved_wa_template()
                            # self.approved_mail()
                        else:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
                                pass
                                # self.approver_wa_template()
                                # self.approver_mail()
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

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.loan.installment.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'target': 'new',
        }

    def action_reject(self):
        for record in self:
            for user in record.loan_installment_approver_user_ids:
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
            record.approved_user = self.env.user.name + ' ' + 'has Rejected the Cash Advance!'
            record.write({'state': 'rejected'})
            # record.reject_mail()
            # self.rejected_wa_template()

    @api.depends('state', 'employee_id', 'approved_user_ids')
    def _compute_is_approved(self):
        current_user = self.env.user
        for rec in self:
            if current_user in rec.approved_user_ids or rec.state != 'unpaid':
                rec.is_approved = True
            else:
                rec.is_approved = False

    def book_interest(self):
        res = super(LoanInstallmentDetail, self).book_interest()
        for line in self.loan_installment_approver_user_ids:
            line.write({'approver_state': 'draft'})
        return res

class LoanInstallmentApproverUser(models.Model):
    _name = 'loan.installment.approver.user'

    loan_id = fields.Many2one('loan.installment.details', string="Loan Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'loan_installment_user_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='loan_id.state')
    # Auto follow
    # is_auto_follow_approver = fields.Boolean()
    # repetition_follow_count = fields.Integer()

    @api.depends('loan_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.loan_id.loan_installment_approver_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver:
                rec.minimum_approver = len(rec.user_ids)

class EmployeeLoanProof(models.Model):
    _name = 'employee.loan.proof'

    emp_loan_id = fields.Many2one('employee.loan.details', string="Employee Loan Id")
    name = fields.Char(string='Name')
    attachment =fields.Binary('Attachment')
    attachment_name = fields.Char('Attachment Name')
    mandatory = fields.Boolean(string='Mandatory')