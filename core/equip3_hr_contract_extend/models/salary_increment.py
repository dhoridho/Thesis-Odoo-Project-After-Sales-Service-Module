from odoo import fields,api,models,_
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

class HrSalaryIncrement(models.Model):
    _name = 'hr.salary.increment'
    _description="Salary Increment"

    @api.returns('self')
    def _get_employee(self):
        emp = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        return emp or False

    def _default_domain_emp(self):
        emp_list = []
        for res in self.env['hr.contract'].search([('state','=','open')]):
            emp_list.append(res.employee_id.id)
        return [('id', 'in', emp_list)]

    name = fields.Char(string='Sequence Number', copy=False)
    apply_to = fields.Selection(
        [('by_employee', 'By Employee'),
         ('by_job', 'By Job Position'),
         ('by_department', 'By Department'),
        #  ('by_company', 'By Company'),
         ], string="Apply To")
    employee_id = fields.Many2one('hr.employee', string='Employee', default=_get_employee)
    employee_ids = fields.Many2many('hr.employee', string="Employees", domain=_default_domain_emp)
    job_ids = fields.Many2many('hr.job', string="Job Position")
    department_ids = fields.Many2many('hr.department', string="Departments")
    company_ids = fields.Many2many('res.company', string="Companies")
    based_on = fields.Selection(
        [('fix_amount', 'Fix Amount'),
         ('percentage', 'Percentage'),
         ], string="Based On")
    amount = fields.Float("Amount")
    percentage = fields.Float("Percentage")
    effective_date = fields.Date(string="Effective Date")
    state = fields.Selection([('draft', 'Draft'), ('to_approve', 'To Approve'), ('approved', 'Approved'),
                              ('generated', 'Generated'),('rejected', 'Rejected')], default='draft', copy=False, string='Status')
    line_ids = fields.One2many('hr.salary.increment.line', 'parent_id', string="Salary Increment Details")
    approvers_ids = fields.Many2many('res.users', 'approver_users_salary_rel', string='Approvers')
    is_approver = fields.Boolean(string="Is Approver", compute="_compute_can_approve")
    approver_user_ids = fields.One2many('salary.increment.approver.user', 'salary_increment_id', string='Approver')
    approved_user_ids = fields.Many2many('res.users', string='Approved User')
    is_readonly = fields.Boolean(compute='_compute_is_readonly')
    
    @api.depends('apply_to')
    def _compute_is_readonly(self):
        for record in self:
            if self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader'):
                record.is_readonly = True
            else:
                record.is_readonly = False
            
    
    
    @api.model
    def default_get(self, fields):
        res = super(HrSalaryIncrement, self).default_get(fields)
        if self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader'):
            res['apply_to'] = 'by_employee'
            res['employee_ids'] = [(6,0,[self.env.user.employee_id.id])]
            print(res)
        
        
        return res
    
    
    def get_menu(self):
        # views = [(self.env.ref('equip3_hr_masterdata_employee.hr_employee_change_request_tree_view').id, 'tree'),
        #          (self.env.ref('equip3_hr_masterdata_employee.hr_employee_change_request_form_view').id, 'form')]
        if self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Salary Increment',
                'res_model': 'hr.salary.increment',
                'view_mode': 'tree,form',
                # 'views': views,
                'domain': [('employee_id','=',self.env.user.employee_id.id)],
                'context': {}

            }
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Salary Increment',
                'res_model': 'hr.salary.increment',
                'view_mode': 'tree,form',
                # 'views': views,
                'domain': [('employee_id','in',employee_ids)],
                'context': {}

            }
            
            
        return {
                'type': 'ir.actions.act_window',
                'name': 'Salary Increment',
                'res_model': 'hr.salary.increment',
                'view_mode': 'tree,form',
                # 'views': views,
                'domain': [],
                'context': {}

            }

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('hr.salary.increment')
        vals.update({'name': sequence})
        return super(HrSalaryIncrement, self).create(vals)

    @api.onchange('employee_id')
    def onchange_employee(self):
        for record in self:
            if record.employee_id:
                if record.approver_user_ids:
                    remove = []
                    for line in record.approver_user_ids:
                        remove.append((2, line.id))
                    record.approver_user_ids = remove
                self.approval_by_matrix(record)

    @api.onchange('apply_to')
    def onchange_apply_to(self):
        for rec in self:
            # rec.employee_ids = [(5, 0, 0)]
            rec.job_ids = [(5, 0, 0)]
            rec.department_ids = [(5, 0, 0)]
            rec.company_ids = [(5, 0, 0)]

    @api.onchange('based_on')
    def onchange_based_on(self):
        for rec in self:
            rec.amount = 0.0
            rec.percentage = 0.0

    @api.onchange('apply_to','employee_ids','job_ids','department_ids','company_ids','based_on','amount','percentage')
    def onchange_salary_increment(self):
        for rec in self:
            if (not rec.apply_to) or (not rec.based_on):
                return
            
            if rec.line_ids:
                remove = []
                for line in rec.line_ids:
                    remove.append((2, line.id))
                rec.line_ids = remove
            
            contracts = self.env['hr.contract']
            if rec.apply_to == "by_employee":
                if (not rec.employee_ids):
                    return
                contracts = self.env['hr.contract'].search([('employee_id','in',rec.employee_ids.ids),('state','=','open')])
            elif rec.apply_to == "by_job":
                if (not rec.job_ids):
                    return
                contracts = self.env['hr.contract'].search([('job_id','in',rec.job_ids.ids),('state','=','open'),('employee_id','!=',False)], order="job_id asc")
            elif rec.apply_to == "by_department":
                if (not rec.department_ids):
                    return
                contracts = self.env['hr.contract'].search([('department_id','in',rec.department_ids.ids),('state','=','open'),('employee_id','!=',False)], order="job_id asc")
            elif rec.apply_to == "by_company":
                if (not rec.company_ids):
                    return
                contracts = self.env['hr.contract'].search([('company_id','in',rec.company_ids.ids),('state','=','open'),('employee_id','!=',False)], order="job_id asc")
            if not contracts:
                raise ValidationError("There is no data!")
            
            increment_details = []
            seq = 1
            for contract in contracts:
                new_salary = self.calculate_base_on(contract.wage)
                increment_details.append((0, 0, {'sequence': seq,
                                    'employee_id': contract.employee_id.id,
                                    'job_id': contract.job_id.id,
                                    'last_salary': contract.wage,
                                    'new_salary': new_salary
                                    }))
                seq += 1
            rec.line_ids = increment_details

    def get_manager_hierarchy(self, changes, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(changes, employee_manager['parent_id'], data, manager_ids, seq, level)
                break
        return manager_ids
    
    def approval_by_matrix(self, record):
        approval_matrix = self.env['salary.increment.approval.matrix'].search([('apply_to', '=', 'employee')])
        matrix = approval_matrix.filtered(lambda line: record.employee_id.id in line.employee_ids.ids)
        app_list = []
        if matrix:
            data_approvers = []
            for line in matrix[0].approval_matrix_ids:
                if line.approver_types == "specific_approver":
                    data_approvers.append((0, 0, {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                  'approver_id': [(6, 0, line.approver_ids.ids)]}))
                    for approvers in line.approver_ids:
                        app_list.append(approvers.id)
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data = 0
                    approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                           line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                        app_list.append(approver)
            record.approvers_ids = app_list
            record.approver_user_ids = data_approvers
        if not matrix:
            data_approvers = []
            approval_matrix = self.env['salary.increment.approval.matrix'].search(
                [('apply_to', '=', 'job_position')])
            matrix = approval_matrix.filtered(lambda line: record.employee_id.job_id.id in line.job_ids.ids)
            if matrix:
                for line in matrix[0].approval_matrix_ids:
                    if line.approver_types == "specific_approver":
                        data_approvers.append((0, 0, {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                      'approver_id': [(6, 0, line.approver_ids.ids)]}))
                        for approvers in line.approver_ids:
                            app_list.append(approvers.id)
                    elif line.approver_types == "by_hierarchy":
                        manager_ids = []
                        seq = 1
                        data = 0
                        approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                               line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                            app_list.append(approver)
                record.approvers_ids = app_list
                record.approver_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['salary.increment.approval.matrix'].search(
                    [('apply_to', '=', 'department')])
                matrix = approval_matrix.filtered(lambda line: record.employee_id.department_id.id in line.department_ids.ids)
                if matrix:
                    for line in matrix[0].approval_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0, 0,
                                                   {'sequence': line.sequence, 'minimum_approver': line.minimum_approver,
                                                    'approver_id': [(6, 0, line.approver_ids.ids)]}))
                            for approvers in line.approver_ids:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(record, record.employee_id, data, manager_ids, seq,
                                                                   line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'approver_id': [(4, approver)]}))
                                app_list.append(approver)
                    record.approvers_ids = app_list
                    record.approver_user_ids = data_approvers
    
    @api.depends('approver_user_ids','approved_user_ids')
    def _compute_can_approve(self):
        for rec in self:
            current_user = rec.env.user
            if current_user in rec.approvers_ids and current_user not in rec.approved_user_ids:
                rec.is_approver = True
            else:
                rec.is_approver = False

    def submit(self):
        for rec in self:
            rec.state = "to_approve"
            rec.approver_mail()
    
    def get_url(self, obj):
        url = ''
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_contract_extend', 'hr_salary_increment_menu')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'equip3_hr_contract_extend', 'hr_salary_increment_act_window')[1]
        url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(
            obj.id) + "&view_type=form&model=hr.salary.increment&menu_id=" + str(
            menu_id) + "&action=" + str(action_id)
        return url
    
    def approver_mail(self):
        ir_model_data = self.env['ir.model.data']
        for rec in self:
            if rec.approver_user_ids:
                matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approver_user_ids[len(matrix_line)]
                for user in approver.approver_id:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_contract_extend',
                            'email_template_approver_of_salary_increment')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(self)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': user.email,
                        'url': url,
                        'approver_name': user.name,
                        'request_user': rec.create_uid.name,
                    })
                    self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(self.id, force_send=True)
                break
    
    def approve(self):
        self.approver_user_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'salary.increment.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_salary_increment_id':self.id,'default_state': 'approved'},
        }
    
    def reject(self):
        self.approver_user_ids.update_approver_state()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'salary.increment.approval.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_salary_increment_id':self.id, 'default_state': 'rejected'},
        }
    
    def calculate_base_on(self, wage):
        salary = 0.0
        if self.based_on == "fix_amount":
            salary = wage + self.amount
        else:
            percent = wage * self.percentage
            salary = wage + percent
        return salary
    
    def generate(self):
        for rec in self:
            if rec.apply_to == "by_employee":
                contracts = self.env['hr.contract'].search([('employee_id','in',rec.employee_ids.ids),('state','=','open')])
                for contract in contracts:
                    salary = self.calculate_base_on(contract.wage)
                    contract.copy({'wage': salary, 'date_start': rec.effective_date})
                    date_end_before = (rec.effective_date - relativedelta(days=1)).strftime('%Y-%m-%d')
                    contract.write({'date_end': date_end_before})
            elif rec.apply_to == "by_job":
                contracts = self.env['hr.contract'].search([('job_id','in',rec.job_ids.ids),('state','=','open'),('employee_id','!=',False)])
                for contract in contracts:
                    salary = self.calculate_base_on(contract.wage)
                    contract.copy({'wage': salary, 'date_start': rec.effective_date})
                    date_end_before = (rec.effective_date - relativedelta(days=1)).strftime('%Y-%m-%d')
                    contract.write({'date_end': date_end_before})
            elif rec.apply_to == "by_department":
                contracts = self.env['hr.contract'].search([('department_id','in',rec.department_ids.ids),('state','=','open'),('employee_id','!=',False)])
                for contract in contracts:
                    salary = self.calculate_base_on(contract.wage)
                    contract.copy({'wage': salary, 'date_start': rec.effective_date})
                    date_end_before = (rec.effective_date - relativedelta(days=1)).strftime('%Y-%m-%d')
                    contract.write({'date_end': date_end_before})
            elif rec.apply_to == "by_company":
                contracts = self.env['hr.contract'].search([('company_id','in',rec.company_ids.ids),('state','=','open'),('employee_id','!=',False)])
                for contract in contracts:
                    salary = self.calculate_base_on(contract.wage)
                    contract.copy({'wage': salary, 'date_start': rec.effective_date})
                    date_end_before = (rec.effective_date - relativedelta(days=1)).strftime('%Y-%m-%d')
                    contract.write({'date_end': date_end_before})
            rec.state = "generated"
    
    @api.model
    def get_auto_follow_up_approver(self):
        ir_model_data = self.env['ir.model.data']
        number_of_repetitions_salary_increment = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_contract_extend.number_of_repetitions_salary_increment'))
        salary_increment_approve = self.search([('state', '=', 'to_approve')])
        for rec in salary_increment_approve:
            if rec.approver_user_ids:
                matrix_line = sorted(rec.approver_user_ids.filtered(lambda r: r.is_approve == True))
                approver = rec.approver_user_ids[len(matrix_line)]
                for user in approver.approver_id:
                    try:
                        template_id = ir_model_data.get_object_reference(
                            'equip3_hr_contract_extend',
                            'email_template_approver_of_salary_increment')[1]
                    except ValueError:
                        template_id = False
                    ctx = self._context.copy()
                    url = self.get_url(self)
                    ctx.update({
                        'email_from': self.env.user.email,
                        'email_to': user.email,
                        'url': url,
                        'approver_name': user.name,
                        'request_user': rec.create_uid.name,
                    })
                    if not approver.is_auto_follow_approver:
                        count = number_of_repetitions_salary_increment - 1
                        query_statement = """UPDATE salary_increment_approver_user set is_auto_follow_approver = TRUE, repetition_follow_count = %s WHERE id = %s """
                        self.sudo().env.cr.execute(query_statement, [count, approver.id])
                        self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                  force_send=True)
                    elif approver.is_auto_follow_approver:
                        if user not in approver.approved_employee_ids and approver.repetition_follow_count > 0:
                            count = approver.repetition_follow_count - 1
                            query_statement = """UPDATE salary_increment_approver_user set repetition_follow_count = %s WHERE id = %s """
                            self.sudo().env.cr.execute(query_statement, [count, approver.id])
                            self.env['mail.template'].browse(template_id).with_context(ctx).send_mail(rec.id,
                                                                                                      force_send=True)
    
    @api.constrains('line_ids')
    def _check_new_salary(self):
        for rec in self:
            for line in rec.line_ids:
                if line.new_salary <= line.last_salary:
                    raise ValidationError(_("New salary must be greater than last salary"))
    
class HrSalaryIncrementLine(models.Model):
    _name = 'hr.salary.increment.line'

    parent_id = fields.Many2one('hr.salary.increment', string="Parent Id")
    sequence = fields.Integer('Sequence', compute="fetch_sl_no")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    job_id = fields.Many2one('hr.job', string="Job Position")
    last_salary = fields.Float('Last Salary')
    new_salary = fields.Float('New Salary')

    @api.depends('parent_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.parent_id.line_ids:
            sl = sl + 1
            line.sequence = sl

class LeaveApproverUser(models.Model):
    _name = 'salary.increment.approver.user'

    salary_increment_id = fields.Many2one('hr.salary.increment', string="Salary Increment")
    sequence = fields.Integer('Sequence', compute="fetch_sl_no")
    approver_id = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'salary_inc_approved_users_rel', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    approval_status = fields.Text(string="Approval Status")
    timestamp = fields.Text('Timestamp')
    feedback = fields.Text('Feedback')
    is_approve = fields.Boolean(string="Is Approve", default=False)
    is_auto_follow_approver = fields.Boolean()
    repetition_follow_count = fields.Integer()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='draft', string="State")
    #parent status
    state = fields.Selection(string='Parent Status', related='salary_increment_id.state')

    @api.depends('salary_increment_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.salary_increment_id.approver_user_ids:
            sl = sl + 1
            line.sequence = sl
        self.update_minimum_app()
    
    def update_minimum_app(self):
        for rec in self:
            if len(rec.approver_id) < rec.minimum_approver:
                rec.minimum_approver = len(rec.approver_id)
    
    def update_approver_state(self):
        for rec in self:
            if rec.salary_increment_id.state == 'to_approve':
                if not rec.approved_employee_ids:
                    rec.approver_state = 'draft'
                elif rec.approved_employee_ids and rec.minimum_approver == len(rec.approved_employee_ids):
                    rec.approver_state = 'approved'
                else:
                    rec.approver_state = 'pending'
            if rec.salary_increment_id.state == 'rejected':
                rec.approver_state = 'refuse'