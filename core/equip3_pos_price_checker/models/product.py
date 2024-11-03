# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, api, _

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def all_scan_search(self, barcode):
        res = super(ProductProduct, self).all_scan_search(barcode)
        if barcode:
            product_id = self.search([('barcode','=',barcode)],limit=1)
            if product_id:
                sh_product_sale_price = res['sh_product_sale_price']
                split_sh_product_sale_price = sh_product_sale_price.split(' ')
                len_sh_product_sale_price = len(split_sh_product_sale_price)
                rev_price = "{:,.2f}".format(float(split_sh_product_sale_price[len_sh_product_sale_price-1]))
                res['sh_product_sale_price'] = sh_product_sale_price.replace(split_sh_product_sale_price[len_sh_product_sale_price-1],rev_price)
                
                sh_pricelist = []
                item_ids = self.env['product.pricelist.item'].search([])
                for item in item_ids:
                    if item.applied_on == '3_global':
                        sh_pricelist += ['Min Qty %s - %s %s' % (int(item.min_quantity), product_id.currency_id.symbol, "{:,.2f}".format(item.fixed_price))]
                    elif item.applied_on == '2_product_category' and item.categ_id.id == product_id.categ_id.id:
                        sh_pricelist += ['Min Qty %s - %s %s' % (int(item.min_quantity), product_id.currency_id.symbol, "{:,.2f}".format(item.fixed_price))]
                    elif item.applied_on == '1_product' and item.product_tmpl_id.id == product_id.product_tmpl_id.id:      
                        sh_pricelist += ['Min Qty %s - %s %s' % (int(item.min_quantity), product_id.currency_id.symbol, "{:,.2f}".format(item.fixed_price))]
                    elif item.applied_on == '0_product_variant' and item.product_id.id == product_id.id:
                        sh_pricelist += ['Min Qty %s - %s %s' % (int(item.min_quantity), product_id.currency_id.symbol, "{:,.2f}".format(item.fixed_price))]
                
                res['sh_product_pricelist'] = '<br/>'.join(sh_pricelist)
        return res
    
    @api.model
    def all_scan_search_pos_price_checker(self, barcode):
        stock_quant_obj = self.env['stock.quant']
        if barcode:
            product = self.search([('barcode','=',barcode)],limit=1)
            if product:
                result = {}
                stock_quant = stock_quant_obj.search([('product_id','=',product.id),('location_id.usage','=','internal')])
                quant_result = []
                for quant in stock_quant:
                    quant_result.append({
                        'name':quant.location_id.display_name,
                        'qty':quant.quantity
                    })
                if quant_result:
                    result['quant_result'] = quant_result

                if not product.image_1920:
                    result['need_image_default'] = '/web/image?model=product.product&field=image_1920&id='+str(product.id)+'&unique='
                if not result:
                    return False
                else:
                    return result
            else:
                return False
        else:
            return False