# -*- coding: utf-8 -*
from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import UserError
from lxml import etree


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    plu_number = fields.Char('PLU Number')
    
    is_pos_bom = fields.Boolean(
        'Is POS BoM Product?', related="product_tmpl_id.is_pos_bom")
    product_bom_id = fields.One2many(
        'pos.product.bom', 'product_id', string='Product BOM Structure')
 

    def getProductInformation(self, price, quantity, pos_config_id):
        self.ensure_one()
        config = self.env['pos.config'].browse(pos_config_id)

        # Tax related
        taxes = self.taxes_id.compute_all(price, config.currency_id, quantity, self)
        all_prices = {
            'price_without_tax': taxes['total_excluded'] / quantity,
            'price_with_tax': taxes['total_included'] / quantity,
            'tax_details': [{'name': tax['name'], 'amount': tax['amount'] / quantity} for tax in taxes['taxes']],
        }

        # Pricelists
        if config.use_pricelist:
            pricelists = config.available_pricelist_ids
        else:
            pricelists = config.pricelist_id
        price_per_pricelist_id = pricelists.price_get(self.id, quantity)
        pricelist_list = [
            {
                'name': pl.name,
                'id': pl.id,
                'price': price_per_pricelist_id[pl.id]
            } for pl in pricelists]

        # Warehouses
        warehouse_list = [
            {
                'name': w.name,
                'available_quantity': self.with_context({'warehouse': w.id}).qty_available,
                'forecasted_quantity': self.with_context({'warehouse': w.id}).virtual_available,
                'uom': self.uom_name
            }
            for w in self.env['stock.warehouse'].search([])]

        # Stock Location list
        location_list = [
            {
                'name': l.complete_name,
                'available_quantity': self.with_context({'location': l.id}).qty_available,
                'forecasted_quantity': self.with_context({'location': l.id}).virtual_available,
                'uom': self.uom_name
            }
            for l in self.env['stock.location'].search([('usage', '=', 'internal')])]
        # Lots
        lots = [
            {
                'id': l.id,
                'name': l.name,
                'ref': l.ref,
                'product_qty': l.product_qty,
            }
            for l in self.env['stock.production.lot'].search(
                [
                    ('product_id', '=', self.id),
                    ('product_qty', '>', 0),
                ])]
        
        # Variants
        variant_list = [{
            'name': attribute_line.attribute_id.name,
            'values': list(
                map(lambda attr_name: {'name': attr_name, 'search': '%s %s' % (self.name, attr_name)},
                    attribute_line.value_ids.mapped('name')))
        }
            for attribute_line in self.attribute_line_ids]

        return {
            'lots': lots,
            'all_prices': all_prices,
            'pricelists': pricelist_list,
            'warehouses': warehouse_list,
            # 'suppliers': supplier_list,
            'locations': location_list,
            'variants': variant_list
        }

    def force_write(self, vals):
        self.sudo().write(vals)
        return True

    def unlink(self):
        product_ids = []
        for product in self:
            product_ids.append(product.id)
            if product.product_tmpl_id and product.product_tmpl_id.available_in_pos:
                linesHavePurchased = self.env['pos.order.line'].search([('product_id', '=', product.id)])
                if linesHavePurchased:
                    raise UserError(
                        _('You cannot delete a product . Because products have exsting in POS Order Lines'))
        res = super(ProductProduct, self).unlink()
        return res

    def add_barcode(self):
        newCode = None
        for product in self:
            format_code = "%s%s%s" % ('777', product.id, datetime.now().strftime("%d%m%y%H%M"))
            barcode = self.env['barcode.nomenclature'].sanitize_ean(format_code)
            product.write({'barcode': barcode})
            newCode = barcode
        return newCode

    def write(self, vals):
        user_pos_not_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_cashier') or self.env.user.has_group('equip3_pos_masterdata.group_pos_waiter') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cooker')
        user_pos_have_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_staff') or self.env.user.has_group('equip3_pos_masterdata.group_pos_supervisor') or self.env.user.has_group('equip3_pos_masterdata.group_pos_manager')
        if user_pos_not_create_edit and not user_pos_have_create_edit and 'active' in vals:
            raise Warning(_("Your user not have permission to archive/active products.")) 

        res = super(ProductProduct, self).write(vals)

        product_ids = []
        for product in self:
            if product.available_in_pos:
                if 'taxes_id' in vals:
                    raise UserError(_('You cannot change Tax a product saleable in point of sale while a session is still opened.'))

            product_ids.append(product.id)
        
        return res


    def pos_product_domain(self):
        return [('available_in_pos', '=', True)]


    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(ProductProduct, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        user_pos_not_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_cashier') or self.env.user.has_group('equip3_pos_masterdata.group_pos_waiter') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cooker')
        user_pos_have_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_staff') or self.env.user.has_group('equip3_pos_masterdata.group_pos_supervisor') or self.env.user.has_group('equip3_pos_masterdata.group_pos_manager')
        if user_pos_not_create_edit and not user_pos_have_create_edit:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        if self.env.user.has_group('equip3_pos_masterdata.group_pos_user') and not self.env.user.has_group('equip3_pos_masterdata.group_pos_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res