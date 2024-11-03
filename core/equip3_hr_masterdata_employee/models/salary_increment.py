from odoo import fields,api,models
from odoo.exceptions import UserError, ValidationError


class HrEmployeeSalaryIncrement(models.Model):
    _inherit = 'hr.salary.increment'

    state1 = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Submitted'),
                              ('generated', 'Generated'), ('rejected', 'Rejected')], default='draft', copy=False,
                              store=True, string='Status', compute='_compute_state1')
    is_salary_increment_approval_matrix = fields.Boolean("Is Salary Increment Approval Matrix", compute='_compute_salary_increment_approval_matrix')

    @api.depends('state')
    def _compute_state1(self):
        for record in self:
            record.state1 = record.state

    def _compute_salary_increment_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.salary_increment_approval_matrix')
            rec.is_salary_increment_approval_matrix = setting

    @api.onchange('employee_id')
    def onchange_employee(self):
        setting_salary_increment_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.salary_increment_approval_matrix')
        setting_salary_increment_approval_method = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.salary_increment_approval_method')
        if setting_salary_increment_approval_matrix:
            for record in self:
                if record.employee_id:
                    if record.approver_user_ids:
                        remove = []
                        for line in record.approver_user_ids:
                            remove.append((2, line.id))
                        record.approver_user_ids = remove
                    if setting_salary_increment_approval_method == 'approval_matrix':
                        self.approval_by_matrix(record)
                    if setting_salary_increment_approval_method == 'employee_hierarchy':
                        record.approver_user_ids = self.salary_emp_by_hierarchy(record)
                        self.app_list_salary_emp_by_hierarchy()

    def app_list_salary_emp_by_hierarchy(self):
        for record in self:
            app_list = []
            for line in record.approver_user_ids:
                app_list.append(line.approver_id.id)
            record.approvers_ids = app_list

    def salary_emp_by_hierarchy(self, record):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(record, record.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, cash, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.salary_level')
        if not setting_level:
            raise ValidationError("level not set")
        if not employee_manager['parent_id']['user_id']:
            return approval_ids
        while data < int(setting_level):
            approval_ids.append(
                (0, 0, {'approver_id': [(4, employee_manager['parent_id']['user_id']['id'])]}))
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager(cash, employee_manager['parent_id'], data, approval_ids, seq)
                break
        return approval_ids

    def submit(self):
        setting_salary_increment_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.salary_increment_approval_matrix')
        for rec in self:
            if setting_salary_increment_approval_matrix:
                rec.state = "to_approve"
                rec.approver_mail()
            else:
                rec.state = "approved"