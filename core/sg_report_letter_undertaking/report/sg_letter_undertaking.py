import datetime
import time
from odoo import api, models


class SGLetterUndertaking(models.AbstractModel):
    _name = 'report.sg_report_letter_undertaking.report_form_letter'
    _description = "Letter Undertaking Report"

    def get_data(self, form):
        employee_obj = self.env['hr.employee']

        vals = []
        emp_ids = employee_obj.search([('id', 'in', form.get('employee_ids'))])
        for employee in emp_ids:
            res = {
                'date': datetime.date.today(),
                'name': employee.name or '',
                'cmp_name':
                employee.address_id and employee.address_id.name or '',
                'cmp_house_no':
                employee.address_id and employee.address_id.house_no or '',
                'cmp_street':
                employee.address_id and employee.address_id.street or '',
                'cmp_unit_no':
                employee.address_id and employee.address_id.unit_no or '',
                'cmp_email':
                employee.address_id and employee.address_id.email or '',
                'cmp_contry': employee.address_id and employee.address_id.
                country_id and employee.address_id.country_id.name or '',
                'cmp_zip': employee.address_id and
                employee.address_id.zip or '',
                'cmp_phone': employee.address_id and
                employee.address_id.phone or '',
                'user_house_no': employee.address_home_id and
                employee.address_home_id.house_no or '',
                'user_unit_no': employee.address_home_id and
                employee.address_home_id.unit_no or '',
                'user_street': employee.address_home_id and
                employee.address_home_id.street or '',
                'user_country': employee.address_home_id and employee.
                address_home_id.country_id and employee.address_home_id.
                country_id.name or '',
                'user_zip': employee.address_home_id and employee.
                address_home_id.zip or '',
                'user_phone': employee.address_home_id and employee.
                address_home_id.phone or '',
                'nric_no': employee.identification_id if employee.
                identification_no == '1' else ''
            }
            vals.append(res)
        return vals

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        datas = docs.read([])
        report_lines = self.get_data(datas[0])
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': datas,
            'docs': docs,
            'time': time,
            'get_data': report_lines
        }
