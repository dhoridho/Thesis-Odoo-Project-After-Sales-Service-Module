from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HashmicroHRTaxBracket(models.Model):
    _name = 'hr.tax.bracket'
    _inherit = ['mail.thread']
    _description = 'HR Tax Bracket'

    name = fields.Char()
    sequence = fields.Integer()
    taxable_income_from = fields.Float()
    taxable_income_to = fields.Float()
    tax_rate = fields.Float()
    tax_penalty_rate = fields.Float()
    company_id = fields.Many2one('res.company',default=lambda self:self.env.company.id)
    branch_id = fields.Many2one('res.branch',domain=[('company_id','=',company_id)])
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HashmicroHRTaxBracket, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HashmicroHRTaxBracket, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.model
    def default_get(self, fields):
        res = super(HashmicroHRTaxBracket, self).default_get(fields)
        num_list = []
        tax_bracket = self.search([])
        if not tax_bracket:
            res['sequence'] = 1
        if tax_bracket:
            num_list.extend([data.sequence for data in tax_bracket])
            res['sequence'] = max(num_list) + 1


        return res




