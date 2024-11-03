
import base64
import tempfile
import time

from datetime import datetime

from dateutil.relativedelta import relativedelta as rv

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF

import xlwt


class CpfPaymentWizard(models.TransientModel):
    _name = 'cpf.payment.wizard'
    _description = "CPF Payment"

    employee_ids = fields.Many2many('hr.employee', 'cpf_employee_rel',
                                    'wizard_id', 'employee_id', 'Employees')
    date_start = fields.Date('Date Start',
                             default=lambda *a: time.strftime('%Y-%m-01'))
    date_stop = fields.Date('Date End',
                            default=lambda *a: str(datetime.now() +
                                                   rv(months=+1,
                                                      day=1,
                                                      days=-1))[:10])

    def get_xls_file(self):
        """Generate xls file.

        The method used to call download file of wizard
        @self : Record Set
        @return: Return of wizard of action in dictionary
        -----------------------------------------------------
        """
        cpf_binary_obj = self.env['cpf.binary.wizard']
        context = dict(self.env.context) if self.env.context else {}
        start_date = self.date_start
        end_date = self.date_stop
        emp_ids = self.employee_ids
        if not emp_ids.ids:
            raise ValidationError(_("Please select employee"))
        if start_date >= end_date:
            raise ValidationError(_(
                'You must be enter start date less than '
                'end date !'))
        for employee in emp_ids:
            if not employee.identification_id:
                raise ValidationError(_(
                    'There is no identification no define '
                    'for %s employee.' % (employee.name)))
        context.update({'employee_id': emp_ids,
                        'date_start': start_date,
                        'date_stop': end_date})
        wbk = xlwt.Workbook()
        sheet = wbk.add_sheet('sheet 1', cell_overwrite_ok=True)
        font = xlwt.Font()
        font.bold = True
        bold_style = xlwt.XFStyle()
        bold_style.font = font
        style = xlwt.easyxf('align: wrap no')
        style.num_format_str = '#,##0.00'
        new_style = xlwt.easyxf('font: bold on; align: wrap no')
        new_style.num_format_str = '#,##0.00'
        company_data = self.env['res.users'].browse(
            context.get('uid')).company_id
        #  static data
        sheet.write(0, 4, company_data.name)
        sheet.write(1, 3, company_data.street or '')
        sheet.write(2, 3, str(company_data and company_data.street2 or ' ') +
                    ' ' + str(company_data and company_data.country_id and
                              company_data.country_id.name or '') + ' ' +
                    str(company_data.zip) or '')
        sheet.write(3, 4, 'Tel : ' + str(company_data.phone or ' '))
        sheet.write(4, 5, 'PAYMENT ADVICE')
        sheet.write(6, 0, 'MANDATORY REF NO. : ' +
                    str(company_data.company_code or ''))
        sheet.write(7, 0, 'VOLUNTARY  REF NO. : ')
        sheet.write(8, 0, company_data.name)
        sheet.write(9, 0, '6 Jalan Kilang #04-00')
        sheet.write(6, 8, 'SUBM MODE')
        sheet.write(7, 8, 'DATE')
        sheet.write(6, 10, ':')
        sheet.write(7, 10, ':')
        sheet.write(6, 11, 'INTERNAL')
        sheet.write(12, 2, 'PART 1 : Payment Details For ')
        sheet.write(13, 8, 'AMOUNT', bold_style)
        sheet.write(13, 10, 'NO. OF EMPLOYEE', bold_style)
        sheet.write(15, 0, '1. CPF Contribution')
        sheet.write(16, 1, 'Mandatory Contribution')
        sheet.write(17, 1, 'Voluntary Contribution')
        sheet.write(18, 0, '2. B/F CPF late Payment interest')
        sheet.write(19, 0, 'Interest charged on last payment')
        sheet.write(20, 0, '3. Late payment interest on CPF Contribution')
        sheet.write(21, 0, '4. Late payment penalty for Foreign Worker Levy')
        sheet.write(22, 0, '5. Foreign Worker Levy')
        sheet.write(23, 0, '6. Skills Development Levy')
        sheet.write(24, 0, '7. Donation to Community Chest')
        sheet.write(25, 0, '8. Mosque Building & Mendaki Fund (MBMF)')
        sheet.write(26, 0, '9. SINDA Fund')
        sheet.write(27, 0, '10. CDAC Fund')
        sheet.write(28, 0, '11. Eurasian Community Fund (EUCF)')
        #  total
        sheet.write(30, 7, 'Total', bold_style)
        #  static data
        sheet.write(31, 4, 'Please fill in cheque details if you are \
                            paying by cheque')
        sheet.write(32, 4, 'BANK')
        sheet.write(32, 5, ':')
        sheet.write(33, 4, 'CHEQUE NO.')
        sheet.write(33, 5, ':')
        sheet.write(34, 4, 'THE EMPLOYER HEREBY GUARANTEES')
        sheet.write(35, 4, 'THE ACCURACY')
        sheet.write(36, 4, 'OF THE CPF RETURNS FOR')
        sheet.write(37, 4, 'AS SHOWN ON THE SUBMITTED DISKETTE.')
        sheet.write(39, 4, 'EMPLOYER\'S AUTHORIZED SIGNATORY')
        sheet.write(42, 0, 'PART 2 : Contribution Details For')
        #  data header
        sheet.write(44, 0, 'Employee Name', bold_style)
        sheet.write(43, 3, 'CPF', bold_style)
        sheet.write(44, 3, 'Account No.', bold_style)
        sheet.write(43, 4, 'Mandatory CPF', bold_style)
        sheet.write(44, 4, 'Contribution', bold_style)
        sheet.write(43, 5, 'Voluntary CPF', bold_style)
        sheet.write(44, 5, 'Contribution', bold_style)
        sheet.write(43, 6, 'Last', bold_style)
        sheet.write(44, 6, 'Contribution', bold_style)
        sheet.write(43, 8, 'MBMF', bold_style)
        sheet.write(44, 8, 'Fund', bold_style)
        sheet.write(43, 9, 'SINDA', bold_style)
        sheet.write(44, 9, 'Fund', bold_style)
        sheet.write(43, 10, 'CDAC', bold_style)
        sheet.write(44, 10, 'Fund', bold_style)
        sheet.write(43, 11, 'ECF', bold_style)
        sheet.write(44, 11, 'Fund', bold_style)
        sheet.write(43, 12, 'SDL', bold_style)
        sheet.write(44, 12, 'Fund', bold_style)
        sheet.write(43, 13, 'Ordinary', bold_style)
        sheet.write(44, 13, 'Wages', bold_style)
        sheet.write(43, 14, 'Additional', bold_style)
        sheet.write(44, 14, 'Wages', bold_style)

        emp_obj = self.env['hr.employee']
        payslip_obj = self.env['hr.payslip']
        hr_contract_obj = self.env['hr.contract']
        category_ids = self.env['hr.employee.category'].search([])
        start_row = raw_no = 45
        start_date = self.date_start.strftime(DSDF) or False
        stop_date = self.date_stop.strftime(DSDF) or False
        month_dict = {'01': 'January', '02': 'February', '03': 'March',
                      '04': 'April', '05': 'May', '06': 'June',
                      '07': 'July', '08': 'August', '09': 'September',
                      '10': 'October', '11': 'November', '12': 'December'}
        period = month_dict.get(start_date.split('-')[1]) + ', ' + \
            start_date.split('-')[0]
        sheet.write(36, 7, period)
        sheet.write(7, 11,
                    datetime.strptime(start_date,
                                      DSDF).strftime('%d-%m-%Y'))
        sheet.write(42, 3, period)
        sheet.write(12, 4, period)
        t_cpfsdl_amount = t_p_cpf_sdl_amount = t_p_fwl_amount = 0.0
        t_p_cpf_amount = t_gross_amount = t_ecf_amount = 0.0
        t_cdac_amount = t_sinda_amount = t_mbmf_amount = t_cpf_amount = 0.0
        total_additional_amount = total_cpfsdl_amount = 0.0
        total_p_cpf_amount = total_gross_amount = total_ecf_amount = 0.0
        total_cdac_amount = total_sinda_amount = total_mbmf_amount = 0.0
        total_cpf_amount = emp_sdl_amount = 0.0
        emp_ecf_amount = emp_fwl_amount = emp_cdac_amount = 0.0
        emp_sinda_amount = emp_mbmf_amount = emp_cpf_amount = 0
        #  no category
        join_date = start_date
        emply_ids = emp_obj.search([('id', 'in', emp_ids.ids),
                                    ('category_ids', '=', False)])
        do_total = False
#        payslip_lst_ids = []
        for emp_record in emply_ids:
            payslip_ids = payslip_obj.search([('employee_id', '=',
                                               emp_record.id),
                                              ('date_from', '>=', start_date),
                                              ('date_from', '<=', stop_date),
                                              ('state', 'in', ['draft', 'done',
                                                               'verify'])])
            previous_date = cpf_binary_obj._default_previous_date(start_date)
            domain = [('employee_id', '=', emp_record.id)]
            previous_payslip_ids = payslip_obj.search(domain,
                                                      order='date_from ASC',
                                                      limit=1)
            if previous_payslip_ids:
                join_date = previous_payslip_ids.date_from
            while(join_date.strftime(DSDF) <= previous_date[0]):
                domain = [('employee_id', '=', emp_record.id),
                          ('date_from', '>=', previous_date[0]),
                          ('date_from', '<=', previous_date[1]),
                          ('state', 'in', ['draft', 'done', 'verify'])]
                previous_payslip_ids = payslip_obj.search(domain)
                if previous_payslip_ids:
                    break
                else:
                    data = previous_date[0]
                    previous_date = cpf_binary_obj._default_previous_date(data)
            if not payslip_ids:
                raise ValidationError(_('There is no payslip details between '
                                        'selected date %s and '
                                        '%s') % (start_date, stop_date))
            additional_amount = cpfsdl_amount = p_cpf_amount = 0.0
            gross_amount = ecf_amount = fwl_amount = cdac_amount = 0.0
            sinda_amount = mbmf_amount = cpf_amount = 0.0
            for payslip_rec in payslip_ids:
                for line in payslip_rec.line_ids:
                    if line.register_id.name == 'CPF':
                        cpf_amount += line.amount
                    if line.register_id.name == 'CPF - MBMF':
                        mbmf_amount += line.amount
                    if line.register_id.name == 'CPF - SINDA':
                        sinda_amount += line.amount
                    if line.register_id.name == 'CPF - CDAC':
                        cdac_amount += line.amount
                    if line.register_id.name == 'CPF - ECF':
                        ecf_amount += line.amount
                    if line.register_id.name == 'CPF - FWL':
                        fwl_amount += line.amount
                        t_p_fwl_amount += line.amount
                    if line.register_id and line.register_id.name == 'BONUS':
                        gross_amount -= line.amount
                    if line.category_id.code == 'GROSS':
                        gross_amount += line.amount
                    if line.code == 'CPFSDL':
                        cpfsdl_amount += line.amount
                        t_p_cpf_sdl_amount += line.amount
                    if line.register_id and line.register_id.name == 'BONUS':
                        additional_amount += line.amount
            if not gross_amount:
                continue
            if not cpf_amount and not mbmf_amount and not sinda_amount and \
               not cdac_amount and not ecf_amount and not cpfsdl_amount:
                continue
            sheet.write(raw_no, 0, payslip_rec.employee_id and
                        payslip_rec.employee_id.name or '')
            sheet.write(raw_no, 3, payslip_rec.employee_id and
                        payslip_rec.employee_id.identification_id or '')
            #  previous cpf
            if previous_payslip_ids:
                if payslip_rec.date_from != payslip_rec.date_from:
                    for previous_line in previous_payslip_ids.line_ids:
                        if previous_line.register_id.name == 'CPF':
                            p_cpf_amount += previous_line.amount
            #  Counts Employee
            if fwl_amount:
                emp_fwl_amount += 1
            if cpf_amount != 0:
                emp_cpf_amount += 1
            if mbmf_amount != 0:
                emp_mbmf_amount += 1
            if sinda_amount != 0:
                emp_sinda_amount += 1
            if cdac_amount != 0:
                emp_cdac_amount += 1
            if ecf_amount != 0:
                emp_ecf_amount += 1
            if cpfsdl_amount != 0:
                emp_sdl_amount += 1

            #  writes in xls file
            do_total = True
            sheet.write(raw_no, 4, round(cpf_amount or 0.00, 2), style)
            t_cpf_amount += cpf_amount
            total_cpf_amount += cpf_amount
            sheet.write(raw_no, 5, round(0.00, 2), style)
            sheet.write(raw_no, 8, round(mbmf_amount or 0.00, 2), style)
            t_mbmf_amount += mbmf_amount
            total_mbmf_amount += mbmf_amount
            sheet.write(raw_no, 9, round(sinda_amount or 0.00, 2), style)
            t_sinda_amount += sinda_amount
            total_sinda_amount += sinda_amount
            sheet.write(raw_no, 10, round(cdac_amount or 0.00, 2), style)
            t_cdac_amount += cdac_amount
            total_cdac_amount += cdac_amount
            sheet.write(raw_no, 11, round(ecf_amount or 0.00, 2), style)
            t_ecf_amount += ecf_amount
            total_ecf_amount += ecf_amount
            sheet.write(raw_no, 12, round(cpfsdl_amount or 0.00, 2), style)
            total_cpfsdl_amount += cpfsdl_amount
            t_cpfsdl_amount += cpfsdl_amount
            sheet.write(raw_no, 13, round(gross_amount or 0.00, 2), style)
            sheet.write(raw_no, 14, round(additional_amount or 0.00, 2), style)
            t_gross_amount += gross_amount
            total_gross_amount += gross_amount
            total_additional_amount += additional_amount
            sheet.write(raw_no, 6, round(p_cpf_amount or 0.00, 2), style)
            t_p_cpf_amount += p_cpf_amount
            total_p_cpf_amount += p_cpf_amount
            #  sheet.write(raw_no, 6, 0.00, style)
            domain = [('employee_id', '=', emp_record.id), '|',
                      ('date_end', '>=', payslip_rec.date_from),
                      ('date_end', '=', False)]
            contract_id = hr_contract_obj.search(domain)
            emp_domain = [('employee_id', '=', emp_record.id),
                          ('date_end', '<=', payslip_rec.date_from)]
            old_contract_id = hr_contract_obj.search(emp_domain)
            for contract in contract_id:
                if not payslip_rec.employee_id.active:
                    sheet.write(raw_no, 7, 'Left')
                elif contract.date_start >= payslip_rec.date_from and \
                        not old_contract_id.ids:
                    sheet.write(raw_no, 7, 'New Join')
                else:
                    sheet.write(raw_no, 7, 'Existing')
            raw_no += 1
        if do_total:
            raw_no = raw_no + 1
            sheet.write(raw_no, 0, 'Total :', bold_style)
            start_row = start_row + 1

            #  cpf
            sheet.write(raw_no, 4, total_cpf_amount, new_style)
            #  v_cpf
            sheet.write(raw_no, 5, round(0.00, 2), style)
            #  p_cpf
            sheet.write(raw_no, 6, round(total_p_cpf_amount or 0.00, 2),
                        new_style)

            #  MBPF
            sheet.write(raw_no, 8, round(total_mbmf_amount or 0.00, 2),
                        new_style)
            #  SINDA
            sheet.write(raw_no, 9, round(total_sinda_amount or 0.00, 2),
                        new_style)
            #  CDAC
            sheet.write(raw_no, 10, round(total_cdac_amount or 0.00, 2),
                        new_style)
            #  ECF
            sheet.write(raw_no, 11, round(total_ecf_amount or 0.00, 2),
                        new_style)
            #  CPFSDL
            sheet.write(raw_no, 12, round(total_cpfsdl_amount or 0.00, 2),
                        new_style)
            #  O_WAGE
            sheet.write(raw_no, 13, round(total_gross_amount or 0.00, 2),
                        new_style)
            sheet.write(raw_no, 14, round(total_additional_amount, 2), style)

        #  emp by category
        start_row = raw_no = raw_no + 2

        emp_rec = emp_obj.search([('id', 'in', emp_ids.ids),
                                  ('category_ids', '!=', False)])
        for category in category_ids:
            emp_flag = False
            total_additional_amount = total_cpfsdl_amount = 0.0
            total_p_cpf_amount = total_gross_amount = total_ecf_amount = 0.0
            total_cdac_amount = total_sinda_amount = total_mbmf_amount = 0.0
            total_cpf_amount = 0.0
            for emp_record in emp_rec:
                if (emp_record.category_ids and
                    emp_record.category_ids[0].id != category.id) or \
                        not emp_record.category_ids:
                    continue
                payslip_ids = payslip_obj.search([
                    ('employee_id', '=', emp_record.id),
                    ('date_from', '>=', start_date),
                    ('date_from', '<=', stop_date),
                    ('state', 'in', ['draft', 'done', 'verify'])])

                s_date = start_date
                previous_date = cpf_binary_obj._default_previous_date(s_date)
                previous_payslip_ids = payslip_obj.search([
                    ('employee_id', '=', emp_record.id)
                ], order=('date_from ASC'), limit=1)
                if previous_payslip_ids:
                    join_date = previous_payslip_ids.date_from.strftime(DSDF)
                while(join_date <= previous_date[0]):
                    domain = [('employee_id', '=', emp_record.id),
                              ('date_from', '>=', previous_date[0]),
                              ('date_from', '<=', previous_date[1]),
                              ('state', 'in', ['draft', 'done', 'verify'])]
                    previous_payslip_ids = payslip_obj.search(domain)
                    if previous_payslip_ids:
                        break
                    else:
                        data = previous_date[0]
                        date = cpf_binary_obj._default_previous_date(data)
                        previous_date = date
                if not payslip_ids:
                    raise ValidationError(_(
                        'There is no payslip details '
                        'between selected date %s and %s') % (start_date,
                                                              stop_date))
                additional_amount = cpfsdl_amount = p_cpf_amount = 0.0
                gross_amount = ecf_amount = fwl_amount = cdac_amount = 0.0
                sinda_amount = mbmf_amount = cpf_amount = 0.0
                for payslip_rec in payslip_ids:
                    for line in payslip_rec.line_ids:
                        if line.register_id.name == 'CPF':
                            cpf_amount += line.amount
                        if line.register_id.name == 'CPF - MBMF':
                            mbmf_amount += line.amount
                        if line.register_id.name == 'CPF - SINDA':
                            sinda_amount += line.amount
                        if line.register_id.name == 'CPF - CDAC':
                            cdac_amount += line.amount
                        if line.register_id.name == 'CPF - ECF':
                            ecf_amount += line.amount
                        if line.register_id.name == 'CPF - FWL':
                            fwl_amount += line.amount
                            t_p_fwl_amount += line.amount
                        if line.register_id and \
                                line.register_id.name == 'BONUS':
                            gross_amount -= line.amount
                        if line.category_id.code == 'GROSS':
                            gross_amount += line.amount
                        if line.code == 'CPFSDL':
                            cpfsdl_amount += line.amount
                            t_p_cpf_sdl_amount += line.amount
                        if line.register_id and \
                                line.register_id.name == 'BONUS':
                            additional_amount += line.amount

                if not gross_amount:
                    continue
                if not cpf_amount and not mbmf_amount and not sinda_amount \
                        and not cdac_amount and not ecf_amount and \
                        not cpfsdl_amount:
                    t_p_fwl_amount -= fwl_amount
                    continue
                sheet.write(raw_no, 0, payslip_rec.employee_id and
                            payslip_rec.employee_id.name or '')
                sheet.write(raw_no, 3, payslip_rec.employee_id and
                            payslip_rec.employee_id.identification_id or '')
                #  previous cpf
                if previous_payslip_ids:
                    if payslip_rec.date_from != payslip_rec.date_from:
                        for previous_line in previous_payslip_ids.line_ids:
                            if previous_line.register_id.name == 'CPF':
                                p_cpf_amount += previous_line.amount

                #  Counts Employee
                if fwl_amount:
                    emp_fwl_amount += 1
                if cpf_amount != 0:
                    emp_cpf_amount += 1
                if mbmf_amount != 0:
                    emp_mbmf_amount += 1
                if sinda_amount != 0:
                    emp_sinda_amount += 1
                if cdac_amount != 0:
                    emp_cdac_amount += 1
                if ecf_amount != 0:
                    emp_ecf_amount += 1
                if cpfsdl_amount != 0:
                    emp_sdl_amount += 1

                #  writes in xls file
                emp_flag = True
                sheet.write(raw_no, 4, round(cpf_amount or 0.00, 2), style)
                t_cpf_amount += cpf_amount
                total_cpf_amount += cpf_amount
                sheet.write(raw_no, 5, round(0.00, 2), style)
                sheet.write(raw_no, 8, round(mbmf_amount or 0.00, 2), style)
                t_mbmf_amount += mbmf_amount
                total_mbmf_amount += mbmf_amount
                sheet.write(raw_no, 9, round(sinda_amount or 0.00, 2), style)
                t_sinda_amount += sinda_amount
                total_sinda_amount += sinda_amount
                sheet.write(raw_no, 10, round(cdac_amount or 0.00, 2), style)
                t_cdac_amount += cdac_amount
                total_cdac_amount += cdac_amount
                sheet.write(raw_no, 11, round(ecf_amount or 0.00, 2), style)
                t_ecf_amount += ecf_amount
                total_ecf_amount += ecf_amount
                sheet.write(raw_no, 12, round(cpfsdl_amount or 0.00, 2), style)
                t_cpfsdl_amount += cpfsdl_amount
                total_cpfsdl_amount += cpfsdl_amount
                sheet.write(raw_no, 13, round(gross_amount or 0.00, 2), style)
                sheet.write(raw_no, 14, round(additional_amount or 0.00, 2),
                            style)
                t_gross_amount += gross_amount
                total_gross_amount += gross_amount
                sheet.write(raw_no, 6, round(p_cpf_amount or 0.00, 2), style)
                t_p_cpf_amount += p_cpf_amount
                total_p_cpf_amount += p_cpf_amount
                total_additional_amount += additional_amount

                #  sheet.write(raw_no, 6, 0.00, style)
                domain = [('employee_id', '=', emp_record.id), '|',
                          ('date_end', '>=', payslip_rec.date_from),
                          ('date_end', '=', False)]
                contract_id = hr_contract_obj.search(domain)
                domain1 = [('employee_id', '=', emp_record.id),
                           ('date_end', '<=', payslip_rec.date_from)]
                old_contract_id = hr_contract_obj.search(domain1)
                for contract in contract_id:
                    if not payslip_rec.employee_id.active:
                        sheet.write(raw_no, 7, 'Left')
                    elif contract.date_start >= payslip_rec.date_from and \
                            not old_contract_id.ids:
                        sheet.write(raw_no, 7, 'New Join')
                    else:
                        sheet.write(raw_no, 7, 'Existing')
                raw_no += 1

            if emp_flag:
                raw_no = raw_no + 1
                sheet.write(raw_no, 0, 'Total %s :' % category.name,
                            bold_style)
                start_row = start_row + 1

                #  cpf
                sheet.write(raw_no, 4, round(total_cpf_amount or 0.00, 2),
                            new_style)
                #  v_cpf
                sheet.write(raw_no, 5, round(0.00, 2), style)
                #  p_cpf
                sheet.write(raw_no, 6, round(total_p_cpf_amount or 0.00, 2),
                            new_style)

                #  MBPF
                sheet.write(raw_no, 8, round(total_mbmf_amount or 0.00, 2),
                            new_style)
                #  SINDA
                sheet.write(raw_no, 9, round(total_sinda_amount or 0.00, 2),
                            new_style)
                #  CDAC
                sheet.write(raw_no, 10, round(total_cdac_amount or 0.00, 2),
                            new_style)
                #  ECF
                sheet.write(raw_no, 11, round(total_ecf_amount or 0.00, 2),
                            new_style)
                #  ECF
                sheet.write(raw_no, 12, round(total_cpfsdl_amount or 0.00, 2),
                            new_style)
                #  O_WAGE
                sheet.write(raw_no, 13, round(total_gross_amount or 0.00, 2),
                            new_style)
                sheet.write(raw_no, 14, round(total_additional_amount, 2),
                            style)

                raw_no = raw_no + 2
                start_row = start_row + 3
        #  amount columns
        #  cpf
        sheet.write(16, 8, round(t_cpf_amount or 0.00, 2), style)
        sheet.write(17, 8, 0.00, style)
        sheet.write(18, 8, 0.00, style)
        sheet.write(19, 8, 0.00, style)
        sheet.write(20, 8, 0.00, style)
        sheet.write(21, 8, 0.00, style)
        sheet.write(22, 8, t_p_fwl_amount, style)
        sheet.write(23, 8, t_p_cpf_sdl_amount, style)
        sheet.write(24, 8, 0.00, style)
        #  MBPF
        sheet.write(25, 8, round(t_mbmf_amount or 0.00, 2), style)
        #  SINDA
        sheet.write(26, 8, round(t_sinda_amount or 0.00, 2), style)
        #  CDAC
        sheet.write(27, 8, round(t_cdac_amount or 0.00, 2), style)
        #  ECF
        sheet.write(28, 8, round(t_ecf_amount or 0.00, 2), style)

        #  no of employee
        sheet.write(16, 10, emp_cpf_amount)
        sheet.write(17, 10, 0)
        sheet.write(18, 10, 0)
        sheet.write(19, 10, 0)
        sheet.write(20, 10, 0)
        sheet.write(21, 10, 0)
        sheet.write(22, 10, emp_fwl_amount)
        sheet.write(23, 10, emp_sdl_amount)
        sheet.write(24, 10, 0)
        sheet.write(25, 10, emp_mbmf_amount)
        sheet.write(26, 10, emp_sinda_amount)
        sheet.write(27, 10, emp_cdac_amount)
        sheet.write(28, 10, emp_ecf_amount)

        #  Total
        sheet.write(30, 8, xlwt.Formula("sum(I17:I29)"), new_style)

        wbk.save(tempfile.gettempdir() + "/payslip.xls")

        file = open(tempfile.gettempdir() + "/payslip.xls", "rb")
        out = file.read()
        file.close()
        res = base64.b64encode(out)

        if not start_date and stop_date:
            return ''
        end_date = datetime.strptime(stop_date, DSDF)
        monthyear = end_date.strftime('%m%Y')
        file_name = "Payment Advice " + monthyear + '.xls'

        module_rec = cpf_binary_obj.create({'name': file_name,
                                            'xls_file': res})
        return {'name': _('Payment Advice Report'),
                'res_id': module_rec.id,
                "view_mode": 'form',
                'res_model': 'cpf.binary.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context}


class CpfBinaryWizard(models.TransientModel):
    _name = 'cpf.binary.wizard'
    _description = "CPF Wiz"

    name = fields.Char('Name')
    xls_file = fields.Binary('Click On Download Link To Download Xls File',
                             readonly=True)

    @api.model
    def _default_previous_date(self, date):
        date_obj = datetime.strptime(date, DSDF)
        date_obj = date_obj - rv(months=1)
        return [str(date_obj.year) + "-" + str(date_obj.month) + "-01",
                (date_obj + rv(months=+1, day=1,
                               days=-1)).strftime('%Y-%m-%d')]

    def action_back(self):
        """Action back to return back."""
        return {'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'cpf.payment.wizard',
                'target': 'new'}
