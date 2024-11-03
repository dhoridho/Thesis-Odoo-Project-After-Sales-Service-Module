from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Hr Employee'

    # date_of_joining = fields.Date("Date of Joining", related='contract_id.first_contract_date')
    date_of_joining = fields.Date("Date of Joining", compute='_compute_date_of_joining', store=True, readonly=False)

    @api.depends('contract_ids.state', 'contract_ids.date_start')
    def _compute_date_of_joining(self):
        for employee in self:
            contracts = employee._get_first_contracts()
            if not employee.date_of_joining:
                if contracts:
                    employee.date_of_joining = min(contracts.mapped('date_start'))
                else:
                    employee.date_of_joining = False