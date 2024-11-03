from odoo import api, fields, models, _
from datetime import date, timedelta, datetime
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
from odoo.tools.float_utils import float_round
import requests
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from lxml import etree
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

headers = {'content-type': 'application/json'}

class HrLeave(models.Model):
    _inherit = 'hr.leave'
    _description = "Hr Leave"
    _rec_name = "seq_name"

    def custom_menu(self):
        search_view_id = self.env.ref("hr_holidays.hr_leave_view_search_manager")
        if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_responsible') and not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            leave_ids = [data.id for data in self.search([('approvers_ids','in',self.env.user.id)])]
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'All Leaves',
                'res_model': 'hr.leave',
                'target': 'current',
                'view_mode': 'tree,kanban,form,calendar,activity,pivot',
                'domain': ['|',('employee_id','in',employee_ids),('id','in',leave_ids)],
                'context': {'hide_employee_name': 1,'create':1},
                'help': """<p class="o_view_nocontent_smiling_face">
                Meet the time off dashboard.
            </p>
            <p>
                A great way to keep track on employee’s PTOs, sick days, and approval status.
            </p>""",
            'search_view_id':search_view_id.id,

            }

        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'All Leaves',
                'res_model': 'hr.leave',
                'target': 'current',
                'view_mode': 'tree,kanban,form,calendar,activity,pivot',
                'domain': [],
                'help': """<p class="o_view_nocontent_smiling_face">
                    Meet the time off dashboard.
                </p>
                <p>
                    A great way to keep track on employee’s PTOs, sick days, and approval status.
                </p>
                </p>""",
                'context': {'hide_employee_name': 1,'create':1},
                'search_view_id':search_view_id.id,
            }

    @api.onchange('employee_id')
    def _onchange_employee__id(self):
        res = {}
        balance_list = []
        if self.holiday_type == 'employee':
            for leave_balance in self.env['hr.leave.balance'].search(
                    [('employee_id', '=', self.employee_id.id),
                     ('active', '=', True)]):
                balance_list.append(leave_balance.holiday_status_id.id)
            res['domain'] = {'holiday_status_id': [('id', 'in', balance_list)]}
        else:
            res['domain'] = {'holiday_status_id': []}
        return res
    
    @api.onchange('holiday_status_id')
    def _onchange_holiday_status_id(self):
        for data in self:
            if data.holiday_status_id.request_unit  == 'half_day':
                data.request_unit_half = True
            else:
                data.request_unit_half = False
        

    @api.model
    def get_state_selection(self):
        return [('draft', 'To Submit'),
                ('confirm', 'To Approve'),
                ('refuse', 'Rejected'),
                ('validate1', 'Second Approval'),
                ('validate', 'Approved'),
                ('cancel', 'Cancelled')]

    @api.model
    def _department_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    @api.model
    def _multi_company_domain(self):
        context = self.env.context
        if context.get('allowed_company_ids'):
            return [('id','in', self.env.context.get('allowed_company_ids'))]
        else:
            return [('id','=', self.env.company.id)]

    seq_name = fields.Char('Name', default='New', copy=False)
    request_unit = fields.Selection([
        ('day', 'Day'), ('half_day', 'Half Day'), ('hour', 'Hours')],
        default='day', string='Take Leave in', required=True, tracking=True, 
        help='\tDay : Will only able to be requested in units of Days; '
             '\tHalf Day : Will able to be requested on a Half Day schema; '
             '\tHours : Will able to be requested on a specific Hours ',related='holiday_status_id.request_unit',store=True)
    department_id = fields.Many2one(domain=_department_company_domain)
    mode_company_id = fields.Many2one(domain=_multi_company_domain)
    state = fields.Selection(get_state_selection,
        string='Status', compute='_compute_state', store=True, tracking=True, copy=False, readonly=False, default='draft',
        help="The status is set to 'To Submit', when a time off request is created." +
             "\nThe status is 'To Approve', when time off request is confirmed by user." +
             "\nThe status is 'Refused', when time off request is refused by manager." +
             "\nThe status is 'Approved', when time off request is approved by manager.")

    feedback_parent = fields.Text(string='Parent Feedback', default='')
    leave_type_urgent_leave = fields.Boolean(related="holiday_status_id.urgent_leave", string="Urgent Leave Type")
    is_urgent = fields.Boolean(string="Urgent Leave", default=False)
    is_required = fields.Boolean(string="Required Attachment", related="holiday_status_id.is_required")
    attachment = fields.Binary('Attachment')
    attachment_name = fields.Char('Attachment Name')
    holiday_status_id = fields.Many2one("hr.leave.type", string="Leave Type", required=True, readonly=False,
                                        states={'cancel': [('readonly', True)], 'refuse': [('readonly', True)],
                                                'validate1': [('readonly', True)],
                                                'validate': [('readonly', True)]}, domain=[])
    cancel_id = fields.Many2one('hr.leave.cancelation', string='Leave cancel', compute='_compute_cancel')
    approvers_ids = fields.Many2many('res.users', 'approver_users_leave_rel', string='Approvers')
    approved_user = fields.Text(string="Approved User", tracking=True)
    can_approve = fields.Boolean(compute_sudo=True)
    is_approver = fields.Boolean(string="Is Approver", compute="_compute_can_approve", compute_sudo=True)
    filter_approver = fields.Boolean(string="Filter Approver", compute="_compute_can_approve", store=True)
    approver_user_ids = fields.One2many('leave.approver.user', 'leave_id', string='Approver')
    approved_user_ids = fields.Many2many('res.users', string='Approved User')
    next_approver_ids = fields.Many2many('res.users', 'next_approver_users_leave_rel', string='Next Approvers', compute="_compute_next_approver", store=True)
    line_item_visible = fields.Boolean(string="Line item visible", compute="_compute_line_items")
    leave_count_ids = fields.One2many('hr.leave.line', 'leave_id', string='Leave Count')
    leave_balance_id = fields.Many2one('hr.leave.balance', string='Leave Balance')
    current_period = fields.Integer('Current Period', copy=False, store=True, compute='compute_current_period')
    current_year = fields.Integer('Current Year', store=True, compute='compute_current_period')
    is_readonly_mode = fields.Boolean(compute='_compute_readonly_mode')
    is_invisible_mode = fields.Boolean(compute='_compute_is_invisible_mode')
    domain_employee_ids = fields.Many2many('hr.employee', string="Employee Domain", compute='_compute_employee_ids')
    is_refused_by_leave_cancel_form = fields.Boolean('Refused by Leave Cancel Form', default=False)
    hide_cancel = fields.Boolean('Hide Button Cancel', compute="_compute_hide_cancel")
    attachment_notes = fields.Text('Attachment Notes', related="holiday_status_id.attachment_notes")
    leave_balance_value = fields.Char('Leave Balance')
    request_back_date = fields.Boolean("Backdate Leave")
    leave_type_back_date = fields.Boolean(compute='_compute_leave_type_back_date', store=True, string="Past Date Leave Type")


    @api.depends_context('uid')
    def _compute_description(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
        is_officer = self.user_has_groups('hr_holidays.group_hr_holidays_user')
        for leave in self:
            if is_officer or leave.user_id == self.env.user or leave.employee_id.leave_manager_id == self.env.user:
                leave.name = leave.sudo().private_name
            else:
                leave.name = leave.sudo().private_name



    @api.depends('request_unit_half')
    def _compute_number_of_days(self):
        for holiday in self:
            if holiday.request_unit_half:
                holiday.number_of_days = 0.5

    @api.onchange('holiday_status_id')
    def onchange_leave_type(self):
        for holiday in self:
            holiday.request_back_date = False

    @api.depends('holiday_status_id')
    def _compute_leave_type_back_date(self):
        for holiday in self:
            if holiday.holiday_status_id.allow_past_date:
                holiday.leave_type_back_date = True
            else:
                holiday.leave_type_back_date = False

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrLeave, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.context.get('is_approve'):
            if self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
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

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return


    def no_validation(self):
        if self.holiday_status_id.leave_validation_type == 'no_validation':
            self.write({'state': 'draft'})
            if self.holiday_status_id.set_by == 'duration':
                remaining_leaves = self.number_of_days
            else:
                remaining_leaves = 1
            self.leave_balance_id.used = self.leave_balance_id.used - remaining_leaves
            for count in self.leave_count_ids:
                if count.count_id.count < 0:
                    var_count = count.count_id.count
                else:
                    var_count = 0
                count.count_id.count = count.count_id.count - var_count + count.count
            self.leave_count_ids.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        """ Override to avoid automatic logging of creation """
        if not self._context.get('leave_fast_create'):
            leave_types = self.env['hr.leave.type'].browse(
                [values.get('holiday_status_id') for values in vals_list if values.get('holiday_status_id')])
            mapped_validation_type = {leave_type.id: leave_type.leave_validation_type for leave_type in leave_types}

            for values in vals_list:
                employee_id = values.get('employee_id', False)
                leave_type_id = values.get('holiday_status_id')
                # Handle automatic department_id
                if not values.get('department_id'):
                    values.update({'department_id': self.env['hr.employee'].browse(employee_id).department_id.id})

                # Handle no_validation
                if mapped_validation_type[leave_type_id] == 'no_validation':
                    values.update({'state': 'confirm'})

                if 'state' not in values:
                    # To mimic the behavior of compute_state that was always triggered, as the field was readonly
                    values['state'] = 'confirm' if mapped_validation_type[leave_type_id] != 'no_validation' else 'draft'

                # Handle double validation
                if mapped_validation_type[leave_type_id] == 'both':
                    self._check_double_validation_rules(employee_id, values.get('state', False))

        holidays = super(HrLeave, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        holidays.no_validation()
        for holiday in holidays:
            if not self._context.get('leave_fast_create'):
                # Everything that is done here must be done using sudo because we might
                # have different create and write rights
                # eg : holidays_user can create a leave request with validation_type = 'manager' for someone else
                # but they can only write on it if they are leave_manager_id
                holiday_sudo = holiday.sudo()
                holiday_sudo.add_follower(employee_id)
                if holiday.validation_type == 'manager':
                    holiday_sudo.message_subscribe(partner_ids=holiday.employee_id.leave_manager_id.partner_id.ids)
                if holiday.validation_type == 'no_validation':
                    print('----create')
                    # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
                    # holiday_sudo.action_validate()
                    holiday_sudo.message_subscribe(partner_ids=[holiday._get_responsible_for_approval().partner_id.id])
                    # holiday_sudo.message_post(body=_("The time off has been automatically approved"),
                    #                           subtype_xmlid="mail.mt_comment")  # Message from OdooBot (sudo)
                # elif not self._context.get('import_file'):
                #     holiday_sudo.activity_update()
        return holidays

    @api.depends('holiday_type')
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

    @api.depends('holiday_type')
    def _compute_readonly_mode(self):
        for record in self:
            if self.env.user.has_group(
                    'equip3_hr_employee_access_right_setting.group_responsible') and not self.env.user.has_group(
                    'hr_holidays.group_hr_holidays_user'):
                record.is_readonly_mode = True
            else:
                record.is_readonly_mode = False

    @api.depends('holiday_type')
    def _compute_is_invisible_mode(self):
        for record in self:
            if self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
                record.is_invisible_mode = True
            else:
                record.is_invisible_mode = False

    @api.depends('holiday_status_id')
    def _compute_state(self):
        for holiday in self:
            if self.env.context.get('unlink') and holiday.state == 'draft':
                # Otherwise the record in draft with validation_type in (hr, manager, both) will be set to confirm
                # and a simple internal user will not be able to delete his own draft record
                holiday.state = 'draft'
            else:
                holiday.state = 'draft' if holiday.validation_type != 'no_validation' else 'draft'

    @api.depends('employee_id', 'request_date_to')
    def compute_current_period(self):
        for leave in self:
            if leave.request_date_to:
                leave.current_period = leave.request_date_to.year
                leave.current_year = date.today().year
            else:
                leave.current_period = 0
                leave.current_year = 0

    @api.depends('approver_user_ids','approver_user_ids.employee_id','approver_user_ids.approved_employee_ids')
    def _compute_next_approver(self):
        for record in self:
            if record.approver_user_ids:
                sequence = [data.name for data in record.approver_user_ids.filtered(
                    lambda line: len(line.approved_employee_ids.ids) != line.minimum_approver)]
                if sequence:
                    minimum_sequence = min(sequence)
                    approve_user = record.approver_user_ids.filtered(lambda line: line.name == minimum_sequence)

                    if approve_user:
                        next_approver = []
                        for approver in approve_user:
                            for rec in approver.employee_id:
                                if rec.id not in approver.approved_employee_ids.ids:
                                    next_approver.append(rec.id)
                        record.next_approver_ids = next_approver
                    else:
                        record.next_approver_ids = False
                else:
                    record.next_approver_ids = False
            else:
                record.next_approver_ids = False



    @api.model
    def _cron_next_approvers(self):
        leave = self.env['hr.leave'].search([('state','in',['draft','confirm'])])
        if leave:
            for record in leave:
                if record.approver_user_ids:
                    sequence = [data.name for data in record.approver_user_ids.filtered(
                        lambda line: len(line.approved_employee_ids.ids) != line.minimum_approver)]
                    if sequence:
                        minimum_sequence = min(sequence)
                        approve_user = record.approver_user_ids.filtered(lambda line: line.name == minimum_sequence)

                        if approve_user:
                            next_approver = []
                            for approver in approve_user:
                                for rec in approver.employee_id:
                                    if rec.id not in approver.approved_employee_ids.ids and rec.id not in record.approved_user_ids.ids:
                                        next_approver.append(rec.id)
                            record.next_approver_ids = next_approver
                        else:
                            record.next_approver_ids = False
                    else:
                        record.next_approver_ids = False
                else:
                    record.next_approver_ids = False

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve(self):
        for holiday in self:
            # try:
            #     if holiday.state == 'confirm' and holiday.validation_type == 'both':
            #         holiday._check_approval_update('validate1')
            #     else:
            #         holiday._check_approval_update('validate')
            # except (AccessError, UserError):
            #     holiday.can_approve = False
            # else:
            #     holiday.can_approve = True
            if holiday.approvers_ids:
                if holiday.holiday_status_id.leave_validation_type == 'by_employee_hierarchy':
                    current_user = holiday.env.user
                    matrix_line = sorted(holiday.approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(holiday.approver_user_ids)
                    if app < holiday.holiday_status_id.approval_level and app < a:
                        if current_user in holiday.approver_user_ids[len(matrix_line)].employee_id:
                            holiday.is_approver = True
                            holiday.can_approve = True
                            holiday.filter_approver = True
                        else:
                            holiday.is_approver = False
                            holiday.can_approve = False
                            holiday.filter_approver = False
                    else:
                        holiday.is_approver = False
                        holiday.can_approve = False
                        holiday.filter_approver = False
                elif holiday.holiday_status_id.leave_validation_type == 'by_approval_matrix':
                    current_user = holiday.env.user
                    matrix_line = sorted(holiday.approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(holiday.approver_user_ids)
                    if app < a:
                        for line in holiday.approver_user_ids[app]:
                            if current_user in line.approved_employee_ids:
                                holiday.is_approver = False
                                holiday.can_approve = False
                                holiday.filter_approver = False
                            elif current_user in line.employee_id:
                                holiday.is_approver = True
                                holiday.can_approve = True
                                holiday.filter_approver = True
                            else:
                                holiday.is_approver = False
                                holiday.can_approve = False
                                holiday.filter_approver = False
                    else:
                        holiday.is_approver = False
                        holiday.can_approve = False
                        holiday.filter_approver = False
                elif holiday.holiday_status_id.leave_validation_type == 'hr':
                    current_user = holiday.env.user
                    if current_user in holiday.approvers_ids:
                        holiday.is_approver = True
                        holiday.can_approve = True
                        holiday.filter_approver = True
                    else:
                        holiday.is_approver = False
                        holiday.can_approve = False
                        holiday.filter_approver = False
                elif holiday.holiday_status_id.leave_validation_type == 'manager':
                    current_user = holiday.env.user
                    if current_user in holiday.approvers_ids:
                        holiday.is_approver = True
                        holiday.can_approve = True
                        holiday.filter_approver = True
                    else:
                        holiday.is_approver = False
                        holiday.can_approve = False
                        holiday.filter_approver = False
                elif holiday.holiday_status_id.leave_validation_type == 'both':
                    current_user = holiday.env.user
                    matrix_line = sorted(holiday.approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(holiday.approver_user_ids)
                    if app < 2 and app < a:
                        if current_user in holiday.approver_user_ids[len(matrix_line)].employee_id:
                            holiday.is_approver = True
                            holiday.can_approve = True
                            holiday.filter_approver = True
                        else:
                            holiday.is_approver = False
                            holiday.can_approve = False
                            holiday.filter_approver = False
                    else:
                        holiday.is_approver = False
                        holiday.can_approve = False
                        holiday.filter_approver = False
                else:
                    holiday.is_approver = False
                    holiday.can_approve = False
                    holiday.filter_approver = False
            else:
                holiday.is_approver = False
                holiday.can_approve = False
                holiday.filter_approver = False

    # @api.depends('employee_id', 'holiday_status_id', 'department_id')
    def app_list_leave_emp(self):
        for leave in self:
            app_list = []
            if leave.employee_id and leave.holiday_status_id.leave_validation_type == 'by_employee_hierarchy':
                app_level = leave.holiday_status_id.approval_level
                employee = leave.employee_id
                for i in range(app_level):
                    emp = self.env['hr.employee'].search([('id', '=', employee.id)])
                    if emp:
                        parent = self.env['hr.employee'].search([('id', '=', emp.parent_id.id)])
                        employee = parent
                        if employee:
                            app_list.append(employee.user_id.id)
            if leave.employee_id and leave.holiday_status_id.leave_validation_type == 'hr':
                responsible = leave.holiday_status_id.responsible_id
                # emp_responsible = self.env['hr.employee'].search([('user_id', '=', responsible.id)],
                #                                                  limit=1)
                if responsible:
                    app_list.append(responsible.id)
            if leave.employee_id and leave.holiday_status_id.leave_validation_type == 'manager':
                emp_manager = leave.employee_id.parent_id.user_id
                if emp_manager:
                    app_list.append(emp_manager.id)
            if leave.employee_id and leave.holiday_status_id.leave_validation_type == 'both':
                both_emp_manager = leave.employee_id.parent_id.user_id
                both_responsible = leave.holiday_status_id.responsible_id
                # both_emp_responsible = self.env['hr.employee'].search([('user_id', '=', both_responsible.id)],
                #                                                       limit=1)
                if both_emp_manager:
                    app_list.append(both_emp_manager.id)
                if both_responsible:
                    app_list.append(both_responsible.id)
            # if leave.holiday_status_id.leave_validation_type == 'by_approval_matrix':
            #     employee_matrix = self.env['hr.leave.approval'].search([('employee_ids', 'in', leave.employee_id.id)],
            #                                                            limit=1)
            #     job_position_matrix = self.env['hr.leave.approval'].search(
            #         [('job_ids', 'in', leave.employee_id.job_id.id)], limit=1)
            #     department_matrix = self.env['hr.leave.approval'].search(
            #         [('department_ids', 'in', leave.employee_id.department_id.id)], limit=1)
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
            leave.approvers_ids = app_list

    def get_manager_hierarchy(self, leave, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(leave, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    @api.onchange('holiday_status_id', 'employee_id', 'department_id', )
    def onchange_approver_user(self):
        for leave in self:
            if leave.approver_user_ids:
                leave.approver_user_ids.unlink()
                leave.approved_user_ids = False
            if leave.employee_id and leave.holiday_status_id.leave_validation_type == 'by_employee_hierarchy':
                app_level = leave.holiday_status_id.approval_level
                employee = leave.employee_id
                for i in range(app_level):
                    emp = self.env['hr.employee'].search([('id', '=', employee.id)])
                    if emp:
                        parent = self.env['hr.employee'].search([('id', '=', emp.parent_id.id)])
                        employee = parent
                        if employee:
                            vals = [(0, 0, {'employee_id': employee.user_id.ids, 'leave_id': self.id})]
                            leave.approver_user_ids = vals
            elif leave.employee_id and leave.holiday_status_id.leave_validation_type == 'hr':
                responsible = leave.holiday_status_id.responsible_id
                # emp_responsible = self.env['hr.employee'].search([('user_id', '=', responsible.id)],
                #                                                  limit=1)
                hr_vals = [(0, 0, {'employee_id': responsible, 'leave_id': self.id})]
                leave.approver_user_ids = hr_vals
            elif leave.employee_id and leave.holiday_status_id.leave_validation_type == 'manager':
                emp_manager = leave.employee_id.parent_id
                manager_vals = [(0, 0, {'employee_id': emp_manager.user_id.ids, 'leave_id': self.id})]
                leave.approver_user_ids = manager_vals
            elif leave.employee_id and leave.holiday_status_id.leave_validation_type == 'both':
                emp_manager = leave.employee_id.parent_id
                both_manager_vals = [(0, 0, {'employee_id': emp_manager.user_id.ids, 'leave_id': self.id})]
                leave.approver_user_ids = both_manager_vals
                responsible = leave.holiday_status_id.responsible_id
                # emp_responsible = self.env['hr.employee'].search([('user_id', '=', responsible.id)],
                #                                                  limit=1)
                both_hr_vals = [(0, 0, {'employee_id': responsible, 'leave_id': self.id})]
                leave.approver_user_ids = both_hr_vals
            elif leave.holiday_status_id.leave_validation_type == 'by_approval_matrix':
                app_list = []
                leave_type_matrix = self.env['hr.leave.approval'].search(
                    [('mode_type', '=', 'leave_type'), ('leave_type_ids', 'in', leave.holiday_status_id.id), (
                    'applicable_to', 'in', ['leave_request', 'leave_and_allocation_request'])], limit=1)
                employee_matrix = self.env['hr.leave.approval'].search(
                    [('mode_type', '=', 'employee'), ('employee_ids', 'in', leave.employee_id.id), (
                    'applicable_to', 'in', ['leave_request', 'leave_and_allocation_request'])], limit=1)
                job_position_matrix = self.env['hr.leave.approval'].search(
                    [('mode_type', '=', 'job_position'), ('job_ids', 'in', leave.employee_id.job_id.id), (
                    'applicable_to', 'in', ['leave_request', 'leave_and_allocation_request'])], limit=1)
                department_matrix = self.env['hr.leave.approval'].search(
                    [('mode_type', '=', 'department'), ('department_ids', 'in', leave.employee_id.department_id.id), (
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
                            approvers = self.get_manager_hierarchy(leave, leave.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'employee_id': [(4, approver)]}))
                                app_list.append(approver)
                    leave.approvers_ids = app_list
                    leave.approver_user_ids = data_approvers
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
                            approvers = self.get_manager_hierarchy(leave, leave.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'employee_id': [(4, approver)]}))
                                app_list.append(approver)
                    leave.approvers_ids = app_list
                    leave.approver_user_ids = data_approvers
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
                            approvers = self.get_manager_hierarchy(leave, leave.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'employee_id': [(4, approver)]}))
                                app_list.append(approver)
                    leave.approvers_ids = app_list
                    leave.approver_user_ids = data_approvers
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
                            approvers = self.get_manager_hierarchy(leave, leave.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'employee_id': [(4, approver)]}))
                                app_list.append(approver)
                    leave.approvers_ids = app_list
                    leave.approver_user_ids = data_approvers
            else:
                leave.approver_user_ids.unlink()
                leave.approved_user_ids = False
        self.app_list_leave_emp()

    @api.constrains('state', 'number_of_days', 'holiday_status_id')
    def _check_holidays(self):
        mapped_days = self.mapped('holiday_status_id').get_employees_days(self.mapped('employee_id').ids)
        for holiday in self:
            if holiday.holiday_type != 'employee' or not holiday.employee_id or holiday.holiday_status_id.allocation_type == 'no':
                continue
            leave_days = mapped_days[holiday.employee_id.id][holiday.holiday_status_id.id]
            # if float_compare(leave_days['remaining_leaves'], 0, precision_digits=2) == -1 or float_compare(
            #         leave_days['virtual_remaining_leaves'], 0, precision_digits=2) == -1:
            #     raise ValidationError(_('The number of remaining time off is not sufficient for this time off type.\n'
            #                             'Please also check the time off waiting for validation.'))

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'hr_holidays', 'menu_open_department_leave_approve')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'hr_holidays', 'hr_leave_action_action_approve_department')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.holidays&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        send_by_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_email')
        if send_by_email:
            ir_model_data = self.env['ir.model.data']
            for rec in self:
                if rec.approver_user_ids:
                    matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                    approver = rec.approver_user_ids[len(matrix_line)]
                    for user in approver.employee_id:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_holidays_extend',
                                'email_template_leave_approval_request')[1]
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
                            ctx.update(
                                {'date_to': fields.Datetime.from_string(self.request_date_to).strftime('%d/%m/%Y')})
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                force_send=True)
                    break

    def approved_mail(self):
        send_by_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_email')
        if send_by_email:
            ir_model_data = self.env['ir.model.data']
            for rec in self:
                if rec.approver_user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_holidays_extend',
                            'email_template_edi_leave_request_approved')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(self)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': self.employee_id.user_id.email,
                        'url': url,
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
                        

    def reject_mail(self):
        send_by_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_email')
        if send_by_email:
            ir_model_data = self.env['ir.model.data']
            for rec in self:
                if rec.approver_user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_holidays_extend',
                            'email_template_edi_leave_request_reject')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    ctx.pop('default_state', None)
                    url = self.get_url(self)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': self.employee_id.user_id.email,
                        'url': url,
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
                        

    def approver_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_wa')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if send_by_wa:
            # connector = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.connector_id')
            # if connector:
            #     connector_id = self.env['acrux.chat.connector'].search([('id', '=', connector)])
            #     if connector_id.ca_status:
            template = self.env.ref('equip3_hr_holidays_extend.leave_approver_wa_template')
            wa_sender = waParam()
            # url = self.get_url(self)
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
                            string_test = string_test.replace("${name}", self.seq_name)
                        # if "${survey_url}" in string_test:
                        #     string_test = string_test.replace("${survey_url}", url)
                        if "${br}" in string_test:
                            string_test = string_test.replace("${br}", f"\n")
                        if "${url}" in string_test:
                            string_test = string_test.replace("${url}", f"{base_url}/leave/{self.id}")
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
        #                         # connector_id.ca_request('post', 'sendMessage', param)

    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_wa')
        if send_by_wa:
            # connector = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.connector_id')
            # if connector:
            #     connector_id = self.env['acrux.chat.connector'].search([('id', '=', connector)])
            #     if connector_id.ca_status:
            template = self.env.ref('equip3_hr_holidays_extend.leave_approved_wa_template')
            wa_sender = waParam()
            # url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
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
                        string_test = string_test.replace("${name}", self.seq_name)
                    # if "${survey_url}" in string_test:
                    #     string_test = string_test.replace("${survey_url}", url)
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
            template = self.env.ref('equip3_hr_holidays_extend.leave_rejected_wa_template')
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
                        string_test = string_test.replace("${name}", self.seq_name)
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
                            # connector_id.ca_request('post', 'sendMessage', param)

    def get_auto_follow_up_approver_wa_template(self, rec):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_wa')
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        wa_sender = waParam()
        if send_by_wa:
            template = self.env.ref('equip3_hr_holidays_extend.leave_approver_wa_template')
            if template:
                # leave_to_approve = self.search([('state', '=', 'confirm')])
                # for rec in leave_to_approve:
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
                            string_test = string_test.replace("${name}", rec.seq_name)
                        if "${br}" in string_test:
                            string_test = string_test.replace("${br}", f"\n")
                        if "${url}" in string_test:
                            string_test = string_test.replace("${url}", f"{base_url}/leave/{rec.id}")
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
        number_of_repetitions_leave = int(
            self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.number_of_repetitions_leave'))
        leave_to_approve = self.search([('state', '=', 'confirm')])
        for rec in leave_to_approve:
            if rec.approver_user_ids:
                matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approver_user_ids[len(matrix_line)]
                for user in approver.employee_id:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_holidays_extend',
                            'email_template_leave_approval_request')[1]
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
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_leave - 1
                        query_statement = """UPDATE leave_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                        self.get_auto_follow_up_approver_wa_template(rec)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE leave_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
                            self.get_auto_follow_up_approver_wa_template(rec)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        leave_to_approve = self.search([('state', '=', 'confirm')])
        for rec in leave_to_approve:
            if rec.approver_user_ids:
                matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approver_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_holidays_extend',
                                    'email_template_leave_approval_request')[1]
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
                            approver.update({
                                'employee_id': [(4, user.user_delegation_id.id)],
                                'is_delegation_mail_sent': True,
                            })
                            rec.update({
                                'approvers_ids': [(4, user.user_delegation_id.id)],
                            })
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

    def action_confirm(self):
        if self.number_of_days == 0:
            raise ValidationError(_(
                'Cannot Request for this Leave Type. Please Contact Your Administrator!'
            ))
        if self.env.user.has_group('hr_holidays.group_hr_holidays_manager') or self.env.user.has_group(
                'hr_holidays.group_hr_holidays_user'):
            if self.holiday_type != 'employee':
                self.write({'state': 'confirm'})
                self.sudo().action_validate()
                user_tz = self.employee_id.tz or 'UTC'
                local = pytz.timezone(user_tz)
                for user in self.approver_user_ids:
                    timestamp = datetime.strftime(datetime.now().astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
                    app_state = 'System' + ':' + 'Approved'
                    app_time = 'System' + ':' + str(timestamp)
                    user.approval_status = app_state
                    user.approved_time = app_time
                    user.is_approve = True
            else:
                self.write({'state': 'confirm'})
                self.sudo().submit_used_balance()
                self.approver_mail()
        else:
            if self.holiday_type == 'employee':
                self.approver_wa_template()
                self.approver_mail()
                holidays = self.filtered(lambda leave: leave.validation_type == 'no_validation')
                self.write({'state': 'confirm'})
                self.sudo().submit_used_balance()
                if holidays:
                    # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
                    holidays.sudo().action_validate()
                    # self.activity_update()
            else:
                self.write({'state': 'validate'})
            for line in self.approver_user_ids:
                line.write({'approver_state': 'draft'})
        if self.holiday_type == 'employee':
            leave_balance = self.leave_balance_id
            if leave_balance:
                leave_balance_value = "%(count)s" % {
                    'count': _('%g remaining out of %g') % (
                        float_round(float(leave_balance.remaining), precision_digits=2) or 0.0,
                        float_round(float(leave_balance.assigned) + float(leave_balance.bring_forward) + float(
                            leave_balance.extra_leave), precision_digits=2) or 0.0,
                    ) + (_(' hours') if self.holiday_status_id.request_unit == 'hour' else _(' days'))
                }
                self.leave_balance_value = leave_balance_value
        return True


    def wizard__leave_req_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.request.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':True},
            'target': 'new'
        }


    def action_approve(self):
        for record in self:
            current_user = self.env.uid
            user_tz = self.employee_id.tz or 'UTC'
            local = pytz.timezone(user_tz)
            if record.holiday_status_id.leave_validation_type == 'by_employee_hierarchy':
                if self.env.user not in record.approved_user_ids:
                    if record.is_approver:
                        for user in record.approver_user_ids:
                            for employee in user.employee_id:
                                if current_user == employee.id:
                                    user.approved_employee_ids = [(4, current_user)]
                                    user.is_approve = True
                                    user.timestamp = fields.Datetime.now()
                                    user.approver_state = 'approved'
                                    timestamp = datetime.strftime(datetime.now().astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
                                    if user.approval_status:
                                        app_state = user.approval_status + ', ' + self.env.user.name + ':' + 'Approved'
                                        app_time = user.approved_time + ', ' + self.env.user.name + ':' + str(timestamp)

                                        if record.feedback_parent:
                                            if user.feedback:
                                                feedback = user.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                            else:
                                                feedback = self.env.user.name + ':' + str(record.feedback_parent)
                                        else:
                                            feedback = ""
                                    else:
                                        app_state = self.env.user.name + ':' + 'Approved'
                                        app_time = self.env.user.name + ':' + str(timestamp)

                                        if record.feedback_parent:
                                            if user.feedback:
                                                feedback = user.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                            else:
                                                feedback = self.env.user.name + ':' + str(record.feedback_parent)
                                        else:
                                            feedback = ""


                                    user.approval_status = app_state
                                    user.approved_time = app_time
                                    user.feedback = feedback
                                    record.approved_user_ids = [(4, current_user)]
                        matrix_line = sorted(record.approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            self.approved_wa_template()
                            self.approved_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            super(HrLeave, self).action_approve()
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
                                    user.approved_employee_ids = [(4, current_user)]
                                    user.is_approve = True
                                    user.timestamp = fields.Datetime.now()
                                    user.approver_state = 'approved'
                                    timestamp = datetime.strftime(datetime.now().astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
                                    if user.approval_status:
                                        app_state = user.approval_status + ', ' + self.env.user.name + ':' + 'Approved'
                                        app_time = user.approved_time + ', ' + self.env.user.name + ':' + str(timestamp)
                                        if record.feedback_parent:
                                            if user.feedback:
                                                feedback = user.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                            else:
                                                feedback = self.env.user.name + ':' + str(record.feedback_parent)
                                        else:
                                            feedback = ""
                                    else:
                                        app_state = self.env.user.name + ':' + 'Approved'
                                        app_time = self.env.user.name + ':' + str(timestamp)
                                        if record.feedback_parent:
                                            if user.feedback:
                                                feedback = user.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                            else:
                                                feedback = self.env.user.name + ':' + str(record.feedback_parent)
                                        else:
                                            feedback = ""

                                    user.approval_status = app_state
                                    user.approved_time = app_time
                                    user.feedback = feedback
                        matrix_line = sorted(record.approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            self.approved_wa_template()
                            self.approved_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            super(HrLeave, self).action_approve()
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
                                    user.approved_employee_ids = [(4, current_user)]
                                    user.is_approve = True
                                    user.timestamp = fields.Datetime.now()
                                    user.approver_state = 'approved'
                                    timestamp = datetime.strftime(datetime.now().astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
                                    if user.approval_status:
                                        app_state = user.approval_status + ', ' + self.env.user.name + ':' + 'Approved'
                                        app_time = user.approved_time + ', ' + self.env.user.name + ':' + str(timestamp)

                                        if record.feedback_parent:
                                            if user.feedback:
                                                feedback = user.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                            else:
                                                feedback = self.env.user.name + ':' + str(record.feedback_parent)
                                        else:
                                            feedback = ""

                                    else:
                                        app_state = self.env.user.name + ':' + 'Approved'
                                        app_time = self.env.user.name + ':' + str(timestamp)
                                        if record.feedback_parent:
                                            if user.feedback:
                                                feedback = user.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                            else:
                                                feedback = self.env.user.name + ':' + str(record.feedback_parent)
                                        else:
                                            feedback = ""

                                    user.approval_status = app_state
                                    user.approved_time = app_time
                                    user.feedback = feedback
                                    record.approved_user_ids = [(4, current_user)]
                        matrix_line = sorted(record.approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            self.approved_wa_template()
                            self.approved_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            super(HrLeave, self).action_approve()
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
                                    user.approved_employee_ids = [(4, current_user)]
                                    user.is_approve = True
                                    user.timestamp = fields.Datetime.now()
                                    user.approver_state = 'approved'
                                    timestamp = datetime.strftime(datetime.now().astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
                                    if user.approval_status:
                                        app_state = user.approval_status + ', ' + self.env.user.name + ':' + 'Approved'
                                        app_time = user.approved_time + ', ' + self.env.user.name + ':' + str(timestamp)
                                        if record.feedback_parent:
                                            if user.feedback:
                                                feedback = user.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                            else:
                                                feedback = self.env.user.name + ':' + str(record.feedback_parent)
                                        else:
                                            feedback = ""

                                    else:
                                        app_state = self.env.user.name + ':' + 'Approved'
                                        app_time = self.env.user.name + ':' + str(timestamp)

                                        if record.feedback_parent:
                                            if user.feedback:
                                                feedback = user.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                            else:
                                                feedback = self.env.user.name + ':' + str(record.feedback_parent)
                                        else:
                                            feedback = ""

                                    user.approval_status = app_state
                                    user.approved_time = app_time
                                    user.feedback = feedback
                                    record.approved_user_ids = [(4, current_user)]
                        matrix_line = sorted(record.approver_user_ids.filtered(lambda r: r.is_approve == False))
                        if len(matrix_line) == 0:
                            self.approved_wa_template()
                            self.approved_mail()
                            record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                            record.write({'state': 'confirm'})
                            record.action_validate()
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
                if record.is_approver:
                    for user in record.approver_user_ids:
                        for employee in user.employee_id:
                            if current_user in employee.ids:
                                sequence_matrix = [data.name for data in record.approver_user_ids]
                                sequence_approval = [data.name for data in record.approver_user_ids.filtered(
                                    lambda line: len(line.approved_employee_ids) != line.minimum_approver)]
                                max_seq = max(sequence_matrix)
                                min_seq = min(sequence_approval)
                                approval = user.filtered(
                                    lambda line: self.env.user.id in line.employee_id.ids and len(
                                        line.approved_employee_ids) != line.minimum_approver and line.name == min_seq)
                                if approval:
                                    approval.approved_employee_ids = [(4, current_user)]
                                    user.timestamp = fields.Datetime.now()
                                    timestamp = datetime.strftime(datetime.now().astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT)
                                    record.approved_user_ids = [(4, current_user)]
                                    if len(approval.approved_employee_ids) == approval.minimum_approver:
                                        approval.approver_state = 'approved'
                                        if approval.approval_status:
                                            app_state = approval.approval_status + ', ' + self.env.user.name + ':' + 'Approved'
                                            app_time = approval.approved_time + ', ' + self.env.user.name + ':' + str(timestamp)
                                            if record.feedback_parent:
                                                if approval.feedback:
                                                    feedback = approval.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                                else:
                                                    feedback = self.env.user.name + ':' + str(record.feedback_parent)
                                            else:
                                                feedback = ""

                                        else:
                                            app_state = self.env.user.name + ':' + 'Approved'
                                            app_time = self.env.user.name + ':' + str(timestamp)
                                            if record.feedback_parent:
                                                if user.feedback:
                                                    feedback = user.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                                else:
                                                    feedback = self.env.user.name + ':' + str(record.feedback_parent)
                                            else:
                                                feedback = ""

                                        approval.approval_status = app_state
                                        approval.approved_time = app_time
                                        approval.feedback = feedback
                                        approval.is_approve = True
                                    else:
                                        approval.approver_state = 'pending'
                                        if approval.approval_status:
                                            app_state = approval.approval_status + ', ' + self.env.user.name + ':' + 'Approved'
                                            app_time = approval.approved_time + ', ' + self.env.user.name + ':' + str(timestamp)
                                        else:
                                            app_state = self.env.user.name + ':' + 'Approved'
                                            app_time = self.env.user.name + ':' + str(timestamp)
                                        approval.approval_status = app_state
                                        approval.approved_time = app_time

                    matrix_line = sorted(record.approver_user_ids.filtered(lambda r: r.is_approve == False))
                    if len(matrix_line) == 0:
                        self.approved_wa_template()
                        self.approved_mail()
                        record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                        record.write({'state': 'confirm'})
                        record.action_validate()
                    else:
                        self.approver_wa_template()
                        self.approver_mail()
                        record.approved_user = self.env.user.name + ' ' + 'has approved the Leave Request!'
                else:
                    raise ValidationError(_(
                        'You are not allowed to perform this action!'
                    ))
            else:
                # if validation_type == 'both': this method is the first approval approval
                # if validation_type != 'both': this method calls action_validate() below
                if any(holiday.state != 'confirm' for holiday in self):
                    raise UserError(_('Time off request must be confirmed ("To Approve") in order to approve it.'))

                current_employee = self.env.user.employee_id
                self.filtered(lambda hol: hol.validation_type == 'both').write(
                    {'state': 'validate1', 'first_approver_id': current_employee.id})

                # Post a second message, more verbose than the tracking message
                # for holiday in self.filtered(lambda holiday: holiday.employee_id.user_id):
                #     holiday.message_post(
                #         body=_(
                #             'Your %(leave_type)s planned on %(date)s has been accepted',
                #             leave_type=holiday.holiday_status_id.display_name,
                #             date=holiday.date_from
                #         ),
                #         partner_ids=holiday.employee_id.user_id.partner_id.ids)

                self.filtered(lambda hol: not hol.validation_type == 'both').action_validate()
                # if not self.env.context.get('leave_fast_create'):
                    # self.c()
                return True

    def action_refuse(self):
        for record in self:
            if self.holiday_status_id.set_by == 'duration':
                remaining_leaves = self.number_of_days
            else:
                remaining_leaves = 1
            record.leave_balance_id.used = record.leave_balance_id.used - remaining_leaves
            for count in record.leave_count_ids:
                if count.count_id.count < 0:
                    var_count = count.count_id.count
                else:
                    var_count = 0
                count.count_id.count = count.count_id.count - var_count + count.count
            record.leave_count_ids.unlink()
            for user in record.approver_user_ids:
                for employee in user.employee_id:
                    if self.env.uid == employee.id:
                        user.approved_employee_ids = [(4, self.env.user.id)]
                        user.timestamp = fields.Datetime.now()
                        user.approver_state = 'refuse'
                        if user.approval_status:
                            app_state = user.approval_status + ', ' + self.env.user.name + ':' + 'Refused'
                            app_time = user.approved_time + ', ' + self.env.user.name + ':' + str(user.timestamp)
                            if record.feedback_parent:
                                if user.feedback:
                                    feedback = user.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                else:
                                    feedback = self.env.user.name + ':' + str(record.feedback_parent)
                            else:
                                feedback = ""
                        else:
                            app_state = self.env.user.name + ':' + 'Refused'
                            app_time = self.env.user.name + ':' + str(user.timestamp)
                            if record.feedback_parent:
                                if user.feedback:
                                    feedback = user.feedback + ', ' + self.env.user.name + ':' + str(record.feedback_parent)
                                else:
                                    feedback = self.env.user.name + ':' + str(record.feedback_parent)
                            else:
                                feedback = ""
                        user.approval_status = app_state
                        user.approved_time = app_time
                        user.feedback = feedback

            self.rejected_wa_template()
            if not record.is_refused_by_leave_cancel_form:
                self.reject_mail()
            record.approved_user = self.env.user.name + ' ' + 'has Refused the Leave Request!'
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['draft', 'confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Time off request must be confirmed or validated in order to refuse it.'))

        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
        # Delete the meeting
        self.mapped('meeting_id').write({'active': False})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()

        # Post a second message, more verbose than the tracking message
        # for holiday in self:
        #     if holiday.employee_id.user_id:
        #         holiday.message_post(
        #             body=_('Your %(leave_type)s planned on %(date)s has been refused', leave_type=holiday.holiday_status_id.display_name, date=holiday.date_from),
        #             partner_ids=holiday.employee_id.user_id.partner_id.ids)

        self._remove_resource_leave()
        return True

    def wizard_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':False,'default_state':'rejected'},
            'target': 'new'
        }


    @api.depends('request_date_from')
    def _compute_hide_cancel(self):
        for rec in self:
            if rec.request_date_from:
                if date.today() >= rec.request_date_from:
                    rec.hide_cancel = True
                else:
                    rec.hide_cancel = False
            else:
                rec.hide_cancel = True

    def action_cancel(self):
        for vals in self:
            if vals.holiday_status_id.set_by == 'duration':
                remaining_leaves = self.number_of_days
            else:
                remaining_leaves = 1
            vals.leave_balance_id.used = vals.leave_balance_id.used - remaining_leaves
            for count in vals.leave_count_ids:
                if count.count_id.count < 0:
                    var_count = count.count_id.count
                else:
                    var_count = 0
                count.count_id.count = count.count_id.count - var_count + count.count
            vals.leave_count_ids.unlink()
            vals.write({'state': 'cancel'})

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date(self):
        if self.env.context.get('leave_skip_date_check', False):
            return
        if self.holiday_type == "employee":
            if self.employee_id.contract_id:
                if self.employee_id.contract_id.state != "open":
                    raise ValidationError(
                        _('Cannot request for a Leave. There is No Running Contract on This Employee!'))
                if self.employee_id.contract_id.date_end:
                    if self.request_date_to > self.employee_id.contract_id.date_end:
                        raise ValidationError(
                            _('Cannot request for a Leave. Submission Date is Greater Than the expiration Date of the Employee Contract!'))
            else:
                raise ValidationError(
                    _('Cannot request for a Leave. There is no Contract of the Employee!'))
        for holiday in self.filtered('employee_id'):
            domain = [
                ('date_from', '<', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('employee_id', '=', holiday.employee_id.id),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse', 'confirm', 'validate']),
            ]
            nholidays = self.search_count(domain)
            if nholidays:
                raise ValidationError(
                    _('You can not set 2 time off that overlaps on the same day for the same employee.'))


    def action_validate(self):
        current_employee = self.env.user.employee_id
        leaves = self.filtered(lambda l: l.employee_id and not l.number_of_days)
        if leaves:
            raise ValidationError(
                _('The following employees are not supposed to work during that period:\n %s') % ','.join(
                    leaves.mapped('employee_id.name')))

        if any(holiday.state not in ['confirm', 'validate1'] and holiday.validation_type != 'no_validation' for holiday
               in self):
            raise UserError(_('Time off request must be confirmed in order to approve it.'))
        self.write({'state': 'validate'})
        self.filtered(lambda holiday: holiday.validation_type == 'both').write(
            {'second_approver_id': current_employee.id})
        self.filtered(lambda holiday: holiday.validation_type != 'both').write(
            {'first_approver_id': current_employee.id})

        for holiday in self.filtered(lambda holiday: holiday.holiday_type != 'employee'):
            if holiday.holiday_type == 'category':
                employee_ids = holiday.category_id.employee_ids.filtered(lambda l: l.active and l.contract_id and l.leave_struct_id)
                employee_datas = []
                for emp in employee_ids:
                    if emp.contract_id.state == "open" and holiday.holiday_status_id.id in emp.leave_struct_id.leaves_ids.ids:
                        employee_datas.append(emp.id)
                employees = self.env['hr.employee'].browse(employee_datas)
            elif holiday.holiday_type == 'company':
                employee_ids = self.env['hr.employee'].search([('company_id', '=', holiday.mode_company_id.id),('active','=',True),('contract_id','!=',False),('leave_struct_id','!=',False)])
                employee_datas = []
                for emp in employee_ids:
                    if emp.contract_id.state == "open" and holiday.holiday_status_id.id in emp.leave_struct_id.leaves_ids.ids:
                        employee_datas.append(emp.id)
                employees = self.env['hr.employee'].browse(employee_datas)
            else:
                employee_ids = holiday.department_id.member_ids.filtered(lambda l: l.active and l.contract_id and l.leave_struct_id)
                employee_datas = []
                for emp in employee_ids:
                    if emp.contract_id.state == "open" and holiday.holiday_status_id.id in emp.leave_struct_id.leaves_ids.ids:
                        employee_datas.append(emp.id)
                employees = self.env['hr.employee'].browse(employee_datas)
        
            conflicting_leaves = self.env['hr.leave'].with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True
            ).search([
                ('date_from', '<=', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('state', 'not in', ['cancel', 'refuse', 'confirm', 'validate']),
                ('holiday_type', '=', 'employee'),
                ('holiday_status_id', '=', holiday.holiday_status_id.id),
                ('employee_id', 'in', employees.ids)])

            if conflicting_leaves:
                # YTI: More complex use cases could be managed in master
                if holiday.leave_type_request_unit != 'day' or any(
                        l.leave_type_request_unit == 'hour' for l in conflicting_leaves):
                    raise ValidationError(_('You can not have 2 time off that overlaps on the same day.'))

                # keep track of conflicting leaves states before refusal
                target_states = {l.id: l.state for l in conflicting_leaves}
                conflicting_leaves.action_refuse()
                split_leaves_vals = []
                for conflicting_leave in conflicting_leaves:
                    if conflicting_leave.leave_type_request_unit == 'half_day' and conflicting_leave.request_unit_half:
                        continue

                    # Leaves in days
                    if conflicting_leave.date_from < holiday.date_from:
                        before_leave_vals = conflicting_leave.copy_data({
                            'date_from': conflicting_leave.date_from.date(),
                            'date_to': holiday.date_from.date() + timedelta(days=-1),
                            'state': target_states[conflicting_leave.id],
                        })[0]
                        before_leave = self.env['hr.leave'].new(before_leave_vals)
                        before_leave._compute_date_from_to()

                        # Could happen for part-time contract, that time off is not necessary
                        # anymore.
                        # Imagine you work on monday-wednesday-friday only.
                        # You take a time off on friday.
                        # We create a company time off on friday.
                        # By looking at the last attendance before the company time off
                        # start date to compute the date_to, you would have a date_from > date_to.
                        # Just don't create the leave at that time. That's the reason why we use
                        # new instead of create. As the leave is not actually created yet, the sql
                        # constraint didn't check date_from < date_to yet.
                        if before_leave.date_from < before_leave.date_to:
                            split_leaves_vals.append(before_leave._convert_to_write(before_leave._cache))
                    if conflicting_leave.date_to > holiday.date_to:
                        after_leave_vals = conflicting_leave.copy_data({
                            'date_from': holiday.date_to.date() + timedelta(days=1),
                            'date_to': conflicting_leave.date_to.date(),
                            'state': target_states[conflicting_leave.id],
                        })[0]
                        after_leave = self.env['hr.leave'].new(after_leave_vals)
                        after_leave._compute_date_from_to()
                        # Could happen for part-time contract, that time off is not necessary
                        # anymore.
                        if after_leave.date_from < after_leave.date_to:
                            split_leaves_vals.append(after_leave._convert_to_write(after_leave._cache))

                split_leaves = self.env['hr.leave'].with_context(
                    tracking_disable=True,
                    mail_activity_automation_skip=True,
                    leave_fast_create=True,
                    leave_skip_state_check=True
                ).create(split_leaves_vals)

                split_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()

            employee_leaves = self.env['hr.leave'].with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True
            ).search([
                ('date_from', '<=', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('state', 'in', ['cancel', 'refuse', 'confirm', 'validate']),
                ('holiday_type', '=', 'employee'),
                ('holiday_status_id', '=', holiday.holiday_status_id.id),
                ('employee_id', 'in', employees.ids)])

            values = holiday._prepare_employees_holiday_values(employees)
            leaves = self.env['hr.leave'].with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True,
                leave_skip_state_check=True,
            ).create(values)

            leaves._validate_leave_request()
            if employee_leaves:
                pass
            else:
                self.sudo().submit_used_balance()

        employee_requests = self.filtered(lambda hol: hol.holiday_type == 'employee')
        employee_requests._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            employee_requests.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True

    def submit_used_balance(self):
        for rec in self:
            if rec.holiday_type == 'employee':
                leave_count = self.env['hr.leave.count'].search([('employee_id', '=', rec.employee_id.id),
                                                                ('holiday_status_id', '=', rec.holiday_status_id.id),
                                                                ('count', '>', 0), ('expired_date', '>=', date.today()),
                                                                ('is_expired','=',False)],
                                                                order='expired_date asc')
                data_leave_count = len(leave_count)
                num_rec = 0
                var_count = 0
                expired_date = ''
                leave_balance_id = 0
                if rec.holiday_status_id.set_by == 'duration':
                    remaining_leaves = rec.number_of_days
                    number_of_days = rec.number_of_days
                else:
                    remaining_leaves = 1
                    number_of_days = 1
                for count_line in leave_count:
                    expired_date = count_line.expired_date
                    leave_balance_id = count_line.leave_balance_id.id
                if expired_date and rec.request_date_to > expired_date and rec.holiday_status_id.carry_forward in ['remaining_amount','specific_days']:
                    leave_balance = self.env['hr.leave.balance'].search([('employee_id', '=', rec.employee_id.id),
                                                                        ('holiday_status_id', '=', rec.holiday_status_id.id),
                                                                        # ('current_period', '=', expired_date.year)],
                                                                        ('id', '=', leave_balance_id)],
                                                                        limit=1)
                else:
                    leave_balance = self.env['hr.leave.balance'].search([('employee_id', '=', rec.employee_id.id),
                                                                        ('holiday_status_id', '=', rec.holiday_status_id.id),
                                                                        # ('current_period', '=', self.request_date_to.year)],
                                                                        ('id', '=', leave_balance_id)],
                                                                        limit=1)
                if leave_balance:
                    for count_line in leave_count:
                        num_rec += 1
                        if number_of_days > var_count:
                            var_count += count_line.count
                            taken_leaves = abs(remaining_leaves)
                            remaining_leaves = count_line.count - abs(remaining_leaves)
                            if remaining_leaves < 0 and num_rec == data_leave_count and count_line.description == "Allocation":
                                count = remaining_leaves
                                taken_count = count_line.count
                            elif remaining_leaves < 0:
                                count = 0
                                taken_count = count_line.count
                            else:
                                count = remaining_leaves
                                taken_count = taken_leaves
                            rec.leave_count_ids.create({
                                'leave_id': rec.id,
                                'count_id': count_line.id,
                                'count': taken_count
                            })
                            count_line.count = count
                    rec.leave_balance_id = leave_balance.id
                    leave_balance.used = leave_balance.used + number_of_days
            else:
                employees = False
                if rec.holiday_type == 'category':
                    employee_ids = rec.category_id.employee_ids.filtered(lambda l: l.active and l.contract_id)
                    employee_datas = []
                    for emp in employee_ids:
                        emp_leave_bal = self.env['hr.leave.balance'].search([('employee_id','=',emp.id),('holiday_status_id','=',rec.holiday_status_id.id)])
                        if emp.contract_id.state == "open" and emp_leave_bal:
                            employee_datas.append(emp.id)
                    employees = self.env['hr.employee'].browse(employee_datas)
                elif rec.holiday_type == 'company':
                    employee_ids = self.env['hr.employee'].search([('company_id', '=', rec.mode_company_id.id),('active','=',True),('contract_id','!=',False)])
                    employee_datas = []
                    for emp in employee_ids:
                        emp_leave_bal = self.env['hr.leave.balance'].search([('employee_id','=',emp.id),('holiday_status_id','=',rec.holiday_status_id.id)])
                        if emp.contract_id.state == "open" and emp_leave_bal:
                            employee_datas.append(emp.id)
                    employees = self.env['hr.employee'].browse(employee_datas)
                elif rec.holiday_type == 'department':
                    employee_ids = rec.department_id.member_ids.filtered(lambda l: l.active and l.contract_id)
                    employee_datas = []
                    for emp in employee_ids:
                        emp_leave_bal = self.env['hr.leave.balance'].search([('employee_id','=',emp.id),('holiday_status_id','=',rec.holiday_status_id.id)])
                        if emp.contract_id.state == "open" and emp_leave_bal:
                            employee_datas.append(emp.id)
                    employees = self.env['hr.employee'].browse(employee_datas)

                for employee in employees:
                    leave_count = self.env['hr.leave.count'].search([
                        ('employee_id', '=', employee.id),
                        ('holiday_status_id', '=', rec.holiday_status_id.id),
                        ('count', '>', 0), ('expired_date', '>=', date.today())
                    ], order='expired_date asc')

                    data_leave_count = len(leave_count)
                    num_rec = 0
                    var_count = 0
                    expired_date = ''
                    # leave_balance_id = 0
                    if rec.holiday_status_id.set_by == 'duration':
                        remaining_leaves = rec.number_of_days
                        number_of_days = rec.number_of_days
                    else:
                        remaining_leaves = 1
                        number_of_days = 1
                    for count_line in leave_count:
                        expired_date = count_line.expired_date
                        # leave_balance_id = count_line.leave_balance_id.id

                    if expired_date and rec.request_date_to > expired_date:
                        if rec.holiday_status_id.carry_forward in ['remaining_amount', 'specific_days']:
                            leave_balance = self.env['hr.leave.balance'].search([
                                ('employee_id', '=', employee.id),
                                ('holiday_status_id', '=', rec.holiday_status_id.id),
                                # ('current_period', '=', expired_date.year)],
                                # ('id', '=', leave_balance_id)
                                ('current_period', '=', expired_date.year)
                            ])
                        else:
                            leave_balance = self.env['hr.leave.balance'].search([
                                ('employee_id', '=', employee.id),
                                ('holiday_status_id', '=', rec.holiday_status_id.id),
                                # ('current_period', '=', self.request_date_to.year)],
                                # ('id', '=', leave_balance_id)
                                # ('current_period', '=', self.request_date_to.year)
                            ])
                    else:
                        leave_balance = self.env['hr.leave.balance'].search([
                            ('employee_id', 'in', employees.ids),
                            ('holiday_status_id', '=', rec.holiday_status_id.id),
                            # ('current_period', '=', self.request_date_to.year)],
                            # ('id', '=', leave_balance_id)
                            ('current_period', '=', self.request_date_to.year)
                        ])
                    if leave_balance:
                        for count_line in leave_count:
                            num_rec += 1
                            if number_of_days > var_count:
                                var_count += count_line.count
                                taken_leaves = abs(remaining_leaves)
                                remaining_leaves = count_line.count - abs(remaining_leaves)
                                if remaining_leaves < 0 and num_rec == data_leave_count and count_line.description == "Allocation":
                                    count = remaining_leaves
                                    taken_count = count_line.count
                                elif remaining_leaves < 0:
                                    count = 0
                                    taken_count = count_line.count
                                else:
                                    count = remaining_leaves
                                    taken_count = taken_leaves
                                rec.leave_count_ids.create({
                                    'leave_id': rec.id,
                                    'count_id': count_line.id,
                                    'count': taken_count
                                })
                                count_line.count = count
                        for balance in leave_balance:
                            rec.leave_balance_id = balance.id
                            balance.used = balance.used + number_of_days

    @api.constrains('number_of_days', 'request_date_from', 'request_date_to')
    def _check_limit_days(self):
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
            if self.holiday_status_id.limit_days > 0 and self.request_date_from and self.request_date_to:
                if self.holiday_status_id.limit_days < self.number_of_days:
                    raise ValidationError(
                        _('You can not apply %(type)s more than %(count)s for a single request.',
                          count=self.holiday_status_id.limit_days,
                          type=self.holiday_status_id.name))

    @api.depends('date_from', 'date_to', 'employee_id')
    def _compute_number_of_days(self):
        for holiday in self:
            if holiday.request_unit_half:
                holiday.number_of_days = 0.5
            elif holiday.date_from and holiday.date_to and holiday.holiday_status_id.day_count == 'calendar_day':
                delta = (holiday.date_to - holiday.date_from).days  # as timedelta
                holiday.number_of_days = delta + 1
            elif holiday.request_date_from and holiday.request_date_to and holiday.holiday_status_id.day_count == 'work_day':
                start_leave = holiday.request_date_from
                duration_list = []
                employee_calendar = self.env['employee.working.schedule.calendar'].search(
                    [('employee_id', '=', holiday.employee_id.id), ('active', '=', True),
                     ('date_start', '>=', holiday.request_date_from), ('date_start', '<=', holiday.request_date_to)], order="date_start asc")
                wrk_calendar = []
                for rec in employee_calendar:
                    wrk_calendar.append(rec.date_start)
                public_holiday_comp = []
                for rec in holiday.employee_id.resource_calendar_id.global_leave_ids:
                    start_from = rec.date_from
                    while start_from <= rec.date_to:
                        public_holiday_comp.append(start_from)
                        start_from += relativedelta(days=1)
                while start_leave <= holiday.request_date_to:
                    if start_leave in wrk_calendar and start_leave not in public_holiday_comp:
                        duration_list.append(start_leave)
                    start_leave += relativedelta(days=1)
                holiday.number_of_days = len(duration_list)
            # else:
            #     holiday.number_of_days = \
            #         holiday._get_number_of_days(holiday.date_from, holiday.date_to, holiday.employee_id.id)['days']

            else:
                holiday.number_of_days = 0

    @api.depends('employee_id')
    def _compute_cancel(self):
        for leave in self:
            cancel = self.env['hr.leave.cancelation'].search([('leave_id', '=', leave.id)], limit=1)
            if cancel:
                leave.cancel_id = cancel.id
            else:
                leave.cancel_id = False

    def name_get(self):
        res = []
        view_type = self._context.get('view_mode')
        for leave in self:
            if view_type == 'calendar':
                # Display employee's name in calendar view
                res.append((leave.id, leave.employee_id.name))
            else:
                # Display leave's sequence name in other views
                res.append((leave.id, leave.seq_name))
        return res

    @api.constrains('number_of_days', 'request_date_from', 'request_date_to')
    def _check_leave_balance(self):
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
            for leave in self:
                if leave.holiday_type == 'employee':
                    leave_count = self.env['hr.leave.count'].search([('employee_id', '=', leave.employee_id.id),
                                                                ('holiday_status_id', '=', leave.holiday_status_id.id),
                                                                ('count', '>', 0), ('expired_date', '>=', date.today())],
                                                                order='expired_date asc')
                    expired_date = ''
                    for count_line in leave_count:
                        expired_date = count_line.expired_date

                    if expired_date and leave.request_date_to > expired_date and leave.holiday_status_id.carry_forward not in ['remaining_amount','specific_days']:
                        raise ValidationError(_("Leave Type doesn't allow to over expiry days!"))
                    if expired_date and leave.request_date_to > expired_date:
                        if leave.holiday_status_id.carry_forward not in ['remaining_amount','specific_days']:
                            raise ValidationError(_("Leave Type doesn't allow to over expiry days!"))
                        else:
                            continue
                    else:
                        leave_counts = self.env['hr.leave.count'].search([('employee_id', '=', leave.employee_id.id),
                                                                    ('holiday_status_id', '=', leave.holiday_status_id.id),
                                                                    ('expired_date', '>=', leave.request_date_to),
                                                                    ('active', '=', True)])

                        available_leave_count = 0
                        if leave_counts:
                            start_date_leave_count = leave_counts.sorted(key=lambda p: (p.start_date), reverse=False)
                            expired_date_leave_count = leave_counts.sorted(key=lambda p: (p.expired_date), reverse=True)
                            for rec in leave_counts:
                                if leave.request_date_from >= start_date_leave_count[0].start_date and leave.request_date_from <= expired_date_leave_count[0].expired_date:
                                    available_leave_count += rec.count

                        available_leave = 0
                        if leave.holiday_status_id.allow_minus:
                            available_leave = available_leave + float(
                                available_leave_count) + leave.holiday_status_id.maximum_minus
                        else:
                            available_leave = available_leave + float(available_leave_count)

                        if available_leave_count == 0:
                            raise ValidationError(
                                _('Please ask the responsible user in order to allocate your leaves!'))
                        elif leave.number_of_days > available_leave:
                            raise ValidationError(
                                _('You can not request leave more than leave balance.'))
                else:
                    continue

    @api.constrains('holiday_status_id')
    def _check_leave_minimum_days(self):
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
            for leave in self:
                if leave.request_back_date:
                    if leave.holiday_status_id.day_count == 'calendar_day':
                        past_days = date.today() - relativedelta(days=leave.holiday_status_id.past_days)
                        if leave.request_date_from < past_days and not leave.is_urgent:
                            raise ValidationError(
                                _('You can only able for request leave for the last %s days') % (
                                    leave.holiday_status_id.past_days))
                    elif leave.holiday_status_id.day_count == 'work_day':
                        start_leave = leave.request_date_from
                        weekend = 0
                        while start_leave <= date.today():
                            if start_leave.weekday() in (5, 6):
                                weekend += 1
                            start_leave += relativedelta(days=1)
                        minimum_days_weekend = date.today() - relativedelta(days=leave.holiday_status_id.past_days)
                        past_days = minimum_days_weekend - relativedelta(days=weekend)
                        if leave.request_date_from < past_days and not leave.is_urgent:
                            raise ValidationError(
                                _('You can only able for request leave for the last %s days ') % (
                                    leave.holiday_status_id.past_days))
                else:
                    if not leave.holiday_status_id.allow_past_date:
                        if leave.request_date_from < date.today() and not leave.is_urgent:
                            raise ValidationError(_('You cannot request leave for past dated'))
                        else:
                            if leave.holiday_status_id.minimum_days_before and leave.holiday_status_id.day_count == 'calendar_day':
                                minimum_days = date.today() + relativedelta(days=leave.holiday_status_id.minimum_days_before)
                                if leave.request_date_from < minimum_days and not leave.is_urgent:
                                    raise ValidationError(
                                        _('You only able to request leave minimum %s days before the leave date') % (
                                            leave.holiday_status_id.minimum_days_before))
                            elif leave.holiday_status_id.minimum_days_before and leave.holiday_status_id.day_count == 'work_day':
                                start_leave = date.today()
                                weekend = 0
                                while start_leave <= leave.request_date_to:
                                    if start_leave.weekday() in (5, 6):
                                        weekend += 1
                                    start_leave += relativedelta(days=1)
                                minimum_days_weekend = date.today() + relativedelta(days=leave.holiday_status_id.minimum_days_before)
                                minimum_days = minimum_days_weekend + relativedelta(days=weekend)
                                if leave.request_date_from < minimum_days and not leave.is_urgent:
                                    raise ValidationError(
                                        _('You only able to request leave minimum %s days before the leave date') % (
                                            leave.holiday_status_id.minimum_days_before))
                    elif leave.holiday_status_id.allow_past_date:
                        if leave.holiday_status_id.minimum_days_before and leave.holiday_status_id.day_count == 'calendar_day':
                            minimum_days = date.today() + relativedelta(days=leave.holiday_status_id.minimum_days_before)
                            if leave.request_date_from < minimum_days and not leave.is_urgent:
                                raise ValidationError(
                                    _('You only able to request leave minimum %s days before the leave date') % (
                                        leave.holiday_status_id.minimum_days_before))
                        elif leave.holiday_status_id.minimum_days_before and leave.holiday_status_id.day_count == 'work_day':
                            start_leave = date.today()
                            weekend = 0
                            while start_leave <= leave.request_date_to:
                                if start_leave.weekday() in (5, 6):
                                    weekend += 1
                                start_leave += relativedelta(days=1)
                            minimum_days_weekend = date.today() + relativedelta(days=leave.holiday_status_id.minimum_days_before)
                            minimum_days = minimum_days_weekend + relativedelta(days=weekend)
                            if leave.request_date_from < minimum_days and not leave.is_urgent:
                                raise ValidationError(
                                    _('You only able to request leave minimum %s days before the leave date') % (
                                        leave.holiday_status_id.minimum_days_before))
                if leave.holiday_status_id.gender and leave.holiday_status_id.gender != leave.employee_id.gender:
                    raise ValidationError(_('Selected Employee and Leave Type Gender is different'))

    @api.constrains('number_of_days', 'request_date_from', 'request_date_to')
    def _check_over_expiry_days(self):
        for leave in self:
            if leave.holiday_type == 'employee':
                leave_count = self.env['hr.leave.count'].search([('employee_id', '=', leave.employee_id.id),
                                                                ('holiday_status_id', '=', leave.holiday_status_id.id),
                                                                ('count', '>', 0), ('expired_date', '>=', date.today())],
                                                                order='expired_date asc')
                expired_date = ''
                for count_line in leave_count:
                    expired_date = count_line.expired_date

                if expired_date and leave.request_date_to > expired_date and leave.holiday_status_id.carry_forward not in ['remaining_amount','specific_days']:
                    raise ValidationError(_("Leave Type doesn't allow to over expiry days!"))
            else:
                continue

    @api.model
    def default_get(self, fields_list):
        defaults = super(HrLeave, self).default_get(fields_list)
        defaults = self._default_get_request_parameters(defaults)
        defaults['holiday_status_id'] = False
        if 'holiday_status_id' in fields_list and not defaults.get('holiday_status_id'):
            for lt in self.employee_id.leave_struct_id.leaves_ids:
                if lt:
                    defaults['holiday_status_id'] = lt.id
        if 'state' in fields_list and not defaults.get('state'):
            lt = self.env['hr.leave.type'].browse(defaults.get('holiday_status_id'))
            defaults['state'] = 'confirm' if lt and lt.leave_validation_type != 'no_validation' else 'draft'
        now = fields.Datetime.now()
        if 'date_from' not in defaults:
            defaults.update({'date_from': now})
        if 'date_to' not in defaults:
            defaults.update({'date_to': now})
        return defaults

    # @api.onchange('holiday_type', 'employee_id')
    # def onchange_domain_holiday_type(self):
    #     res = {}
    #     holiday_list = []
    #     if self.holiday_type == 'employee':
    #         for vals in self.employee_id.leave_struct_id.leaves_ids:
    #             holiday_list.append(vals.id)
    #             res['domain'] = {'holiday_status_id': [('id', 'in', holiday_list)]}
    #     else:
    #         res['domain'] = {'holiday_status_id': []}
    #     return res

    @api.onchange('employee_id', 'holiday_status_id')
    def onchange_emp_in_type(self):
        for rec in self:
            if rec.holiday_type == 'employee':
                leave_type_master = self.env['hr.leave.type'].search([])
                leave_type_master.update({
                    'employee_id': rec.employee_id,
                })
            else:
                leave_type_master = self.env['hr.leave.type'].search([])
                leave_type_master.update({
                    'employee_id': False, })

    @api.depends('employee_id', 'holiday_status_id')
    def _compute_line_items(self):
        for rec in self:
            if rec.holiday_status_id.leave_validation_type == 'no_validation':
                rec.line_item_visible = True
            else:
                rec.line_item_visible = False

class HrLeaveLine(models.Model):
    _name = 'hr.leave.line'

    leave_id = fields.Many2one('hr.leave', string="Leave")
    count_id = fields.Many2one('hr.leave.count', string="Leave Count")
    count = fields.Float(string="Count")


class LeaveApproverUser(models.Model):
    _name = 'leave.approver.user'

    leave_id = fields.Many2one('hr.leave', string="Leave")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    employee_id = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'approved_users_rel', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Char(string="Timestamp")
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='draft', string="State")
    approval_status = fields.Text(string="Approval Status")
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'leave_max_user_ids', string="Matrix user")
    is_delegation_mail_sent = fields.Boolean(string="Is Delegation Email Sent", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='leave_id.state')
    feedback = fields.Text(string='Feedback')

    @api.depends('leave_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.leave_id.approver_user_ids:
            sl = sl + 1
            line.name = sl
        self.update_minimum_app()
    def update_minimum_app(self):
        for rec in self:
            if len(rec.employee_id) < rec.minimum_approver and rec.leave_id.state == 'draft':
                rec.minimum_approver = len(rec.employee_id)
            if not rec.matrix_user_ids and rec.leave_id.state == 'draft':
                rec.matrix_user_ids = rec.employee_id

class LeaveReport(models.Model):
    _inherit = 'hr.leave.report'

    @api.model
    def action_leave_analysis(self):
        domain = [('holiday_type', '=', 'employee')]

        if self.env.context.get('active_ids'):
            domain = expression.AND([
                domain,
                [('employee_id', 'in', self.env.context.get('active_ids', []))]
            ])

        return {
            'name': _('Leave Analysis'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.report',
            'view_mode': 'tree,pivot,form',
            'search_view_id': self.env.ref('hr_holidays.view_hr_holidays_filter_report').id,
            'domain': domain,
            'context': {
                'search_default_group_type': True,
                'search_default_year': True,
                'search_default_validated': True,
            }
        }

