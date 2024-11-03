from odoo import models, fields, api
from odoo.exceptions import ValidationError

class Equip3GenerateAsset(models.TransientModel):
    _inherit = 'rental.generate.asset.wizard'
    
    
    def generate_asset(self):
        res = super(Equip3GenerateAsset,self).generate_asset()
        if self.env.context.get('is_from_rental',False):
            lots = self.env['stock.production.lot'].search([])
            domain_all_assets = [('type', '=', 'asset'),('tracking', '=', 'serial'),(('rent_ok','=',True))]
            if self.env.context.get('is_from_rental',False):
                domain_all_assets.append(('rent_ok','=',True))
                
            all_assets = self.env['product.template'].search(domain_all_assets)

            if self.generate_all_asset:
                unique_product_tmpl_id = set()
                for lot in lots:
                    if not lot.is_return_of_asset_created:
                        product_tmpl_id = lot.product_id.product_tmpl_id
                        matching_assets = all_assets.filtered(lambda asset: asset.id == product_tmpl_id.id)
                        for matching_asset in matching_assets:
                            unique_product_tmpl_id.add(product_tmpl_id.id)
                            self.env['return.of.assets'].create({
                                'product_template_id': lot.product_id.product_tmpl_id.id,
                                'lot_id': lot.id,
                            })
                            lot.is_return_of_asset_created = True

            else:
                if self.asset_ids:
                    unique_product_tmpl_id = set()
                    for lot in lots:
                        if not lot.is_return_of_asset_created:
                            product_tmpl_id = lot.product_id.product_tmpl_id
                            matching_assets = self.asset_ids.filtered(lambda asset: asset.id == product_tmpl_id.id)
                            for matching_asset in matching_assets:
                                unique_product_tmpl_id.add(product_tmpl_id.id)
                                self.env['return.of.assets'].create({
                                    'product_template_id': lot.product_id.product_tmpl_id.id,
                                    'lot_id': lot.id,
                                })
                                lot.is_return_of_asset_created = True
        
        return res