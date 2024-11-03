# -*- coding: utf-8 -*-

import json
import logging
import requests
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from pytz import timezone

_logger = logging.getLogger(__name__)

class PosOnlineOutlet(models.Model):
    _inherit = "pos.online.outlet"
    
    exponent = fields.Integer('Exponent', default=0, help='''Exponent refers to the number of times we need to multiply the major unit by a log base of 10, in order to get the minor unit.\nExample: A price of 100 means 1 dollar with an exponent of 2.\nFor VN, the exponent is 0 and for all other countries (SG/MY/ID/TH/PH/KH), the exponent is 2.''')
    grabfood_merchant_id = fields.Char('GrabFood Store ID', copy=False)
    grabfood_partner_merchant_id = fields.Char('GrabFood Partner Store ID', copy=False)
    grabfood_state = fields.Char('GrabFood Outlet Status')
    grabfood_update_menu_error_msg = fields.Text('GrabFood: Latest update menu - Error Message')
    grabfood_change_state_error_msg = fields.Text('GrabFood: Change Status - Error Message')
   
    @api.model
    def create(self, vals):
        res = super(PosOnlineOutlet, self).create(vals)
        self.check_duplicate_grabfood_merchant(vals.get('grabfood_merchant_id'))
        self.check_duplicate_grabfood_partner_merchant(vals.get('grabfood_partner_merchant_id'))
        return res


    def write(self, vals):
        res = super(PosOnlineOutlet, self).write(vals)
        self.check_duplicate_grabfood_merchant(vals.get('grabfood_merchant_id'))
        self.check_duplicate_grabfood_partner_merchant(vals.get('grabfood_partner_merchant_id'))
        return res

    def check_duplicate_grabfood_merchant(self, grabfood_merchant_id):
        if grabfood_merchant_id:
            domain = [('grabfood_merchant_id','=', grabfood_merchant_id)]
            outlets = self.env[self._name].search(domain, limit=3)
            if len(outlets) > 1:
                raise ValidationError('Duplicate Store ID! (%s: %s)' % (outlets[0].name, str(outlets[0].grabfood_merchant_id)))

    def check_duplicate_grabfood_partner_merchant(self, grabfood_partner_merchant_id):
        if grabfood_partner_merchant_id:
            domain = [('grabfood_partner_merchant_id','=', grabfood_partner_merchant_id)]
            outlets = self.env[self._name].search(domain, limit=3)
            if len(outlets) > 1:
                raise ValidationError('Duplicate Partner Store ID! (%s: %s)'  % (outlets[0].name, str(outlets[0].grabfood_partner_merchant_id)))
                
    def grabfood_get_access_token(self):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')

        headers = { }
        json_data = {
            'client_id': 'client_id',
            'client_secret': 'client_secret',
            'grant_type': 'client_credentials',
            'scope': 'food.partner_api',
        }

        endpoint_url = '#'
        if environment == 'sandbox':
            endpoint_url = f'https://api.stg-myteksi.com/grabid/v1/oauth2/token'
            json_data['client_id'] = ConfigParameter.get_param('base_setup.grabfood_sandbox_client_id')
            json_data['client_secret'] = ConfigParameter.get_param('base_setup.grabfood_sandbox_client_secret')

        if environment == 'production':
            endpoint_url = f'https://api.grab.com/grabid/v1/oauth2/token'
            json_data['client_id'] = ConfigParameter.get_param('base_setup.grabfood_production_client_id')
            json_data['client_secret'] = ConfigParameter.get_param('base_setup.grabfood_production_client_secret')

        response = requests.post(endpoint_url, headers=headers, json=json_data)
        if response.status_code == 200:
            return True, json.loads(response.text)['access_token']

        return False, response.text


    def action_update_menu(self):
        res = super(PosOnlineOutlet, self).action_update_menu()
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')
        
        is_access_token, access_token = self.grabfood_get_access_token()
        if not is_access_token:
            raise ValidationError(access_token)

        if access_token:
            for outlet in self:
                error_msg = '%s - ' % datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if outlet.grabfood_merchant_id:
                    headers = {
                        'Authorization': 'Bearer %s' % access_token,
                    }
                    json_data = {
                        'merchantID': outlet.grabfood_merchant_id,
                    }
                    if environment == 'sandbox':
                        endpoint_url = f'https://partner-api.stg-myteksi.com/grabfood-sandbox/partner/v1/merchant/menu/notification'
                    if environment == 'production':
                        endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/merchant/menu/notification'
                    response = requests.post(endpoint_url, headers=headers, json=json_data)
                    print()
                    if response.status_code not in [200, 204]:
                        error_msg += '[GrabFood:%s]' % response.text.strip()
                        error_msg += '\n[headers:%s]' % str(response.headers)
                        _logger.error(error_msg)
                        raise ValidationError(error_msg)

                outlet.write({ 'grabfood_update_menu_error_msg': error_msg })
        return res

    def grabfood_do_auto_update_menu(self):
        domain = [('online_outlet_id','!=', False), ('online_outlet_id.grabfood_merchant_id','!=', False)]
        pos_config = self.env['pos.config'].search(domain, limit=1)
        if pos_config:
            try:
                self.grabfood_auto_update_menu()
                _logger.info('Grabfood Update Success ~ grabfood_auto_update_menu')
            except Exception as e:
                _logger.error('Grabfood Update Error ~ grabfood_auto_update_menu: ' + str(e))
        return True

    def grabfood_auto_update_menu(self):
        res = super(PosOnlineOutlet, self).grabfood_auto_update_menu()

        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')
        pos_configs = self.env['pos.config'].sudo().search([('online_outlet_id','!=',False)])
        
        is_access_token, access_token = self.grabfood_get_access_token()
        if not is_access_token:
            raise ValidationError('Error grabfood_auto_update_menu:\n' + str(access_token))

        if access_token:
            for pos in pos_configs:
                if pos.online_outlet_id.grabfood_merchant_id:
                    outlet = pos.online_outlet_id
                    headers = {
                        'Authorization': 'Bearer %s' % access_token,
                    }
                    json_data = {
                        'merchantID': outlet.grabfood_merchant_id,
                    }

                    if environment == 'sandbox':
                        endpoint_url = f'https://partner-api.stg-myteksi.com/grabfood-sandbox/partner/v1/merchant/menu/notification'
                    if environment == 'production':
                        endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/merchant/menu/notification'

                    error_msg = '%s - ' % datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    response = requests.post(endpoint_url, headers=headers, json=json_data)
                    if response.status_code not in [200, 204]:
                        error_msg = response.text
                        error_msg += '[%s]' % response.text.strip()
                        error_msg += '\n[headers:%s]' % str(response.headers)
                        _logger.error(error_msg)
                        
                    outlet.write({ 'grabfood_update_menu_error_msg': error_msg })
        return True

    def update_state_in_grabfood(self, access_token, duration=''):
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')
        outlet = self
        headers = {
            'Authorization': 'Bearer %s' % access_token,
        }
        json_data = {
            'merchantID': outlet.grabfood_merchant_id,
            'isPause': False,
        }
        if outlet.state == 'closed':
            json_data['isPause'] = True
            json_data['duration'] = duration

        if environment == 'sandbox':
            endpoint_url = f'https://partner-api.stg-myteksi.com/grabfood-sandbox/partner/v1/merchant/pause'
        if environment == 'production':
            endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/merchant/pause'

        error_msg = '%s - ' % datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        response = requests.put(endpoint_url, headers=headers, json=json_data)
        if response.status_code in [200, 204]:
            outlet.write({ 
                'grabfood_state': outlet.state,
                'close_duration': json_data.get('duration'),
                'close_date': fields.Datetime.now(), 
            })
            if not json_data['isPause']:
                outlet.write({ 'close_date': False })

            _logger.info('Grabfood Update Outlet Success ~ Outlet Status: ' + str(outlet.state))
        if response.status_code not in [200, 204]:
            error_msg += '[%s]' % response.text.strip()
            error_msg += '\n[headers:%s]' % str(response.headers)

        outlet.write({ 'grabfood_change_state_error_msg': error_msg })

    def update_online_state(self):
        res = super(PosOnlineOutlet, self).update_online_state()
        outlet = self
        if outlet.grabfood_merchant_id:
            is_access_token, access_token = self.grabfood_get_access_token()
            if not is_access_token:
                raise ValidationError('[Grabfood access_token] ' + str(access_token))

            duration = '1h'
            if 'duration' in self._context:
                duration = self._context['duration']

            if access_token:
                outlet.update_state_in_grabfood(access_token, duration=duration)
        return res

    def check_outlet_status(self):
        res = super(PosOnlineOutlet, self).check_outlet_status()
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')

        pos_configs = self.env['pos.config'].sudo().search([('online_outlet_id','!=',False)])
        close_outlets = self.env['pos.online.outlet'].sudo().search([('state','=','closed')]) 
        if close_outlets or pos_configs:
            is_access_token, access_token = self.grabfood_get_access_token()
            if not is_access_token:
                _logger.info('Grabfood Failed Check Status ~ access_token: ', access_token)

            today = datetime.now()
            today_day = today.strftime("%A").lower()
            today_in_utc = datetime.strptime(today.utcnow().strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')

            for pos in pos_configs:
                if pos.online_outlet_id.grabfood_merchant_id:
                    outlet = pos.online_outlet_id
                    outlet_state = 'closed'
                    for op in outlet.operational_hour_ids:
                        if op.day == today_day:
                            start_date_in_utc = op.get_date_in_utc(hour=op.start_time_24hour)
                            end_date_in_utc = op.get_date_in_utc(hour=op.end_time_24hour)
                            if start_date_in_utc < today_in_utc < end_date_in_utc:
                                outlet_state = 'open'

                            print( outlet.name,' - Day: ', today_day.capitalize())
                            print('Today (UTC)      :', today_in_utc)
                            print('Start Date (UTC) :', start_date_in_utc)
                            print('End Date (UTC)   :', end_date_in_utc)
                            print('')

                    if pos.pos_session_state not in ['opened']:
                        outlet_state = 'closed'
                        
                    if outlet_state and outlet.close_duration != '1h':
                        values = { 'state': outlet_state, 'close_duration': '' }
                        if outlet_state == 'closed':
                            values['close_duration'] = '24h'
                        if outlet.state != outlet_state:
                            outlet.with_context(duration='24h').write(values)

            for outlet in close_outlets:
                if access_token and outlet.grabfood_merchant_id:
                    if outlet.close_duration == '1h':
                        now = datetime.now() - timedelta(hours=1)
                        if (now > outlet.close_date):
                            outlet.write({ 'state': 'open' })
        return res