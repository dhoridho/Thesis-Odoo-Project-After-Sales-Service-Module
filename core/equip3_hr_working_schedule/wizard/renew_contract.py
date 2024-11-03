from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class RenewContractMutation(models.TransientModel):
    _name = 'renew.contract.mutation'

    def action_renew_contract(self):

        context = dict(self._context or {})
        active_id = context.get('active_id', [])
        mutation = self.env['employee.mutation'].browse(active_id)
        action = self.env.ref('employee_mutation.act_mutation_contract').read()[0]

        contract = self.env['hr.contract'].search([('employee_id', '=', mutation.employee.id)], order='id desc',
                                                  limit=1)

        action['views'] = [(self.env.ref('hr_contract.hr_contract_view_form').id, 'form'),
                           (self.env.ref('hr_contract.hr_contract_view_tree').id, 'tree')]

        if contract:
            action['context'] = {'default_employee_id': mutation.employee.id,
                                 'default_date_start': mutation.mutation_time,
                                 'mutation_id': mutation.id,
                                 'default_reference_mutation': mutation.id,
                                 'default_reference': contract.id,
                                 'default_job_id': mutation.job_position_to_mutation.id,
                                 'default_department_id': mutation.department_to_mutation.id,
                                 'default_company_id': mutation.company_for_mutation.id,
                                 'default_work_location': mutation.work_location_mutation.id}
        else:
            action['context'] = {'default_employee_id': mutation.employee.id,
                                 'default_date_start': mutation.mutation_time,
                                 'mutation_id': mutation.id,
                                 'default_reference_mutation': mutation.id,
                                 'default_job_id': mutation.job_position_to_mutation.id,
                                 'default_department_id': mutation.department_to_mutation.id,
                                 'default_company_id': mutation.company_for_mutation.id,
                                 'default_work_location': mutation.work_location_mutation.id}
        return action
