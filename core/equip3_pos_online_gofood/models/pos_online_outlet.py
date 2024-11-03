# -*- coding: utf-8 -*-

import requests
import json
import logging
import math
from datetime import datetime, timedelta
from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

def format24hour(hours):
    td = timedelta(hours=hours)
    dt = datetime.min + td
    return "{:%H:%M}".format(dt)

def normal_round(n, decimals=0):
    expoN = n * 10 ** decimals
    if abs(expoN) - abs(math.floor(expoN)) < 0.5:
        return math.floor(expoN) / 10 ** decimals
    return math.ceil(expoN) / 10 ** decimals

class PosOnlineOutlet(models.Model):
    _inherit = 'pos.online.outlet'

    gofood_merchant_id = fields.Char('GoFood Store ID', help='ID of the outlet on GoBiz side.', copy=False)
    gofood_partner_merchant_id = fields.Char('GoFood Partner Store ID', help='ID of the outlet on partner side.', copy=False) #external_outlet_id
    gofood_state = fields.Char('GoFood Outlet Status')
    gofood_update_menu_error_msg = fields.Text('GoFood: Latest update menu - Error Message')
    gofood_change_state_error_msg = fields.Text('GoFood: Change Status - Error Message')

    @api.model
    def create(self, vals):
        res = super(PosOnlineOutlet, self).create(vals)
        self.check_duplicate_gofood_merchant(vals.get('gofood_merchant_id'))
        self.check_duplicate_gofood_partner_merchant(vals.get('gofood_partner_merchant_id'))
        return res


    def write(self, vals):
        res = super(PosOnlineOutlet, self).write(vals)
        self.check_duplicate_gofood_merchant(vals.get('gofood_merchant_id'))
        self.check_duplicate_gofood_partner_merchant(vals.get('gofood_partner_merchant_id'))
        return res

    def check_duplicate_gofood_merchant(self, gofood_merchant_id):
        if gofood_merchant_id:
            domain = [('gofood_merchant_id','=', gofood_merchant_id)]
            outlets = self.env[self._name].search(domain, limit=3)
            if len(outlets) > 1:
                raise ValidationError('Duplicate Store ID! (%s: %s)' % (outlets[0].name, str(outlets[0].gofood_merchant_id)))
        return True

    def check_duplicate_gofood_partner_merchant(self, gofood_partner_merchant_id):
        if gofood_partner_merchant_id:
            domain = [('gofood_partner_merchant_id','=', gofood_partner_merchant_id)]
            outlets = self.env[self._name].search(domain, limit=3)
            if len(outlets) > 1:
                raise ValidationError('Duplicate Partner Store ID! (%s: %s)'  % (outlets[0].name, str(outlets[0].gofood_partner_merchant_id)))
        return True


    def gobiz_get_access_token(self, scope):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.gobiz_environment')

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = ''
        data += 'grant_type=client_credentials'
        data += '&scope=' + scope

        client_id = '#'
        client_secret = '#'
        endpoint_url = '#'

        if environment == 'sandbox':
            endpoint_url = f'https://integration-goauth.gojekapi.com/oauth2/token'
            client_id = ConfigParameter.get_param('base_setup.gobiz_sandbox_client_id')
            client_secret = ConfigParameter.get_param('base_setup.gobiz_sandbox_client_secret')
        if environment == 'production':
            endpoint_url = f'https://accounts.go-jek.com/oauth2/token'
            client_id = ConfigParameter.get_param('base_setup.gobiz_production_client_id')
            client_secret = ConfigParameter.get_param('base_setup.gobiz_production_client_secret')

        response = requests.post(endpoint_url, headers=headers, data=data, auth=(client_id, client_secret))
        if response.status_code == 200:
            return True, json.loads(response.text)['access_token'] 
        return False, response.text



    def action_update_menu(self):
        res = super(PosOnlineOutlet, self).action_update_menu()
        CconfigParameter = self.env['ir.config_parameter'].sudo()
        environment = CconfigParameter.get_param('base_setup.gobiz_environment')
       
        outlets = [ o for o in self if o.gofood_merchant_id]
        if outlets:
            _logger.info('Updated GoFood')
            is_access_token, access_token = self.gobiz_get_access_token(scope='gofood:catalog:write')
            if not is_access_token:
                raise ValidationError(access_token)

            headers = {
                'Authorization': 'Bearer ' + access_token,
            }
            for outlet in self:
                error_msg = '%s - ' % datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if outlet.gofood_merchant_id:
                    outlet_id = outlet.gofood_merchant_id
                    endpoint_url = '#'
                    if environment == 'sandbox':
                        endpoint_url = f'https://api.sandbox.gobiz.co.id/integrations/gofood/outlets/{outlet_id}/v1/catalog'
                    if environment == 'production':
                        endpoint_url = f'https://api.gobiz.co.id/integrations/gofood/outlets/{outlet_id}/v1/catalog'
                    
                    json_data = self.gobiz_get_menu_structure(outlet)
                    response = requests.put(endpoint_url, headers=headers, json=json_data)
                    if response.status_code in [200, 201]:
                        _logger.info('GoBiz Response: [%s]' % response.text)

                    if response.status_code not in [200, 201]:
                        error_msg += '[GoFood:%s]' % response.text.strip()
                        error_msg += '\n[headers:%s]' % str(response.headers)
                        _logger.error(error_msg)
                        raise ValidationError(error_msg)

                outlet.write({ 'gofood_update_menu_error_msg': error_msg })

        return res

    def gofood_auto_update_menu(self):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.gobiz_environment')
        pos_configs = self.env['pos.config'].sudo().search([
            ('online_outlet_id','!=',False),
            ('online_outlet_id.gofood_merchant_id','!=',False),
        ])
        _logger.info('Auto Updated GoFood')
        if pos_configs:
            is_access_token, access_token = self.gobiz_get_access_token(scope='gofood:catalog:write')
            if not is_access_token:
                _logger.error('Error gofood_auto_update_menu:\n' + str(access_token))

            if access_token:
                for pos in pos_configs:
                    if pos.online_outlet_id.gofood_merchant_id:
                        outlet = pos.online_outlet_id
                        headers = {
                            'Authorization': 'Bearer %s' % access_token,
                        }
                        error_msg = '%s - ' % datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        if outlet.gofood_merchant_id:
                            gofood_outlet_id = outlet.gofood_merchant_id
                            endpoint_url = '#'
                            if environment == 'sandbox':
                                endpoint_url = f'https://api.sandbox.gobiz.co.id/integrations/gofood/outlets/{gofood_outlet_id}/v1/catalog'
                            if environment == 'production':
                                endpoint_url = f'https://api.gobiz.co.id/integrations/gofood/outlets/{gofood_outlet_id}/v1/catalog'

                            json_data = self.gobiz_get_menu_structure(outlet)
                            response = requests.put(endpoint_url, headers=headers, json=json_data)
                            if response.status_code in [200, 201]:
                                _logger.info('GoBiz Response: [%s]' % response.text)

                            if response.status_code not in [200, 201]:
                                error_msg += '[%s]' % response.text.strip()
                                error_msg += '\n[headers:%s]' % str(response.headers)
                                _logger.error(error_msg)

                        outlet.write({ 'gofood_update_menu_error_msg': error_msg })
        return True

    def gobiz_check_menu_structure(self):
        raise ValidationError(json.dumps(self.gobiz_get_menu_structure(self)))

    def get_operational_hours(self, outlet):
        values = {}
        for operational in outlet.operational_hour_ids:
            values[operational.day] = [{
                'start': operational.start_time_24hour, 
                'end': operational.end_time_24hour,
            }]
        return values

    def gobiz_get_menu_structure(self, outlet):
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        operational_hours = self.get_operational_hours(outlet)
        outlet_id = outlet.id
        menus = []
        variant_categories = []

        line_category_ids = filter(lambda c: c['available_in_gofood'] == True, outlet.categ_ids)
        for category_sequence, line_category in enumerate(line_category_ids):
            category = line_category.pos_categ_id
            menu_items = []
            for product_sequence, line_product in enumerate(line_category.line_product_ids):
                product = line_product.product_tmpl_id
                if not product.available_in_pos:
                    continue
                if not product.product_variant_id:
                    continue

                variant_category_external_ids = []
                for line_option in product.oloutlet_product_option_ids:
                    variants = []
                    for product_option_sequence, product_option in enumerate(line_option.product_tmpl_ids):
                        if not product_option.available_in_pos:
                            continue
                        if not product_option.product_variant_id:
                            continue
                            
                        variants += [{
                            'external_id': f'V-' + str(product_option.id),
                            'name': product_option.name,
                            'price': int(normal_round(product_option.list_price)),
                            'in_stock': product_option.oloutlet_stock_available
                        }]
                    if variants:
                        variant_category_external_ids += [f'VC-{line_option.id}']
                        variant_categories += [{
                            'external_id':  f'VC-{line_option.id}',
                            'internal_name': line_option.name,
                            'name': line_option.name,
                            'rules': {
                                'selection': {
                                    'min_quantity': line_option.min_selection,
                                    'max_quantity': len(variants),
                                }
                            },
                            'variants': variants,
                        }]

                items_values = {
                    'external_id': f'ITEM-' + str(product.id),
                    'name': str(product.name)[:150],
                    'description': product.oloutlet_description or '',
                    'in_stock': product.oloutlet_stock_available,
                    'price': int(normal_round(product.list_price,0)),
                    'image': product.oloutlet_product_image_url,
                    'operational_hours': operational_hours,
                    'variant_category_external_ids': variant_category_external_ids
                }
                if not product.is_use_outlet_operational_hours and product.selling_time_id:
                    selling_time = product.selling_time_id.get_selling_time('gofood')
                    items_values['operational_hours'] = selling_time

                menu_items += [items_values]

            if menu_items:
                menus += [{
                    'name': category.name,
                    'menu_items': menu_items
                }]

        values = {
            'request_id': f'gobiz-menu-ol00{outlet.id}-t{timestamp}',
            'menus': menus,
            'variant_categories': variant_categories
        }
        return values

 
    def update_online_state(self):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.gobiz_environment')
        res = super(PosOnlineOutlet, self).update_online_state()

        outlet = self
        if outlet.gofood_merchant_id:
            is_access_token, access_token = self.gobiz_get_access_token(scope='gofood:outlet:write')
            if not is_access_token:
                raise ValidationError('[Gofood access_token] ' + str(access_token))

            if access_token:
                gofood_outlet_id = outlet.gofood_merchant_id
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer %s' % access_token,
                }
                json_data = {
                    'force_close': False,
                }
                if outlet.state == 'closed':
                    json_data['force_close'] = True

                if environment == 'sandbox':
                    endpoint_url = f'https://api.partner-sandbox.gobiz.co.id/integrations/gofood/outlets/{gofood_outlet_id}/v1/properties'
                if environment == 'production':
                    endpoint_url = f'https://api.gobiz.co.id/integrations/gofood/outlets/{gofood_outlet_id}/v1/properties'
                
                error_msg = '%s - ' % datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                response = requests.patch(endpoint_url, headers=headers, json=json_data)
                if response.status_code in [200, 204]:
                    outlet.write({ 
                        'gofood_state': outlet.state,
                    })
                    _logger.info('Gofood Update Outlet Success ~ Outlet Status: ' + str(outlet.state))
                if response.status_code not in [200, 204]:
                    error_msg += '[%s]' % response.text.strip()
                    error_msg += '\n[headers:%s]' % str(response.headers)

                outlet.write({ 'gofood_change_state_error_msg': error_msg })
        return res