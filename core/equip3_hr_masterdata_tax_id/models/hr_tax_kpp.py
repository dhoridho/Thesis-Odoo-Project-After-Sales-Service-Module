from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HashmicroKppMasterData(models.Model):
    _name = 'hr.tax.kpp'
    _description = 'Hr Tax Kpp'
    _inherit = ['mail.thread']

    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company.id,
                                 tracking=True)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]",
                                tracking=True)
    name = fields.Char(required=True, tracking=True)
    code = fields.Char()
    address = fields.Text(required=True, tracking=True)
    phone = fields.Char()
    fax = fields.Char()
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HashmicroKppMasterData, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HashmicroKppMasterData, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    @api.constrains("name")
    def name_constraimn(self):
        for record in self:
            if record.name:
                name = self.env['hr.tax.kpp'].search([('name', '=', record.name), ('id', '!=', record.id)])
                if name:
                    raise ValidationError("name already use")
