# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta, date
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
import requests
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
headers = {'content-type': 'application/json'}


class EmployeeLoanCancelation(models.Model):
    _name = "employee.loan.cancelation"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = "name desc"
    _rec_name = 'name'


    @api.model
    def default_get(self, fields):
        res = super(EmployeeLoanCancelation, self).default_get(fields)
        employees = self.env['hr.employee'].search([('user_id', '=', self.env.uid),('company_id','=',self.env.company.id)])
        res['employee_id'] = employees.id
        return res
    
    
    @api.model
    def _employee_get(self):
        ids = self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1)
        if ids:
            return ids

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('employee.loan.cancelation')
        return super(EmployeeLoanCancelation, self).create(vals)

    name = fields.Char(
        string='Number',
        readonly=True,
        copy=False
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )
    loan_id = fields.Many2one(
        'employee.loan.details', string='Loan', required=True,
        domain="[('employee_id', '=', employee_id),('state', '=', 'approved')]"
    )
    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        states={'paid': [('readonly', True)], 'disburse': [('readonly', True)], 'approved': [('readonly', True)]},
        related='loan_id.department_id'
    )
    date_applied = fields.Date(
        string='Applied Date',
        required=False,
        states={'paid': [('readonly', True)], 'disburse': [('readonly', True)], 'approved': [('readonly', True)]},
        related='loan_id.date_applied'
    )
    date_approved = fields.Date(
        string='Approved Date',
        readonly=True,
        copy=False, related='loan_id.date_approved'
    )
    date_repayment = fields.Date(
        string='Repayment Date',
        readonly=False,
        states={'paid': [('readonly', True)], 'disburse': [('readonly', True)], 'approved': [('readonly', True)]},
        copy=False, related='loan_id.date_repayment'
    )
    date_disb = fields.Date(
        string='Disbursement Date',
        readonly=True,
        related='loan_id.date_disb'
    )
    loan_type = fields.Many2one(
        'loan.type',
        string='Loan Type',
        required=True,
        readonly=True, related='loan_id.loan_type'
    )
    duration = fields.Integer(
        string='Duration(Months)',
        required=True,
        readonly=True, related='loan_id.duration'
    )
    loan_policy_ids = fields.Many2many(
        'loan.policy',
        'loan_policy_cancel_rel',
        'policy_id',
        'loan_id',
        string="Active Policies",
        states={'disburse': [('readonly', True)]}, related='loan_id.loan_policy_ids'
    )
    int_payable = fields.Boolean(
        string='Is Interest Payable',
        related='loan_id.int_payable', store=True
    )
    interest_mode = fields.Selection(
        string='Interest Mode', related='loan_id.interest_mode',
        store=True,
    )
    int_rate = fields.Float(
        string='Rate',
        # multi='type',
        help='Interest rate between 0-100 in range',
        digits=(16, 2), related='loan_id.int_rate',
        store=True
    )
    principal_amount = fields.Float(
        string='Principal Amount',
        required=True,
        readonly=True, related='loan_id.principal_amount', store=True
    )
    employee_gross = fields.Float(
        string='Gross Salary',
        help='Employee Gross Salary from Payslip if payslip is not available please enter value manually.',
        required=False,
        readonly=True, related='loan_id.employee_gross'
    )
    final_total = fields.Float(
        string='Total Loan', related='loan_id.final_total',
        store=True
    )
    total_amount_paid = fields.Float(
        string='Received From Employee', related='loan_id.total_amount_paid',
        store=True
    )
    total_amount_due = fields.Float(
        help='Remaining Amount due.',
        string='Balance on Loan', related='loan_id.total_amount_due',
        store=True
    )
    total_interest_amount = fields.Float(
        string='Total Interest on Loan', related='loan_id.total_interest_amount',
        store=True
    )
    max_loan_amt = fields.Float(
        related='loan_id.max_loan_amt', store=True,
        string='Max Loan Amount'
    )
    installment_lines = fields.One2many(
        'loan.installment.details',
        'loan_id',
        'Installments',
        copy=False, related='loan_id.installment_lines'
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        readonly=True, related='loan_id.company_id', store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        readonly=True, related='loan_id.currency_id', store=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        readonly=True,
        required=True, related='loan_id.user_id', store=True
    )
    employee_loan_account = fields.Many2one(
        'account.account',
        string="Employee Account",
        readonly=False,
        states={'disburse': [('readonly', True)]}, related='loan_id.employee_loan_account', store=True
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Disburse Journal',
        help='Journal related to loan for Accounting Entries',
        required=False,
        readonly=False,
        states={'disburse': [('readonly', True)]}, related='loan_id.journal_id', store=True
    )
    journal_id1 = fields.Many2one(
        'account.journal',
        string='Repayment Board Journal',
        required=False,
        readonly=False,
        states={'close': [('readonly', True)]}, related='loan_id.journal_id1', store=True
    )
    journal_id2 = fields.Many2one(
        'account.journal',
        string='Interest Journal',
        required=False,
        readonly=False, related='loan_id.journal_id2', store=True
    )
    move_id = fields.Many2one(
        'account.move',
        string='Accounting Entry',
        readonly=True,
        help='Accounting Entry once loan has been given to employee',
        copy=False, related='loan_id.move_id', store=True
    )
    loan_proof_ids = fields.One2many(
        string='Loan Proofs', related='loan_id.loan_proof_ids'
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('to_approve', 'To Approve'),
            ('approved', 'Approved'),
            ('paid', 'Paid'),
            ('disburse', 'Disbursed'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled')],
        string='Status',
        readonly=True,
        copy=False,
        default='draft',
        tracking=True
    )
    notes = fields.Text(
        string='Note')
    loan_approver_user_ids = fields.One2many('loan.approver.cancel', 'emp_loan_id', string='Approver')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    approvers_ids = fields.Many2many('res.users', 'emp_loan_cancell_approvers_rel', string='Approvers List')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id')
    feedback_parent = fields.Text(string='Parent Feedback')
    is_readonly = fields.Boolean(compute='_compute_readonly')
    domain_employee_ids = fields.Many2many('hr.employee', string="Employee Domain", compute='_compute_employee_ids')
    is_loan_approval_matrix = fields.Boolean("Is Loan Approval Matrix", compute='_compute_is_loan_approval_matrix')
    state1 = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('to_approve', 'To Approve'),
            ('approved', 'Submitted'),
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

        result = super(EmployeeLoanCancelation, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeLoanCancelation, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_is_loan_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_approval_matrix')
            rec.is_loan_approval_matrix = setting
    
    def custom_menu(self):
        views = [(self.env.ref('equip3_hr_employee_loan_extend.view_loan_cancel_tree').id, 'tree'),
                    (self.env.ref('equip3_hr_employee_loan_extend.view_loan_cancel_form').id, 'form')]
        # search_view_id = self.env.ref("hr_employee_loan.view_loan_filter")
        if self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_self_service') and not self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_supervisor'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Loan Cancellation',
                'res_model': 'employee.loan.cancelation',
                'target': 'current',
                'view_mode': 'tree,form',
                'views':views,
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                # 'context': {'default_holiday_type': 'company'},
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create New Loan Cancellation
                </p>""",
                'context':{},
                # 'search_view_id': search_view_id.id,

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
                    'name': 'Loan Cancellation',
                    'res_model': 'employee.loan.cancelation',
                    'target': 'current',
                    'view_mode': 'tree,form',
                    'views':views,
                    'domain': [('employee_id', 'in', employee_ids)],
                    'context': {},
                    'help': """<p class="o_view_nocontent_smiling_face">
                    Create New Loan Cancellation
                    </p>""",
                    # 'search_view_id': search_view_id.id,

                }

        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Loan Cancellation',
                'res_model': 'employee.loan.cancelation',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [],
                'context': {},
                'views':views,
                'help': """<p class="o_view_nocontent_smiling_face">
                Create New Loan Cancellation
                </p>""",
                # 'search_view_id': search_view_id.id,
              
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

    def action_confirm(self):
        loan_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_approval_matrix')
        if loan_setting:
            for rec in self:
                current_date = date.today()
                if rec.date_disb:
                    if rec.date_disb <= current_date:
                        raise ValidationError("Please select a loan with a disbursement date more than the current date")
                rec.state = 'to_approve'
                for line in rec.loan_approver_user_ids:
                    line.write({'approver_state': 'draft'})
            self.approver_wa_template()
            self.approver_mail()
        else:
            for rec in self:
                date_approved = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
                rec.write({'state': 'approved',
                           'date_approved': date_approved})
                rec.loan_id.state = 'cancel'

    @api.onchange('employee_id', 'loan_type')
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
                            record.write({'state': 'approved',
                                          'date_approved': date_approved})
                            record.loan_id.state = 'cancel'
                            self.approved_wa_template()
                            self.approved_mail()
                        else:
                            record.approved_user = self.env.user.name + ' ' + 'has been approved the Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
                                self.approver_wa_template()
                                self.approver_mail()
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
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            record.write({'state': 'approved',
                                          'date_approved': date_approved})
                            record.loan_id.state = 'cancel'
                            self.approved_wa_template()
                            self.approved_mail()
                        else:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
                                self.approver_wa_template()
                                self.approver_mail()
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
            record.approved_user = self.env.user.name + ' ' + 'has been Rejected!'
            record.write({'state': 'rejected'})
            self.rejected_wa_template()
            self.reject_mail()

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.loan.cancel.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':True},
            'name': "Confirmation Message",
            'target': 'new',
        }
        
    def wizard_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.loan.cancel.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':False,
                       'default_is_reject':True},
            'name': "Confirmation Message",
            'target': 'new',
        }

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_employee_loan_extend', 'loan_cancel_manager')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_employee_loan_extend', 'action_loan_cancelation_manager')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=employee.loan.cancelation&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.send_by_wa_loan')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(self)
        if send_by_wa:
            template = self.env.ref('equip3_hr_employee_loan_extend.loan_cancel_approver_wa_template')
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
            template = self.env.ref('equip3_hr_employee_loan_extend.loan_cancel_approved_wa_template')
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
            template = self.env.ref('equip3_hr_employee_loan_extend.loan_cancel_rejected_wa_template')
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
                            'email_template_loan_cancelation_approval_request')[1]
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
                                'email_template_loan_cancelation_approved')[1]
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
                                'email_template_loan_cancelation_reject')[1]
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

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_loan = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_employee_loan_extend.number_of_repetitions_loan'))
        loan_cancel_approve = self.search([('state', '=', 'to_approve')])
        for rec in loan_cancel_approve:
            if rec.loan_approver_user_ids:
                matrix_line = sorted(rec.loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.loan_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_employee_loan_extend',
                            'email_template_loan_cancelation_approval_request')[1]
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
                        query_statement = """UPDATE loan_approver_cancel set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE loan_approver_cancel set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        loan_cancel_approve = self.search([('state', '=', 'to_approve')])
        for rec in loan_cancel_approve:
            if rec.loan_approver_user_ids:
                matrix_line = sorted(rec.loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.loan_approver_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_employee_loan_extend',
                                    'email_template_loan_cancelation_approval_request')[1]
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

class LoanApproverCancelUser(models.Model):
    _name = 'loan.approver.cancel'

    emp_loan_id = fields.Many2one('employee.loan.cancelation', string="Employee Loan Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'emp_loan_cancel_user_ids', string="Approved user")
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
    matrix_user_ids = fields.Many2many('res.users', 'loan_cancel_max_user_ids', string="Matrix user")
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