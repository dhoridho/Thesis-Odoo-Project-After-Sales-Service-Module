# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request

import requests
import json
import string
import random
import datetime
from dateutil.relativedelta import relativedelta

class Equip3AssetFmsTracking(http.Controller):
    @http.route('/asset', auth='user', type='json', method=['GET'], website=True)
    def get_asset(self, **kw):

        # set to dummy data
        if kw.get('dummy', True):
            return self.get_asset_dummy(**kw)

        # vehicle_ids = request.env['maintenance.equipment'].search([('vehicle_checkbox', '=', True)])
        # return vehicle_ids.sudo().read(['id', 'display_name'])

        # url = "https://serv.vsms.co.id/api/vehicle/status"

        url_ = request.env['ir.config_parameter'].sudo().get_param('mceasy_api_url') or "https://serv.vsms.co.id"
        api_key = request.env['ir.config_parameter'].sudo().get_param('mceasy_api_key') or "59732ed1eb0b35736575995fd2afbf69"

        url = url_ + "/api/vehicle/status"
        payload={}
        headers = {
        'Authorization': 'Bearer ' + api_key
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        data = response.text
        json_d = json.loads(data)['data']

        # Speed data 
        speed_url = url_ + "/api/livedata/speed"
        speed_response = requests.request("GET", speed_url, headers=headers, data=payload)
        speed_data = speed_response.text
        speed_json_d = json.loads(speed_data)['data']

        # Postion data 
        position_url = url_ + "/api/livedata/position"
        position_response = requests.request("GET", position_url, headers=headers, data=payload)
        position_data = position_response.text
        position_json_d = json.loads(position_data)['data']

        obj = {
            'status': json_d,
            'speed': speed_json_d,
            'position': position_json_d
        }


        return obj

    def get_asset_dummy(self, **kw):

        ascii_upper = string.ascii_uppercase
        n_ascii = len(ascii_upper)

        center_point = {'lat': -6.200000, 'lon': 106.816666} # Jakarta
        lat_range = {'min': 0.1, 'max': 0.2}
        lon_range = {'min': 0.2, 'max': 0.2}

        if center_point['lat'] < 0:
            lat_range['min'] *= -1
            lat_range['max'] *= -1

        if center_point['lon'] < 0:
            lon_range['min'] *= -1
            lon_range['max'] *= -1

        statuses = ['Parking', 'Moving', 'Offline', 'Idle']
        n_statuses = len(statuses)

        now = datetime.datetime.now()
        last_3_years = now - relativedelta(years=3)
        
        def random_index(length_of_array):
            return random.randint(1, length_of_array) - 1

        def random_license_plate():
            first_letter = ascii_upper[random_index(n_ascii)]
            numbers = random.randint(1000, 9999)
            last_letter_1 = ascii_upper[random_index(n_ascii)]
            last_letter_2 = ascii_upper[random_index(n_ascii)]
            return '%s %s %s%s' % (first_letter, numbers, last_letter_1, last_letter_2)

        def random_lat_lon(range_from, range_to):
            return round(random.random() * (range_to - range_from) + range_from, 6)

        def random_status():
            return statuses[random_index(n_statuses)]

        def random_speed():
            return random.randint(40, 100)

        def random_date(start, end):
            delta = end - start
            int_delta = delta.total_seconds()
            random_second = random.randrange(int_delta)
            dt = start + datetime.timedelta(seconds=random_second)
            return dt.strftime('%d-%m-%Y %H:%M:%S')
        
        n_assets = 10 # number of assets

        status = []
        speed = []
        position = []
        for i in range(n_assets):
            license_plate = ascii_upper[random_index(n_ascii)]
            status += [{
                'license_plate': random_license_plate(),
                'latitude': random_lat_lon(center_point['lat'] - lat_range['min'], center_point['lat'] + lat_range['max']),
                'longitude': random_lat_lon(center_point['lon'] - lon_range['min'], center_point['lon'] + lon_range['max']),
                'status': random_status()
            }]
            speed += [{
                'speed': random_speed(),
                'last_data': random_date(last_3_years, now)
            }]

        data = {
            'status': status,
            'speed': speed,
            'position': position
        }
        return data
