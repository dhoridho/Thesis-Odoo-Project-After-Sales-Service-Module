from datetime import datetime, timedelta
from datetime import date
# from attr import field
import pytz
from pytz import timezone
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta
from odoo.tools.safe_eval import safe_eval
from lxml import etree
import requests
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
import time
headers = {'content-type': 'application/json'}

class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'
    _description = "Hr Leave Allocation"

    @api.model
    def _leave_type_company_domain(self):
        return [('company_id','=', self.env.company.id),('leave_method', '=', 'none'),('valid', '=', True)]
    
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Rejected'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
    ], string='Status', readonly=True, tracking=True, copy=False, default='draft',
        help="The status is set to 'To Submit', when an allocation request is created." +
             "\nThe status is 'To Approve', when an allocation request is confirmed by user." +
             "\nThe status is 'Refused', when an allocation request is refused by manager." +
             "\nThe status is 'Approved', when an allocation request is approved by manager.")
    feedback_parent = fields.Text(string='Parent Feedback', default='')
    holiday_status_id = fields.Many2one(
        "hr.leave.type", string="Leave Type", required=True,
        readonly=False,
        default=False,
        states={'cancel': [('readonly', True)], 'confirm': [('readonly', True)], 'refuse': [('readonly', True)], 'validate1': [('readonly', True)],
                'validate': [('readonly', True)]},
        domain=_leave_type_company_domain)
    approver_user_ids = fields.One2many('allocation.approver.user', 'leave_id', string='Approver')
    is_hide_approve = fields.Boolean(compute='_compute_approver', default=True)
    approvers_ids = fields.Many2many('res.users', 'allocation_approver_users_rel', string='Approvers')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    allocation_type_by = fields.Selection([
        ('overtime', 'By Overtime'),
        ('dates', 'By Dates')
    ], string='Allocation Type', default='dates')
    overtime_id = fields.Many2one('hr.overtime.actual', string='Overtime')
    allocation_date_from = fields.Date('Allocation Start Date')
    allocation_date_to = fields.Date('Allocation End Date')
    allocation_date_from_period = fields.Selection([
        ('morning', 'Morning'), ('afternoon', 'Afternoon'), ('evening', 'Evening')],
        string="Date Period Start", default='morning')
    allocation_half_day = fields.Boolean('Half Day')
    effective_date = fields.Date('Effective Date', default=fields.Date.context_today)
    sequence = fields.Char('Name')
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrLeaveAllocation, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrLeaveAllocation, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def custom_menu(self):
        views = [(self.env.ref('equip3_hr_holidays_extend.hr_leave_allocation_view_tree_manager').id, 'tree'),
                     (self.env.ref('equip3_hr_holidays_extend.hr_leave_allocation_view_form_manager').id, 'form')]
        # search_view_id = self.env.ref("hr_contract.hr_contract_view_search")
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
                    'name': 'Allocation Requests',
                    'res_model': 'hr.leave.allocation',
                    'target': 'current',
                    'view_mode': 'tree,form,kanban,activity',
                    'views':views,
                    'domain': ['|',('employee_id', 'in', employee_ids),('approvers_ids', 'in', self.env.user.ids)],
                    'context': {'search_default_pending_my_approval': 1,'is_approve':True},
                    'help': """<p class="o_view_nocontent_smiling_face">
                        Create a new leave allocation
                    </p>"""
                    # 'search_view_id':search_view_id.id,

                }

        else:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Allocation Requests',
                    'res_model': 'hr.leave.allocation',
                    'target': 'current',
                    'view_mode': 'tree,form,kanban,activity',
                    'views':views,
                    # 'domain': [('employee_id', 'in', employee_ids)],
                    'context': {'search_default_pending_my_approval': 1,'is_approve':True},
                    'help': """<p class="o_view_nocontent_smiling_face">
                        Create a new leave allocation
                    </p>"""
                    # 'search_view_id':search_view_id.id,

                }
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrLeaveAllocation, self).fields_view_get(
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
        
        if not self._context.get('validate', False):
            approve_button_id = self.env.ref('hr_holidays.ir_actions_server_approve_allocations').id or False
            for button in res.get('toolbar', {}).get('action', []):
                if approve_button_id and button['id'] == approve_button_id:
                    res['toolbar']['action'].remove(button)
            
        return res

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('hr.leave.allocation')
        vals.update({'sequence': sequence})
        result = super(HrLeaveAllocation, self).create(vals)
        if result.allocation_type_by == 'overtime' and result.holiday_status_id.overtime_extra_leave == False:
            raise ValidationError(_("Selected leave types not allow to overtime extra leave"))
        return result
    
    def unlink(self):
        for res in self:
            if res.state in ['validate']:
                raise UserError(_('You can not delete if already approve'))
        return super(HrLeaveAllocation, self).unlink()

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return
        current_employee = self.env.user.employee_id
        if not current_employee:
            return
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')
        for holiday in self:
            val_type = holiday.holiday_status_id.sudo().allocation_validation_type
            if state == 'confirm':
                continue

            if state == 'draft':
                if holiday.employee_id != current_employee and not is_manager:
                    raise UserError(_('Only a time off Manager can reset other people allocation.'))
                continue

            # if not is_officer and self.env.user != holiday.employee_id.leave_manager_id:
            #     raise UserError(_('Only a time off Officer/Responsible or Manager can approve or refuse time off requests.'))

            if is_officer or self.env.user == holiday.employee_id.leave_manager_id:
                # use ir.rule based first access check: department, members, ... (see security.xml)
                holiday.check_access_rule('write')

            # if holiday.employee_id == current_employee and not is_manager:
            #     raise UserError(_('Only a time off Manager can approve its own requests.'))

            # if (state == 'validate1' and val_type == 'both') or (state == 'validate' and val_type == 'manager'):
            #     if self.env.user == holiday.employee_id.leave_manager_id and self.env.user != holiday.employee_id.user_id:
            #         continue
            #     manager = holiday.employee_id.parent_id or holiday.employee_id.department_id.manager_id
            #     if (manager != current_employee) and not is_manager:
            #         raise UserError(_('You must be either %s\'s manager or time off manager to approve this time off') % (holiday.employee_id.name))
            #
            # if state == 'validate' and val_type == 'both':
            #     if not is_officer:
            #         raise UserError(_('Only a Time off Approver can apply the second approval on allocation requests.'))


    @api.constrains('employee_id', 'holiday_status_id')
    def _check_leave_gender(self):
        for leave in self:
            if leave.holiday_status_id.gender:
                if leave.employee_id.gender != leave.holiday_status_id.gender:
                    raise ValidationError(_('Selected Employee and Leave Type Gender is different!'))
            else:
                continue

    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'hr_holidays', 'hr_holidays_menu_manager_approve_allocations')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'hr_holidays', 'hr_leave_allocation_action_approve_department')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.holidays&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url

    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.approver_user_ids:
                for matrix_line in sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True)):
                    approver = rec.approver_user_ids[len(matrix_line)]
                    for user in approver.user_ids:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_holidays_extend',
                                'email_template_leave_allocation_request')[1]
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
                            'duration': self.number_of_days_display,
                        })
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                    break

    def approved_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.approver_user_ids:
                for rec in rec.approver_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.user_ids:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_holidays_extend',
                                'email_template_edi_leave_allocation_approved')[1]
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
                            'duration': self.number_of_days_display,
                        })
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                    break

    def reject_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.approver_user_ids:
                for rec in rec.approver_user_ids.sorted(key=lambda r: r.name):
                    for user in rec.user_ids:
                        try:
                            template_id = ir_model_data.get_object_reference(
                                'equip3_hr_holidays_extend',
                                'email_template_edi_leave_allocation_reject')[1]
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
                            'duration': self.number_of_days_display,
                        })
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id,
                                                                                                  force_send=True)
                    break

    def approver_wa_template(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_wa')
        if send_by_wa:
            # connector = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.connector_id')
            # if connector:
            #     connector_id = self.env['acrux.chat.connector'].search([('id', '=', connector)])
            #     if connector_id.ca_status:
            template = self.env.ref('equip3_hr_holidays_extend.leave_allocation_approver_wa_template')
            wa_sender = waParam()
            # url = self.get_url(self)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if template:
                if self.approver_user_ids:
                    for matrix_line in sorted(self.approver_user_ids.filtered(lambda r: r.is_approve == True)):
                        approver = self.approver_user_ids[len(matrix_line)]
                        for user in approver.user_ids:
                            string_test = str(template.message)
                            if "${employee_name}" in string_test:
                                string_test = string_test.replace("${employee_name}", self.employee_id.name)
                            if "${leave_name}" in string_test:
                                string_test = string_test.replace("${leave_name}", self.holiday_status_id.name)
                            if "${duration}" in string_test:
                                string_test = string_test.replace("${duration}", str(self.number_of_days_display))
                            if "${approver_name}" in string_test:
                                string_test = string_test.replace("${approver_name}", user.name)
                            if "${name}" in string_test:
                                string_test = string_test.replace("${name}", self.name)
                            # if "${survey_url}" in string_test:
                            #     string_test = string_test.replace("${survey_url}", url)
                            if "${br}" in string_test:
                                string_test = string_test.replace("${br}", f"\n")
                            phone_num = str(user.mobile_phone)
                            if "+" in phone_num:
                                phone_num = int(phone_num.replace("+", ""))
                            if "${url}" in string_test:
                                string_test = string_test.replace("${url}", f"{base_url}/allocation/{self.id}")
                            
                            wa_sender.set_wa_string(string_test,template._name,template_id=template)
                            wa_sender.send_wa(phone_num)
        #                     param = {'body': string_test, 'phone': phone_num}
        #                     domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
        #                     token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
        #                     try:
        #                         request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param,headers=headers,verify=True)
        #                     except ConnectionError:
        #                         raise ValidationError("Not connect to API Chat Server. Limit reached or not active")
                        

    def approved_wa_template(self):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.send_by_wa')
        if send_by_wa:
            # connector = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_holidays_extend.connector_id')
            # if connector:
            #     connector_id = self.env['acrux.chat.connector'].search([('id', '=', connector)])
            #     if connector_id.ca_status:
            template = self.env.ref('equip3_hr_holidays_extend.leave_allocation_approved_wa_template')
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
            template = self.env.ref('equip3_hr_holidays_extend.leave_allocation_rejected_wa_template')
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
            template = self.env.ref('equip3_hr_holidays_extend.leave_allocation_approver_wa_template')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            wa_sender = waParam()
            if template:
                if rec.approver_user_ids:
                    for matrix_line in sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True)):
                        approver = rec.approver_user_ids[len(matrix_line)]
                        for user in approver.user_ids:
                            string_test = str(template.message)
                            if "${employee_name}" in string_test:
                                string_test = string_test.replace("${employee_name}", rec.employee_id.name)
                            if "${leave_name}" in string_test:
                                string_test = string_test.replace("${leave_name}", rec.holiday_status_id.name)
                            if "${duration}" in string_test:
                                string_test = string_test.replace("${duration}", str(rec.number_of_days_display))
                            if "${approver_name}" in string_test:
                                string_test = string_test.replace("${approver_name}", user.name)
                            if "${name}" in string_test:
                                string_test = string_test.replace("${name}", rec.name)
                            if "${br}" in string_test:
                                string_test = string_test.replace("${br}", f"\n")
                            phone_num = str(user.mobile_phone)
                            if "+" in phone_num:
                                phone_num = int(phone_num.replace("+", ""))
                            if "${url}" in string_test:
                                string_test = string_test.replace("${url}", f"{base_url}/allocation/{rec.id}")
                            
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
        leave_allocation_approve = self.search([('state', '=', 'confirm')])
        for rec in leave_allocation_approve:
            if rec.approver_user_ids:
                matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approver_user_ids[len(matrix_line)]
                for user in approver.user_ids:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_holidays_extend',
                            'email_template_leave_allocation_request')[1]
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
                        'duration': rec.number_of_days_display,
                    })
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_leave - 1
                        query_statement = """UPDATE allocation_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                        self.get_auto_follow_up_approver_wa_template(rec)
                    elif approver.is_auto_follow_approver:
                        if user not in rec.approved_user_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE allocation_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
                            self.get_auto_follow_up_approver_wa_template(rec)
        self.user_delegation_mail()

    @api.model
    def user_delegation_mail(self):
        ir_model_data = self.env['ir.model.data']
        leave_allocation_approve = self.search([('state', '=', 'confirm')])
        for rec in leave_allocation_approve:
            if rec.approver_user_ids:
                matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approver_user_ids[len(matrix_line)]
                if approver.is_auto_follow_approver and approver.repetition_follow_count == 0 and approver.approver_state in ('draft', 'pending') and not approver.is_delegation_mail_sent:
                    for user in approver.matrix_user_ids:
                        if user.user_delegation_id and user.id not in rec.approved_user_ids.ids and user.user_delegation_id.id not in rec.approved_user_ids.ids:
                            try:
                                template_id = ir_model_data.get_object_reference(
                                    'equip3_hr_holidays_extend',
                                    'email_template_leave_allocation_request')[1]
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
                                'duration': rec.number_of_days_display,
                            })
                            approver.update({
                                'user_ids': [(4, user.user_delegation_id.id)],
                                'is_delegation_mail_sent': True,
                            })
                            rec.update({
                                'approvers_ids': [(4, user.user_delegation_id.id)],
                            })
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id, force_send=True)

    def action_confirm(self):
        if self.filtered(lambda holiday: holiday.state != 'draft'):
            raise UserError(_('Allocation request must be in Draft state ("To Submit") in order to confirm it.'))
        self.approver_wa_template()
        self.approver_mail()
        res = self.write({'state': 'confirm'})
        # self.activity_update()
        for line in self.approver_user_ids:
            line.write({'approver_state': 'draft'})
        return res

    def action_refuse(self):
        for record in self:
            # for user in record.approver_user_ids:
            #     now = datetime.now(timezone(self.env.user.tz))
            #     lines = self.approver_user_ids.filtered(lambda line: self.env.user.id in line.user_ids.ids)
            #     for approval_line in lines:
            #         if approval_line:
            #             format_timestamp = f"{self.env.user.name}:{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
            #             format_approve = f"{self.env.user.name}:Refuse"
            #             approval_line.approved_user_ids = [(4, self.env.user.id)]
            #             if not approval_line.approved_time:
            #                 approval_line.approved_time = format_timestamp
            #             else:
            #                 timestamp_list = []
            #                 timestamp_list.append(approval_line.timestamp)
            #                 approval_line.approved_time = "\n".join(format_timestamp)
            #             if not approval_line.approval_status:
            #                 approval_line.approval_status = format_approve
            #                 if record.feedback_parent:
            #                     user.feedback = f"{self.env.user.name}:{record.feedback_parent}"
            #             else:
            #                 approve_list = []
            #                 approve_list.append(approval_line.approval_status)
            #                 approval_line.approval_status = "\n".join(format_approve)
            #                 if record.feedback_parent:
            #                     user.feedback = f"{self.env.user.name}:{record.feedback_parent}"
            for user in record.approver_user_ids:
                for employee in user.user_ids:
                    if self.env.uid == employee.id:
                        user.timestamp = fields.Datetime.now()
                        user.approver_state = 'refuse'
                        if user.approval_status:
                            app_state = user.approval_status + ',' + '\n' + self.env.user.name + ':' + 'Refused'
                            app_time = user.approved_time + ',' + '\n' + self.env.user.name + ':' + str(user.timestamp)
                            if record.feedback_parent:
                                if user.feedback:
                                    feedback = user.feedback + ',' + '\n' + self.env.user.name + ':' + str(record.feedback_parent)
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
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Allocation request must be confirmed or validated in order to refuse it.'))
        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
        # If a category that created several holidays, cancel all related
        linked_requests = self.mapped('linked_request_ids')
        if linked_requests:
            linked_requests.action_refuse()
        self.rejected_wa_template()
        self.reject_mail()
        # self.activity_update()
        return True
    
    def wizard_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.allocation.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'context':{'is_approve':False, 'default_state':'rejected'},
            'target': 'new'
        }

    def action_approve(self):
        now = datetime.now(timezone(self.env.user.tz))
        for record in self:
            if not record.holiday_status_id.allocation_validation_type == 'by_approval_matrix':
                seq_approve = [seq.name for seq in record.approver_user_ids]
                max_seq = max(seq_approve)
                lines = record.approver_user_ids.filtered(lambda line: self.env.user.id in line.user_ids.ids)

                for approval_line in lines:
                    if approval_line:
                        format_timestamp = f"{self.env.user.name}:{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
                        format_approve = f"{self.env.user.name}:Approved"
                        approval_line.approved_user_ids = [(4, self.env.user.id)]
                        approval_line.is_approve = True

                        if not approval_line.approved_time:
                            approval_line.approved_time = format_timestamp
                        else:
                            timestamp_list = []
                            timestamp_list.append(approval_line.timestamp)
                            approval_line.approved_time = "\n".join(format_timestamp)
                        if not approval_line.approval_status:
                            approval_line.approval_status = format_approve
                        else:
                            approve_list = []
                            approve_list.append(approval_line.approval_status)
                            approval_line.approval_status = "\n".join(format_approve)
                        record.approved_user_ids = [(4, self.env.user.id)]
                    approval_line.update_approver_state()

                if any(holiday.state != 'confirm' for holiday in record):
                    raise UserError(_('Allocation request must be confirmed ("To Approve") in order to approve it.'))
                current_employee = self.env.user.employee_id
                if record.holiday_status_id.allocation_type == 'fixed_allocation' \
                        and record.holiday_status_id.allocation_validation_type == 'both':
                    if record.holiday_status_id.responsible_id.id in record.approved_user_ids.ids:
                        record.action_validate()
                    else:
                        record.write({'state': 'validate1', 'first_approver_id': current_employee.id})
                        self.approver_wa_template()
                        self.approver_mail()
                else:
                    record.action_validate()
                    # record.activity_update()
            elif record.holiday_status_id.allocation_validation_type == 'by_approval_matrix':
                self.action_approval_matrix(record)
            else:
                record.action_validate()

    def action_approval_matrix(self, record):
        current_user = self.env.uid
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        if self.env.user not in record.approved_user_ids:
            if not record.is_hide_approve:
                for user in record.approver_user_ids:
                    for employee in user.user_ids:
                        if current_user in employee.ids:
                            sequence_matrix = [data.name for data in record.approver_user_ids]
                            sequence_approval = [data.name for data in record.approver_user_ids.filtered(
                                lambda line: len(line.approved_user_ids) != line.minimum_approver)]
                            max_seq = max(sequence_matrix)
                            min_seq = min(sequence_approval)
                            approval = user.filtered(
                                lambda line: self.env.user.id in line.user_ids.ids and len(
                                    line.approved_user_ids) != line.minimum_approver and line.name == min_seq)
                            if approval:
                                approval.approved_user_ids = [(4, current_user)]
                                user.timestamp = fields.Datetime.now()
                                record.approved_user_ids = [(4, current_user)]
                                timestamp = datetime.strftime(datetime.now().astimezone(local), '%d/%m/%Y %H:%M:%S')
                                if len(approval.approved_user_ids) == approval.minimum_approver:
                                    approval.approver_state = 'approved'
                                    if approval.approval_status:
                                        app_state = approval.approval_status + ',' + '\n' + self.env.user.name + ':' + 'Approved'
                                        app_time = approval.approved_time + ',' + '\n' + self.env.user.name + ':' + str(timestamp)
                                    else:
                                        app_state = self.env.user.name + ':' + 'Approved'
                                        app_time = self.env.user.name + ':' + str(timestamp)
                                    approval.approval_status = app_state
                                    approval.approved_time = app_time
                                    approval.is_approve = True
                                else:
                                    approval.approver_state = 'pending'
                                    if approval.approval_status:
                                        app_state = approval.approval_status + ',' + '\n' + self.env.user.name + ':' + 'Approved'
                                        app_time = approval.approved_time + ',' + '\n' + self.env.user.name + ':' + str(timestamp)
                                    else:
                                        app_state = self.env.user.name + ':' + 'Approved'
                                        app_time = self.env.user.name + ':' + str(timestamp)
                                    approval.approval_status = app_state
                                    approval.approved_time = app_time
                matrix_line = sorted(record.approver_user_ids.filtered(lambda r: r.is_approve == False))
                if len(matrix_line) == 0:
                    self.action_validate()
                else:
                    self.approver_wa_template()
                    self.approver_mail()
            else:
                raise ValidationError(_(
                    'You are not allowed to perform this action!'
                ))
        else:
            raise ValidationError(_(
                'Already approved for this Leave!'
            ))

    def action_validate(self):
        current_employee = self.env.user.employee_id
        for holiday in self:
            if holiday.state not in ['confirm', 'validate1']:
                raise UserError(_('Allocation request must be confirmed in order to approve it.'))

            holiday.write({'state': 'validate'})
            for line in holiday.approver_user_ids:
                line.write({'approver_state': 'approved'})
            if holiday.validation_type == 'both':
                print("///// both")
                holiday.write({'second_approver_id': current_employee.id})
            else:
                print("///// not both")
                holiday.write({'first_approver_id': current_employee.id})

            holiday._action_validate_create_childs()
            leave_balance_active = self.env['hr.leave.balance'].search([('employee_id', '=', holiday.employee_id.id),
                                                                        ('holiday_status_id', '=', holiday.holiday_status_id.id),
                                                                        ('current_period', '=', date.today().year),
                                                                        ('active', '=', True)], limit=1)
            if leave_balance_active:
                if holiday.holiday_status_id.repeated_allocation == True:
                    assigned = leave_balance_active.assigned + holiday.number_of_days_display
                    leave_balance_active.write({'assigned': assigned})
                    leave_balance_id = leave_balance_active
            else:
                leave_balance_id = self.env['hr.leave.balance'].create({'employee_id': holiday.employee_id.id,
                                                                        'holiday_status_id': holiday.holiday_status_id.id,
                                                                        'assigned': holiday.number_of_days_display,
                                                                        'current_period': date.today().year,
                                                                        'start_date': date.today(),
                                                                        'hr_years': date.today().year,
                                                                        'description': "Leave Allocation Request"
                                                                        })
            if holiday.holiday_status_id.allocation_valid_until == 'end_of_year':
                valid_to_date = date(date.today().year, 12, 31)
            elif holiday.holiday_status_id.allocation_valid_until == 'spesific_days':
                valid_specific_month = int(holiday.holiday_status_id.allocation_months_expired)
                valid_specific_date = int(holiday.holiday_status_id.allocation_date_expired)
                valid_to_date = date(date.today().year, valid_specific_month, valid_specific_date)
            elif holiday.holiday_status_id.allocation_valid_until == 'number_of_days':
                valid_to_date = holiday.effective_date + relativedelta(days=holiday.holiday_status_id.expiry_days)

            self.env['hr.leave.count'].create({'employee_id': holiday.employee_id.id,
                                            'holiday_status_id': holiday.holiday_status_id.id,
                                            'count': holiday.number_of_days_display,
                                            'expired_date': valid_to_date,
                                            'start_date': holiday.effective_date,
                                            'hr_years': date.today().year,
                                            'leave_balance_id': leave_balance_id.id,
                                            'description': "Leave Allocation Request"
                                            })
            if holiday.allocation_type_by == 'overtime' and holiday.overtime_id:
                holiday.overtime_id.state = 'convert_as_leave'
        self.approved_wa_template()
        self.approved_mail()
        # self.activity_update()
        return True

    def _compute_approver(self):
        for holiday in self:
            current_user = holiday.env.user
            matrix_line = sorted(holiday.approver_user_ids.filtered(lambda r: r.is_approve == True))
            app = len(matrix_line)
            a = len(holiday.approver_user_ids)
            if app < 2 and app < a and holiday.holiday_status_id.allocation_validation_type != 'by_approval_matrix':
                if current_user in holiday.approver_user_ids[len(matrix_line)].user_ids:
                    holiday.is_hide_approve = False
                else:
                    holiday.is_hide_approve = True
            elif holiday.holiday_status_id.allocation_validation_type == 'by_approval_matrix':
                current_user = holiday.env.user
                matrix_line = sorted(holiday.approver_user_ids.filtered(lambda r: r.is_approve == True))
                app = len(matrix_line)
                a = len(holiday.approver_user_ids)
                if app < a:
                    for line in holiday.approver_user_ids[app]:
                        if current_user in holiday.approved_user_ids:
                            holiday.is_hide_approve = True
                        elif current_user in line.user_ids:
                            holiday.is_hide_approve = False
                        else:
                            holiday.is_hide_approve = True
                else:
                    holiday.is_hide_approve = True
            else:
                holiday.is_hide_approve = True

    def approve_by_matrix(self):
        pass

    def get_manager_hierarchy(self, leave_allocation, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(leave_allocation, employee_manager['parent_id'], data, manager_ids, seq, level)
                break
        return manager_ids

    @api.onchange('employee_id', 'holiday_status_id')
    def onchange_approver(self):
        for leave_cancel in self:
            app_list = []
            if leave_cancel.employee_id and leave_cancel.holiday_status_id.allocation_type != 'fixed_allocation':
                responsible = leave_cancel.holiday_status_id.responsible_id
                if responsible:
                    app_list.append(responsible.id)
            else:
                if leave_cancel.employee_id and leave_cancel.holiday_status_id.allocation_validation_type == 'hr':
                    responsible = leave_cancel.holiday_status_id.responsible_id
                    if responsible:
                        app_list.append(responsible.id)
                elif leave_cancel.employee_id and leave_cancel.holiday_status_id.allocation_validation_type == 'manager':
                    emp_manager = leave_cancel.employee_id.parent_id.user_id
                    if emp_manager:
                        app_list.append(emp_manager.id)
                elif leave_cancel.employee_id and leave_cancel.holiday_status_id.allocation_validation_type == 'both':
                    both_emp_manager = leave_cancel.employee_id.parent_id.user_id
                    both_responsible = leave_cancel.holiday_status_id.responsible_id
                    if both_emp_manager:
                        app_list.append(both_emp_manager.id)
                    if both_responsible:
                        app_list.append(both_responsible.id)
            leave_cancel.approvers_ids = app_list

    @api.onchange('holiday_status_id', 'employee_id')
    def _onchange_holiday_status_id(self):
        for record in self:
            if record.holiday_status_id:
                if record.approver_user_ids:
                    line_remove = []
                    for line in record.approver_user_ids:
                        line_remove.append((2, line.id))
                    record.approver_user_ids = line_remove
                if record.holiday_status_id.allocation_type != 'fixed_allocation':
                    if not record.holiday_status_id.responsible_id:
                        raise ValidationError(f"Responsible not set in leave types {record.holiday_status_id.name}")
                    line_data = [(0, 0, {'user_ids': [(4, record.holiday_status_id.responsible_id.id)]})]
                    record.approver_user_ids = line_data
                elif record.holiday_status_id.allocation_type == 'fixed_allocation':
                    if record.holiday_status_id.allocation_validation_type == 'hr':
                        if not record.holiday_status_id.responsible_id:
                            raise ValidationError(f"Responsible not set in leave types {record.holiday_status_id.name}")
                        line_data = [(0, 0, {'user_ids': [(4, record.holiday_status_id.responsible_id.id)]})]
                        record.approver_user_ids = line_data
                    if record.holiday_status_id.allocation_validation_type == 'manager':
                        if not record.employee_id.parent_id:
                            raise ValidationError(f"Manager not set in Employee {record.employee_id.name}")
                        if not record.employee_id.parent_id.user_id:
                            raise ValidationError(f"User not set in Employee {record.employee_id.parent_id.name}")
                        line_data = [(0, 0, {'user_ids': [(4, record.employee_id.parent_id.user_id.id)]})]
                        record.approver_user_ids = line_data
                    if record.holiday_status_id.allocation_validation_type == 'both':
                        if not record.employee_id.parent_id:
                            raise ValidationError(f"Manager not set in Employee {record.employee_id.name}")
                        if not record.employee_id.parent_id.user_id:
                            raise ValidationError(f"User not set in Employee {record.employee_id.parent_id.name}")
                        if not record.holiday_status_id.responsible_id:
                            raise ValidationError(f"Responsible not set in leave types {record.holiday_status_id.name}")
                        line_data = [(0, 0, {'user_ids': [(4, record.employee_id.parent_id.user_id.id)]})]
                        line_data.append((0, 0, {'user_ids': [(4, record.holiday_status_id.responsible_id.id)]}))
                        record.approver_user_ids = line_data
                    if record.holiday_status_id.allocation_validation_type == 'by_approval_matrix':
                        app_list = []
                        leave_type_matrix = self.env['hr.leave.approval'].search(
                            [('mode_type', '=', 'leave_type'), ('leave_type_ids', 'in', record.holiday_status_id.id), (
                        'applicable_to', 'in', ['allocation_request', 'leave_and_allocation_request'])], limit=1)
                        employee_matrix = self.env['hr.leave.approval'].search(
                            [('mode_type', '=', 'employee'), ('employee_ids', 'in', record.employee_id.id), (
                        'applicable_to', 'in', ['allocation_request', 'leave_and_allocation_request'])], limit=1)
                        job_position_matrix = self.env['hr.leave.approval'].search(
                            [('mode_type', '=', 'job_position'), ('job_ids', 'in', record.employee_id.job_id.id), (
                        'applicable_to', 'in', ['allocation_request', 'leave_and_allocation_request'])], limit=1)
                        department_matrix = self.env['hr.leave.approval'].search(
                            [('mode_type', '=', 'department'), ('department_ids', 'in', record.employee_id.department_id.id), (
                        'applicable_to', 'in', ['allocation_request', 'leave_and_allocation_request'])], limit=1)
                        if leave_type_matrix:
                            data_approvers = []
                            for line in leave_type_matrix.leave_approvel_matrix_ids:
                                if line.approver_types == "specific_approver":
                                    data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                                  'user_ids': [(6, 0, line.approver_ids.ids)]}))
                                    for approvers in line.approver_ids:
                                        app_list.append(approvers.id)
                                elif line.approver_types == "by_hierarchy":
                                    manager_ids = []
                                    seq = 1
                                    data = 0
                                    approvers = self.get_manager_hierarchy(record, record.employee_id, data,
                                                                           manager_ids, seq,
                                                                           line.minimum_approver)
                                    for approver in approvers:
                                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                        app_list.append(approver)
                            record.approvers_ids = app_list
                            record.approver_user_ids = data_approvers
                        elif employee_matrix:
                            data_approvers = []
                            for line in employee_matrix.leave_approvel_matrix_ids:
                                if line.approver_types == "specific_approver":
                                    data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                                  'user_ids': [(6, 0, line.approver_ids.ids)]}))
                                    for approvers in line.approver_ids:
                                        app_list.append(approvers.id)
                                elif line.approver_types == "by_hierarchy":
                                    manager_ids = []
                                    seq = 1
                                    data = 0
                                    approvers = self.get_manager_hierarchy(record, record.employee_id, data,
                                                                           manager_ids, seq,
                                                                           line.minimum_approver)
                                    for approver in approvers:
                                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                        app_list.append(approver)
                            record.approvers_ids = app_list
                            record.approver_user_ids = data_approvers
                        elif job_position_matrix:
                            data_approvers = []
                            for line in job_position_matrix.leave_approvel_matrix_ids:
                                if line.approver_types == "specific_approver":
                                    data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                                  'user_ids': [(6, 0, line.approver_ids.ids)]}))
                                    for approvers in line.approver_ids:
                                        app_list.append(approvers.id)
                                elif line.approver_types == "by_hierarchy":
                                    manager_ids = []
                                    seq = 1
                                    data = 0
                                    approvers = self.get_manager_hierarchy(record, record.employee_id, data,
                                                                           manager_ids, seq,
                                                                           line.minimum_approver)
                                    for approver in approvers:
                                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                        app_list.append(approver)
                            record.approvers_ids = app_list
                            record.approver_user_ids = data_approvers
                        elif department_matrix:
                            data_approvers = []
                            for line in department_matrix.leave_approvel_matrix_ids:
                                if line.approver_types == "specific_approver":
                                    data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                                  'user_ids': [(6, 0, line.approver_ids.ids)]}))
                                    for approvers in line.approver_ids:
                                        app_list.append(approvers.id)
                                elif line.approver_types == "by_hierarchy":
                                    manager_ids = []
                                    seq = 1
                                    data = 0
                                    approvers = self.get_manager_hierarchy(record, record.employee_id, data,
                                                                           manager_ids, seq,
                                                                           line.minimum_approver)
                                    for approver in approvers:
                                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                        app_list.append(approver)
                            record.approvers_ids = app_list
                            record.approver_user_ids = data_approvers
        # for record in self:
        #     if record.holiday_status_id:
        #         if record.approver_user_ids:
        #             line_remove = []
        #             for line in record.approver_user_ids:
        #                 line_remove.append((2, line.id))
        #             record.approver_user_ids = line_remove
        #         if record.holiday_status_id.allocation_type != 'fixed_allocation':
        #             if not record.employee_id.parent_id:
        #                 raise ValidationError(f"Manager not set in Employee {record.employee_id.name}")
        #             if not record.employee_id.parent_id.user_id:
        #                 raise ValidationError(f"User not set in Employee {record.employee_id.parent_id.name}")
        #             if not record.holiday_status_id.responsible_id:
        #                 raise ValidationError(f"Responsible not set in leave types {record.holiday_status_id.name}")
        #             line_data = [(0, 0, {'user_ids': [(4, record.employee_id.parent_id.user_id.id)]})]
        #             line_data.append((0, 0, {'user_ids': [(4, record.holiday_status_id.responsible_id.id)]}))
        #             record.approver_user_ids = line_data
                leave_balance_active = self.env['hr.leave.balance'].search([('employee_id', '=', record.employee_id.id),
                                                                            ('holiday_status_id', '=',
                                                                             record.holiday_status_id.id),
                                                                            ('active', '=', True)])
                if leave_balance_active and record.holiday_status_id.repeated_allocation == False:
                    raise ValidationError(_('Already allocated for this leave type, please choose another leave type.'))

    @api.onchange('allocation_half_day', 'allocation_date_from', 'allocation_date_to')
    def onchange_allocation_half_day(self):
        for res in self:
            if res.allocation_half_day:
                res.number_of_days_display = 0.5
            else:
                if res.allocation_date_from and res.allocation_date_to:
                    d1 = datetime.strptime(str(res.allocation_date_from), "%Y-%m-%d")
                    d2 = datetime.strptime(str(res.allocation_date_to), "%Y-%m-%d")
                    diff_day =  abs((d2 - d1).days)
                    res.number_of_days_display = diff_day + 1
                else:
                    res.number_of_days_display = 1.0

    @api.onchange('holiday_status_id', 'employee_id')
    def _onchange_domain_overtime(self):
        if self.holiday_status_id:
            period = date.today() + relativedelta(days=self.holiday_status_id.min_days_before_alloc)
        else:
            period = date.today()
        if self.employee_id:
            employee = self.employee_id.id
        else:
            employee = -1
        domain = {'domain': {'overtime_id': [('period_start', '>=', period),('employee_id', '=', employee),('applied_to','=','extra_leave')]}}
        return domain

    @api.onchange('overtime_id', 'holiday_status_id')
    def onchange_overtime_id(self):
        for res in self:
            if res.holiday_status_id and res.overtime_id:
                res.number_of_days_display = 0.0
                formula = res.holiday_status_id.formula
                if res.holiday_status_id.total_actual_hours:
                    localdict = {"actual_hours": res.overtime_id.total_actual_hours,"duration": 0.0}
                    safe_eval(formula, localdict, mode='exec', nocopy=True)
                    res.number_of_days_display = localdict['duration']
                else:
                    total_duration = 0.0
                    for line in res.overtime_id.actual_line_ids:
                        localdict = {"actual_hours": line.actual_hours,"duration": 0.0}
                        safe_eval(formula, localdict, mode='exec', nocopy=True)
                        total_duration += localdict['duration']
                    res.number_of_days_display = total_duration

class AllocationApproverUser(models.Model):
    _name = 'allocation.approver.user'
    
    leave_id = fields.Many2one('hr.leave.allocation', string="Leave")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_user_ids = fields.Many2many('res.users', 'approved_users_allocation_rel', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")
    approval_status = fields.Text(string="Approval Status")
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    matrix_user_ids = fields.Many2many('res.users', 'allo_max_user_ids', string="Matrix user")
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
            if not rec.matrix_user_ids and rec.leave_id.state == 'draft':
                rec.matrix_user_ids = rec.user_ids

    def update_approver_state(self):
        for rec in self:
            if rec.leave_id.state == 'confirm':
                if not rec.approved_user_ids:
                    rec.approver_state = 'draft'
                elif rec.approved_user_ids and rec.minimum_approver == len(rec.approved_user_ids):
                    rec.approver_state = 'approved'
                else:
                    rec.approver_state = 'pending'