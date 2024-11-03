import time
import base64
import tempfile
from xml.dom import minidom
from datetime import datetime
from odoo.tools.misc import get_lang

from odoo import tools
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF


class EmpAppendix8bTextFile(models.TransientModel):
    _name = 'emp.appendix8b.text.file'
    _description = "Appendix 8b Text"

    def _get_payroll_user_name(self):
        supervisors_list = [(False, '')]
        group_data = self.env.ref('l10n_sg_hr_payroll.group_hr_payroll_admin')
        for user in group_data.users:
            supervisors_list.append((tools.ustr(user.id),
                                     tools.ustr(user.name)))
        return supervisors_list

    employee_ids = fields.Many2many('hr.employee',
                                    'hr_employe_appendix8b_text_rel',
                                    'empl_id', 'employee_id', 'Employee',
                                    required=True)
    start_date = fields.Date('Start Date', required=True,
                             default=lambda *a: time.strftime('%Y-01-01'))
    end_date = fields.Date('End Date', required=True,
                           default=lambda *a: time.strftime('%Y-12-31'))
    source = fields.Selection([('6', 'Private Sector'), ('9', 'Others')],
                              string='Source', default='6')
    batch_indicatior = fields.Selection([('O', 'Original'),
                                         ('A', 'Amendment')],
                                        string='Batch Indicator')
    batch_date = fields.Date('Batch Date')
    payroll_user = fields.Selection(_get_payroll_user_name,
                                    'Name of authorised person')
    print_type = fields.Selection([('pdf', 'PDF'), ('text', 'Text'),
                                   ('xml', 'XML')], default='pdf',
                                  string='Print as')
    incorporation_date = fields.Date("Date of incorporation")

    def print_report(self):
        ResUsersObj = self.env['res.users']
        HrEmployeeObj = self.env['hr.employee']
        incometax_brw = self.env['hr.contract.income.tax']
        data = self.read([])[0]
        user_rec = self.env.user

        if data.get('employee_ids') == []:
            raise ValidationError(_("Please select employee"))
        else:
            data = self.read([])[0]
            start_year = data.get('start_date', False).strftime('%Y')
            to_year = data.get('end_date', False).strftime('%Y')
            start_date = '%s-01-01' % tools.ustr(int(start_year) - 1)
            end_date = '%s-12-31' % tools.ustr(int(to_year) - 1)
            start_date_year = '%s-01-01' % tools.ustr(int(start_year))
            end_date_year = '%s-12-31' % tools.ustr(int(to_year))
            if 'start_date' in data and 'end_date' in data and \
                    data.get('start_date', False) >= data.get('end_date',
                                                              False):
                raise ValidationError(
                    _("You must enter start date less than end date !"))

            emp_ids = data.get('employee_ids') or []
            if emp_ids and emp_ids is not False:
                hr_contract_obj = self.env['hr.contract']
                hr_payslip_obj = self.env['hr.payslip']
                for employee in HrEmployeeObj.browse(emp_ids):
                    emp_name = employee and employee.name or ''
                    emp_id = employee and employee.id or False

                    contract_ids = hr_contract_obj.search(
                        [('employee_id', '=', emp_id)])
                    contract_income_tax_ids = incometax_brw.search([
                        ('contract_id', 'in', contract_ids.ids),
                        ('start_date', '>=', self.start_date),
                        ('end_date', '<=', self.end_date)
                        ])
                    if not contract_income_tax_ids.ids:
                        raise ValidationError(
                            _("There is no Income tax details available "
                              "between selected date %s and %s for the "
                              "%s employee for contract." % (
                                self.start_date.strftime(
                                    get_lang(self.env).date_format),
                                self.end_date.strftime(
                                    get_lang(self.env).date_format), emp_name)))
                    payslip_ids = hr_payslip_obj.search([
                        ('date_from', '>=', self.start_date),
                        ('date_from', '<=', self.end_date),
                        ('state', 'in', ['draft', 'done', 'verify'])
                        ])
                    if not payslip_ids.ids:
                        raise ValidationError(
                            _("There is no payslip details available between "
                              "selected date %s and %s for the %s "
                              "employee." % (
                                self.start_date.strftime(
                                    get_lang(self.env).date_format),
                                self.end_date.strftime(
                                    get_lang(self.env).date_format), emp_name)))
            if data['print_type'] == 'pdf':
                report_id = self.env.ref(
                    'sg_appendix8b_report.hrms_appendix8b_form')
                return report_id.report_action(self, data=data, config=False)
            elif data['print_type'] == 'text':
                context = dict(self._context) or {}
                context.update({'employe_id': data['employee_ids'],
                                'datas': data})
                tgz_tmp_filename = tempfile.mktemp('.' + "txt")
                tmp_file = False
                start_date = end_date = False
                from_date = context.get('datas', False).get(
                    'start_date', False) or False
                to_date = context.get('datas', False).get('end_date', False
                                                          ) or False
                if from_date and to_date:
                    basis_year = tools.ustr(from_date.year - 1)
                    start_date = '%s-01-01' % tools.ustr(int(
                        from_date.year) - 1)
                    end_date = '%s-12-31' % tools.ustr(int(from_date.year) - 1)
                    start_date = datetime.strptime(start_date, DSDF)
                    end_date = datetime.strptime(end_date, DSDF)
                try:
                    tmp_file = open(tgz_tmp_filename, "w")
                    batchdate = context.get('datas')['batch_date'].strftime(
                        '%Y%m%d')
                    incorporation_date = ''
                    if context.get('datas')['incorporation_date']:
                        incorporation_date = context.get('datas')[
                                'incorporation_date'].strftime('%Y%m%d')
                    emp_rec = HrEmployeeObj.search([
                        ('user_id', '=', int(context.get('datas')
                                             ['payroll_user']))], limit=1)
                    emp_designation = ''
                    user_brw = ResUsersObj.browse(int(context.get('datas')
                                                      ['payroll_user']))
                    payroll_admin_user_name = user_brw.name
                    company_name = user_brw.company_id.name
                    organization_id_type = user_rec.company_id and \
                        user_rec.company_id.organization_id_type or ''
                    organization_id_no = user_rec.company_id and \
                        user_rec.company_id.organization_id_no or ''
                    if emp_rec and emp_rec.id:
                        emp_designation = emp_rec.job_id.name
                        emp_email = emp_rec.work_email
                        emp_contact = emp_rec.work_phone
                    """ Header for Appendix8B """
                    header_record = '0'.ljust(1) + tools.ustr(
                        context.get('datas')['source'] or '').ljust(1) + \
                        tools.ustr(basis_year or '').ljust(4) + \
                        tools.ustr('13').ljust(2) + \
                        tools.ustr(organization_id_type or '').ljust(1) + \
                        tools.ustr(organization_id_no or '').ljust(12) + \
                        tools.ustr(payroll_admin_user_name or ''
                                   )[:30].ljust(30) + \
                        tools.ustr(emp_designation or '')[:30].ljust(30) + \
                        tools.ustr(company_name)[:60].ljust(60) + \
                        tools.ustr(emp_contact)[:20].ljust(20) + \
                        tools.ustr(emp_email)[:60].ljust(60) + \
                        tools.ustr(context.get('datas')[
                            'batch_indicatior'] or '').ljust(1) + \
                        tools.ustr(batchdate).ljust(8) + \
                        tools.ustr(incorporation_date).ljust(8) + \
                        ''.ljust(30) + ''.ljust(10) + ''.ljust(9022) + "\r\n"
                    tmp_file.write(header_record)
                    """ get the contract for selected employee"""
                    employee_ids = data['employee_ids']
                    employee_ids = HrEmployeeObj.browse(employee_ids)
                    total_detail_record = 0
                    total_gross_amt_qulfy_secA_s10_b = 0.0
                    total_gorss_amt_gain_secA_s10_b = 0.0
                    total_gross_amt_qulfy_secA_s10_g = 0.0
                    total_gorss_amt_gain_secA_s10_g = 0.0

                    total_eris_smes_secB_s10_b = 0.0
                    total_eris_smes_secB_s10_g = 0.0
                    total_gross_amt_qulfy_secB_s10_b = 0.0
                    total_gorss_amt_gain_secB_s10_g = 0.0
                    total_gorss_amt_gain_secB_s10_b = 0.0
                    total_gross_amt_qulfy_secB_s10_g = 0.0

                    total_eris_all_corporation_secC_s10_b = 0.0
                    total_eris_all_corporation_secC_s10_g = 0.0
                    total_gross_amt_qulfy_secC_s10_b = 0.0
                    total_gross_amt_qulfy_secC_s10_g = 0.0
                    total_gorss_amt_gain_secC_s10_b = 0.0
                    total_gorss_amt_gain_secC_s10_g = 0.0

                    total_eris_start_ups_secD_s10_b = 0.0
                    total_eris_start_ups_secD_s10_g = 0.0
                    total_gross_amt_qulfy_secD_s10_b = 0.0
                    total_gross_amt_qulfy_secD_s10_g = 0.0
                    total_gorss_amt_gain_secD_s10_b = 0.0
                    total_gorss_amt_gain_secD_s10_g = 0.0

                    total_grand_total_secE_gross_amt_qulfy_s10_b = 0.0
                    total_grand_total_secE_gross_amt_qulfy_s10_g = 0.0
                    total_grand_total_secE_gorss_amt_gain_s10_b = 0.0
                    total_grand_total_secE_gorss_amt_gain_s10_g = 0.0

                    for employee in employee_ids:
                        total_detail_record += 1
                        if not employee.identification_id:
                            raise ValidationError(
                                _("There is no identification no define "
                                  "for %s employee." % (employee.name)))
                        if not employee.empnationality_id:
                            raise ValidationError(
                                _("There is no Nationality code define "
                                  "for %s employee." % (employee.name)))
                        birth_date = employee.birthday.strftime('%Y%m%d')
                        if employee.gender == 'male':
                            gender = 'M'
                        else:
                            gender = 'F'
                        contract_income_tax_ids = incometax_brw.search(
                            [('contract_id.employee_id', '=', employee.id),
                             ('start_date', '>=', start_date_year),
                             ('end_date', '<=', end_date_year)])
                        detail_record = ''
                        detail_record += '1'.ljust(1)
                        detail_record += tools.ustr(employee.identification_no
                                                    or '').ljust(1)
                        detail_record += tools.ustr(employee.identification_id
                                                    or '')[:12].ljust(12)
                        detail_record += tools.ustr(employee.name or ''
                                                    )[:40].ljust(40)
                        detail_record += ''.ljust(40)
                        detail_record += tools.ustr(
                            employee.empnationality_id.code).ljust(3)
                        detail_record += tools.ustr(gender).ljust(1)
                        detail_record += tools.ustr(birth_date).ljust(8)

                        gross_amt_qulfy_secA_s10_b = 0.0
                        gorss_amt_gain_secA_s10_b = 0.0
                        gross_amt_qulfy_secA_s10_g = 0.0
                        gorss_amt_gain_secA_s10_g = 0.0

                        gross_amt_qulfy_secB_s10_b = 0.0
                        gross_amt_qulfy_secB_s10_g = 0.0
                        gorss_amt_gain_secB_s10_b = 0.0
                        gorss_amt_gain_secB_s10_g = 0.0
                        eris_smes_secB_s10_b = 0.0
                        eris_smes_secB_s10_g = 0.0

                        gross_amt_qulfy_secC_s10_b = 0.0
                        gorss_amt_gain_secC_s10_b = 0.0
                        eris_all_corporation_secC_s10_b = 0.0
                        gross_amt_qulfy_secC_s10_g = 0.0
                        gorss_amt_gain_secC_s10_g = 0.0
                        eris_all_corporation_secC_s10_g = 0.0

                        eris_start_ups_secD_s10_b = 0.0
                        eris_start_ups_secD_s10_g = 0.0
                        gross_amt_qulfy_secD_s10_b = 0.0
                        gorss_amt_gain_secD_s10_b = 0.0
                        gross_amt_qulfy_secD_s10_g = 0.0
                        gorss_amt_gain_secD_s10_g = 0.0

                        grand_toatl_secE_eris_smes_s10_b = 0.0
                        grand_toatl_secE_eris_smes_s10_g = 0.0
                        grand_total_secE_eris_all_corporation_s10_b = 0.0
                        grand_total_secE_eris_all_corporation_s10_g = 0.0
                        grand_total_secE_eris_start_ups_s10_b = 0.0
                        grand_total_secE_eris_start_ups_s10_g = 0.0
                        grand_total_secE_gross_amt_qulfy_s10_b = 0.0
                        grand_total_secE_gross_amt_qulfy_s10_g = 0.0
                        grand_total_secE_gorss_amt_gain_s10_b = 0.0
                        grand_total_secE_gorss_amt_gain_s10_g = 0.0

                        detail_record_1 = ''
                        detail_record_2 = ''
                        detail_record_3 = ''
                        detail_record_4 = ''
                        detail_record_5 = ''

                        secA_len = 0
                        secB_len = 0
                        secC_len = 0
                        secD_len = 0
                        if (contract_income_tax_ids and
                                contract_income_tax_ids.ids):
                            for emp in contract_income_tax_ids[0]:
                                for line in emp.app_8b_income_tax:
                                    grant_date = ''
                                    if line.tax_plan_grant_date:
                                        grant_date = (
                                            line.tax_plan_grant_date.strftime(
                                                '%Y%m%d'))
                                    exercise_date = ''
                                    exercise_price = 0.00
                                    open_mrkt_val = 0.00
                                    open_mrkt_val_1 = 0.00
                                    if line.tax_plan == 'esop':
                                        exercise_price = line.ex_price_esop
                                        open_mrkt_val = line.open_val_esop
                                        if line.is_moratorium is True:
                                            open_mrkt_val_1 = (
                                                line.moratorium_price)
                                            if line.moratorium_date:
                                                exercise_date = (
                                                 line.moratorium_date.strftime(
                                                    '%Y%m%d'))
                                        else:
                                            open_mrkt_val_1 = (
                                                line.open_val_esop)
                                            if line.esop_date:
                                                exercise_date = (
                                                    line.esop_date.strftime(
                                                        '%Y%m%d'))
                                    elif line.tax_plan == 'esow':
                                        exercise_price = line.pay_under_esow
                                        open_mrkt_val = line.esow_plan
                                        if line.is_moratorium is True:
                                            open_mrkt_val_1 = (
                                                line.moratorium_price)
                                            if line.moratorium_date:
                                                exercise_date = (
                                                 line.moratorium_date.strftime(
                                                     '%Y%m%d'))
                                        else:
                                            open_mrkt_val_1 = line.esow_plan
                                            if line.esow_date:
                                                exercise_date = (
                                                    line.esow_date.strftime(
                                                        '%Y%m%d'))
                                    exercise_price = '%0*d' % (12, int(
                                        abs(exercise_price * 100000)))
                                    open_mrkt_val = '%0*d' % (12, int(
                                        abs(open_mrkt_val * 100000)))
                                    open_mrkt_val_1 = '%0*d' % (12, int(
                                        abs(open_mrkt_val_1 * 100000)))
                                    no_share = '%0*d' % (12, int(abs(
                                        line.no_of_share * 100000)))
                                    gross_amt_qulfy_secA = '%0*d' % (9, int(
                                        abs(line.secA_grss_amt_qulfy_tx * 100)
                                        ))
                                    gorss_amt_gain_secA = '%0*d' % (9, int(abs(
                                        line.secA_grss_amt_qulfy_tx * 100)))
                                    if line.section == 'sectionA':
                                        secA_len += 1
                                        detail_record_1 += tools.ustr(
                                                organization_id_type).ljust(1)
                                        detail_record_1 += tools.ustr(
                                                organization_id_no).ljust(12)
                                        detail_record_1 += tools.ustr(
                                                company_name).ljust(40)
                                        detail_record_1 += tools.ustr(
                                                line.tax_plan).ljust(4)
                                        detail_record_1 += tools.ustr(
                                                grant_date).ljust(8)
                                        detail_record_1 += tools.ustr(
                                                exercise_date).ljust(8)
                                        detail_record_1 += tools.ustr(
                                                exercise_price).ljust(12)
                                        detail_record_1 += tools.ustr(
                                                open_mrkt_val).ljust(12)
                                        detail_record_1 += tools.ustr(
                                                open_mrkt_val_1).ljust(12)
                                        detail_record_1 += tools.ustr(
                                                no_share).ljust(12)
                                        detail_record_1 += tools.ustr(
                                                gross_amt_qulfy_secA).ljust(9)
                                        detail_record_1 += tools.ustr(
                                                gorss_amt_gain_secA).ljust(9)
                                        if line.tax_plan == 'esow':
                                            gross_amt_qulfy_secA_s10_b += (
                                               line.secA_grss_amt_qulfy_tx)
                                            gorss_amt_gain_secA_s10_b += (
                                               line.secA_grss_amt_qulfy_tx)
                                        if line.tax_plan == 'esop':
                                            grant_date = line.tax_plan_grant_date.strftime('%Y/%m/%d')
                                            esop_appvl_date = '2003/01/01'
                                            if grant_date > esop_appvl_date:
                                                gross_amt_qulfy_secA_s10_b += \
                                                    line.secA_grss_amt_qulfy_tx
                                                gorss_amt_gain_secA_s10_b += \
                                                    line.secA_grss_amt_qulfy_tx
                                            elif grant_date < esop_appvl_date:
                                                gross_amt_qulfy_secA_s10_g += \
                                                    line.secA_grss_amt_qulfy_tx
                                                gorss_amt_gain_secA_s10_g += \
                                                    line.secA_grss_amt_qulfy_tx

                                    gross_amt_qulfy_secB = '%0*d' % (9, int(
                                        abs(line.secB_grss_amt_qulfy_tx * 100)
                                        ))
                                    gorss_amt_gain_secB = line.eris_smes + \
                                        line.secB_grss_amt_qulfy_tx
                                    gorss_amt_gain_secB = '%0*d' % (9, int(
                                        abs(gorss_amt_gain_secB * 100)))
                                    eris_smes = '%0*d' % (9, int(abs(
                                                        line.eris_smes * 100)))
                                    if line.section == 'sectionB':
                                        secB_len += 1
                                        detail_record_2 += tools.ustr(
                                                organization_id_type).ljust(1)
                                        detail_record_2 += tools.ustr(
                                                organization_id_no).ljust(12)
                                        detail_record_2 += tools.ustr(
                                                company_name).ljust(40)
                                        detail_record_2 += tools.ustr(
                                                line.tax_plan).ljust(4)
                                        detail_record_2 += tools.ustr(
                                                grant_date).ljust(8)
                                        detail_record_2 += tools.ustr(
                                                exercise_date).ljust(8)
                                        detail_record_2 += tools.ustr(
                                                exercise_price).ljust(12)
                                        detail_record_2 += tools.ustr(
                                                open_mrkt_val).ljust(12)
                                        detail_record_2 += tools.ustr(
                                                open_mrkt_val_1).ljust(12)
                                        detail_record_2 += tools.ustr(
                                                no_share).ljust(12)
                                        detail_record_2 += tools.ustr(
                                                eris_smes).ljust(9)
                                        detail_record_2 += tools.ustr(
                                                gross_amt_qulfy_secB).ljust(9)
                                        detail_record_2 += tools.ustr(
                                                gorss_amt_gain_secB).ljust(9)
                                        if line.tax_plan == 'esow':
                                            gross_amt_qulfy_secB_s10_b += \
                                                    line.secB_grss_amt_qulfy_tx
                                            gorss_amt_gain_secB_s10_b += (
                                                line.eris_smes +
                                                line.secB_grss_amt_qulfy_tx)
                                            eris_smes_secB_s10_b += (
                                                line.eris_smes)
                                        if line.tax_plan == 'esop':
                                            grant_date = line.tax_plan_grant_date.strftime('%Y/%m/%d')
                                            esop_appvl_date = '2003/01/01'
                                            if grant_date > esop_appvl_date:
                                                gross_amt_qulfy_secB_s10_b += \
                                                    line.secB_grss_amt_qulfy_tx
                                                gorss_amt_gain_secB_s10_b += \
                                                    line.eris_smes + \
                                                    line.secB_grss_amt_qulfy_tx
                                                eris_smes_secB_s10_b += \
                                                    line.eris_smes
                                            elif grant_date < esop_appvl_date:
                                                gross_amt_qulfy_secB_s10_g += \
                                                    line.secB_grss_amt_qulfy_tx
                                                gorss_amt_gain_secB_s10_g += \
                                                    line.eris_smes + \
                                                    line.secB_grss_amt_qulfy_tx
                                                eris_smes_secB_s10_g += \
                                                    line.eris_smes

                                    gross_amt_qulfy_secC = '%0*d' % (9, int(
                                        abs(line.secC_grss_amt_qulfy_tx * 100)
                                        ))
                                    gorss_amt_gain_secC = (
                                        line.eris_all_corporation +
                                        line.secC_grss_amt_qulfy_tx)
                                    gorss_amt_gain_secC = '%0*d' % (9, int(
                                        abs(gorss_amt_gain_secC * 100)))
                                    eris_all_corporation = '%0*d' % (9, int(
                                        abs(line.eris_all_corporation * 100)))
                                    if line.section == 'sectionC':
                                        secC_len += 1
                                        detail_record_3 += tools.ustr(
                                                organization_id_type).ljust(1)
                                        detail_record_3 += tools.ustr(
                                                organization_id_no).ljust(12)
                                        detail_record_3 += tools.ustr(
                                                company_name).ljust(40)
                                        detail_record_3 += tools.ustr(
                                                line.tax_plan).ljust(4)
                                        detail_record_3 += tools.ustr(
                                                grant_date).ljust(8)
                                        detail_record_3 += tools.ustr(
                                                exercise_date).ljust(8)
                                        detail_record_3 += tools.ustr(
                                                exercise_price).ljust(12)
                                        detail_record_3 += tools.ustr(
                                                open_mrkt_val).ljust(12)
                                        detail_record_3 += tools.ustr(
                                                open_mrkt_val_1).ljust(12)
                                        detail_record_3 += tools.ustr(
                                                no_share).ljust(12)
                                        detail_record_3 += tools.ustr(
                                                eris_all_corporation).ljust(9)
                                        detail_record_3 += tools.ustr(
                                                gross_amt_qulfy_secC).ljust(9)
                                        detail_record_3 += tools.ustr(
                                                gorss_amt_gain_secC).ljust(9)
                                        if line.tax_plan == 'esow':
                                            gross_amt_qulfy_secC_s10_b += \
                                                line.secC_grss_amt_qulfy_tx
                                            gorss_amt_gain_secC_s10_b += \
                                                line.eris_smes + \
                                                line.secC_grss_amt_qulfy_tx
                                            eris_all_corporation_secC_s10_b +=\
                                                line.eris_smes
                                        if line.tax_plan == 'esop':
                                            grant_date = line.tax_plan_grant_date
                                            grant_date = grant_date.strftime(
                                                '%Y/%m/%d')
                                            esop_appvl_date = '2003/01/01'
                                            if grant_date > esop_appvl_date:
                                                gross_amt_qulfy_secC_s10_b += \
                                                    line.secC_grss_amt_qulfy_tx
                                                gorss_amt_gain_secC_s10_b += \
                                                    line.eris_smes + \
                                                    line.secC_grss_amt_qulfy_tx
                                                eris_all_corporation_secC_s10_b\
                                                    += line.eris_smes
                                            elif grant_date < esop_appvl_date:
                                                gross_amt_qulfy_secC_s10_g += \
                                                    line.secC_grss_amt_qulfy_tx
                                                gorss_amt_gain_secC_s10_g += \
                                                    line.eris_smes + \
                                                    line.secC_grss_amt_qulfy_tx
                                                eris_all_corporation_secC_s10_g\
                                                    += line.eris_smes

                                    gross_amt_qulfy_secD = '%0*d' % (9, int(
                                        abs(line.secD_grss_amt_qulfy_tx * 100)
                                        ))
                                    gorss_amt_gain_secD = (
                                        line.eris_start_ups +
                                        line.secD_grss_amt_qulfy_tx)
                                    gorss_amt_gain_secD = '%0*d' % (9, int(
                                        abs(gorss_amt_gain_secD * 100)))
                                    eris_start_ups = '%0*d' % (9, int(abs(
                                        line.eris_start_ups * 100)))
                                    if line.section == 'sectionD':
                                        secD_len += 1
                                        detail_record_4 += tools.ustr(
                                                organization_id_type).ljust(1)
                                        detail_record_4 += tools.ustr(
                                                organization_id_no).ljust(12)
                                        detail_record_4 += tools.ustr(
                                                company_name).ljust(40)
                                        detail_record_4 += tools.ustr(
                                                line.tax_plan).ljust(4)
                                        detail_record_4 += tools.ustr(
                                                grant_date).ljust(8)
                                        detail_record_4 += tools.ustr(
                                                exercise_date).ljust(8)
                                        detail_record_4 += tools.ustr(
                                                exercise_price).ljust(12)
                                        detail_record_4 += tools.ustr(
                                                open_mrkt_val).ljust(12)
                                        detail_record_4 += tools.ustr(
                                                open_mrkt_val_1).ljust(12)
                                        detail_record_4 += tools.ustr(
                                                no_share).ljust(12)
                                        detail_record_4 += tools.ustr(
                                                eris_start_ups).ljust(9)
                                        detail_record_4 += tools.ustr(
                                                gross_amt_qulfy_secD).ljust(9)
                                        detail_record_4 += tools.ustr(
                                                gorss_amt_gain_secD).ljust(9)
                                        if line.tax_plan == 'esow':
                                            gross_amt_qulfy_secD_s10_b += \
                                                line.secD_grss_amt_qulfy_tx
                                            gorss_amt_gain_secD_s10_b += \
                                                line.eris_start_ups + \
                                                line.secD_grss_amt_qulfy_tx
                                            eris_start_ups_secD_s10_b += \
                                                line.eris_start_ups
                                        if line.tax_plan == 'esop':
                                            grant_date = \
                                                    line.tax_plan_grant_date
                                            grant_date = grant_date.strftime(
                                                '%Y/%m/%d')
                                            esop_appvl_date = '2003/01/01'
                                            if grant_date > esop_appvl_date:
                                                gross_amt_qulfy_secD_s10_b += \
                                                    line.secD_grss_amt_qulfy_tx
                                                gorss_amt_gain_secD_s10_b += \
                                                    line.eris_start_ups + \
                                                    line.secD_grss_amt_qulfy_tx
                                                eris_start_ups_secD_s10_b += \
                                                    line.eris_start_ups
                                            elif grant_date < esop_appvl_date:
                                                gross_amt_qulfy_secD_s10_g += \
                                                    line.secD_grss_amt_qulfy_tx
                                                gorss_amt_gain_secD_s10_g += (
                                                    line.eris_smes +
                                                    line.secC_grss_amt_qulfy_tx
                                                    )
                                                eris_start_ups_secD_s10_g += \
                                                    line.eris_start_ups

                                gross_amt_qulfy_secA_s10_b1 = '%0*d' % (
                                    10, int(abs(
                                        gross_amt_qulfy_secA_s10_b * 100)))
                                gross_amt_qulfy_secA_s10_g1 = '%0*d' % (
                                    10, int(abs(
                                        gross_amt_qulfy_secA_s10_g * 100)))
                                gorss_amt_gain_secA_s10_b1 = '%0*d' % (10, int(
                                    abs(gorss_amt_gain_secA_s10_b * 100)))
                                gorss_amt_gain_secA_s10_g1 = '%0*d' % (10, int(
                                    abs(gorss_amt_gain_secA_s10_g * 100)))

                                total_gross_amt_qulfy_secA_s10_b += (
                                            gross_amt_qulfy_secA_s10_b)
                                total_gorss_amt_gain_secA_s10_b += (
                                            gorss_amt_gain_secA_s10_b)
                                total_gross_amt_qulfy_secA_s10_g += (
                                            gross_amt_qulfy_secA_s10_g)
                                total_gorss_amt_gain_secA_s10_g += (
                                            gorss_amt_gain_secA_s10_g)

                                if secA_len < 15:
                                    length = 15 - secA_len
                                    length = length * 139
                                    detail_record_1 += tools.ustr('').ljust(
                                        length)
                                detail_record_1 += tools.ustr(
                                        gross_amt_qulfy_secA_s10_b1).ljust(10)
                                detail_record_1 += tools.ustr(
                                        gross_amt_qulfy_secA_s10_g1).ljust(10)
                                detail_record_1 += tools.ustr(
                                        gorss_amt_gain_secA_s10_b1).ljust(10)
                                detail_record_1 += tools.ustr(
                                        gorss_amt_gain_secA_s10_g1).ljust(10)

                                eris_smes_secB_s10_b1 = '%0*d' % (10, int(abs(
                                    eris_smes_secB_s10_b * 100)))
                                eris_smes_secB_s10_g1 = '%0*d' % (10, int(abs(
                                    eris_smes_secB_s10_g * 100)))
                                gross_amt_qulfy_secB_s10_b1 = '%0*d' % (
                                    10, int(abs(
                                        gross_amt_qulfy_secB_s10_b * 100)))
                                gross_amt_qulfy_secB_s10_g1 = '%0*d' % (
                                    10, int(abs(
                                        gross_amt_qulfy_secB_s10_g * 100)))
                                gorss_amt_gain_secB_s10_b1 = '%0*d' % (10, int(
                                    abs(gorss_amt_gain_secB_s10_b * 100)))
                                gorss_amt_gain_secB_s10_g1 = '%0*d' % (10, int(
                                    abs(gorss_amt_gain_secB_s10_g * 100)))

                                total_eris_smes_secB_s10_b += (
                                                eris_smes_secB_s10_b)
                                total_eris_smes_secB_s10_g += (
                                                eris_smes_secB_s10_g)
                                total_gross_amt_qulfy_secB_s10_b += (
                                                gross_amt_qulfy_secB_s10_b)
                                total_gorss_amt_gain_secB_s10_g += (
                                                gorss_amt_gain_secB_s10_g)
                                total_gorss_amt_gain_secB_s10_b += (
                                                gorss_amt_gain_secB_s10_b)
                                total_gross_amt_qulfy_secB_s10_g += (
                                                gross_amt_qulfy_secB_s10_g)

                                if secB_len < 15:
                                    length = 15 - secB_len
                                    length = length * 148
                                    detail_record_2 += tools.ustr('').ljust(
                                        length)
                                detail_record_2 += tools.ustr(
                                                eris_smes_secB_s10_b1).ljust(
                                                    10)
                                detail_record_2 += tools.ustr(
                                                eris_smes_secB_s10_g1).ljust(
                                                    10)
                                detail_record_2 += tools.ustr(
                                         gross_amt_qulfy_secB_s10_b1).ljust(10)
                                detail_record_2 += tools.ustr(
                                        gross_amt_qulfy_secB_s10_g1).ljust(10)
                                detail_record_2 += tools.ustr(
                                        gorss_amt_gain_secB_s10_b1).ljust(10)
                                detail_record_2 += tools.ustr(
                                        gorss_amt_gain_secB_s10_g1).ljust(10)

                                eris_all_corporation_secC_s10_b1 = '%0*d' % (
                                    10, int(abs(
                                        eris_all_corporation_secC_s10_b * 100)
                                    ))
                                eris_all_corporation_secC_s10_g1 = '%0*d' % (
                                    10, int(abs(
                                        eris_all_corporation_secC_s10_g * 100)
                                    ))
                                gross_amt_qulfy_secC_s10_b1 = '%0*d' % (
                                    10, int(abs(
                                        gross_amt_qulfy_secC_s10_b * 100)))
                                gorss_amt_gain_secC_s10_b1 = '%0*d' % (10, int(
                                    abs(gorss_amt_gain_secC_s10_b * 100)))
                                gross_amt_qulfy_secC_s10_g1 = '%0*d' % (
                                    10, int(abs(
                                        gross_amt_qulfy_secC_s10_g * 100)))
                                gorss_amt_gain_secC_s10_g1 = '%0*d' % (10, int(
                                    abs(gorss_amt_gain_secC_s10_g * 100)))

                                total_eris_all_corporation_secC_s10_b += (
                                        eris_all_corporation_secC_s10_b)
                                total_eris_all_corporation_secC_s10_g += (
                                        eris_all_corporation_secC_s10_g)
                                total_gross_amt_qulfy_secC_s10_b += (
                                        gross_amt_qulfy_secC_s10_b)
                                total_gross_amt_qulfy_secC_s10_g += (
                                        gross_amt_qulfy_secC_s10_g)
                                total_gorss_amt_gain_secC_s10_b += (
                                        gorss_amt_gain_secC_s10_b)
                                total_gorss_amt_gain_secC_s10_g += (
                                        gorss_amt_gain_secC_s10_g)

                                if secC_len < 15:
                                    length = 15 - secC_len
                                    length = length * 148
                                    detail_record_3 += tools.ustr('').ljust(
                                        length)
                                detail_record_3 += tools.ustr(
                                    eris_all_corporation_secC_s10_b1).ljust(10)
                                detail_record_3 += tools.ustr(
                                    eris_all_corporation_secC_s10_g1).ljust(10)
                                detail_record_3 += tools.ustr(
                                    gross_amt_qulfy_secC_s10_b1).ljust(10)
                                detail_record_3 += tools.ustr(
                                    gross_amt_qulfy_secC_s10_g1).ljust(10)
                                detail_record_3 += tools.ustr(
                                    gorss_amt_gain_secC_s10_b1).ljust(10)
                                detail_record_3 += tools.ustr(
                                    gorss_amt_gain_secC_s10_g1).ljust(10)

                                eris_start_ups_secD_s10_b1 = '%0*d' % (10, int(
                                    abs(eris_start_ups_secD_s10_b * 100)))
                                eris_start_ups_secD_s10_g1 = '%0*d' % (10, int(
                                    abs(eris_start_ups_secD_s10_g * 100)))
                                gross_amt_qulfy_secD_s10_b1 = '%0*d' % (
                                    10, int(abs(
                                        gross_amt_qulfy_secD_s10_b * 100)))
                                gorss_amt_gain_secD_s10_b1 = '%0*d' % (10, int(
                                    abs(gorss_amt_gain_secD_s10_b * 100)))
                                gross_amt_qulfy_secD_s10_g1 = '%0*d' % (
                                    10, int(abs(
                                        gross_amt_qulfy_secD_s10_g * 100)))
                                gorss_amt_gain_secD_s10_g1 = '%0*d' % (10, int(
                                    abs(gorss_amt_gain_secD_s10_g * 100)))

                                total_eris_start_ups_secD_s10_b += (
                                            eris_start_ups_secD_s10_b)
                                total_eris_start_ups_secD_s10_g += (
                                            eris_start_ups_secD_s10_g)
                                total_gross_amt_qulfy_secD_s10_b += (
                                            gross_amt_qulfy_secD_s10_b)
                                total_gross_amt_qulfy_secD_s10_g += (
                                            gross_amt_qulfy_secD_s10_g)
                                total_gorss_amt_gain_secD_s10_b += (
                                            gorss_amt_gain_secD_s10_b)
                                total_gorss_amt_gain_secD_s10_g += (
                                            gorss_amt_gain_secD_s10_g)

                                if secD_len < 15:
                                    length = 15 - secD_len
                                    length = length * 148
                                    detail_record_4 += tools.ustr('').ljust(
                                        length)
                                detail_record_4 += tools.ustr(
                                        eris_start_ups_secD_s10_b1).ljust(10)
                                detail_record_4 += tools.ustr(
                                        eris_start_ups_secD_s10_g1).ljust(10)
                                detail_record_4 += tools.ustr(
                                        gross_amt_qulfy_secD_s10_b1).ljust(10)
                                detail_record_4 += tools.ustr(
                                        gross_amt_qulfy_secD_s10_g1).ljust(10)
                                detail_record_4 += tools.ustr(
                                        gorss_amt_gain_secD_s10_b1).ljust(10)
                                detail_record_4 += tools.ustr(
                                        gorss_amt_gain_secD_s10_g1).ljust(10)

                                grand_toatl_secE_eris_smes_s10_b = (
                                                        eris_smes_secB_s10_b)
                                grand_toatl_secE_eris_smes_s10_g = (
                                                        eris_smes_secB_s10_g)
                                grand_total_secE_eris_all_corporation_s10_b = (
                                            eris_all_corporation_secC_s10_b)
                                grand_total_secE_eris_all_corporation_s10_g = (
                                            eris_all_corporation_secC_s10_g)
                                grand_total_secE_eris_start_ups_s10_b = (
                                            eris_start_ups_secD_s10_b)
                                grand_total_secE_eris_start_ups_s10_g = (
                                            eris_start_ups_secD_s10_g)
                                grand_total_secE_gross_amt_qulfy_s10_b = (
                                            gross_amt_qulfy_secA_s10_b +
                                            gross_amt_qulfy_secB_s10_b +
                                            gross_amt_qulfy_secC_s10_b +
                                            gross_amt_qulfy_secD_s10_b)
                                grand_total_secE_gross_amt_qulfy_s10_g = (
                                            gross_amt_qulfy_secA_s10_g +
                                            gross_amt_qulfy_secB_s10_g +
                                            gross_amt_qulfy_secC_s10_g +
                                            gross_amt_qulfy_secD_s10_g)
                                grand_total_secE_gorss_amt_gain_s10_b = (
                                            gorss_amt_gain_secA_s10_b +
                                            gorss_amt_gain_secB_s10_b +
                                            gorss_amt_gain_secC_s10_b +
                                            gorss_amt_gain_secD_s10_b)
                                grand_total_secE_gorss_amt_gain_s10_g = (
                                            gorss_amt_gain_secA_s10_g +
                                            gorss_amt_gain_secB_s10_g +
                                            gorss_amt_gain_secC_s10_g +
                                            gorss_amt_gain_secD_s10_g)

                                total_grand_total_secE_gross_amt_qulfy_s10_b +=\
                                    grand_total_secE_gross_amt_qulfy_s10_b
                                total_grand_total_secE_gross_amt_qulfy_s10_g +=\
                                    grand_total_secE_gross_amt_qulfy_s10_g
                                total_grand_total_secE_gorss_amt_gain_s10_b +=\
                                    grand_total_secE_gorss_amt_gain_s10_b
                                total_grand_total_secE_gorss_amt_gain_s10_g +=\
                                    grand_total_secE_gorss_amt_gain_s10_g

                                grand_toatl_secE_eris_smes_s10_b = '%0*d' % (
                                    11, int(abs(
                                        grand_toatl_secE_eris_smes_s10_b * 100)
                                    ))
                                grand_toatl_secE_eris_smes_s10_g = '%0*d' % (
                                    11, int(abs(
                                        grand_toatl_secE_eris_smes_s10_g * 100)
                                    ))
                                grand_total_secE_eris_all_corporation_s10_b = (
                                 '%0*d' % (11, int(abs(
                                  grand_total_secE_eris_all_corporation_s10_b *
                                  100))))
                                grand_total_secE_eris_all_corporation_s10_g = (
                                 '%0*d' % (11, int(abs(
                                  grand_total_secE_eris_all_corporation_s10_g *
                                  100))))
                                grand_total_secE_eris_start_ups_s10_b = (
                                 '%0*d' % (11, int(abs(
                                  grand_total_secE_eris_start_ups_s10_b * 100)
                                     )))
                                grand_total_secE_eris_start_ups_s10_g = (
                                 '%0*d' % (11, int(abs(
                                     grand_total_secE_eris_start_ups_s10_g *
                                     100))))
                                grand_total_secE_gross_amt_qulfy_s10_b = (
                                 '%0*d' % (11, int(abs(
                                     grand_total_secE_gross_amt_qulfy_s10_b *
                                     100))))
                                grand_total_secE_gross_amt_qulfy_s10_g = (
                                 '%0*d' % (11, int(abs(
                                     grand_total_secE_gross_amt_qulfy_s10_g *
                                     100))))
                                grand_total_secE_gorss_amt_gain_s10_b = (
                                 '%0*d' % (11, int(abs(
                                     grand_total_secE_gorss_amt_gain_s10_b *
                                     100))))
                                grand_total_secE_gorss_amt_gain_s10_g = (
                                 '%0*d' % (11, int(abs(
                                     grand_total_secE_gorss_amt_gain_s10_g *
                                     100))))

                                detail_record_5 += tools.ustr(
                                    grand_total_secE_gross_amt_qulfy_s10_b
                                    ).ljust(11)
                                detail_record_5 += tools.ustr(
                                        grand_total_secE_gross_amt_qulfy_s10_g
                                        ).ljust(11)
                                detail_record_5 += tools.ustr(
                                        grand_total_secE_gorss_amt_gain_s10_b
                                        ).ljust(11)
                                detail_record_5 += tools.ustr(
                                        grand_total_secE_gorss_amt_gain_s10_g
                                        ).ljust(11)
                                detail_record_5 += tools.ustr('').ljust(135)
                                detail_record_5 += tools.ustr('').ljust(
                                    50)+"\r\n"

                                main_detail = (detail_record +
                                               detail_record_1 +
                                               detail_record_2 +
                                               detail_record_3 +
                                               detail_record_4 +
                                               detail_record_5 or '')
                                tmp_file.write(main_detail)

                    total_detail_record = '%0*d' % (6, int(
                                                abs(total_detail_record)))
                    total_gross_amt_qulfy_secA_s10_b = '%0*d' % (14, int(
                                abs(total_gross_amt_qulfy_secA_s10_b * 100)))
                    total_gorss_amt_gain_secA_s10_b = '%0*d' % (14, int(
                                abs(total_gorss_amt_gain_secA_s10_b * 100)))
                    total_gross_amt_qulfy_secA_s10_g = '%0*d' % (14, int(
                                abs(total_gross_amt_qulfy_secA_s10_g * 100)))
                    total_gorss_amt_gain_secA_s10_g = '%0*d' % (14, int(
                                abs(total_gorss_amt_gain_secA_s10_g * 100)))

                    total_eris_smes_secB_s10_b = '%0*d' % (14, int(
                                abs(total_eris_smes_secB_s10_b * 100)))
                    total_eris_smes_secB_s10_g = '%0*d' % (14, int(
                                abs(total_eris_smes_secB_s10_g * 100)))
                    total_gross_amt_qulfy_secB_s10_b = '%0*d' % (14, int(
                                abs(total_gross_amt_qulfy_secB_s10_b * 100)))
                    total_gross_amt_qulfy_secB_s10_g = '%0*d' % (14, int(
                                abs(total_gross_amt_qulfy_secB_s10_g * 100)))
                    total_gorss_amt_gain_secB_s10_b = '%0*d' % (14, int(
                                abs(total_gorss_amt_gain_secB_s10_b * 100)))
                    total_gorss_amt_gain_secB_s10_g = '%0*d' % (14, int(
                                abs(total_gorss_amt_gain_secB_s10_g * 100)))

                    total_eris_all_corporation_secC_s10_b = '%0*d' % (14, int(
                            abs(total_eris_all_corporation_secC_s10_b * 100)))
                    total_eris_all_corporation_secC_s10_g = '%0*d' % (14, int(
                            abs(total_eris_all_corporation_secC_s10_g * 100)))
                    total_gross_amt_qulfy_secC_s10_b = '%0*d' % (14, int(
                            abs(total_gross_amt_qulfy_secC_s10_b * 100)))
                    total_gross_amt_qulfy_secC_s10_g = '%0*d' % (14, int(
                            abs(total_gross_amt_qulfy_secC_s10_g * 100)))
                    total_gorss_amt_gain_secC_s10_b = '%0*d' % (14, int(
                            abs(total_gorss_amt_gain_secC_s10_b * 100)))
                    total_gorss_amt_gain_secC_s10_g = '%0*d' % (14, int(
                            abs(total_gorss_amt_gain_secC_s10_g * 100)))

                    total_eris_start_ups_secD_s10_b = '%0*d' % (14, int(
                            abs(total_eris_start_ups_secD_s10_b * 100)))
                    total_eris_start_ups_secD_s10_g = '%0*d' % (14, int(
                            abs(total_eris_start_ups_secD_s10_g * 100)))
                    total_gross_amt_qulfy_secD_s10_b = '%0*d' % (14, int(
                            abs(total_gross_amt_qulfy_secD_s10_b * 100)))
                    total_gross_amt_qulfy_secD_s10_g = '%0*d' % (14, int(
                            abs(total_gross_amt_qulfy_secD_s10_g * 100)))
                    total_gorss_amt_gain_secD_s10_b = '%0*d' % (14, int(
                            abs(total_gorss_amt_gain_secD_s10_b * 100)))
                    total_gorss_amt_gain_secD_s10_g = '%0*d' % (14, int(
                            abs(total_gorss_amt_gain_secD_s10_g * 100)))

                    total_grand_total_secE_gross_amt_qulfy_s10_b = '%0*d' % (
                        14, int(abs(
                            total_grand_total_secE_gross_amt_qulfy_s10_b * 100)
                        ))
                    total_grand_total_secE_gross_amt_qulfy_s10_g = '%0*d' % (
                        14, int(abs(
                            total_grand_total_secE_gross_amt_qulfy_s10_g * 100)
                        ))
                    total_grand_total_secE_gorss_amt_gain_s10_b = '%0*d' % (
                        14, int(abs(
                            total_grand_total_secE_gorss_amt_gain_s10_b * 100)
                        ))
                    total_grand_total_secE_gorss_amt_gain_s10_g = '%0*d' % (
                        14, int(abs(
                            total_grand_total_secE_gorss_amt_gain_s10_g * 100)
                        ))

                    footer_record = '2'.ljust(1) + tools.ustr(
                        total_detail_record).ljust(6) + tools.ustr(
                                total_gross_amt_qulfy_secA_s10_b
                                ).ljust(14) + tools.ustr(
                                total_gross_amt_qulfy_secA_s10_g
                                ).ljust(14) + tools.ustr(
                                total_gorss_amt_gain_secA_s10_b
                                ).ljust(14) + tools.ustr(
                                total_gorss_amt_gain_secA_s10_g
                                ).ljust(14) + tools.ustr(
                                total_eris_smes_secB_s10_b
                                ).ljust(14) + tools.ustr(
                                total_eris_smes_secB_s10_g
                                ).ljust(14) + tools.ustr(
                                total_gross_amt_qulfy_secB_s10_b
                                ).ljust(14) + tools.ustr(
                                total_gross_amt_qulfy_secB_s10_g
                                ).ljust(14) + tools.ustr(
                                total_gorss_amt_gain_secB_s10_b
                                ).ljust(14) + tools.ustr(
                                total_gorss_amt_gain_secB_s10_g
                                ).ljust(14) + tools.ustr(
                                total_eris_all_corporation_secC_s10_b
                                ).ljust(14) + tools.ustr(
                                total_eris_all_corporation_secC_s10_g
                                ).ljust(14) + tools.ustr(
                                total_gross_amt_qulfy_secC_s10_b
                                ).ljust(14) + tools.ustr(
                                total_gross_amt_qulfy_secC_s10_g
                                ).ljust(14) + tools.ustr(
                                total_gorss_amt_gain_secC_s10_b
                                ).ljust(14) + tools.ustr(
                                total_gorss_amt_gain_secC_s10_g
                                ).ljust(14) + tools.ustr(
                                total_eris_start_ups_secD_s10_b
                                ).ljust(14) + tools.ustr(
                                total_eris_start_ups_secD_s10_g
                                ).ljust(14) + tools.ustr(
                                total_gross_amt_qulfy_secD_s10_b
                                ).ljust(14) + tools.ustr(
                                total_gross_amt_qulfy_secD_s10_g
                                ).ljust(14) + tools.ustr(
                                total_gorss_amt_gain_secD_s10_b
                                ).ljust(14) + tools.ustr(
                                total_gorss_amt_gain_secD_s10_g
                                ).ljust(14) + tools.ustr(
                                total_grand_total_secE_gross_amt_qulfy_s10_b
                                ).ljust(14) + tools.ustr(
                                total_grand_total_secE_gross_amt_qulfy_s10_g
                                ).ljust(14) + tools.ustr(
                                total_grand_total_secE_gorss_amt_gain_s10_b
                                ).ljust(14) + tools.ustr(
                                total_grand_total_secE_gorss_amt_gain_s10_g
                                ).ljust(14) + tools.ustr('').ljust(8929
                                                                   ) + "\r\n"
                    tmp_file.write(footer_record)
                finally:
                    if tmp_file:
                        tmp_file.close()
                file_rec = open(tgz_tmp_filename, "rb")
                out = file_rec.read()
                file_rec.close()
                res = base64.b64encode(out)
                module_rec = self.env['binary.appendix8b.text.file.wizard'
                                      ].create({'name': 'appendix8b.txt',
                                                'appendix8b_txt_file': res})
                return {
                  'name': _('Binary'),
                  'res_id': module_rec.id,
                  "view_mode": 'form',
                  'res_model': 'binary.appendix8b.text.file.wizard',
                  'type': 'ir.actions.act_window',
                  'target': 'new',
                  'context': context,
                }

            elif data['print_type'] == 'xml':

                doc = minidom.Document()
                root = doc.createElement('A8B2009')
                root.setAttribute('xmlns', 'http://www.iras.gov.sg/A8BDef2009')
                doc.appendChild(root)
                context = dict(self._context) or {}

                start_year = data.get('start_date', False).strftime('%Y')
                to_year = data.get('end_date', False).strftime('%Y')
                start_date = '%s-01-01' % tools.ustr(int(start_year) - 1)
                end_date = '%s-12-31' % tools.ustr(int(to_year) - 1)
                start_date_year = '%s-01-01' % tools.ustr(int(start_year))
                end_date_year = '%s-12-31' % tools.ustr(int(to_year))
                if ('start_date' in data and 'end_date' in data) and (
                    data.get('start_date', False) >= data.get('end_date',
                                                              False)):
                    raise ValidationError(
                        _("You must be enter start date less than end date !"))
                context.update({'employe_id': data['employee_ids'],
                                'datas': data
                                })
                start_date = end_date = False
                from_date = context.get('datas', False
                                        ).get('start_date', False)
                to_date = context.get('datas', False
                                      ).get('end_date', False)
                if from_date and to_date:
                    basis_year = tools.ustr(from_date.year - 1)
                    start_date = '%s-01-01' % tools.ustr(int(
                                                        from_date.year) - 1)
                    end_date = '%s-12-31' % tools.ustr(int(
                                                        from_date.year) - 1)
                    start_date = datetime.strptime(start_date, DSDF)
                    end_date = datetime.strptime(end_date, DSDF)

                batchdate = context.get('datas')['batch_date'
                                                 ].strftime('%Y%m%d')
                incorporation_date = ''
                if context.get('datas')['incorporation_date']:
                    incorporation_date = context.get('datas')[
                        'incorporation_date'].strftime('%Y%m%d')
                emp_rec = HrEmployeeObj.search([
                    ('user_id', '=', int(context.get('datas')['payroll_user']))
                                        ], limit=1)
                emp_designation = ''
                user_brw = ResUsersObj.browse(int(
                    context.get('datas')['payroll_user']))
                payroll_admin_user_name = user_brw.name
                company_name = user_brw.company_id.name
                organization_id_type = user_rec.company_id.organization_id_type
                organization_id_no = user_rec.company_id.organization_id_no
                if emp_rec and emp_rec.id:
                    emp_designation = emp_rec.job_id.name
                    emp_email = emp_rec.work_email
                    emp_contact = emp_rec.work_phone
                    if not emp_email and emp_contact:
                        raise ValidationError(
                            _("Please configure Email or Contact for %s "
                              "employee." % (emp_rec.name)))

                """ Header for Appendix8B """
                header = doc.createElement('A8BHeader')
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
                    Source.appendChild(doc.createTextNode(
                        context.get('datas')['source']))
                FileHeaderST.appendChild(Source)

                BasisYear = doc.createElement('BasisYear')
                if basis_year:
                    BasisYear.appendChild(doc.createTextNode(str(basis_year)))
                FileHeaderST.appendChild(BasisYear)

                PaymentType = doc.createElement('PaymentType')
                PaymentType.appendChild(doc.createTextNode('13'))
                FileHeaderST.appendChild(PaymentType)

                OrganizationID = doc.createElement('OrganizationID')
                if organization_id_type:
                    OrganizationID.appendChild(doc.createTextNode(str(
                                                        organization_id_type)))
                FileHeaderST.appendChild(OrganizationID)

                OrganizationIDNo = doc.createElement('OrganizationIDNo')
                if organization_id_no:
                    OrganizationIDNo.appendChild(doc.createTextNode(
                                                        organization_id_no))
                FileHeaderST.appendChild(OrganizationIDNo)

                AuthorisedPersonName = doc.createElement(
                                                        'AuthorisedPersonName')
                if payroll_admin_user_name:
                    AuthorisedPersonName.appendChild(doc.createTextNode(str(
                                                    payroll_admin_user_name)))
                FileHeaderST.appendChild(AuthorisedPersonName)

                AuthorisedPersonDesignation = doc.createElement(
                                                'AuthorisedPersonDesignation')
                if emp_designation:
                    AuthorisedPersonDesignation.appendChild(doc.createTextNode(
                                                        str(emp_designation)))
                FileHeaderST.appendChild(AuthorisedPersonDesignation)

                EmployerName = doc.createElement('EmployerName')
                if company_name:
                    EmployerName.appendChild(doc.createTextNode(str(
                                                                company_name)))
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
                if (context.get('datas') and
                        context.get('datas')['batch_indicatior']):
                    BatchIndicator.appendChild(doc.createTextNode(str(
                                    context.get('datas')['batch_indicatior'])))
                FileHeaderST.appendChild(BatchIndicator)

                BatchDate = doc.createElement('BatchDate')
                if batchdate:
                    BatchDate.appendChild(doc.createTextNode(str(batchdate)))
                FileHeaderST.appendChild(BatchDate)

                IncorporationDate = doc.createElement('IncorporationDate')
                if incorporation_date:
                    IncorporationDate.appendChild(doc.createTextNode(
                                                    str(incorporation_date)))
                FileHeaderST.appendChild(IncorporationDate)

                DivisionOrBranchName = doc.createElement(
                                                        'DivisionOrBranchName')
                FileHeaderST.appendChild(DivisionOrBranchName)

                Details = doc.createElement('Details')
                root.appendChild(Details)

                """ get the contract for selected employee"""
                employee_ids = data['employee_ids']
                employee_ids = HrEmployeeObj.browse(employee_ids)
                total_detail_record = 0
                total_gross_amt_qulfy_secA_s10_b = 0.0
                total_gorss_amt_gain_secA_s10_b = 0.0
                total_gross_amt_qulfy_secA_s10_g = 0.0
                total_gorss_amt_gain_secA_s10_g = 0.0

                total_eris_smes_secB_s10_b = 0.0
                total_eris_smes_secB_s10_g = 0.0
                total_gross_amt_qulfy_secB_s10_b = 0.0
                total_gorss_amt_gain_secB_s10_g = 0.0
                total_gorss_amt_gain_secB_s10_b = 0.0
                total_gross_amt_qulfy_secB_s10_g = 0.0

                total_eris_all_corporation_secC_s10_b = 0.0
                total_eris_all_corporation_secC_s10_g = 0.0
                total_gross_amt_qulfy_secC_s10_b = 0.0
                total_gross_amt_qulfy_secC_s10_g = 0.0
                total_gorss_amt_gain_secC_s10_b = 0.0
                total_gorss_amt_gain_secC_s10_g = 0.0

                total_eris_start_ups_secD_s10_b = 0.0
                total_eris_start_ups_secD_s10_g = 0.0
                total_gross_amt_qulfy_secD_s10_b = 0.0
                total_gross_amt_qulfy_secD_s10_g = 0.0
                total_gorss_amt_gain_secD_s10_b = 0.0
                total_gorss_amt_gain_secD_s10_g = 0.0

                total_grand_total_secE_gross_amt_qulfy_s10_b = 0.0
                total_grand_total_secE_gross_amt_qulfy_s10_g = 0.0
                total_grand_total_secE_gorss_amt_gain_s10_b = 0.0
                total_grand_total_secE_gorss_amt_gain_s10_g = 0.0

                for employee in employee_ids:
                    total_detail_record += 1
                    if not employee.identification_id:
                        raise ValidationError(
                            _("There is no identification no define for %s "
                              "employee." % (employee.name)))
                    if not employee.empnationality_id:
                        raise ValidationError(
                            _("There is no Nationality code define for %s "
                              "employee." % (employee.name)))
                    birth_date = employee.birthday.strftime('%Y%m%d')
                    if employee.gender == 'male':
                        gender = 'M'
                    else:
                        gender = 'F'
                    contract_income_tax_ids = incometax_brw.search([
                       ('contract_id.employee_id', '=', employee.id),
                       ('start_date', '>=', start_date_year),
                       ('end_date', '<=', end_date_year)])

                    A8BRecord = doc.createElement('A8BRecord')
                    Details.appendChild(A8BRecord)

                    ESubmissionSDSC = doc.createElement('ESubmissionSDSC')
                    ESubmissionSDSC.setAttribute(
                        'xmlns', 'http://tempuri.org/ESubmissionSDSC.xsd')
                    A8BRecord.appendChild(ESubmissionSDSC)

                    record1 = doc.createElement('A8B2009ST')
                    ESubmissionSDSC.appendChild(record1)

                    RecordType = doc.createElement('RecordType')
                    RecordType.setAttribute(
                        'xmlns', 'http://www.iras.gov.sg/A8B2009')
                    RecordType.appendChild(doc.createTextNode('1'))
                    record1.appendChild(RecordType)

                    IDType = doc.createElement('IDType')
                    IDType.setAttribute(
                        'xmlns', 'http://www.iras.gov.sg/A8B2009')
                    if employee.identification_no:
                        IDType.appendChild(doc.createTextNode(str(
                                                employee.identification_no)))
                    record1.appendChild(IDType)

                    IDNo = doc.createElement('IDNo')
                    IDNo.setAttribute('xmlns', 'http://www.iras.gov.sg/A8B2009'
                                      )
                    if employee.identification_id:
                        IDNo.appendChild(doc.createTextNode(str(
                                                employee.identification_id)))
                    record1.appendChild(IDNo)

                    NameLine1 = doc.createElement('NameLine1')
                    NameLine1.setAttribute(
                        'xmlns', 'http://www.iras.gov.sg/A8B2009')
                    if employee.name:
                        NameLine1.appendChild(doc.createTextNode(str(
                                                            employee.name)))
                    record1.appendChild(NameLine1)

                    NameLine2 = doc.createElement('NameLine2')
                    NameLine2.setAttribute(
                        'xmlns', 'http://www.iras.gov.sg/A8B2009')
                    record1.appendChild(NameLine2)

                    Nationality = doc.createElement('Nationality')
                    Nationality.setAttribute(
                        'xmlns', 'http://www.iras.gov.sg/A8B2009')
                    if employee.empnationality_id and \
                            employee.empnationality_id.code:
                        Nationality.appendChild(doc.createTextNode(str(
                                            employee.empnationality_id.code)))
                    record1.appendChild(Nationality)

                    Sex = doc.createElement('Sex')
                    Sex.setAttribute('xmlns', 'http://www.iras.gov.sg/A8B2009')
                    if gender:
                        Sex.appendChild(doc.createTextNode(str(gender)))
                    record1.appendChild(Sex)

                    DateOfBirth = doc.createElement('DateOfBirth')
                    DateOfBirth.setAttribute(
                        'xmlns', 'http://www.iras.gov.sg/A8B2009')
                    if birth_date:
                        DateOfBirth.appendChild(doc.createTextNode(str(
                                                                birth_date)))
                    record1.appendChild(DateOfBirth)

                    gross_amt_qulfy_secA_s10_b = 0.0
                    gorss_amt_gain_secA_s10_b = 0.0
                    gross_amt_qulfy_secA_s10_g = 0.0
                    gorss_amt_gain_secA_s10_g = 0.0

                    gross_amt_qulfy_secB_s10_b = 0.0
                    gross_amt_qulfy_secB_s10_g = 0.0
                    gorss_amt_gain_secB_s10_b = 0.0
                    gorss_amt_gain_secB_s10_g = 0.0
                    eris_smes_secB_s10_b = 0.0
                    eris_smes_secB_s10_g = 0.0

                    gross_amt_qulfy_secC_s10_b = 0.0
                    gorss_amt_gain_secC_s10_b = 0.0
                    eris_all_corporation_secC_s10_b = 0.0
                    gross_amt_qulfy_secC_s10_g = 0.0
                    gorss_amt_gain_secC_s10_g = 0.0
                    eris_all_corporation_secC_s10_g = 0.0

                    eris_start_ups_secD_s10_b = 0.0
                    eris_start_ups_secD_s10_g = 0.0
                    gross_amt_qulfy_secD_s10_b = 0.0
                    gorss_amt_gain_secD_s10_b = 0.0
                    gross_amt_qulfy_secD_s10_g = 0.0
                    gorss_amt_gain_secD_s10_g = 0.0

                    grand_toatl_secE_eris_smes_s10_b = 0.0
                    grand_toatl_secE_eris_smes_s10_g = 0.0
                    grand_total_secE_eris_all_corporation_s10_b = 0.0
                    grand_total_secE_eris_all_corporation_s10_g = 0.0
                    grand_total_secE_eris_start_ups_s10_b = 0.0
                    grand_total_secE_eris_start_ups_s10_g = 0.0
                    grand_total_secE_gross_amt_qulfy_s10_b = 0.0
                    grand_total_secE_gross_amt_qulfy_s10_g = 0.0
                    grand_total_secE_gorss_amt_gain_s10_b = 0.0
                    grand_total_secE_gorss_amt_gain_s10_g = 0.0

                    detail_record_1 = ''
                    detail_record_2 = ''
                    detail_record_3 = ''
                    detail_record_4 = ''
                    detail_record_5 = ''

                    secA_len = 0
                    secB_len = 0
                    secC_len = 0
                    secD_len = 0
                    if contract_income_tax_ids and contract_income_tax_ids.ids:
                        counter = 1
                        for emp in contract_income_tax_ids[0]:
                            secA = []
                            secB = []
                            secC = []
                            secD = []
                            for line in emp.app_8b_income_tax:
                                grant_date = ''
                                if line.tax_plan_grant_date:
                                    grant_date = (
                                        line.tax_plan_grant_date.strftime(
                                            '%Y%m%d'))
                                exercise_date = ''
                                exercise_price = 0.00
                                open_mrkt_val = 0.00
                                open_mrkt_val_1 = 0.00
                                if line.tax_plan == 'esop':
                                    if line.esop_date:
                                        exercise_date = (
                                            line.esop_date.strftime('%Y%m%d'))
                                    exercise_price = line.ex_price_esop
                                    open_mrkt_val = line.open_val_esop
                                    if line.is_moratorium is True:
                                        open_mrkt_val_1 = line.moratorium_price
                                    else:
                                        open_mrkt_val_1 = line.open_val_esop
                                elif line.tax_plan == 'esow':
                                    if line.esow_date:
                                        exercise_date = (
                                            line.esow_date.strftime('%Y%m%d'))
                                    exercise_price = line.pay_under_esow
                                    open_mrkt_val = line.esow_plan
                                    if line.is_moratorium is True:
                                        open_mrkt_val_1 = line.moratorium_price
                                    else:
                                        open_mrkt_val_1 = line.esow_plan

                                exercise_price = (int(abs(
                                          exercise_price * 100000)) / 100000.0)
                                open_mrkt_val = (int(abs(
                                          open_mrkt_val * 100000))/100000.0)
                                open_mrkt_val_1 = (int(abs(
                                          open_mrkt_val_1 * 100000))/100000.0)
                                no_share = (int(abs(
                                          line.no_of_share * 100000))/100000.0)

                                gross_amt_qulfy_secA = (
                                                line.secA_grss_amt_qulfy_tx)
                                gorss_amt_gain_secA = (
                                                line.secA_grss_amt_qulfy_tx)

                                if line.section == 'sectionA':
                                    det_sec_A = {}
                                    secA_len += 1

                                    det_sec_A = {'1': organization_id_type,
                                                 '2': organization_id_no,
                                                 '3': company_name,
                                                 '4': line.tax_plan,
                                                 '5': grant_date,
                                                 '6': exercise_date,
                                                 '7': exercise_price,
                                                 '8': open_mrkt_val,
                                                 '9': open_mrkt_val_1,
                                                 '10': no_share,
                                                 '11': gross_amt_qulfy_secA,
                                                 '12': gorss_amt_gain_secA,
                                                 }

                                    secA.append(det_sec_A)

                                    if line.tax_plan == 'esow':
                                        gross_amt_qulfy_secA_s10_b += (
                                                line.secA_grss_amt_qulfy_tx)
                                        gorss_amt_gain_secA_s10_b += (
                                                line.secA_grss_amt_qulfy_tx)
                                    if line.tax_plan == 'esop':
                                        grant_date = (
                                            line.tax_plan_grant_date.strftime(
                                                '%Y/%m/%d'))
                                        esop_appvl_date = '2003/01/01'
                                        if grant_date > esop_appvl_date:
                                            gross_amt_qulfy_secA_s10_b += (
                                                line.secA_grss_amt_qulfy_tx)
                                            gorss_amt_gain_secA_s10_b += (
                                                line.secA_grss_amt_qulfy_tx)
                                        elif grant_date < esop_appvl_date:
                                            gross_amt_qulfy_secA_s10_g += (
                                                line.secA_grss_amt_qulfy_tx)
                                            gorss_amt_gain_secA_s10_g += (
                                                line.secA_grss_amt_qulfy_tx)

                                gross_amt_qulfy_secB = (
                                                line.secB_grss_amt_qulfy_tx)
                                gorss_amt_gain_secB = (
                                 line.eris_smes + line.secB_grss_amt_qulfy_tx)
                                gorss_amt_gain_secB = abs(gorss_amt_gain_secB)
                                eris_smes = abs(line.eris_smes)
                                if line.section == 'sectionB':
                                    secB_len += 1
                                    det_sec_B = {}

                                    det_sec_B = {'1': organization_id_type,
                                                 '2': organization_id_no,
                                                 '3': company_name,
                                                 '4': line.tax_plan,
                                                 '5': grant_date,
                                                 '6': exercise_date,
                                                 '7': exercise_price,
                                                 '8': open_mrkt_val,
                                                 '9': open_mrkt_val_1,
                                                 '10': no_share,
                                                 '11': eris_smes,
                                                 '12': gross_amt_qulfy_secB,
                                                 '13': gorss_amt_gain_secB,
                                                 }
                                    secB.append(det_sec_B)

                                    if line.tax_plan == 'esow':
                                        gross_amt_qulfy_secB_s10_b += \
                                                line.secB_grss_amt_qulfy_tx
                                        gorss_amt_gain_secB_s10_b += (
                                                line.eris_smes +
                                                line.secB_grss_amt_qulfy_tx)
                                        eris_smes_secB_s10_b += line.eris_smes
                                    if line.tax_plan == 'esop':
                                        grant_date = line.tax_plan_grant_date
                                        grant_date = datetime.strptime(
                                            grant_date, DSDF)
                                        grant_date = grant_date.strftime(
                                            '%Y/%m/%d')
                                        esop_appvl_date = '2003/01/01'
                                        if grant_date > esop_appvl_date:
                                            gross_amt_qulfy_secB_s10_b += \
                                                    line.secB_grss_amt_qulfy_tx
                                            gorss_amt_gain_secB_s10_b += (
                                                line.eris_smes +
                                                line.secB_grss_amt_qulfy_tx)
                                            eris_smes_secB_s10_b += (
                                                line.eris_smes)
                                        elif grant_date < esop_appvl_date:
                                            gross_amt_qulfy_secB_s10_g += \
                                                    line.secB_grss_amt_qulfy_tx
                                            gorss_amt_gain_secB_s10_g += (
                                                line.eris_smes +
                                                line.secB_grss_amt_qulfy_tx)
                                            eris_smes_secB_s10_g += (
                                                line.eris_smes)

                                gross_amt_qulfy_secC = abs(
                                                line.secC_grss_amt_qulfy_tx)
                                gorss_amt_gain_secC = (
                                    line.eris_all_corporation +
                                    line.secC_grss_amt_qulfy_tx)
                                gorss_amt_gain_secC = abs(gorss_amt_gain_secC)
                                eris_all_corporation = abs(
                                                    line.eris_all_corporation)
                                if line.section == 'sectionC':
                                    det_sec_C = {}
                                    secC_len += 1

                                    det_sec_C = {'1': organization_id_type,
                                                 '2': organization_id_no,
                                                 '3': company_name,
                                                 '4': line.tax_plan,
                                                 '5': grant_date,
                                                 '6': exercise_date,
                                                 '7': exercise_price,
                                                 '8': open_mrkt_val,
                                                 '9': open_mrkt_val_1,
                                                 '10': no_share,
                                                 '11': eris_all_corporation,
                                                 '12': gross_amt_qulfy_secC,
                                                 '13': gorss_amt_gain_secC,
                                                 }
                                    secC.append(det_sec_C)

                                    if line.tax_plan == 'esow':
                                        gross_amt_qulfy_secC_s10_b += \
                                                    line.secC_grss_amt_qulfy_tx
                                        gorss_amt_gain_secC_s10_b += (
                                                line.eris_smes +
                                                line.secC_grss_amt_qulfy_tx)
                                        eris_all_corporation_secC_s10_b += (
                                                    line.eris_smes)
                                    if line.tax_plan == 'esop':
                                        grant_date = (
                                            line.tax_plan_grant_date.strftime(
                                                                '%Y/%m/%d'))
                                        esop_appvl_date = '2003/01/01'
                                        if grant_date > esop_appvl_date:
                                            gross_amt_qulfy_secC_s10_b += \
                                                    line.secC_grss_amt_qulfy_tx
                                            gorss_amt_gain_secC_s10_b += (
                                                line.eris_smes +
                                                line.secC_grss_amt_qulfy_tx)
                                            eris_all_corporation_secC_s10_b +=\
                                                line.eris_smes
                                        elif grant_date < esop_appvl_date:
                                            gross_amt_qulfy_secC_s10_g +=\
                                                    line.secC_grss_amt_qulfy_tx
                                            gorss_amt_gain_secC_s10_g += (
                                                line.eris_smes +
                                                line.secC_grss_amt_qulfy_tx)
                                            eris_all_corporation_secC_s10_g +=\
                                                line.eris_smes

                                gross_amt_qulfy_secD = abs(
                                                line.secD_grss_amt_qulfy_tx)
                                gorss_amt_gain_secD = (
                                    line.eris_start_ups +
                                    line.secD_grss_amt_qulfy_tx)
                                gorss_amt_gain_secD = abs(gorss_amt_gain_secD)
                                eris_start_ups = abs(line.eris_start_ups)

                                if line.section == 'sectionD':
                                    det_sec_D = {}
                                    secD_len += 1

                                    det_sec_D = {'1': organization_id_type,
                                                 '2': organization_id_no,
                                                 '3': company_name,
                                                 '4': line.tax_plan,
                                                 '5': grant_date,
                                                 '6': exercise_date,
                                                 '7': exercise_price,
                                                 '8': open_mrkt_val,
                                                 '9': open_mrkt_val_1,
                                                 '10': no_share,
                                                 '11': eris_start_ups,
                                                 '12': gross_amt_qulfy_secD,
                                                 '13': gorss_amt_gain_secD,
                                                 }
                                    secD.append(det_sec_D)

                                    if line.tax_plan == 'esow':
                                        gross_amt_qulfy_secD_s10_b += \
                                                line.secD_grss_amt_qulfy_tx
                                        gorss_amt_gain_secD_s10_b += (
                                                line.eris_start_ups +
                                                line.secD_grss_amt_qulfy_tx)
                                        eris_start_ups_secD_s10_b += (
                                                line.eris_start_ups)
                                    if line.tax_plan == 'esop':
                                        grant_date = (
                                            line.tax_plan_grant_date.strftime(
                                                                '%Y/%m/%d'))
                                        esop_appvl_date = '2003/01/01'
                                        if grant_date > esop_appvl_date:
                                            gross_amt_qulfy_secD_s10_b += \
                                                line.secD_grss_amt_qulfy_tx
                                            gorss_amt_gain_secD_s10_b += \
                                                line.eris_start_ups + \
                                                line.secD_grss_amt_qulfy_tx
                                            eris_start_ups_secD_s10_b += \
                                                line.eris_start_ups
                                        elif grant_date < esop_appvl_date:
                                            gross_amt_qulfy_secD_s10_g += \
                                                line.secD_grss_amt_qulfy_tx
                                            gorss_amt_gain_secD_s10_g += \
                                                line.eris_smes + \
                                                line.secC_grss_amt_qulfy_tx
                                            eris_start_ups_secD_s10_g += \
                                                line.eris_start_ups

                            gross_amt_qulfy_secA_s10_b1 = abs(
                                                    gross_amt_qulfy_secA_s10_b)
                            gross_amt_qulfy_secA_s10_g1 = abs(
                                                    gross_amt_qulfy_secA_s10_g)
                            gorss_amt_gain_secA_s10_b1 = abs(
                                                    gorss_amt_gain_secA_s10_b)
                            gorss_amt_gain_secA_s10_g1 = abs(
                                                    gorss_amt_gain_secA_s10_g)

                            total_gross_amt_qulfy_secA_s10_b += (
                                                    gross_amt_qulfy_secA_s10_b)
                            total_gorss_amt_gain_secA_s10_b += (
                                                    gorss_amt_gain_secA_s10_b)
                            total_gross_amt_qulfy_secA_s10_g += (
                                                    gross_amt_qulfy_secA_s10_g)
                            total_gorss_amt_gain_secA_s10_g += (
                                                    gorss_amt_gain_secA_s10_g)

                            if secA_len < 15:
                                length = 15 - secA_len
                                for dummy_rec in range(length):
                                    det_sec_A = {'1': organization_id_type,
                                                 '2': organization_id_no,
                                                 '3': company_name,
                                                 '4': False,
                                                 '5': False,
                                                 '6': False,
                                                 '7': 0,
                                                 '8': 0,
                                                 '9': 0,
                                                 '10': 0,
                                                 '11': 0,
                                                 '12': 0,
                                                 }
                                    secA.append(det_sec_A)

                            for rec_secA in secA:
                                records = 'Record' + str(counter)

                                record_n = doc.createElement(records)
                                record_n.setAttribute(
                                    'xmlns', 'http://www.iras.gov.sg/A8B2009')
                                record1.appendChild(record_n)

                                CompanyIDType = doc.createElement(
                                                            'CompanyIDType')
                                CompanyIDType.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '1' in rec_secA and rec_secA['1']:
                                    CompanyIDType.appendChild(
                                        doc.createTextNode(str(rec_secA['1'])))
                                record_n.appendChild(CompanyIDType)

                                CompanyIDNo = doc.createElement('CompanyIDNo')
                                CompanyIDNo.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '2' in rec_secA and rec_secA['2']:
                                    CompanyIDNo.appendChild(
                                        doc.createTextNode(str(rec_secA['2'])))
                                record_n.appendChild(CompanyIDNo)

                                CompanyName = doc.createElement('CompanyName')
                                CompanyName.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '3' in rec_secA and rec_secA['3']:
                                    CompanyName.appendChild(doc.createTextNode(
                                                        str(rec_secA['3'])))
                                record_n.appendChild(CompanyName)

                                PlanType = doc.createElement('PlanType')
                                PlanType.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '4' in rec_secA and rec_secA['4']:
                                    PlanType.appendChild(doc.createTextNode(
                                                        str(rec_secA['4'])))
                                record_n.appendChild(PlanType)

                                DateOfGrant = doc.createElement('DateOfGrant')
                                DateOfGrant.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '5' in rec_secA and rec_secA['5']:
                                    DateOfGrant.appendChild(doc.createTextNode(
                                                        str(rec_secA['5'])))
                                record_n.appendChild(DateOfGrant)

                                DateOfExercise = doc.createElement(
                                                            'DateOfExercise')
                                DateOfExercise.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '6' in rec_secA and rec_secA['6']:
                                    DateOfExercise.appendChild(
                                        doc.createTextNode(str(rec_secA['6'])))
                                record_n.appendChild(DateOfExercise)

                                Price = doc.createElement('Price')
                                Price.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '7' in rec_secA and rec_secA['7']:
                                    Price.appendChild(
                                        doc.createTextNode(str(rec_secA['7'])))
                                record_n.appendChild(Price)

                                OpenMarketValueAtDateOfGrant = (
                                    doc.createElement(
                                        'OpenMarketValueAtDateOfGrant'))
                                OpenMarketValueAtDateOfGrant.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '8' in rec_secA:
                                    OpenMarketValueAtDateOfGrant.appendChild(
                                        doc.createTextNode(str(rec_secA['8'])))
                                record_n.appendChild(
                                                OpenMarketValueAtDateOfGrant)

                                OpenMarketValueAtDateOfExercise = (
                                    doc.createElement(
                                        'OpenMarketValueAtDateOfExercise'))
                                OpenMarketValueAtDateOfExercise.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '9' in rec_secA and rec_secA['9']:
                                    OpenMarketValueAtDateOfExercise.appendChild
                                    (doc.createTextNode(str(rec_secA['9'])))
                                record_n.appendChild(
                                        OpenMarketValueAtDateOfExercise)

                                NoOfShares = doc.createElement('NoOfShares')
                                NoOfShares.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '10' in rec_secA and rec_secA['10']:
                                    NoOfShares.appendChild(doc.createTextNode(
                                                        str(rec_secA['10'])))
                                record_n.appendChild(NoOfShares)

                                NonExemptGrossAmount = doc.createElement(
                                                        'NonExemptGrossAmount')
                                NonExemptGrossAmount.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '11' in rec_secA and rec_secA['11']:
                                    NonExemptGrossAmount.appendChild(
                                        doc.createTextNode(str(rec_secA['11'])
                                                           ))
                                record_n.appendChild(NonExemptGrossAmount)

                                GrossAmountGains = doc.createElement(
                                                        'GrossAmountGains')
                                GrossAmountGains.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '12' in rec_secA and rec_secA['12']:
                                    GrossAmountGains.appendChild(
                                        doc.createTextNode(str(rec_secA['12'])
                                                           ))
                                record_n.appendChild(GrossAmountGains)
                                counter += 1

    #                        Section A Total
                            SectionATotals = doc.createElement('SectionATotals'
                                                               )
                            SectionATotals.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/A8B2009')
                            record1.appendChild(SectionATotals)

                            TotalGrossAmountNonExemptAfter2003 = (
                                doc.createElement(
                                    'TotalGrossAmountNonExemptAfter2003'))
                            TotalGrossAmountNonExemptAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountNonExemptAfter2003.appendChild(
                                doc.createTextNode(str(
                                        gross_amt_qulfy_secA_s10_b1)))
                            SectionATotals.appendChild(
                                            TotalGrossAmountNonExemptAfter2003)

                            TotalGrossAmountNonExemptBefore2003 = (
                                doc.createElement(
                                    'TotalGrossAmountNonExemptBefore2003'))
                            TotalGrossAmountNonExemptBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountNonExemptBefore2003.appendChild(
                                doc.createTextNode(str(
                                                gross_amt_qulfy_secA_s10_g1)))
                            SectionATotals.appendChild(
                                        TotalGrossAmountNonExemptBefore2003)

                            TotalGrossAmountGainsAfter2003 = doc.createElement(
                                            'TotalGrossAmountGainsAfter2003')
                            TotalGrossAmountGainsAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountGainsAfter2003.appendChild(
                             doc.createTextNode(str(gorss_amt_gain_secA_s10_b1)
                                                ))
                            SectionATotals.appendChild(
                                                TotalGrossAmountGainsAfter2003)

                            TotalGrossAmountGainsBefore2003 = (
                                doc.createElement(
                                    'TotalGrossAmountGainsBefore2003'))
                            TotalGrossAmountGainsBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountGainsBefore2003.appendChild(
                                doc.createTextNode(str(
                                                gorss_amt_gain_secA_s10_g1)))
                            SectionATotals.appendChild(
                                            TotalGrossAmountGainsBefore2003)

                            eris_smes_secB_s10_b1 = abs(eris_smes_secB_s10_b)
                            eris_smes_secB_s10_g1 = abs(eris_smes_secB_s10_g)
                            gross_amt_qulfy_secB_s10_b1 = abs(
                                                    gross_amt_qulfy_secB_s10_b)
                            gross_amt_qulfy_secB_s10_g1 = abs(
                                                    gross_amt_qulfy_secB_s10_g)
                            gorss_amt_gain_secB_s10_b1 = abs(
                                                    gorss_amt_gain_secB_s10_b)
                            gorss_amt_gain_secB_s10_g1 = abs(
                                                    gorss_amt_gain_secB_s10_g)

                            total_eris_smes_secB_s10_b += eris_smes_secB_s10_b
                            total_eris_smes_secB_s10_g += eris_smes_secB_s10_g
                            total_gross_amt_qulfy_secB_s10_b += (
                                                    gross_amt_qulfy_secB_s10_b)
                            total_gorss_amt_gain_secB_s10_g += (
                                                    gorss_amt_gain_secB_s10_g)
                            total_gorss_amt_gain_secB_s10_b += (
                                                    gorss_amt_gain_secB_s10_b)
                            total_gross_amt_qulfy_secB_s10_g += (
                                                    gross_amt_qulfy_secB_s10_g)

                            if secB_len < 15:
                                length = 15 - secB_len

                                for dummy_rec in range(length):
                                    det_sec_B = {'1': organization_id_type,
                                                 '2': organization_id_no,
                                                 '3': company_name,
                                                 '4': False,
                                                 '5': False,
                                                 '6': False,
                                                 '7': 0,
                                                 '8': 0,
                                                 '9': 0,
                                                 '10': 0,
                                                 '11': 0,
                                                 '12': 0,
                                                 '13': 0,
                                                 }
                                    secB.append(det_sec_B)

                            for rec_secB in secB:
                                records = 'Record' + str(counter)

                                record_n = doc.createElement(records)
                                record_n.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/A8B2009')
                                record1.appendChild(record_n)

                                CompanyIDType = doc.createElement(
                                                            'CompanyIDType')
                                CompanyIDType.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '1' in rec_secB and rec_secB['1']:
                                    CompanyIDType.appendChild(
                                        doc.createTextNode(str(rec_secB['1'])))
                                record_n.appendChild(CompanyIDType)

                                CompanyIDNo = doc.createElement('CompanyIDNo')
                                CompanyIDNo.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '2' in rec_secB and rec_secB['2']:
                                    CompanyIDNo.appendChild(doc.createTextNode(
                                                        str(rec_secB['2'])))
                                record_n.appendChild(CompanyIDNo)

                                CompanyName = doc.createElement('CompanyName')
                                CompanyName.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '3' in rec_secB and rec_secB['3']:
                                    CompanyName.appendChild(doc.createTextNode(
                                                        str(rec_secB['3'])))
                                record_n.appendChild(CompanyName)

                                PlanType = doc.createElement('PlanType')
                                PlanType.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '4' in rec_secB and rec_secB['4']:
                                    PlanType.appendChild(doc.createTextNode(
                                                        str(rec_secB['4'])))
                                record_n.appendChild(PlanType)

                                DateOfGrant = doc.createElement('DateOfGrant')
                                DateOfGrant.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '5' in rec_secB and rec_secB['5']:
                                    DateOfGrant.appendChild(doc.createTextNode(
                                                        str(rec_secB['5'])))
                                record_n.appendChild(DateOfGrant)

                                DateOfExercise = doc.createElement(
                                                            'DateOfExercise')
                                DateOfExercise.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '6' in rec_secB and rec_secB['6']:
                                    DateOfExercise.appendChild(
                                        doc.createTextNode(str(rec_secB['6'])))
                                record_n.appendChild(DateOfExercise)

                                Price = doc.createElement('Price')
                                Price.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '7' in rec_secB and rec_secB['7']:
                                    Price.appendChild(doc.createTextNode(str(
                                                            rec_secB['7'])))
                                record_n.appendChild(Price)

                                OpenMarketValueAtDateOfGrant = (
                                    doc.createElement(
                                        'OpenMarketValueAtDateOfGrant'))
                                OpenMarketValueAtDateOfGrant.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '8' in rec_secB:
                                    OpenMarketValueAtDateOfGrant.appendChild(
                                        doc.createTextNode(str(rec_secB['8'])))
                                record_n.appendChild(
                                    OpenMarketValueAtDateOfGrant)

                                OpenMarketValueAtDateOfExercise = (
                                    doc.createElement(
                                        'OpenMarketValueAtDateOfExercise'))
                                OpenMarketValueAtDateOfExercise.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '9' in rec_secB and rec_secB['9']:
                                    OpenMarketValueAtDateOfExercise.\
                                        appendChild(doc.createTextNode(str(
                                                            rec_secB['9'])))
                                record_n.appendChild(
                                            OpenMarketValueAtDateOfExercise)

                                NoOfShares = doc.createElement('NoOfShares')
                                NoOfShares.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '10' in rec_secB and rec_secB['10']:
                                    NoOfShares.appendChild(doc.createTextNode(
                                                    str(rec_secB['10'])))
                                record_n.appendChild(NoOfShares)

                                ExemptGrossAmountUnderERIS = doc.createElement(
                                                'ExemptGrossAmountUnderERIS')
                                ExemptGrossAmountUnderERIS.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '11' in rec_secB and rec_secB['11']:
                                    ExemptGrossAmountUnderERIS.appendChild(
                                        doc.createTextNode(str(rec_secB['11'])
                                                           ))
                                record_n.appendChild(ExemptGrossAmountUnderERIS
                                                     )

                                NonExemptGrossAmount = doc.createElement(
                                                        'NonExemptGrossAmount')
                                NonExemptGrossAmount.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '12' in rec_secB and rec_secB['12']:
                                    NonExemptGrossAmount.appendChild(
                                        doc.createTextNode(str(rec_secB['12'])
                                                           ))
                                record_n.appendChild(NonExemptGrossAmount)

                                GrossAmountGains = doc.createElement(
                                                            'GrossAmountGains')
                                GrossAmountGains.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '13' in rec_secB and rec_secB['13']:
                                    GrossAmountGains.appendChild(
                                        doc.createTextNode(str(rec_secB['13'])
                                                           ))
                                record_n.appendChild(GrossAmountGains)
                                counter += 1

    #                        Section B total

                            SectionBTotals = doc.createElement('SectionBTotals'
                                                               )
                            SectionBTotals.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/A8B2009')
                            record1.appendChild(SectionBTotals)

                            TotalGrossAmountExemptAfter2003 = (
                                doc.createElement(
                                    'TotalGrossAmountExemptAfter2003'))
                            TotalGrossAmountExemptAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountExemptAfter2003.appendChild(
                                doc.createTextNode(str(eris_smes_secB_s10_b1)))
                            SectionBTotals.appendChild(
                                            TotalGrossAmountExemptAfter2003)

                            TotalGrossAmountExemptBefore2003 = (
                                doc.createElement(
                                    'TotalGrossAmountExemptBefore2003'))
                            TotalGrossAmountExemptBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountExemptBefore2003.appendChild(
                                doc.createTextNode(str(eris_smes_secB_s10_g1)))
                            SectionBTotals.appendChild(
                                            TotalGrossAmountExemptBefore2003)

                            TotalGrossAmountNonExemptAfter2003 = (
                                doc.createElement(
                                    'TotalGrossAmountNonExemptAfter2003'))
                            TotalGrossAmountNonExemptAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountNonExemptAfter2003.appendChild(
                                doc.createTextNode(str(
                                                gross_amt_qulfy_secB_s10_b1)))
                            SectionBTotals.appendChild(
                                            TotalGrossAmountNonExemptAfter2003)

                            TotalGrossAmountNonExemptBefore2003 = (
                                doc.createElement(
                                    'TotalGrossAmountNonExemptBefore2003'))
                            TotalGrossAmountNonExemptBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountNonExemptBefore2003.appendChild(
                                doc.createTextNode(str(
                                                gross_amt_qulfy_secB_s10_g1)))
                            SectionBTotals.appendChild(
                                        TotalGrossAmountNonExemptBefore2003)

                            TotalGrossAmountGainsAfter2003 = doc.createElement(
                                            'TotalGrossAmountGainsAfter2003')
                            TotalGrossAmountGainsAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountGainsAfter2003.appendChild(
                                doc.createTextNode(str(
                                                gorss_amt_gain_secB_s10_b1)))
                            SectionBTotals.appendChild(
                                                TotalGrossAmountGainsAfter2003)

                            TotalGrossAmountGainsBefore2003 = \
                                doc.createElement(
                                            'TotalGrossAmountGainsBefore2003')
                            TotalGrossAmountGainsBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountGainsBefore2003.appendChild(
                                doc.createTextNode(str(
                                                gorss_amt_gain_secB_s10_g1)))
                            SectionBTotals.appendChild(
                                            TotalGrossAmountGainsBefore2003)

                            eris_all_corporation_secC_s10_b1 = abs(
                                            eris_all_corporation_secC_s10_b)
                            eris_all_corporation_secC_s10_g1 = abs(
                                            eris_all_corporation_secC_s10_g)
                            gross_amt_qulfy_secC_s10_b1 = abs(
                                            gross_amt_qulfy_secC_s10_b)
                            gorss_amt_gain_secC_s10_b1 = abs(
                                            gorss_amt_gain_secC_s10_b)
                            gross_amt_qulfy_secC_s10_g1 = abs(
                                            gross_amt_qulfy_secC_s10_g)
                            gorss_amt_gain_secC_s10_g1 = abs(
                                            gorss_amt_gain_secC_s10_g)

                            total_eris_all_corporation_secC_s10_b += (
                                            eris_all_corporation_secC_s10_b)
                            total_eris_all_corporation_secC_s10_g += (
                                            eris_all_corporation_secC_s10_g)
                            total_gross_amt_qulfy_secC_s10_b += (
                                            gross_amt_qulfy_secC_s10_b)
                            total_gross_amt_qulfy_secC_s10_g += (
                                            gross_amt_qulfy_secC_s10_g)
                            total_gorss_amt_gain_secC_s10_b += (
                                            gorss_amt_gain_secC_s10_b)
                            total_gorss_amt_gain_secC_s10_g += (
                                                gorss_amt_gain_secC_s10_g)

                            if secC_len < 15:
                                length = 15 - secC_len

                                for dummy_rec in range(length):
                                    det_sec_C = {'1': organization_id_type,
                                                 '2': organization_id_no,
                                                 '3': company_name,
                                                 '4': False,
                                                 '5': False,
                                                 '6': False,
                                                 '7': 0,
                                                 '8': 0,
                                                 '9': 0,
                                                 '10': 0,
                                                 '11': 0,
                                                 '12': 0,
                                                 '13': 0,
                                                 }
                                    secC.append(det_sec_C)

                            for rec_secC in secC:
                                records = 'Record' + str(counter)

                                record_n = doc.createElement(records)
                                record_n.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/A8B2009')
                                record1.appendChild(record_n)

                                CompanyIDType = doc.createElement(
                                                            'CompanyIDType')
                                CompanyIDType.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '1' in rec_secC and rec_secC['1']:
                                    CompanyIDType.appendChild(
                                        doc.createTextNode(str(rec_secC['1'])))
                                record_n.appendChild(CompanyIDType)

                                CompanyIDNo = doc.createElement('CompanyIDNo')
                                CompanyIDNo.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '2' in rec_secC and rec_secC['2']:
                                    CompanyIDNo.appendChild(
                                        doc.createTextNode(str(rec_secC['2'])))
                                record_n.appendChild(CompanyIDNo)

                                CompanyName = doc.createElement('CompanyName')
                                CompanyName.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '3' in rec_secC and rec_secC['3']:
                                    CompanyName.appendChild(
                                        doc.createTextNode(str(rec_secC['3'])))
                                record_n.appendChild(CompanyName)

                                PlanType = doc.createElement('PlanType')
                                PlanType.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '4' in rec_secC and rec_secC['4']:
                                    PlanType.appendChild(
                                        doc.createTextNode(str(rec_secC['4'])))
                                record_n.appendChild(PlanType)

                                DateOfGrant = doc.createElement('DateOfGrant')
                                DateOfGrant.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '5' in rec_secC and rec_secC['5']:
                                    DateOfGrant.appendChild(
                                        doc.createTextNode(str(rec_secC['5'])))
                                record_n.appendChild(DateOfGrant)

                                DateOfExercise = doc.createElement(
                                                            'DateOfExercise')
                                DateOfExercise.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '6' in rec_secC and rec_secC['6']:
                                    DateOfExercise.appendChild(
                                        doc.createTextNode(str(rec_secC['6'])))
                                record_n.appendChild(DateOfExercise)

                                Price = doc.createElement('Price')
                                Price.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '7' in rec_secC and rec_secC['7']:
                                    Price.appendChild(
                                        doc.createTextNode(str(rec_secC['7'])))
                                record_n.appendChild(Price)

                                OpenMarketValueAtDateOfGrant = (
                                    doc.createElement(
                                               'OpenMarketValueAtDateOfGrant'))
                                OpenMarketValueAtDateOfGrant.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '8' in rec_secC:
                                    OpenMarketValueAtDateOfGrant.appendChild(
                                        doc.createTextNode(str(rec_secC['8'])))
                                record_n.appendChild(
                                                OpenMarketValueAtDateOfGrant)

                                OpenMarketValueAtDateOfExercise = \
                                    doc.createElement(
                                        'OpenMarketValueAtDateOfExercise')
                                OpenMarketValueAtDateOfExercise.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '9' in rec_secC and rec_secC['9']:
                                    OpenMarketValueAtDateOfExercise.appendChild
                                    (doc.createTextNode(str(rec_secC['9'])))
                                record_n.appendChild(
                                            OpenMarketValueAtDateOfExercise)

                                NoOfShares = doc.createElement('NoOfShares')
                                NoOfShares.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '10' in rec_secC and rec_secC['10']:
                                    NoOfShares.appendChild(doc.createTextNode(
                                                        str(rec_secC['10'])))
                                record_n.appendChild(NoOfShares)

                                ExemptGrossAmountUnderERIS = doc.createElement(
                                                'ExemptGrossAmountUnderERIS')
                                ExemptGrossAmountUnderERIS.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '11' in rec_secC and rec_secC['11']:
                                    ExemptGrossAmountUnderERIS.appendChild(
                                        doc.createTextNode(str(rec_secC['11'])
                                                           ))
                                record_n.appendChild(
                                                    ExemptGrossAmountUnderERIS)

                                NonExemptGrossAmount = doc.createElement(
                                                        'NonExemptGrossAmount')
                                NonExemptGrossAmount.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '12' in rec_secC and rec_secC['12']:
                                    NonExemptGrossAmount.appendChild(
                                        doc.createTextNode(str(rec_secC['12'])
                                                           ))
                                record_n.appendChild(NonExemptGrossAmount)

                                GrossAmountGains = doc.createElement(
                                                            'GrossAmountGains')
                                GrossAmountGains.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '13' in rec_secC and rec_secC['13']:
                                    GrossAmountGains.appendChild(
                                        doc.createTextNode(str(rec_secC['13'])
                                                           ))
                                record_n.appendChild(GrossAmountGains)
                                counter += 1

    #                        Section C Total
                            SectionCTotals = doc.createElement(
                                                            'SectionCTotals')
                            SectionCTotals.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/A8B2009')
                            record1.appendChild(SectionCTotals)

                            TotalGrossAmountExemptAfter2003 = (
                                doc.createElement(
                                    'TotalGrossAmountExemptAfter2003'))
                            TotalGrossAmountExemptAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountExemptAfter2003.appendChild(
                                doc.createTextNode(str(
                                            eris_all_corporation_secC_s10_b1)))
                            SectionCTotals.appendChild(
                                            TotalGrossAmountExemptAfter2003)

                            TotalGrossAmountExemptBefore2003 = (
                                doc.createElement(
                                    'TotalGrossAmountExemptBefore2003'))
                            TotalGrossAmountExemptBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountExemptBefore2003.appendChild(
                                doc.createTextNode(str(
                                            eris_all_corporation_secC_s10_g1)))
                            SectionCTotals.appendChild(
                                            TotalGrossAmountExemptBefore2003)

                            TotalGrossAmountNonExemptAfter2003 = (
                                doc.createElement(
                                    'TotalGrossAmountNonExemptAfter2003'))
                            TotalGrossAmountNonExemptAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountNonExemptAfter2003.appendChild(
                                doc.createTextNode(str(
                                                gross_amt_qulfy_secC_s10_b1)))
                            SectionCTotals.appendChild(
                                            TotalGrossAmountNonExemptAfter2003)

                            TotalGrossAmountNonExemptBefore2003 = (
                                doc.createElement(
                                    'TotalGrossAmountNonExemptBefore2003'))
                            TotalGrossAmountNonExemptBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountNonExemptBefore2003.appendChild(
                                doc.createTextNode(str(
                                                gross_amt_qulfy_secC_s10_g1)))
                            SectionCTotals.appendChild(
                                        TotalGrossAmountNonExemptBefore2003)

                            TotalGrossAmountGainsAfter2003 = doc.createElement(
                                            'TotalGrossAmountGainsAfter2003')
                            TotalGrossAmountGainsAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountGainsAfter2003.appendChild(
                                doc.createTextNode(str(
                                                gorss_amt_gain_secC_s10_b1)))
                            SectionCTotals.appendChild(
                                                TotalGrossAmountGainsAfter2003)

                            TotalGrossAmountGainsBefore2003 = (
                                doc.createElement(
                                    'TotalGrossAmountGainsBefore2003'))
                            TotalGrossAmountGainsBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountGainsBefore2003.appendChild(
                                doc.createTextNode(str(
                                                gorss_amt_gain_secC_s10_g1)))
                            SectionCTotals.appendChild(
                                            TotalGrossAmountGainsBefore2003)

                            eris_start_ups_secD_s10_b1 = abs(
                                                    eris_start_ups_secD_s10_b)
                            eris_start_ups_secD_s10_g1 = abs(
                                                    eris_start_ups_secD_s10_g)
                            gross_amt_qulfy_secD_s10_b1 = abs(
                                                    gross_amt_qulfy_secD_s10_b)
                            gorss_amt_gain_secD_s10_b1 = abs(
                                                    gorss_amt_gain_secD_s10_b)
                            gross_amt_qulfy_secD_s10_g1 = abs(
                                                    gross_amt_qulfy_secD_s10_g)
                            gorss_amt_gain_secD_s10_g1 = abs(
                                                    gorss_amt_gain_secD_s10_g)

                            total_eris_start_ups_secD_s10_b += (
                                                    eris_start_ups_secD_s10_b)
                            total_eris_start_ups_secD_s10_g += (
                                                    eris_start_ups_secD_s10_g)
                            total_gross_amt_qulfy_secD_s10_b += (
                                                    gross_amt_qulfy_secD_s10_b)
                            total_gross_amt_qulfy_secD_s10_g += (
                                                    gross_amt_qulfy_secD_s10_g)
                            total_gorss_amt_gain_secD_s10_b += (
                                                    gorss_amt_gain_secD_s10_b)
                            total_gorss_amt_gain_secD_s10_g += (
                                                    gorss_amt_gain_secD_s10_g)

                            if secD_len < 15:
                                length = 15 - secD_len

                                for dummy_rec in range(length):
                                    det_sec_D = {'1': organization_id_type,
                                                 '2': organization_id_no,
                                                 '3': company_name,
                                                 '4': False,
                                                 '5': False,
                                                 '6': False,
                                                 '7': 0,
                                                 '8': 0,
                                                 '9': 0,
                                                 '10': 0,
                                                 '11': 0,
                                                 '12': 0,
                                                 '13': 0,
                                                 }
                                    secD.append(det_sec_D)

                            for rec_secD in secD:
                                records = 'Record' + str(counter)

                                record_n = doc.createElement(records)
                                record_n.setAttribute(
                                    'xmlns', 'http://www.iras.gov.sg/A8B2009')
                                record1.appendChild(record_n)

                                CompanyIDType = doc.createElement(
                                                            'CompanyIDType')
                                CompanyIDType.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '1' in rec_secD and rec_secD['1']:
                                    CompanyIDType.appendChild(
                                        doc.createTextNode(str(rec_secD['1'])))
                                record_n.appendChild(CompanyIDType)

                                CompanyIDNo = doc.createElement('CompanyIDNo')
                                CompanyIDNo.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '2' in rec_secD and rec_secD['2']:
                                    CompanyIDNo.appendChild(
                                        doc.createTextNode(str(rec_secD['2'])))
                                record_n.appendChild(CompanyIDNo)

                                CompanyName = doc.createElement('CompanyName')
                                CompanyName.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '3' in rec_secD and rec_secD['3']:
                                    CompanyName.appendChild(
                                        doc.createTextNode(str(rec_secD['3'])))
                                record_n.appendChild(CompanyName)

                                PlanType = doc.createElement('PlanType')
                                PlanType.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '4' in rec_secD and rec_secD['4']:
                                    PlanType.appendChild(doc.createTextNode(
                                                        str(rec_secD['4'])))
                                record_n.appendChild(PlanType)

                                DateOfGrant = doc.createElement('DateOfGrant')
                                DateOfGrant.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '5' in rec_secD and rec_secD['5']:
                                    DateOfGrant.appendChild(doc.createTextNode(
                                                        str(rec_secD['5'])))
                                record_n.appendChild(DateOfGrant)

                                DateOfExercise = doc.createElement(
                                                            'DateOfExercise')
                                DateOfExercise.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '6' in rec_secD and rec_secD['6']:
                                    DateOfExercise.appendChild(
                                        doc.createTextNode(str(rec_secD['6'])))
                                record_n.appendChild(DateOfExercise)

                                Price = doc.createElement('Price')
                                Price.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '7' in rec_secD and rec_secD['7']:
                                    Price.appendChild(doc.createTextNode(str(
                                                            rec_secD['7'])))
                                record_n.appendChild(Price)

                                OpenMarketValueAtDateOfGrant = \
                                    doc.createElement(
                                            'OpenMarketValueAtDateOfGrant')
                                OpenMarketValueAtDateOfGrant.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '8' in rec_secD:
                                    OpenMarketValueAtDateOfGrant.appendChild(
                                        doc.createTextNode(str(rec_secD['8'])))
                                record_n.appendChild(
                                                OpenMarketValueAtDateOfGrant)

                                OpenMarketValueAtDateOfExercise = \
                                    doc.createElement(
                                            'OpenMarketValueAtDateOfExercise')
                                OpenMarketValueAtDateOfExercise.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '9' in rec_secD and rec_secD['9']:
                                    OpenMarketValueAtDateOfExercise.appendChild
                                    (doc.createTextNode(str(rec_secD['9'])))
                                record_n.appendChild(
                                            OpenMarketValueAtDateOfExercise)

                                NoOfShares = doc.createElement('NoOfShares')
                                NoOfShares.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '10' in rec_secD and rec_secD['10']:
                                    NoOfShares.appendChild(doc.createTextNode(
                                                        str(rec_secD['10'])))
                                record_n.appendChild(NoOfShares)

                                ExemptGrossAmountUnderERIS = doc.createElement(
                                                'ExemptGrossAmountUnderERIS')
                                ExemptGrossAmountUnderERIS.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '11' in rec_secD and rec_secD['11']:
                                    ExemptGrossAmountUnderERIS.appendChild(
                                        doc.createTextNode(str(rec_secD['11'])
                                                           ))
                                record_n.appendChild(ExemptGrossAmountUnderERIS
                                                     )

                                NonExemptGrossAmount = doc.createElement(
                                                        'NonExemptGrossAmount')
                                NonExemptGrossAmount.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '12' in rec_secD and rec_secD['12']:
                                    NonExemptGrossAmount.appendChild(
                                        doc.createTextNode(str(
                                                            rec_secD['12'])))
                                record_n.appendChild(NonExemptGrossAmount)

                                GrossAmountGains = doc.createElement(
                                                        'GrossAmountGains')
                                GrossAmountGains.setAttribute(
                                 'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                                if '13' in rec_secD and rec_secD['13']:
                                    GrossAmountGains.appendChild(
                                        doc.createTextNode(str(rec_secD['13'])
                                                           ))
                                record_n.appendChild(GrossAmountGains)
                                counter += 1

    #                        Section D Total
                            SectionDTotals = doc.createElement('SectionDTotals'
                                                               )
                            SectionDTotals.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/A8B2009')
                            record1.appendChild(SectionDTotals)

                            TotalGrossAmountExemptAfter2003 = (
                                doc.createElement(
                                    'TotalGrossAmountExemptAfter2003'))
                            TotalGrossAmountExemptAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountExemptAfter2003.appendChild(
                                    doc.createTextNode(str(
                                                eris_start_ups_secD_s10_b1)))
                            SectionDTotals.appendChild(
                                            TotalGrossAmountExemptAfter2003)

                            TotalGrossAmountExemptBefore2003 = (
                                doc.createElement(
                                    'TotalGrossAmountExemptBefore2003'))
                            TotalGrossAmountExemptBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountExemptBefore2003.appendChild(
                                    doc.createTextNode(str(
                                                eris_start_ups_secD_s10_g1)))
                            SectionDTotals.appendChild(
                                            TotalGrossAmountExemptBefore2003)

                            TotalGrossAmountNonExemptAfter2003 = (
                                doc.createElement(
                                    'TotalGrossAmountNonExemptAfter2003'))
                            TotalGrossAmountNonExemptAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountNonExemptAfter2003.appendChild(
                                    doc.createTextNode(str(
                                                gross_amt_qulfy_secD_s10_b1)))
                            SectionDTotals.appendChild(
                                            TotalGrossAmountNonExemptAfter2003)

                            TotalGrossAmountNonExemptBefore2003 = (
                                doc.createElement(
                                    'TotalGrossAmountNonExemptBefore2003'))
                            TotalGrossAmountNonExemptBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountNonExemptBefore2003.appendChild(
                                    doc.createTextNode(str(
                                                gross_amt_qulfy_secD_s10_g1)))
                            SectionDTotals.appendChild(
                                        TotalGrossAmountNonExemptBefore2003)

                            TotalGrossAmountGainsAfter2003 = doc.createElement(
                                            'TotalGrossAmountGainsAfter2003')
                            TotalGrossAmountGainsAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountGainsAfter2003.appendChild(
                                    doc.createTextNode(str(
                                                gorss_amt_gain_secD_s10_b1)))
                            SectionDTotals.appendChild(
                                                TotalGrossAmountGainsAfter2003)

                            TotalGrossAmountGainsBefore2003 = (
                                doc.createElement(
                                    'TotalGrossAmountGainsBefore2003'))
                            TotalGrossAmountGainsBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            TotalGrossAmountGainsBefore2003.appendChild(
                                    doc.createTextNode(str(
                                                gorss_amt_gain_secD_s10_g1)))
                            SectionDTotals.appendChild(
                                            TotalGrossAmountGainsBefore2003)

                            grand_toatl_secE_eris_smes_s10_b = (
                                                        eris_smes_secB_s10_b)
                            grand_toatl_secE_eris_smes_s10_g = (
                                                    eris_smes_secB_s10_g)
                            grand_total_secE_eris_all_corporation_s10_b = (
                                            eris_all_corporation_secC_s10_b)
                            grand_total_secE_eris_all_corporation_s10_g = (
                                            eris_all_corporation_secC_s10_g)
                            grand_total_secE_eris_start_ups_s10_b = (
                                            eris_start_ups_secD_s10_b)
                            grand_total_secE_eris_start_ups_s10_g = (
                                            eris_start_ups_secD_s10_g)
                            grand_total_secE_gross_amt_qulfy_s10_b = (
                                            gross_amt_qulfy_secA_s10_b +
                                            gross_amt_qulfy_secB_s10_b +
                                            gross_amt_qulfy_secC_s10_b +
                                            gross_amt_qulfy_secD_s10_b)
                            grand_total_secE_gross_amt_qulfy_s10_g = (
                                            gross_amt_qulfy_secA_s10_g +
                                            gross_amt_qulfy_secB_s10_g +
                                            gross_amt_qulfy_secC_s10_g +
                                            gross_amt_qulfy_secD_s10_g)
                            grand_total_secE_gorss_amt_gain_s10_b = (
                                            gorss_amt_gain_secA_s10_b +
                                            gorss_amt_gain_secB_s10_b +
                                            gorss_amt_gain_secC_s10_b +
                                            gorss_amt_gain_secD_s10_b)
                            grand_total_secE_gorss_amt_gain_s10_g = (
                                            gorss_amt_gain_secA_s10_g +
                                            gorss_amt_gain_secB_s10_g +
                                            gorss_amt_gain_secC_s10_g +
                                            gorss_amt_gain_secD_s10_g)

                            total_grand_total_secE_gross_amt_qulfy_s10_b += (
                                        grand_total_secE_gross_amt_qulfy_s10_b)
                            total_grand_total_secE_gross_amt_qulfy_s10_g += (
                                        grand_total_secE_gross_amt_qulfy_s10_g)
                            total_grand_total_secE_gorss_amt_gain_s10_b += (
                                        grand_total_secE_gorss_amt_gain_s10_b)
                            total_grand_total_secE_gorss_amt_gain_s10_g += (
                                        grand_total_secE_gorss_amt_gain_s10_g)

                            grand_toatl_secE_eris_smes_s10_b = abs(
                                            grand_toatl_secE_eris_smes_s10_b)
                            grand_toatl_secE_eris_smes_s10_g = abs(
                                            grand_toatl_secE_eris_smes_s10_g)
                            grand_total_secE_eris_all_corporation_s10_b = abs(
                                grand_total_secE_eris_all_corporation_s10_b)
                            grand_total_secE_eris_all_corporation_s10_g = abs(
                                grand_total_secE_eris_all_corporation_s10_g)
                            grand_total_secE_eris_start_ups_s10_b = abs(
                                grand_total_secE_eris_start_ups_s10_b)
                            grand_total_secE_eris_start_ups_s10_g = abs(
                                grand_total_secE_eris_start_ups_s10_g)
                            grand_total_secE_gross_amt_qulfy_s10_b = abs(
                                grand_total_secE_gross_amt_qulfy_s10_b)
                            grand_total_secE_gross_amt_qulfy_s10_g = abs(
                                grand_total_secE_gross_amt_qulfy_s10_g)
                            grand_total_secE_gorss_amt_gain_s10_b = abs(
                                grand_total_secE_gorss_amt_gain_s10_b)
                            grand_total_secE_gorss_amt_gain_s10_g = abs(
                                grand_total_secE_gorss_amt_gain_s10_g)

                            SectionE = doc.createElement('SectionE')
                            SectionE.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/A8B2009')
                            record1.appendChild(SectionE)

                            NonExemptGrandTotalGrossAmountAfter2003 = (
                                doc.createElement(
                                    'NonExemptGrandTotalGrossAmountAfter2003'))
                            NonExemptGrandTotalGrossAmountAfter2003.setAttribute
                            ('xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            NonExemptGrandTotalGrossAmountAfter2003.appendChild
                            (doc.createTextNode(str(
                                    grand_total_secE_gross_amt_qulfy_s10_b)))
                            SectionE.appendChild(
                                    NonExemptGrandTotalGrossAmountAfter2003)

                            NonExemptGrandTotalGrossAmountBefore2003 = \
                                doc.createElement(
                                    'NonExemptGrandTotalGrossAmountBefore2003')
                            NonExemptGrandTotalGrossAmountBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            NonExemptGrandTotalGrossAmountBefore2003.appendChild(
                                doc.createTextNode(str(
                                    grand_total_secE_gross_amt_qulfy_s10_g)))
                            SectionE.appendChild(
                                    NonExemptGrandTotalGrossAmountBefore2003)

                            GainsGrandTotalGrossAmountAfter2003 = \
                                doc.createElement(
                                        'GainsGrandTotalGrossAmountAfter2003')
                            GainsGrandTotalGrossAmountAfter2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            GainsGrandTotalGrossAmountAfter2003.appendChild(
                                doc.createTextNode(str(
                                    grand_total_secE_gorss_amt_gain_s10_b)))
                            SectionE.appendChild(
                                        GainsGrandTotalGrossAmountAfter2003)

                            GainsGrandTotalGrossAmountBefore2003 = \
                                doc.createElement(
                                        'GainsGrandTotalGrossAmountBefore2003')
                            GainsGrandTotalGrossAmountBefore2003.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            GainsGrandTotalGrossAmountBefore2003.appendChild(
                                doc.createTextNode(str(
                                    grand_total_secE_gorss_amt_gain_s10_g)))
                            SectionE.appendChild(
                                        GainsGrandTotalGrossAmountBefore2003)

                            Remarks = doc.createElement('Remarks')
                            Remarks.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            SectionE.appendChild(Remarks)

                            Filler = doc.createElement('Filler')
                            Filler.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/SchemaTypes')
                            SectionE.appendChild(Filler)

                total_detail_record = abs(total_detail_record)
                total_gross_amt_qulfy_secA_s10_b = abs(
                                            total_gross_amt_qulfy_secA_s10_b)
                total_gorss_amt_gain_secA_s10_b = abs(
                                            total_gorss_amt_gain_secA_s10_b)
                total_gross_amt_qulfy_secA_s10_g = abs(
                                            total_gross_amt_qulfy_secA_s10_g)
                total_gorss_amt_gain_secA_s10_g = abs(
                                            total_gorss_amt_gain_secA_s10_g)

                total_eris_smes_secB_s10_b = abs(total_eris_smes_secB_s10_b)
                total_eris_smes_secB_s10_g = abs(total_eris_smes_secB_s10_g)
                total_gross_amt_qulfy_secB_s10_b = abs(
                                            total_gross_amt_qulfy_secB_s10_b)
                total_gross_amt_qulfy_secB_s10_g = abs(
                                            total_gross_amt_qulfy_secB_s10_g)
                total_gorss_amt_gain_secB_s10_b = abs(
                                            total_gorss_amt_gain_secB_s10_b)
                total_gorss_amt_gain_secB_s10_g = abs(
                                            total_gorss_amt_gain_secB_s10_g)

                total_eris_all_corporation_secC_s10_b = abs(
                                        total_eris_all_corporation_secC_s10_b)
                total_eris_all_corporation_secC_s10_g = abs(
                                        total_eris_all_corporation_secC_s10_g)
                total_gross_amt_qulfy_secC_s10_b = abs(
                                        total_gross_amt_qulfy_secC_s10_b)
                total_gross_amt_qulfy_secC_s10_g = abs(
                                        total_gross_amt_qulfy_secC_s10_g)
                total_gorss_amt_gain_secC_s10_b = abs(
                                        total_gorss_amt_gain_secC_s10_b)
                total_gorss_amt_gain_secC_s10_g = abs(
                                        total_gorss_amt_gain_secC_s10_g)

                total_eris_start_ups_secD_s10_b = abs(
                                        total_eris_start_ups_secD_s10_b)
                total_eris_start_ups_secD_s10_g = abs(
                                        total_eris_start_ups_secD_s10_g)
                total_gross_amt_qulfy_secD_s10_b = abs(
                                        total_gross_amt_qulfy_secD_s10_b)
                total_gross_amt_qulfy_secD_s10_g = abs(
                                        total_gross_amt_qulfy_secD_s10_g)
                total_gorss_amt_gain_secD_s10_b = abs(
                                        total_gorss_amt_gain_secD_s10_b)
                total_gorss_amt_gain_secD_s10_g = abs(
                                        total_gorss_amt_gain_secD_s10_g)

                total_grand_total_secE_gross_amt_qulfy_s10_b = abs(
                                total_grand_total_secE_gross_amt_qulfy_s10_b)
                total_grand_total_secE_gross_amt_qulfy_s10_g = abs(
                                total_grand_total_secE_gross_amt_qulfy_s10_g)
                total_grand_total_secE_gorss_amt_gain_s10_b = abs(
                                total_grand_total_secE_gorss_amt_gain_s10_b)
                total_grand_total_secE_gorss_amt_gain_s10_g = abs(
                                total_grand_total_secE_gorss_amt_gain_s10_g)

                A8BTrailer = doc.createElement('A8BTrailer')
                root.appendChild(A8BTrailer)

                ESubmissionSDSC = doc.createElement('ESubmissionSDSC')
                ESubmissionSDSC.setAttribute(
                    'xmlns', 'http://tempuri.org/ESubmissionSDSC.xsd')
                A8BTrailer.appendChild(ESubmissionSDSC)

                A8BTrailer2009ST = doc.createElement('A8BTrailer2009ST')
                ESubmissionSDSC.appendChild(A8BTrailer2009ST)

                RecordType = doc.createElement('RecordType')
                RecordType.appendChild(doc.createTextNode('2'))
                A8BTrailer2009ST.appendChild(RecordType)

                NoOfRecords = doc.createElement('NoOfRecords')
                if total_detail_record:
                    NoOfRecords.appendChild(doc.createTextNode(str(
                                                        total_detail_record)))
                A8BTrailer2009ST.appendChild(NoOfRecords)

                SectionATrailerNonExemptTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionATrailerNonExemptTotalGrossAmountAfter2003'))
                SectionATrailerNonExemptTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(
                                            total_gross_amt_qulfy_secA_s10_b)))
                A8BTrailer2009ST.appendChild(
                            SectionATrailerNonExemptTotalGrossAmountAfter2003)

                SectionATrailerNonExemptTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionATrailerNonExemptTotalGrossAmountBefore2003'))
                SectionATrailerNonExemptTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(
                                            total_gross_amt_qulfy_secA_s10_g)))
                A8BTrailer2009ST.appendChild(
                            SectionATrailerNonExemptTotalGrossAmountBefore2003)

                SectionATrailerGainsTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionATrailerGainsTotalGrossAmountAfter2003'))
                SectionATrailerGainsTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(total_gorss_amt_gain_secA_s10_b)
                                           ))
                A8BTrailer2009ST.appendChild(
                                SectionATrailerGainsTotalGrossAmountAfter2003)

                SectionATrailerGainsTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionATrailerGainsTotalGrossAmountBefore2003'))
                SectionATrailerGainsTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(
                                            total_gorss_amt_gain_secA_s10_g)))
                A8BTrailer2009ST.appendChild(
                                SectionATrailerGainsTotalGrossAmountBefore2003)

                SectionBTrailerExemptTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionBTrailerExemptTotalGrossAmountAfter2003'))
                SectionBTrailerExemptTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(total_eris_smes_secB_s10_b)))
                A8BTrailer2009ST.appendChild(
                        SectionBTrailerExemptTotalGrossAmountAfter2003)

                SectionBTrailerExemptTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionBTrailerExemptTotalGrossAmountBefore2003'))
                SectionBTrailerExemptTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(total_eris_smes_secB_s10_g)))
                A8BTrailer2009ST.appendChild(
                        SectionBTrailerExemptTotalGrossAmountBefore2003)

                SectionBTrailerNonExemptTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionBTrailerNonExemptTotalGrossAmountAfter2003'))
                SectionBTrailerNonExemptTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(
                                            total_gross_amt_qulfy_secB_s10_b)))
                A8BTrailer2009ST.appendChild(
                        SectionBTrailerNonExemptTotalGrossAmountAfter2003)

                SectionBTrailerNonExemptTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionBTrailerNonExemptTotalGrossAmountBefore2003'))
                SectionBTrailerNonExemptTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(
                                            total_gross_amt_qulfy_secB_s10_g)))
                A8BTrailer2009ST.appendChild(
                        SectionBTrailerNonExemptTotalGrossAmountBefore2003)

                SectionBTrailerGainsTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionBTrailerGainsTotalGrossAmountAfter2003'))
                SectionBTrailerGainsTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(
                            total_gorss_amt_gain_secB_s10_b)))
                A8BTrailer2009ST.appendChild(
                        SectionBTrailerGainsTotalGrossAmountAfter2003)

                SectionBTrailerGainsTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionBTrailerGainsTotalGrossAmountBefore2003'))
                SectionBTrailerGainsTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(
                                            total_gorss_amt_gain_secB_s10_g)))
                A8BTrailer2009ST.appendChild(
                        SectionBTrailerGainsTotalGrossAmountBefore2003)

                SectionCTrailerExemptTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionCTrailerExemptTotalGrossAmountAfter2003'))
                SectionCTrailerExemptTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(
                            total_eris_all_corporation_secC_s10_b)))
                A8BTrailer2009ST.appendChild(
                        SectionCTrailerExemptTotalGrossAmountAfter2003)

                SectionCTrailerExemptTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionCTrailerExemptTotalGrossAmountBefore2003'))
                SectionCTrailerExemptTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(
                                    total_eris_all_corporation_secC_s10_g)))
                A8BTrailer2009ST.appendChild(
                        SectionCTrailerExemptTotalGrossAmountBefore2003)

                SectionCTrailerNonExemptTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionCTrailerNonExemptTotalGrossAmountAfter2003'))
                SectionCTrailerNonExemptTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(
                                            total_gross_amt_qulfy_secC_s10_b)))
                A8BTrailer2009ST.appendChild(
                        SectionCTrailerNonExemptTotalGrossAmountAfter2003)

                SectionCTrailerNonExemptTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionCTrailerNonExemptTotalGrossAmountBefore2003'))
                SectionCTrailerNonExemptTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(
                                            total_gross_amt_qulfy_secC_s10_g)))
                A8BTrailer2009ST.appendChild(
                        SectionCTrailerNonExemptTotalGrossAmountBefore2003)

                SectionCTrailerGainsTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionCTrailerGainsTotalGrossAmountAfter2003'))
                SectionCTrailerGainsTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(
                                            total_gorss_amt_gain_secC_s10_b)))
                A8BTrailer2009ST.appendChild(
                                SectionCTrailerGainsTotalGrossAmountAfter2003)

                SectionCTrailerGainsTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionCTrailerGainsTotalGrossAmountBefore2003'))
                SectionCTrailerGainsTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(
                                        total_gorss_amt_gain_secC_s10_g)))
                A8BTrailer2009ST.appendChild(
                        SectionCTrailerGainsTotalGrossAmountBefore2003)

                SectionDTrailerExemptTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionDTrailerExemptTotalGrossAmountAfter2003'))
                SectionDTrailerExemptTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(
                                            total_eris_start_ups_secD_s10_b)))
                A8BTrailer2009ST.appendChild(
                        SectionDTrailerExemptTotalGrossAmountAfter2003)

                SectionDTrailerExemptTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionDTrailerExemptTotalGrossAmountBefore2003'))
                SectionDTrailerExemptTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(
                                            total_eris_start_ups_secD_s10_g)))
                A8BTrailer2009ST.appendChild(
                            SectionDTrailerExemptTotalGrossAmountBefore2003)

                SectionDTrailerNonExemptTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionDTrailerNonExemptTotalGrossAmountAfter2003'))
                SectionDTrailerNonExemptTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(
                            total_gross_amt_qulfy_secD_s10_b)))
                A8BTrailer2009ST.appendChild(
                        SectionDTrailerNonExemptTotalGrossAmountAfter2003)

                SectionDTrailerNonExemptTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionDTrailerNonExemptTotalGrossAmountBefore2003'))
                SectionDTrailerNonExemptTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(
                                            total_gross_amt_qulfy_secD_s10_g)))
                A8BTrailer2009ST.appendChild(
                            SectionDTrailerNonExemptTotalGrossAmountBefore2003)

                SectionDTrailerGainsTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionDTrailerGainsTotalGrossAmountAfter2003'))
                SectionDTrailerGainsTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(
                                            total_gorss_amt_gain_secD_s10_b)))
                A8BTrailer2009ST.appendChild(
                                SectionDTrailerGainsTotalGrossAmountAfter2003)

                SectionDTrailerGainsTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionDTrailerGainsTotalGrossAmountBefore2003'))
                SectionDTrailerGainsTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(
                                            total_gorss_amt_gain_secD_s10_g)))
                A8BTrailer2009ST.appendChild(
                        SectionDTrailerGainsTotalGrossAmountBefore2003)

                SectionETrailerNonExemptGrandTotalGrossAmountAfter2003 = (
                    doc.createElement(
                     'SectionETrailerNonExemptGrandTotalGrossAmountAfter2003'))
                SectionETrailerNonExemptGrandTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(
                            total_grand_total_secE_gross_amt_qulfy_s10_b)))
                A8BTrailer2009ST.appendChild(
                        SectionETrailerNonExemptGrandTotalGrossAmountAfter2003)

                SectionETrailerNonExemptGrandTotalGrossAmountBefore2003 = (
                    doc.createElement(
                     'SectionETrailerNonExemptGrandTotalGrossAmountBefore2003')
                     )
                SectionETrailerNonExemptGrandTotalGrossAmountBefore2003.appendChild(
                        doc.createTextNode(str(
                                total_grand_total_secE_gross_amt_qulfy_s10_g)))
                A8BTrailer2009ST.appendChild(
                    SectionETrailerNonExemptGrandTotalGrossAmountBefore2003)

                SectionETrailerGainsGrandTotalGrossAmountAfter2003 = (
                    doc.createElement(
                        'SectionETrailerGainsGrandTotalGrossAmountAfter2003'))
                SectionETrailerGainsGrandTotalGrossAmountAfter2003.appendChild(
                        doc.createTextNode(str(
                                total_grand_total_secE_gorss_amt_gain_s10_b)))
                A8BTrailer2009ST.appendChild(
                        SectionETrailerGainsGrandTotalGrossAmountAfter2003)

                SectionETrailerGainsGrandTotalGrossAmountBefore2003 = (
                    doc.createElement(
                        'SectionETrailerGainsGrandTotalGrossAmountBefore2003'))
                SectionETrailerGainsGrandTotalGrossAmountBefore2003.appendChild
                (doc.createTextNode(str(
                    total_grand_total_secE_gorss_amt_gain_s10_g)))
                A8BTrailer2009ST.appendChild(
                        SectionETrailerGainsGrandTotalGrossAmountBefore2003)

                Filler = doc.createElement('Filler')
                A8BTrailer2009ST.appendChild(Filler)

                result = doc.toprettyxml(indent='   ')
                res = base64.b64encode(result.encode('UTF-8'))
                module_rec = self.env['binary.appendix8b.xml.file.wizard'
                                      ].create({'name': 'appendix8b.xml',
                                                'appendix8b_xml_file': res})
                return {
                  'name': _('Binary'),
                  'res_id': module_rec.id,
                  "view_mode": 'form',
                  'res_model': 'binary.appendix8b.xml.file.wizard',
                  'type': 'ir.actions.act_window',
                  'target': 'new',
                  'context': context,
                }


class BinaryAppendix8bTextFileWizard(models.TransientModel):
    _name = 'binary.appendix8b.text.file.wizard'
    _description = "Appendix 8B wizard"

    name = fields.Char('Name', default='appendix8b.txt')
    appendix8b_txt_file = fields.Binary('Click On Download Link To \
                        Download File', readonly=True)


class BinaryAppendix8bXMLFileWizard(models.TransientModel):
    _name = 'binary.appendix8b.xml.file.wizard'
    _description = "Appendix 8B XML wizard"

    name = fields.Char('Name', default='appendix8b.xml')
    appendix8b_xml_file = fields.Binary('Click On Download Link To \
                            Download File', readonly=True)
