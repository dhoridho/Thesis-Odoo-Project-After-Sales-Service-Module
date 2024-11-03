from odoo import api, fields, models

class LoanType(models.Model):
    _inherit = 'loan.type'

    apply_to = fields.Selection([
        ('employee_categories', 'By Employee Categories'),
        ('employees', 'By Employees'),
        ('years_of_service', 'By Years of Services')
    ], string="Apply To", required=True)
    years_of_service = fields.Integer("Years of Service")
    months_of_service = fields.Integer("Months of Service")
    days_of_service = fields.Integer("Days of Service")
    payment_method = fields.Selection(selection_add=[('payroll', 'Payroll')], ondelete={'payroll': 'cascade'})
    deduction_based_period = fields.Selection([
        ('date_from', 'Date From'),
        ('date_to', 'Date To')
    ], string="Deduction Based On Period")
    disburse_method = fields.Selection(selection_add=[('payroll', 'Payroll')], ondelete={'payroll': 'cascade'})

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(LoanType, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(LoanType, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)