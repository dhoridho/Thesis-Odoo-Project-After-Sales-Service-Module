from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class HashmicroPtkpMasterData(models.Model):
    _name = 'hr.tax.ptkp'
    _description = 'Hr Tax Ptkp'
    _rec_name = 'ptkp_name'
    _inherit = ['mail.thread']

    ptkp_name = fields.Char(required=True, string="PTKP Name")
    ptkp_amount = fields.Float(required=True, string="PTKP Amount")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company.id,
                                 tracking=True)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]",
                                tracking=True)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HashmicroPtkpMasterData, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HashmicroPtkpMasterData, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
