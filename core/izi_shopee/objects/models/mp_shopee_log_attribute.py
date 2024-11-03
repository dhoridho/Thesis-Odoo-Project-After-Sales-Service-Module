# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
from datetime import datetime
from odoo import api, fields, models


class MpShopeeLogAttribute(models.Model):
    _name = 'mp.shopee.log.attribute'
    _inherit = 'mp.base'
    _description = 'Shopee Log Attribute'
    _rec_name = 'log_text'
    _order = 'id desc'

    status = fields.Selection([
        ('fail', 'Fail'),
        ('success', 'Success'), ],
        string='Status', default='fail')
    json_request = fields.Text(string='JSON Request')
    json_response = fields.Text(string='JSON Response')
    log_text = fields.Text(string='Log')
    log_create_datetime = fields.Datetime(string='Log Datetime')
    mp_account_id = fields.Many2one(comodel_name='mp.account', string='Marketplace Account', ondelete='cascade')

    @api.model
    def create_log_attribute(self, mp_account, raw_token, request_json, status):
        mp_shopee_log_attribute_obj = self.env['mp.shopee.log.attribute']

        values = {
            'log_text': self.format_raw_data(raw_token),
            'json_request': request_json,
            'mp_account_id': mp_account.id,
            'json_response': self.format_raw_data(raw_token),
            'status': status,
            'log_create_datetime': datetime.now()
        }
        mp_shopee_log_attribute_obj.create(values)
