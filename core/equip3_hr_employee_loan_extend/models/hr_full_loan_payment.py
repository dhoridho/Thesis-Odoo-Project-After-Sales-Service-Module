# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
import requests
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
headers = {'content-type': 'application/json'}

class HrFullLoanPayment(models.Model):
    _name = 'hr.full.loan.payment'

    def name_get(self):
        result = []
        for loan in self:
            result.append((loan.id, loan.loan_id.name))
        return result

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    loan_id = fields.Many2one('employee.loan.details', string='Loan',required=True, domain=lambda self: "[('employee_id', '=', employee_id),('state','=','disburse'),('is_computed','=',True),('loan_type.payment_method','=','cash')]")
    loan_type_id = fields.Many2one('loan.type', related='loan_id.loan_type', string='Loan Type', readonly=True)
    state = fields.Selection(
        selection=[('unpaid', 'Unpaid'),('to_approve', 'To Approve'), ('approve', 'Approved'), ('paid', 'Paid'), ('rejected', 'Rejected')], string='Status', readonly=True, copy=False, default='unpaid')
    installment_lines = fields.One2many('loan.installment.details', 'full_loan_payment_id', 'Installments', copy=False,
        domain=lambda self: "[('employee_id', '=', employee_id), ('state', '=', 'unpaid'), ('loan_id', '=', loan_id)]")
    currency_id = fields.Many2one('res.currency', string='Currency', related='loan_id.currency_id')
    principal_amount = fields.Float('Principal Amount', digits=(16, 2))
    interest_amount = fields.Float('Interest Amount', digits=(16, 2))
    emi_installment = fields.Float('EMI (Installment)', digits=(16, 2))
    #Approval Matrix
    full_loan_approver_user_ids = fields.One2many('full.loan.approver.user', 'emp_full_loan_id', string='Approver')
    approvers_ids = fields.Many2many('res.users', 'emp_full_loan_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approved_user_text = fields.Text(string="Approved User")
    approved_user = fields.Text(string="Approved User")
    job_id = fields.Many2one('hr.job', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    feedback_parent = fields.Text(string='Parent Feedback')
    # insallment line items
    can_approve_installment = fields.Boolean(compute='_compute_can_approve_installment', string="Installment Approvers")
    is_readonly = fields.Boolean(compute='_compute_readonly')
    domain_employee_ids = fields.Many2many('hr.employee', string="Employee Domain", compute='_compute_employee_ids')
    loan_repayment_method = fields.Selection(
        related='loan_id.loan_type.payment_method',
        string='Loan Repayment Method',
        store=True,
    )
    payment_date = fields.Date('Payment Date', required=True)
    is_loan_approval_matrix = fields.Boolean("Is Loan Approval Matrix", compute='_compute_is_loan_approval_matrix')
    state1 = fields.Selection(
        selection=[('unpaid', 'Unpaid'), ('to_approve', 'To Approve'), ('approve', 'Submitted'), ('paid', 'Paid'),
                   ('rejected', 'Rejected')], string='Status', default='unpaid', copy=False, store=True, compute='_compute_state1')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrFullLoanPayment, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrFullLoanPayment, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
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
        res = super(HrFullLoanPayment, self).create(vals)
        if res.loan_id and res.payment_date: 
            date_disb = res.loan_id.date_disb + relativedelta(months=1)
            if res.payment_date < date_disb:
                raise ValidationError(_('Payment Date must be greater than %s.') % (date_disb))
        return res

    def write(self, vals):
        res = super(HrFullLoanPayment, self).write(vals)
        for loan in self:
            if loan.loan_id and loan.payment_date: 
                date_disb = loan.loan_id.date_disb + relativedelta(months=1)
                if loan.payment_date < date_disb:
                    raise ValidationError(_('Payment Date must be greater than %s.') % (date_disb))
        return res
    
    @api.model
    def default_get(self, fields):
        res = super(HrFullLoanPayment, self).default_get(fields)
        employees = self.env['hr.employee'].search([('user_id', '=', self.env.uid),('company_id','=',self.env.company.id)])
        res['employee_id'] = employees.id
        return res
    
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
    
    
    
    def custom_menu(self):
            # views = [(self.env.ref('bi_employee_travel_managment.view_travel_req_tree').id, 'tree'),
        #              (self.env.ref('bi_employee_travel_managment.view_travel_req_form').id, 'form')]
        # search_view_id = self.env.ref("hr_employee_loan.view_loan_installment_filter")
        if self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_self_service') and not self.env.user.has_group('equip3_hr_employee_loan_extend.group_loan_supervisor'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Multiple Payment',
                'res_model': 'hr.full.loan.payment',
                'target': 'current',
                'view_mode': 'tree,form',
                # 'views':views,
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                # 'context': {'default_holiday_type': 'company'},
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create New Multiple Payment
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
                    'name': 'Multiple Payment',
                    'res_model': 'hr.full.loan.payment',
                    'target': 'current',
                    'view_mode': 'tree,form',
                    # 'views':views,
                    'domain': [('employee_id', 'in', employee_ids)],
                    'context': {},
                    'help': """<p class="o_view_nocontent_smiling_face">
                    Create New Multiple Payment
                    </p>""",
                    # 'search_view_id': search_view_id.id,

                }

        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Multiple Payment',
                'res_model': 'hr.full.loan.payment',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [],
                'context': {},
                'help': """<p class="o_view_nocontent_smiling_face">
                Create New Multiple Payment
                </p>""",
                # 'search_view_id': search_view_id.id,
                
            }

    def _compute_can_approve_installment(self):
        current_user = self.env.uid
        setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_approval_matrix')
        for rec in self:
            if rec.approvers_ids and current_user in rec.approvers_ids.ids:
                rec.can_approve_installment = True
            elif not setting:
                rec.can_approve_installment = True
            else:
                rec.can_approve_installment = False

    @api.onchange('employee_id')
    def onchange_employee(self):
        for loan in self:
            loan.loan_id = False

    @api.onchange('loan_id')
    def onchange_loan(self):
        for loan in self:
            loan.installment_lines = [(5,0,0)]

    @api.onchange('employee_id', 'loan_id')
    def onchange_approver_user(self):
        loan_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_approval_matrix')
        if loan_setting:
            for loan in self:
                if loan.full_loan_approver_user_ids:
                    remove = []
                    for line in loan.full_loan_approver_user_ids:
                        remove.append((2, line.id))
                    loan.full_loan_approver_user_ids = remove
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_employee_loan_extend.loan_type_approval')
                if setting == 'employee_hierarchy':
                    loan.full_loan_approver_user_ids = self.full_loan_emp_by_hierarchy(loan)
                    self.app_list_full_loan_emp_by_hierarchy()
                if setting == 'approval_matrix':
                    self.full_loan_approval_by_matrix(loan)

    def full_loan_emp_by_hierarchy(self, loan):
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

    def app_list_full_loan_emp_by_hierarchy(self):
        for loan in self:
            app_list = []
            for line in loan.full_loan_approver_user_ids:
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

    def full_loan_approval_by_matrix(self, loan):
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
            loan.full_loan_approver_user_ids = data_approvers

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
                loan.full_loan_approver_user_ids = data_approvers
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
                    loan.full_loan_approver_user_ids = data_approvers

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
                    matrix_line = sorted(loan.full_loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(loan.full_loan_approver_user_ids)
                    if app < app_level and app < a:
                        if current_user in loan.full_loan_approver_user_ids[app].user_ids:
                            loan.is_approver = True
                        else:
                            loan.is_approver = False
                    else:
                        loan.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(loan.full_loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(loan.full_loan_approver_user_ids)
                    if app < a:
                        for line in loan.full_loan_approver_user_ids[app]:
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
        sequence_matrix = [data.name for data in self.full_loan_approver_user_ids]
        sequence_approval = [data.name for data in self.full_loan_approver_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.full_loan_approver_user_ids.filtered(
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
                        for user in record.full_loan_approver_user_ids:
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
                        matrix_line = sorted(record.full_loan_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.write({'state': 'approve'})
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
                        for line in record.full_loan_approver_user_ids:
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

                        matrix_line = sorted(record.full_loan_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            record.write({'state': 'approve'})
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
        self.sync_installment_approval_matrix()

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.full.loan.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'target': 'new',
        }


    @api.onchange('installment_lines')
    def onchange_sum_line_items(self):
        total_principal = 0
        total_interest = 0
        total_emi = 0
        for rec in self:
            for line in rec.installment_lines:
                total_principal += line.principal_amt
                total_interest  += line.interest_amt
                total_emi += line.total
        rec.principal_amount = total_principal
        rec.interest_amount = total_interest
        rec.emi_installment = total_emi

    def action_confirm(self):
        loan_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.loan_approval_matrix')
        if loan_setting:
            for rec in self:
                rec.write({"state": 'to_approve'})
                for line in rec.full_loan_approver_user_ids:
                    line.write({'approver_state': 'draft'})
            self.approver_wa_template()
            self.approver_mail()
            self.sync_installment_approval_matrix()
        else:
            for record in self:
                record.write({'state': 'approve'})


    def loan_pay(self):
        for rec in self:
            rec.write({"state": 'paid'})
            for line in rec.installment_lines:
                line.pay_installment()
        self.sync_installment_approval_matrix()

    def action_rejected(self):
        for record in self:
            for user in record.full_loan_approver_user_ids:
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
            record.approved_user = self.env.user.name + ' ' + 'has been Rejected!'
            record.write({'state': 'rejected'})
            self.rejected_wa_template()
            self.reject_mail()
        self.sync_installment_approval_matrix()

    def sync_installment_approval_matrix(self):
        field_values = []
        for rec in self:
            for record in rec.full_loan_approver_user_ids:
                field_values.append((0, 0, {
                    'user_ids': [(6, 0, record.user_ids.ids)],
                    'approved_employee_ids': [(6, 0, record.approved_employee_ids.ids)],
                    'minimum_approver': record.minimum_approver,
                    'timestamp': record.timestamp,
                    'approved_time': record.approved_time,
                    'feedback': record.feedback,
                    'approver_state': record.approver_state,
                    'approval_status': record.approval_status,
                    'is_approve': record.is_approve,
                }))
            for installment in rec.installment_lines:
                if installment.loan_installment_approver_user_ids:
                    installment.loan_installment_approver_user_ids.unlink()
                installment.loan_installment_approver_user_ids = field_values

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'hr_employee_loan', 'full_loan_payment')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_employee_loan_extend', 'action_hr_full_loan_payment')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.full.loan.payment&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.full_loan_approver_user_ids:
                matrix_line = sorted(rec.full_loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.full_loan_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_employee_loan_extend',
                            'email_template_full_loan_payment_approval_request')[1]
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
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                              force_send=True)
                break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.full_loan_approver_user_ids:
                for rec in rec.full_loan_approver_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.user_ids:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_employee_loan_extend',
                                'email_template_full_loan_payment_approved')[1]
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
            if rec.full_loan_approver_user_ids:
                for rec in rec.full_loan_approver_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.user_ids:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_employee_loan_extend',
                                'email_template_full_loan_payment_reject')[1]
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
            template = self.env.ref('equip3_hr_employee_loan_extend.loan_payment_approver_wa_template')
            wa_sender = waParam()
            if template:
                if self.full_loan_approver_user_ids:
                    matrix_line = sorted(self.full_loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.full_loan_approver_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", self.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.loan_id.name)
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

                        print("============== TEST APPROVER ===========")
                        print(string_test)
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
            template = self.env.ref('equip3_hr_employee_loan_extend.loan_payment_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.full_loan_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.loan_id.name)
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)
                    if "+" in phone_num:
                        phone_num = int(phone_num.replace("+", ""))
                    if "${url}" in string_test:
                        string_test = string_test.replace("${url}", url)
                    
                    wa_sender.set_wa_string(string_test,template._name,template_id=template)
                    wa_sender.send_wa(phone_num)

                    print("================ TEST APPROVED ============")
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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_loan_extend.send_by_wa_loan')
        if send_by_wa:
            template = self.env.ref('equip3_hr_employee_loan_extend.loan_payment_rejected_wa_template')
            url = self.get_url(self)
            wa_sender = waParam()
            if template:
                if self.full_loan_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.loan_id.name)
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)
                    if "+" in phone_num:
                        phone_num = int(phone_num.replace("+", ""))
                    
                    wa_sender.set_wa_string(string_test,template._name,template_id=template)
                    wa_sender.send_wa(phone_num)

                    print("========== TEST REJECTED =========")
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
        number_of_repetitions_loan = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_employee_loan_extend.number_of_repetitions_loan'))
        full_loan_approve = self.search([('state', '=', 'to_approve')])
        for rec in full_loan_approve:
            if rec.full_loan_approver_user_ids:
                matrix_line = sorted(rec.full_loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.full_loan_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_employee_loan_extend',
                            'email_template_full_loan_payment_approval_request')[1]
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
                        count = number_of_repetitions_loan - 1
                        query_statement = """UPDATE full_loan_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE full_loan_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
        self.user_delegation_mail()
    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        full_loan_approve = self.search([('state', '=', 'to_approve')])
        for rec in full_loan_approve:
            if rec.full_loan_approver_user_ids:
                matrix_line = sorted(rec.full_loan_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.full_loan_approver_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_employee_loan_extend',
                                    'email_template_full_loan_payment_approval_request')[1]
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

class LoanInstallmentDetails(models.Model):

    _inherit = "loan.installment.details"

    full_loan_payment_id = fields.Many2one('hr.full.loan.payment')

class FullLoanApproverUser(models.Model):
    _name = 'full.loan.approver.user'

    emp_full_loan_id = fields.Many2one('hr.full.loan.payment', string="Employee Loan Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'emp_full_loan_user_ids', string="Approved user")
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
    matrix_user_ids = fields.Many2many('res.users', 'emp_full_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='emp_full_loan_id.state')

    @api.depends('emp_full_loan_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.emp_full_loan_id.full_loan_approver_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.emp_full_loan_id.state == 'unpaid':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.emp_full_loan_id.state == 'unpaid':
                rec.matrix_user_ids = rec.user_ids