import time
import base64
import tempfile
from xml.dom import minidom
from datetime import datetime
from odoo.tools.misc import get_lang

from odoo import tools
from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF


class EmpAppendix8aTextFile(models.TransientModel):
    _name = 'emp.appendix8a.text.file'
    _description = "Appendix 8a Text File"

    def _get_payroll_user_name(self):
        supervisors_list = [(False, '')]
        group_data = self.env.ref('l10n_sg_hr_payroll.group_hr_payroll_admin')
        for user in group_data.users:
            supervisors_list.append((tools.ustr(user.id),
                                     tools.ustr(user.name)))
        return supervisors_list

    employee_ids = fields.Many2many(
        'hr.employee', 'hr_employe_appendix8a_text_rel', 'emp_id',
        'employee_id', 'Employee', required=False)
    start_date = fields.Date('Start Date', required=True,
                             default=lambda *a: time.strftime('%Y-01-01'))
    end_date = fields.Date('End Date', required=True,
                           default=lambda *a: time.strftime('%Y-12-31'))
    source = fields.Selection([('1', 'Mindef'),
                               ('4', 'Government Department'),
                               ('5', 'Statutory Board'),
                               ('6', 'Private Sector'),
                               ('9', 'Others')], string='Source', default='6')
    batch_indicatior = fields.Selection(
        [('O', 'Original'), ('A', 'Amendment')], string='Batch Indicator')
    batch_date = fields.Date('Batch Date')
    payroll_user = fields.Selection(
        _get_payroll_user_name, 'Name of authorized person')
    print_type = fields.Selection([('text', 'Text'),
                                   ('pdf', 'PDF'),
                                   ('xml', 'XML')], 'Print as', required=True,
                                  default='text')

    def download_appendix8a_txt_file(self):
        context = dict(self._context) or {}
        context.update({'active_test': False})
        data = self.read([])[0]
        start_year = data.get('start_date', False).strftime('%Y')
        to_year = data.get('end_date', False).strftime('%Y')
        start_date = '%s-01-01' % tools.ustr(int(start_year) - 1)
        end_date = '%s-12-31' % tools.ustr(int(to_year) - 1)
        start_date_year = '%s-01-01' % tools.ustr(int(start_year))
        end_date_year = '%s-12-31' % tools.ustr(int(to_year))
        if 'start_date' in data and 'end_date' in data and \
                data.get('start_date', False) >= data.get('end_date', False):
            raise ValidationError(
                _("You must enter start date less than end date."))
        if len(data['employee_ids']) == 0:
            raise ValidationError(_("Please select employee"))
        emp_ids = data.get('employee_ids') or []
        user_rec = self.env.user

        contract_obj = self.env['hr.contract']
        incometax_obj = self.env['hr.contract.income.tax']
        if emp_ids and emp_ids is not False:
            for employee in self.env['hr.employee'].browse(emp_ids):
                emp_name = employee and employee.name or ''
                emp_id = employee and employee.id or False
                contract_ids = contract_obj.search([
                    ('employee_id', '=', emp_id)])
                contract_income_tax_ids = incometax_obj.search([
                    ('contract_id', 'in', contract_ids.ids),
                    ('start_date', '>=', self.start_date),
                    ('end_date', '<=', self.end_date)])
                if not contract_income_tax_ids.ids:
                    raise ValidationError(
                        _("There is no Income tax details available between "
                          "selected date %s and %s for the %s employee for "
                          "contract." % (
                            self.start_date.strftime(
                                get_lang(self.env).date_format),
                            self.end_date.strftime(
                                get_lang(self.env).date_format), emp_name)))
                payslip_ids = self.env['hr.payslip'].search(
                    [('date_from', '>=', self.start_date),
                     ('date_from', '<=', self.end_date),
                     ('employee_id', '=', emp_id),
                     ('state', 'in', ['draft', 'done', 'verify'])])
                if not payslip_ids.ids:
                    raise ValidationError(
                        _("There is no payslip details available between "
                          "selected date %s and %s for the %s employee." % (
                            self.start_date.strftime(
                                get_lang(self.env).date_format),
                            self.end_date.strftime(
                                get_lang(self.env).date_format), emp_name)))
        context.update({'employe_id': data['employee_ids'], 'datas': data})
        if data.get('print_type', '') == 'text':
            tgz_tmp_filename = tempfile.mktemp(suffix='.txt')
            tmp_file = False
            start_date = end_date = False
            from_date = context.get('datas', False).get('start_date', False)
            to_date = context.get('datas', False).get('end_date', False)
            if from_date and to_date:
                basis_year = tools.ustr(from_date.year - 1)
                start_date = '%s-01-01' % tools.ustr(int(from_date.year) - 1)
                end_date = '%s-12-31' % tools.ustr(int(from_date.year) - 1)
                start_date = datetime.strptime(start_date, DSDF)
                end_date = datetime.strptime(end_date, DSDF)
            try:
                tmp_file = open(tgz_tmp_filename, "w")
                batchdate = context.get('datas')['batch_date']
                if batchdate > datetime.today().date():
                    raise ValidationError(_("Batch date can not be future date"))
                batchdate = batchdate.strftime('%Y%m%d')
                #  server_date = basis_year + strftime("%m%d", gmtime())
                emp_rec = self.env['hr.employee'].search(
                    [('user_id', '=',
                      int(context.get('datas')['payroll_user']))], limit=1)
                emp_designation = ''
                user_brw = self.env['res.users'].browse(
                    int(context.get('datas')['payroll_user']))
                payroll_admin_user_name = user_brw.name
                company_name = user_brw.company_id.name
                organization_id_type = user_rec.company_id.organization_id_type
                organization_id_no = user_rec.company_id.organization_id_no
                if emp_rec and emp_rec.id:
                    emp_designation = emp_rec.job_id.name
                    emp_email = emp_rec.work_email
                    emp_contact = emp_rec.work_phone
                """ Header for Appendix8A """
                header_record = '0'.ljust(1) + \
                                tools.ustr(context.get('datas')['source'] or
                                           '').ljust(1) + \
                                tools.ustr(basis_year or '').ljust(4) + \
                                tools.ustr(organization_id_type or
                                           '').ljust(1) + \
                                tools.ustr(
                                    organization_id_no or '').ljust(12) + \
                                tools.ustr(payroll_admin_user_name or
                                           '')[:30].ljust(30) + \
                                tools.ustr(
                                    emp_designation or '')[:30].ljust(30) + \
                                tools.ustr(company_name)[:60].ljust(60) + \
                                tools.ustr(emp_contact)[:20].ljust(20) + \
                                tools.ustr(emp_email)[:60].ljust(60) + \
                                tools.ustr(
                                    context.get('datas')[
                                        'batch_indicatior'] or '').ljust(1) + \
                                tools.ustr(batchdate).ljust(8) + \
                                ''.ljust(30) + \
                                ''.ljust(10) + \
                                ''.ljust(432) + \
                                "\r\n"
                tmp_file.write(header_record)

                """ get the contract for selected employee"""
                contract_ids = contract_obj.search(
                    [('employee_id', 'in', context.get('employe_id'))])
                from_date = to_date = ''
                for contract in contract_ids:
                    tax_domain = [('contract_id', '=', contract.id),
                                  ('start_date', '>=', start_date_year),
                                  ('end_date', '<=', end_date_year)]
                    contract_income_tax_ids = incometax_obj.search(tax_domain)
                    emp_id = contract.employee_id
                    if not emp_id.identification_id:
                        raise ValidationError(
                            _("There is no identification no define for %s "
                              "employee." % (emp_id.name)))
                    if contract_income_tax_ids and contract_income_tax_ids.ids:
                        for emp in contract_income_tax_ids[0]:
                            if emp.from_date:
                                from_date = emp.from_date.strftime('%Y%m%d')
                            if emp.to_date:
                                to_date = emp.to_date.strftime('%Y%m%d')
                            annual_value = rent_landloard = \
                                place_of_residence_taxable_value = \
                                total_rent_paid = 0
                            utilities_misc_value = driver_value = \
                                employer_paid_amount = \
                                taxalble_value_of_utilities_housekeeping = ''
                            actual_hotel_accommodation = \
                                employee_paid_amount = \
                                taxable_value_of_hotel_acco = ''
                            cost_of_home_leave_benefits = interest_payment = \
                                insurance_payment = free_holidays = \
                                edu_expenses = ''
                            non_monetary_awards = entrance_fees = \
                                gains_from_assets = cost_of_motor = \
                                car_benefits = non_monetary_benefits = ''
                            """ string variable declaration"""
                            furniture_value = total_taxable_value = \
                                annual_value = \
                                '%0*d' % (9, int(abs(emp.annual_value * 100)))
                            if emp.annual_value == 0 and not \
                                    emp.furniture_value_indicator:
                                if emp.rent_landloard == 0:
                                    raise ValidationError(
                                        "Rent paid to landlord including "
                                        "rental of Furniture & Fittings can "
                                        "not be zero")
                            """Must be blank if item annual_value(6a) is
                            not blank or > zero """
                            if annual_value != '' or int(emp.annual_value) > 0:
                                rent_landloard = ''
                            else:
                                rent_landloard = \
                                    '%0*d' % (9, int(abs(emp.rent_landloard)))
                            line11 = line22 = line33 = ''
                            if int(emp.annual_value) > 0 or \
                                    emp.rent_landloard > 0:
                                if not emp.address:
                                    raise ValidationError(
                                        _("There is no address define for %s "
                                          "employee." % (emp_id.name)))
                                if emp.address:
                                    emp_address = str(emp.address)
                                    demo_lst = list(emp_address)
                                    line1 = []
                                    line2 = []
                                    line3 = []
                                    indexes = [i for i, x in enumerate(
                                        demo_lst) if x == '\n']
                                    if len(indexes) == 1:
                                        for lst in range(0, indexes[0]):
                                            line1.append(demo_lst[lst])
                                        for lst1 in range(int(indexes[0]) + 1,
                                                          len(demo_lst)):
                                            line2.append(demo_lst[lst1])
                                    elif len(indexes) == 2:
                                        for lst in range(0, indexes[0]):
                                            line1.append(demo_lst[lst])
                                        for lst1 in range(int(indexes[0]) + 1,
                                                          int(indexes[1])):
                                            line2.append(demo_lst[lst1])
                                        for lst2 in range(int(indexes[1]) + 1,
                                                          len(demo_lst)):
                                            line3.append(demo_lst[lst2])
                                    line11 = ''.join(line1)
                                    line22 = ''.join(line2)
                                    line33 = ''.join(line3)
                            """ Cannot be blank when Value of Furniture &
                            Fitting indicator is not blank."""
                            if emp.furniture_value_indicator:
                                if int(emp.furniture_value) < 0:
                                    raise UserError(
                                        _("Cannot be blank or zero when Value "
                                          "of Furniture & Fitting indicator "
                                          "is not blank."))
                                else:
                                    furniture_value = '%0*d' % (
                                        9, int(abs(emp.furniture_value * 100)))

                            """No of employee cannot be blank when annual
                            value or  rent paid to landlord is not blank or
                            not zero"""
                            no_of_emp = 0
                            if (emp.annual_value) > 0 or \
                                    (emp.rent_landloard) > 0:
                                if (emp.no_of_emp) == 0:
                                    raise UserError(
                                        _("No of employee can not be zero or "
                                          "blank when annual value or rent "
                                          "paid to landlord is not blank"))
                                else:
                                    no_of_emp = '%0*d' % (2,
                                                          int(emp.no_of_emp))

                            """ If not blank, must be Y or N."""
                            cost_of_home_leave_benefits = \
                                '%0*d' % (9, int(abs(
                                    emp.cost_of_home_leave_benefits * 100)))

                            place_of_residence_taxable_value = '%0*d' % (
                                9, int(abs(
                                    emp.place_of_residence_taxable_value * 100
                                    )))
                            total_rent_paid = '%0*d' % (
                                9, int(abs(emp.total_rent_paid * 100)))
                            utilities_misc_value = '%0*d' % (
                                9, int(abs(emp.utilities_misc_value * 100)))
                            driver_value = '%0*d' % (
                                9, int(abs(emp.driver_value * 100)))
                            employer_paid_amount = '%0*d' % (
                                9, int(abs(emp.employer_paid_amount * 100)))
                            house = \
                                emp.taxalble_value_of_utilities_housekeeping
                            taxalble_value_of_utilities_housekeeping = \
                                '%0*d' % (
                                    9, int(abs(house * 100)))
                            actual_hotel_accommodation = '%0*d' % (
                                9, int(
                                    abs(emp.actual_hotel_accommodation * 100)))
                            employee_paid_amount = '%0*d' % (
                                9, int(abs(emp.employee_paid_amount) * 100))
                            taxable_value_of_hotel_acco = '%0*d' % (
                                9, int(abs(
                                    emp.taxable_value_of_hotel_acco * 100)))
                            interest_payment = '%0*d' % (
                                9, int(abs(emp.interest_payment * 100)))
                            insurance_payment = '%0*d' % (
                                9, int(abs(emp.insurance_payment * 100)))
                            free_holidays = '%0*d' % (
                                9, int(abs(emp.free_holidays * 100)))
                            edu_expenses = '%0*d' % (
                                9, int(abs(emp.edu_expenses * 100)))
                            non_monetary_awards = '%0*d' % (
                                9, int(abs(emp.non_monetary_awards * 100)))
                            entrance_fees = '%0*d' % (
                                9, int(abs(emp.entrance_fees * 100)))
                            gains_from_assets = '%0*d' % (
                                9, int(abs(emp.gains_from_assets * 100)))
                            cost_of_motor = '%0*d' % (
                                9, int(abs(emp.cost_of_motor * 100)))
                            car_benefits = '%0*d' % (
                                9, int(abs(emp.car_benefits * 100)))
                            non_monetary_benefits = '%0*d' % (
                                9, int(abs(emp.non_monetary_benefits * 100)))
                            no_of_passanger = '%0*d' % (
                                3, int(abs(emp.no_of_passanger * 100)))
                            spouse = '%0*d' % (2, int(abs(emp.spouse * 100)))
                            children = '%0*d' % (2,
                                                 int(abs(emp.children * 100)))

                            """ 6f = 6d – 6e"""
                            total_taxable_value = '%0*d' % (
                                9, int(abs(emp.total_taxable_value * 100)))

                            """ Value must be the sum of item 6f, 6j, 7c, 8a
                            to 8k."""
                            total_value_of_benefits = '%0*d' % (
                                9, int(abs(emp.total_value_of_benefits * 100)))
                            indicator = emp.furniture_value_indicator
                            taxable_value = place_of_residence_taxable_value
                            h_keeping = \
                                taxalble_value_of_utilities_housekeeping
                            detail_record = '1'.ljust(1) + \
                                            tools.ustr(
                                                emp_id.identification_no or
                                                '').ljust(1) + \
                                            tools.ustr(
                                                emp_id.identification_id or
                                                '')[:12].ljust(12) + \
                                            tools.ustr(
                                                emp_id.name or
                                                '')[:40].ljust(40) + \
                                            ''.ljust(40) + \
                                            tools.ustr(
                                                line11 or
                                                '')[:30].ljust(30) + \
                                            tools.ustr(
                                                line22 or
                                                '')[:30].ljust(30) + \
                                            tools.ustr(
                                                line33 or
                                                '')[:30].ljust(30) + \
                                            tools.ustr(
                                                from_date)[:8].ljust(8) + \
                                            tools.ustr(
                                                to_date)[:8].ljust(8) + \
                                            tools.ustr(
                                                emp.no_of_days)[
                                                :3].ljust(3) + \
                                            tools.ustr(
                                                no_of_emp)[:2].ljust(2) + \
                                            tools.ustr(
                                                annual_value)[:9].ljust(9) + \
                                            tools.ustr(indicator or
                                                       '')[:1].ljust(1) + \
                                            tools.ustr(
                                                furniture_value)[:9].ljust(9) \
                                            +\
                                            tools.ustr(
                                                rent_landloard)[:9].ljust(9) \
                                            +\
                                            tools.ustr(
                                                taxable_value)[:9].ljust(9) + \
                                            tools.ustr(
                                                total_rent_paid)[:9].ljust(9) \
                                            +\
                                            tools.ustr(
                                                total_taxable_value)[
                                                :9].ljust(9) + \
                                            tools.ustr(utilities_misc_value)[
                                                :9].ljust(9) + \
                                            tools.ustr(driver_value)[:9].ljust(
                                                9) + \
                                            tools.ustr(
                                                employer_paid_amount)[
                                                :9].ljust(9) + \
                                            tools.ustr(
                                                h_keeping)[:9].ljust(9) + \
                                            tools.ustr(
                                                actual_hotel_accommodation)[
                                                :9].ljust(9) + \
                                            tools.ustr(employee_paid_amount)[
                                                :9].ljust(9) + \
                                            tools.ustr(
                                                taxable_value_of_hotel_acco)[
                                                :9].ljust(9) + \
                                            tools.ustr(
                                                cost_of_home_leave_benefits)[
                                                :9].ljust(9) + \
                                            tools.ustr(
                                                no_of_passanger)[:2].ljust(2) \
                                            +\
                                            tools.ustr(spouse)[:2].ljust(2) + \
                                            tools.ustr(
                                                children)[:2].ljust(2) + \
                                            tools.ustr('')[:1].ljust(1) + \
                                            tools.ustr(
                                                interest_payment)[
                                                :9].ljust(9) + \
                                            tools.ustr(
                                                insurance_payment)[
                                                :9].ljust(9) + \
                                            tools.ustr(
                                                free_holidays)[:9].ljust(9) + \
                                            tools.ustr(edu_expenses)[
                                                :9].ljust(9) + \
                                            tools.ustr(
                                                non_monetary_awards)[
                                                :9].ljust(9) + \
                                            tools.ustr(
                                                entrance_fees)[:9].ljust(9) + \
                                            tools.ustr(
                                                gains_from_assets)[
                                                :9].ljust(9) + \
                                            tools.ustr(
                                                cost_of_motor)[:9].ljust(9) + \
                                            tools.ustr(
                                                car_benefits)[:9].ljust(9) + \
                                            tools.ustr(
                                                non_monetary_benefits)[
                                                :9].ljust(9) + \
                                            tools.ustr(
                                                total_value_of_benefits)[
                                                :9].ljust(9) + \
                                            ''.ljust(212) + \
                                            ''.ljust(50) + \
                                "\r\n"
                            tmp_file.write(detail_record)
            finally:
                if tmp_file:
                    tmp_file.close()
            file_rep = open(tgz_tmp_filename, "rb")
            out = file_rep.read()
            file_rep.close()
            res = base64.b64encode(out)
            module_rec = self.env['binary.appendix8a.text.file.wizard'].create(
                {'name': 'appendix8a.txt', 'appendix8a_txt_file': res})
            return {
                'name': _('Binary'),
                'res_id': module_rec.id,
                "view_mode": 'form',
                'res_model': 'binary.appendix8a.text.file.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context,
            }
        elif data.get('print_type', '') == 'xml':
            doc = minidom.Document()
            root = doc.createElement('A8A2015')
            root_url = 'http://www.iras.gov.sg/A8A2015'
            root.setAttribute('xmlns', 'http://www.iras.gov.sg/A8A2015Def')
            doc.appendChild(root)

            start_date = end_date = False
            from_date = context.get('datas', False
                                    ).get('start_date', False) or False
            to_date = context.get('datas', False
                                  ).get('end_date', False) or False
            basis_year = tools.ustr(from_date.year - 1)
            start_date = '%s-01-01' % tools.ustr(int(from_date.year) - 1)
            end_date = '%s-12-31' % tools.ustr(int(from_date.year) - 1)
            start_date = datetime.strptime(start_date, DSDF)
            end_date = datetime.strptime(end_date, DSDF)

            batchdate = context.get('datas')['batch_date'].strftime('%Y%m%d')

            emp_rec = self.env['hr.employee'].search(
                [('user_id', '=', int(context.get('datas')['payroll_user']))
                 ], limit=1)
            emp_designation = emp_contact = emp_email = ''
            user_brw = self.env['res.users'].browse(int(context.get('datas')[
                'payroll_user']))
            payroll_admin_user_name = user_brw.name or ''
            company_name = user_brw.company_id.name or ''
            organization_id_type = user_rec.company_id and \
                user_rec.company_id.organization_id_type or ''
            organization_id_no = user_rec.company_id and \
                user_rec.company_id.organization_id_no or ''
            for emp in emp_rec:
                emp_designation = emp.job_id.name
                emp_email = emp.work_email
                emp_contact = emp.work_phone
                if not emp_email and emp_contact:
                    raise ValidationError(
                        _("Please configure Email or Contact for %s "
                          "employee." % (emp.name)))

            """ Header for Appendix8A """
            header = doc.createElement('A8AHeader')
            root.appendChild(header)

            ESubmissionSDSC = doc.createElement('ESubmissionSDSC')
            ESubmissionSDSC.setAttribute(
                'xmlns', 'http://tempuri.org/ESubmissionSDSC.xsd')
            header.appendChild(ESubmissionSDSC)

            FileHeaderST = doc.createElement('FileHeaderST')
            ESubmissionSDSC.appendChild(FileHeaderST)

            RecordType = doc.createElement('RecordType')
            RecordType.appendChild(doc.createTextNode('0'))
            FileHeaderST.appendChild(RecordType)

            Source = doc.createElement('Source')
            if context.get('datas') and context.get('datas')['source']:
                Source.appendChild(doc.createTextNode(context.get('datas'
                                                                  )['source']))
            FileHeaderST.appendChild(Source)

            BasisYear = doc.createElement('BasisYear')
            if basis_year:
                BasisYear.appendChild(doc.createTextNode(str(basis_year)))
            FileHeaderST.appendChild(BasisYear)

            OrganizationID = doc.createElement('OrganizationID')
            if organization_id_type:
                OrganizationID.appendChild(doc.createTextNode(
                    str(organization_id_type)))
            FileHeaderST.appendChild(OrganizationID)

            OrganizationIDNo = doc.createElement('OrganizationIDNo')
            if organization_id_no:
                OrganizationIDNo.appendChild(doc.createTextNode(
                    organization_id_no))
            FileHeaderST.appendChild(OrganizationIDNo)

            AuthorisedPersonName = doc.createElement('AuthorisedPersonName')
            if payroll_admin_user_name:
                AuthorisedPersonName.appendChild(doc.createTextNode(
                    str(payroll_admin_user_name)))
            FileHeaderST.appendChild(AuthorisedPersonName)

            AuthorisedPersonDesignation = doc.createElement(
                'AuthorisedPersonDesignation')
            if emp_designation:
                AuthorisedPersonDesignation.appendChild(doc.createTextNode(
                    str(emp_designation)))
            FileHeaderST.appendChild(AuthorisedPersonDesignation)

            EmployerName = doc.createElement('EmployerName')
            if company_name:
                EmployerName.appendChild(doc.createTextNode(str(company_name)))
            FileHeaderST.appendChild(EmployerName)

            Telephone = doc.createElement('Telephone')
            if emp_contact:
                Telephone.appendChild(doc.createTextNode(str(emp_contact)))
            FileHeaderST.appendChild(Telephone)

            aut_email = doc.createElement('AuthorisedPersonEmail')
            if emp_email:
                aut_email.appendChild(doc.createTextNode(str(emp_email)))
            FileHeaderST.appendChild(aut_email)

            BatchIndicator = doc.createElement('BatchIndicator')
            if context.get('datas') and context.get('datas'
                                                    )['batch_indicatior']:
                BatchIndicator.appendChild(doc.createTextNode(
                    str(context.get('datas')['batch_indicatior'])))
            FileHeaderST.appendChild(BatchIndicator)

            BatchDate = doc.createElement('BatchDate')
            if batchdate:
                BatchDate.appendChild(doc.createTextNode(str(batchdate)))
            FileHeaderST.appendChild(BatchDate)

            DivisionOrBranchName = doc.createElement('DivisionOrBranchName')
            FileHeaderST.appendChild(DivisionOrBranchName)

            Details = doc.createElement('Details')
            root.appendChild(Details)

            """ get the contract for selected employee"""
            contract_ids = contract_obj.search([
                ('employee_id', 'in', context.get('employe_id'))])
            from_date = to_date = ''

            for contract in contract_ids:
                contract_income_tax_ids = incometax_obj.search([
                    ('contract_id', '=', contract.id),
                    ('start_date', '>=', start_date_year),
                    ('end_date', '<=', end_date_year)])
                if not contract.employee_id.identification_id:
                    raise ValidationError(
                        _("There is no identification no define for %s "
                          "employee." % (contract.employee_id.name)))
                if contract_income_tax_ids and contract_income_tax_ids.ids:
                    for emp in contract_income_tax_ids[0]:
                        if emp.from_date:
                            from_date = emp.from_date.strftime('%Y%m%d')
                        if emp.to_date:
                            to_date = emp.to_date.strftime('%Y%m%d')

                        """ string variable declaration"""
                        annual_value = rent_landloard = 0
                        place_of_residence_taxable_value = total_rent_paid = 0
                        utilities_misc_value = driver_value = car_benefits = ''
                        employer_paid_amount = non_monetary_benefits = ''
                        taxalble_value_of_utilities_housekeeping = ''
                        actual_hotel_accommodation = employee_paid_amount = ''
                        taxable_value_of_hotel_acco = non_monetary_awards = ''
                        cost_of_home_leave_benefits = interest_payment = ''
                        insurance_payment = free_holidays = edu_expenses = ''
                        gains_from_assets = cost_of_motor = entrance_fees = ''
                        furniture_value = total_taxable_value = ''

                        annual_value = abs(emp.annual_value)
                        """Must be blank if item annual_value(6a) is not
                        blank or > zero """
                        if annual_value != '' or emp.annual_value > 0:
                            rent_landloard = ''
                        else:
                            rent_landloard = int(abs(emp.rent_landloard))
                        line11 = line22 = line33 = ''
                        if int(emp.annual_value) > 0 or emp.rent_landloard > 0:
                            if not emp.address:
                                raise ValidationError(
                                    _("There is no address define for %s "
                                      "employee." % (contract.employee_id.name
                                                     )))
                            if emp.address:
                                emp_address = str(emp.address)
                                demo_lst = list(emp_address)
                                line1 = []
                                line2 = []
                                line3 = []
                                indexes = [i for i, x in enumerate(
                                    demo_lst) if x == '\n']
                                if len(indexes) == 1:
                                    for lst in range(0, indexes[0]):
                                        line1.append(demo_lst[lst])
                                    for lst1 in range(int(indexes[0]) + 1,
                                                      len(demo_lst)):
                                        line2.append(demo_lst[lst1])
                                elif len(indexes) == 2:
                                    for lst in range(0, indexes[0]):
                                        line1.append(demo_lst[lst])
                                    for lst1 in range(int(indexes[0]) + 1,
                                                      int(indexes[1])):
                                        line2.append(demo_lst[lst1])
                                    for lst2 in range(int(indexes[1]) + 1,
                                                      len(demo_lst)):
                                        line3.append(demo_lst[lst2])
                                line11 = ''.join(line1)
                                line22 = ''.join(line2)
                                line33 = ''.join(line3)
                        """ Cannot be blank when Value of Furniture & Fitting
                        indicator is not blank."""
                        if emp.furniture_value_indicator:
                            if int(emp.furniture_value) < 0:
                                raise UserError(
                                    _("Cannot be blank or zero when Value of "
                                      "Furniture & Fitting indicator is "
                                      "not blank."))
                            else:
                                furniture_value = abs(emp.furniture_value)

                        """No of employee cannot be blank when annual value
                        or  rent paid to landlord is not blank or not zero"""
                        no_of_emp = 0
                        if (emp.annual_value) > 0 or (emp.rent_landloard) > 0:
                            if (emp.no_of_emp) == 0:
                                raise UserError(
                                    _("No of employee can not be zero or "
                                      "blank when annual value or rent paid "
                                      "to landlord is not blank"))
                            else:
                                no_of_emp = int(emp.no_of_emp)

                        """ If not blank, must be Y or N."""
                        cost_of_home_leave_benefits = \
                            emp.cost_of_home_leave_benefits
                        place_of_residence_taxable_value = \
                            emp.place_of_residence_taxable_value
                        total_rent_paid = emp.total_rent_paid
                        utilities_misc_value = emp.utilities_misc_value
                        driver_value = emp.driver_value
                        employer_paid_amount = emp.employer_paid_amount
                        taxalble_value_of_utilities_housekeeping = \
                            emp.taxalble_value_of_utilities_housekeeping
                        actual_hotel_accommodation = \
                            emp.actual_hotel_accommodation
                        employee_paid_amount = emp.employee_paid_amount
                        taxable_value_of_hotel_acco = \
                            emp.taxable_value_of_hotel_acco
                        interest_payment = emp.interest_payment
                        insurance_payment = emp.insurance_payment
                        free_holidays = emp.free_holidays
                        edu_expenses = emp.edu_expenses
                        non_monetary_awards = emp.non_monetary_awards
                        entrance_fees = emp.entrance_fees
                        gains_from_assets = emp.gains_from_assets
                        cost_of_motor = emp.cost_of_motor
                        car_benefits = emp.car_benefits
                        non_monetary_benefits = emp.non_monetary_benefits
                        no_of_passanger = emp.no_of_passanger
                        spouse = emp.spouse
                        children = emp.children

                        """ 6f = 6d – 6e"""
                        total_taxable_value = emp.total_taxable_value

                        """ Value must be the sum of item 6f, 6j,
                        7c, 8a to 8k."""
                        total_value_of_benefits = emp.total_value_of_benefits

                        A8ARecord = doc.createElement('A8ARecord')
                        Details.appendChild(A8ARecord)

                        ESubmissionSDSC = doc.createElement('ESubmissionSDSC')
                        ESubmissionSDSC.setAttribute(
                            'xmlns', 'http://tempuri.org/ESubmissionSDSC.xsd')
                        A8ARecord.appendChild(ESubmissionSDSC)

                        record1 = doc.createElement('A8A2015ST')
                        ESubmissionSDSC.appendChild(record1)

                        RecordType = doc.createElement('RecordType')
                        RecordType.setAttribute('xmlns', root_url)
                        RecordType.appendChild(doc.createTextNode('1'))
                        record1.appendChild(RecordType)

                        IDType = doc.createElement('IDType')
                        IDType.setAttribute('xmlns', root_url)
                        if contract.employee_id.identification_no:
                            IDType.appendChild(doc.createTextNode(
                                str(contract.employee_id.identification_no)))
                        record1.appendChild(IDType)

                        IDNo = doc.createElement('IDNo')
                        IDNo.setAttribute('xmlns', root_url)
                        if contract.employee_id.identification_id:
                            IDNo.appendChild(doc.createTextNode(
                                str(contract.employee_id.identification_id)))
                        record1.appendChild(IDNo)

                        NameLine1 = doc.createElement('NameLine1')
                        NameLine1.setAttribute('xmlns', root_url)
                        if contract.employee_id.name:
                            NameLine1.appendChild(doc.createTextNode(
                                str(contract.employee_id.name)))
                        record1.appendChild(NameLine1)

                        NameLine2 = doc.createElement('NameLine2')
                        NameLine2.setAttribute('xmlns', root_url)
                        record1.appendChild(NameLine2)

                        ResidenceAddressLine1 = doc.createElement(
                            'ResidenceAddressLine1')
                        ResidenceAddressLine1.setAttribute('xmlns', root_url)
                        if line11:
                            ResidenceAddressLine1.appendChild(
                                doc.createTextNode(str(line11)))
                        record1.appendChild(ResidenceAddressLine1)

                        ResidenceAddressLine2 = doc.createElement(
                            'ResidenceAddressLine2')
                        ResidenceAddressLine2.setAttribute('xmlns', root_url)
                        if line22:
                            ResidenceAddressLine2.appendChild(
                                doc.createTextNode(str(line22)))
                        record1.appendChild(ResidenceAddressLine2)

                        ResidenceAddressLine3 = doc.createElement(
                            'ResidenceAddressLine3')
                        ResidenceAddressLine3.setAttribute('xmlns', root_url)
                        if line33:
                            ResidenceAddressLine3.appendChild(
                                doc.createTextNode(str(line33)))
                        record1.appendChild(ResidenceAddressLine3)

                        OccupationFromDate = doc.createElement(
                            'OccupationFromDate')
                        OccupationFromDate.setAttribute('xmlns', root_url)
                        if from_date:
                            OccupationFromDate.appendChild(
                                doc.createTextNode(str(from_date)))
                        record1.appendChild(OccupationFromDate)

                        OccupationToDate = doc.createElement(
                            'OccupationToDate')
                        OccupationToDate.setAttribute('xmlns', root_url)
                        if to_date:
                            OccupationToDate.appendChild(
                                doc.createTextNode(str(to_date)))
                        record1.appendChild(OccupationToDate)

                        NoOfDays = doc.createElement('NoOfDays')
                        NoOfDays.setAttribute('xmlns', root_url)
                        if emp.no_of_days:
                            NoOfDays.appendChild(doc.createTextNode(
                                str(emp.no_of_days)))
                        record1.appendChild(NoOfDays)

                        NoOfEmployeeSharePremises = doc.createElement(
                            'NoOfEmployeeSharePremises')
                        NoOfEmployeeSharePremises.setAttribute(
                            'xmlns', root_url)
                        if no_of_emp:
                            NoOfEmployeeSharePremises.appendChild(
                                doc.createTextNode(str(no_of_emp)))
                        record1.appendChild(NoOfEmployeeSharePremises)

                        AVOfPremises = doc.createElement('AVOfPremises')
                        AVOfPremises.setAttribute('xmlns', root_url)
                        if annual_value and int(annual_value) != 0:
                            AVOfPremises.appendChild(
                                doc.createTextNode(str(annual_value)))
                        record1.appendChild(AVOfPremises)

                        ValueFurnitureFittingInd = doc.createElement(
                            'ValueFurnitureFittingInd')
                        ValueFurnitureFittingInd.setAttribute(
                            'xmlns', root_url)
                        if emp.furniture_value_indicator:
                            ValueFurnitureFittingInd.appendChild(
                                doc.createTextNode(
                                    str(emp.furniture_value_indicator)))
                        record1.appendChild(ValueFurnitureFittingInd)

                        ValueFurnitureFitting = doc.createElement(
                            'ValueFurnitureFitting')
                        ValueFurnitureFitting.setAttribute('xmlns', root_url)
                        if furniture_value:
                            ValueFurnitureFitting.appendChild(
                                doc.createTextNode(str(furniture_value)))
                        record1.appendChild(ValueFurnitureFitting)

                        RentPaidToLandlord = doc.createElement(
                            'RentPaidToLandlord')
                        RentPaidToLandlord.setAttribute('xmlns', root_url)
                        if rent_landloard:
                            RentPaidToLandlord.appendChild(
                                doc.createTextNode(str(rent_landloard)))
                        record1.appendChild(RentPaidToLandlord)

                        TaxableValuePlaceOfResidence = doc.createElement(
                            'TaxableValuePlaceOfResidence')
                        TaxableValuePlaceOfResidence.setAttribute(
                            'xmlns', root_url)
                        if place_of_residence_taxable_value and int(
                                place_of_residence_taxable_value) != 0:
                            TaxableValuePlaceOfResidence.appendChild(
                                doc.createTextNode(
                                    str(place_of_residence_taxable_value)))
                        record1.appendChild(TaxableValuePlaceOfResidence)

                        TotalRentPaidByEmprPlaceOfRcy = doc.createElement(
                            'TotalRentPaidByEmployeePlaceOfResidence')
                        TotalRentPaidByEmprPlaceOfRcy.setAttribute(
                            'xmlns', root_url)
                        if total_rent_paid and int(total_rent_paid) != 0:
                            TotalRentPaidByEmprPlaceOfRcy.appendChild(
                                doc.createTextNode(str(total_rent_paid)))
                        record1.appendChild(TotalRentPaidByEmprPlaceOfRcy)

                        TotalTaxableValuePlaceOfResidence = doc.createElement(
                            'TotalTaxableValuePlaceOfResidence')
                        TotalTaxableValuePlaceOfResidence.setAttribute(
                            'xmlns', root_url)
                        if total_taxable_value and int(total_taxable_value
                                                       ) != 0:
                            TotalTaxableValuePlaceOfResidence.appendChild(
                                doc.createTextNode(str(total_taxable_value)))
                        record1.appendChild(TotalTaxableValuePlaceOfResidence)

                        UtilitiesTelPagerAcsry = doc.createElement(
                            'UtilitiesTelPagerSuitCaseAccessories')
                        UtilitiesTelPagerAcsry.setAttribute(
                            'xmlns', root_url)
                        if utilities_misc_value and int(utilities_misc_value
                                                        ) != 0:
                            UtilitiesTelPagerAcsry.appendChild(
                                doc.createTextNode(str(utilities_misc_value)))
                        record1.appendChild(
                            UtilitiesTelPagerAcsry)

                        Driver = doc.createElement('Driver')
                        Driver.setAttribute('xmlns', root_url)
                        if driver_value and int(driver_value) != 0:
                            Driver.appendChild(doc.createTextNode(
                                str(driver_value)))
                        record1.appendChild(Driver)

                        ServantGardener = doc.createElement('ServantGardener')
                        ServantGardener.setAttribute('xmlns', root_url)
                        if employer_paid_amount and int(employer_paid_amount
                                                        ) != 0:
                            ServantGardener.appendChild(
                                doc.createTextNode(str(employer_paid_amount)))
                        record1.appendChild(ServantGardener)

                        TaxableValueUtilitiesHouseKeeping = doc.createElement(
                            'TaxableValueUtilitiesHouseKeeping')
                        TaxableValueUtilitiesHouseKeeping.setAttribute(
                            'xmlns', root_url)
                        if taxalble_value_of_utilities_housekeeping and \
                                int(taxalble_value_of_utilities_housekeeping
                                    ) != 0:
                            TaxableValueUtilitiesHouseKeeping.appendChild(
                                doc.createTextNode(str(
                                    taxalble_value_of_utilities_housekeeping)))
                        record1.appendChild(TaxableValueUtilitiesHouseKeeping)

                        ActualHotelAccommodation = doc.createElement(
                            'ActualHotelAccommodation')
                        ActualHotelAccommodation.setAttribute(
                            'xmlns', root_url)
                        if actual_hotel_accommodation and int(
                                actual_hotel_accommodation) != 0:
                            ActualHotelAccommodation.appendChild(
                                doc.createTextNode(
                                    str(actual_hotel_accommodation)))
                        record1.appendChild(ActualHotelAccommodation)

                        AmountPaidByEmployee = doc.createElement(
                            'AmountPaidByEmployee')
                        AmountPaidByEmployee.setAttribute('xmlns', root_url)
                        if employee_paid_amount and int(employee_paid_amount
                                                        ) != 0:
                            AmountPaidByEmployee.appendChild(
                                doc.createTextNode(str(employee_paid_amount)))
                        record1.appendChild(AmountPaidByEmployee)

                        TaxableValueHotelAccommodation = doc.createElement(
                            'TaxableValueHotelAccommodation')
                        TaxableValueHotelAccommodation.setAttribute(
                            'xmlns', root_url)
                        if taxable_value_of_hotel_acco and int(
                                taxable_value_of_hotel_acco) != 0:
                            TaxableValueHotelAccommodation.appendChild(
                                doc.createTextNode(
                                    str(taxable_value_of_hotel_acco)))
                        record1.appendChild(TaxableValueHotelAccommodation)

                        CostOfLeavePsgAndIncidentalBfts = doc.createElement(
                            'CostOfLeavePassageAndIncidentalBenefits')
                        CostOfLeavePsgAndIncidentalBfts.setAttribute(
                            'xmlns', root_url)
                        if cost_of_home_leave_benefits and int(
                                cost_of_home_leave_benefits) != 0:
                            CostOfLeavePsgAndIncidentalBfts.appendChild(
                                doc.createTextNode(
                                    str(cost_of_home_leave_benefits)))
                        record1.appendChild(CostOfLeavePsgAndIncidentalBfts)

                        NoOfLeavePassageSelf = doc.createElement(
                            'NoOfLeavePassageSelf')
                        NoOfLeavePassageSelf.setAttribute('xmlns', root_url)
                        record1.appendChild(NoOfLeavePassageSelf)

                        NoOfLeavePassageSpouse = doc.createElement(
                            'NoOfLeavePassageSpouse')
                        NoOfLeavePassageSpouse.setAttribute('xmlns', root_url)
                        record1.appendChild(NoOfLeavePassageSpouse)

                        NoOfLeavePassageChildren = doc.createElement(
                            'NoOfLeavePassageChildren')
                        NoOfLeavePassageChildren.setAttribute(
                            'xmlns', root_url)
                        record1.appendChild(NoOfLeavePassageChildren)

                        OHQStatus = doc.createElement('OHQStatus')
                        OHQStatus.setAttribute('xmlns', root_url)
                        record1.appendChild(OHQStatus)

                        InterestPaidByEmployer = doc.createElement(
                            'InterestPaidByEmployer')
                        InterestPaidByEmployer.setAttribute('xmlns', root_url)
                        if interest_payment and int(interest_payment) != 0:
                            InterestPaidByEmployer.appendChild(
                                doc.createTextNode(str(interest_payment)))
                        record1.appendChild(InterestPaidByEmployer)

                        LifeInsurPremiumsPaidByEmpr = doc.createElement(
                            'LifeInsurancePremiumsPaidByEmployer')
                        LifeInsurPremiumsPaidByEmpr.setAttribute(
                            'xmlns', root_url)
                        if insurance_payment and int(insurance_payment) != 0:
                            LifeInsurPremiumsPaidByEmpr.appendChild(
                                doc.createTextNode(str(insurance_payment)))
                        record1.appendChild(LifeInsurPremiumsPaidByEmpr)

                        FreeOrSubsidisedHoliday = doc.createElement(
                            'FreeOrSubsidisedHoliday')
                        FreeOrSubsidisedHoliday.setAttribute('xmlns', root_url)
                        if free_holidays and int(free_holidays) != 0:
                            FreeOrSubsidisedHoliday.appendChild(
                                doc.createTextNode(str(free_holidays)))
                        record1.appendChild(FreeOrSubsidisedHoliday)

                        EducationalExpenses = doc.createElement(
                            'EducationalExpenses')
                        EducationalExpenses.setAttribute('xmlns', root_url)
                        if edu_expenses and int(edu_expenses):
                            EducationalExpenses.appendChild(
                                doc.createTextNode(str(edu_expenses)))
                        record1.appendChild(EducationalExpenses)

                        NonMonetaryAwardsForLongService = doc.createElement(
                            'NonMonetaryAwardsForLongService')
                        NonMonetaryAwardsForLongService.setAttribute(
                            'xmlns', root_url)
                        if non_monetary_awards and int(non_monetary_awards
                                                       ) != 0:
                            NonMonetaryAwardsForLongService.appendChild(
                                doc.createTextNode(str(non_monetary_awards)))
                        record1.appendChild(NonMonetaryAwardsForLongService)

                        EntranceOrTransFeesToSclclubs = doc.createElement(
                            'EntranceOrTransferFeesToSocialClubs')
                        EntranceOrTransFeesToSclclubs.setAttribute(
                            'xmlns', root_url)
                        if entrance_fees and int(entrance_fees) != 0:
                            EntranceOrTransFeesToSclclubs.appendChild(
                                doc.createTextNode(str(entrance_fees)))
                        record1.appendChild(EntranceOrTransFeesToSclclubs)

                        GainsFromAssets = doc.createElement('GainsFromAssets')
                        GainsFromAssets.setAttribute('xmlns', root_url)
                        if gains_from_assets and int(gains_from_assets) != 0:
                            GainsFromAssets.appendChild(
                                doc.createTextNode(str(gains_from_assets)))
                        record1.appendChild(GainsFromAssets)

                        FullCostOfMotorVehicle = doc.createElement(
                            'FullCostOfMotorVehicle')
                        FullCostOfMotorVehicle.setAttribute('xmlns', root_url)
                        if cost_of_motor and int(cost_of_motor) != 0:
                            FullCostOfMotorVehicle.appendChild(
                                doc.createTextNode(str(cost_of_motor)))
                        record1.appendChild(FullCostOfMotorVehicle)

                        CarBenefit = doc.createElement('CarBenefit')
                        CarBenefit.setAttribute('xmlns', root_url)
                        if car_benefits and int(car_benefits) != 0:
                            CarBenefit.appendChild(doc.createTextNode(
                                str(car_benefits)))
                        record1.appendChild(CarBenefit)

                        OthersBenefits = doc.createElement('OthersBenefits')
                        OthersBenefits.setAttribute('xmlns', root_url)
                        record1.appendChild(OthersBenefits)

                        TotalBenefitsInKind = doc.createElement(
                            'TotalBenefitsInKind')
                        TotalBenefitsInKind.setAttribute('xmlns', root_url)
                        if total_value_of_benefits and int(
                                total_value_of_benefits) != 0:
                            TotalBenefitsInKind.appendChild(
                                doc.createTextNode(
                                    str(total_value_of_benefits)))
                        record1.appendChild(TotalBenefitsInKind)

                        Filler = doc.createElement('Filler')
                        Filler.setAttribute('xmlns', root_url)
                        record1.appendChild(Filler)

                        FieldReserved = doc.createElement('FieldReserved')
                        FieldReserved.setAttribute('xmlns', root_url)
                        record1.appendChild(FieldReserved)

            result = doc.toprettyxml(indent='   ')
            res = base64.b64encode(result.encode('UTF-8'))
            module_rec = self.env['binary.appendix8a.xml.file.wizard'
                                  ].create({'name': 'appendix8a.xml',
                                            'appendix8a_xml_file': res})
            return {
              'name': _('Binary'),
              'res_id': module_rec.id,
              "view_mode": 'form',
              'res_model': 'binary.appendix8a.xml.file.wizard',
              'type': 'ir.actions.act_window',
              'target': 'new',
              'context': context,
            }
        elif data.get('print_type', '') == 'pdf':
            report_id = self.env.ref(
                'sg_appendix8a_report.hrms_appendix8a_form')
            return report_id.report_action(self, data=data, config=False)


class BinaryAppendix8aTextFileWizard(models.TransientModel):
    _name = 'binary.appendix8a.text.file.wizard'
    _description = "Appendix 8a Text Wizard"

    name = fields.Char('Name', default='appendix8a.txt')
    appendix8a_txt_file = fields.Binary(
        'Click On Download Link To Download File', readonly=True)


class BinaryAppendix8aXMLFileWizard(models.TransientModel):
    _name = 'binary.appendix8a.xml.file.wizard'
    _description = "Appendix 8a xml wizard"

    name = fields.Char('Name', default='appendix8a.xml')
    appendix8a_xml_file = fields.Binary(
        'Click On Download Link To Download File', readonly=True)
