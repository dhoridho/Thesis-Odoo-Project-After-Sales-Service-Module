# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from datetime import date, datetime, timedelta
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
import pytz
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning, UserError
from odoo.exceptions import UserError, ValidationError
from lxml import etree
import requests
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

headers = {'content-type': 'application/json'}


class HrTravelRequest(models.Model):
    _inherit = "travel.request"
    _order = "create_date desc"

    def _default_employee(self):
        return self.env.user.employee_id

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    @api.model
    def get_state_selection(self):
        return [('draft', 'Draft'),
                ('confirmed', 'To Approved'),
                ('approved', 'Approved'),
                ('cancelled', 'Cancelled'),
                ('rejected', 'Rejected'),
                ('cash_advance_submitted', 'Cash Advance Created'),
                ('returned', 'Returned'),
                ('submitted', 'Expenses Created')]

    name = fields.Char(string="Name", readonly=True, default='New')
    employee_id = fields.Many2one('hr.employee', 'Employee', default=_default_employee, domain=_multi_company_domain)
    cash_advance_ids = fields.One2many('travel.vendor.deposit', 'travel_cash_id', string="Cash Advance")
    cash_advance_orgin_id = fields.Many2one('vendor.deposit', string="Created Cash Advance")
    cash_advance_state = fields.Selection(string="Status", readonly=True, related='cash_advance_orgin_id.state')
    state = fields.Selection(get_state_selection, default="draft", string="States")
    state1 = fields.Selection(related="state")
    is_return_button_visible = fields.Boolean('Return Button Visible', compute='compute_is_return', default=False)

    travel_approver_user_ids = fields.One2many('travel.approver.user', 'emp_travel_id', string='Approver')
    approvers_ids = fields.Many2many('res.users', 'emp_travel_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    is_approved = fields.Boolean(string="Is Approved", compute="_compute_is_approved")
    approved_user_text = fields.Text(string="Approved User")
    approved_user = fields.Text(string="Approved User")
    feedback_parent = fields.Text(string='Parent Feedback')
    domain_employee_ids = fields.Many2many('hr.employee', string="Employee Domain", compute='_compute_employee_ids')
    is_readonly = fields.Boolean(compute='_compute_read_only')
    state2 = fields.Selection([
            ('draft', 'Draft'),
            ('confirmed', 'To Approved'),
            ('approved', 'Submitted'),
            ('cancelled', 'Cancelled'),
            ('rejected', 'Rejected'),
            ('cash_advance_submitted', 'Cash Advance Created'),
            ('returned', 'Returned'),
            ('submitted', 'Expenses Created')
        ],
        default="draft",
        string="States",
        copy=False,
        store=True,
        compute="_compute_state2"
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

        result = super(HrTravelRequest, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrTravelRequest, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def _compute_is_travel_approval_matrix(self):
        for line in self:
            travel_approval_matrix_setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_travel_extend.travel_approval_matrix'
            )
            line.is_travel_approval_matrix = travel_approval_matrix_setting
    
    @api.depends('state')
    def _compute_state2(self):
        for line in self:
            line.state2 = line.state
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrTravelRequest, self).fields_view_get(
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

    def check_ca_limit(self):
        departure_date = self.req_departure_date
        ca_cycle_line = self.env["hr.cash.advance.cycle.line"].search([
            ("cycle_start","<=",departure_date),("cycle_end",">=",departure_date)],
            limit=1)
        if ca_cycle_line:
            cycle_code_id = ca_cycle_line.id
        else:
            cycle_code_id = False
        
        total_amt = 0
        for line in self.cash_advance_ids:
            total_amt += line.amount

        if cycle_code_id:
            if self.employee_id and self.employee_id.cash_advance_limit != 0:
                cash_limit = self.employee_id.cash_advance_limit
            elif self.employee_id and self.employee_id.job_id.cash_advance_limit != 0:
                cash_limit = self.employee_id.job_id.cash_advance_limit
            elif self.employee_id and self.employee_id.cash_advance_limit == 0 and self.employee_id.job_id.cash_advance_limit == 0:
                raise ValidationError("Please set Cash Advance Limit")
            
            if ca_cycle_line.cash_advance_cycle_id.limit_type == "monthly":
                akum_amount_before = 0
                akum_amount = total_amt
                cash_advance_obj = self.env["vendor.deposit"].search([("employee_id","=",self.employee_id.id),("cycle_code_id","=",cycle_code_id),('state','not in',['cancelled','rejected','returned'])])
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
        if len(self.cash_advance_ids) > 0:
            self.check_ca_limit()
        travel_approval_matrix_setting = self.env['ir.config_parameter'].sudo().get_param(
            'equip3_hr_travel_extend.travel_approval_matrix'
        )
        if travel_approval_matrix_setting:
            self.write({
                'state': 'confirmed',
                'confirm_date': fields.datetime.now(),
                'confirm_by': self.env.user.id
            })
        else:
            self.write({
                'state': 'approved',
                'confirm_date': fields.datetime.now(),
                'confirm_by': self.env.user.id
            })
        self.approver_mail()
        self.approver_wa_template()
        for line in self.travel_approver_user_ids:
            line.write({'approver_state': 'draft'})
        return

    def custom_menu(self):
        views = [(self.env.ref('bi_employee_travel_managment.view_travel_req_tree').id, 'tree'),
                 (self.env.ref('bi_employee_travel_managment.view_travel_req_form').id, 'form')]
        # search_view_id = self.env.ref("hr_contract.hr_contract_view_search")
        if self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_travel_supervisor') and not self.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_travel_manager'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Employee Travel Request',
                    'res_model': 'travel.request',
                    'target': 'current',
                    'view_mode': 'tree,form',
                    'views': views,
                    'domain': [('employee_id', 'in', employee_ids)],
                    'context': {},
                    'help': """<p class="o_view_nocontent_smiling_face">
                        Create a new Employee Travel Request
                    </p>"""
                    # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                    # 'search_view_id':search_view_id.id,

                }
        elif self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_travel_self_service') and not self.env.user.has_group(
            'equip3_hr_employee_access_right_setting.group_hr_travel_supervisor'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Travel Request',
                'res_model': 'travel.request',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [('employee_id.user_id', '=', self.env.user.id)],
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create a new Employee Travel Request
                </p>""",
                'context': {},
                'views': views,
                # 'search_view_id':search_view_id.id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Travel Request',
                'res_model': 'travel.request',
                'target': 'current',
                'view_mode': 'tree,form',
                'help': """<p class="o_view_nocontent_smiling_face">
                    Create a new Employee Travel Request
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

    def create_cash_advance(self):
        for rec in self:
            if len(rec.cash_advance_ids) == 0:
                raise ValidationError(_('Please fill Cash Advance Lines.'))
            else:
                self.check_ca_limit()
                ICP = self.env['ir.config_parameter'].sudo()
                # employee_tz = rec.employee_id.tz or 'UTC'
                # local = pytz.timezone(employee_tz)
                # req_departure_date = pytz.UTC.localize(rec.req_departure_date).astimezone(local)
                # departure_date_conv = fields.Datetime.from_string(req_departure_date.date()).strftime('%Y-%m-%d')
                # departure_date = datetime.strptime(departure_date_conv, "%Y-%m-%d").date()
                departure_date = rec.req_departure_date
                ca_cycle_line = self.env["hr.cash.advance.cycle.line"].search([
                    ("cycle_start","<=",departure_date),("cycle_end",">=",departure_date)],
                    limit=1)
                if ca_cycle_line:
                    cash_advance_cycle_id = ca_cycle_line.cash_advance_cycle_id
                    cycle_code_id = ca_cycle_line
                else:
                    raise ValidationError("There is no available period for this advance")
                vendor_deposit_id = self.env['vendor.deposit'].create({
                    'travel_id': rec.id,
                    'employee_id': rec.employee_id.id,
                    'advance_date': departure_date,
                    'communication': rec.travel_purpose,
                    'currency_id': rec.currency_id.id,
                    'deposit_reconcile_journal_id': self.env.company.deposit_reconcile_journal_id.id,
                    'deposit_account_id': self.env.company.deposit_account_id.id,
                    'journal_id': self.env.company.journal_id.id,
                    'is_cash_advance': True,
                    'cash_advance_cycle_id': cash_advance_cycle_id.id,
                    'cycle_code_id': cycle_code_id.id,
                    'from_hr': True,
                    'advance_line_ids': [(0, 0, {
                        "name": line["name"],
                        "amount": line["amount"],
                    }) for line in rec.cash_advance_ids],
                })
                vendor_deposit_id.onchange_advance_date()
                vendor_deposit_id.onchange_amount()
                vendor_deposit_id.onchange_approver_user()
                rec.update({'cash_advance_orgin_id': vendor_deposit_id.id,
                            'state': 'cash_advance_submitted',
                            })

    @api.depends('state', 'cash_advance_state')
    def compute_is_return(self):
        for rec in self:
            if rec.state == 'approved':
                rec.is_return_button_visible = True
            elif rec.state == 'cash_advance_submitted' and rec.cash_advance_state == 'post':
                rec.is_return_button_visible = True
            else:
                rec.is_return_button_visible = False

    def action_create_expence(self):
        id_lst = []
        for rec in self:
            if len(rec.expense_ids) == 0:
                raise ValidationError(_('Please fill Expenses Lines.'))
            else:
                for line in rec.expense_ids:
                    id_lst.append(line.id)
                if len(rec.cash_advance_ids) == 0:
                    res = self.env['hr.expense.sheet'].create(
                        {'name': rec.travel_purpose, 'employee_id': rec.employee_id.id, 'travel_expense': True,
                         'expense_line_ids': [(6, 0, id_lst)], 'travel_id': rec.id})
                    res.exp_difference = res.total_amount
                    res.write({'state': 'submit'})
                    res.onchange_amount_sum()
                    # res.activity_update()
                else:
                    res = self.env['hr.expense.sheet'].create(
                        {'name': rec.travel_purpose, 'employee_id': rec.employee_id.id, 'travel_expense': True,
                         'expense_line_ids': [(6, 0, id_lst)], 'expense_advance': True,
                         'cash_advance_number_ids': rec.cash_advance_orgin_id,
                         'cash_advance_amount': rec.cash_advance_orgin_id.amount, 'travel_id': rec.id,
                         'is_ca_travel': True})
                    res.exp_difference = res.total_amount
                    res.write({'state': 'submit'})
                    res.onchange_amount_sum()
                    # res.activity_update()
                rec.expence_sheet_id = res.id
                rec.expence_sheet_id.onchange_amount_sum()
                rec.expence_sheet_id.onchange_approver_user()
                rec.expence_sheet_id.expense_approver_user_ids.update_minimum_app()
                rec.write({'state': 'submitted'})
            return

    @api.onchange('employee_id', 'travel_purpose')
    def onchange_approver_user(self):
        for travel in self:
            if travel.travel_approver_user_ids:
                remove = []
                for line in travel.travel_approver_user_ids:
                    remove.append((2, line.id))
                travel.travel_approver_user_ids = remove
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_travel_extend.travel_type_approval')
            if setting == 'employee_hierarchy':
                travel.travel_approver_user_ids = self.travel_emp_by_hierarchy(travel)
                self.app_list_travel_emp_by_hierarchy()
            if setting == 'approval_matrix':
                self.travel_approval_by_matrix(travel)

    def travel_emp_by_hierarchy(self, travel):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(travel, travel.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, travel, employee_manager, data, approval_ids, seq):
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
                self.get_manager(travel, employee_manager['parent_id'], data, approval_ids, seq)
                break
        return approval_ids

    def app_list_travel_emp_by_hierarchy(self):
        for travel in self:
            app_list = []
            for line in travel.travel_approver_user_ids:
                app_list.append(line.user_ids.id)
            travel.approvers_ids = app_list

    def get_manager_hierarchy(self, travel, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(travel, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def travel_approval_by_matrix(self, travel):
        app_list = []
        approval_matrix = self.env['hr.travel.approval.matrix'].search([('apply_to', '=', 'by_employee')])
        matrix = approval_matrix.filtered(lambda line: travel.employee_id.id in line.employee_ids.ids)
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
                    approvers = self.get_manager_hierarchy(travel, travel.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            travel.approvers_ids = app_list
            travel.travel_approver_user_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.travel.approval.matrix'].search([('apply_to', '=', 'by_job_position')])
            matrix = approval_matrix.filtered(lambda line: travel.job_id.id in line.job_ids.ids)
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
                        approvers = self.get_manager_hierarchy(travel, travel.employee_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                travel.approvers_ids = app_list
                travel.travel_approver_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.travel.approval.matrix'].search([('apply_to', '=', 'by_department')])
                matrix = approval_matrix.filtered(lambda line: travel.department_id.id in line.department_ids.ids)
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
                            approvers = self.get_manager_hierarchy(travel, travel.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    travel.approvers_ids = app_list
                    travel.travel_approver_user_ids = data_approvers

    @api.depends('state', 'employee_id')
    def _compute_can_approve(self):
        for travel in self:
            if travel.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_travel_extend.travel_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_travel_extend.travel_level')
                app_level = int(setting_level)
                current_user = travel.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(travel.travel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(travel.travel_approver_user_ids)
                    if app < app_level and app < a:
                        if current_user in travel.travel_approver_user_ids[app].user_ids:
                            travel.is_approver = True
                        else:
                            travel.is_approver = False
                    else:
                        travel.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(travel.travel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(travel.travel_approver_user_ids)
                    if app < a:
                        for line in travel.travel_approver_user_ids[app]:
                            if current_user in line.user_ids:
                                travel.is_approver = True
                            else:
                                travel.is_approver = False
                    else:
                        travel.is_approver = False

                else:
                    travel.is_approver = False
            else:
                travel.is_approver = False

    @api.depends('state', 'employee_id', 'approved_user_ids')
    def _compute_is_approved(self):
        current_user = self.env.user
        for rec in self:
            if current_user in rec.approved_user_ids or rec.state != 'confirmed':
                rec.is_approved = True
            else:
                rec.is_approved = False

    def action_approve(self):
        sequence_matrix = [data.name for data in self.travel_approver_user_ids]
        sequence_approval = [data.name for data in self.travel_approver_user_ids.filtered(
            lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
        max_seq = max(sequence_matrix)
        min_seq = min(sequence_approval)
        approval = self.travel_approver_user_ids.filtered(
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
                        for user in record.travel_approver_user_ids:
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
                        matrix_line = sorted(record.travel_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.write({'state': 'approved', 'approve_date': fields.datetime.now(),
                                          'approve_by': self.env.user.id})
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
                        for line in record.travel_approver_user_ids:
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

                        matrix_line = sorted(record.travel_approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
                            record.write({'state': 'approved', 'approve_date': fields.datetime.now(),
                                          'approve_by': self.env.user.id})
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
            for user in record.travel_approver_user_ids:
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

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'travel.request.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':True},
            'name': "Confirmation Message",
            'target': 'new',
        }
        
        
    def wizard_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'travel.request.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'context':{'is_approve':False,
                       'default_is_reject':True},
            'name': "Confirmation Message",
            'target': 'new',
        }

    def return_from_trip(self):
        # start_travel = self.req_departure_date.date()
        # while start_travel <= self.req_return_date.date():
        #     self.env['hr.attendance'].create({
        #         'employee_id': self.employee_id.id,
        #         'check_in': False,
        #         'check_out': False,
        #         'start_working_date': start_travel,
        #         'is_created': True,
        #         'attendance_status': 'travel'
        #     })
        #     start_travel += relativedelta(days=1)
        self.write({'state': 'returned'})
        id_lst = []
        for line in self.advance_payment_ids:
            id_lst.append(line.id)
        self.expense_ids = [(6, 0, id_lst)]
        return

    @api.model
    def _cron_create_attendance_travel(self):
        update_attendance_status_travel_limit = int(self.env['ir.config_parameter'].sudo().get_param('equip3_hr_travel_extend.update_attendance_status_travel_limit'))
        limit_days = date.today() - relativedelta(days=update_attendance_status_travel_limit)
        today = date.today()
        travels = self.search([('req_departure_date','>=',limit_days),('state', '=', 'approved')])
        if travels:
            for travel in travels:
                employee_tz = travel.employee_id.tz or 'UTC'
                local = pytz.timezone(employee_tz)
                req_departure_date = pytz.UTC.localize(travel.req_departure_date).astimezone(local)
                departure_date_conv = fields.Datetime.from_string(req_departure_date.date()).strftime('%Y-%m-%d')
                departure_date = datetime.strptime(departure_date_conv, "%Y-%m-%d").date()
                req_return_date = pytz.UTC.localize(travel.req_return_date).astimezone(local)
                return_date_conv = fields.Datetime.from_string(req_return_date.date()).strftime('%Y-%m-%d')
                return_date = datetime.strptime(return_date_conv, "%Y-%m-%d").date()
                if departure_date == today:
                    start_travel = departure_date
                    while start_travel <= return_date:
                        att_exist = self.env['hr.attendance'].search([('employee_id','=',travel.employee_id.id),('start_working_date','=',start_travel),('attendance_status','=','travel')])
                        if not att_exist:
                            self.env['hr.attendance'].create({
                                'employee_id': travel.employee_id.id,
                                'check_in': False,
                                'check_out': False,
                                'start_working_date': start_travel,
                                'is_created': True,
                                'attendance_status': 'travel'
                            })
                        start_travel += relativedelta(days=1)
                elif departure_date < today:
                    if return_date < today:
                        start_travel = departure_date
                        while start_travel <= return_date:
                            att_exist = self.env['hr.attendance'].search([('employee_id','=',travel.employee_id.id),('start_working_date','=',start_travel)],limit=1)
                            if att_exist:
                                att_exist.check_in = False
                                att_exist.check_out = False
                                att_exist.is_created = True
                                att_exist.attendance_status = 'travel'
                    else:
                        start_travel = departure_date
                        while start_travel <= return_date:
                            if start_travel < today:
                                att_exist = self.env['hr.attendance'].search([('employee_id','=',travel.employee_id.id),('start_working_date','=',start_travel)],limit=1)
                                if att_exist:
                                    att_exist.check_in = False
                                    att_exist.check_out = False
                                    att_exist.is_created = True
                                    att_exist.attendance_status = 'travel'
                            else:
                                att_exist = self.env['hr.attendance'].search([('employee_id','=',travel.employee_id.id),('start_working_date','=',start_travel),('attendance_status','=','travel')])
                                if not att_exist:
                                    self.env['hr.attendance'].create({
                                        'employee_id': travel.employee_id.id,
                                        'check_in': False,
                                        'check_out': False,
                                        'start_working_date': start_travel,
                                        'is_created': True,
                                        'attendance_status': 'travel'
                                    })
                            start_travel += relativedelta(days=1)
                self._cr.commit()

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise Warning("You cannot delete a Travel Request which is in Approved state.")
            return super(HrTravelRequest, rec).unlink()

    # Emails
    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'bi_employee_travel_managment', 'menu_travel_request_approve')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'bi_employee_travel_managment', 'action_travel_req_hr')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=travel.request&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.travel_approver_user_ids:
                matrix_line = sorted(rec.travel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.travel_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_travel_extend',
                            'email_template_travel_request_approval')[1]
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
            if rec.travel_approver_user_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_travel_extend',
                        'email_template_travel_request_approved')[1]
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
            if rec.travel_approver_user_ids:
                try:
                    template_id = ir_model_data.get_object_reference(
                        'equip3_hr_travel_extend',
                        'email_template_travel_request_rejection')[1]
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
            template = self.env.ref('equip3_hr_travel_extend.travel_request_wa_template')
            wa_sender = waParam()
            if template:
                if self.travel_approver_user_ids:
                    url = self.get_url(self)
                    matrix_line = sorted(self.travel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = self.travel_approver_user_ids[len(matrix_line)]
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
            template = self.env.ref('equip3_hr_travel_extend.travel_approved_wa_template')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if self.travel_approver_user_ids:
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
            template = self.env.ref('equip3_hr_travel_extend.travel_rejected_wa_template')
            wa_sender = waParam()
            if template:
                if self.travel_approver_user_ids:
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
        travel_confirmed = self.search([('state', '=', 'confirmed')])
        for rec in travel_confirmed:
            if rec.travel_approver_user_ids:
                matrix_line = sorted(rec.travel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.travel_approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_travel_extend',
                            'email_template_travel_request_approval')[1]
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
                        query_statement = """UPDATE travel_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE travel_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        travel_confirmed = self.search([('state', '=', 'confirmed')])
        for rec in travel_confirmed:
            if rec.travel_approver_user_ids:
                matrix_line = sorted(rec.travel_approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.travel_approver_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_travel_extend',
                                    'email_template_travel_request_approval')[1]
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

class HrTravelVendorDeposit(models.Model):
    _name = 'travel.vendor.deposit'

    travel_cash_id = fields.Many2one('travel.request', string='Travel Id')
    name = fields.Char(string="Description", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", related='travel_cash_id.employee_id')
    amount = fields.Float(string="Amount", required=True)
    state = fields.Selection(string="Status", readonly=True, related='travel_cash_id.cash_advance_state')


class HrTravelCashAdvance(models.Model):
    _inherit = 'vendor.deposit'

    travel_id = fields.Many2one('travel.request', string='Travel')

    def action_confirm(self):
        for rec in self:
            if rec.travel_id.cash_advance_ids:
                remove = []
                for line in rec.travel_id.cash_advance_ids:
                    remove.append((2, line.id))
                rec.travel_id.cash_advance_ids = remove
            if rec.travel_id:
                rec.travel_id.update({'state': 'cash_advance_submitted',
                                      'cash_advance_orgin_id': rec.id})
                cash_ca_lines = []
                for ca_lines in rec.advance_line_ids:
                    cash_ca_lines.append((0, 0, {'name': ca_lines.name,
                                                 'amount': ca_lines.amount}))
                rec.travel_id.cash_advance_ids = cash_ca_lines
            result = super(HrTravelCashAdvance, self).action_confirm()
            return result

    @api.onchange('travel_id')
    def onchange_trvel_ca_lines(self):
        for rec in self:
            if rec.advance_line_ids:
                remove = []
                for line in rec.advance_line_ids:
                    remove.append((2, line.id))
                rec.advance_line_ids = remove
            rec.communication = rec.travel_id.travel_purpose
            rec.update({'communication': rec.travel_id.travel_purpose})
            travel_ca_lines = []
            for travel_lines in rec.travel_id.cash_advance_ids:
                travel_ca_lines.append((0, 0, {'name': travel_lines.name,
                                               'amount': travel_lines.amount}))
            rec.advance_line_ids = travel_ca_lines


class HrExpenseSheet(models.Model):
    _inherit = 'hr.expense.sheet'

    travel_id = fields.Many2one('travel.request', string='Travel',
                                domain=lambda self: "[('employee_id', '=', employee_id), ('state', '=', 'returned')]")
    is_ca_travel = fields.Boolean('Is CA Travel', default=False)
    is_ca_number_readonly = fields.Boolean('CA Number Readonly', compute='compute_is_ca_number', default=False)
    is_exp_line_readonly = fields.Boolean('Is Expense Line', default=False)

    @api.depends('travel_id', 'cash_advance_amount')
    def compute_is_ca_number(self):
        for rec in self:
            if rec.is_ca_travel:
                rec.is_ca_number_readonly = True
            elif rec.state != 'draft':
                rec.is_ca_number_readonly = True
            else:
                rec.is_ca_number_readonly = False

    @api.onchange('travel_id', 'cash_advance_number_ids')
    def onchange_travel_id(self):
        for rec in self:
            if rec.travel_id and rec.travel_id.cash_advance_orgin_id:
                ca_orgin = rec.travel_id.cash_advance_orgin_id
                rec.expense_advance = True
                rec.cash_advance_number_ids = ca_orgin
                rec.cash_advance_amount = ca_orgin.amount
            elif not rec.travel_id:
                rec.get_ca_remaining_amount()
            else:
                rec.expense_advance = False
                rec.cash_advance_number_ids = False
                rec.cash_advance_amount = False

    def action_submit_sheet(self):
        for rec in self:
            if rec.travel_id and rec.travel_id.expense_ids:
                remove = []
                for line in rec.travel_id.expense_ids:
                    remove.append((2, line.id))
                rec.travel_id.expense_ids = remove
            if rec.travel_id:
                rec.travel_id.update({'expence_sheet_id': rec.id,
                                      'state': 'submitted'})
                expense_lines = []
                for exp_expense_lines in rec.expense_line_ids:
                    expense_lines.append((0, 0, {'date': exp_expense_lines.date,
                                                 'name': exp_expense_lines.name,
                                                 'employee_id': exp_expense_lines.employee_id.id,
                                                 'analytic_account_id': exp_expense_lines.analytic_account_id.id,
                                                 'tax_ids': [(6, 0, exp_expense_lines.tax_ids.ids)],
                                                 'total_amount': exp_expense_lines.total_amount,
                                                 'state': exp_expense_lines.state,
                                                 'unit_amount': exp_expense_lines.unit_amount}))
                rec.travel_id.expense_ids = expense_lines
            result = super(HrExpenseSheet, self).action_submit_sheet()
            return result

    @api.onchange('travel_id')
    def onchange_trvel_exp_lines(self):
        for rec in self:
            if rec.expense_line_ids:
                remove = []
                for line in rec.expense_line_ids:
                    remove.append((2, line.id))
                rec.expense_line_ids = remove
            expense_ca_lines = []
            for travel_expense_lines in rec.travel_id.expense_ids:
                expense_ca_lines.append((0, 0, {'date': travel_expense_lines.date,
                                                'name': travel_expense_lines.name,
                                                'employee_id': travel_expense_lines.employee_id.id,
                                                'analytic_account_id': travel_expense_lines.analytic_account_id.id,
                                                'tax_ids': [(6, 0, travel_expense_lines.tax_ids.ids)],
                                                'total_amount': travel_expense_lines.total_amount,
                                                'state': travel_expense_lines.state,
                                                'unit_amount': travel_expense_lines.unit_amount}))
            rec.expense_line_ids = expense_ca_lines
            if len(rec.travel_id.expense_ids) == 0:
                rec.is_exp_line_readonly = False
            else:
                rec.is_exp_line_readonly = True


class TravelApproverUser(models.Model):
    _name = 'travel.approver.user'

    emp_travel_id = fields.Many2one('travel.request', string="Employee Travel Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'emp_travel_user_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    #Auto Follow email
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'travel_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string="Parent Status", related='emp_travel_id.state')

    @api.depends('emp_travel_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.emp_travel_id.travel_approver_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()

    def update_minimum_app(self):
        for rec in self:
            if len (rec.user_ids) < rec.minimum_approver and rec.emp_travel_id.state == 'draft':
                rec.minimum_approver = len(rec.user_ids)
            if not rec.matrix_user_ids and rec.emp_travel_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids