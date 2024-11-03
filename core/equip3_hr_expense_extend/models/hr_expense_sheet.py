# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from datetime import date, timedelta
from json import dumps
from odoo.exceptions import UserError, ValidationError

import json
from datetime import datetime, timedelta
from pytz import timezone
from lxml import etree
import requests
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
headers = {'content-type': 'application/json'}


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    name = fields.Char(states={'draft': [('readonly', False)]})
    date = fields.Date(states={'draft': [('readonly', False)]})
    product_id = fields.Many2one(states={'draft': [('readonly', False)]},domain="[('id','in',allowed_product_ids)]")
    product_uom_id = fields.Many2one(states={'draft': [('readonly', False)]})
    unit_amount = fields.Float(states={'draft': [('readonly', False)]})
    quantity = fields.Float(states={'draft': [('readonly', False)]})
    company_id = fields.Many2one(states={'draft': [('readonly', False)]})
    description = fields.Text(states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('reported', 'Submitted'),
        ('approved', 'Approved'),
        ('done', 'Paid'),
        ('refused', 'Rejected')
    ], compute='_compute_state', string='Status', copy=False, index=True, readonly=True, store=True, default='draft', help="Status of the expense.")
    cycle_code_id = fields.Many2one('hr.expense.cycle.line', string="Cycle Code")
    allowed_product_ids = fields.Many2many('product.product','allowed_product_hr_expense_rel', string="Allowed Product", compute='_compute_allowed_product', store=True)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrExpense, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrExpense, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def create(self, vals):
        if self.env.context.get('default_employee_id'):
            emp_obj = self.env['hr.employee'].browse(self.env.context.get('default_employee_id'))
            if emp_obj and not emp_obj.sudo().address_home_id:
                raise ValidationError(_("No Home Address found for the employee %s, please configure one.") % (emp_obj.name))
        if not vals.get('cycle_code_id'):
            raise ValidationError("There is no cycle for the selected expense date")
        return super(HrExpense, self).create(vals)

    def write(self, vals):
        res = super(HrExpense, self).write(vals)
        for rec in self:
            if not rec.cycle_code_id:
                raise ValidationError("There is no cycle for the selected expense date")
        return res
    
    def unlink(self):
        for expense in self:
            if expense.state in ['done', 'approved']:
                raise UserError(_('You cannot delete a Expense Report to Approve.'))
        return super(HrExpense, self).unlink()

    def action_submit_expenses(self):
        sheet = self._create_sheet_from_expenses()
        sheet.onchange_amount_sum()
        sheet.onchange_approver_user()
        sheet.expense_approver_user_ids.update_minimum_app()
        sheet.action_submit_sheet()
        return {
            'name': _('New Expense Report'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'target': 'current',
            'res_id': sheet.id,
        }

    @api.depends('date', 'total_amount', 'company_currency_id')
    def _compute_total_amount_company(self):
        for expense in self:
            amount = 0
            if expense.company_currency_id:
                date_expense = expense.date
                amount = expense.company_currency_id._convert(
                    expense.total_amount, expense.currency_id,
                    expense.company_id, date_expense or fields.Date.today())
            expense.total_amount_company = amount

    @api.onchange('date')
    def onchange_date(self):
        for rec in self:
            if rec.date:
                exp_cycle_line = self.env["hr.expense.cycle.line"].search([
                    ("cycle_start","<=",rec.date),("cycle_end",">=",rec.date)],
                    limit=1)
                if exp_cycle_line:
                    rec.cycle_code_id = exp_cycle_line.id
                else:
                    rec.cycle_code_id = False
            else:
                rec.cycle_code_id = False
    
    @api.depends('employee_id')
    def _compute_allowed_product(self):
        for rec in self:
            if rec.employee_id and rec.employee_id.employee_expense_line:
                allowed_product = []
                for line in rec.employee_id.employee_expense_line:
                    allowed_product.append(line.product_id.id)
                rec.allowed_product_ids = allowed_product
            else:
                rec.allowed_product_ids = False
    
    @api.depends('employee_id')
    def _compute_is_editable(self):
        is_account_manager = self.env.user.has_group('account.group_account_user') or self.env.user.has_group('account.group_account_manager')
        for expense in self:
            if expense.state == 'draft' or expense.sheet_id.state in ['draft']:
                expense.is_editable = True
            elif expense.sheet_id.state == 'approve':
                expense.is_editable = is_account_manager
            else:
                expense.is_editable = False

    @api.depends('employee_id')
    def _compute_is_ref_editable(self):
        is_account_manager = self.env.user.has_group('account.group_account_user') or self.env.user.has_group('account.group_account_manager')
        for expense in self:
            if expense.state == 'draft' or expense.sheet_id.state in ['draft']:
                expense.is_ref_editable = True
            else:
                expense.is_ref_editable = is_account_manager

class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def unlink(self):
        for expense in self:
            if expense.state in ['done', 'submit', 'approve']:
                raise UserError(_('You cannot delete a Expense.'))
        return super(HrExpenseSheet, self).unlink()

    @api.model
    def create(self, vals):
        sequence_no = self.env['ir.sequence'].next_by_code('hr.expense.sheet')
        vals.update({'seq_name': sequence_no})
        result = super(HrExpenseSheet, self).create(vals)
        return result

    def name_get(self):
        return [(exp.id, exp.seq_name) for exp in self]

    seq_name = fields.Char('Name', default='New', copy=False)
    name = fields.Char('Expense Summary', required=True, tracking=True)
    expense_advance = fields.Boolean(string='Expense Advance', default=False)
    cash_advance_number_ids = fields.Many2many('vendor.deposit', string='Cash Advance Number',
                                               domain=lambda
                                                   self: "[('employee_id', '=', employee_id), ('state', '=', 'post'), ('is_cash_advance', '=', 'True')]")
    expense_payment_widget = fields.Text(string="Expense Payment Widget", compute="_get_payment_info_JSON")
    cash_advance_amount = fields.Monetary(string="Cash Advance Amount", tracking=True)
    exp_difference = fields.Float('Total difference')
    is_hide = fields.Boolean(string='Reconcile Button Visible', default=False)
    line_ids = fields.Many2many('account.move.line', string='Account Line', compute='_compute_acc_line')
    register_button_hide = fields.Boolean(string='Register Button Visible', default=False,
                                          compute='_compute_register_button_hide')
    expense_approver_user_ids = fields.One2many('expense.approver.user', 'expense_id', string='Approver')
    approvers_ids = fields.Many2many('res.users', 'exp_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    amount_sum = fields.Float("Sum of total from line item", )
    feedback_parent = fields.Text(string='Parent Feedback')
    expense_cycle = fields.Char(string='Expense Cycle')
    reimbursement_date = fields.Date(string='Reimbursement Date')
    expense_reminder_before_days = fields.Integer(compute='compute_reminder_details')
    expense_choose_color_reminder = fields.Selection(
        [('red', 'Red'), ('green', 'Green'), ('blue', 'Blue'), ('purple', 'Purple'), ('yellow', 'Yellow'),
         ('white', 'White')],
        compute='compute_reminder_details')
    is_self_service = fields.Boolean(compute='_compute_is_self_service')
    is_read_only_manager = fields.Boolean(compute='_compute_is_read_only_manager')
    employee_domain_ids = fields.Many2many('hr.employee',compute='_compute_employee_domain')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('post', 'Posted'),
        ('done', 'Paid'),
        ('cancel', 'Rejected')
    ], string='Status', index=True, readonly=True, tracking=True, copy=False, default='draft', required=True, help='Expense Report State')
    state1 = fields.Selection([
            ('draft', 'Draft'),
            ('submit', 'To Submit'),
            ('approve', 'Submitted'),
            ('post', 'Posted'),
            ('done', 'Paid'),
            ('cancel', 'Rejected')
        ],
        tracking=False,
        default='draft',
        copy=False,
        store=True,
        string='Status',
        compute='_compute_state1'
    )
    is_expense_approval_matrix = fields.Boolean(
        string='Is Expense Approval Matrix',
        compute="_compute_is_expense_approval_matrix"
    )    
    
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrExpenseSheet, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrExpenseSheet, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def _compute_is_expense_approval_matrix(self):
        for line in self:
            expense_approval_matrix_setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_expense_extend.expense_approval_matrix'
            )
            line.is_expense_approval_matrix = expense_approval_matrix_setting
    

    @api.depends('state')
    def _compute_state1(self):
        for line in self:
            line.state1 = line.state


    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrExpenseSheet, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.context.get('is_to_Approve'):
                root = etree.fromstring(res['arch'])
                root.set('create', 'false')
                root.set('edit', 'false')
                root.set('delete', 'false')
                res['arch'] = etree.tostring(root)
        return res
    
    
    @api.depends('employee_id')
    def _compute_employee_domain(self):
        for record in self:
            if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_team_approver') and not self.env.user.has_group('hr_expense.group_hr_expense_user'):
                my_employee = self.env['hr.employee'].sudo().search([('user_id','=',self.env.user.id),('company_id','in',self.env.company.ids)])
                employee_ids = []
                if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
                record.employee_domain_ids = employee_ids
            else:
                employee = self.env['hr.employee'].sudo().search([('company_id','in',self.env.company.ids)])
                employee_ids = []
                if employee:
                    for record_employee in employee:
                        employee_ids.append(record_employee.id)
                record.employee_domain_ids = employee_ids
            
    
    @api.depends('employee_id')
    def _compute_is_self_service(self):
        for record in self:
            if  self.env.user.has_group('hr_expense.group_hr_expense_team_approver') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_team_approver'):
                record.is_self_service =  True
            else:
                record.is_self_service =  False
                
    @api.depends('employee_id')
    def _compute_is_read_only_manager(self):
        for record in self:
            if  self.env.user.has_group('hr_expense.group_hr_expense_team_approver') and not self.env.user.has_group('hr_expense.group_hr_expense_user') or self.env.user.has_group('equip3_hr_employee_access_right_setting.group_team_approver') and not self.env.user.has_group('hr_expense.group_hr_expense_user'):
                record.is_read_only_manager =  True
            else:
                record.is_read_only_manager =  False
            

    @api.onchange('expense_line_ids', 'state')
    def onchange_amount_sum(self):
        for rec in self:
            total_amt_sum = 0
            for line in rec.expense_line_ids:
                total_amt_sum += line.total_amount
        rec.amount_sum = total_amt_sum
        # self.onchange_approver_user()
        self.get_expense_date()

    @api.onchange('employee_id', 'expense_line_ids', 'amount_sum')
    def onchange_approver_user(self):
        for expense in self:
            if expense.expense_approver_user_ids:
                remove = []
                for line in expense.expense_approver_user_ids:
                    remove.append((2, line.id))
                expense.expense_approver_user_ids = remove
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_expense_extend.expense_type_approval')
            if setting == 'employee_hierarchy':
                expense.expense_approver_user_ids = self.expense_emp_by_hierarchy(expense)
                # self.emp_hierarchy_approver()
                self.app_list_expense_emp_by_hierarchy()
            if setting == 'approval_matrix':
                self.expense_approval_by_matrix(expense)

    def expense_emp_by_hierarchy(self, expense):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(expense, expense.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, expense, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_expense_extend.expense_level')
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
                self.get_manager(expense, employee_manager['parent_id'], data, approval_ids, seq)
                break

        return approval_ids

    def get_manager_hierarchy(self, expense, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(expense, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def app_list_expense_emp_by_hierarchy(self):
        for expense in self:
            app_list = []
            for line in expense.expense_approver_user_ids:
                app_list.append(line.user_ids.id)
            expense.approvers_ids = app_list

    def expense_approval_by_matrix(self, expense):
        app_list = []
        approval_matrix = self.env['hr.expense.approval.matrix'].search(
            [('apply_to', '=', 'by_employee'), ('maximum_amount', '>=', expense.amount_sum),
             ('minimum_amount', '<=', expense.amount_sum)])
        matrix = approval_matrix.filtered(lambda line: expense.employee_id.id in line.employee_ids.ids)
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
                    approvers = self.get_manager_hierarchy(expense, expense.employee_id, data, manager_ids, seq, line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            expense.approvers_ids = app_list
            expense.expense_approver_user_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.expense.approval.matrix'].search(
                [('apply_to', '=', 'by_job_position'), ('maximum_amount', '>=', expense.amount_sum),
                 ('minimum_amount', '<=', expense.amount_sum)])
            matrix = approval_matrix.filtered(lambda line: expense.job_id.id in line.job_ids.ids)
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
                        approvers = self.get_manager_hierarchy(expense, expense.employee_id, data, manager_ids, seq, line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                expense.approvers_ids = app_list
                expense.expense_approver_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.expense.approval.matrix'].search(
                    [('apply_to', '=', 'by_department'), ('maximum_amount', '>=', expense.amount_sum),
                     ('minimum_amount', '<=', expense.amount_sum)])
                matrix = approval_matrix.filtered(lambda line: expense.department_id.id in line.deparment_ids.ids)
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
                            approvers = self.get_manager_hierarchy(expense, expense.employee_id, data, manager_ids, seq, line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    expense.approvers_ids = app_list
                    expense.expense_approver_user_ids = data_approvers

    @api.depends('state', 'employee_id', 'total_amount')
    def _compute_can_approve(self):
        for expense in self:
            if expense.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_expense_extend.expense_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_expense_extend.expense_level')
                app_level = int(setting_level)
                current_user = expense.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(expense.expense_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(expense.expense_approver_user_ids)
                    if app < app_level and app < a:
                        if current_user in expense.expense_approver_user_ids[app].user_ids:
                            expense.is_approver = True
                        else:
                            expense.is_approver = False
                    else:
                        expense.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(expense.expense_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(expense.expense_approver_user_ids)
                    if app < a:
                        for line in expense.expense_approver_user_ids[app]:
                            if current_user in line.user_ids:
                                expense.is_approver = True
                            else:
                                expense.is_approver = False
                    else:
                        expense.is_approver = False

                else:
                    expense.is_approver = False
            else:
                expense.is_approver = False

    def approve_expense_sheets(self):
        if not self.user_has_groups('hr_expense.group_hr_expense_team_approver'):
            raise UserError(_("Only Managers and HR Officers can approve expenses"))
        elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
            current_managers = self.employee_id.sudo().expense_manager_id | self.employee_id.sudo().parent_id.user_id | self.employee_id.sudo().department_id.manager_id.user_id

            if self.employee_id.user_id == self.env.user:
                raise UserError(_("You cannot approve your own expenses"))

            if not self.env.user in current_managers and not self.user_has_groups(
                    'hr_expense.group_hr_expense_user') and self.employee_id.sudo().expense_manager_id != self.env.user:
                raise UserError(_("You can only approve your department expenses"))

        responsible_id = self.user_id.id or self.env.user.id
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('There are no expense reports to approve.'),
                'type': 'warning',
                'sticky': False,  # True/False will display for few seconds if false
            },
        }
        sheet_to_approve = self.filtered(lambda s: s.state in ['submit', 'draft'])
        if sheet_to_approve:
            notification['params'].update({
                'title': _('The expense reports were successfully approved.'),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            })
            # sheet_to_approve.write({'state': 'approve', 'user_id': responsible_id})
            self.approve_expense_sheets_by_list()
        # self.activity_update()
        return notification

    def approve_expense_sheets_by_list(self):
        sequence_matrix = [data.name for data in self.expense_approver_user_ids]
        sequence_approval = [data.name for data in self.expense_approver_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.expense_approver_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        for record in self:
            current_user = self.env.uid
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_expense_extend.expense_type_approval')
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            if setting == 'employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.expense_approver_user_ids:
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
                        matrix_line = sorted(record.expense_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.write({'state': 'approve', 'user_id': self.user_id.id or self.env.user.id})
                            record.approved_mail()
                            self.approved_wa_template()
                        else:
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
                        for line in record.expense_approver_user_ids:
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

                        matrix_line = sorted(record.expense_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            record.write({'state': 'approve', 'user_id': self.user_id.id or self.env.user.id})
                            record.approved_mail()
                            self.approved_wa_template()
                        else:
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

    def refuse_sheet(self, reason):
        if not self.user_has_groups('hr_expense.group_hr_expense_team_approver'):
            raise UserError(_("Only Managers and HR Officers can approve expenses"))
        elif not self.user_has_groups('hr_expense.group_hr_expense_manager'):
            current_managers = self.employee_id.sudo().expense_manager_id | self.employee_id.sudo().parent_id.user_id | self.employee_id.sudo().department_id.manager_id.user_id

            if self.employee_id.sudo().user_id == self.env.user:
                raise UserError(_("You cannot refuse your own expenses"))

            if not self.env.user in current_managers and not self.user_has_groups(
                    'hr_expense.group_hr_expense_user') and self.employee_id.sudo().expense_manager_id != self.env.user:
                raise UserError(_("You can only refuse your department expenses"))

        self.expense_refuse_sheet()
        # for sheet in self:
        #     sheet.message_post_with_view('hr_expense.hr_expense_template_refuse_reason',
        #                                  values={'reason': reason, 'is_sheet': True, 'name': sheet.name})
        # self.activity_update()

    def expense_refuse_sheet(self):
        for record in self:
            for user in record.expense_approver_user_ids:
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
            record.write({'state': 'cancel'})
            record.reject_mail()
            self.rejected_wa_template()

    def _compute_register_button_hide(self):
        for rec in self:
            if rec.is_hide and rec.amount_residual != 0:
                rec.register_button_hide = True
            else:
                rec.register_button_hide = False

    def get_ca_remaining_amount(self):
        for rec in self:
            total_amt = 0
            for line in rec.cash_advance_number_ids:
                total_amt += line.remaining_amount
        rec.cash_advance_amount = total_amt

    def action_submit_sheet(self):
        expense_approval_matrix_setting = self.env['ir.config_parameter'].sudo().get_param(
            'equip3_hr_expense_extend.expense_approval_matrix'
        )
        for rec in self:
            if len(rec.expense_line_ids) == 0:
                raise ValidationError("Can’t submit new expense because the expense line has not been filled")
            for prod_line in rec.expense_line_ids:
                exp_cycle_line = prod_line.cycle_code_id
                if exp_cycle_line:
                    product_limit = 0
                    if prod_line.employee_id and prod_line.employee_id.employee_expense_line:
                        for line in prod_line.employee_id.employee_expense_line:
                            if line.product_id == prod_line.product_id:
                                product_limit = line.limit
                    if product_limit == 0:
                        raise ValidationError(_("Please set Expense Limit for %s", prod_line.product_id.name))
                    akum_amount_before = 0
                    akum_roduct_filter = sum(rec.expense_line_ids.filtered(lambda r: r.id != prod_line.id and r.product_id == prod_line.product_id and r.cycle_code_id == prod_line.cycle_code_id).mapped('total_amount'))
                    akum_amount = prod_line.total_amount + akum_roduct_filter
                    expense_obj = self.env["hr.expense"].search([("id","!=",prod_line.id),("employee_id","=",prod_line.employee_id.id),("product_id","=",prod_line.product_id.id),("cycle_code_id","=",prod_line.cycle_code_id.id),('state','not in',['draft','refused'])])
                    for expense_line in expense_obj:
                        akum_amount_before += expense_line.total_amount
                        akum_amount += expense_line.total_amount
                    remaining_limit = product_limit - akum_amount_before
                    remaining_limit_with_separator = (f"{remaining_limit:,}")
                    if akum_amount > product_limit:
                        raise ValidationError(
                            _("Your limit for spending on this product has been reached. Remaining limit for %s in %s cycle = %s") %
                                (prod_line.product_id.name,prod_line.cycle_code_id.code,remaining_limit_with_separator))
            rec.exp_difference = rec.total_amount
            if expense_approval_matrix_setting:
                rec.write({'state': 'submit'})   
            else: 
                rec.write({'state': 'approve'})
            rec.onchange_amount_sum()
            # rec.activity_update()
            rec.approver_mail()
            rec.approver_wa_template()
            for line in rec.expense_approver_user_ids:
                line.write({'approver_state': 'draft'})

    def action_sheet_move_create(self):
        """Inheriting Post journal entries."""
        super(HrExpenseSheet, self).action_sheet_move_create()
        return self.reconcile_cash_advance()

    def reconcile_cash_advance(self):
        for rec in self:
            rec.is_hide = True
            for cash in rec.cash_advance_number_ids:
                cash.expense_ids = [(4, rec.id)]
                catch_before_update = cash.remaining_amount
                if rec.exp_difference > 0:
                    rec.exp_difference = (cash.remaining_amount - rec.exp_difference)
                    if rec.exp_difference <= 0:
                        cash.update({'remaining_amount': 0,
                                     'state': 'reconciled'})
                    else:
                        cash.update({'remaining_amount': rec.exp_difference,
                                     })
                elif rec.exp_difference < 0:
                    if rec.exp_difference < 0:
                        rec.exp_difference = (cash.remaining_amount + rec.exp_difference)
                        if rec.exp_difference <= 0:
                            cash.update({'remaining_amount': 0,
                                         'state': 'reconciled'})
                        else:
                            cash.update({'remaining_amount': rec.exp_difference,
                                         })
                # second condition: already cash advance is reconciled and made remaining amount != 0 in cash advance
                pay_2 = (catch_before_update - cash.remaining_amount)
                if pay_2 != 0 and cash.is_reconciled:
                    payments = self.env['account.payment.register'].with_context(active_model='account.move',
                                                                                 active_ids=self.account_move_id.ids).create(
                        {
                            'amount': pay_2,
                            'group_payment': True,
                            'payment_difference_handling': 'open',
                            'currency_id': rec.currency_id.id,
                            'payment_method_id': 2,
                        })._create_payments()
                    store_pay = payments.move_id.payment_id
                    payments.move_id.button_draft()
                    payments.move_id.payment_id = False
                    for line in payments.move_id.line_ids:
                        if line.debit == 0:
                            line.write({
                                'account_id': cash.deposit_account_id.id
                            })
                    payments.move_id.action_post()
                    payments.move_id.reconcile_line_order()
                    payments.move_id.payment_id = store_pay
                    payments.move_id.button_draft()
                    payments.move_id.action_post()
                    cash.update({'account_move_ids': [(4, payments.move_id.id)],
                                 })
                # Third condition: already cash advance is reconciled and made remaining amount = 0 in cash advance
                if pay_2 == 0 and cash.is_reconciled:
                    payments = self.env['account.payment.register'].with_context(active_model='account.move',
                                                                                 active_ids=self.account_move_id.ids).create(
                        {
                            'amount': catch_before_update,
                            'group_payment': True,
                            'payment_difference_handling': 'open',
                            'currency_id': rec.currency_id.id,
                            'payment_method_id': 2,
                        })._create_payments()
                    store_pay = payments.move_id.payment_id
                    payments.move_id.button_draft()
                    payments.move_id.payment_id = False
                    for line in payments.move_id.line_ids:
                        if line.debit == 0:
                            line.write({
                                'account_id': cash.deposit_account_id.id
                            })
                    payments.move_id.action_post()
                    payments.move_id.reconcile_line_order()
                    payments.move_id.payment_id = store_pay
                    payments.move_id.button_draft()
                    payments.move_id.action_post()
                    cash.update({'account_move_ids': [(4, payments.move_id.id)],
                                 })

                # first condition: new cash advance without reconciled
                pay = (cash.amount - cash.remaining_amount)
                if pay != 0 and not cash.is_reconciled:
                    payments = self.env['account.payment.register'].with_context(active_model='account.move',
                                                                                 active_ids=self.account_move_id.ids).create(
                        {
                            'amount': pay,
                            'group_payment': True,
                            'payment_difference_handling': 'open',
                            'currency_id': rec.currency_id.id,
                            'payment_method_id': 2,
                        })._create_payments()
                    store_pay = payments.move_id.payment_id
                    payments.move_id.button_draft()
                    payments.move_id.payment_id = False
                    for line in payments.move_id.line_ids:
                        if line.debit == 0:
                            line.write({
                                'account_id': cash.deposit_account_id.id
                            })
                    payments.move_id.action_post()
                    payments.move_id.reconcile_line_order()
                    payments.move_id.payment_id = store_pay
                    payments.move_id.button_draft()
                    payments.move_id.action_post()
                    cash.update({'account_move_ids': [(4, payments.move_id.id)],
                                 'is_reconciled': 'True',
                                 })

    def _compute_acc_line(self):
        for rec in self:
            if rec.account_move_id and rec.account_move_id.line_ids:
                for acc in rec.account_move_id.line_ids:
                    rec.line_ids = acc._reconciled_lines()
            else:
                rec.line_ids = False

    def _get_payment_info_JSON(self):
        self.expense_payment_widget = json.dumps(False)
        if self.account_move_id and self.line_ids:
            info = {'title': _('Payment'), 'content': []}
            for acc_move_line in self.line_ids:
                for payment in self.env['account.payment'].search([('move_id', '=', acc_move_line.move_id.id)]):
                    payment_ref = payment.move_id.name
                    if payment.move_id.ref:
                        payment_ref += ' (' + payment.move_id.ref + ')'
                    info['content'].append({
                        'name': payment.name,
                        'journal_name': payment.journal_id.name,
                        'amount': payment.amount,
                        'currency': payment.currency_id.symbol,
                        'digits': [69, payment.currency_id.decimal_places],
                        'position': payment.currency_id.position,
                        'date': str(payment.date),
                        'account_payment_id': payment.id,
                        'move_id': payment.move_id.id,
                        'ref': payment_ref,
                    })
            self.expense_payment_widget = json.dumps(info)

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.expense.sheet.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'target': 'new',
        }

    def get_expense_date(self):
        for record in self:
            # hr_expense_rec = self.env['hr.expense'].search([('sheet_id', '=', record.id)], order="id desc", limit=1)
            if record.create_date:
                expense_date = record.create_date
                expense_year = expense_date.strftime("%Y")
                expense_month_year = expense_date.strftime("%m/%Y")
                hr_expense_cycle_rec = self.env['hr.expense.cycle'].search([('name', '=', expense_year)],
                                                                           limit=1)
                if hr_expense_cycle_rec:
                    hr_expense_cycle_line_rec = self.env['hr.expense.cycle.line'].search(
                        [('year_id', '=', hr_expense_cycle_rec.id), ('code', '=', expense_month_year)], limit=1)
                    if hr_expense_cycle_line_rec:
                        record.expense_cycle = hr_expense_cycle_line_rec.code
                        record.reimbursement_date = hr_expense_cycle_line_rec.reimbursement_date
            else:
                record.expense_cycle = False
                record.reimbursement_date = False

    def compute_reminder_details(self):
        for rec in self:
            rec.expense_reminder_before_days = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_expense_extend.expense_reminder_before_days')
            bg_color = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_expense_extend.expense_choose_color_reminder')
            if rec.reimbursement_date and rec.state in ('approve', 'post'):
                rei_date = datetime.strptime(str(rec.reimbursement_date), '%Y-%m-%d')
                rei_before_days = timedelta(rec.expense_reminder_before_days)
                a = rei_date - datetime.now()
                b = timedelta(days=-1)
                if b <= a and a <= rei_before_days:
                    rec.expense_choose_color_reminder = bg_color
                else:
                    rec.expense_choose_color_reminder = 'white'
            else:
                rec.expense_choose_color_reminder = 'white'

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'hr_expense', 'menu_hr_expense_sheet_all_to_approve')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'hr_expense', 'action_hr_expense_sheet_all_to_approve')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.expense.sheet&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.expense_approver_user_ids:
                matrix_line = sorted(rec.expense_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.expense_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_expense_extend',
                            'email_template_application_for_expense_approval')[1]
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
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,force_send=True)
                break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.expense_approver_user_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_expense_extend',
                        'email_template_approval_expense_request')[1]
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
                self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id, force_send=True)
            break

    def reject_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.expense_approver_user_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_expense_extend',
                        'email_template_rejection_of_expense_request')[1]
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
                self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)
            break

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_expense_extend.send_by_wa_expense')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(self)
        wa_sender = waParam()
        if send_by_wa:
            template = self.env.ref('equip3_hr_expense_extend.expense_approver_wa_template')
            if template:
                if self.expense_approver_user_ids:
                    matrix_line = sorted(self.expense_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.expense_approver_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", self.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.seq_name)
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${exp_name}" in string_test:
                            string_test = string_test.replace("${exp_name}", self.name)
                        if "${br}" in string_test:
                            string_test = string_test.replace("${br}", f"\n")
                        if "${url}" in string_test:
                            string_test = string_test.replace("${url}", url)
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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_expense_extend.send_by_wa_expense')
        if send_by_wa:
            template = self.env.ref('equip3_hr_expense_extend.expense_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.expense_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.seq_name)
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)
                    if "+" in phone_num:
                        phone_num = int(phone_num.replace("+", ""))
                    if "${url}" in string_test:
                        string_test = string_test.replace("${url}", url)
                    
                    wa_sender.set_wa_string(string_test,template._name,template_id=template)
                    wa_sender.send_wa(phone_num)

                    print("============ TEST =============")
                    print("////////", string_test)
                    
                    # param = {'body': string_test, 'phone': phone_num}
                    # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                    # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                    
                    # try:
                    #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,
                    #                                    headers=headers, verify=True)
                    # except ConnectionError:
                    #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def rejected_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_expense_extend.send_by_wa_expense')
        if send_by_wa:
            template = self.env.ref('equip3_hr_expense_extend.expense_rejected_wa_template')
            url = self.get_url(self)
            wa_sender = waParam()
            if template:
                if self.expense_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${name}" in string_test:
                        string_test = string_test.replace("${name}", self.seq_name)
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

    def _track_subtype(self, init_values):
        self.ensure_one()
        # if 'state' in init_values and self.state == 'approve':
        #     return self.env.ref('hr_expense.mt_expense_approved')
        # elif 'state' in init_values and self.state == 'cancel':
        #     return self.env.ref('hr_expense.mt_expense_refused')
        # elif 'state' in init_values and self.state == 'done':
        #     return self.env.ref('hr_expense.mt_expense_paid')
        # return super(HrExpenseSheet, self)._track_subtype(init_values)

    def get_auto_follow_up_approver_wa_template(self, rec):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_expense_extend.send_by_wa_expense')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(rec)
        if send_by_wa:
            wa_sender = waParam()
            template = self.env.ref('equip3_hr_expense_extend.expense_approver_wa_template')
            if template:
                if rec.expense_approver_user_ids:
                    matrix_line = sorted(rec.expense_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = rec.expense_approver_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", rec.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", rec.seq_name)
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${exp_name}" in string_test:
                            string_test = string_test.replace("${exp_name}", rec.name)
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

    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repititions_expense = int(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_expense_extend.number_of_repititions_expense'))
        expense_submit = self.search([('state', '=', 'submit')])
        for rec in expense_submit:
            if rec.expense_approver_user_ids:
                matrix_line = sorted(rec.expense_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.expense_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_expense_extend',
                            'email_template_application_for_expense_approval')[1]
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
                        count = number_of_repititions_expense - 1
                        query_statement = """UPDATE expense_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count,approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,force_send=True)
                        self.get_auto_follow_up_approver_wa_template(rec)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE expense_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count,approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,force_send=True)
                            self.get_auto_follow_up_approver_wa_template(rec)
        self.user_delegation_mail()

    def set_to_paid(self):
        for rec in self:
            if rec.amount_residual == 0:
                self.write({'state': 'done'})

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        expense_submit = self.search([('state', '=', 'submit')])
        for rec in expense_submit:
            if rec.expense_approver_user_ids:
                matrix_line = sorted(rec.expense_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.expense_approver_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_expense_extend',
                                    'email_template_application_for_expense_approval')[1]
                            except ValueError:
                                template_id = False
                            ctx = self._context.copy()
                            url = self.get_url(rec)
                            ctx.update({
                                'email_from': self.env.user.email,
                                'email_to': user.user_delegation_id.email,
                                'url': url,
                                'approver_name': user.user_delegation_id.name,
                        })
                            approver.update({
                                'user_ids': [(4, user.user_delegation_id.id)],
                                'is_delegation_mail_sent': True,
                            })
                            rec.update({
                                'approvers_ids': [(4, user.user_delegation_id.id)],
                            })
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.account_move_id.ids,
                'default_expense_sheet_id': self.id,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

class VendorDepositHrCashAdvance(models.Model):
    _inherit = 'vendor.deposit'

    expense_count = fields.Integer(compute='compute_count')
    reconcile_count = fields.Integer()
    expense_ids = fields.Many2many('hr.expense.sheet', string='Expenses')
    account_move_ids = fields.Many2many('account.move', string='Journal Entrys')
    is_reconciled = fields.Boolean(string='Is Reconciled', default=False)
    communication = fields.Char(string="Remarks", tracking=True)

    def compute_count(self):
        for record in self:
            record.expense_count = self.env['hr.expense.sheet'].search_count(
                [('id', 'in', self.expense_ids.ids)])
            record.reconcile_count = self.env['account.move'].search_count(
                [('id', 'in', self.account_move_ids.ids)])

    def get_expense(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expense',
            'view_mode': 'tree,form',
            'res_model': 'hr.expense.sheet',
            'domain': [('id', 'in', self.expense_ids.ids)],
            'context': "{'create': False}"
        }

    def get_reconcile(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reconcile',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('account.view_move_tree').id, 'tree'), (False, 'form')],
            'res_model': 'account.move',
            'domain': [('id', 'in', self.account_move_ids.ids)],
            'context': "{'create': False}"
        }


class ExpenseApproverUser(models.Model):
    _name = 'expense.approver.user'

    expense_id = fields.Many2one('hr.expense.sheet', string="Expense Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'exp_user_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver =  fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'exp_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string='Parent Status',
                             related='expense_id.state')

    @api.depends('expense_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.expense_id.expense_approver_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.expense_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.expense_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids

class AccountMove(models.Model):
    _inherit = "account.move"

    def reconcile_line_order(self):
        for rec in self:
            counter = 1
            for line in rec.line_ids:
                if line.credit == 0:
                    line.sequence = (counter - 1)
                counter += 1
                if line.debit == 0:
                    line.sequence = counter