# -*- coding: utf-8 -*-
import requests
import json
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class PosOnlineOutletGobizSubscription(models.Model):
    _name = 'pos.online.outlet.gobiz.subscription'
    _rec_name = 'url'

    url = fields.Char('URL')
    updated_at = fields.Char('Updated at')
    external_id = fields.Char('External id')
    # Events List
    event = fields.Selection([
        ('gofood.order.created','GoFood Order Created Event'),
        ('gofood.order.awaiting_merchant_acceptance','GoFood Awaiting Merchant Acceptance Event'),
        ('gofood.order.merchant_accepted','GoFood Merchant Accepted Event'),
        ('gofood.order.driver_otw_pickup','GoFood Driver Pickup Event (OTW Pickup)'),
        ('gofood.order.driver_arrived','GoFood Driver Arrived Event'), 
        ('gofood.order.completed','GoFood Order Completed Event'),
        ('gofood.order.cancelled','GoFood Order Cancelled Event'),
    ], string='Event')
    created_at = fields.Char('Created at')
    aggregator_id = fields.Char('Aggregator id')
    is_active = fields.Boolean('Is Active?')
    is_new = fields.Boolean('Is New?')


    @api.model
    def create(self, vals):
        context = self._context
        if context.get('_add_subscription'):
            is_added, subscription_values = self.add_subscription(vals)
            if not is_added:
                raise ValidationError(subscription_values)

            if is_added and subscription_values:
                vals = {**vals, **subscription_values}

        result = super(PosOnlineOutletGobizSubscription, self).create(vals)
        return result

    def add_subscription(self, vals):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.gobiz_environment')
        OnlineOutlet = self.env['pos.online.outlet']
        Subscription = self.env['pos.online.outlet.gobiz.subscription']
        
        is_access_token, access_token  = OnlineOutlet.gobiz_get_access_token(scope='gofood:order:read')
        if not is_access_token:
            raise ValidationError(access_token)

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + access_token,
        }

        json_data = {       
            "event": vals['event'],
            "url": vals['url'],
            "active": True
        }

        endpoint_url = ''
        if environment == 'sandbox':
            endpoint_url = f'https://api.sandbox.gobiz.co.id/integrations/partner/v1/notification-subscriptions'
        if environment == 'production':
            endpoint_url = f'https://api.gobiz.co.id/integrations/partner/v1/notification-subscriptions'
        
        response = requests.post(endpoint_url, headers=headers, json=json_data)

        has_error = []
        if response.status_code in [200, 201]:
            resp_data = json.loads(response.text)
            if resp_data['success']:
                subs = resp_data['data']['subscription']
                values = {
                    'external_id': subs.get('id',''),
                    'event': subs.get('event',''),
                    'url': subs.get('url',''),
                    'is_active': subs.get('active', False),
                    'updated_at': subs.get('updated_at',''),
                    'created_at': subs.get('created_at',''),
                    'is_new': True,
                }
                return True, values # Success

            return False, response.text
        return False, response.text

    def action_sync(self):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.gobiz_environment')
        OnlineOutlet = self.env['pos.online.outlet']
        Subscription = self.env['pos.online.outlet.gobiz.subscription'].with_context(_add_subscription=False)

        is_access_token, access_token  = OnlineOutlet.gobiz_get_access_token(scope='gofood:order:read')
        if not is_access_token:
            raise ValidationError(access_token)

        headers = {
            'Authorization': 'Bearer ' + access_token,
        }

        endpoint_url = ''
        if environment == 'sandbox':
            endpoint_url = f'https://api.sandbox.gobiz.co.id/integrations/partner/v1/notification-subscriptions'
        if environment == 'production':
            endpoint_url = f'https://api.gobiz.co.id/integrations/partner/v1/notification-subscriptions'
        response = requests.get(endpoint_url, headers=headers) 

        if response.status_code == 200:
            subscriptions = json.loads(response.text)['data']['subscriptions']
            for subs in subscriptions:
                external_id = subs.get('id','')
                url = subs.get('url','')

                # exclude clubfood url
                if 'dev-instance.clubfood.co' in url:
                    continue

                subscription = Subscription.search([('external_id','=', external_id)], limit=1)
                if not subscription:
                    values = {
                        'url': url,
                        'updated_at': subs.get('updated_at',''),
                        'external_id': external_id,
                        'event': subs.get('event',''),
                        'created_at': subs.get('created_at',''),
                        'aggregator_id': subs.get('aggregator_id',''),
                        'is_active': subs.get('active', False),
                    }
                    Subscription.create(values)

                if subscription.is_new:
                    subscription.write({ 'aggregator_id': subs.get('aggregator_id','') })

        else:
            raise ValidationError(response.content)


        return True

    def action_delete_subscription(self):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.gobiz_environment')
        OnlineOutlet = self.env['pos.online.outlet']
        Subscription = self.env['pos.online.outlet.gobiz.subscription'].with_context(_add_subscription=False)
        
        is_access_token, access_token  = OnlineOutlet.gobiz_get_access_token(scope='gofood:order:read')
        if not is_access_token:
            raise ValidationError(access_token)

        headers = {
            'Authorization': 'Bearer ' + access_token,
        }

        notification_id = self.external_id
        endpoint_url = ''
        if environment == 'sandbox':
            endpoint_url = f' https://api.sandbox.gobiz.co.id/integrations/partner/v1/notification-subscriptions/{notification_id}'
        if environment == 'production':
            endpoint_url = f'https://api.gobiz.co.id/integrations/partner/v1/notification-subscriptions/{notification_id}'

        response = requests.delete(endpoint_url, headers=headers)
        has_error = []
        if response.status_code in [200, 201]:
            self.unlink()
            action = self.env.ref('equip3_pos_online_gofood.pos_online_outlet_gobiz_subscription_action').sudo().read()[0]
            return action

        raise ValidationError(response.text)