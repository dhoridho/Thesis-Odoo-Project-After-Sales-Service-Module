import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DSDTF


class DocumentType(models.Model):
    _name = 'document.type'
    _description = 'Document Type'

    name = fields.Char('Name', required=True)


class EmployeeImmigration(models.Model):
    _name = 'employee.immigration'
    _description = 'Employee Immigration'
    _rec_name = 'documents'

    documents = fields.Char("Documents", required=True)
    number = fields.Char('Number')
    employee_id = fields.Many2one('hr.employee', 'Employee Name')
    exp_date = fields.Date('Expiry Date')
    issue_date = fields.Date('Issue Date')
    eligible_status = fields.Char('Eligible Status')
    issue_by = fields.Many2one('res.country', 'Issue By')
    eligible_review_date = fields.Date('Eligible Review Date')
    doc_type_id = fields.Many2one('document.type', 'Document Type')
    comments = fields.Text("Comments")
    attach_document = fields.Binary('Attach Document')

    @api.constrains('issue_date', 'exp_date')
    def _check_validity_dates(self):
        """Issue_date to exp_date check the date otherwise validation error."""
        for leave_type in self:
            if leave_type.issue_date and leave_type.exp_date and \
               leave_type.issue_date > leave_type.exp_date:
                raise ValidationError(
                    _("Expiry Date period should be greater than Issue Date"
                      " period"))


class HrEducationInformation(models.Model):
    _name = 'hr.education.information'
    _description = 'Employee Education Information'

    comp_prog_knw = fields.Char('Computer Programs Knowledge', required=True)
    shorthand = fields.Integer('Shorthand')
    course = fields.Char('Courses Taken')
    typing = fields.Integer('Typing')
    other_know = fields.Char('Other Knowledge & Skills')
    hr_employee_id = fields.Many2one('hr.employee', 'Employee Id')


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.depends('birthday')
    def _compute_age(self):
        today = datetime.today().date()
        for records in self:
            birthday_age = 0
            birthday_month = 0
            birthday_day = 0
            if records.birthday:
                if records.birthday < today:
                    birthday = records.birthday
                    birthday_age = today.year - birthday.year
                    birthday_month = records.birthday.month
                    birthday_day = records.birthday.day
                else:
                    raise ValidationError(_("Please enter valid Date of Birth!"))
            records.age = birthday_age
            records.birthday_month = birthday_month
            records.birthday_day = birthday_day

    @api.depends('last_date', 'emp_status')
    def _get_rem_days(self):
        """Method to get the remaining days for the employee notice period."""
        today = datetime.today().date()
        for employee in self:
            rem_days = 0
            if employee.last_date and employee.emp_status == 'in_notice':
                time_delta = employee.last_date - today
                diff_day = time_delta.days + (time_delta.seconds) / 86400
                rem_days = diff_day > 0 and round(diff_day) or 0
            employee.rem_days = rem_days

    @api.depends('join_date')
    def compute_joined_year(self):
        """Joined year and difference in years depend the join date."""
        start_date = datetime.today()
        for emp in self:
            diff_in_years = 0
            if emp.join_date:
                diffinyears = relativedelta(start_date, emp.join_date)
                diff_in_years = diffinyears.years + 1
            emp.joined_year = diff_in_years

    @api.constrains('join_date', 'app_date')
    def _application_dates(self):
        """Join date to app_date is start to end date validated."""
        for leave_type in self:
            if leave_type.app_date and leave_type.join_date and \
               leave_type.app_date >= leave_type.join_date:
                raise ValidationError(
                    _("Date Joined should be greater than Application Date"))

    @api.depends('pr_date')
    def compute_pr_year(self):
        """Employee PR year to difference in years and start to end date."""
        start_date = datetime.today()
        for emp in self:
            diff_in_years = 0
            if emp.pr_date:
                diffinyears = relativedelta(start_date, emp.pr_date).years
                diff_in_years = diffinyears + 1
            emp.pr_year = diff_in_years

    cessation_date = fields.Date('Cessation Date')
    job_id = fields.Many2one('hr.job', 'Job')
    parent_id = fields.Many2one('hr.employee', 'Expense Manager')
    leave_manager = fields.Many2one('hr.employee', 'Leave Manager')
    join_date = fields.Date('Date Joined')
    confirm_date = fields.Date('Date Confirmation')
    history_ids = fields.One2many('employee.history', 'history_id',
                                  'Job History')
#    reason = fields.Text('Reason')
    immigration_ids = fields.One2many('employee.immigration', 'employee_id',
                                      'Immigration')
    last_date = fields.Date('Last Date')
    rem_days = fields.Integer(compute='_get_rem_days', string='Remaining Days',
                              help="Number of remaining days of his/her \
                              employment expire")
    hr_manager = fields.Boolean(string='HR Manager')
    training_ids = fields.One2many('employee.training', 'tr_id', 'Training')
    birthday_month = fields.Char(compute='_compute_age')
    birthday_day = fields.Char(compute='_compute_age')
    age = fields.Integer(compute='_compute_age')
    place_of_birth = fields.Char('Place of Birth')
    issue_date = fields.Date('Passport Issue Date')
    dialect = fields.Char('Dialect')
    driving_licence = fields.Char('Driving Licence:Class')
    car = fields.Boolean('Do you own a car?')
    resume = fields.Binary('Resume')
    physical_stability = fields.Boolean('Physical Stability (Yes)')
    physical = fields.Text('Physical Stability Information')
    court_b = fields.Boolean('Court (Yes)')
    court = fields.Char('Court Information')
    dismissed_b = fields.Boolean('Dismissed (Yes)')
    dismiss = fields.Char('Dismissed Information')
    bankrupt_b = fields.Boolean('Bankrupt (Yes)')
    bankrupt = fields.Char('Bankrupt Information')
    about = fields.Text('About Yourself')
    bankrupt_no = fields.Boolean('Bankrupt (No)')
    dismissed_no = fields.Boolean('Dismissed (No)')
    court_no = fields.Boolean('Court (No)')
    physical_stability_no = fields.Boolean('Physical Disability (No)')
    bank_detail_ids = fields.One2many('hr.bank.details', 'bank_emp_id',
                                      'Bank Details')
    employee_type_id = fields.Many2one('employee.id.type', 'Type Of ID')
    emp_country_id = fields.Many2one('res.country', 'Country')
    emp_state_id = fields.Many2one('res.country.state', 'State')
    emp_city_id = fields.Many2one('employee.city', 'City')
    is_daily_notificaiton_email_send = fields.Boolean('Receiving email \
    notifications of employees who are on leave?', default=True)
    is_pending_leave_notificaiton = fields.Boolean('Receiving email \
    notifications of Pending Leaves Notification Email?')
    is_all_final_leave = fields.Boolean('Receiving email notifications of \
    2nd Reminder to Direct / Indirect Managers?')
    joined_year = fields.Integer(compute='compute_joined_year',
                                 string='Joined Year')
    app_date = fields.Date('Application Date',
                           help='The date when the Work Permit was Applied')
    education_info_line = fields.One2many('hr.education.information',
                                          'hr_employee_id',
                                          'Education Info Line')
    singaporean = fields.Boolean('Singaporean')
    pr_date = fields.Date('PR Date')
    pr_year = fields.Integer(compute='compute_pr_year', string='PR Year')
    factors = fields.Selection(selection=[('skilled', 'Skilled'),
                                          ('unskilled', 'Unskilled')],
                               string='Factors', default='skilled')
    sectors = fields.Selection(selection=[('service', 'Service'),
                                          ('manufacturing', 'Manufacturing'),
                                          ('construction', 'Construction'),
                                          ('process', 'Process'),
                                          ('marine', 'Marine'),
                                          ('s_pass', 'S Pass')],
                               string='Sectors', default='service')
    type_tiers = fields.Selection(selection=[('basic_tier_1', 'Basic/Tier 1'),
                                             ('tier_2', 'Tier 2'),
                                             ('tier_3', 'Tier 3'),
                                             ('mye', 'MYE'),
                                             ('mye-waiver', 'MYE-waiver')],
                                  string='Tiers', default='basic_tier_1')
    emp_status = fields.Selection(selection=[('probation', 'Probation'),
                                             ('active', 'Active'),
                                             ('in_notice', 'In notice Period'),
                                             ('terminated', 'Terminated'),
                                             ('inactive', 'Inactive'),
                                             ('promoted', 'Promoted')],
                                  string='Employment Status', default='active')

    @api.onchange('emp_status')
    def onchange_employee_status(self):
        """Onchange employee status inactive then active is false and."""
        """then emp status checked."""
        if self.emp_status == 'inactive':
            self.active = False
        if self.emp_status == 'active':
            self.cessation_date = False
            self.active = True

    @api.onchange('cessation_date')
    def onchange_employee_cessation_date(self):
        """Emp status is in notice then hr.contract is search then."""
        """write cessation date."""
        if self.emp_status == 'in_notice':
            contratc_id = self.env['hr.contract'].search([('employee_id', '=',
                                                           self._origin.id)])
            if contratc_id and self.cessation_date:
                contratc_id.write({'date_end': self.cessation_date})

    @api.onchange('physical_stability')
    def onchange_health_yes(self):
        """Onchange health yes then physical stability is false."""
        if self.physical_stability:
            self.physical_stability_no = False

    @api.onchange('physical_stability_no')
    def onchange_health_no(self):
        """Onchange health no then physical stability is false."""
        if self.physical_stability_no:
            self.physical_stability = False

    @api.onchange('court_b')
    def onchange_court_yes(self):
        """Onchange court yes then court_no is false."""
        if self.court_b:
            self.court_no = False

    @api.onchange('court_no')
    def onchange_court_no(self):
        """Onchange cour no then court_no is false."""
        if self.court_no:
            self.court_b = False

    @api.onchange('dismissed_b')
    def onchange_dismissed_yes(self):
        """Onchange dismissed yes then dismissed no is false."""
        if self.dismissed_b:
            self.dismissed_no = False

    @api.onchange('dismissed_no')
    def onchange_dismissed_no(self):
        """Onchange dismissed no then dismissed_no is false."""
        if self.dismissed_no:
            self.dismissed_b = False

    @api.onchange('bankrupt_b')
    def onchange_bankrupt_yes(self):
        """Onchange bankrupt yes then bankrupt no is false."""
        if self.bankrupt_b:
            self.bankrupt_no = False

    @api.onchange('bankrupt_no')
    def onchange_bankrupt_no(self):
        """Onchange bankrupt no self b is false."""
        if self.bankrupt_no:
            self.bankrupt_b = False

    @api.onchange('address_home_id')
    def onchange_address_home_id(self):
        """Onchange employee status is onchange the address home id."""
        if self.address_home_id and self.address_home_id.country_id:
            self.emp_country_id = self.address_home_id.country_id.id
        if self.address_home_id and self.address_home_id.state_id:
            self.emp_state_id = self.address_home_id.state_id.id

    def write(self, vals):
        """Employee.history is get the value job_id and emp_status and."""
        """then emp history_obj create then append the user id,browse."""
        emp_history_obj = self.env['employee.history']
        if vals.get('job_id', '') or vals.get('emp_status', '') or vals.get(
            'join_date', '') or vals.get('confirm_date', '') or vals.get(
                'cessation_date'):
            for emp_rec in self:
                create_vals = {
                    'job_id': vals.get('job_id', emp_rec.job_id.id),
                    'history_id': emp_rec.id,
                    'user_id': self.env.user.id,
                    'emp_status': vals.get('emp_status', emp_rec.emp_status),
                    'join_date': vals.get('join_date', emp_rec.join_date),
                    'confirm_date': vals.get('confirm_date',
                                             emp_rec.confirm_date),
                    'cessation_date': vals.get('cessation_date',
                                               emp_rec.cessation_date)}
                emp_history_obj.create(create_vals)
        if 'active' in vals:
            user_ids = []
            for employee in self:
                if employee.user_id:
                    user_ids.append(employee.user_id.id)
            if user_ids:
                user_rec = self.env['res.users'].browse(user_ids)
                user_rec.write({'active': vals.get('active')})
        return super(HrEmployee, self).write(vals)

    @api.model
    def create(self, vals):
        """Emp history obj then employee_id call super HrEmployee."""
        """ create uid is fetch values id ,date and user id ie not active."""
        emp_history_obj = self.env['employee.history']
        employee_id = super(HrEmployee, self).create(vals)
        if vals.get('job_id', '') or vals.get('emp_status', '') or \
            vals.get('join_date', '') or vals.get('confirm_date', '') or \
                vals.get('cessation_date'):
            emp_history_obj.create({
                'job_id': vals.get('job_id'),
                'history_id': employee_id.id,
                'user_id': self.env.user.id,
                'emp_status': vals.get('emp_status', 'active'),
                'join_date': vals.get('join_date', False),
                'confirm_date': vals.get('confirm_date', False),
                'cessation_date': vals.get('cessation_date', False)})
        active = vals.get('active', False)
        if vals.get('user_id') and not active:
            user_rec = self.env['res.users'].browse(vals.get('user_id'))
            user_rec.write({'active': active})
        return employee_id


class EmployeeCity(models.Model):
    _name = "employee.city"
    _description = 'Employee City'

    name = fields.Char('City Name', required=True)
    code = fields.Char('City Code', required=True)
    state_id = fields.Many2one('res.country.state', 'State', required=True)


class HrBankDetails(models.Model):
    _name = 'hr.bank.details'
    _description = 'Employee Bank Details'
    _rec_name = 'bank_name'

    bank_name = fields.Char('Name Of Bank')
    bank_code = fields.Char('Bank Code')
    bank_ac_no = fields.Char('Bank Account Number', required=True)
    bank_emp_id = fields.Many2one('hr.employee', 'Bank Detail')
    branch_code = fields.Char('Branch Code')
    beneficiary_name = fields.Char('Beneficiary Name')


class EmployeeIdType(models.Model):
    _name = 'employee.id.type'
    _description = 'Employee ID Type'

    name = fields.Char("EP", required=True)
    s_pass = fields.Selection(selection=[('skilled', 'Skilled'),
                                         ('unskilled', 'Un Skilled')],
                              string='S Pass', default='skilled')
    wp = fields.Selection(selection=[('skilled', 'Skilled'),
                                     ('unskilled', 'Un Skilled')],
                          string='Wp', default='skilled')


class EmployeeTraining(models.Model):
    _name = 'employee.training'
    _description = 'Employee Training'
    _rec_name = 'tr_title'

    tr_id = fields.Many2one('hr.employee', 'Employee')
    tr_title = fields.Char('Title of Training/Workshop', required=True)
    tr_institution = fields.Char('Institution')
    tr_date = fields.Date('Date')
    comments = fields.Text('Comments')
    training_attachment = fields.Binary('Attachment Data')


class EmployeeHistory(models.Model):
    _name = 'employee.history'
    _description = 'Employee History'
    _rec_name = 'history_id'

    history_id = fields.Many2one('hr.employee', 'History', required="1")
    job_id = fields.Many2one('hr.job', 'Job title', readonly=True)
    date_changed = fields.Datetime('Date Changed', readonly=True,
                                   default=lambda * a: time.strftime(DSDTF))
    user_id = fields.Many2one('res.users', "Changed By", readonly=True)
    emp_status = fields.Selection(selection=[
        ('probation', 'Probation'), ('active', 'Active'),
        ('in_notice', 'In notice Period'), ('terminated', 'Terminated'),
        ('inactive', 'Inactive'), ('promoted', 'Promoted')],
        string='Employment Status', default='active')
    join_date = fields.Date('Joined Date')
    confirm_date = fields.Date('Date of Confirmation')
    cessation_date = fields.Date('Cessation Date')
    emp_last_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive')],
        'Employment history', default='active')
