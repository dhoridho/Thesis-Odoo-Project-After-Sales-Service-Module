from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.addons.stock_account.models.product import ProductCategory as BasicProductCategory
from odoo.exceptions import ValidationError


class ProductCategory(models.Model):
    _inherit = 'product.category'

    def _check_existing_transaction(self):
        if not self.env.user.has_group('equip3_inventory_base.group_allow_change_cost_method'):
            product_ids = self.env['product.product'].search([('categ_id', 'child_of', self.ids)]).ids
            move_transactions = self.env['stock.move'].search([('product_id', 'in', product_ids)])
            if move_transactions:
                raise ValidationError(_('The costing method cannot be changed as transactions have already been recorded for this product category.'))

    def _make_write(self):

        def write(self, vals):
            impacted_categories = {}
            move_vals_list = []
            Product = self.env['product.product']
            SVL = self.env['stock.valuation.layer']

            """ Currently, only change in cost method will trigger these actions """
            if 'property_cost_method' in vals:
                self._check_existing_transaction()

                # When the cost method or the valuation are changed on a product category, we empty
                # out and replenish the stock for each impacted products.
                new_cost_method = vals.get('property_cost_method')
                new_valuation = vals.get('property_valuation')


                for product_category in self:
                    valuation_impacted = False
                    if new_cost_method and new_cost_method != product_category.property_cost_method:
                        valuation_impacted = True
                    if new_valuation and new_valuation != product_category.property_valuation:
                        valuation_impacted = True
                    if valuation_impacted is False:
                        continue

                    # Empty out the stock with the current cost method.
                    if new_cost_method:
                        description = _("Costing method change for product category %s: from %s to %s.") \
                            % (product_category.display_name, product_category.property_cost_method, new_cost_method)
                    else:
                        description = _("Valuation method change for product category %s: from %s to %s.") \
                            % (product_category.display_name, product_category.property_valuation, new_valuation)
                    out_svl_vals_list, products_orig_quantity_svl, products = Product\
                        ._svl_empty_stock(description, product_category=product_category)
                    out_stock_valuation_layers = SVL.sudo()._query_create(out_svl_vals_list)
                    if product_category.property_valuation == 'real_time':
                        move_vals_list += Product._svl_empty_stock_am(out_stock_valuation_layers)
                    impacted_categories[product_category] = (products, description, products_orig_quantity_svl)

            res = super(BasicProductCategory, self).write(vals)

            for product_category, (products, description, products_orig_quantity_svl) in impacted_categories.items():
                # Replenish the stock with the new cost method.
                in_svl_vals_list = products._svl_replenish_stock(description, products_orig_quantity_svl)
                in_stock_valuation_layers = SVL.sudo()._query_create(in_svl_vals_list)
                if product_category.property_valuation == 'real_time':
                    move_vals_list += Product._svl_replenish_stock_am(in_stock_valuation_layers)

            # Check access right
            if move_vals_list and not self.env['stock.valuation.layer'].check_access_rights('read', raise_exception=False):
                raise UserError(_("The action leads to the creation of a journal entry, for which you don't have the access rights."))
            # Create the account moves.
            if move_vals_list:
                self.env['account.move'].sudo()._query_create(move_vals_list)
            return res
        
        return write

    def _register_hook(self):
        BasicProductCategory._patch_method('write', self._make_write())
        return super(ProductCategory, self)._register_hook()
