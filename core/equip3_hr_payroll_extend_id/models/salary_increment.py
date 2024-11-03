from odoo import fields,api,models
from dateutil.relativedelta import relativedelta

class HrSalaryIncrement(models.Model):
    _inherit = 'hr.salary.increment'

    def generate(self):
        for rec in self:
            if rec.apply_to == "by_employee":
                contracts = self.env['hr.contract'].search([('employee_id','in',rec.employee_ids.ids),('state','=','open')])
                for contract in contracts:
                    salary = self.calculate_base_on(contract.wage)
                    contract.copy({'wage': salary, 'date_start': rec.effective_date, 'rapel_date': rec.effective_date})
                    date_end_before = (rec.effective_date - relativedelta(days=1)).strftime('%Y-%m-%d')
                    contract.write({'date_end': date_end_before})
            elif rec.apply_to == "by_job":
                contracts = self.env['hr.contract'].search([('job_id','in',rec.job_ids.ids),('state','=','open')])
                for contract in contracts:
                    salary = self.calculate_base_on(contract.wage)
                    contract.copy({'wage': salary, 'date_start': rec.effective_date, 'rapel_date': rec.effective_date})
                    date_end_before = (rec.effective_date - relativedelta(days=1)).strftime('%Y-%m-%d')
                    contract.write({'date_end': date_end_before})
            elif rec.apply_to == "by_department":
                contracts = self.env['hr.contract'].search([('department_id','in',rec.department_ids.ids),('state','=','open')])
                for contract in contracts:
                    salary = self.calculate_base_on(contract.wage)
                    contract.copy({'wage': salary, 'date_start': rec.effective_date, 'rapel_date': rec.effective_date})
                    date_end_before = (rec.effective_date - relativedelta(days=1)).strftime('%Y-%m-%d')
                    contract.write({'date_end': date_end_before})
            elif rec.apply_to == "by_company":
                contracts = self.env['hr.contract'].search([('company_id','in',rec.company_ids.ids),('state','=','open')])
                for contract in contracts:
                    salary = self.calculate_base_on(contract.wage)
                    contract.copy({'wage': salary, 'date_start': rec.effective_date, 'rapel_date': rec.effective_date})
                    date_end_before = (rec.effective_date - relativedelta(days=1)).strftime('%Y-%m-%d')
                    contract.write({'date_end': date_end_before})
            rec.state = "generated"