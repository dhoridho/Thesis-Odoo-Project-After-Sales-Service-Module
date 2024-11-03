# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, api, _

class Product_Product(models.Model):
    _inherit = 'product.product'
    
    @api.model
    def all_scan_search(self, barcode):
        if barcode:
            product_id = self.search([('barcode','=',barcode)],limit=1)
            if product_id:
                attribute_list = []
                if product_id.product_template_attribute_value_ids:
                    for attribute in product_id.product_template_attribute_value_ids:
                        attribute_list.append(str(attribute.product_attribute_value_id.name))
                attribute_str = ''
                attribute_str= ','.join(attribute_list)
                msg_dict = {
                    'issuccess':1, 'msg':_('Successfully Found Product corresponding to %(barcode)s') % {'barcode': barcode},
                    }
                if product_id.name:
                    msg_dict.update({
                        'sh_product_name':product_id.name,
                        })
                if product_id.default_code:
                    msg_dict.update({
                        'sh_product_code':product_id.default_code,
                        })
                if product_id.barcode:
                    msg_dict.update({
                        'sh_product_barcode':product_id.barcode,
                        })
                if product_id.image_1920:
                    msg_dict.update({
                        'sh_product_image':product_id.image_1920,
                        })
                if product_id.categ_id:
                    msg_dict.update({
                        'sh_product_category':product_id.categ_id.name,
                        })
                if attribute_str!='':
                    msg_dict.update({
                        'sh_product_attribute':attribute_str,
                        })
                else:
                    msg_dict.update({
                        'sh_product_attribute':'',
                        })
                model_id = self.env['ir.model'].sudo().search([('model','=','product.product')],limit=1)
                currency_field_id = self.env['ir.model.fields'].sudo().search([('name','=','currency_id'),('model_id','=',model_id.id)],limit=1)
                list_price_field_id = self.env['ir.model.fields'].sudo().search([('name','=','list_price'),('model_id','=',model_id.id)],limit=1)
                qty_available_field_id = self.env['ir.model.fields'].sudo().search([('name','=','qty_available'),('model_id','=',model_id.id)],limit=1)
                uom_field_id = self.env['ir.model.fields'].sudo().search([('name','=','uom_id'),('model_id','=',model_id.id)],limit=1)
                description_sale_field_id = self.env['ir.model.fields'].sudo().search([('name','=','description_sale'),('model_id','=',model_id.id)],limit=1)
                if model_id:
                    item_ids = self.env['product.pricelist.item'].search([])
                    sh_pricelist = []
                    for item in item_ids:
                        if item.applied_on == '3_global':
                            sh_pricelist += ['Min Qty %s - %s %s' % (int(item.min_quantity), product_id.currency_id.symbol, int(item.fixed_price))]
                        elif item.applied_on == '2_product_category' and item.categ_id.id == product_id.categ_id.id:
                            sh_pricelist += ['Min Qty %s - %s %s' % (int(item.min_quantity), product_id.currency_id.symbol, int(item.fixed_price))]
                        elif item.applied_on == '1_product' and item.product_tmpl_id.id == product_id.product_tmpl_id.id:      
                            sh_pricelist += ['Min Qty %s - %s %s' % (int(item.min_quantity), product_id.currency_id.symbol, int(item.fixed_price))]
                        elif item.applied_on == '0_product_variant' and item.product_id.id == product_id.id:
                            sh_pricelist += ['Min Qty %s - %s %s' % (int(item.min_quantity), product_id.currency_id.symbol, int(item.fixed_price))]

                    if currency_field_id and list_price_field_id:
                        msg_dict.update({
                            'sh_product_sale_price':str(product_id.currency_id.symbol)+" "+str(product_id.list_price),
                        })
                    elif currency_field_id and not list_price_field_id:
                        msg_dict.update({
                            'sh_product_sale_price':str(product_id.currency_id.symbol)+" "+str('0.0'),
                        })
                    else:
                        msg_dict.update({
                            'sh_product_sale_price':str('0.0'),
                        })
                    if qty_available_field_id and uom_field_id:
                        msg_dict.update({
                            'sh_product_stock':str(product_id.qty_available) + ' '+str(product_id.uom_id.name),
                            })
                    elif not qty_available_field_id and uom_field_id:
                        msg_dict.update({
                            'sh_product_stock':str('0.0') + ' '+str(product_id.uom_id.name),
                            })
                    if description_sale_field_id:
                        if product_id.description_sale:
                            msg_dict.update({
                            'sh_product_sale_description':product_id.description_sale,
                            })
                        else:
                            msg_dict.update({
                            'sh_product_sale_description':'',
                            })
                    else:
                        msg_dict.update({
                            'sh_product_sale_description':'',
                            })
                msg_dict.update({'sh_product_pricelist': '<br/>'.join(sh_pricelist)})
                return msg_dict
            else:
                return {'msg': _('Not Found Corresponding to %(barcode)s') % {'barcode': barcode}}