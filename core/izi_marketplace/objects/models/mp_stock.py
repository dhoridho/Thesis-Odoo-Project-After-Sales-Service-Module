# -*- coding: utf-8 -*-
# model tambahan 07/30/2024

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class MPStock(models.Model):
    _name = 'mp.stock'
    _description = 'Marketplace Stock'

    name = fields.Char(string='Name', index=True, required=True)
    mp_account_id = fields.Many2one('mp.account', string='Marketplace Account')
    product_id = fields.Many2one('product.product', string='Marketplace Product')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse Marketplace')
    marketplace = fields.Char(string="Marketplace")
    company_id = fields.Many2one(related="mp_account_id.company_id")
    stock = fields.Float(string='Stock', default=0)

    @api.model
    def mp_create_update_stock(self, mp_account_id=None, raw_product=None, map_type='product'):
        if not raw_product:
            raise ValidationError('Product datas not found for marketplace create/update stock')
        mp_account = self.env['mp.account'].browse(mp_account_id)
        products = self._get_product_from_map_line(mp_account, raw_product, map_type)
        if products:
            for item in products:
                mp_stock_obj = self.env['mp.stock'].search(
                    [('mp_account_id', '=', mp_account.id), ('product_id', '=', item.get('product_id'))])
                if not mp_stock_obj:
                    res = mp_stock_obj.create(item)
                else:
                    res = mp_stock_obj.write(item)
        else:
            res = False
        return res

    def _get_product_from_map_line(self, mp_account, raw_products, map_type):
        map_products = []
        cr = self.env.cr
        query = '''SELECT product_id FROM mp_map_product_line WHERE state = 'mapped' AND mp_account_id = %s '''
        if map_type == 'product':
            product_ids = self._get_mp_product(mp_account, raw_products)
            if product_ids:
                for row in product_ids:
                    cr.execute(query + 'AND mp_product_id = %s LIMIT 1', (mp_account.id, row.get('mp_product_id')))
                    res_cr = cr.fetchone()
                    if res_cr:
                        map_products.append({
                            'name': mp_account.name,
                            'mp_account_id': mp_account.id,
                            'product_id': res_cr and res_cr[0] or False,
                            'warehouse_id': mp_account.warehouse_id.id,
                            'marketplace': mp_account.marketplace,
                            'stock': row.get('seller_stock')
                        })
        else:
            variant_ids = self._get_mp_product_variant(mp_account, raw_products)
            if variant_ids:
                for row in variant_ids:
                    cr.execute(query + 'AND mp_product_variant_id = %s LIMIT 1', (mp_account.id, row.get('mp_variant_id')))
                    res_cr = cr.fetchone()
                    if res_cr:
                        map_products.append({
                            'name': mp_account.name,
                            'mp_account_id': mp_account.id,
                            'product_id': res_cr and res_cr[0] or False,
                            'warehouse_id': mp_account.warehouse_id.id,
                            'marketplace': mp_account.marketplace,
                            'stock': row.get('seller_stock')
                        })
        return map_products

    def _get_mp_product(self, mp_account, raw_products):
        mp_products = []
        cr = self.env.cr
        query = '''SELECT id FROM mp_product WHERE mp_account_id = %s AND mp_external_id = %s LIMIT 1'''
        if mp_account.marketplace == 'shopee':
            for item in raw_products:
                if 'stock_info_v2' in item and 'seller_stock' in item['stock_info_v2']:
                    stock = item['stock_info_v2']['seller_stock'][0]['stock']
                else:
                    stock = 0
                cr.execute(query, (mp_account.id, str(item.get('item_id'))))
                res_cr = cr.fetchone()
                if res_cr:
                    mp_products.append({
                        'mp_product_id': res_cr and res_cr[0] or False,
                        'seller_stock': stock
                    })
        elif mp_account.marketplace == 'tokopedia':
            for item in raw_products:
                if 'stock' in item and 'value' in item['stock']:
                    stock = item['stock']['value']
                else:
                    stock = 0
                cr.execute(query, (mp_account.id, str(item['basic']['productID'])))
                res_cr = cr.fetchone()
                if res_cr:
                    mp_products.append({
                        'mp_product_id': res_cr and res_cr[0] or False,
                        'seller_stock': stock
                    })
        elif mp_account.marketplace == 'lazada':
            for item in raw_products:
                mp_products.append(item.get('item_id'))
        elif mp_account.marketplace == 'tiktok':
            # for item in raw_products:
            if 'stock_infos' in raw_products and 'available_stock' in raw_products['stock_infos'][0]:
                stock = raw_products['stock_infos'][0]['available_stock']
            else:
                stock = 0
            cr.execute(query, (mp_account.id, raw_products['product_id']))
            res_cr = cr.fetchone()
            if res_cr:
                mp_products.append({
                    'mp_product_id': res_cr and res_cr[0] or False,
                    'seller_stock': stock
                })

        return mp_products

    def _get_mp_product_variant(self, mp_account, raw_products):
        product_variants = []
        cr = self.env.cr
        query = '''SELECT id FROM mp_product_variant WHERE mp_account_id = %s AND mp_external_id = %s LIMIT 1'''
        if mp_account.marketplace == 'shopee':
            for item in raw_products:
                cr.execute(query, (mp_account.id, str(item.get('sp_variant_id'))))
                res_cr = cr.fetchone()
                if res_cr:
                    product_variants.append({
                        'mp_variant_id': res_cr and res_cr[0] or False,
                        'seller_stock': item.get('sp_variant_stock')
                    })
        elif mp_account.marketplace == 'tokopedia':
            for item in raw_products:
                if 'stock' in item and 'value' in item['stock']:
                    stock = item['stock']['value']
                else:
                    stock = 0
                cr.execute(query, (mp_account.id, str(item['basic']['productID'])))
                res_cr = cr.fetchone()
                if res_cr:
                    product_variants.append({
                        'mp_variant_id': res_cr and res_cr[0] or False,
                        'seller_stock': stock
                    })
        elif mp_account.marketplace == 'lazada':
            for item in raw_products:
                product_variants.append(item.get('item_id'))
        elif mp_account.marketplace == 'tiktok':
            skus = raw_products.get('skus', [])
            if skus:
                for item in skus:
                    if 'stock_infos' in raw_products and 'available_stock' in raw_products['stock_infos'][0]:
                        stock = raw_products['stock_infos'][0]['available_stock']
                    else:
                        stock = 0
                    cr.execute(query, (mp_account.id, item['id']))
                    res_cr = cr.fetchone()
                    if res_cr:
                        product_variants.append({
                            'mp_variant_id': res_cr and res_cr[0] or False,
                            'seller_stock': stock
                        })
        return product_variants