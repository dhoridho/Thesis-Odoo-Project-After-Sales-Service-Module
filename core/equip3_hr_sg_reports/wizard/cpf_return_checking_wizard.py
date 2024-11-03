from datetime import datetime
from dateutil.relativedelta import relativedelta as rv

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF


class CpfReturnCheckingWizard(models.TransientModel):
    _name = 'cpf.return.checking.wizard'
    _description = "CPF Return Checking"

    employee_ids = fields.Many2many('hr.employee', string='Employee')
    end_date = fields.Date(
        string='End Date',
        default=lambda *a: str(datetime.now() +
                               rv(months=+1, day=1, days=-1))[:10]
    )

    def action_print_report(self):
        return self.env.ref('equip3_hr_sg_reports.cpf_return_report_pdf').report_action(self)

    def get_basic_info(self):
        for cpf in self:
            basic_info_list = []
            context = dict(self.env.context) if self.env.context else {}
            end_date = cpf.end_date
            emp_ids = cpf.employee_ids

            if not emp_ids.ids:
                raise ValidationError(_("Please select employee"))
            for employee in emp_ids:
                if not employee.identification_id:
                    raise ValidationError(_(
                        'There is no identification no define '
                        'for %s employee.' % (employee.name)
                    ))
            context.update({
                'employee_id': emp_ids,
                'end_date': end_date
            })
            company_data = self.env['res.users'].browse(
                context.get('uid')).company_id
            month_dict = {
                '01': 'January', '02': 'February', '03': 'March',
                '04': 'April', '05': 'May', '06': 'June',
                '07': 'July', '08': 'August', '09': 'September',
                '10': 'October', '11': 'November', '12': 'December'
            }
            end_date = cpf.end_date.strftime(DSDF)
            end_date_month_num = end_date.split('-')[1]
            end_date_month = month_dict.get(end_date_month_num)
            end_date_year = end_date.split('-')[0]
            period = f'{end_date_month}, {end_date_year}'

            basic_info_list.append({
                'company': company_data.name,
                'date': end_date,
                'period': period,
            })

        return basic_info_list

    @api.constrains('employee_ids')
    def _constraint_employee_ids(self):
        for cpf in self:
            end_date = cpf.end_date.strftime(DSDF)
            end_date_month_num = end_date.split('-')[1]
            month_dict = {
                '01': 'January', '02': 'February', '03': 'March',
                '04': 'April', '05': 'May', '06': 'June',
                '07': 'July', '08': 'August', '09': 'September',
                '10': 'October', '11': 'November', '12': 'December'
            }
            end_date_month = month_dict.get(end_date_month_num)
            end_date_year = end_date.split('-')[0]
            period = f'{end_date_month}, {end_date_year}'

            if not cpf.employee_ids.ids:
                raise ValidationError(_("Please select employee"))

            for employee in cpf.employee_ids:
                if not employee.identification_id:
                    raise ValidationError(_(
                        'There is no identification no define '
                        'for %s employee.' % (employee.name)
                    ))

            employee_ids = self.env['hr.employee'].search([
                ('id', 'in', cpf.employee_ids.ids),
                ('category_ids', '=', False)
            ])

            for emp_record in employee_ids:
                payslip_ids = self.env['hr.payslip'].search([
                    ('employee_id', '=', emp_record.id),
                    ('state', 'in', ['draft', 'done', 'verify'])
                ])

                if not payslip_ids:
                    raise ValidationError(
                        _(
                            'There is no payslip details in '
                            'selected month %s'
                        ) % (period)
                    )

    def get_report_data(self):
        for cpf in self:
            report_data_list = []
            context = dict(self.env.context) if self.env.context else {}
            end_date = cpf.end_date
            emp_ids = cpf.employee_ids

            context.update({
                'employee_id': emp_ids,
                'end_date': end_date
            })
            company_data = self.env['res.users'].browse(
                context.get('uid')).company_id
            month_dict = {
                '01': 'January', '02': 'February', '03': 'March',
                '04': 'April', '05': 'May', '06': 'June',
                '07': 'July', '08': 'August', '09': 'September',
                '10': 'October', '11': 'November', '12': 'December'
            }
            contract_status = False
            end_date = cpf.end_date.strftime(DSDF)
            end_date_month_num = end_date.split('-')[1]
            end_date_month = month_dict.get(end_date_month_num)
            end_date_year = end_date.split('-')[0]
            period = f'{end_date_month}, {end_date_year}'
            emp_obj = self.env['hr.employee']
            payslip_obj = self.env['hr.payslip']
            hr_contract_obj = self.env['hr.contract']

            t_cpfsdl_amount = t_p_cpf_sdl_amount = t_p_fwl_amount = 0.0
            t_p_cpf_amount = t_gross_amount = t_ecf_amount = 0.0
            t_cdac_amount = t_sinda_amount = t_mbmf_amount = t_cpf_amount = 0.0
            total_additional_amount = total_cpfsdl_amount = 0.0
            total_p_cpf_amount = total_gross_amount = total_ecf_amount = 0.0
            total_cdac_amount = total_sinda_amount = total_mbmf_amount = 0.0
            total_cpf_amount = 0.0

            employee_ids = emp_obj.search([
                ('id', 'in', emp_ids.ids),
                ('category_ids', '=', False)
            ])

            for emp_record in employee_ids:
                payslip_ids = payslip_obj.search([
                    ('employee_id', '=', emp_record.id),
                    ('state', 'in', ['draft', 'done', 'verify'])
                ])
                end_date = cpf.end_date.strftime(DSDF) or False
                additional_amount = cpfsdl_amount = p_cpf_amount = 0.0
                gross_amount = ecf_amount = fwl_amount = cdac_amount = 0.0
                sinda_amount = mbmf_amount = cpf_amount = 0.0
                for payslip_rec in payslip_ids:
                    date_from_month = payslip_rec.date_from.strftime(
                        DSDF).split('-')[1]
                    date_from_year = payslip_rec.date_from.strftime(
                        DSDF).split('-')[0]
                    if date_from_year == end_date_year and date_from_month == end_date_month_num:
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

                    t_cpf_amount += cpf_amount
                    total_cpf_amount += cpf_amount
                    t_mbmf_amount += mbmf_amount
                    total_mbmf_amount += mbmf_amount
                    t_sinda_amount += sinda_amount
                    total_sinda_amount += sinda_amount
                    t_cdac_amount += cdac_amount
                    total_cdac_amount += cdac_amount
                    t_ecf_amount += ecf_amount
                    total_ecf_amount += ecf_amount
                    total_cpfsdl_amount += cpfsdl_amount
                    t_cpfsdl_amount += cpfsdl_amount
                    t_gross_amount += gross_amount
                    total_gross_amount += gross_amount
                    total_additional_amount += additional_amount
                    t_p_cpf_amount += p_cpf_amount
                    total_p_cpf_amount += p_cpf_amount

                    domain = [('employee_id', '=', emp_record.id), '|',
                              ('date_end', '>=', payslip_rec.date_from),
                              ('date_end', '=', False)]
                    contract_id = hr_contract_obj.search(domain)
                    emp_domain = [
                        ('employee_id', '=', emp_record.id),
                        ('date_end', '<=', payslip_rec.date_from)
                    ]
                    old_contract_id = hr_contract_obj.search(emp_domain)
                    for contract in contract_id:
                        if not payslip_rec.employee_id.active:
                            contract_status = 'Left'
                        elif contract.date_start >= payslip_rec.date_from and not old_contract_id.ids:
                            contract_status = 'New Join'
                        else:
                            contract_status = 'Existing'

                report_data_list.append({
                    'company': company_data.name,
                    'period': period,
                    'date': end_date,
                    'employee_name': payslip_ids.employee_id and payslip_ids.employee_id.name or '',
                    'identification_id': payslip_ids.employee_id and payslip_ids.employee_id.identification_id or '',
                    'mandatory_contribution': round(cpf_amount or 0.00, 2),
                    'voluntary_contribution': round(0.00, 2),
                    'last_contribution': round(p_cpf_amount or 0.00, 2),
                    'mbmf_fund': round(mbmf_amount or 0.00, 2),
                    'sinda_fund': round(sinda_amount or 0.00, 2),
                    'cdac_fund': round(cdac_amount or 0.00, 2),
                    'ecf_fund': round(ecf_amount or 0.00, 2),
                    'cpfdsl_fund': round(cpfsdl_amount or 0.00, 2),
                    'ordinary_wages': round(gross_amount or 0.00, 2),
                    'additional_wages': round(additional_amount or 0.00, 2),
                    'contract_status': contract_status,
                })

        return report_data_list
