# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
from odoo.exceptions import UserError, Warning
import requests
from lxml import etree
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

headers = {'content-type': 'application/json'}


class HrEmployeeTravelCancellation(models.Model):
    _name = "employee.travel.cancellation"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def _default_employee(self):
        return self.env.user.employee_id

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    name = fields.Char(string="Name", readonly=True, default='New')
    employee_id = fields.Many2one('hr.employee', 'Employee', default=_default_employee, required=True, domain=_multi_company_domain)
    domain_employee_ids = fields.Many2many('hr.employee', string="Employee Domain", compute='_compute_employee_ids')
    is_readonly = fields.Boolean(compute='_compute_read_only')
    start_today_date = fields.Date('Contract Start Date', compute='_compute_today')
    travel_id = fields.Many2one('travel.request', string="Travel", required=True,
                                domain="[('state', '=', 'approved'), ('employee_id', '=', employee_id), ('req_departure_date', '>', start_today_date)]")
    department_manager_id = fields.Many2one('hr.employee', string="Manager", readonly=True,
                                            related='travel_id.department_manager_id')
    department_id = fields.Many2one('hr.department', string="Department", readonly=True,
                                    related='employee_id.department_id')
    job_id = fields.Many2one('hr.job', string="Job Position", readonly=True, related='employee_id.job_id')
    currency_id = fields.Many2one('res.currency', string="Currency", readonly=True, related='travel_id.currency_id')
    expence_sheet_id = fields.Many2one('hr.expense.sheet', string="Created Expense Sheet", readonly=True,
                                       related='travel_id.expence_sheet_id')
    cash_advance_orgin_id = fields.Many2one('vendor.deposit', string="Created Cash Advance", readonly=True,
                                            related='travel_id.cash_advance_orgin_id')

    travel_purpose = fields.Char(string="Travel Purpose", readonly=True, related='travel_id.travel_purpose')
    project_id = fields.Many2one('project.task', string="Project", readonly=True, related='travel_id.project_id')
    account_analytic_id = fields.Many2one('account.analytic.account', readonly=True,
                                          related='travel_id.account_analytic_id')

    from_city = fields.Char('City', readonly=True, related='travel_id.from_city')
    from_state_id = fields.Many2one('res.country.state', string="State", readonly=True,
                                    related='travel_id.from_state_id')
    from_country_id = fields.Many2one('res.country', string="Country", readonly=True,
                                      related='travel_id.from_country_id')

    req_departure_date = fields.Date(string="Request Departure Date", readonly=True,
                                         related='travel_id.req_departure_date')
    req_return_date = fields.Date(string="Request Return Date", readonly=True, related='travel_id.req_return_date')
    days = fields.Char('Days', related='travel_id.days', readonly=True, )
    req_travel_mode_id = fields.Many2one('travel.mode', string="Request Mode Of Travel", readonly=True,
                                         related='travel_id.req_travel_mode_id')
    return_mode_id = fields.Many2one('travel.mode', string="Return Mode Of Travel", readonly=True,
                                     related='travel_id.return_mode_id')

    phone_no = fields.Char('Contact Number', readonly=True, related='travel_id.phone_no')
    email = fields.Char('Email', readonly=True, related='travel_id.email')

    available_departure_date = fields.Datetime(string="Available Departure Date", readonly=True,
                                               related='travel_id.available_departure_date')
    available_return_date = fields.Datetime(string="Available Return Date", readonly=True,
                                            related='travel_id.available_return_date')
    departure_mode_travel_id = fields.Many2one('travel.mode', string="Departure Mode Of Travel", readonly=True,
                                               related='travel_id.departure_mode_travel_id')
    return_mode_travel_id = fields.Many2one('travel.mode', string="Return Mode Of Travel", readonly=True,
                                            related='travel_id.return_mode_travel_id')
    visa_agent_id = fields.Many2one('res.partner', string="Visa Agent", readonly=True,
                                    related='travel_id.visa_agent_id')
    ticket_booking_agent_id = fields.Many2one('res.partner', string="Ticket Booking Agent", readonly=True,
                                              related='travel_id.ticket_booking_agent_id')

    bank_id = fields.Many2one('res.bank', string="Bank Name", readonly=True, related='travel_id.bank_id')
    cheque_number = fields.Char(string="Cheque Number", readonly=True, related='travel_id.cheque_number')

    # advance_payment_ids = fields.One2many('hr.expense', 'travel_id', string="Advance Expenses", readonly=True, related='travel_id.advance_payment_ids')
    expense_ids = fields.One2many('hr.expense', 'travel_expence_id', string="Expenses", readonly=True,
                                  related='travel_id.expense_ids')

    cash_advance_ids = fields.One2many('travel.vendor.deposit', 'travel_cash_id', string="Cash Advance", readonly=True,
                                       related='travel_id.cash_advance_ids')
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'To Approved'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default="draft", string="Status")

    # Travel
    travel_cancel_approver_user_ids = fields.One2many('travel.cancel.approver.user',
                                                      'emp_travel_cancel_id', string='Approver')
    approvers_ids = fields.Many2many('res.users', 'emp_travel_cancel_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approved_user_text = fields.Text(string="Approved User")
    approved_user = fields.Text(string="Approved User")
    feedback_parent = fields.Text(string='Parent Feedback')
    state1 = fields.Selection([
            ('draft', 'Draft'),
            ('confirmed', 'To Approved'),
            ('approved', 'Submitted'),
            ('rejected', 'Rejected'),
        ],
        default="draft",
        string="Status",
        copy=False,
        store=True,
        compute="_compute_state1"
    )
    is_travel_approval_matrix = fields.Boolean(
        string='Is Travel Approval Matrix',
        compute="_compute_is_travel_approval_matrix"
    ) 
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrEmployeeTravelCancellation, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrEmployeeTravelCancellation, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def _compute_is_travel_approval_matrix(self):
        for line in self:
            travel_approval_matrix_setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_travel_extend.travel_approval_matrix'
            )
            line.is_travel_approval_matrix = travel_approval_matrix_setting
    
    @api.depends('state')
    def _compute_state1(self):
        for line in self:
            line.state1 = line.state
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrEmployeeTravelCancellation, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.context.get('is_to_approve'):
            if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_travel_administrator'):
                root = etree.fromstring(res['arch'])
                root.set('create', 'true')
                root.set('edit', 'true')
                root.set('delete', 'true')
                res['arch'] = etree.tostring(root)
            elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_travel_supervisor') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_travel_administrator'):
                root = etree.fromstring(res['arch'])
                root.set('create', 'true')
                root.set('edit', 'false')
                root.set('delete', 'false')
                res['arch'] = etree.tostring(root)
            else:
                root = etree.fromstring(res['arch'])
                root.set('create', 'false')
                root.set('edit', 'false')
                root.set('delete', 'false')
                res['arch'] = etree.tostring(root)
            
        return res

    def custom_menu(self):
        views = [(self.env.ref('equip3_hr_travel_extend.view_employee_travel_cancellation_tree').id, 'tree'),
                 (self.env.ref('equip3_hr_travel_extend.view_employee_travel_cancellation_form').id, 'form')]
        if self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_travel_supervisor') and not self.env.user.has_group(
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
                    'name': 'Employee Travel Cancellation',
                    'res_model': 'employee.travel.cancellation',
                    'target': 'current',
                    'view_mode': 'tree,form',
                    'views': views,
                    'domain': [('employee_id', 'in', employee_ids)],
                    'context': {},
                    'help': """<p class="o_view_nocontent_smiling_face">
                        Create a new Employee Travel Cancellation
                    </p>"""
                    # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                    # 'search_view_id':search_view_id.id,

                }
        elif self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_travel_self_service') and not self.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_travel_supervisor'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Travel Cancellation',
                'res_model': 'employee.travel.cancellation',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create a new Employee Travel Cancellation
                </p>""",
                'context': {},
                'views': views,
                # 'search_view_id':search_view_id.id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Travel Cancellation',
                'res_model': 'employee.travel.cancellation',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [],
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create a new Employee Travel Cancellation
                </p>""",
                'context': {},
                'views': views,
                # 'search_view_id':search_view_id.id,
            }

    @api.depends('employee_id')
    def _compute_read_only(self):
        for record in self:
            if self.env.user.has_group(
                    'equip3_hr_employee_access_right_setting.group_hr_travel_self_service') and not self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_travel_supervisor'):
                record.is_readonly = True
            else:
                record.is_readonly = False

    @api.depends('employee_id')
    def _compute_employee_ids(self):
        for record in self:
            employee_ids = []
            if self.env.user.has_group(
                    'equip3_hr_employee_access_right_setting.group_hr_travel_supervisor') and not self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_travel_manager'):
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
    def create(self, vals):
        sequence_no = self.env['ir.sequence'].next_by_code('employee.travel.cancellation')
        vals.update({'name': sequence_no})
        result = super(HrEmployeeTravelCancellation, self).create(vals)
        return result

    @api.onchange('employee_id', 'travel_id')
    def onchange_approver_user(self):
        for travel_cancel in self:
            if travel_cancel.travel_cancel_approver_user_ids:
                remove = []
                for line in travel_cancel.travel_cancel_approver_user_ids:
                    remove.append((2, line.id))
                travel_cancel.travel_cancel_approver_user_ids = remove
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_travel_extend.travel_type_approval')
            if setting == 'employee_hierarchy':
                travel_cancel.travel_cancel_approver_user_ids = self.travel_cancel_emp_by_hierarchy(
                    travel_cancel)
                self.app_list_travel_cancel_emp_by_hierarchy()
            if setting == 'approval_matrix':
                self.travel_cancel_approval_by_matrix(travel_cancel)

    def travel_cancel_emp_by_hierarchy(self, travel_cancel):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(travel_cancel, travel_cancel.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, travel_cancel, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_travel_extend.travel_level')
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
                self.get_manager(travel_cancel, employee_manager['parent_id'], data, approval_ids, seq)
                break
        return approval_ids

    def app_list_travel_cancel_emp_by_hierarchy(self):
        for travel_cancel in self:
            app_list = []
            for line in travel_cancel.travel_cancel_approver_user_ids:
                app_list.append(line.user_ids.id)
            travel_cancel.approvers_ids = app_list

    def get_manager_hierarchy(self, travel_cancel, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(travel_cancel, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def travel_cancel_approval_by_matrix(self, travel_cancel):
        app_list = []
        approval_matrix = self.env['hr.travel.approval.matrix'].search([('apply_to', '=', 'by_employee')])
        matrix = approval_matrix.filtered(lambda line: travel_cancel.employee_id.id in line.employee_ids.ids)
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
                    approvers = self.get_manager_hierarchy(travel_cancel, travel_cancel.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            travel_cancel.approvers_ids = app_list
            travel_cancel.travel_cancel_approver_user_ids = data_approvers
        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.travel.approval.matrix'].search([('apply_to', '=', 'by_job_position')])
            matrix = approval_matrix.filtered(lambda line: travel_cancel.job_id.id in line.job_ids.ids)
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
                        approvers = self.get_manager_hierarchy(travel_cancel, travel_cancel.employee_id, data,
                                                               manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                travel_cancel.approvers_ids = app_list
                travel_cancel.travel_cancel_approver_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.travel.approval.matrix'].search([('apply_to', '=', 'by_department')])
                matrix = approval_matrix.filtered(
                    lambda line: travel_cancel.department_id.id in line.department_ids.ids)
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
                            approvers = self.get_manager_hierarchy(travel_cancel, travel_cancel.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    travel_cancel.approvers_ids = app_list
                    travel_cancel.travel_cancel_approver_user_ids = data_approvers

    @api.depends('state', 'employee_id')
    def _compute_can_approve(self):
        for travel_cancel in self:
            if travel_cancel.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_travel_extend.travel_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_travel_extend.travel_level')
                app_level = int(setting_level)
                current_user = travel_cancel.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(
                        travel_cancel.travel_cancel_approver_user_ids.filtered(
                            lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(travel_cancel.travel_cancel_approver_user_ids)
                    if app < app_level and app < a:
                        if current_user in travel_cancel.travel_cancel_approver_user_ids[app].user_ids:
                            travel_cancel.is_approver = True
                        else:
                            travel_cancel.is_approver = False
                    else:
                        travel_cancel.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(
                        travel_cancel.travel_cancel_approver_user_ids.filtered(
                            lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(travel_cancel.travel_cancel_approver_user_ids)
                    if app < a:
                        for line in travel_cancel.travel_cancel_approver_user_ids[app]:
                            if current_user in line.user_ids:
                                travel_cancel.is_approver = True
                            else:
                                travel_cancel.is_approver = False
                    else:
                        travel_cancel.is_approver = False

                else:
                    travel_cancel.is_approver = False
            else:
                travel_cancel.is_approver = False

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'travel.cancel.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':True},
            'name': "Confirmation Message",
            'target': 'new',
        }
        
    def wizard_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'travel.cancel.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':False,
                       'default_is_reject':True},
            'name': "Confirmation Message",
            'target': 'new',
        }

    def action_approve(self):
        sequence_matrix = [data.name for data in self.travel_cancel_approver_user_ids]
        sequence_approval = [data.name for data in self.travel_cancel_approver_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.travel_cancel_approver_user_ids.filtered(
            lambda line: self.env.user.id in line.user_ids.ids and len(
                line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
        for record in self:
            current_user = self.env.uid
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_travel_extend.travel_type_approval')
            now = datetime.now(timezone(self.env.user.tz))
            dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            date_approved = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_approved_obj = datetime.strptime(date_approved, DEFAULT_SERVER_DATE_FORMAT)
            if setting == 'employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.travel_cancel_approver_user_ids:
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
                            record.travel_cancel_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            # record.write({'state': 'approved'})
                            record.action_approve_cancel()
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
                        for line in record.travel_cancel_approver_user_ids:
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

                        matrix_line = sorted(
                            record.travel_cancel_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            # record.write({'state': 'approved'})
                            record.action_approve_cancel()
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
            for user in record.travel_cancel_approver_user_ids:
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

    @api.depends('employee_id', 'travel_id')
    def _compute_today(self):
        for rec in self:
            rec.start_today_date = date.today()

    def action_confirm(self):
        travel_approval_matrix_setting = self.env['ir.config_parameter'].sudo().get_param(
            'equip3_hr_travel_extend.travel_approval_matrix'
        )
        for rec in self:
            if travel_approval_matrix_setting:
                rec.write({'state': 'confirmed'})
            else:
                rec.write({'state': 'approved'})

            for line in rec.travel_cancel_approver_user_ids:
                line.write({'approver_state': 'draft'})
        self.approver_mail()
        self.approver_wa_template()

    def action_approve_cancel(self):
        for rec in self:
            rec.write({'state': 'approved'})
            rec.travel_id.write({'state': 'cancelled'})

    # Emails
    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_travel_extend', 'menu_travel_cancel_approve')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_travel_extend', 'action_travel_cancel_approve')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=employee.travel.cancellation&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.travel_cancel_approver_user_ids:
                matrix_line = sorted(rec.travel_cancel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.travel_cancel_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_travel_extend',
                            'email_template_travel_cancel_approval')[1]
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
                    if self.req_departure_date:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(self.req_departure_date).strftime(
                                '%d/%m/%Y %I:%M:%S %p')})
                    if self.req_return_date:
                        ctx.update(
                            {'date_to': fields.Datetime.from_string(self.req_return_date).strftime(
                                '%d/%m/%Y %I:%M:%S %p')})
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id, force_send=True)
                break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.travel_cancel_approver_user_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_travel_extend',
                        'email_template_travel_cancel_approved')[1]
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
            if rec.travel_cancel_approver_user_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_travel_extend',
                        'email_template_travel_cancel_rejection')[1]
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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_travel_extend.send_by_wa_travel')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if send_by_wa:
            template = self.env.ref('equip3_hr_travel_extend.travel_cancel_request_wa_template')
            wa_sender = waParam()
            if template:
                if self.travel_cancel_approver_user_ids:
                    url = self.get_url(self)
                    matrix_line = sorted(self.travel_cancel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.travel_cancel_approver_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        string_test = str(template.message)
                        if "${employee_name}" in string_test:
                            string_test = string_test.replace("${employee_name}", self.employee_id.name)
                        if "${travel_purpose}" in string_test:
                            string_test = string_test.replace("${travel_purpose}", self.travel_purpose)
                        if "${project_name}" in string_test:
                            string_test = string_test.replace("${project_name}", self.project_id.name)
                        if "${req_departure_date}" in string_test:
                            string_test = string_test.replace("${req_departure_date}", fields.Datetime.from_string(
                                self.req_departure_date).strftime('%d/%m/%Y'))
                        if "${req_return_date}" in string_test:
                            string_test = string_test.replace("${req_return_date}", fields.Datetime.from_string(
                                self.req_return_date).strftime('%d/%m/%Y'))
                        if "${approver_name}" in string_test:
                            string_test = string_test.replace("${approver_name}", user.name)
                        if "${name}" in string_test:
                            string_test = string_test.replace("${name}", self.name)
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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_travel_extend.send_by_wa_travel')
        if send_by_wa:
            template = self.env.ref('equip3_hr_travel_extend.travel_cancel_approved_wa_template')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.travel_cancel_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${travel_name}" in string_test:
                        string_test = string_test.replace("${travel_name}", self.name)
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)
                    if "+" in phone_num:
                        phone_num = int(phone_num.replace("+", ""))
                    if "${url}" in string_test:
                        string_test = string_test.replace("${url}", f"{base_url}/leave/{self.id}")

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
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_travel_extend.send_by_wa_travel')
        if send_by_wa:
            template = self.env.ref('equip3_hr_travel_extend.travel_cancel_rejected_wa_template')
            wa_sender = waParam()
            if template:
                if self.travel_cancel_approver_user_ids:
                    string_test = str(template.message)
                    if "${employee_name}" in string_test:
                        string_test = string_test.replace("${employee_name}", self.employee_id.name)
                    if "${travel_name}" in string_test:
                        string_test = string_test.replace("${travel_name}", self.name)
                    if "${br}" in string_test:
                        string_test = string_test.replace("${br}", f"\n")
                    phone_num = str(self.employee_id.mobile_phone)

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
        number_of_repetitions_travel = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_travel_extend.number_of_repetitions_travel'))
        travel_cancel_confirmed = self.search([('state', '=', 'confirmed')])
        for rec in travel_cancel_confirmed:
            if rec.travel_cancel_approver_user_ids:
                matrix_line = sorted(rec.travel_cancel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.travel_cancel_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_travel_extend',
                            'email_template_travel_cancel_approval')[1]
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
                    if rec.req_departure_date:
                        ctx.update(
                            {'date_from': fields.Datetime.from_string(rec.req_departure_date).strftime(
                                '%d/%m/%Y %I:%M:%S %p')})
                    if rec.req_return_date:
                        ctx.update(
                            {'date_to': fields.Datetime.from_string(rec.req_return_date).strftime(
                                '%d/%m/%Y %I:%M:%S %p')})
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_travel - 1
                        query_statement = """UPDATE travel_cancel_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE travel_cancel_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        travel_cancel_confirmed = self.search([('state', '=', 'confirmed')])
        for rec in travel_cancel_confirmed:
            if rec.travel_cancel_approver_user_ids:
                matrix_line = sorted(rec.travel_cancel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.travel_cancel_approver_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_travel_extend',
                                    'email_template_travel_cancel_approval')[1]
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
                            if rec.req_departure_date:
                                ctx.update(
                                    {'date_from': fields.Datetime.from_string(rec.req_departure_date).strftime(
                                        '%d/%m/%Y %I:%M:%S %p')})
                            if rec.req_return_date:
                                ctx.update(
                                    {'date_to': fields.Datetime.from_string(rec.req_return_date).strftime(
                                        '%d/%m/%Y %I:%M:%S %p')})
                            approver.update({
                                'user_ids': [(4, user.user_delegation_id.id)],
                                'is_delegation_mail_sent': True,
                            })
                            rec.update({
                                'approvers_ids': [(4, user.user_delegation_id.id)],
                            })
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

class TrainingConductCancelApproverUser(models.Model):
    _name = 'travel.cancel.approver.user'

    emp_travel_cancel_id = fields.Many2one('employee.travel.cancellation', string="Employee Travel Cancel Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'emp_travel_cancel_user_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    # Auto Follow email
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'travel_cancel_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string="Parent Status", related='emp_travel_cancel_id.state')

    @api.depends('emp_travel_cancel_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.emp_travel_cancel_id.travel_cancel_approver_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.emp_travel_cancel_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.emp_travel_cancel_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids