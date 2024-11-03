from odoo import _, api, fields, models
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo.addons.phone_validation.tools import phone_validation
from lxml import etree

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_employee_change_req_approval_matrix = fields.Boolean("Is Employee Change Request Approval Matrix", compute='_compute_approval_matrix')

    def _compute_approval_matrix(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_masterdata_employee.emp_change_req_approval_matrix')
            rec.is_employee_change_req_approval_matrix = setting


    def phone_format(self, number, country=None, company=None):
        country = country
        if not country:
            return number
        ## force format: E164, RFC3966, INTERNATIONAL ##
        return phone_validation.phone_format(
            number,
            country.code if country else None,
            country.phone_code if country else None,
            force_format='E164',
            raise_exception=False
        )

    @api.model
    def create(self, vals):
        emp_seq = self.env['ir.config_parameter'].sudo().get_param(
            'equip3_hr_masterdata_employee.emp_seq', ) or False
        if emp_seq == 'True':
            sequence = self.env['ir.sequence'].next_by_code('hr.employee')
            vals.update({'sequence_code': sequence})
        return super(HrEmployee, self).create(vals)

    @api.onchange('classification_id', 'job_id')
    def onchange_domain_experience_level(self):
        res = {}
        classify_list = []
        for vals in self.classification_id.classify_detail_ids:
            for exp in vals.experience_ids:
                classify_list.append(exp.id)
        res['domain'] = {'experience_id': [('id', 'in', classify_list)]}
        return res

    @api.onchange('experience_id', 'grade_id')
    def onchange_domain_grade(self):
        res = {}
        grade_list = []
        if self.experience_id:
            for vals in self.classification_id.classify_detail_ids:
                for exp in vals.experience_ids:
                    for grade in vals.grade_id:
                        if self.experience_id == exp:
                            grade_list.append(grade.id)
                res['domain'] = {'grade_id': [('id', 'in', grade_list)]}
        return res

    @api.onchange('experience_id', 'job_id')
    def onchange_domain_null_experience(self):
        res = {}
        grade_list = False
        if not self.experience_id:
            self.grade_id = False
            res['domain'] = {'grade_id': [('id', 'in', grade_list)]}
        if self.experience_id:
            self.grade_id = False
        return res

    @api.depends('company_id')
    def compute_emp_seq(self):
        emp_seq = self.env['ir.config_parameter'].sudo().get_param(
            'equip3_hr_masterdata_employee.emp_seq') or False
        for emp in self:
            if emp_seq == 'True':
                emp.emp_seq = True
            else:
                emp.emp_seq = False
                
    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]
    
    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    

    emp_seq = fields.Boolean(string="Employee ID Sequence Number", compute='compute_emp_seq')
    sequence_code = fields.Char(string="Employee ID")
    years_of_service = fields.Integer(string="Years of Service", compute='compute_year_of_service')
    months = fields.Integer(compute='compute_year_of_service')
    days = fields.Integer(compute='compute_year_of_service')
    year = fields.Char(string=' ', default='year(s) -')
    month = fields.Char(string=' ', default='month(s) -')
    day = fields.Char(string=' ', default='day(s)')
    location_id = fields.Many2one('work.location.object', string='Work Location',domain=_multi_company_domain)
    religion_id = fields.Many2one('employee.religion', string='Religion',domain=_multi_company_domain)
    experience_id = fields.Many2one('employee.job.experience.level', string='Job Experience Level')
    classification_id = fields.Many2one("employee.job.classification", string="Job Classification",
                                        related="job_id.classification_id")
    grade_id = fields.Many2one('employee.grade', string='Grade')
    # cost_center_id = fields.Many2one('cost.center', string='Cost center')
    race_id = fields.Many2one('employee.race', string='Race',domain=_multi_company_domain)
    birth_years = fields.Integer(string="Years of Service", compute='compute_birth_year', store=True)
    birth_months = fields.Integer(compute='compute_birth_year', compute_sudo=True)
    birth_days = fields.Integer(compute='compute_birth_year', compute_sudo=True)
    birth_year = fields.Char(string=' ', default='year(s) -')
    birth_month = fields.Char(string=' ', default='month(s) -')
    birth_day = fields.Char(string=' ', default='day(s)')
    state_id = fields.Many2one('res.country.state', "Province(State)")
    current_address = fields.Text(string='Current Address')
    identity_address = fields.Text(string='Identity Address')
    education_ids = fields.One2many('hr.employee.education', 'employee_id', string="Education")
    health_ids = fields.One2many('employee.health.records', 'employee_id', string="Health Record")
    emergency_ids = fields.One2many('employee.emergency.contact', 'employee_id', string="Emergency Contact")
    address_ids = fields.One2many('hr.employee.address', 'employee_id', string="Addresses")
    blood_type = fields.Char(string='Blood Type')
    height = fields.Float(string='Height (CM)')
    weight = fields.Float(string='Weight (KG)')
    bank_ids = fields.One2many('bank.account', 'employee_id', string="Bank Account")
    fam_ids = fields.One2many('hr.employee.family', 'employee_id', string="Family")
    private_email = fields.Char(store=True,readonly=False)
    phone = fields.Char(store=True,readonly=False)
    contract_line_ids = fields.One2many('employee.contract', 'employee_id', string="Contracts History")
    province_wage_id = fields.Many2one('res.country.state', "Province Wage", domain="[('country_id','=',100)]")
    marital = fields.Many2one('employee.marital.status', string='Marital Status')
    payslip_password = fields.Char('Payslip Password')
    gender = fields.Selection("_gender_selection", string='Gender', groups="hr.group_hr_user", tracking=True)
    restrict_org_chart_link = fields.Html(string='Restrict Org Chart Link', sanitize=False)
    address_home_id = fields.Many2one(
        'res.partner', 'Address',
        help='Enter here the private address of the employee, not the one linked to your company.',
        groups="hr.group_hr_user", tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", related='user_id.partner_id')
    country_mobile_code = fields.Many2one('res.country', string='Code')
    country_phone_code = fields.Many2one('res.country', string='Code')
    job_id = fields.Many2one('hr.job', 'Job Position', domain="['|','&',('company_id', '=', False),('department_id','=',department_id),'&',('company_id', '=', company_id),('department_id','=',department_id)]")
    analytic_group_id = fields.Many2many('account.analytic.tag', string="Analytic Group")
    contract_state = fields.Selection(related="contract_id.state", string="Contract Status")
    branch_id = fields.Many2one("res.branch", string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=_domain_branch)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]
        if context.get('allowed_branch_ids'):
            domain += ['|',('branch_id', 'in', self.env.context.get('allowed_branch_ids')),('branch_id', '=', False)]

        result = super(HrEmployee, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        if context.get('allowed_branch_ids'):
            domain.extend(['|',('branch_id', 'in', self.env.context.get('allowed_branch_ids')),('branch_id', '=', False)])
        return super(HrEmployee, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(HrEmployee, self).fields_view_get(
            view_id=view_id, view_type=view_type)

        if self._context.get('hide_create_button'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        # else:
        #     root = etree.fromstring(res['arch'])
        #     root.set('create', 'true')
        #     root.set('edit', 'true')
        #     root.set('delete', 'true')
        #     res['arch'] = etree.tostring(root)
            
        return res
    
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args =  args or []
        domain = []
        if name:
            domain = ['|',('name', operator, name),('sequence_code', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

    def compute_restrict_org_chart_link(self):
        for rec in self:
            rec.restrict_org_chart_link = '<style># o_employee_right .o_field_widget, #o_employee_right .o_org_chart_group_up, {pointer-events: none !important;} .o_org_chart_entry.o_org_chart_entry_manager.media{pointer-events: none !important;} </style>'

    @api.model
    def _gender_selection(self):
        return [
            ("male", _("Male")),
            ("female", _("Female")),
        ]

    def _compute_contracts_count(self):
        super(HrEmployee, self)._compute_contracts_count()
        self.compute_restrict_org_chart_link()
        self.get_contracts_list()

    def get_contracts_list(self):
        for contract in self:
            if contract.contract_line_ids:
                contract.contract_line_ids = False
            contract_data = self.env['hr.contract'].search([('employee_id', 'in', contract.ids)], order="id asc")
            sequence = 1
            for con_data in contract_data:
                contract.contract_line_ids = [(0, 0, {'sequence': sequence, 'contract_id': con_data.id, 'employee_id': self.id})]
                sequence += 1

    _sql_constraints = [
        ('unique_sequence_code', 'unique(sequence_code)', 'The Employee ID must be unique!')
    ]

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            self.analytic_group_id = self.location_id.analytic_group_ids.ids
            self.province_wage_id = self.location_id.province_wage_id.id
    
    @api.onchange('country_mobile_code','mobile_phone')
    def _onchange_country_mobile_code(self):
        if self.mobile_phone:
            self.mobile_phone = self.phone_format(self.mobile_phone, self.country_mobile_code)

    @api.onchange('country_phone_code','work_phone')
    def _onchange_country_phone_code(self):
        if self.work_phone:
            self.work_phone = self.phone_format(self.work_phone, self.country_phone_code)

    @api.onchange('bank_ids')
    def _onchange_bank_ids(self):
        for record in self:
            if record.bank_ids:
                data = len(record.bank_ids.filtered(lambda line: line.is_used))
                if data > 1:
                    for line in record.bank_ids.filtered(lambda line: line.is_used):
                        line.is_used = False

    @api.constrains('bank_ids')
    def check_is_used_bank(self):
        for record in self:
            if record.bank_ids:
                data = len(record.bank_ids.filtered(lambda line: line.is_used))
                if data > 1:
                    raise ValidationError("Used bank account can't more than one")

    @api.depends('date_of_joining')
    def compute_year_of_service(self):
        for record in self:
            if record.date_of_joining:
                current_day = date.today()
                d1 = record.date_of_joining
                d2 = current_day
                record.years_of_service = ((d2 - d1).days) / 365
                d3 = record.date_of_joining + relativedelta(years=+record.years_of_service)
                record.months = ((d2 - d3).days) / 30
                d4 = d3 + relativedelta(months=+record.months)
                record.days = ((d2 - d4).days)
            else:
                record.years_of_service = 0
                record.months = 0
                record.days = 0

    @api.depends('birthday')
    def compute_birth_year(self):
        for record in self:
            if record.birthday:
                current_day = date.today()
                d1 = record.birthday
                d2 = current_day
                record.birth_years = ((d2 - d1).days) / 365
                d3 = record.birthday + relativedelta(years=+record.birth_years)
                record.birth_months = ((d2 - d3).days) / 30
                d4 = d3 + relativedelta(months=+record.birth_months)
                record.birth_days = ((d2 - d4).days)
            else:
                record.birth_years = 0
                record.birth_months = 0
                record.birth_days = 0

    def _company_document_count(self):
        now = datetime.now()
        now_date = now.date()
        for obj in self:
            company_document_ids_general = self.env['hr.company.document'].sudo().search([('general_document', '=', True),
                                                                                  ('state', '=', 'submitted'),
                                                                                  ('start_date', '<=', now_date)])
            company_document_ids_emp = self.env['hr.company.document'].sudo().search([('employee_ids', 'in', self.id),
                                                                              ('state', '=', 'submitted'),
                                                                              ('start_date', '<=', now_date)])
            company_document_ids_dep = self.env['hr.company.document'].sudo().search([('department_ids', 'in', self.department_id.id),
                                                                              ('state', '=', 'submitted'),
                                                                              ('start_date', '<=', now_date)])
            company_document_ids_job = self.env['hr.company.document'].sudo().search([('job_position_ids', 'in', self.job_id.id),
                                                                              ('state', '=', 'submitted'),
                                                                              ('start_date', '<=', now_date)])

            company_document_ids = company_document_ids_general.ids + company_document_ids_emp.ids + company_document_ids_dep.ids + company_document_ids_job.ids

            obj.company_document_count = len(set(company_document_ids))

    def company_document_view(self):
        now = datetime.now()
        now_date = now.date()
        for obj in self:
            company_document_ids_general = self.env['hr.company.document'].sudo().search([('general_document', '=', True),
                                                                                  ('state', '=', 'submitted'),
                                                                                  ('start_date', '<=', now_date)])
            company_document_ids_emp = self.env['hr.company.document'].sudo().search([('employee_ids', 'in', self.id),
                                                                              ('state', '=', 'submitted'),
                                                                              ('start_date', '<=', now_date)])
            company_document_ids_dep = self.env['hr.company.document'].sudo().search([('department_ids', 'in', self.department_id.id),
                                                                              ('state', '=', 'submitted'),
                                                                              ('start_date', '<=', now_date)])
            company_document_ids_job = self.env['hr.company.document'].sudo().search([('job_position_ids', 'in', self.job_id.id),
                                                                              ('state', '=', 'submitted'),
                                                                              ('start_date', '<=', now_date)])

            company_document_ids = company_document_ids_general.ids + company_document_ids_emp.ids + company_document_ids_dep.ids + company_document_ids_job.ids

            doc_ids = []

            for each in company_document_ids:
                doc_ids.append(each)
            view_id = self.env.ref('equip3_hr_masterdata_employee.view_hr_company_document_form').id
            if doc_ids:
                if len(doc_ids) > 1:
                    value = {
                        'domain': str([('id', 'in', doc_ids)]),
                        'view_mode': 'tree,form',
                        'res_model': 'hr.company.document',
                        'view_id': False,
                        'type': 'ir.actions.act_window',
                        'name': _('Company Document'),
                        'res_id': doc_ids
                    }
                else:
                    value = {
                        'view_mode': 'form',
                        'res_model': 'hr.company.document',
                        'view_id': view_id,
                        'type': 'ir.actions.act_window',
                        'name': _('Company Document'),
                        'res_id': doc_ids and doc_ids[0]
                    }
                return value

    company_document_count = fields.Integer(compute='_company_document_count', string="# Company's Document", help="Count of Company's Document")

    @api.model
    def archive_employee_record(self):
        current_date = date.today()
        for contract_expired in self.env["hr.contract"].search([('state', '=', 'close')]):
            contract_ongoing = self.env["hr.contract"].search([('state', 'in', ['draft', 'open']), ("employee_id", "=", contract_expired.employee_id.id)], limit=1)
            if not contract_ongoing:
                employee_archive = self.env["hr.employee"].search([('id', '=', contract_expired.employee_id.id)], limit=1)
                thirty_days = contract_expired.date_end + relativedelta(days=50)
                if current_date == thirty_days or current_date > thirty_days:
                    employee_archive.write({'active': False})

    @api.constrains('user_id')
    def constrains_user_id(self):
        for rec in self:
            employee_exist = self.env["hr.employee"].search(
                [('user_id', '=', rec.user_id.id), ('company_id', '=', rec.user_id.company_id.id),
                 ('active', '=', True)], limit=1)
            if employee_exist and employee_exist.sequence_code and employee_exist.sequence_code != rec.sequence_code:
                raise ValidationError(
                    _('A user cannot be linked to multiple employees in the same company. %s already using this user.') % employee_exist.name)

    @api.onchange('user_id')
    def onchange_user_id(self):
        self.constrains_user_id()
        # self.env.cr.execute("""ALTER TABLE hr_employee DROP CONSTRAINT hr_employee_user_uniq;""")

    @api.onchange('department_id')
    def _onchange_department_id(self):
        for rec in self:
            rec.job_id = False

class EmployeeEmergencyContact(models.Model):
    _name = 'employee.emergency.contact'
    _description = 'Employee Emergency Contact'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    name = fields.Char(string='Name')
    phone = fields.Char(string='Phone')
    relation_id = fields.Many2one('hr.employee.relation', string='Relation')
    address = fields.Char(string='Address')


class HrEmployeeEducation(models.Model):
    _name = 'hr.employee.education'
    _description = 'HR Employee Education'

    employee_id = fields.Many2one('hr.employee', "Employee")
    certificate = fields.Selection([
        ('graduate', 'Graduate'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ], 'Certificate Level', default='other')
    study_field = fields.Char("Field of Study")
    study_school = fields.Char("School")
    city = fields.Char(string='City')
    graduation_year = fields.Char(string='Graduation Year')
    gpa_score = fields.Float(string='GPA Score')


class EmployeeHealthRecords(models.Model):
    _name = 'employee.health.records'
    _description = 'Employee Health Records'

    name = fields.Integer("Sequence")
    employee_id = fields.Many2one('hr.employee', "Employee")
    illness_type = fields.Char("Illness Type")
    medical_checkup = fields.Char("Medical Checkup")
    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')
    notes = fields.Char(string='Notes')
    
    
    @api.model
    def default_get(self, fields):
        res = super(EmployeeHealthRecords,self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if 'health_ids' in context_keys:
                if len(self.env.context.get('health_ids')) > 0:
                    next_sequence = len(self.env.context.get('health_ids')) + 1
        res.update({'name': next_sequence})
        return res


    #its error becareful with your code

    # @api.depends('name')
    # def fetch_sl_no(self):
    #     sl = 0
    #     if self.ids:
    #         line_id = self.browse(self.ids[0])
    #         for line in line_id.employee_id.health_ids:
    #             sl = sl + 1
    #             line.name = sl

class employee_contract(models.Model):
    _name = 'employee.contract'
    _description = 'Employee Contract'

    sequence = fields.Integer(string="No")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    company_id = fields.Many2one('res.company', related='contract_id.company_id')
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id')
    contract_id = fields.Many2one('hr.contract', string="Contract Reference")
    job_id = fields.Many2one('hr.job', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                             related='contract_id.job_id', string='Job Position')
    department_id = fields.Many2one('hr.department', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                    related='contract_id.department_id', string="Department")
    parent_id = fields.Many2one('hr.employee', 'Manager', related='contract_id.parent_id')
    work_location_id = fields.Many2one('work.location.object', 'Work Location', related='contract_id.work_location_id')
    date_start = fields.Date('Start Date', related='contract_id.date_start', help="Start date of the contract.")
    date_end = fields.Date('End Date', related='contract_id.date_end', help="End date of the contract (if it's a fixed-term contract).")
    wage = fields.Monetary('Salary', related='contract_id.wage', help="Employee's monthly gross wage.")
    state = fields.Selection(string='Status', help='Status of the contract', related='contract_id.state',)

class User(models.Model):
    _inherit = ['res.users']

    marital = fields.Many2one(related='employee_id.marital', readonly=False, related_sudo=False)


class ResCountryCodeInherit(models.Model):
    _inherit = 'res.country'

    @api.depends('name')
    def name_get(self):
        result = []
        show = self._context.get('show_code')
        for rec in self:
            if show:
                name = rec.name + ' (+' + str(rec.phone_code) + ')'
            else:
                name = rec.name
            result.append((rec.id, name))
        return result
