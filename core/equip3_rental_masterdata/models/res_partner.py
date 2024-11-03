from odoo import api, fields, models


class RentallInheritResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get("default_branch_id", False)
        if default_branch_id:
            return default_branch_id
        return (
            self.env.company_branches[0].id
            if len(self.env.company_branches) == 1
            else False
        )
    
    @api.model
    def _domain_branch(self):
        return [
            ("id", "in", self.env.branches.ids),
            ("company_id", "in", self.env.companies.ids),
        ]

    @api.model
    def _domain_company(self):
        return [("id", "in", self.env.companies.ids)]

    branch_id = fields.Many2one(
        comodel_name="res.branch",
        check_company=True,
        domain=_domain_branch,
        default=_default_branch,
        string="Branch",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        readonly=True,
        default=lambda self: self.env.company,
        domain=_domain_company,
    )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', context.get('allowed_company_ids'))]

        if context.get('allowed_branch_ids'):
            domain += [
                '|',
                ('branch_id', 'in', context.get('allowed_branch_ids')),
                ('branch_id', '=', False)
            ]

        result = super(RentallInheritResPartner, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context

        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.companies.ids)])

        if context.get('allowed_branch_ids'):
            domain.extend(
                [
                    '|',
                    ('branch_id', 'in', context.get('allowed_branch_ids')),
                    ('branch_id', '=', False)
                ]
            )
        return super(RentallInheritResPartner, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
