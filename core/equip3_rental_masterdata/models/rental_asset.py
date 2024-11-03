from odoo import api, fields, models,_
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta

class RentalAccountAssetAsset(models.Model):
    _inherit = "account.asset.asset"
    _description = "Rental Account Asset Asset"

    rental_product_id = fields.Many2one(
        comodel_name="stock.production.lot",
        string="Rental Product"
    )


class RentalMaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"
    _description = "Rental Maintenance Equipment"

    rental_product_id = fields.Many2one(
        comodel_name="stock.production.lot",
        string="Rental Product"
    )

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        domain=_domain_branch,
        default = _default_branch,
        readonly=False
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
                ('branch_id', 'in', context.get('allowed_branch_ids'))
                ,('branch_id', '=', False)
            ]

        result = super(RentalMaintenanceEquipment, self).search_read(
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
        return super(RentalMaintenanceEquipment, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def create_account_asset(self):
        category_id = self.env['account.asset.category'].search([('type', '=', 'purchase')], limit=1)
        vals = {
            'name' : self.name,
            'company_id' : self.company_id.id,
            'date' : date.today(),
            'first_depreciation_manual_date' : date.today(),
            'equipment_id' : self.id,
            'value' : self.asset_value,
            'branch_id' : self.branch_id.id,
            'rental_product_id': self.rental_product_id.id,
            'serial_number_id': self.lot_id.id
        }

        if category_id:
            vals['category_id'] = category_id.id
        asset_id = self.env['account.asset.asset'].create(vals)
        self.account_asset_id = asset_id.id
	