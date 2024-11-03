# -*- coding: utf-8 -*-

import logging
import json
import requests
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class PosOnlineOutletCampaign(models.Model):
    _inherit = 'pos.online.outlet.campaign'

    campaign_type = fields.Selection(selection_add=[('grabfood', 'GrabFood')])
    eater_type = fields.Selection([('all','All'), ('new','New')], string='Eater Type', help='''The type of eater eligible for the campaign.\n\nAll - campaign will be applied to everyone. No limitation on campaign type.\nNew - campaign will be applied to consumers who have not ordered from this store in the last three months. Only applicable to order-level campaign.''')
    min_basket_amount = fields.Float('Minimum total amount')
    bundle_quantity = fields.Integer('Bundle Quantity', help='Specify the bundle quantity for bundle offer campaign.')
    total_count = fields.Integer('Max usage quota')
    total_count_per_user = fields.Integer('Max usage quota per customer')
    discount_type = fields.Selection([
        ('net','Net'),
        ('percentage','Percentage'),
        ('delivery','Delivery'),
        ('freeItem','FreeItem'),
        ('bundleSameNet','Bundle same net'),
        ('bundleSamePercentage','Bundle same percentage'),
        ('bundleSameFixPrice','Bundle same fix price'),
    ], string='Discount Type')
    discount_cap = fields.Float('Cap')
    discount_scope = fields.Selection([
        ('order','Order'),
        ('items','Items'),
        ('category','Category'),
    ], string='Scope Type')
    discount_product_ids = fields.Many2many(
        'product.template', 
        'pos_online_outlet_campaign_product_template_rel', 
        'campaign_id', 
        'product_id', 
        domain="[('is_online_outlet','=',True)]",
        string='Items')
    discount_category_ids = fields.Many2many(
        'pos.category', 
        'pos_online_outlet_campaign_pos_category_rel', 
        'campaign_id', 
        'pos_category_id', 
        domain="[('is_online_outlet','=',True)]",
        string='Category')
    discount_scope_objectids = fields.Text(compute='_compute_discount_scope_objectids')

    def _compute_discount_scope_objectids(self):
        for rec in self:
            objectids = []
            if rec.discount_scope == 'order':
                objectids = []

            if rec.discount_scope == 'items':
                for product in self.discount_product_ids:
                    objectids += ['ITEM-' + str(product.id)]

            if rec.discount_scope == 'category':
                for category in self.discount_category_ids:
                    objectids += ['CATEGORY-' + str(category.id)]

            rec.discount_scope_objectids = json.dumps(objectids)

    @api.model
    def create(self, values):
        res = super(PosOnlineOutletCampaign, self).create(values)
        for campaign in res:
            if campaign.campaign_type == 'grabfood':
                campaign.grabfood_create_campaign()

        return res

    def write(self, vals):
        res = super(PosOnlineOutletCampaign, self).write(vals)
        for campaign in self:
            if campaign.campaign_type == 'grabfood':
                campaign.grabfood_update_campaign()
        return res

    def unlink(self):
        for campaign in self:
            if campaign.campaign_type == 'grabfood':
                campaign.grabfood_delete_campaign()
        return super(PosOnlineOutletCampaign, self).unlink()    

    def grabfood_campaign_data(self):
        self.ensure_one()
        Outlet = self.env['pos.online.outlet']
        values = {}

        start_time = Outlet.format24hour(self.start_time)
        start_date = '%sT%s:00Z' % (self.start_date.strftime('%Y-%m-%d'), start_time)

        end_time = Outlet.format24hour(self.end_time)
        end_date = '%sT%s:00Z' % (self.end_date.strftime('%Y-%m-%d'), end_time)

        working_hour = {}
        if self.is_sunday:
            working_hour['sun'] = [{'startTime': start_time, 'endTime': end_time }]
        if self.is_monday:
            working_hour['mon'] = [{'startTime': start_time, 'endTime': end_time }]
        if self.is_tuesday:
            working_hour['tue'] = [{'startTime': start_time, 'endTime': end_time }]
        if self.is_wednesday:
            working_hour['wed'] = [{'startTime': start_time, 'endTime': end_time }]
        if self.is_thursday:
            working_hour['thu'] = [{'startTime': start_time, 'endTime': end_time }]
        if self.is_friday:
            working_hour['fri'] = [{'startTime': start_time, 'endTime': end_time }]
        if self.is_saturday:
            working_hour['sat'] = [{'startTime': start_time, 'endTime': end_time }]

        values = {
            'merchantID': self.outlet_id.grabfood_merchant_id,
            'name': self.name,
            'quotas': {
                'totalCount': self.total_count,
                'totalCountPerUser': self.total_count_per_user,
            },
            'conditions': {
                'startTime': start_date,
                'endTime': end_date,
                'eaterType': self.eater_type,
                'minBasketAmount': self.min_basket_amount,
                'workingHour': working_hour,
                'bundleQuantity': self.bundle_quantity,
            },
            'discount': {
                'type': self.discount_type,
                'cap': self.discount_cap,
                'value': self.discount_value,
                'scope': {
                    'type': self.discount_scope,
                    'objectIDs': json.loads(self.discount_scope_objectids),
                }
            }
        }
        return values

    def grabfood_create_campaign(self):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')

        is_access_token, access_token = self.env['pos.online.outlet'].grabfood_get_access_token()
        if not is_access_token:
            raise ValidationError(access_token)

        if access_token:
            headers = { 'Authorization': 'Bearer %s' % access_token, }
            json_data = self.grabfood_campaign_data()

            #Sandbox not exist
            # if environment == 'sandbox':
            #     endpoint_url = f'https://partner-api.stg-myteksi.com/grabfood-sandbox/partner/v1/campaigns'
            # if environment == 'production':
            #     endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/campaigns'
            endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/campaigns'

            response = requests.post(endpoint_url, headers=headers, json=json_data)
            if response.status_code == 200:
                resp_data = json.loads(response.text)
                self.write({ 'external_id': resp_data['id'] })
                _logger.info('Successfully create GrabFood campaign ID:' + str(self.id))
                _logger.info('[GrabFood] [' + response.text + ']')
            else:
                error_message = ''
                # error_message += json.loads(response.text)['message']
                # error_message += '\n\n' + str(response.headers)
                _logger.error('Failed create GrabFood campaign ID:' + str(self.id))
                _logger.error('[GrabFood] [' + error_message + ']')
                # raise ValidationError(error_message)
        return True

    def grabfood_update_campaign(self):
        self.ensure_one()
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')

        is_access_token, access_token = self.env['pos.online.outlet'].grabfood_get_access_token()
        if not is_access_token:
            raise ValidationError(access_token)

        if access_token:
            campaign_id = self.external_id
            headers = { 'Authorization': 'Bearer %s' % access_token, }
            json_data = self.grabfood_campaign_data()

            #Sandbox not exist
            # if environment == 'sandbox':
            #     endpoint_url = f'https://partner-api.stg-myteksi.com/grabfood-sandbox/partner/v1/campaigns/{campaign_id}'
            # if environment == 'production':
            #     endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/campaigns/{campaign_id}'

            endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/campaigns/{campaign_id}'

            response = requests.put(endpoint_url, headers=headers, json=json_data)
            if response.status_code == 200:
                _logger.info('Successfully update GrabFood campaign ID:' + str(self.id))
                _logger.info('[GrabFood] [' + json.loads(response.text) + ']')
            elif response.status_code == 204:
                _logger.info('Successfully update GrabFood campaign ID:' + str(self.id))
                _logger.info('[GrabFood] []')
            else:
                error_message = ''
                # error_message += json.loads(response.text)['message']
                # error_message += '\n\n' + str(response.headers)
                _logger.error('Failed update GrabFood campaign ID:' + str(self.id))
                _logger.error('[GrabFood] [' + error_message + ']')
                # raise ValidationError(error_message)
        return True


    def grabfood_delete_campaign(self):
        self.ensure_one()
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')

        is_access_token, access_token = self.env['pos.online.outlet'].grabfood_get_access_token()
        if not is_access_token:
            raise ValidationError(access_token)

        if access_token:
            campaign_id = self.external_id
            headers = { 'Authorization': 'Bearer %s' % access_token, }

            #Sandbox not exist
            # if environment == 'sandbox':
            #     endpoint_url = f'https://partner-api.stg-myteksi.com/grabfood-sandbox/partner/v1/campaigns/{campaign_id}'
            # if environment == 'production':
            #     endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/campaigns/{campaign_id}'

            endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/campaigns/{campaign_id}'
            response = requests.delete(endpoint_url, headers=headers)
            if response.status_code == 200:
                _logger.info('Successfully delete GrabFood campaign ID:' + str(self.id))
                _logger.info('[GrabFood] [' + json.loads(response.text) + ']')
            elif response.status_code == 204:
                _logger.info('Successfully delete GrabFood campaign ID:' + str(self.id))
                _logger.info('[GrabFood] []')
            else:
                error_message = ''
                # error_message += json.loads(response.text)['message']
                # error_message += '\n\n' + str(response.headers)
                _logger.error('Failed delete GrabFood campaign ID:' + str(self.id))
                _logger.error('[GrabFood] [' + error_message + ']')
                # raise ValidationError(error_message)
        return True
