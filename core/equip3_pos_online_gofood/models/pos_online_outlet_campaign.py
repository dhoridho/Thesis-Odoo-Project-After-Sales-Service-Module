# -*- coding: utf-8 -*-

import uuid
import logging
import json
import requests
from datetime import datetime
from odoo import api, fields, models, _
from odoo.exceptions import  ValidationError

_logger = logging.getLogger(__name__)

class PosOnlineOutletCampaign(models.Model):
    _inherit = 'pos.online.outlet.campaign'

    campaign_type = fields.Selection(selection_add=[('gofood', 'GoFood')])
    promo_type = fields.Selection([('sku_promo','sku_promo')], string='Promo Type', default='sku_promo')
    gofood_discount_type = fields.Selection([
        ('selling_price','Selling Price'),
        ('percentage','Percentage'),
    ], string='Discount Type')
    gofood_product_id = fields.Many2one('product.template', string='Item', 
        domain="[('is_online_outlet','=',True)]")
    gofood_product_ids = fields.Many2many(
        'product.template', 
        'pos_online_outlet_campaign_product_template_gofood_rel', 
        'campaign_id', 
        'product_id', 
        domain="[('is_online_outlet','=',True)]",
        string='Items')
    gofood_category_ids = fields.Many2many(
        'pos.category', 
        'pos_online_outlet_campaign_pos_category_gofood_rel', 
        'campaign_id', 
        'pos_category_id', 
        domain="[('is_online_outlet','=',True)]",
        string='Category')
    gofood_x_idempotency_key = fields.Char('X-Idempotency-Key', help='It is used to identify whether the request is a new request or a retry request. Maximum Limit: 32 characters')

    @api.model
    def create(self, values):
        res = super(PosOnlineOutletCampaign, self).create(values)
        for campaign in res:
            if campaign.campaign_type == 'gofood':
                campaign.gofood_create_campaign()

        return res

    def write(self, vals):
        res = super(PosOnlineOutletCampaign, self).write(vals)
        for campaign in self:
            if campaign.campaign_type == 'gofood':
                campaign.gofood_update_campaign()
        return res

    def unlink(self):
        for campaign in self:
            if campaign.campaign_type == 'gofood':
                campaign.gofood_delete_campaign()
        return super(PosOnlineOutletCampaign, self).unlink()

    def gofood_campaign_data(self):
        Outlet = self.env['pos.online.outlet']
        values = {}

        outlet_id = self.outlet_id.id

        start_time = '%s:00' % Outlet.format24hour(self.start_time)
        start_date = '%s' % (self.start_date.strftime('%Y-%m-%d'))

        end_time = '%s:00' % Outlet.format24hour(self.end_time)
        end_date = '%s' % (self.end_date.strftime('%Y-%m-%d'))

        applicable_days = []
        if self.is_sunday:
            applicable_days += ['sunday']
        if self.is_monday:
            applicable_days += ['monday']
        if self.is_tuesday:
            applicable_days += ['tuesday']
        if self.is_wednesday:
            applicable_days += ['wednesday']
        if self.is_thursday:
            applicable_days += ['thursday']
        if self.is_friday:
            applicable_days += ['friday']
        if self.is_saturday:
            applicable_days += ['saturday']

        values = {
            'promo_type': self.promo_type,
            'promo_detail': {
                'start_date': start_date,
                'end_date': end_date,
                'start_time': start_time,
                'end_time': end_time,
                'selling_price': self.discount_value,
                'external_menu_id': f'ITEM-' + str(self.gofood_product_id.id),
                'applicable_days': applicable_days
            },
        }
        # items = []
        # for product in self.gofood_product_ids:
        #     items += [f'ITEM-' + str(product.id)]
        return values

    def gofood_create_campaign(self):
        self.ensure_one()
        OnlineOutlet = self.env['pos.online.outlet']
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.gobiz_environment')

        is_access_token, access_token = OnlineOutlet.gobiz_get_access_token(scope='promo:food_promo:write')
        if not is_access_token:
            raise ValidationError(access_token)

        outlet_id = self.outlet_id.id
        campaign = self
        
        if access_token:
            x_idempotency_key = uuid.uuid4().hex
            headers = {
                'Content-Type': 'application/json',
                'X-Request-ID': f'hm-campaign-request-id-{str(campaign.id)}' + datetime.now().strftime('%Y-%m-%d-%H:%M:'),
                'X-Idempotency-Key': x_idempotency_key,
                'Authorization': 'Bearer %s' % access_token,
            }
            json_data = self.gofood_campaign_data()

            base_url = '#'
            if environment == 'sandbox':
                base_url = f'https://api.sandbox.gobiz.co.id'
            if environment == 'production':
                base_url = f'https://api.gobiz.co.id'

            endpoint_url = f'{base_url}/integrations/promo/outlets/{outlet_id}/v1/food-promos'

            response = requests.post(endpoint_url, headers=headers, json=json_data)
            if response.status_code in [200, 201]:
                resp_data = json.loads(response.text)
                self.write({ 'external_id': resp_data['data']['success']['id'] })
                _logger.info('Successfully create gofood campaign ID:' + str(self.id))
                _logger.info('[gofood] [' + response.text + ']')
            else:
                error_message = ''
                error_message += response.text
                error_message += '\n\n' + str(response.headers)
                _logger.error('Failed create gofood campaign ID:' + str(self.id))
                _logger.error('[gofood] [' + error_message + ']')
                raise ValidationError(error_message)

            self.write({ 'gofood_x_idempotency_key' : x_idempotency_key})

        return False

    def gofood_update_campaign(self):
        return False

    def gofood_delete_campaign(self):
        OnlineOutlet = self.env['pos.online.outlet']
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.gobiz_environment')

        is_access_token, access_token = OnlineOutlet.gobiz_get_access_token(scope='promo:food_promo:write')
        if not is_access_token:
            raise ValidationError(access_token)

        outlet_id = self.outlet_id.id
        promotion_id = self.external_id
        campaign = self
        
        if access_token:
            x_idempotency_key = uuid.uuid4().hex
            headers = {
                'X-Request-ID': f'hm-campaign-request-id-{str(campaign.id)}' + datetime.now().strftime('%Y-%m-%d-%H:%M:'),
                'Authorization': 'Bearer %s' % access_token,
            }
            
            base_url = '#'
            if environment == 'sandbox':
                base_url = f'https://api.sandbox.gobiz.co.id'
            if environment == 'production':
                base_url = f'https://api.gobiz.co.id'

            endpoint_url = f'{base_url}/integrations/promo/outlets/{outlet_id}/v1/food-promos{promotion_id}'

            response = requests.delete(endpoint_url, headers=headers)
            if response.status_code == 200:
                _logger.info('Successfully delete gofood campaign ID:' + str(self.id))
                _logger.info('[gofood] [' + response.text + ']')
            else:
                error_message = ''
                error_message += response.text
                error_message += '\n\n' + str(response.headers)
                _logger.error('Failed delete gofood campaign ID:' + str(self.id))
                _logger.error('[gofood] [' + error_message + ']')
                raise ValidationError(error_message)

        return False