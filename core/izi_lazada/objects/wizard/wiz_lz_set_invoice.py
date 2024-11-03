# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.izi_marketplace.objects.utils.tools import mp
from odoo.addons.izi_lazada.objects.utils.lazada.order import LazadaOrder


class WizardLazadaSetInvoice(models.TransientModel):
    _name = 'wiz.lz_set_invoice'
    _description = 'Lazada Set Invoice Order Wizard'

    order_ids = fields.Many2many(comodel_name="sale.order", relation="rel_lz_set_invoice_sale_order",
                                 column1="order_invoice_id", column2="order_id", string="Order(s)", required=True)
    mp_invoice_number = fields.Char(string='Invoice Number')

    def confirm(self):
        for order in self.order_ids:
            status = []
            if order.mp_account_id.mp_token_id.state == 'valid':
                params = {'access_token': order.mp_account_id.mp_token_id.name}
                lz_account = order.mp_account_id.lazada_get_account(host=order.mp_account_id.lz_country, **params)
                lz_order = LazadaOrder(lz_account)
                for line in order.order_line:
                    if line.product_type == 'product':
                        order_item_split = line.lz_order_item_id.split(',')
                        for item_number in order_item_split:
                            kwargs = {
                                'order_item_id': int(item_number),
                                'invoice_number': self.mp_invoice_number,
                            }
                            action_status = lz_order.action_set_invoice(**kwargs)

                order.mp_invoice_number = self.mp_invoice_number
                order.lazada_fetch_order()
