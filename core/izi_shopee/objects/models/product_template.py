# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError, MissingError
import base64
import time
import logging
_logger = logging.getLogger(__name__)
from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.izi_shopee.objects.utils.shopee.api import ShopeeAPI
from odoo.addons.izi_shopee.objects.utils.shopee.product import ShopeeProduct
from base64 import b64decode


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = 'Product Template'

    sp_account_ids = fields.Many2many('mp.account', 'sp_shop_id', string="Shopee Accounts", domain="[('marketplace', '=', 'shopee')]")
    sp_categ_id = fields.Many2one('mp.shopee.category', string="Shopee Category", required=False)
    sp_brands_id = fields.Many2one('mp.shopee.brand', string="Shopee Brand", required=False)
    sp_attributes_ids = fields.One2many('mp.shopee.attribute.line', 'product_tmpl_id', string="Attribute", copy=True)
    sp_condition = fields.Selection([('NEW', 'New'), ('USED', 'Used')], string="Shopee Condition", default='NEW')
    sp_item_dangerous = fields.Boolean(string='SP Item Dangerous', default=False)
    sp_logistic_ids = fields.One2many(comodel_name="mp.shopee.shop.logistic", inverse_name="shop_id",
                                        string="Shopee Logistics",
                                        required=False)
    sp_sales_price = fields.Float('Sale Price', digits='Shopee Product Price', default=100.0)

    def _compute_shopee_accounts(self):
        for shopee in self:
            shopee.sp_account_ids = self.env['mp.account'].search([('marketplace', '=', 'shopee'), ('active', '=', True)])

    # @api.onchange('list_price')
    # def _compute_sales_price(self):
    #     for res in self:
    #         if not res.sp_sales_price:
    #             res.sp_sales_price = res.list_price

    @api.constrains('sp_attributes_ids')
    def _check_mandatory_shopee_attributes(self):
        for res in self:
            if res.sp_attributes_ids:
                attribute_ids = res.sp_attributes_ids.filtered(lambda x: x.is_mandatory)
                for attr in attribute_ids:
                    if attr.is_mandatory and not attr.attribute_value_id:
                        raise ValidationError(
                            "Fields '%s' are mandatory. Please complete the fields." % attr.attribute_id.display_name)

    @api.onchange('sp_categ_id')
    def _onchange_shopee_attribute_product_template(self):
        self.ensure_one()
        for res in self:
            product_id = self.id
            if self.sp_categ_id:
                if not self.sp_attributes_ids:
                    attribute_line = [(5, 0)]
                    attrib_obj = self.env['mp.shopee.attribute'].search([('category_id', '=', self.sp_categ_id.id)])
                    if attrib_obj:
                        attribute_line += [(0, 0, {
                            'attribute_id': rec.id,
                            'attribute_value_id': False,
                            'category_id': self.sp_categ_id.id,
                            'product_tmpl_id': product_id,
                            'sp_attribute_name': rec.name,
                            'is_mandatory': rec.is_mandatory
                        }) for rec in attrib_obj]
                        self.sp_attributes_ids = attribute_line
                    else:
                        self.sp_attributes_ids = False
            else:
                self.sp_attributes_ids = False

    # @api.onchange('sp_categ_id')
    # def _onchange_shopee_attribute_product_template(self):
    #     self.ensure_one()
    #     for res in self:
    #         product_id = res.id
    #         if res.sp_categ_id:
    #             attrib_line_obj = self.env['mp.shopee.attribute.line'].search([(
    #                 'category_id', '=', res.sp_categ_id.id), ('product_tmpl_id', '=', product_id)])
    #             res.sp_attributes_ids = False
    #             attribute_line = [(5, 0)]
    #             if attrib_line_obj:
    #                 attribute_line += [(0, 0, {
    #                     'attribute_id': rec.attribute_id.id,
    #                     'attribute_value_id': rec.attribute_value_id.id,
    #                     'category_id': rec.category_id.id,
    #                     'product_tmpl_id': rec.product_tmpl_id.id
    #                 }) for rec in attrib_line_obj]
    #                 res.sp_attributes_ids = attribute_line
    #             else:
    #                 attrib_obj = self.env['mp.shopee.attribute'].search([('category_id', '=', res.sp_categ_id.id)])
    #                 if attrib_obj:
    #                     attribute_line += [(0, 0, {
    #                         'attribute_id': rec.id,
    #                         'attribute_value_id': False,
    #                         'category_id': res.sp_categ_id.id,
    #                         'product_tmpl_id': product_id
    #                     }) for rec in attrib_obj]
    #                     res.sp_attributes_ids = attribute_line
    #         else:
    #             res.sp_attributes_ids = False

    @mp.shopee.capture_error
    def shopee_add_product(self, **kw):
        self.ensure_one()
        sp_shop_obj = self.env['mp.shopee.shop']
        sp_logistic_obj = self.env['mp.shopee.shop.logistic']
        mp_map_product_obj = self.env['mp.map.product']
        country_code = self.env.company.country_id.code
        if country_code and country_code == 'ID':
            original_price = 100 if self.sp_sales_price < 100 else int(self.sp_sales_price)
        else:
            original_price = 1.00 if self.sp_sales_price < 0.00 else self.sp_sales_price

        # if not self.mp_product_image_ids:
        #     raise ValidationError('Image not found. Please fill the picture.')
        spd_item_ids = []
        if not self.sp_account_ids:
            raise UserError('Shopee account not found. Please set your account first.')
        for account in self.sp_account_ids:
            if account.mp_token_id.state == 'valid':
                account_params = {
                    'access_token': account.mp_token_id.name
                }
                sp_account = account.shopee_get_account(**account_params)
                sp_product = ShopeeProduct(sp_account)
                sp_shop_id = sp_shop_obj.search([('mp_account_id', '=', account.id)], limit=1).id
                sp_logistic = sp_logistic_obj.search([('shop_id', '=', sp_shop_id)])
                api = ShopeeAPI(sp_account)
                mp_product_ids = []
                quantity_on_hand = 0
                product_obj = self.env['product.product'].search(
                    [('product_tmpl_id', '=', self.id)])
                for product in product_obj:
                    quantities = product.with_context(warehouse=account.warehouse_id.id,
                                                       location=False)._compute_quantities_dict(None, None, None)
                    quantity_on_hand += quantities[product.id]['qty_available']

                # try:
                preprocessed_request = {}
                processed_requests = {}
                if sp_logistic:
                    preprocessed_request['logistic_info'] = []
                    for logist in sp_logistic:
                        preprocessed_request['logistic_info'].append({
                            'enabled': logist.enabled,
                            'logistic_id': int(logist.logistic_id.logistics_channel_id)
                        })
                if self.mp_product_wholesale_ids:
                    preprocessed_request['wholesale'] = []
                    for wsl_data in self.mp_product_wholesale_ids:
                        preprocessed_request['wholesale'].append({
                            'min_count': wsl_data.min_qty,
                            'max_count': wsl_data.max_qty,
                            'unit_price': wsl_data.price,
                        })
                if self.sp_attributes_ids:
                    attribute_list = []
                    value_list = []
                    for recattr in self.sp_attributes_ids:
                        value_list.append({
                        })
                        value_id = 0
                        if recattr.attribute_value_id:
                            if not recattr.attribute_value_id.value_id:
                                if recattr.attribute_id.input_type == 'TEXT_FILED':
                                    value_id = 1
                                elif recattr.attribute_id.input_type == 'COMBO_BOX' or recattr.attribute_id.input_type == 'MULTIPLE_SELECT_COMBO_BOX':
                                    value_id = 2
                                else:
                                    value_id = 0

                            attribute_list.append({
                                'attribute_id': int(recattr.attribute_id.attribute_id),
                                'attribute_value_list': [{
                                    'value_id': int(recattr.attribute_value_id.value_id) or value_id,
                                    'original_value_name': recattr.attribute_value_id.name or '',
                                    'value_unit': recattr.attribute_value_id.value_unit or ''
                                }]
                            })
                    preprocessed_request['attribute_list'] = attribute_list
                if self.mp_product_image_ids:
                    image_id_list = []
                    for image_id in self.mp_product_image_ids:
                        image_prepared_request = api.build_request(
                            'set_product_image',
                            sp_account.partner_id,
                            sp_account.partner_key,
                            sp_account.shop_id,
                            sp_account.host,
                            sp_account.access_token, **{
                                'data': {
                                    'scene': 'normal',
                                },
                                'files': {
                                    'image': ('image.png', b64decode(image_id.image), 'image/png')
                                }
                            })
                        image_prepared_request['headers'] = None
                        image_process_response = api.process_response(
                            'set_product_image', api.request(**image_prepared_request))
                        if 'message' in image_process_response and image_process_response.get('message') != '':
                            raise UserError('Shopee API error with the code: %s caused by %s' % (
                            image_process_response.get('error'), image_process_response.get('message')))
                        if image_process_response.get('image_info', {}).get('image_id'):
                            image_id_list.append(image_process_response['image_info']['image_id'])
                        # else:
                        #     self.env['mp.base']._logger(self.marketplace, 'Product image %s failed to update' % (
                        #         kw['data'].name), notify=True, notif_sticky=False)
                    if image_id_list:
                        preprocessed_request['image'] = {'image_id_list': image_id_list}

                if self.sp_brands_id:
                    mp_brand = {
                        'brand_id': self.sp_brands_id.brand_id,
                        'original_brand_name': self.sp_brands_id.name,
                    }
                else:
                    mp_brand = {
                        'brand_id': 0,
                        'original_brand_name': 'NoBrand',
                    }
                # original_price = self.sp_sales_price if self.sp_sales_price > 0 else 100
                seller_stock = int(quantity_on_hand) if int(quantity_on_hand) > 0 else 0
                processed_requests.update({
                    'json': {
                        'item_name': self.name,
                        'category_id': self.sp_categ_id.category_id,
                        'item_sku': '' if not self.default_code else self.default_code,
                        'condition': self.sp_condition,
                        'original_price': original_price,
                        "seller_stock": [
                            {
                                "stock": seller_stock
                            }
                        ],
                        'normal_stock': seller_stock,
                        'weight': 1.0 if self.weight <= 0 else self.weight,
                        'item_status': 'NORMAL',
                        'item_dangerous': 0 if self.sp_item_dangerous == False else 1,
                        'dimension': {
                            'package_height': 1 if self.mp_height == 0 else int(self.mp_height),
                            'package_length': 1 if self.mp_length == 0 else int(self.mp_length),
                            'package_width': 1 if self.mp_width == 0 else int(self.mp_width)
                        },
                        'brand': mp_brand,
                        'description_type': "normal",
                        'description': 'self description' if not self.description else self.description,
                        **preprocessed_request,
                    }
                })

                if self.sp_item_id and (self.sp_item_id != '' or self.sp_item_id != '0'):
                    response_set_detail = sp_product.set_product_detail(item_id=int(self.sp_item_id), item_data=processed_requests)
                    if 'message' in response_set_detail and response_set_detail.get('message') != '':
                        raise UserError('Shopee API error with the code: %s caused by %s' % (
                            response_set_detail.get('error'), response_set_detail.get('message')))
                    time.sleep(5)
                    ###update stock
                    response_set_stock = sp_product.set_product_stock(item_id=int(self.sp_item_id),
                                                                      stock=seller_stock)
                    if 'message' in response_set_stock and response_set_stock.get('message') != '':
                        raise UserError('Shopee API error with the code: %s caused by %s' % (
                            response_set_stock.get('error'), response_set_stock.get('message')))
                    time.sleep(5)
                    ### update price
                    response_set_price = sp_product.set_product_price(item_id=int(self.sp_item_id), price=original_price)
                    if 'message' in response_set_price and response_set_price.get('message') != '':
                        raise UserError('Shopee API error with the code: %s caused by %s' % (
                            response_set_price.get('error'), response_set_price.get('message')))
                else:
                    prepared_request = api.build_request(
                        'add_new_product',
                        sp_account.partner_id,
                        sp_account.partner_key,
                        sp_account.shop_id,
                        sp_account.host,
                        sp_account.access_token, **processed_requests)
                    process_response = api.process_response('add_new_product', api.request(**prepared_request))
                    if 'message' in process_response and process_response.get('message') != '':
                        raise UserError('Shopee API error with the code: %s caused by %s' % (
                        process_response.get('error'), process_response.get('message')))
                    if process_response and 'item_id' in process_response:
                        sp_item = process_response.get('item_id')
                    else:
                        sp_item = None
                    self.sp_item_id = sp_item
                    spd_item_ids.append({
                        'name': sp_item,
                        'product_tmpl_id': self.id,
                        'sp_account_id': account.id
                    })
                    # if self.product_variant_ids:
                    if self.mp_attribute_value_ids:
                        variant_prepared_request = api.build_request(
                            'add_new_variation',
                            sp_account.partner_id,
                            sp_account.partner_key,
                            sp_account.shop_id,
                            sp_account.host,
                            sp_account.access_token, **{
                                'json': self.shopee_add_item_variation(sp_item)
                            })
                        variant_prepared_request['headers'] = None
                        variant_process_response = api.process_response(
                            'add_new_variation', api.request(**variant_prepared_request))
                        if 'message' in variant_process_response and variant_process_response.get('message') != '':
                            raise UserError('Shopee API error with the code: %s caused by %s' % (
                            variant_process_response.get('error'), variant_process_response.get('message')))
                    # mp_product_ids.append(int(process_response.get('item_id')))
                    # account.shopee_get_products(**{'product_ids': mp_product_ids})
                mp_product_ids.append(int(self.sp_item_id))
                account.shopee_get_products(**{'product_ids': mp_product_ids})
                # self.env['mp.base']._logger(self.marketplace, 'Product %s has been posted' %
                #                             (kw['data'].name), notify=True, notif_sticky=False)
                # except Exception as e:
                #     self.env['mp.base']._logger('shopee', e, notify=True, notif_sticky=False)
            else:
                raise UserError('Access Token is invalid, Please Reauthenticated Shopee Account')
        # self.sp_item_ids = [(6, 0, spd_item_ids)]
        mp_map_product_obj.action_start()


    def shopee_add_item_variation(self, item_id):
        if not item_id:
            raise ValidationError("Item ID: %s. Record does not exist or has been deleted." % (item_id))
        product_ids = self.env['product.product'].search([('product_tmpl_id', '=', self.id), ('combination_indices', '!=', False)])
        product_template_attribute_obj = self.env['product.template.attribute.value']
        attr_product = {
            'item_id': item_id
        }
        tier_variation = []
        tier1_opt_list = []
        tier1_option = []
        tier2_option = []
        tier1_variation = []
        tier2_variation = []
        tier2_opt_list = []
        model_list = []
        x = 0
        y = 0
        if product_ids:
            i = 0
            attribute_id = 0
            attributes = {}
            for product in product_ids:
                if product.combination_indices:
                    resplit = product.combination_indices.split(",")
                    lensplit = len(resplit)
                    if lensplit > 1:
                        option1 = product_template_attribute_obj.search([('id', '=', int(resplit[0]))])
                        option2 = product_template_attribute_obj.search([('id', '=', int(resplit[1]))])
                        if option1.product_attribute_value_id.name and not option1.product_attribute_value_id.name in tier1_option:
                            tier1_option.append(option1.product_attribute_value_id.name)
                            tier1_opt_list.append({
                                'option': option1.product_attribute_value_id.name
                            })
                        if option1.attribute_id.name and not option1.attribute_id.name in tier1_variation:
                            tier1_variation.append(option1.attribute_id.name)
                            tier_variation.append({
                                'name': option1.attribute_id.name,
                                'option_list': tier1_opt_list
                            })

                        if option2.product_attribute_value_id.name and not option2.product_attribute_value_id.name in tier2_option:
                            tier2_option.append(option2.product_attribute_value_id.name)
                            tier2_opt_list.append({
                                'option': option2.product_attribute_value_id.name
                            })

                        if option2.attribute_id.name and not option2.attribute_id.name in tier2_variation:
                            tier2_variation.append(option2.attribute_id.name)
                            tier_variation.append({
                                'name': option2.attribute_id.name,
                                'option_list': tier2_opt_list
                            })
                        x = tier1_option.index(option1.product_attribute_value_id.name)
                        y = tier2_option.index(option2.product_attribute_value_id.name)
                        tier_model_index = [x, y]
                        model_list.append({
                            'tier_index': tier_model_index,
                            'original_price': int(product.variant_price) if product.variant_price > 100 else 100,
                            'model_sku': '' if not product.default_code else product.default_code,
                            # 'normal_stock': int(product.normal_stock)
                            'seller_stock': [{
                                'stock': int(product.normal_stock)
                            }]
                        })
                    else:
                        option1 = product_template_attribute_obj.search([('id', '=', int(resplit[0]))])
                        if option1.product_attribute_value_id.name and not option1.product_attribute_value_id.name in tier1_option:
                            tier1_option.append(option1.product_attribute_value_id.name)
                            tier1_opt_list.append({
                                'option': option1.product_attribute_value_id.name
                            })
                        if option1.attribute_id.name and not option1.attribute_id.name in tier1_variation:
                            tier1_variation.append(option1.attribute_id.name)
                            tier_variation.append({
                                'name': option1.attribute_id.name,
                                'option_list': tier1_opt_list
                            })
                        x = tier1_option.index(option1.product_attribute_value_id.name)
                        tier_model_index = [x]
                        model_list.append({
                            'tier_index': tier_model_index,
                            'original_price': int(product.variant_price) if product.variant_price > 100 else 100,
                            'model_sku': '' if not product.default_code else product.default_code,
                            # 'normal_stock': int(product.normal_stock)
                            'seller_stock': [{
                                'stock': int(product.normal_stock)
                            }]
                        })

            attr_product.update({
                'tier_variation': tier_variation,
                'model': model_list
            })
            return attr_product

    def action_get_shopee_attribute(self):
        if not self.sp_categ_id:
            raise ValidationError('Shopee category not found!')
        if not self.sp_account_ids:
            raise UserError('Shopee account not found!')
        self.sp_attributes_ids = False
        sp_account = self.sp_account_ids[0]
        sp_account.shopee_get_attribute_by_category(self.sp_categ_id.category_id)
        self._onchange_shopee_attribute_product_template()