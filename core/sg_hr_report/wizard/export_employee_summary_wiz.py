
import base64
import io


from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

import xlwt

LEAVE_STATE = {'draft': 'New',
               'confirm': 'Waiting Pre-Approval',
               'refuse': 'Refused',
               'validate1': 'Waiting Final Approval',
               'validate': 'Approved',
               'cancel': 'Cancelled'}
LEAVE_REQUEST = {'remove': 'Leave Request',
                 'add': 'Allocation Request'}
PAYSLIP_STATE = {"draft": "Draft",
                 "verify": "Waiting",
                 "done": "Done",
                 "cancel": "Rejected"}


class ExportEmployeeDataRecordXls(models.TransientModel):
    _name = 'export.employee.data.record.xls'
    _description = "Export Employee Data Record Xls"

    file = fields.Binary("Click On Save As Button To Download Xls File",
                         readonly=True)
    name = fields.Char("Name", readonly=True, invisible=True,
                       default='Employee Summary.xls')


class ExportEmployeeSummaryWiz(models.TransientModel):
    _name = 'export.employee.summary.wiz'
    _description = "Export Employee Summary"

    employee_ids = fields.Many2many('hr.employee',
                                    'ihrms_hr_employee_export_summary_rel',
                                    'emp_id', 'employee_id', 'Employee Name',
                                    required=True)
    user_id = fields.Boolean('User', default=True)
    active = fields.Boolean('Active', default=True)
    department = fields.Boolean('Department', default=False)
    direct_manager = fields.Boolean('Expense Manager', default=False)
    indirect_manager = fields.Boolean('Leave Manager', default=False)
    personal_information = fields.Boolean('Select All', default=False)
    identification_id = fields.Boolean('Identification', default=False)
    passport_id = fields.Boolean('Passport', default=False)
    gender = fields.Boolean('Gender', default=False)
    marital = fields.Boolean('Martial Status', default=False)
    nationality = fields.Boolean('Nationality', default=False)
    dob = fields.Boolean('Date Of Birth', default=False)
    pob = fields.Boolean('Place Of Birth', default=False)
    age = fields.Boolean('Age', default=False)
    home_address = fields.Boolean('Home Address', default=False)
    country_id = fields.Boolean('Country', default=False)
    state_id = fields.Boolean('State', default=False)
    city_id = fields.Boolean('City', default=False)
    phone = fields.Boolean('Phone', default=False)
    mobile = fields.Boolean('Mobile', default=False)
    email = fields.Boolean('Email', default=False)
    permit_no = fields.Boolean('Work Permit Number', default=False)
    dialect = fields.Boolean('Dialect', default=False)
    driving_licence = fields.Boolean('Driving Licence Class', default=False)
    employee_type_id = fields.Boolean('Type of ID', default=False)
    evaluation_plan_id = fields.Boolean('Appraisal Plan', default=False)
    evaluation_date = fields.Boolean('Next Appraisal Date', default=False)
    language_ids = fields.Boolean('Language', default=False)
    com_prog_know = fields.Boolean('Computer Program Knowledge', default=False)
    shorthand = fields.Boolean('Shorthand', default=False)
    courses = fields.Boolean('Courses Taken', default=False)
    typing = fields.Boolean('Typing', default=False)
    other_know = fields.Boolean('Other Knowledge & Skills', default=False)
    job_title = fields.Boolean('Job Title', default=False)
    emp_status = fields.Boolean('Employment Status', default=False)
    join_date = fields.Boolean('Joined Date', default=False)
    confirm_date = fields.Boolean('Confirmation Date', default=False)
    date_changed = fields.Boolean('Date Changed', default=False)
    changed_by = fields.Boolean('Changed By', default=False)
    date_confirm_month = fields.Boolean('Date Confirm Month', default=False)
    category_ids = fields.Boolean('Categories', default=False)
    immigration_ids = fields.Boolean('Immigration', default=False)
    tarining_ids = fields.Boolean('Training Workshop', default=False)
    emp_leave_ids = fields.Boolean('Leave History', default=False)
    health_condition = fields.Boolean(
        'Are you suffering from any physical '
        'disability or illness that requires you to be medication '
        'for a prolonged period?',
        default=False)
    court_law = fields.Boolean(
        'Have you ever been convicted in a court of '
        'law in any country?',
        default=False)
    suspend_employment = fields.Boolean(
        'Have you ever been dismissed or '
        'suspended from employment?', default=False)
    bankrupt = fields.Boolean(
        'Have you ever been declared a bankrupt?',
        default=False)
    about = fields.Boolean('About Yourself', default=False)
    emp_noty_leave = fields.Boolean(
        'Receiving email notifications of employees who are on leave?',
        default=False)
    pending_levae_noty = fields.Boolean(
        'Receiving email notifications of'
        'Pending Leaves Notification Email?',
        default=False)
    receive_mail_manager = fields.Boolean(
        'Receiving email notifications of '
        '2nd Reminder to Direct / Indirect Managers?',
        default=False)
    bank_detail_ids = fields.Boolean('Bank Details', default=False)
    first_name = fields.Boolean('First Name', default=False)
    last_name = fields.Boolean('Last Name', default=False)
    relation_ship = fields.Boolean("Relationship", default=False)
    identification_number = fields.Boolean(
        "Identification Number",
        default=False)
    notes = fields.Boolean('Notes', default=False)
    payslip = fields.Boolean('Payslips', default=False)
    contract = fields.Boolean('Contract', default=False)
    employee_information = fields.Boolean('Select All', default=False)
    edu_information = fields.Boolean('Select All', default=False)
    job_information = fields.Boolean('Select All', default=False)
    extra_information = fields.Boolean('Select All', default=False)
    dependent_information = fields.Boolean('Select All', default=False)

    @api.constrains('user_id', 'department', 'indirect_manager', 'active',
                    'direct_manager', 'first_name', 'last_name',
                    'relation_ship', 'identification_number',
                    'identification_id', 'passport_id', 'gender',
                    'marital', 'nationality', 'dob', 'pob', 'age',
                    'home_address', 'country_id', 'state_id', 'city_id',
                    'phone', 'mobile', 'email', 'permit_no', 'dialect',
                    'driving_licence', 'employee_type_id',
                    'evaluation_plan_id', 'evaluation_date', 'com_prog_know',
                    'courses', 'other_know', 'shorthand', 'typing',
                    'job_title',
                    'join_date', 'date_changed', 'date_confirm_month',
                    'emp_status', 'confirm_date', 'changed_by',
                    'category_ids', 'immigration_ids', 'tarining_ids',
                    'emp_leave_ids', 'health_condition', 'bankrupt',
                    'suspend_employment', 'court_law', 'about',
                    'bank_detail_ids', 'notes')
    def onchange_emp_detail(self):
        """Onchnage employee details."""
        if not self.user_id and not self.department and not \
                self.indirect_manager and not self.active and not \
                self.direct_manager and not self.first_name and not \
                self.last_name and \
                not self.relation_ship and not self.identification_number and \
                not self.identification_id and not self.passport_id and not \
                self.gender and not self.marital and not self.nationality\
                and not self.dob and not self.pob and not self.age and not \
                self.home_address and not self.country_id and not \
                self.state_id and not self.city_id and not self.phone \
                and not self.mobile and not self.email and not self.permit_no \
                and not self.dialect and not self.driving_licence and not \
                self.employee_type_id and not self.evaluation_plan_id and not \
                self.evaluation_date and not self.com_prog_know and not \
                self.courses and not self.other_know and not self.shorthand \
                and not self.typing and not self.job_title and not \
                self.join_date and not self.date_changed and not \
                self.date_confirm_month and not self.emp_status and not \
                self.confirm_date and not self.changed_by and not \
                self.category_ids and not self.immigration_ids and not \
                self.tarining_ids and not self.emp_leave_ids \
                and not self.health_condition and not self.bankrupt and not \
                self.suspend_employment and not self.court_law and not \
                self.about and not self.bank_detail_ids and not self.notes:
            raise ValidationError(
                'Please select atleast one from '
                '\n *Employee Information \n * Dependents \n * Personal'
                'Information \n * Appraisal \n * Educational Information'
                '\n * Job or Categories \n * Immigration \n * Training '
                '\n * Leave History \n * Extra Information \n * Bank Details '
                '\n * Notes.')

    @api.onchange('extra_information')
    def onchange_extra_information(self):
        """Onchange extra information."""
        if self.extra_information and \
                self._context.get('extra_information'):
            self.health_condition = self.bankrupt = self.suspend_employment = \
                self.court_law = self.about = True
        elif not self.extra_information and \
                self._context.get('extra_information'):
            self.bankrupt = self.suspend_employment = self.court_law = \
                self.about = self.health_condition = False

    @api.onchange('bankrupt', 'suspend_employment', 'court_law', 'about',
                  'health_condition')
    def onchange_extra_info(self):
        """Onchnage bankrupt."""
        if not self.bankrupt or not self.suspend_employment or not \
                self.court_law or not self.about or not self.health_condition \
                and self.extra_information:
            self.extra_information = False
        if self.bankrupt and self.suspend_employment and self.court_law and \
                self.about and self.health_condition and not \
                self.extra_information:
            self.extra_information = True

    @api.onchange('job_information')
    def onchange_job_information(self):
        """Onchnage job information."""
        if self.job_information and \
                self._context.get('job_information'):
            self.job_title = self.emp_status = self.join_date = \
                self.confirm_date = self.date_changed = self.changed_by = \
                self.date_confirm_month = True
        elif not self.job_information and \
                self._context.get('job_information'):
            self.job_title = self.emp_status = self.join_date = \
                self.confirm_date = self.date_changed = self.changed_by = \
                self.date_confirm_month = False

    @api.onchange('job_title', 'emp_status', 'join_date', 'confirm_date',
                  'date_changed', 'changed_by', 'date_confirm_month')
    def onchange_job_info(self):
        """Onchange job details."""
        if not self.job_title or not self.emp_status or not \
                self.join_date or not self.confirm_date or not \
                self.date_changed or not self.changed_by or not \
                self.date_confirm_month and self.job_information:
            self.job_information = False
        if self.job_title and self.emp_status and self.join_date and \
                self.confirm_date and self.date_changed and \
                self.changed_by and \
                self.date_confirm_month and not self.job_information:
            self.job_information = True

    @api.onchange('edu_information')
    def onchange_edu_information(self):
        """Onchange education boolean."""
        if self.edu_information and \
                self._context.get('edu_information'):
            self.com_prog_know = self.shorthand = self.courses = \
                self.typing = self.other_know = True
        elif not self.edu_information and \
                self._context.get('edu_information'):
            self.com_prog_know = self.shorthand = self.courses = \
                self.typing = self.other_know = False

    @api.onchange('com_prog_know', 'shorthand', 'courses', 'typing',
                  'other_know')
    def onchange_edu_info(self):
        """Onchnage education information."""
        if not self.com_prog_know or not self.shorthand or \
                not self.courses or not self.typing or not self.other_know \
                and self.edu_information:
            self.edu_information = False
        if self.com_prog_know and self.shorthand and self.courses and \
                self.typing and self.other_know and not self.edu_information:
            self.edu_information = True

    @api.onchange('employee_information')
    def onchange_employee_information(self):
        """Onchnage employee info boolean."""
        if self.employee_information and \
                self._context.get('employee_information'):
            self.user_id = self.active = self.department = \
                self.direct_manager = self.indirect_manager = True
        elif not self.employee_information and \
                self._context.get('employee_information'):
            self.user_id = self.active = self.department = \
                self.direct_manager = self.indirect_manager = False

    @api.onchange('user_id', 'active', 'department', 'direct_manager',
                  'indirect_manager')
    def onchange_emp_info(self):
        """Onchnage employee information."""
        if not self.user_id or not self.active or not self.department \
                or not self.direct_manager or not self.indirect_manager and \
                self.employee_information:
            self.employee_information = False
        if self.active and self.user_id and\
                self.department and self.direct_manager and \
                self.indirect_manager:
            self.employee_information = True

    @api.onchange('dependent_information')
    def onchange_dependent_information(self):
        """Onchnage dependent boolean information."""
        if self.dependent_information and \
                self._context.get('dependent_information'):
            self.first_name = self.last_name = self.relation_ship = \
                self.identification_number = True
        elif not self.dependent_information and \
                self._context.get('dependent_information'):
            self.first_name = self.last_name = self.relation_ship = \
                self.identification_number = False

    @api.onchange('first_name', 'last_name', 'relation_ship',
                  'identification_number')
    def onchange_dependent_info(self):
        """Onchnage dependent information."""
        if not self.first_name or not self.last_name or not \
                self.relation_ship or not self.identification_number and \
                self.dependent_information:
            self.dependent_information = False
        if self.first_name and self.last_name and \
                self.relation_ship and self.identification_number and not \
                self.dependent_information:
            self.dependent_information = True

    @api.onchange('personal_information')
    def onchange_personal_information(self):
        """Onchange personal info boolean.

        The method used to onchange event call when user checked or
        unchecked the on the boolean field, default=False
        at time all boolean fields of value change, default=False
        @self : Record Set
        @api.onchange : The decorator of onchange
        @return: None
        -----------------------------------------------------------------
        """
        if self.personal_information and \
                self._context.get('personal_information'):
            self.identification_id = self.passport_id = self.gender = \
                self.marital = self.nationality = self.dob = self.pob = \
                self.age = self.home_address = self.country_id = \
                self.state_id = self.city_id = self.phone = self.mobile = \
                self.email = self.permit_no = self.dialect = \
                self.driving_licence = self.employee_type_id = True
        elif not self.personal_information and \
                self._context.get('personal_information'):
            self.identification_id = self.passport_id = self.gender = \
                self.marital = self.nationality = self.dob = self.pob = \
                self.age = self.home_address = self.country_id = \
                self.state_id = self.city_id = self.phone = self.mobile = \
                self.email = self.permit_no = self.dialect = \
                self.driving_licence = self.employee_type_id = False

    @api.onchange('identification_id', 'passport_id', 'gender', 'marital',
                  'nationality', 'dob', 'pob', 'age', 'home_address',
                  'country_id', 'state_id', 'city_id', 'phone', 'mobile',
                  'email', 'permit_no', 'dialect', 'driving_licence',
                  'employee_type_id')
    def onchange_personal_info(self):
        """Onchnage personal detail information."""
        if not self.identification_id or not self.passport_id or \
                not self.gender or not self.marital or not self.nationality \
                or not self.dob or not self.pob or not self.age or \
                not self.home_address or not self.country_id or not \
                self.state_id or \
                not self.city_id or not self.phone or not self.mobile or \
                not self.email or not self.permit_no or not self.dialect or \
                not self.driving_licence or not self.employee_type_id and \
                self.personal_information:
            self.personal_information = False
        if self.identification_id and self.passport_id and \
                self.gender and self.marital and self.nationality and \
                self.dob and self.pob and self.age and self.home_address \
                and self.country_id and self.state_id and self.city_id \
                and self.phone and self.mobile and \
                self.email and self.permit_no and self.dialect and \
                self.driving_licence and self.employee_type_id and \
                not self.personal_information:
            self.personal_information = True

    @api.constrains('employee_ids')
    def onchange_employees(self):
        """Onchnage employees."""
        for rec in self:
            if not rec.employee_ids:
                raise ValidationError(_("Please Select Employee"))

    def export_employee_summary_xls(self):
        """Export the employee deatils.

        The method used to call download file of wizard
        @self : Record Set
        @return: Return of wizard of action in dictionary
        """
        # employee_obj = self.env['hr.employee']
        payslip_obj = self.env['hr.payslip']
        contract_obj = self.env['hr.contract']
        context = dict(self._context or {})
        context.update({'active_test': False})

        for employee in self.employee_ids:
            condition_string = ''
            condition_check = False

            if not employee.bank_account_id:
                condition_check = True
                condition_string += '\n * Bank Account'
            if not employee.gender:
                condition_check = True
                condition_string += '\n * Gender'
            if not employee.birthday:
                condition_check = True
                condition_string += '\n * Birth Day'
            if not employee.identification_id:
                condition_check = True
                condition_string += '\n * Identification No'
            if not employee.work_phone:
                condition_check = True
                condition_string += '\n * Contact'
            if not employee.work_email:
                condition_check = True
                condition_string += '\n * Email'

            if condition_check:
                raise ValidationError(_(
                    'One of the following configuration is still missing '
                    'from employee\'s profile.\nPlease configure the '
                    'following details for employee %s. \n %s' % (employee.name,
                                                                  condition_string)))

        workbook = xlwt.Workbook()
        font = xlwt.Font()
        font.bold = True
        # other format is not support in excel sheet so updated it
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'dd/mm/yyyy'
        header = xlwt.easyxf(
            'font: name Arial, bold on, height 200; align: wrap off;')
        style = xlwt.easyxf('align: wrap off')
        # datetime_format =
        number_format = xlwt.easyxf('align: wrap off')
        number_format.num_format_str = '#,##0.00'
        personal_information = False
        emp_note_row = emp_payslip_row = emp_contract_row = \
            emp_edu_skill_row = emp_dependent_info_row = \
            emp_extra_info_row = emp_notification_row = \
            emp_info_row = emp_per_info_row = emp_appraisal_row = \
            emp_bank_row = emp_leave_row = \
            emp_training_row = emp_job_row = emp_immigration_row = \
            emp_categories_row = 0
        emp_info_col = emp_per_info_col = emp_appraisal_col = \
            emp_notification_col = emp_extra_info_col = 0
        if self.employee_ids:
            if (self.user_id or self.active or
                    self.department or self.direct_manager or
                    self.indirect_manager):
                emp_info_ws = workbook.add_sheet('Employee Information')
                emp_info_ws.col(emp_info_col).width = 6000
                emp_info_ws.write(emp_info_row, emp_info_col, 'Employee Name',
                                  header)
                if self.user_id:
                    emp_info_col += 1
                    emp_info_ws.col(emp_info_col).width = 5000
                    emp_info_ws.write(emp_info_row, emp_info_col, 'User',
                                      header)
                if self.active:
                    emp_info_col += 1
                    emp_info_ws.col(emp_info_col).width = 5000
                    emp_info_ws.write(emp_info_row, emp_info_col, 'Active',
                                      header)
                if self.department:
                    emp_info_col += 1
                    emp_info_ws.col(emp_info_col).width = 5000
                    emp_info_ws.write(emp_info_row, emp_info_col, 'Department',
                                      header)
                if self.direct_manager:
                    emp_info_col += 1
                    emp_info_ws.col(emp_info_col).width = 5000
                    emp_info_ws.write(emp_info_row, emp_info_col,
                                      'Expense Manager', header)
                if self.indirect_manager:
                    emp_info_col += 1
                    emp_info_ws.col(emp_info_col).width = 5000
                    emp_info_ws.write(emp_info_row, emp_info_col,
                                      'Leave Manager', header)

            #  Employee Personal Information
            if (self.identification_id or
                self.passport_id or self.gender or self.marital or
                self.nationality or self.dob or self.pob or self.age or
                self.home_address or self.country_id or self.state_id or
                self.city_id or self.phone or self.mobile or self.email or
                self.permit_no or self.dialect or
                self.driving_licence or self.employee_type_id):
                personal_information = True
            if personal_information:
                emp_personal_info_ws = workbook.add_sheet(
                    'Personal Information')
                emp_per_info_col = 0
                emp_personal_info_ws.col(emp_per_info_col).width = 6000
                emp_personal_info_ws.write(emp_per_info_row, emp_per_info_col,
                                           'Employee Name : ', header)
                if self.identification_id:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col,
                                               'Identification', header)
                if self.passport_id:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'Passport No',
                                               header)

                if self.gender:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'Gender',
                                               header)
                if self.marital:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col,
                                               'Marital Status', header)
                if self.nationality:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'Nationality',
                                               header)
                if self.dob:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'Birthdate',
                                               header)
                if self.pob:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col,
                                               'Place Of Birth', header)
                if self.age:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'Age', header)

                if self.home_address:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col,
                                               'Home Address',
                                               header)
                if self.country_id:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'Country',
                                               header)
                if self.state_id:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'State',
                                               header)
                if self.city_id:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'City',
                                               header)
                if self.phone:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'Phome',
                                               header)
                if self.mobile:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'Mobile',
                                               header)
                if self.email:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'Email',
                                               header)

                if self.permit_no:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col,
                                               'Work Permit Number', header)
                if self.dialect:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'Dialect',
                                               header)
                if self.driving_licence:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col,
                                               'Driving Licence', header)
                if self.employee_type_id:
                    emp_per_info_col += 1
                    emp_personal_info_ws.col(emp_per_info_col).width = 6000
                    emp_personal_info_ws.write(emp_per_info_row,
                                               emp_per_info_col, 'Type of ID',
                                               header)
            #  Evaluation
            if self.evaluation_plan_id or self.evaluation_date:
                emp_appraisal_ws = workbook.add_sheet('Appraisal')
                emp_appraisal_ws.col(emp_appraisal_col).width = 6000
                emp_appraisal_ws.write(emp_appraisal_row,
                                       emp_appraisal_col, 'Employee Name',
                                       header)
                if self.evaluation_plan_id:
                    emp_appraisal_col += 1
                    emp_appraisal_ws.col(emp_appraisal_col).width = 6000
                    emp_appraisal_ws.write(emp_appraisal_row,
                                           emp_appraisal_col,
                                           'Appraisal', header)
                if self.evaluation_date:
                    emp_appraisal_col += 1
                    emp_appraisal_ws.col(emp_appraisal_col).width = 6000
                    emp_appraisal_ws.write(emp_appraisal_row,
                                           emp_appraisal_col,
                                           'Next Appraisal Date', header)

            #  Notification
            if (self.emp_noty_leave or self.pending_levae_noty or
                    self.receive_mail_manager):
                emp_notification_ws = workbook.add_sheet('Notification')
                emp_notification_ws.col(emp_notification_col).width = 6000
                emp_notification_ws.write(emp_notification_row,
                                          emp_notification_col,
                                          'Employee Name',
                                          header)
                if self.emp_noty_leave:
                    emp_notification_col += 1
                    emp_notification_ws.col(emp_notification_col).width = 15000
                    emp_notification_ws.write(
                        emp_notification_row,
                        emp_notification_col,
                        'Receiving email notifications of employees'
                        ' who are on leave? :',
                        header)
                if self.pending_levae_noty:
                    emp_notification_col += 1
                    emp_notification_ws.col(emp_notification_col).width = 15000
                    emp_notification_ws.write(
                        emp_notification_row,
                        emp_notification_col,
                        'Receiving email notifications of Pending Leaves'
                        ' Notification Email? :',
                        header)
                if self.receive_mail_manager:
                    emp_notification_col += 1
                    emp_notification_ws.col(emp_notification_col).width = 15000
                    emp_notification_ws.write(
                        emp_notification_row,
                        emp_notification_col,
                        'Receiving email notifications of 2nd Reminder'
                        ' to Direct / Indirect Managers? :',
                        header)

            #  Extra Information
            if self.health_condition or \
                    self.bankrupt or \
                    self.suspend_employment or \
                    self.court_law or \
                    self.about:
                emp_extra_info_ws = workbook.add_sheet('Extra Information')
                emp_extra_info_ws.col(emp_extra_info_col).width = 6000
                emp_extra_info_ws.write(
                    emp_extra_info_row, emp_extra_info_col, 'Employee Name',
                    header)
                if self.health_condition:
                    emp_extra_info_col += 1
                    emp_extra_info_ws.col(emp_extra_info_col).width = 15000
                    emp_extra_info_ws.write(
                        emp_extra_info_row,
                        emp_extra_info_col,
                        'Are you suffering from any physical disability'
                        ' or illness that requires you to be '
                        'medication for a prolonged period? ',
                        header)
                if self.bankrupt:
                    emp_extra_info_col += 1
                    emp_extra_info_ws.col(emp_extra_info_col).width = 15000
                    emp_extra_info_ws.write(
                        emp_extra_info_row, emp_extra_info_col,
                        'Have you ever been declared a bankrupt?', header)
                if self.suspend_employment:
                    emp_extra_info_col += 1
                    emp_extra_info_ws.col(emp_extra_info_col).width = 15000
                    emp_extra_info_ws.write(
                        emp_extra_info_row,
                        emp_extra_info_col,
                        'Have you ever been dismissed or suspended '
                        'from employement? ',
                        header)
                if self.court_law:
                    emp_extra_info_col += 1
                    emp_extra_info_ws.col(emp_extra_info_col).width = 15000
                    emp_extra_info_ws.write(
                        emp_extra_info_row,
                        emp_extra_info_col,
                        'Have you ever been convicted in a court of law'
                        ' in any country? ',
                        header)
                if self.about:
                    emp_extra_info_col += 1
                    emp_extra_info_ws.col(emp_extra_info_col).width = 15000
                    emp_extra_info_ws.write(
                        emp_extra_info_row, emp_extra_info_col,
                        'About Yourself', header)
            if self.first_name or self.last_name:
                emp_dependent_ws = workbook.add_sheet('Dependent Information')
                emp_dependent_info_col = 0
                emp_dependent_ws.col(emp_dependent_info_col).width = 6000
                emp_dependent_ws.write(
                    emp_edu_skill_row, emp_dependent_info_col, 'Employee Name',
                    header)
                if self.first_name:
                    emp_dependent_info_col += 1
                    emp_dependent_ws.col(emp_dependent_info_col).width = 6000
                    emp_dependent_ws.write(
                        emp_dependent_info_row, emp_dependent_info_col,
                        "First Name", header)
                if self.last_name:
                    emp_dependent_info_col += 1
                    emp_dependent_ws.col(emp_dependent_info_col).width = 6000
                    emp_dependent_ws.write(
                        emp_dependent_info_row, emp_dependent_info_col,
                        "Last Name", header)
                if self.relation_ship:
                    emp_dependent_info_col += 1
                    emp_dependent_ws.col(emp_dependent_info_col).width = 6000
                    emp_dependent_ws.write(
                        emp_dependent_info_row, emp_dependent_info_col,
                        "Relationship", header)
                if self.identification_number:
                    emp_dependent_info_col += 1
                    emp_dependent_ws.col(emp_dependent_info_col).width = 6000
                    emp_dependent_ws.write(
                        emp_dependent_info_row, emp_dependent_info_col,
                        "Identification Number", header)
            if (self.com_prog_know or self.shorthand or self.courses or
                    self.typing or self.other_know):
                emp_edu_skill_ws = workbook.add_sheet(
                    'Computer Knowledge and Skills')
                emp_edu_info_col = 0
                emp_edu_skill_ws.col(emp_edu_info_col).width = 6000
                emp_edu_skill_ws.write(
                    emp_edu_skill_row, emp_edu_info_col, 'Employee Name',
                    header)
                if self.com_prog_know:
                    emp_edu_info_col += 1
                    emp_edu_skill_ws.col(emp_edu_info_col).width = 6000
                    emp_edu_skill_ws.write(
                        emp_edu_skill_row, emp_edu_info_col,
                        'Computer Program Knowledge ', header)
                if self.shorthand:
                    emp_edu_info_col += 1
                    emp_edu_skill_ws.col(emp_edu_info_col).width = 6000
                    emp_edu_skill_ws.write(
                        emp_edu_skill_row, emp_edu_info_col, 'Shorthand',
                        header)
                if self.courses:
                    emp_edu_info_col += 1
                    emp_edu_skill_ws.col(emp_edu_info_col).width = 6000
                    emp_edu_skill_ws.write(
                        emp_edu_skill_row, emp_edu_info_col, 'Courses ',
                        header)
                if self.typing:
                    emp_edu_info_col += 1
                    emp_edu_skill_ws.col(emp_edu_info_col).width = 6000
                    emp_edu_skill_ws.write(
                        emp_edu_skill_row, emp_edu_info_col, 'Typing', header)
                if self.other_know:
                    emp_edu_info_col += 1
                    emp_edu_skill_ws.col(emp_edu_info_col).width = 6000
                    emp_edu_skill_ws.write(
                        emp_edu_skill_row, emp_edu_info_col,
                        'Other Knowledge & Skills', header)

            if self.job_title or self.emp_status or self.join_date \
                    or self.confirm_date or self.date_changed or \
                    self.changed_by or self.date_confirm_month:
                emp_job_ws = workbook.add_sheet('Job')
                emp_job_col = 0
                emp_job_ws.col(emp_job_col).width = 6000
                emp_job_ws.write(emp_job_row, emp_job_col,
                                 'Employee Name', header)
                if self.job_title:
                    emp_job_col += 1
                    emp_job_ws.col(emp_job_col).width = 6000
                    emp_job_ws.write(emp_job_row, emp_job_col,
                                     'Job Title', header)
                if self.emp_status:
                    emp_job_col += 1
                    emp_job_ws.col(emp_job_col).width = 6000
                    emp_job_ws.write(emp_job_row, emp_job_col,
                                     'Employment Status', header)
                if self.join_date:
                    emp_job_col += 1
                    emp_job_ws.col(emp_job_col).width = 6000
                    emp_job_ws.write(emp_job_row, emp_job_col,
                                     'Join Date', header)
                if self.confirm_date:
                    emp_job_col += 1
                    emp_job_ws.col(emp_job_col).width = 6000
                    emp_job_ws.write(emp_job_row, emp_job_col,
                                     'Date Confirmation', header)
                if self.date_changed:
                    emp_job_col += 1
                    emp_job_ws.col(emp_job_col).width = 6000
                    emp_job_ws.write(emp_job_row, emp_job_col,
                                     'Date Changed', header)
                if self.changed_by:
                    emp_job_col += 1
                    emp_job_ws.col(emp_job_col).width = 6000
                    emp_job_ws.write(emp_job_row, emp_job_col,
                                     'Changed By', header)
                if self.date_confirm_month:
                    emp_job_col += 1
                    emp_job_ws.col(emp_job_col).width = 6000
                    emp_job_ws.write(emp_job_row, emp_job_col,
                                     'Date Confirmation Month', header)

            if self.category_ids:
                emp_categories_ws = workbook.add_sheet('Categories')
                emp_categories_ws.col(0).width = 6000
                emp_categories_ws.col(1).width = 6000
                emp_categories_ws.col(2).width = 6000
                emp_categories_ws.write(
                    emp_categories_row, 0, 'Employee Name', header)
                emp_categories_ws.write(
                    emp_categories_row, 1, 'Category', header)
                emp_categories_ws.write(
                    emp_categories_row, 2, 'Parent Category', header)

            #  Immigration
            if self.immigration_ids:
                emp_immigration_ws = workbook.add_sheet('Immigration')
                emp_immigration_ws.col(0).width = 6000
                emp_immigration_ws.col(1).width = 6000
                emp_immigration_ws.col(2).width = 6000
                emp_immigration_ws.col(3).width = 6000
                emp_immigration_ws.col(4).width = 6000
                emp_immigration_ws.col(5).width = 6000
                emp_immigration_ws.col(6).width = 6000
                emp_immigration_ws.col(7).width = 6000
                emp_immigration_ws.col(8).width = 6000
                emp_immigration_ws.write(
                    emp_immigration_row, 0, 'Employee Name', header)
                emp_immigration_ws.write(
                    emp_immigration_row, 1, 'Document', header)
                emp_immigration_ws.write(
                    emp_immigration_row, 2, 'Number', header)
                emp_immigration_ws.write(
                    emp_immigration_row, 3, 'Issue Date', header)
                emp_immigration_ws.write(
                    emp_immigration_row, 4, 'Expiry Date', header)
                emp_immigration_ws.write(
                    emp_immigration_row, 5, 'Eligible Status', header)
                emp_immigration_ws.write(
                    emp_immigration_row, 6, 'Eligible Review Date', header)
                emp_immigration_ws.write(
                    emp_immigration_row, 7, 'Issue By', header)
                emp_immigration_ws.write(
                    emp_immigration_row, 8, 'Comment', header)

            #  Trainig Workshop
            if self.tarining_ids:
                emp_training_ws = workbook.add_sheet('Training Workshop')
                emp_training_ws.col(0).width = 6000
                emp_training_ws.col(1).width = 6000
                emp_training_ws.col(2).width = 6000
                emp_training_ws.col(3).width = 6000
                emp_training_ws.col(4).width = 15000
                emp_training_ws.write(
                    emp_training_row, 0, 'Employee Name', header)
                emp_training_ws.write(
                    emp_training_row, 1, 'Training Workshop', header)
                emp_training_ws.write(
                    emp_training_row, 2, 'Institution', header)
                emp_training_ws.write(emp_training_row, 3, 'Date', header)
                emp_training_ws.write(emp_training_row, 4, 'Comment', header)

            #  Leave History
            if self.emp_leave_ids:
                emp_leave_ws = workbook.add_sheet('Leave History')
                emp_leave_ws.col(0).width = 6000
                emp_leave_ws.col(1).width = 9000
                emp_leave_ws.col(2).width = 3000
                emp_leave_ws.col(3).width = 6000
                emp_leave_ws.col(4).width = 6000
                emp_leave_ws.col(5).width = 6000
                emp_leave_ws.col(6).width = 6000
                emp_leave_ws.write(emp_leave_row, 0, 'Employee Name', header)
                emp_leave_ws.write(emp_leave_row, 1, 'Description', header)
                emp_leave_ws.write(emp_leave_row, 2, 'Year', header)
                emp_leave_ws.write(emp_leave_row, 3, 'Start Date', header)
                emp_leave_ws.write(emp_leave_row, 4, 'End Date', header)
                emp_leave_ws.write(emp_leave_row, 5, 'Request Type', header)
                emp_leave_ws.write(emp_leave_row, 6, 'Leave Type', header)
                emp_leave_ws.write(emp_leave_row, 7, 'Number Of Days', header)
                emp_leave_ws.write(emp_leave_row, 8, 'State', header)
                emp_leave_ws.write(emp_leave_row, 9, 'Reason', header)

            #  Bank Details
            if self.bank_detail_ids:
                emp_bank_ws = workbook.add_sheet('Bank Details')
                emp_bank_ws.col(0).width = 6000
                emp_bank_ws.col(1).width = 6000
                emp_bank_ws.col(2).width = 6000
                emp_bank_ws.col(3).width = 6000
                emp_bank_ws.col(4).width = 6000
                emp_bank_ws.col(5).width = 6000
                emp_bank_ws.write(emp_bank_row, 0, 'Employee Name', header)
                emp_bank_ws.write(emp_bank_row, 1, 'Name Of Bank', header)
                emp_bank_ws.write(emp_bank_row, 2, 'Bank Code', header)
                emp_bank_ws.write(emp_bank_row, 3, 'Branch Code', header)
                emp_bank_ws.write(
                    emp_bank_row, 4, 'Bank Account Number', header)
                emp_bank_ws.write(emp_bank_row, 5, 'Beneficiary Name', header)

            #  Notes
            if self.notes:
                emp_note_ws = workbook.add_sheet('Notes')
                emp_note_ws.col(0).width = 6000
                emp_note_ws.col(1).width = 15000
                emp_note_ws.write(emp_note_row, 0, 'Employee Name', header)
                emp_note_ws.write(emp_note_row, 1, 'Note', header)

            #  Payslip
            if self.payslip:
                emp_payslip_ws = workbook.add_sheet('Payslip')
                emp_payslip_ws.col(0).width = 6000
                emp_payslip_ws.col(2).width = 16000
                emp_payslip_ws.write(emp_payslip_row, 0, 'Employee Name',
                                     header)
                emp_payslip_ws.write(emp_payslip_row, 1, 'Reference', header)
                emp_payslip_ws.write(emp_payslip_row, 2, 'Description',
                                     header)
                emp_payslip_ws.write(emp_payslip_row, 3, 'Date from', header)
                emp_payslip_ws.write(emp_payslip_row, 4, 'Date to', header)
                emp_payslip_ws.write(emp_payslip_row, 5, 'Amount', header)
                emp_payslip_ws.write(emp_payslip_row, 6, 'State', header)

            #  Payslip
            if self.contract:
                emp_contract_ws = workbook.add_sheet('Contract')
                emp_contract_ws.col(0).width = 6000
                emp_contract_ws.col(1).width = 6000
                emp_contract_ws.col(5).width = 6000
                emp_contract_ws.col(6).width = 6000
                emp_contract_ws.write(emp_contract_row, 0, 'Employee Name',
                                      header)
                emp_contract_ws.write(emp_contract_row, 1, 'Reference', header)
                emp_contract_ws.write(emp_contract_row, 2, 'Wage', header)
                emp_contract_ws.write(emp_contract_row, 3, 'Start date',
                                      header)
                emp_contract_ws.write(emp_contract_row, 4, 'End date', header)
                emp_contract_ws.write(emp_contract_row, 5, 'Salary structure',
                                      header)

            #  Payslip
            for emp in self.employee_ids:
                if self.user_id or \
                        self.active or \
                        self.department \
                        or self.direct_manager or \
                        self.indirect_manager:
                    emp_info_row += 1
                    emp_info_col = emp_per_info_col = 0
                    emp_info_ws.write(emp_info_row, emp_info_col,
                                      str(emp.name or ''), style)
                    if self.user_id:
                        emp_info_col += 1
                        emp_info_ws.write(emp_info_row, emp_info_col,
                                          str(emp.user_id.name or ''),
                                          style)
                    if self.active:
                        emp_info_col += 1
                        emp_info_ws.write(emp_info_row, emp_info_col,
                                          str(emp.active or ''),
                                          style)
                    if self.department:
                        emp_info_col += 1
                        d_name = emp.department_id.name or ''
                        emp_info_ws.write(emp_info_row, emp_info_col,
                                          str(d_name), style)
                    if self.direct_manager:
                        emp_info_col += 1
                        p_name = emp.parent_id.name or ''
                        emp_info_ws.write(emp_info_row, emp_info_col,
                                          str(p_name),
                                          style)
                    if self.indirect_manager:
                        emp_info_col += 1
                        mngr = emp.leave_manager.name or ''
                        emp_info_ws.write(emp_info_row, emp_info_col,
                                          str(mngr), style)
                #  Employee Personal Information
                if personal_information:
                    emp_per_info_row += 1
                    emp_per_info_col = 0
                    emp_personal_info_ws.write(
                        emp_per_info_row, emp_per_info_col,
                        str(emp.name or ''), style)
                    if self.identification_id:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row,
                            emp_per_info_col, str(
                                emp.identification_id or ''), style)
                    if self.passport_id:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col,
                            str(emp.passport_id or ''), style)

                    if self.gender:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col,
                            str(emp.gender or ''), style)
                    if self.marital:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col,
                            str(emp.marital or ''), style)
                    if self.nationality:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row,
                            emp_per_info_col, str(
                                emp.country_id.name or ''), style)
                    if self.dob:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col,
                            emp.birthday, date_format)
                    if self.pob:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col, str(
                                emp.place_of_birth or ''), style)
                    if self.age:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col,
                            str(emp.age or ''), style)

                    if self.home_address:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col, str(
                                emp.address_home_id.name or ''), style)
                    if self.country_id:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col, str(
                                emp.emp_country_id.name or ''), style)
                    if self.state_id:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col, str(
                                emp.emp_state_id.name or ''), style)
                    if self.city_id:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col, str(
                                emp.emp_city_id.name or ''), style)
                    if self.phone:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col,
                            str(emp.work_phone or ''), style)
                    if self.mobile:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col,
                            str(emp.mobile_phone or ''), style)
                    if self.email:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col,
                            str(emp.work_email or ''), style)

                    if self.permit_no:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col,
                            str(emp.permit_no or ''), style)
                    if self.dialect:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col,
                            str(emp.dialect or ''), style)
                    if self.driving_licence:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col, str(
                                emp.driving_licence or ''), style)
                    if self.employee_type_id:
                        emp_per_info_col += 1
                        emp_personal_info_ws.write(
                            emp_per_info_row, emp_per_info_col, str(
                                emp.employee_type_id.name or ''), style)

                #  Appraisal
                    if self.evaluation_plan_id:
                        emp_appraisal_col += 1
                        emp_appraisal_ws.write(
                            emp_appraisal_row, emp_appraisal_col, '', style)
                    if self.evaluation_date:
                        emp_appraisal_col += 1
                        emp_appraisal_ws.write(
                            emp_appraisal_row, emp_appraisal_col, '', style)

                #  Notification
                if (self.emp_noty_leave or self.pending_levae_noty or
                        self.receive_mail_manager):
                    emp_notification_row += 1
                    emp_notification_col = 0
                    emp_notification_ws.write(
                        emp_notification_row, emp_notification_col,
                        str(emp.name or ''), style)
                    if self.emp_noty_leave:
                        emp_notification_col += 1
                        emp_notification_ws.write(
                            emp_notification_row, emp_notification_col,
                            str(
                                emp.is_daily_notificaiton_email_send or ''),
                            style)
                    if self.pending_levae_noty:
                        emp_notification_col += 1
                        emp_notification_ws.write(
                            emp_notification_row, emp_notification_col,
                            str(
                                emp.is_pending_leave_notificaiton or ''),
                            style)
                    if self.receive_mail_manager:
                        emp_notification_col += 1
                        emp_notification_ws.write(
                            emp_notification_row, emp_notification_col,
                            str(
                                emp.is_all_final_leave), style)

                #  Extra Information
                if self.health_condition or \
                        self.bankrupt or \
                        self.suspend_employment or \
                        self.court_law or \
                        self.about:
                    emp_extra_info_col = 0
                    emp_extra_info_row += 1
                    emp_extra_info_ws.write(
                        emp_extra_info_row, emp_extra_info_col,
                        str(emp.name or ''), style)
                    if self.health_condition:
                        emp_extra_info_col += 1
                        helath_condition = ''
                        if emp.physical_stability:
                            helath_condition = 'Yes'
                        if emp.physical_stability_no:
                            helath_condition = 'No'
                        emp_extra_info_ws.write(
                            emp_extra_info_row, emp_extra_info_col, str(
                                helath_condition or ''), style)
                    if self.bankrupt:
                        emp_extra_info_col += 1
                        bankrupt = ''
                        if emp.bankrupt_b:
                            bankrupt = 'Yes'
                        if emp.bankrupt_no:
                            bankrupt = 'No'
                        emp_extra_info_ws.write(
                            emp_extra_info_row, emp_extra_info_col,
                            str(bankrupt or ''), style)
                    if self.suspend_employment:
                        emp_extra_info_col += 1
                        supspend = ''
                        if emp.dismissed_b:
                            supspend = 'Yes'
                        if emp.dismissed_no:
                            supspend = 'No'
                        emp_extra_info_ws.write(
                            emp_extra_info_row, emp_extra_info_col,
                            str(supspend or ''), style)
                    if self.court_law:
                        emp_extra_info_col += 1
                        court = ''
                        if emp.court_b:
                            court = "Yes"
                        if emp.court_no:
                            court = "No"
                        emp_extra_info_ws.write(
                            emp_extra_info_row, emp_extra_info_col,
                            str(court or ''), style)
                    if self.about:
                        emp_extra_info_col += 1
                        emp_extra_info_ws.write(
                            emp_extra_info_row, emp_extra_info_col,
                            str(emp.about or ''), style)

                if self.first_name:
                    for dependent in emp.dependent_ids:
                        emp_dependent_col = 0
                        emp_dependent_info_row += 1
                        emp_dependent_ws.write(
                            emp_dependent_info_row, emp_dependent_col,
                            str(emp.name or ''), style)
                        if self.first_name:
                            emp_dependent_col += 1
                            emp_dependent_ws.write(
                                emp_dependent_info_row,
                                emp_dependent_col, str(
                                    dependent.first_name or ''), style)
                        if self.last_name:
                            emp_dependent_col += 1
                            emp_dependent_ws.write(
                                emp_dependent_info_row,
                                emp_dependent_col, str(
                                    dependent.last_name or ''), style)
                        if self.relation_ship:
                            emp_dependent_col += 1
                            emp_dependent_ws.write(
                                emp_dependent_info_row,
                                emp_dependent_col, str(
                                    dependent.relation_ship or ''), style)
                        if self.identification_number:
                            emp_dependent_col += 1
                            emp_dependent_ws.write(
                                emp_dependent_info_row,
                                emp_dependent_col, str(
                                    dependent.identification_number or ''),
                                style)

                #  Educational Information
                if (self.com_prog_know or self.shorthand or
                        self.courses or self.typing or self.other_know):
                    for edu in emp.education_info_line:
                        emp_edu_skill_col = 0
                        emp_edu_skill_row += 1
                        emp_edu_skill_ws.write(
                            emp_edu_skill_row, emp_edu_skill_col,
                            str(emp.name or ''), style)
                        if self.com_prog_know:
                            emp_edu_skill_col += 1
                            emp_edu_skill_ws.write(
                                emp_edu_skill_row,
                                emp_edu_skill_col, str(
                                    edu.comp_prog_knw or ''), style)
                        if self.shorthand:
                            emp_edu_skill_col += 1
                            emp_edu_skill_ws.write(
                                emp_edu_skill_row, emp_edu_skill_col,
                                str(edu.shorthand or ''), style)
                        if self.courses:
                            emp_edu_skill_col += 1
                            emp_edu_skill_ws.write(
                                emp_edu_skill_row, 3,
                                str(edu.course or ''), style)
                        if self.typing:
                            emp_edu_skill_col += 1
                            emp_edu_skill_ws.write(
                                emp_edu_skill_row, 4,
                                str(edu.typing or ''), style)
                        if self.other_know:
                            emp_edu_skill_col += 1
                            emp_edu_skill_ws.write(
                                emp_edu_skill_row, 5,
                                str(edu.other_know or ''), style)

#                 #Job
                if self.job_title or \
                        self.emp_status \
                        or self.join_date \
                        or self.confirm_date \
                        or self.date_changed \
                        or self.changed_by \
                        or self.date_confirm_month:
                    for job in emp.history_ids:
                        emp_job_col = 0
                        emp_job_row += 1
                        emp_job_ws.write(emp_job_row, emp_job_col,
                                         str(emp.name or ''), style)
                        if self.job_title:
                            emp_job_col += 1
                            emp_job_ws.write(
                                emp_job_row, emp_job_col,
                                str(
                                    job.job_id.name or ''), style)
                        if self.emp_status:
                            emp_job_col += 1
                            emp_job_ws.write(
                                emp_job_row, emp_job_col, str(
                                    job.emp_status or ''), style)
                        if self.join_date:
                            emp_job_col += 1
                            emp_job_ws.write(
                                emp_job_row, emp_job_col,
                                job.join_date or '', date_format)
                        if self.confirm_date:
                            emp_job_col += 1
                            emp_job_ws.write(
                                emp_job_row, emp_job_col,
                                job.confirm_date or '', date_format)
                        if self.date_changed:
                            emp_job_col += 1
                            emp_job_ws.write(
                                emp_job_row,
                                emp_job_col,
                                job.date_changed or '',
                                date_format)
                        if self.changed_by:
                            emp_job_col += 1
                            emp_job_ws.write(
                                emp_job_row, emp_job_col,
                                str(
                                    job.user_id.name or ''), style)
                        if self.date_confirm_month:
                            emp_job_col += 1
                            emp_job_ws.write(
                                emp_job_row, emp_job_col,
                                job.confirm_date or '',
                                date_format)
                #  Categories
                if self.category_ids:
                    for category in emp.category_ids:
                        emp_categories_row += 1
                        emp_categories_ws.write(
                            emp_categories_row, 0,
                            str(emp.name or ''), style)
                        emp_categories_ws.write(
                            emp_categories_row, 1,
                            str(category.name or ''), style)
                        emp_categories_ws.write(
                            emp_categories_row, 2, str(''), style)
                #  Immigration
                if self.immigration_ids:
                    for immigration in emp.immigration_ids:
                        emp_immigration_row += 1
                        emp_immigration_ws.write(
                            emp_immigration_row, 0,
                            str(emp.name or ''), style)
                        emp_immigration_ws.write(
                            emp_immigration_row, 1, str(
                                immigration.documents or ''), style)
                        emp_immigration_ws.write(
                            emp_immigration_row, 2, str(
                                immigration.number or ''), style)
                        emp_immigration_ws.write(
                            emp_immigration_row, 3,
                            immigration.issue_date or '', date_format)
                        emp_immigration_ws.write(
                            emp_immigration_row, 4,
                            immigration.exp_date or '', date_format)
                        emp_immigration_ws.write(
                            emp_immigration_row, 5, str(
                                immigration.eligible_status or ''), style)
                        emp_immigration_ws.write(
                            emp_immigration_row, 6,
                            immigration.eligible_review_date or '',
                            date_format)
                        emp_immigration_ws.write(
                            emp_immigration_row, 7, str(
                                immigration.issue_by.name or ''), style)
                        emp_immigration_ws.write(
                            emp_immigration_row, 8, str(
                                immigration.comments or ''), style)
                #  Trainig Workshop
                if self.tarining_ids:
                    if emp.training_ids:
                        for training in emp.training_ids:
                            emp_training_row += 1
                            emp_training_ws.write(
                                emp_training_row, 0,
                                str(emp.name or ''), style)
                            emp_training_ws.write(
                                emp_training_row, 1, str(
                                    training.tr_title or ''), style)
                            emp_training_ws.write(
                                emp_training_row, 2, str(
                                    training.tr_institution or ''), style)
                            emp_training_ws.write(
                                emp_training_row, 3,
                                training.tr_date or '', date_format)
                            emp_training_ws.write(
                                emp_training_row, 4,
                                str(
                                    training.comments or ''), style)
                    else:
                        emp_training_row += 1
                        emp_training_ws.write(
                            emp_training_row, 0,
                            str(emp.name or ''), style)
                        emp_training_ws.write(emp_training_row, 1, '', style)
                        emp_training_ws.write(emp_training_row, 2, '', style)
                        emp_training_ws.write(emp_training_row, 3, '', style)
                        emp_training_ws.write(emp_training_row, 4, '', style)

                #  Leave History
                if self.emp_leave_ids:
                    for leave in emp.employee_leave_ids:
                        emp_leave_row += 1
                        emp_leave_ws.write(
                            emp_leave_row, 0, str(emp.name or ''),
                            style)
                        emp_leave_ws.write(
                            emp_leave_row, 1, str(leave.name or ''),
                            style)
                        emp_leave_ws.write(
                            emp_leave_row, 3,
                            leave.date_from or '',
                            date_format)
                        emp_leave_ws.write(
                            emp_leave_row, 4,
                            leave.date_to or '',
                            date_format)
                        emp_leave_ws.write(emp_leave_row, 5, '', style)
                        emp_leave_ws.write(emp_leave_row, 7, str(
                            ''), style)
                        emp_leave_ws.write(emp_leave_row, 8, str(
                            LEAVE_STATE.get(leave.state, '')), style)
                #  Bank Details
                if self.bank_detail_ids:
                    for bank in emp.bank_detail_ids:
                        emp_bank_row += 1
                        emp_bank_ws.write(
                            emp_bank_row, 0, str(emp.name or ''), style)
                        emp_bank_ws.write(emp_bank_row, 1, str(
                            bank.bank_name or ''), style)
                        emp_bank_ws.write(emp_bank_row, 2, str(
                            bank.bank_code or ''), style)
                        emp_bank_ws.write(emp_bank_row, 3, str(
                            bank.branch_code or ''), style)
                        emp_bank_ws.write(emp_bank_row, 4, str(
                            bank.bank_ac_no or ''), style)
                        emp_bank_ws.write(emp_bank_row, 5, str(
                            bank.beneficiary_name or ''), style)

                #  Notes
                if self.notes:
                    emp_note_row += 1
                    emp_note_ws.write(
                        emp_note_row, 0, str(emp.name or ''), style)
                    emp_note_ws.write(
                        emp_note_row, 1, str(emp.notes or ''), style)

                #  Payslip
                if self.payslip:
                    payslip_ids = payslip_obj.search(
                        [('employee_id', '=', emp.id)])
                    for payslip in payslip_obj.browse(payslip_ids.ids):
                        net_amount = 0.0
                        for line in payslip.line_ids:
                            if line.code == "NET":
                                net_amount = line.amount
                        emp_payslip_row += 1
                        emp_payslip_ws.write(
                            emp_payslip_row, 0, str(emp.name or ''),
                            style)
                        emp_payslip_ws.write(emp_payslip_row, 1, str(
                            payslip.number or ''), style)
                        emp_payslip_ws.write(
                            emp_payslip_row, 2, str(payslip.name or ''),
                            style)
                        emp_payslip_ws.write(
                            emp_payslip_row, 3,
                            payslip.date_from or '',
                            date_format)
                        emp_payslip_ws.write(
                            emp_payslip_row, 4,
                            payslip.date_to or '',
                            date_format)
                        emp_payslip_ws.write(
                            emp_payslip_row, 5, net_amount, number_format)
                        emp_payslip_ws.write(emp_payslip_row, 6, str(
                            PAYSLIP_STATE.get(payslip.state, '')), style)

                if self.contract:
                    contract_ids = contract_obj.search(
                        [('employee_id', '=', emp.id)])
                    for contract in contract_obj.browse(contract_ids.ids):
                        emp_contract_row += 1
                        emp_contract_ws.write(
                            emp_contract_row, 0, str(
                                emp.name or ''), style)
                        emp_contract_ws.write(
                            emp_contract_row, 1, str(
                                contract.name or ''), style)
                        emp_contract_ws.write(
                            emp_contract_row, 2, contract.wage, number_format)
                        emp_contract_ws.write(
                            emp_contract_row, 3,
                            contract.date_start or '',
                            date_format)
                        emp_contract_ws.write(
                            emp_contract_row, 4,
                            contract.date_end or '', date_format)
                        emp_contract_ws.write(emp_contract_row, 5, str(
                            contract.struct_id and
                            contract.struct_id.name or ''), style)
#                        emp_contract_ws.write(emp_contract_row, 6, str(
# contract.commission_id and contract.commission_id.name or ''), style)

        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        res = base64.b64encode(data)
        export_rec = self.env['export.employee.data.record.xls'].create(
            {'name': 'Employee Summary.xls', 'file': res})
        return {
            'name': _('Employee Summary Report'),
            'res_id': export_rec.id,
            "view_mode": 'form',
            'res_model': 'export.employee.data.record.xls',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }
