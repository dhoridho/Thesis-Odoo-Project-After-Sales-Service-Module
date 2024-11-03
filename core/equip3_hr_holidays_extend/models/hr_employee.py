from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = "Hr Employee"

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    leave_struct_id = fields.Many2one('hr.leave.structure', string='Leave Structure',domain=_multi_company_domain)
