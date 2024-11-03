from odoo import api, models,fields
from datetime import date
from dateutil.relativedelta import relativedelta

class HrContract(models.Model):
    _inherit = 'hr.contract'

    def write(self, values):
        for rec in self:
            probation = self.env['employee.probation'].search([('contract_id','=',rec.id),('state','=','pass')])
            for prob in probation:
                prob.show_update_contract = False
        return super(HrContract, self).write(values)
    
    
    def action_launch_probation(self):
        return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Probation',
                'res_model': 'employee.probation',
                'view_type': 'form',
                'view_id': False,
                'target':'new',
                'view_mode': 'form',
                'context':{
                        'default_employee_id':self.employee_id.id,
                        'default_contract_id':self.id,
                        'default_start_date':self.date_start,
                        'default_end_date':self.date_end,
                        },
                }