from odoo import models, fields, api
from odoo.exceptions import ValidationError

class HrEmployeeReporting(models.TransientModel):
    _name = 'rental.generate.asset.wizard'
    _description = "Rental Generate Asset Wizard"

    asset_ids = fields.Many2many(
        comodel_name="product.template",
        string="Asset",
        domain=[('rent_ok', '=', True), ('type', '=', 'asset')]
    )
    generate_all_asset = fields.Boolean(string="Generate All Assets", default=True)

    def generate_asset(self):
        self.ensure_one()
        lots = self.env['stock.production.lot'].search([])
        all_assets = self.env['product.template'].search([
            ('rent_ok', '=', True),
            ('type', '=', 'asset')
        ])

        if self.generate_all_asset:
            unique_product_tmpl_id = set()
            for lot in lots:
                product_tmpl_id = lot.product_id.product_tmpl_id
                if not product_tmpl_id.is_asset_generated:
                    matching_assets = all_assets.filtered(lambda asset: asset.id == product_tmpl_id.id)
                    for matching_asset in matching_assets:
                        unique_product_tmpl_id.add(product_tmpl_id.id)
                        self.env['maintenance.equipment'].create({
                            'name': matching_asset.name,
                            'category_id': matching_asset.asset_category_id.id,
                            'serial_no': lot.name,
                            'serial_no': lot.id,
                            'branch_id': matching_asset.branch_id.id,
                            'rental_product_id': lot.id,
                        })
            for product in all_assets.filtered(lambda p: p.id in unique_product_tmpl_id):
                product.is_asset_generated = True

        else:
            if self.asset_ids:
                unique_product_tmpl_id = set()
                for lot in lots:
                    product_tmpl_id = lot.product_id.product_tmpl_id
                    if not product_tmpl_id.is_asset_generated:
                        matching_assets = self.asset_ids.filtered(lambda asset: asset.id == product_tmpl_id.id)
                        for matching_asset in matching_assets:
                            unique_product_tmpl_id.add(product_tmpl_id.id)
                            self.env['maintenance.equipment'].create({
                                'name': matching_asset.name,
                                'category_id': matching_asset.asset_category_id.id,
                                'serial_no': lot.name,
                                'serial_no': lot.id,
                                'rental_product_id': lot.id,
                                'branch_id': matching_asset.branch_id.id
                            })
                for product in self.asset_ids:
                    product.is_asset_generated = True
