# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime
from datetime import datetime, timedelta
from pytz import timezone
from lxml import etree
import requests
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
headers = {'content-type': 'application/json'}


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    cash_advance_limit = fields.Integer('Cash Advance Limit')


class HrJob(models.Model):
    _inherit = 'hr.job'

    cash_advance_limit = fields.Integer('Cash Advance Limit')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id',
                                  string='Currency')


class VendorDepositHrCashAdvance(models.Model):
    _inherit = 'vendor.deposit'
    _order = 'create_date desc'

    account_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")

    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    @api.model
    def default_get(self, rec):
        res = super(VendorDepositHrCashAdvance, self).default_get(rec)
        company = self.env.company
        res.update({
            'deposit_reconcile_journal_id': company.deposit_reconcile_journal_id,
            'deposit_account_id': company.deposit_account_id,
            'journal_id': company.journal_id
        })
        return res

    @api.model
    def get_state_selection(self):
        return [('draft', 'Draft'),
                ('to_approve', 'Waiting For Approval'),
                ('confirmed', 'Confirmed'),
                ('approved', 'Approved'),
                ('post', 'Paid'),
                ('returned', 'Returned'),
                ('converted', 'Reconcile as Expense'),
                ('reconciled', 'Reconciled'),
                ('cancelled', 'Cancelled'),
                ('rejected', 'Rejected')]

    name = fields.Char(string="Name", readonly=True, tracking=True, default='New')
    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee_id)
    advance_line_ids = fields.One2many('cash.advance.details', 'vendor_advance_line_id', string="Advance Line")
    cash_approver_user_ids = fields.One2many('cash.advance.approver.user', 'cash_advance_id', string='Approver')
    approvers_ids = fields.Many2many('res.users', 'approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute="_compute_can_approve")
    is_approved = fields.Boolean(string="Is Approved", compute="_compute_is_approved")
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    payment_date = fields.Date(string="Payment Date", required=True, tracking=True, default=date.today())
    advance_date = fields.Date(default=datetime.now())
    amount = fields.Monetary(currency_field='currency_id', string="Advance Amount", tracking=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    approved_user = fields.Text(string="Approved User", tracking=True)
    employee_partner_id = fields.Many2one('res.partner', 'Employee Partner', related='employee_id.address_id')
    feedback_parent = fields.Text(string='Parent Feedback')
    state = fields.Selection(get_state_selection,
        default='draft', string="Status", tracking=True)
    is_readonly = fields.Boolean(compute='_compute_is_read_only')
    employee_domain_ids = fields.Many2many('hr.employee',string="Employee Domain",compute='_get_employee_domain_ids')
    # currency_id = fields.Many2one('res.currency', string="Currency", required=True, default=lambda self: self._get_currency(), tracking=True, store=True)
    is_cash_advance_approval_matrix = fields.Boolean("Is Cash Advance Approval Matrix", compute='_compute_is_cash_advance_approval_matrix')
    state_clone = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Confirmed'),
        ('post', 'Paid'),
        ('returned', 'Returned'),
        ('converted', 'Reconcile as Expense'),
        ('reconciled', 'Reconciled'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=False, copy=False, store=True, compute='_compute_state1')
    cash_advance_cycle_id = fields.Many2one('hr.cash.advance.cycle', string="Cash Advance Cycle")
    cycle_code_id = fields.Many2one('hr.cash.advance.cycle.line', string="Cycle Code")
    from_hr = fields.Boolean('FromHR')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(VendorDepositHrCashAdvance, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(VendorDepositHrCashAdvance, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state_clone = record.state

    def _compute_is_cash_advance_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_cash_advance.cash_advance_approval_matrix')
            rec.is_cash_advance_approval_matrix = setting

    # @api.model
    # def _get_currency(self):
    #     if not self.env.user.has_group('base.group_multi_currency'):
    #         return self.env.user.company_id.currency_id.id

    @api.onchange('journal_id')
    def currency(self):
        self._get_approve_button_from_config()
        # if self.env.user.has_group('base.group_multi_currency'):
        #     for rec in self:
        #         if rec.journal_id:
        #             rec.currency_id = rec.journal_id.currency_id

    @api.depends('employee_id')
    def _get_employee_domain_ids(self):
        for record in self:
            if self.env.user.has_group('equip3_hr_cash_advance.group_cash_advance_supervisor') and not self.env.user.has_group('equip3_accounting_accessright_setting.group_cash_advance_manager'):
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
    def _compute_is_read_only(self):
        for record in self:
            if record.state == "draft":
                if  not self.env.user.has_group('equip3_hr_cash_advance.group_cash_advance_supervisor') and self.env.user.has_group('equip3_accounting_accessright_setting.group_cash_advance_user'):
                    record.is_readonly = True

                else:
                    record.is_readonly = False
               
            else:
                record.is_readonly = True
    
    # @api.model
    # def fields_view_get(self, view_id=None, view_type=None,
    #                     toolbar=True, submenu=True):
    #     res = super(VendorDepositHrCashAdvance, self).fields_view_get(
    #         view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
    #     if self.env.context.get('default_is_cash_advance') and self.env.context.get('default_is_approve') or self.env.context.get('default_is_cash_advance') and self.env.context.get('default_is_pay'):
    #         if  self.env.user.has_group('equip3_accounting_accessright_setting.group_cash_advance_manager'):
    #             root = etree.fromstring(res['arch'])
    #             root.set('create', 'true')
    #             root.set('edit', 'true')
    #             root.set('delete', 'true')
    #             res['arch'] = etree.tostring(root)
    #         else:
    #             root = etree.fromstring(res['arch'])
    #             root.set('create', 'false')
    #             root.set('edit', 'false')
    #             root.set('delete', 'false')
    #             res['arch'] = etree.tostring(root)
    #
    #     return res
    
    def custom_menu(self):
        views = [(self.env.ref('equip3_accounting_cash_advance.vendor_deposite_inherit_view_tree').id, 'tree'),
                        (self.env.ref('equip3_accounting_cash_advance.vendor_deposite_inherit_view_form_new').id, 'form')]
        if  self.env.user.has_group('equip3_accounting_accessright_setting.group_cash_advance_user') and not self.env.user.has_group('equip3_accounting_accessright_setting.group_cash_advance_manager'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Cash Advance',
                'res_model': 'vendor.deposit',
                'view_mode': 'tree,form',
                'views':views,
                'domain': [('employee_id.user_id', '=', self.env.user.id),('is_cash_advance', '=', True)],
                'context':{'default_is_cash_advance': True},
                'help':"""<p>Create a new Cash Advance</p>"""
        }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Cash Advance',
                'res_model': 'vendor.deposit',
                'view_mode': 'tree,form',
                'views':views,
                'domain': [('is_cash_advance', '=', True)],
                'context':{'default_is_cash_advance': True},
                'help':"""<p>Create a new Cash Advance</p>"""
        }

    @api.model
    def create(self, values):
        res = super(VendorDepositHrCashAdvance, self).create(values)
        if res.is_cash_advance:
            sequence = self.env['ir.sequence'].search([('code', '=', 'hr.cash.advance')])
            if not sequence:
                raise ValidationError("Sequence for HR Cash Advance not found")
            now = datetime.now()
            split_sequence = str(sequence.next_by_id()).split('/')
            advance_seq = F"ADV/{split_sequence[0]}/{now.month}/{now.day}/{split_sequence[1]}"
            res.name = advance_seq
        return res

    @api.onchange('advance_date')
    def onchange_advance_date(self):
        for rec in self:
            if rec.advance_date and rec.from_hr:
                ca_cycle_line = self.env["hr.cash.advance.cycle.line"].search([
                    ("cycle_start","<=",rec.advance_date),("cycle_end",">=",rec.advance_date)],
                    limit=1)
                if ca_cycle_line:
                    rec.cash_advance_cycle_id = ca_cycle_line.cash_advance_cycle_id.id
                    rec.cycle_code_id = ca_cycle_line.id
                else:
                    rec.cycle_code_id = False
            else:
                rec.cycle_code_id = False

    @api.onchange('advance_line_ids')
    def onchange_amount(self):
        for rec in self:
            total_amt = 0
            for line in rec.advance_line_ids:
                total_amt += line.amount
        rec.amount = total_amt

    @api.constrains('amount','cycle_code_id')
    def _check_advan_limit(self):
        for amt in self:
            if amt.from_hr:
                ca_cycle_line = amt.cycle_code_id
                if ca_cycle_line:
                    if amt.employee_id and amt.employee_id.cash_advance_limit != 0:
                        cash_limit = amt.employee_id.cash_advance_limit
                    elif amt.employee_id and amt.employee_id.job_id.cash_advance_limit != 0:
                        cash_limit = amt.employee_id.job_id.cash_advance_limit
                    elif amt.employee_id and amt.employee_id.cash_advance_limit == 0 and amt.employee_id.job_id.cash_advance_limit == 0:
                        raise ValidationError("Please set Cash Advance Limit")
                    
                    if ca_cycle_line.cash_advance_cycle_id.limit_type == "monthly":
                        akum_amount_before = 0
                        akum_amount = amt.amount
                        cash_advance_obj = self.env["vendor.deposit"].search([("id","!=",amt.id),("employee_id","=",amt.employee_id.id),("cycle_code_id","=",amt.cycle_code_id.id),('state','not in',['cancelled','rejected','returned'])])
                        for rec in cash_advance_obj:
                            if rec.state == "post":
                                akum_amount_before += rec.remaining_amount
                                akum_amount += rec.remaining_amount
                            elif rec.state == "converted":
                                akum_return_amount = 0
                                if rec.return_cash_advance_ids:
                                    for ret in rec.return_cash_advance_ids:
                                        akum_return_amount += sum(ret.line_ids.mapped("debit")) or 0.0
                                akum_amount_before += rec.amount - akum_return_amount
                                akum_amount += rec.amount - akum_return_amount
                            else:
                                akum_amount_before += rec.amount
                                akum_amount += rec.amount
                        remaining_limit = cash_limit - akum_amount_before
                        remaining_limit_with_separator = (f"{remaining_limit:,}")
                        if akum_amount > cash_limit:
                            raise ValidationError(
                                _('Cash Advance limit exceeded, remaining limit in this cycle = %s',
                                    remaining_limit_with_separator))
                else:
                    raise ValidationError("There is no available period for this advance")


    def action_confirm(self):
        ca_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_cash_advance.cash_advance_approval_matrix')
        for record in self:
            if ca_setting:
                record.write({'state': 'confirmed'})
                record.approver_mail()
                record.approver_wa_template()
                for line in record.cash_approver_user_ids:
                    line.write({'approver_state': 'draft'})
            else:
                record.write({'state': 'approved'})

    @api.onchange('employee_id', 'amount')
    def onchange_approver_user(self):
        for cash in self:
            ca_setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_cash_advance.cash_advance_approval_matrix')
            if ca_setting:
                if cash.cash_approver_user_ids:
                    remove = []
                    for line in cash.cash_approver_user_ids:
                        remove.append((2, line.id))
                    cash.cash_approver_user_ids = remove
                setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_cash_advance.cash_type_approval')
                if setting == 'employee_hierarchy':
                    # self.cash_emp_by_hierarchy()
                    cash.cash_approver_user_ids = self.cash_emp_by_hierarchy(cash)
                    self.app_list_cash_emp_by_hierarchy()
                if setting == 'approval_matrix':
                    self.cash_approval_by_matrix(cash)

    def app_list_cash_emp_by_hierarchy(self):
        for cash in self:
            app_list = []
            for line in cash.cash_approver_user_ids:
                app_list.append(line.user_ids.id)
            cash.approvers_ids = app_list

    def cash_emp_by_hierarchy(self, cash):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(cash, cash.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, cash, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_cash_advance.cash_level')
        if not setting_level:
            raise ValidationError("level not set")
        if not employee_manager['parent_id']['user_id']:
            return approval_ids
        while data < int(setting_level):
            approval_ids.append(
                (0, 0, {'user_ids': [(4, employee_manager['parent_id']['user_id']['id'])]}))
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager(cash, employee_manager['parent_id'], data, approval_ids, seq)
                break

        return approval_ids

    def get_manager_hierarchy(self, cash, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(cash, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def cash_approval_by_matrix(self, cash):
        app_list = []
        approval_matrix = self.env['hr.cash.advance.approval.matrix'].search(
            [('apply_to', '=', 'by_employee'), ('maximum_amount', '>=', cash.amount),
             ('minimum_amount', '<=', cash.amount)])
        matrix = approval_matrix.filtered(lambda line: cash.employee_id.id in line.employee_ids.ids)
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
                    approvers = self.get_manager_hierarchy(cash, cash.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            cash.approvers_ids = app_list
            cash.cash_approver_user_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.cash.advance.approval.matrix'].search(
                [('apply_to', '=', 'by_job_position'), ('maximum_amount', '>=', cash.amount),
                 ('minimum_amount', '<=', cash.amount)])
            matrix = approval_matrix.filtered(lambda line: cash.job_id.id in line.job_ids.ids)
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
                        approvers = self.get_manager_hierarchy(cash, cash.employee_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                cash.approvers_ids = app_list
                cash.cash_approver_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.cash.advance.approval.matrix'].search(
                    [('apply_to', '=', 'by_department'), ('maximum_amount', '>=', cash.amount),
                     ('minimum_amount', '<=', cash.amount)])
                matrix = approval_matrix.filtered(lambda line: cash.department_id.id in line.deparment_ids.ids)
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
                            approvers = self.get_manager_hierarchy(cash, cash.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    cash.approvers_ids = app_list
                    cash.cash_approver_user_ids = data_approvers

    @api.depends('state', 'employee_id', 'amount')
    def _compute_can_approve(self):
        for cash in self:
            if cash.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_cash_advance.cash_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_cash_advance.cash_level')
                app_level = int(setting_level)
                current_user = cash.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(cash.cash_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(cash.cash_approver_user_ids)
                    if app < app_level and app < a:
                        if current_user in cash.cash_approver_user_ids[app].user_ids:
                            cash.is_approver = True
                        else:
                            cash.is_approver = False
                    else:
                        cash.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(cash.cash_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(cash.cash_approver_user_ids)
                    if app < a:
                        for line in cash.cash_approver_user_ids[app]:
                            # if current_user in cash.cash_approver_user_ids:
                            #     cash.is_approver = False
                            if current_user in line.user_ids:
                                cash.is_approver = True
                            else:
                                cash.is_approver = False
                    else:
                        cash.is_approver = False
                else:
                    cash.is_approver = False
            else:
                cash.is_approver = False

    @api.depends('state', 'employee_id', 'amount', 'approved_user_ids')
    def _compute_is_approved(self):
        current_user = self.env.user
        for rec in self:
            if current_user in rec.approved_user_ids or rec.state != 'confirmed':
                rec.is_approved = True
            else:
                rec.is_approved = False

    def action_approve(self):
        sequence_matrix = [data.name for data in self.cash_approver_user_ids]
        sequence_approval = [data.name for data in self.cash_approver_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.cash_approver_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        for record in self:
            current_user = self.env.uid
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_cash_advance.cash_type_approval')
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            if setting == 'employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.cash_approver_user_ids:
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
                                            feedback_list = [user.feedback, f"{self.env.user.name}:{record.feedback_parent}"]
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
                        matrix_line = sorted(record.cash_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.write({'state': 'approved'})
                            record.approved_mail()
                            self.approved_wa_template()
                        else:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
                                self.approver_wa_template()
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved for this Leave!'
                    ))
            elif setting == 'approval_matrix':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for line in record.cash_approver_user_ids:
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

                        matrix_line = sorted(record.cash_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            record.write({'state': 'approved'})
                            record.approved_mail()
                            self.approved_wa_template()
                        else:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            if len(approval.approved_employee_ids) == approval.minimum_approver and not approval.name == max_seq:
                                self.approver_wa_template()
                    else:
                        raise ValidationError(_(
                            'You are not allowed to perform this action!'
                        ))
                else:
                    raise ValidationError(_(
                        'Already approved for this Leave!'
                    ))
            else:
                raise ValidationError(_(
                    'Already approved for this Leave!'
                ))

    def action_reject(self):
        for record in self:
            for user in record.cash_approver_user_ids:
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
            record.approved_user = self.env.user.name + ' ' + 'has Rejected the Cash Advance!'
            record.write({'state': 'rejected'})
            record.reject_mail()
            self.rejected_wa_template()

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.deposit.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':True},
            'target': 'new'
        }
        
        
    def wizard_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.deposit.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':False,
                       'default_is_reject':True},
            'target': 'new'
        }

    def unlink(self):
        for expense in self:
            if expense.state in ['confirmed', 'approved']:
                raise UserError(_('You cannot delete a Advance to Approve.'))
        return super(VendorDepositHrCashAdvance, self).unlink()

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_cash_advance', 'menu_account_cash_advance_approve')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_cash_advance', 'action_account_cash_advance_approve_manager')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=vendor.deposit&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.cash_approver_user_ids:
                matrix_line = sorted(rec.cash_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.cash_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_cash_advance',
                            'email_template_application_for_cash_advance_approval')[1]
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
            if rec.cash_approver_user_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_cash_advance',
                        'email_template_approval_cash_advance_request')[1]
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
            if rec.cash_approver_user_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_cash_advance',
                        'email_template_rejection_of_cash_advance_request')[1]
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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_cash_advance.send_by_wa_cashadvance')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(self)
        if send_by_wa:
            template = self.env.ref('equip3_hr_cash_advance.cash_advance_approver_wa_template')
            wa_sender = waParam()
            if template:
                if self.cash_approver_user_ids:
                    matrix_line = sorted(self.cash_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.cash_approver_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", self.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.name)
                        if "${communication}" in string_test:
                            string_test = string_test.replace("${communication}", self.communication)
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
                        
                        # param = {'body': string_test, 'phone': phone_num}
                        # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
                        # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
                        # try:
                        #     request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
                        # except ConnectionError:
                        #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_cash_advance.send_by_wa_cashadvance')
        if send_by_wa:
            template = self.env.ref('equip3_hr_cash_advance.cash_advance_approved_wa_template')
            url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.cash_approver_user_ids:
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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_cash_advance.send_by_wa_cashadvance')
        if send_by_wa:
            template = self.env.ref('equip3_hr_cash_advance.cash_advance_rejected_wa_template')
            url = self.get_url(self)
            wa_sender = waParam()
            if template:
                if self.cash_approver_user_ids:
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

    def get_auto_follow_up_approver_wa_template(self, rec):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_cash_advance.send_by_wa_cashadvance')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        url = self.get_url(rec)
        if send_by_wa:
            template = self.env.ref('equip3_hr_cash_advance.cash_advance_approver_wa_template')
            wa_sender = waParam()
            if template:
                if rec.cash_approver_user_ids:
                    matrix_line = sorted(rec.cash_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = rec.cash_approver_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", rec.employee_id.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", rec.name)
                        if "${communication}" in string_test:
                            string_test = string_test.replace("${communication}", rec.communication)
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
        number_of_repititions_cash = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_cash_advance.number_of_repititions_cash'))
        cash_confirmed = self.search([('state', '=', 'confirmed')])
        for rec in cash_confirmed:
            if rec.cash_approver_user_ids:
                matrix_line = sorted(rec.cash_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.cash_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_cash_advance',
                            'email_template_application_for_cash_advance_approval')[1]
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
                        count = number_of_repititions_cash - 1
                        query_statement = """UPDATE cash_advance_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                        self.get_auto_follow_up_approver_wa_template(rec)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE cash_advance_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
                            self.get_auto_follow_up_approver_wa_template(rec)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        cash_confirmed = self.search([('state', '=', 'confirmed')])
        for rec in cash_confirmed:
            if rec.cash_approver_user_ids:
                matrix_line = sorted(rec.cash_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.cash_approver_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_cash_advance',
                                    'email_template_application_for_cash_advance_approval')[1]
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

    def action_pay_cash_advance(self):
        for record in self:
            ref = (record.name or '')
            name = 'Cash Advance ' + (record.name or '')
            if not record.journal_id.payment_credit_account_id.id:
                raise Warning("Payment Method Credit Account Not Found!")
            debit_vals = {
                    'debit': abs(record.amount),
                    'date': record.payment_date,
                    'name': name,
                    'credit': 0.0,
                    'account_id': record.deposit_account_id.id,
                    'analytic_tag_ids': record.account_tag_ids.ids,
                }
            credit_vals = {
                    'debit': 0.0,
                    'date': record.payment_date,
                    'name': name,
                    'credit': abs(record.amount),
                    'account_id': record.journal_id.payment_credit_account_id.id,
                    'analytic_tag_ids': record.account_tag_ids.ids,
                }
            vals = {
                'ref': ref,
                'date': record.payment_date,
                'journal_id': record.journal_id.id,
                'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
            }
            move_id = self.env['account.move'].create(vals)
            move_id.post()
            record.move_id = move_id.id
            record.remaining_amount = record.amount
            record.write({'state': 'post'})

class CashAdvanceDetails(models.Model):
    _name = 'cash.advance.details'

    vendor_advance_line_id = fields.Many2one('vendor.deposit', string="Advance Id")
    name = fields.Char(string="Description", required=True)
    amount = fields.Float(string="Amount", required=True)


class CashAdvanceApproverUser(models.Model):
    _name = 'cash.advance.approver.user'

    cash_advance_id = fields.Many2one('vendor.deposit', string="Advance Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'app_emp_ids', string="Approved user")
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
    matrix_user_ids = fields.Many2many('res.users', 'max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string="Parent Status", related='cash_advance_id.state')

    @api.depends('cash_advance_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.cash_advance_id.cash_approver_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.cash_advance_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.cash_advance_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids

class ResCompany(models.Model):
    _inherit = "res.company"

    deposit_reconcile_journal_id = fields.Many2one('account.journal', string="Reconcile Journal", invisible=True)
    journal_id = fields.Many2one('account.journal', string="Payment Method", invisible=True)
    deposit_account_id = fields.Many2one('account.account', string="Advance Account", invisible=True,)