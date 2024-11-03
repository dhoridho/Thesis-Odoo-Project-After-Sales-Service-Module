import time
from datetime import datetime

from odoo import api, models, tools, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF


class PpdAppendix8aForm(models.AbstractModel):
    _name = "report.sg_appendix8a_report.report_appendix8a"
    _description = "Appendix 8a Form"

    def get_employee(self, data):
        result = []
        hr_contract_income_tax = self.env['hr.contract.income.tax']
        contract_ids = self.env['hr.contract'].search(
            [('employee_id', 'in', data.get('employee_ids', []))])
        if len(contract_ids.ids) == 0:
            raise UserError(_('No Contract found for selected dates'))
        furniture_value_indicator = pioneer_service = employer_name = \
            employer_address = authorized_person = batchdate = ''
        autho_person_desg = autho_person_tel = last_year = ''

        from_date = to_date = start_date = end_date = False
        if data.get('start_date', False) and data.get('end_date', False):
            from_date = data.get('start_date', False)
            to_date = data.get('end_date', False)
            fiscal_start = from_date.year - 1
            fiscal_end = to_date.year - 1
            start_date = '%s-01-01' % tools.ustr(int(fiscal_start))
            end_date = '%s-12-31' % tools.ustr(int(fiscal_end))
            start_date = datetime.strptime(start_date, DSDF)
            end_date = datetime.strptime(end_date, DSDF)
        if data.get('payroll_user'):
            payroll_use_id = int(data['payroll_user'])
            authorized_person = self.env[
                'res.users'].browse(payroll_use_id).name
            payroll_emp = self.env['hr.employee'].search(
                [('user_id', '=', payroll_use_id)])
            if len(payroll_emp.ids) != 0:
                premp_brw = payroll_emp[0]
                autho_person_desg = premp_brw.job_id and premp_brw.job_id.id \
                    and premp_brw.job_id.name or ''
                autho_person_tel = premp_brw.work_phone or ''
        if data.get('batch_date'):
            batchdate = data['batch_date'].strftime('%d/%m/%Y')
        for contract in contract_ids:
            contract_income_tax_id = hr_contract_income_tax.search([
                ('contract_id', '=', contract.id),
                ('start_date', '>=', from_date),
                ('end_date', '<=', to_date)], limit=1)
            from_sg_date = to_sg_date = ''
            if contract_income_tax_id.furniture_value_indicator:
                furniture_value_indicator = \
                    dict(hr_contract_income_tax.fields_get(
                        allfields=['furniture_value_indicator'])[
                        'furniture_value_indicator']['selection'])[
                        contract_income_tax_id.furniture_value_indicator]
            if contract_income_tax_id.pioneer_service:
                pioneer_service = \
                    dict(hr_contract_income_tax.fields_get(
                        allfields=['pioneer_service'])[
                        'pioneer_service']['selection'])[
                        contract_income_tax_id.pioneer_service]
            emp_id = contract.employee_id
            if emp_id.address_id:
                employer_name = emp_id.address_id.name
                employer_address = str(emp_id.address_id.street or
                                       '') + ',' + str(
                    emp_id.address_id.street2 or '')
            if contract_income_tax_id.from_date:
                from_sg_date = contract_income_tax_id.from_date.strftime('%d/%m/%Y')
            if contract_income_tax_id.to_date:
                to_sg_date = contract_income_tax_id.to_date.strftime('%d/%m/%Y')
            if from_date:
                last_year = fiscal_start or ''
            housekeeping = contract_income_tax_id.taxalble_value_of_utilities_housekeeping
            result.append({
                'year_id': from_date.year or '',
                'last_year': last_year,
                'employee_name': emp_id.name,
                'address': contract_income_tax_id.address,
                'from_date': from_sg_date,
                'to_date': to_sg_date,
                'no_of_days': contract_income_tax_id.no_of_days,
                'no_of_emp': contract_income_tax_id.no_of_emp,
                'annual_value': contract_income_tax_id.annual_value,
                'furniture_value_indicator': furniture_value_indicator,
                'furniture_value': contract_income_tax_id.furniture_value,
                'rent_landlord': contract_income_tax_id.rent_landloard,
                'place_of_residence_taxable_value':
                contract_income_tax_id.place_of_residence_taxable_value,
                'total_rent_paid': contract_income_tax_id.total_rent_paid,
                'total_taxable_value': contract_income_tax_id.total_taxable_value,
                'utilities_misc_value': contract_income_tax_id.utilities_misc_value,
                'driver_value': contract_income_tax_id.driver_value,
                'employer_paid_amount': contract_income_tax_id.employer_paid_amount,
                'taxalble_value_of_utilities_housekeeping': housekeeping,
                'actual_hotel_accommodation':
                contract_income_tax_id.actual_hotel_accommodation,
                'employee_paid_amount': contract_income_tax_id.employee_paid_amount,
                'taxable_value_of_hotel_acco':
                contract_income_tax_id.taxable_value_of_hotel_acco,
                'cost_of_home_leave_benefits':
                contract_income_tax_id.cost_of_home_leave_benefits,
                'no_of_passanger': contract_income_tax_id.no_of_passanger,
                'spouse': contract_income_tax_id.spouse,
                'children': contract_income_tax_id.children,
                'pioneer_service': pioneer_service,
                'interest_payment': contract_income_tax_id.interest_payment,
                'insurance_payment': contract_income_tax_id.insurance_payment,
                'free_holidays': contract_income_tax_id.free_holidays,
                'edu_expenses': contract_income_tax_id.edu_expenses,
                'non_monetary_awards': contract_income_tax_id.non_monetary_awards,
                'entrance_fees': contract_income_tax_id.entrance_fees,
                'gains_from_assets': contract_income_tax_id.gains_from_assets,
                'cost_of_motor': contract_income_tax_id.cost_of_motor,
                'car_benefits': contract_income_tax_id.car_benefits,
                'non_monetary_benefits': contract_income_tax_id.non_monetary_benefits,
                'total_value_of_benefits': contract_income_tax_id.total_value_of_benefits,
                'employer_name': employer_name,
                'employer_address': employer_address,
                'authorized_person': authorized_person,
                'autho_person_desg': autho_person_desg,
                'autho_person_tel': autho_person_tel,
                'org_id_no': emp_id.identification_id or '',
                'batchdate': batchdate or ''
            })
        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        data = docs.read([])[0]
        report_lines = self.get_employee(data)
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data,
            'docs': docs,
            'time': time,
            'get_employee': report_lines
        }
