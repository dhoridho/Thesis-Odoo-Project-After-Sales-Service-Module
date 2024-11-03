# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro
import hashlib
import json
import base64
import tempfile, shutil
import os
import codecs
import io
import logging
import requests
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError, MissingError
from odoo.addons.izi_tiktok.models.utils.product import TiktokProduct
from odoo.addons.izi_tiktok.models.utils.api import TiktokAPI
from odoo.tools import image_process, image_to_base64, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta
from PIL import Image
from pathlib import Path

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = 'Product Template'

    tts_account_ids = fields.Many2many('mp.account', 'tts_shop_id', string="Tiktok Accounts", domain="[('marketplace', '=', 'tiktok')]")
    tts_categ_id = fields.Many2one('mp.tiktok.product.category', string="Tiktok Category", required=False)
    tts_brand_id = fields.Many2one('mp.tiktok.brand', string="Tiktok Brand", required=False)
    tts_attributes_ids = fields.One2many('mp.tiktok.product.attribute.line', 'product_tmpl_id', string="Tiktok Attribute", copy=True)
    tts_logistic_ids = fields.One2many(comodel_name="mp.tiktok.logistic", inverse_name="shop_id",
                                        string="Tiktok Logistics",
                                        required=False)
    tts_sales_price = fields.Float('Sale Price', digits='Tiktok Product Price', default=100.0)
    tts_is_cod_allowed = fields.Boolean('Is COD Allowed', default=False)
    tts_is_not_for_sale = fields.Boolean('Is Not For Sale', default=False)


    def _compute_tiktok_accounts(self):
        for tiktok in self:
            tiktok.tts_account_ids = self.env['mp.account'].search([('marketplace', '=', 'tiktok'), ('active', '=', True)])

    @api.onchange('tts_categ_id')
    def _onchange_set_attribute_tiktok(self):
        product_id = self.id
        if self.tts_categ_id:
            attribs_line_obj = self.env['mp.tiktok.attribute.line'].search([('category_id', '=', self.tts_categ_id.id), ('product_tmpl_id', '=', product_id)])
            if not attribs_line_obj:
                attributes_line = [(5, 0)]
                attribs_obj = self.env['mp.tiktok.attribute'].search([('category_id', '=', self.tts_categ_id.id)])
                if attribs_obj:
                    attributes_line += [(0, 0, {
                        'attribute_id': recs.id,
                        'attribute_value_id': False,
                        'category_id': self.tts_categ_id.id,
                        'product_tmpl_id': product_id
                    }) for recs in attribs_obj]
                    self.tts_attributes_ids = attributes_line
                else:
                    self.tts_attributes_ids = False
            else:
                self.tts_attributes_ids = [(6, 0, attribs_line_obj.ids)]
        else:
            self.tts_attributes_ids = False

    def tiktok_add_product(self, **kw):
        _notify = self.env['mp.base']._notify
        self.ensure_one()
        tts_shop_obj = self.env['mp.tiktok.shop']
        tts_logistic_obj = self.env['mp.tiktok.shop.logistic']
        mp_map_product_obj = self.env['mp.map.product']
        # if not self.mp_product_image_ids:
        #     raise ValidationError('Image not found. Please fill the picture.')
        tts_item_ids = []
        if not self.tts_account_ids:
            raise UserError('Tiktok account not found. Please set your account first.')
        for account in self.tts_account_ids:
            params = {}
            tts_account = account.tiktok_get_account()
            tts_product = TiktokProduct(tts_account, api_version="v3")
            # _notify('info', 'Upload product from {} is started... Please wait!'.format('Tiktok'),
            #         notif_sticky=False)

            tts_shop_id = tts_shop_obj.search([('mp_account_id', '=', account.id)])
            mp_product_ids = []
            mp_product_data = []
            quantity_on_hand = 0
            product_obj = self.env['product.product'].search(
                [('product_tmpl_id', '=', self.id)])
            for product in product_obj:
                quantities = product.with_context(warehouse=account.warehouse_id.id,
                                                  location=False)._compute_quantities_dict(None, None, None)
                quantity_on_hand += quantities[product.id]['qty_available']
            try:
                product_data = {
                    'name': self.name,
                    'condition': self.tts_condition,
                    'Description': "" if not self.description else self.description,
                    'sku': '' if not self.default_code else self.default_code.strip(),
                    'price_currency': "IDR",
                    'price': int(self.tts_sales_price) if self.tts_sales_price > 100 else 100,
                    'status': self.tts_stock_status,
                    'min_order': self.min_order,
                    'category_id': self.tts_categ_id.category_id,
                    'dimension': {
                            'height': 1 if self.mp_height == 0 else int(self.mp_height),
                            'width': 1 if self.mp_width == 0 else int(self.mp_width),
                            'length': 1 if self.mp_length == 0 else int(self.mp_length),
                    },
                    'weight': 1 if self.weight < 1 else int(self.weight),
                    'weight_unit': self.weight_uom_name.upper(),
                    'is_free_return': self.is_free_return,
                    'is_must_insurance': self.is_must_insurance,
                }
                if self.mp_product_wholesale_ids:
                    wholesale = []
                    for wsl_data in self.mp_product_wholesale_ids:
                        wholesale.append({
                            'min_qty': wsl_data.min_qty,
                            'price': wsl_data.price,
                        })

                    product_data.update({
                        'wholesale': wholesale
                    })
                if self.tts_logistic_ids:
                    prologist = []
                    for logist in self.tts_logistic_ids:
                        prologist.append(int(logist.logistic_id.shipper_id))
                    product_data.update({
                        'custom_product_logistics': prologist
                    })

                if self.mp_attribute_value_ids:
                    product_data.update({
                        'variant': self.tiktok_add_item_variation()
                    })

                if self.tts_attributes_ids:
                    attribute_ids = []
                    for attrib in self.tts_attributes_ids:
                        attribute_ids.append(str(attrib.attribute_value_id.value_id))
                    product_data.update({
                        'annotations': attribute_ids
                    })

                if self.mp_product_image_ids:
                    image_id_list = []
                    date_today = datetime.now().strftime("%Y/%m/%d")
                    url_image = "https://8.215.31.36"
                    attachment_object = self.env['ir.attachment']
                    base_image_url = self.env['ir.config_parameter'].sudo().get_param('web.image.url')
                    # work_dir = '/tmp/product-%s/%s/%s/' % (self.id, date_today, tts_shop_id.shop_id)
                    # work_dir = '/img/cache/700/product-1/%s/%s/' % (date_today, tts_shop_id.shop_id)
                    base_path = '/var/www/html'
                    image_path = 'marketplace/img/tiktok/product-%s/' % (self.id)
                    work_dir = os.path.join(base_path, image_path)
                    try:
                        os.umask(0)
                        os.makedirs(work_dir, mode=0o777, exist_ok=True)
                        # _logger.error('Directory %s created successfully.' % (work_dir))
                    except OSError as error:
                        _logger.error('%s: %s' % (error, work_dir))
                    x = 0
                    for imagine in self.mp_product_image_ids:
                        if x < 5:
                            # image_obj = self.image2jpg(imagine.image)
                            image_data = base64.b64decode(imagine.image)
                            temporary_obj = tempfile.NamedTemporaryFile(dir=work_dir, delete=False)
                            filename = temporary_obj.name
                            temporary_obj.write(image_data)
                            temporary_obj.close()
                            mime_type = attachment_object.sudo().search([
                                ('res_model', '=', 'product.template.image'),
                                ('res_field', '=', 'image'),
                                ('res_id', '=', imagine.id)
                            ]).mimetype
                            try:
                                filename_without_path = tts_shop_id.shop_id + '_' + hashlib.md5(
                                    filename.encode('utf-8')).hexdigest()
                                generate_filename = work_dir + filename_without_path
                                if mime_type == 'image/png':
                                    temp_filename = r'%s' % (filename)
                                    tiktok_filename = generate_filename + '.png'
                                    new_filename = r'%s' % (tiktok_filename)
                                    filename_without_path = filename_without_path + '.png'
                                    os.rename(temp_filename, new_filename)
                                elif mime_type == 'image/jpeg':
                                    temp_filename = r'%s' % (filename)
                                    tiktok_filename = generate_filename + '.jpg'
                                    new_filename = r'%s' % (tiktok_filename)
                                    filename_without_path = filename_without_path + '.jpg'
                                    os.rename(temp_filename, new_filename)
                                else:
                                    _logger.info('Image has wrong image format, please use images with extensions [.jpg, .jpeg, .png]')
                                    # temp_filename = r'%s' % (filename)
                                    # tiktok_filename = generate_filename
                                    # new_filename = r'%s' % (tiktok_filename)
                                    # os.rename(temp_filename, new_filename)
                                os.chmod(tiktok_filename, 0o777)
                                # tiktok_image = url_image + tiktok_filename
                                # tiktok_image = "http://8.215.31.36/" + image_path + filename_without_path
                                tiktok_image = base_image_url + image_path + filename_without_path
                                image_id_list.append({
                                    'file_path': tiktok_image
                                })
                            except Exception as error:
                                _logger.error('%s: %s' % (error, filename))
                            # finally:
                            #     os.unlink(filename)
                        x += 1
                    product_data.update({
                        'pictures': image_id_list
                    })
                if self.tts_item_id and self.tts_item_id != 0:
                    product_data.update({
                        'id': int(self.tts_item_id)
                    })
                    api = TiktokAPI(tts_account)
                    ###self.tts_shop_id.mp_external_id
                    params = ({
                        'shop_id': tts_shop_id.shop_id
                    })
                    mp_product_data.append(product_data)
                    prepared_request = api.build_request('set_product_detail', **{
                        'params': params,
                        'json': {
                            'products': mp_product_data
                        }
                    })
                    process_response = api.process_response('set_product_detail', api.request(**prepared_request))
                    # _logger.info('Update Response: %s' % (process_response))
                    account.tiktok_get_products(**{'product_ids': int(self.tts_item_id)})
                    # self.env['mp.base']._logger('tiktok', 'Product %s updated' %
                    #                             (kw['data'].name), notify=True, notif_sticky=False)
                else:
                    product_data.update({
                        'stock': 1,
                    })
                    mp_product_data.append(product_data)
                    # _logger.info('Product Data: %s' % (product_data))
                    var_response = tts_product.create_new_product(shop_id=tts_shop_id.shop_id,
                                                               products=mp_product_data)
                    if var_response.status_code == 200:
                        tts_product_raw = json.loads(var_response.text, strict=False)['data']
                        # _logger.info('Response from Tiktok: %s' % (tts_product_raw))
                        if tts_product_raw:
                            if 'error' in tts_product_raw:
                                raise ValidationError(tts_product_raw.get("error"))
                            if 'success_rows_data' in tts_product_raw:
                                product_ids = tts_product_raw.get("success_rows_data")
                                for product in product_ids:
                                    self.tts_item_id = product.get('product_id')
                                    tts_item_ids.append({
                                        'name': product.get('product_id'),
                                        'product_tmpl_id': self.id,
                                        'tts_account_id': account.id
                                    })
                                # mp_product_ids.append(int(product_ids.product_id))
                                account.tiktok_get_products(**{'product_ids': int(self.tts_item_id)})
                                shutil.rmtree(work_dir, ignore_errors=True)
                                # self.env['mp.base']._logger('tiktok', 'Product %s has been posted' %
                                #                             (kw['data'].name), notify=True, notif_sticky=False)
            except Exception as e:
                self.env['mp.base']._logger('tiktok', e, notify=True, notif_sticky=False)
        # self.tts_item_ids = [(6, 0, tts_item_ids)]
        mp_map_product_obj.action_start()


    def image2jpg(self, content):
        if not content:
            return False
        if isinstance(content, str):
            content = content.encode('ascii')

        try:
            image_stream = io.BytesIO(codecs.decode(content, 'base64'))
            image = Image.open(image_stream)
            image_w, image_h = image.size
            if image_h < 500 or image_w < 500:
                w = int(500 * image_w / image_h)
                h = 500
            elif image_h > 700 or image_w > 700:
                w = int(700 * image_w / image_h)
                h = 700
            else:
                w = image_w
                h = image_h
            if image.mode == 'P':
                if 'transparency' in image.info:
                    alpha = image.convert('RGBA').split()[-1]
                    bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
                    bg.paste(image, mask=alpha)
                image = image.convert('RGB')
            opt = {'format': 'JPEG', 'optimize': True, 'quality': 80}
            to_base64 = image_to_base64(image, **opt)
            ret = image_process(to_base64, size=(w, h), quality=80, output_format='JPEG')
        except Exception as _e:
            ret = False
            # _logger.error('Could not convert image to JPG.')

        return ret

    def tiktok_add_item_variation(self):
        product_ids = self.env['product.product'].search([('product_tmpl_id', '=', self.id), ('combination_indices', '!=', False)])
        product_template_attribute_obj = self.env['product.template.attribute.value']
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
                # if product.variant_price < 100:
                #     raise ValidationError('Please set variant price with minimum value: 100.')
                # if product.normal_stock < 1:
                #     raise ValidationError('Please set stock with minimum value: 1.')
                if product.combination_indices:
                    resplit = product.combination_indices.split(",")
                    lensplit = len(resplit)
                    if lensplit > 1:
                        option1 = product_template_attribute_obj.search([('id', '=', int(resplit[0]))])
                        option2 = product_template_attribute_obj.search([('id', '=', int(resplit[1]))])
                        if option1.product_attribute_value_id.name and not option1.product_attribute_value_id.name in tier1_option:
                            tier1_option.append(option1.product_attribute_value_id.name)
                            tier1_opt_list.append({
                                'hex_code': '' if not option1.product_attribute_value_id.hex else option1.product_attribute_value_id.hex,
                                'unit_value_id': option1.product_attribute_value_id.unit_value_id,
                                'value': option1.product_attribute_value_id.name
                            })
                        if option1.attribute_id.name and not option1.attribute_id.name in tier1_variation:
                            tier1_variation.append(option1.attribute_id.name)
                            tier_variation.append({
                                'id': option1.attribute_id.variant_id,
                                'unit_id': 0 if not option1.product_attribute_value_id.attribute_unit_id else option1.product_attribute_value_id.attribute_unit_id.id,
                                'options': tier1_opt_list
                            })

                        if option2.product_attribute_value_id.name and not option2.product_attribute_value_id.name in tier2_option:
                            tier2_option.append(option2.product_attribute_value_id.name)
                            tier2_opt_list.append({
                                'hex_code': '' if not option1.product_attribute_value_id.hex else option1.product_attribute_value_id.hex,
                                'unit_value_id': option1.product_attribute_value_id.unit_value_id,
                                'value': option2.product_attribute_value_id.name
                            })

                        if option2.attribute_id.name and not option2.attribute_id.name in tier2_variation:
                            tier2_variation.append(option2.attribute_id.name)
                            tier_variation.append({
                                'id': option2.attribute_id.variant_id,
                                'unit_id': 0 if not option1.product_attribute_value_id.attribute_unit_id else option1.product_attribute_value_id.attribute_unit_id.id,
                                'options': tier2_opt_list
                            })
                        x = tier1_option.index(option1.product_attribute_value_id.name)
                        y = tier2_option.index(option2.product_attribute_value_id.name)
                        tier_model_index = [x, y]
                        if i == 0:
                            model_list.append({
                                'is_primary': True,
                                'status': product.product_tmpl_id.tts_stock_status,
                                'price': int(product.variant_price) if product.variant_price > 100 else 100,
                                'sku': '' if not product.default_code else product.default_code,
                                'stock': product.normal_stock,
                                'combination': tier_model_index,
                            })
                        else:
                            model_list.append({
                                'status': product.product_tmpl_id.tts_stock_status,
                                'price': int(product.variant_price) if product.variant_price > 100 else 100,
                                'sku': '' if not product.default_code else product.default_code,
                                'stock': product.normal_stock,
                                'combination': tier_model_index,
                            })
                        i += 1
                    else:
                        option1 = product_template_attribute_obj.search([('id', '=', int(resplit[0]))])
                        if option1.product_attribute_value_id.name and not option1.product_attribute_value_id.name in tier1_option:
                            tier1_option.append(option1.product_attribute_value_id.name)
                            tier1_opt_list.append({
                                'hex_code': '' if not option1.product_attribute_value_id.hex else option1.product_attribute_value_id.hex,
                                'unit_value_id': option1.product_attribute_value_id.unit_value_id,
                                'value': option1.product_attribute_value_id.name
                            })
                        if option1.attribute_id.name and not option1.attribute_id.name in tier1_variation:
                            tier1_variation.append(option1.attribute_id.name)
                            tier_variation.append({
                                'id': option1.attribute_id.variant_id,
                                'unit_id': 0 if not option1.product_attribute_value_id.attribute_unit_id else option1.product_attribute_value_id.attribute_unit_id.id,
                                'options': tier1_opt_list
                            })
                        x = tier1_option.index(option1.product_attribute_value_id.name)
                        tier_model_index = [x]
                        if i == 0:
                            model_list.append({
                                'is_primary': True,
                                'status': product.product_tmpl_id.tts_stock_status,
                                'price': int(product.variant_price) if product.variant_price > 100 else 100,
                                'sku': '' if not product.default_code else product.default_code,
                                'stock': int(product.normal_stock) if product.normal_stock < 1 else 1,
                                'combination': tier_model_index,
                            })
                        else:
                            model_list.append({
                                'status': product.product_tmpl_id.tts_tts_stock_status,
                                'price': int(product.variant_price) if product.variant_price > 100 else 100,
                                'sku': '' if not product.default_code else product.default_code,
                                'stock': int(product.normal_stock) if product.normal_stock < 1 else 1,
                                'combination': tier_model_index,
                            })
                        i += 1
            attr_product = {
                'products': model_list,
                'selection': tier_variation,
            }
            return attr_product