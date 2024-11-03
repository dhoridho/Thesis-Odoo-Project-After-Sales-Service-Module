from odoo import models, fields, api
from odoo.exceptions import ValidationError
from lxml import etree
class Equip3GenerateAsset(models.TransientModel):
    _name = 'rental.generate.asset.wizard'
    _description = "Rental Generate Asset Wizard"

    asset_ids = fields.Many2many(
        comodel_name="product.template",
        string="Asset",
        domain=[('type', '=', 'asset'),('tracking', '=', 'serial')]
    )
    generate_all_asset = fields.Boolean(string="Generate All Assets", default=True)
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(Equip3GenerateAsset, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        root = etree.fromstring(res['arch'])
        res['arch'] = etree.tostring(root)
        if self.env.context.get('is_from_rental',False):
            if 'asset_ids' in res['fields']:
                if not ('rent_ok','=',True) in res['fields']['asset_ids']['domain']:
                    res['fields']['asset_ids']['domain'].append(('rent_ok','=',True))        
        else:
            if 'asset_ids' in res['fields']:
                if ('rent_ok','=',True) in res['fields']['asset_ids']['domain']:
                    res['fields']['asset_ids']['domain'].remove(('rent_ok','=',True))      
                
        return res

    def generate_asset(self):
        self.ensure_one()
        lots = self.env['stock.production.lot'].search([])
        domain_all_assets = [('type', '=', 'asset'),('tracking', '=', 'serial')]
        if self.env.context.get('is_from_rental',False):
            domain_all_assets.append(('rent_ok','=',True))
            
        all_assets = self.env['product.template'].search(domain_all_assets)

        if self.generate_all_asset:
            unique_product_tmpl_id = set()
            for lot in lots:
                if not lot.is_depreciation_asset_created and not lot.is_asset_control_created:
                    product_tmpl_id = lot.product_id.product_tmpl_id
                    matching_assets = all_assets.filtered(lambda asset: asset.id == product_tmpl_id.id)
                    for matching_asset in matching_assets:
                        if not matching_asset.asset_control_category:
                            raise ValidationError(
                                "Asset Control Catergory of %s has not been set!" % matching_asset.name
                            )
                        
                        if not matching_asset.branch_id:
                            raise ValidationError(
                                "Branch of %s has not been set!" % matching_asset.name
                            )
        
                        unique_product_tmpl_id.add(product_tmpl_id.id)
                        self.env['maintenance.equipment'].create({
                            'name': matching_asset.name,
                            'category_id': matching_asset.asset_control_category.id,
                            'serial_no': lot.name,
                            'lot_id': lot.id,
                            'branch_id': matching_asset.branch_id.id,
                            'product_template_id': lot.product_id.product_tmpl_id.id,
                        })
                        lot.is_depreciation_asset_created = True
                        lot.is_asset_control_created = True

        else:
            if self.asset_ids:
                unique_product_tmpl_id = set()
                for lot in lots:
                    if not lot.is_depreciation_asset_created and not lot.is_asset_control_created:
                        product_tmpl_id = lot.product_id.product_tmpl_id
                        matching_assets = self.asset_ids.filtered(lambda asset: asset.id == product_tmpl_id.id)
                        for matching_asset in matching_assets:
                            if not matching_asset.asset_control_category:
                                raise ValidationError(
                                    "Asset Control Catergory of %s has not been set!" % matching_asset.name
                                )

                            if not matching_asset.branch_id:
                                raise ValidationError(
                                    "Branch of %s has not been set!" % matching_asset.name
                                )
                            unique_product_tmpl_id.add(product_tmpl_id.id)
                            self.env['maintenance.equipment'].create({
                                'name': matching_asset.name,
                                'category_id': matching_asset.asset_control_category.id,
                                'serial_no': lot.name,
                                'lot_id': lot.id,
                                'branch_id': matching_asset.branch_id.id,
                                'product_template_id': lot.product_id.product_tmpl_id.id,
                            })
                            lot.is_depreciation_asset_created = True
                            lot.is_asset_control_created = True
