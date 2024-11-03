from odoo import models,api,fields,_

class HrEmployeeAppraisalsSurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    employee_performance_id = fields.Many2one('employee.performance')
    reviewer_role = fields.Selection([('manager', 'Manager'), ('subordinate', 'Subordinate'),
                            ('peer', 'Peer'), ('external', 'External')], string='Reviewer Role')
    company_name = fields.Char('Company Name')
    reviewer_name = fields.Char('Reviewer Name')