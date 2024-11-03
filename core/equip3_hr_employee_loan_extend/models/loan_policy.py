from odoo import api, fields, models

class LoanPloicy(models.Model):
    _inherit = 'loan.policy'

    @api.model
    def _multi_company_domain(self):
        context = self.env.context
        if context.get('allowed_company_ids'):
            return [('id','in', self.env.context.get('allowed_company_ids'))]
        else:
            return [('id','=', self.env.company.id)]

    company_id = fields.Many2one(domain=_multi_company_domain)
    max_loan_type = fields.Selection(selection_add=[('salary_percentage', 'Salary Percentage')], ondelete={'salary_percentage': 'cascade'})
    employee_ids = fields.Many2many(domain="[('company_id','=',company_id)]")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(LoanPloicy, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(LoanPloicy, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)