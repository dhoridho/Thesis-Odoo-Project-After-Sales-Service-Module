
import base64
import tempfile
import time

from datetime import datetime

from dateutil.relativedelta import relativedelta as rv

from odoo import _, fields, models
from odoo import tools
from odoo.exceptions import ValidationError


class CpfRuleTextFile(models.TransientModel):
    _name = 'cpf.rule.text.file'
    _description = "Cpf Rule Text File"

    employee_ids = fields.Many2many('hr.employee',
                                    'hr_employe_cpf_text_rel', 'cpf_emp_id',
                                    'employee_id', 'Employee')
    include_fwl = fields.Boolean('INCLUDE FWL')
    date_start = fields.Date('Date Start',
                             default=lambda *a: time.strftime('%Y-%m-01'))
    date_stop = fields.Date('Date End',
                            default=lambda *a: str(datetime.now() +
                                                   rv(months=+1, day=1,
                                                      days=-1))[:10])

    def download_cpf_txt_file(self):
        """Download CPF txt file.

        The method used to call download file of wizard
        @self : Record Set
        @return: Return of wizard of action in dictionary
        --------------------------------------------------------
        """
        context = self.env.context
        hr_contract_obj = self.env['hr.contract']
        # cpf_data_wiz = self.read([])
        # data = {}
        # if cpf_data_wiz:
        #     data = cpf_data_wiz[0]
        start_date = self.date_start
        end_date = self.date_stop
        emp_ids = self.employee_ids
        if len(emp_ids) == 0:
            raise ValidationError(_("Please select employee"))
        if start_date >= end_date:
            raise ValidationError(
                _("You must be enter start date less than end date !"))
        for employee in emp_ids:
            emp_name = employee and employee.name or ''
            if not employee.identification_id:
                raise ValidationError(_(
                    'There is no identification no define for %s '
                    'employee.' % (emp_name)))
        payslip_ids = self.env['hr.payslip'].search([
            ('date_from', '>=', start_date),
            ('date_from', '<=', end_date),
            ('employee_id', 'in', emp_ids.ids),
            ('state', 'in', ['draft', 'done', 'verify'])])
        if not payslip_ids.ids:
            raise ValidationError(
                _('There is no payslip details available between selected '
                    'date %s and %s') % (start_date, end_date))
        total_record = 0.0
        summary_record_amount_total = 0.0
        include_fwl = self.include_fwl
        current_date = datetime.today()
        year_month_date = current_date.strftime('%Y%m%d')
        hour_minute_second = current_date.strftime('%H%M%S')
        year_month = start_date.strftime('%Y%m')
        tgz_tmp_filename = tempfile.mktemp('.' + "txt")
        tmp_file = False
        company_data = self.env.user.company_id
        try:
            tmp_file = open(tgz_tmp_filename, "w")
            header_record = 'F'.ljust(1) + \
                            ' '.ljust(1) + \
                            str(company_data.company_code)[:10].ljust(10) + \
                            'PTE'.ljust(3) + \
                            '01'.ljust(2) + \
                            ' '.ljust(1) + \
                            '01'.ljust(2) + \
                            year_month_date.ljust(8) + \
                            hour_minute_second.ljust(6) + \
                            'FTP.DTL'.ljust(13) + \
                            ' '.ljust(103) + "\r\n"
            tmp_file.write(header_record)

            summary_total_employee = 0.0
            for payslip in payslip_ids:
                summary_total_employee += 1
            summary_total_employee = '%0*d' % (7, summary_total_employee)

            sdl_salary_rule_code = fwl_salary_rule_code = ''
            ecf_salary_rule_code = cdac_salary_rule_code = ''
            sinda_salary_rule_code = mbmf_salary_rule_code = ''
            cpf_salary_rule_code = ''
            sdl_amount = fwl_amount = ecf_amount = cdac_amount = 0.0
            sinda_amount = mbmf_amount = cpf_amount = 0.0
            cpf_emp = mbmf_emp = sinda_emp = cdac_emp = ecf_emp = 0
            fwl_emp = sdl_emp = 0
            for payslip in payslip_ids:
                count_mbmf_emp = count_sinda_emp = count_cdac_emp = True
                count_ecf_emp = count_fwl_emp = True
                for line in payslip.line_ids:
                    if line.register_id.name == 'CPF':
                        cpf_salary_rule_code = '01'
                        cpf_amount += line.amount
                    elif line.register_id.name == 'CPF - MBMF':
                        mbmf_salary_rule_code = '02'
                        mbmf_amount += line.amount
                        if count_mbmf_emp:
                            mbmf_emp += 1
                            count_mbmf_emp = False
                    elif line.register_id.name == 'CPF - SINDA':
                        sinda_salary_rule_code = '03'
                        sinda_amount += line.amount
                        if count_sinda_emp:
                            sinda_emp += 1
                            count_sinda_emp = False
                    elif line.register_id.name == 'CPF - CDAC':
                        cdac_salary_rule_code = '04'
                        cdac_amount += line.amount
                        if count_cdac_emp:
                            cdac_emp += 1
                            count_cdac_emp = False
                    elif line.register_id.name == 'CPF - ECF':
                        ecf_salary_rule_code = '05'
                        ecf_amount += line.amount
                        if count_ecf_emp:
                            ecf_emp += 1
                            count_ecf_emp = False
                    elif line.register_id.name == 'CPF - FWL':
                        fwl_salary_rule_code = '08'
                        fwl_amount += line.amount
                        if count_fwl_emp:
                            fwl_emp += 1
                            count_fwl_emp = False
                    elif line.register_id.name == 'CPF - SDL':
                        sdl_salary_rule_code = '11'
                        sdl_amount += line.amount
                    #  else:
                        #  salary_rule_code = ''
                        #  amount = 0.0

            if cpf_salary_rule_code and cpf_amount:
                total_record += 1
                cpf_amount = cpf_amount * 100
                new_amt = int(round(cpf_amount))
                if new_amt < 0:
                    new_amt = new_amt * -1
                final_amt = '%0*d' % (12, new_amt)
                summary_record_amount_total += float(final_amt)
                cpf_emp = '%0*d' % (7, 0)
                summary_record = 'F'.ljust(1) + \
                    '0'.ljust(1) + \
                    str(company_data.company_code)[:10].ljust(10) + \
                    'PTE'.ljust(3) + \
                    '01'.ljust(2) + \
                    ' '.ljust(1) + \
                    '01'.ljust(2) + \
                    str(year_month).ljust(6) + \
                    cpf_salary_rule_code.ljust(2) + \
                    str(final_amt).ljust(12) + \
                    str(cpf_emp).ljust(7) + \
                    ' '.ljust(103) + "\r\n"
                tmp_file.write(summary_record)

            if mbmf_salary_rule_code and mbmf_amount and mbmf_emp:
                total_record += 1
                mbmf_amount = mbmf_amount * 100
                new_amt = int(round(mbmf_amount))
                if new_amt < 0:
                    new_amt = new_amt * -1
                final_amt = '%0*d' % (12, new_amt)
                summary_record_amount_total += float(final_amt)
                mbmf_emp = '%0*d' % (7, mbmf_emp)
                summary_record = 'F'.ljust(1) + \
                    '0'.ljust(1) + \
                    str(company_data.company_code)[:10].ljust(10) + \
                    'PTE'.ljust(3) + \
                    '01'.ljust(2) + \
                    ' '.ljust(1) + \
                    '01'.ljust(2) + \
                    str(year_month).ljust(6) + \
                    mbmf_salary_rule_code.ljust(2) + \
                    str(final_amt).ljust(12) + \
                    str(mbmf_emp).ljust(7) + \
                    ' '.ljust(103) + "\r\n"
                tmp_file.write(summary_record)

            if sinda_salary_rule_code and sinda_amount and sinda_emp:
                total_record += 1
                sinda_amount = sinda_amount * 100
                new_amt = int(round(sinda_amount))
                if new_amt < 0:
                    new_amt = new_amt * -1
                final_amt = '%0*d' % (12, new_amt)
                summary_record_amount_total += float(final_amt)
                sinda_emp = '%0*d' % (7, sinda_emp)
                summary_record = 'F'.ljust(1) + \
                    '0'.ljust(1) + \
                    str(company_data.company_code)[:10].ljust(10) + \
                    'PTE'.ljust(3) + \
                    '01'.ljust(2) + \
                    ' '.ljust(1) + \
                    '01'.ljust(2) + \
                    str(year_month).ljust(6) + \
                    sinda_salary_rule_code.ljust(2) + \
                    str(final_amt).ljust(12) + \
                    str(sinda_emp).ljust(7) + \
                    ' '.ljust(103) + "\r\n"
                tmp_file.write(summary_record)

            if cdac_salary_rule_code and cdac_amount and cdac_emp:
                total_record += 1
                cdac_amount = cdac_amount * 100
                new_amt = int(round(cdac_amount))
                if new_amt < 0:
                    new_amt = new_amt * -1
                final_amt = '%0*d' % (12, new_amt)
                summary_record_amount_total += float(final_amt)
                cdac_emp = '%0*d' % (7, cdac_emp)
                summary_record = 'F'.ljust(1) + \
                    '0'.ljust(1) + \
                    str(company_data.company_code)[:10].ljust(10) + \
                    'PTE'.ljust(3) + \
                    '01'.ljust(2) + \
                    ' '.ljust(1) + \
                    '01'.ljust(2) + \
                    str(year_month).ljust(6) + \
                    cdac_salary_rule_code.ljust(2) + \
                    str(final_amt).ljust(12) + \
                    str(cdac_emp).ljust(7) + \
                    ' '.ljust(103) + "\r\n"
                tmp_file.write(summary_record)

            if ecf_salary_rule_code and ecf_amount and ecf_emp:
                total_record += 1
                ecf_amount = ecf_amount * 100
                new_amt = int(round(ecf_amount))
                if new_amt < 0:
                    new_amt = new_amt * -1
                final_amt = '%0*d' % (12, new_amt)
                summary_record_amount_total += float(final_amt)
                ecf_emp = '%0*d' % (7, ecf_emp)
                summary_record = 'F'.ljust(1) + \
                    '0'.ljust(1) + \
                    str(company_data.company_code)[:10].ljust(10) + \
                    'PTE'.ljust(3) + \
                    '01'.ljust(2) + \
                    ' '.ljust(1) + \
                    '01'.ljust(2) + \
                    str(year_month).ljust(6) + \
                    ecf_salary_rule_code.ljust(2) + \
                    str(final_amt).ljust(12) + \
                    str(ecf_emp).ljust(7) + \
                    ' '.ljust(103) + "\r\n"
                tmp_file.write(summary_record)
            if include_fwl and fwl_salary_rule_code and fwl_amount and fwl_emp:
                total_record += 1
                fwl_amount = fwl_amount * 100
                new_amt = int(round(fwl_amount))
                if new_amt < 0:
                    new_amt = new_amt * -1
                final_amt = '%0*d' % (12, new_amt)
                summary_record_amount_total += float(final_amt)
                fwl_emp = '%0*d' % (7, fwl_emp)
                summary_record = 'F'.ljust(1) + \
                    '0'.ljust(1) + \
                    str(company_data.company_code)[:10].ljust(10) + \
                    'PTE'.ljust(3) + \
                    '01'.ljust(2) + \
                    ' '.ljust(1) + \
                    '01'.ljust(2) + \
                    str(year_month).ljust(6) + \
                    fwl_salary_rule_code.ljust(2) + \
                    str(final_amt).ljust(12) + \
                    str(fwl_emp).ljust(7) + \
                    ' '.ljust(103) + "\r\n"
                tmp_file.write(summary_record)

            if sdl_salary_rule_code and sdl_amount:
                total_record += 1
                sdl_amount = sdl_amount * 100
                new_amt = int(round(sdl_amount))
                if new_amt < 0:
                    new_amt = new_amt * -1
                final_amt = '%0*d' % (12, new_amt)
                summary_record_amount_total += float(final_amt)
                sdl_emp = '%0*d' % (7, 0)
                summary_record = 'F'.ljust(1) + \
                    '0'.ljust(1) + \
                    str(company_data.company_code)[:10].ljust(10) + \
                    'PTE'.ljust(3) + \
                    '01'.ljust(2) + \
                    ' '.ljust(1) + \
                    '01'.ljust(2) + \
                    str(year_month).ljust(6) + \
                    sdl_salary_rule_code.ljust(2) + \
                    str(final_amt).ljust(12) + \
                    str(sdl_emp).ljust(7) + \
                    ' '.ljust(103) + "\r\n"
                tmp_file.write(summary_record)
            for payslip in payslip_ids:
                employee_status = ''
                domain = [('employee_id', '=', payslip.employee_id.id), '|',
                          ('date_end', '>=', payslip.date_from),
                          ('date_end', '=', False)]
                contract_id = hr_contract_obj.search(domain)
                domain1 = [('employee_id', '=', payslip.employee_id.id),
                           ('date_end', '<=', payslip.date_from)]
                old_contract_id = hr_contract_obj.search(domain1)
                for contract in contract_id:
                    if not payslip.employee_id.active:
                        employee_status = 'L'
                    elif contract.date_start >= payslip.date_from and not \
                            old_contract_id:
                        employee_status = 'N'
                    else:
                        employee_status = 'E'
                #  salary_rule_code = ''
                #  amount = gross = 0.0
                sdl_salary_rule_code = fwl_salary_rule_code = ''
                ecf_salary_rule_code = cdac_salary_rule_code = ''
                sinda_salary_rule_code = mbmf_salary_rule_code = ''
                cpf_salary_rule_code = ''
                sdl_amount = fwl_amount = ecf_amount = cdac_amount = 0.0
                sinda_amount = mbmf_amount = cpf_amount = 0.0
                for line in payslip.line_ids:
                    if line.register_id.name == 'CPF':
                        cpf_salary_rule_code = '01'
                        cpf_amount += line.amount
                    elif line.register_id.name == 'CPF - MBMF':
                        mbmf_salary_rule_code = '02'
                        mbmf_amount += line.amount
                    elif line.register_id.name == 'CPF - SINDA':
                        sinda_salary_rule_code = '03'
                        sinda_amount += line.amount
                    elif line.register_id.name == 'CPF - CDAC':
                        cdac_salary_rule_code = '04'
                        cdac_amount += line.amount
                    elif line.register_id.name == 'CPF - ECF':
                        ecf_salary_rule_code = '05'
                        ecf_amount += line.amount
                    elif line.register_id.name == 'CPF - FWL':
                        fwl_salary_rule_code = '08'
                        fwl_amount += line.amount

                    if line.salary_rule_id.code in ['GROSS']:
                        gross = line.amount
                        gross = gross * 100
                        new_gross = int(round(gross))
                        if new_gross < 0:
                            new_gross = new_gross * -1
                        final_gross = '%0*d' % (10, new_gross)
                identificaiton_id = ''
                if payslip.employee_id.identification_id:
                    if payslip.employee_id.identification_id.__len__() <= 9:
                        identificaiton_id += tools.ustr(
                            payslip.employee_id.identification_id.ljust(9))
                    else:
                        identi = payslip.employee_id.identification_id[0:9]
                        identificaiton_id += tools.ustr(
                            identi.ljust(9))
                else:
                    identificaiton_id = ' '.ljust(9)
                employee_name_text = ''
                if payslip.employee_id.name:
                    if payslip.employee_id.name.__len__() <= 22:
                        employee_name_text += tools.ustr(
                            payslip.employee_id.name.ljust(22))
                    else:
                        employee_name_text += tools.ustr(
                            payslip.employee_id.name[0:22].ljust(22))
                else:
                    employee_name_text = ' '.ljust(22)
                if cpf_salary_rule_code and cpf_amount:
                    total_record += 1
                    cpf_amount = cpf_amount * 100
                    new_amt = int(round(cpf_amount))
                    if new_amt < 0:
                        new_amt = new_amt * -1
                    final_amt = '%0*d' % (12, new_amt)
                    cmpny_code = str(company_data.company_code)[:10]
                    detail_record = 'F'.ljust(1) + \
                                    '1'.ljust(1) + \
                                    cmpny_code.ljust(10) + \
                                    'PTE'.ljust(3) + \
                                    '01'.ljust(2) + \
                                    ' '.ljust(1) + \
                                    '01'.ljust(2) + \
                                    str(year_month).ljust(6) + \
                                    cpf_salary_rule_code.ljust(2) + \
                                    identificaiton_id + \
                                    str(final_amt).ljust(12) + \
                                    final_gross.ljust(10) + \
                                    '0000000000'.ljust(10) + \
                                    employee_status.ljust(1) + \
                                    employee_name_text + \
                                    ' '.ljust(58) + "\r\n"
                    tmp_file.write(detail_record)

                if mbmf_salary_rule_code and mbmf_amount:
                    total_record += 1
                    mbmf_amount = mbmf_amount * 100
                    new_amt = int(round(mbmf_amount))
                    if new_amt < 0:
                        new_amt = new_amt * -1
                    final_amt = '%0*d' % (12, new_amt)
                    cmpny_code = str(company_data.company_code)[:10]
                    detail_record = 'F'.ljust(1) + \
                                    '1'.ljust(1) + \
                                    cmpny_code.ljust(10) + \
                                    'PTE'.ljust(3) + \
                                    '01'.ljust(2) + \
                                    ' '.ljust(1) + \
                                    '01'.ljust(2) + \
                                    str(year_month).ljust(6) + \
                                    mbmf_salary_rule_code.ljust(2) + \
                                    identificaiton_id + \
                                    str(final_amt).ljust(12) + \
                                    final_gross.ljust(10) + \
                                    '0000000000'.ljust(10) + \
                                    ' ' + \
                                    employee_name_text + \
                                    ' '.ljust(58) + "\r\n"
                    tmp_file.write(detail_record)

                if sinda_salary_rule_code and sinda_amount:
                    total_record += 1
                    sinda_amount = sinda_amount * 100
                    new_amt = int(round(sinda_amount))
                    if new_amt < 0:
                        new_amt = new_amt * -1
                    final_amt = '%0*d' % (12, new_amt)
                    cmpny_code = str(company_data.company_code)[:10]
                    detail_record = 'F'.ljust(1) + \
                                    '1'.ljust(1) + \
                                    cmpny_code.ljust(10) + \
                                    'PTE'.ljust(3) + \
                                    '01'.ljust(2) + \
                                    ' '.ljust(1) + \
                                    '01'.ljust(2) + \
                                    str(year_month).ljust(6) + \
                                    sinda_salary_rule_code.ljust(2) + \
                                    identificaiton_id + \
                                    str(final_amt).ljust(12) + \
                                    final_gross.ljust(10) + \
                                    '0000000000'.ljust(10) + \
                                    ' ' + \
                                    employee_name_text + \
                                    ' '.ljust(58) + "\r\n"
                    tmp_file.write(detail_record)

                if cdac_salary_rule_code and cdac_amount:
                    total_record += 1
                    cdac_amount = cdac_amount * 100
                    new_amt = int(round(cdac_amount))
                    if new_amt < 0:
                        new_amt = new_amt * -1
                    final_amt = '%0*d' % (12, new_amt)
                    cmpny_code = str(company_data.company_code)[:10]
                    detail_record = 'F'.ljust(1) + \
                                    '1'.ljust(1) + \
                                    cmpny_code.ljust(10) + \
                                    'PTE'.ljust(3) + \
                                    '01'.ljust(2) + \
                                    ' '.ljust(1) + \
                                    '01'.ljust(2) + \
                                    str(year_month).ljust(6) + \
                                    cdac_salary_rule_code.ljust(2) + \
                                    identificaiton_id + \
                                    str(final_amt).ljust(12) + \
                                    final_gross.ljust(10) + \
                                    '0000000000'.ljust(10) + \
                                    ' ' + \
                                    employee_name_text + \
                                    ' '.ljust(58) + "\r\n"
                    tmp_file.write(detail_record)

                if ecf_salary_rule_code and ecf_amount:
                    total_record += 1
                    ecf_amount = ecf_amount * 100
                    new_amt = int(round(ecf_amount))
                    if new_amt < 0:
                        new_amt = new_amt * -1
                    final_amt = '%0*d' % (12, new_amt)
                    cmpny_code = str(company_data.company_code)[:10]
                    detail_record = 'F'.ljust(1) + \
                                    '1'.ljust(1) + \
                                    cmpny_code.ljust(10) + \
                                    'PTE'.ljust(3) + \
                                    '01'.ljust(2) + \
                                    ' '.ljust(1) + \
                                    '01'.ljust(2) + \
                                    str(year_month).ljust(6) + \
                                    ecf_salary_rule_code.ljust(2) + \
                                    identificaiton_id + \
                                    str(final_amt).ljust(12) + \
                                    final_gross.ljust(10) + \
                                    '0000000000'.ljust(10) + \
                                    ' ' + \
                                    employee_name_text + \
                                    ' '.ljust(58) + "\r\n"
                    tmp_file.write(detail_record)

                if include_fwl and fwl_salary_rule_code and fwl_amount:
                    total_record += 1
                    fwl_amount = fwl_amount * 100
                    new_amt = int(round(fwl_amount))
                    if new_amt < 0:
                        new_amt = new_amt * -1
                    final_amt = '%0*d' % (12, new_amt)
                    cmpny_code = str(company_data.company_code)[:10]
                    detail_record = 'F'.ljust(1) + \
                                    '1'.ljust(1) + \
                                    cmpny_code.ljust(10) + \
                                    'PTE'.ljust(3) + \
                                    '01'.ljust(2) + \
                                    ' '.ljust(1) + \
                                    '01'.ljust(2) + \
                                    str(year_month).ljust(6) + \
                                    fwl_salary_rule_code.ljust(2) + \
                                    identificaiton_id + \
                                    str(final_amt).ljust(12) + \
                                    final_gross.ljust(10) + \
                                    '0000000000'.ljust(10) + \
                                    ' ' + \
                                    employee_name_text + \
                                    ' '.ljust(58) + "\r\n"
                    tmp_file.write(detail_record)

            summary_record_amount_total = '%0*d' % (
                15, summary_record_amount_total)
            total_record = total_record + 2
            total_record = '%0*d' % (7, total_record)
            trailer_record = 'F'.ljust(1) + \
                '9'.ljust(1) + \
                str(company_data.company_code)[:10].ljust(10) + \
                'PTE'.ljust(3) + \
                '01'.ljust(2) + \
                ' '.ljust(1) + \
                '01'.ljust(2) + \
                str(total_record).ljust(7) + \
                str(summary_record_amount_total).ljust(15) + \
                ' '.ljust(108) + "\r\n"
            tmp_file.write(trailer_record)
        finally:
            if tmp_file:
                tmp_file.close()
        file = open(tgz_tmp_filename, "rb")
        out = file.read()
        file.close()
        res = base64.b64encode(out)

        if not start_date and end_date:
            return ''
        monthyear = end_date.strftime('%b%Y')
        if company_data.company_code:
            company_uen = company_data.company_code
        else:
            raise ValidationError(
                _("You must be enter company-code in company detail !"))
        file_name = company_uen + monthyear + '01.txt'
        module_rec = self.env['binary.cpf.text.file.wizard'].create(
            {'name': file_name, 'cpf_txt_file': res})
        return {'name': _('Text File'),
                'res_id': module_rec.id,
                "view_mode": 'form',
                'res_model': 'binary.cpf.text.file.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context}


class BinaryCpfTextFileWizard(models.TransientModel):
    _name = 'binary.cpf.text.file.wizard'
    _description = "Binary Cpf Text File Wizard"

    name = fields.Char('Name')
    cpf_txt_file = fields.Binary('Click On Download Link To Download \
        Text File', readonly=True)

    def action_back(self):
        """Return back to cpf rule wizard."""
        return {'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'cpf.rule.text.file',
                'target': 'new'}
