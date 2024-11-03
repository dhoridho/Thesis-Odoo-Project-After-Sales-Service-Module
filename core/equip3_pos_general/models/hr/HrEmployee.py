# -*- coding: utf-8 -*-

import math, random
from twilio.rest import Client
from datetime import datetime
from odoo import api, models, fields, registry

class PosBranch(models.Model):
    _inherit = "hr.employee"

    allow_discount = fields.Boolean('Allow Change Discount', default=1)
    allow_qty = fields.Boolean('Allow Change Quantity', default=1)
    allow_price = fields.Boolean('Allow Change Price', default=1)
    allow_remove_line = fields.Boolean('Allow Remove Line', default=1)
    allow_minus = fields.Boolean('Allow Minus (+/-)', default=1)
    allow_payment = fields.Boolean('Allow Payment', default=1)
    allow_customer = fields.Boolean('Allow set Customer', default=1)
    allow_add_order = fields.Boolean('Allow Add Order', default=1)
    allow_remove_order = fields.Boolean('Allow Remove Order', default=1)
    allow_add_product = fields.Boolean('Allow Add Product', default=1)
    allow_payment_zero = fields.Boolean(
        'Allow Payment Zero',
        default=1,
        help='If active, cashier can made order total amount smaller than or equal 0')
    allow_offline_mode = fields.Boolean(
        'Allow Offline Mode',
        default=1,
        help='Required Internet of Cashiers Counter Devlice used POS Session online \n'
             'If have problem internet of Cashier Counter, POS not allow submit Orders to Backend \n'
             'Example Case Problem: \n'
             '1) Intenet Offline , Cashiers submit orders to Odoo server and not success \n'
             '2) And then them clear cache browse , and orders save on Cache of Browse removed \n'
             '- It mean all orders will lost \n'
             'So this function active, when any Orders submit to backend, POS auto check Odoo server online or not. If online allow Validate Order'
    )
    pos_use_otp = fields.Boolean('Use OTP')
    pos_otp_phone = fields.Char('Phone')
    last_sent_otp = fields.Char('Last Sent OTP')

    @api.model
    def pos_send_otp(self, data, api_access):
        sid = api_access.get('sid')
        token = api_access.get('token')
        msg = api_access.get('msg_format')
        
        otp_digits = "0123456789"
        OTP = ""
        for i in range(4) :
            OTP += otp_digits[math.floor(random.random() * 10)]

        if data:
            if sid and token:
                client = Client(sid, token)
                body = msg.replace('[otp]',OTP)
                from_ = data.get('pos_otp_phone')
                to = data.get('work_phone')
                m_sid = 'MG8e2e7e83d9dd70566f59e05155f69a04'

                if client and body and to and m_sid and data.get('id'):
                    otp_message = client.messages.create(body=body,to=to,messaging_service_sid=m_sid)
                    print(otp_message.sid)
                    if otp_message.sid:
                        self.browse(data.get('id')).last_sent_otp = OTP
                        
        return 'OTP Message Sent...'

