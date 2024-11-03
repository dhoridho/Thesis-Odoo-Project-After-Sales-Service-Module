# -*- coding: utf-8 -*-

from odoo import api, fields, models

class DictToObject:
    def __init__(self, d=None):
        if d is not None:
            for key, value in d.items():
                setattr(self, key, value)


class PosQrCodeReceiptTemplate(models.Model):
    _name = "pos.qrcode.receipt.template"
    _description = "QrCode fields display for scan qrcode of Receipt Fnb"

    name = fields.Char('QrCode Label', required=1)
    field_id = fields.Many2one(
        'ir.model.fields',
        domain=[
            ('model', '=', 'pos.order'),
            ('ttype', 'not in', ['binary', 'one2many', 'many2many'])
        ],
        string='Field Display',
        required=1,
        ondelete='cascade'
    )
    receipt_template_id = fields.Many2one('pos.receipt.template', 'Receipt Template', required=1)

    @api.onchange('field_id')
    def onchange_field_id(self):
        if self.field_id:
            self.name = self.field_id.field_description


class PosReceiptTemplate(models.Model):
    _inherit= "pos.receipt.template"

    is_receipt_bom_info = fields.Boolean('Show custom BOM')
    is_receipt_combo_info = fields.Boolean('Show Combo Option')
    is_display_barcode_ean13 = fields.Boolean('Display Barcode [Ean13]')
    is_qrcode_link = fields.Boolean('QrCode Link')
    is_table_guest_info = fields.Boolean("Table and Guest Information")
    qrcode_ids = fields.One2many(
        'pos.qrcode.receipt.template',
        'receipt_template_id',
        string='Fields Display for Qrcode'
    )

    def receipt_template_dict_data(self):
        company = self.env.company
        currency = company.currency_id
        if currency.position == 'after':
            price = 'xxxxx ' + currency.symbol
        else:
            price = currency.symbol + ' xxxxx'

        res = super(PosReceiptTemplate, self).receipt_template_dict_data()
        for l in res['orderlines']:
            l.pos_combo_options = [DictToObject({
                'full_product_name':'[ST-018] Combo bundle 1',
                'product_only_name':'Combo bundle 1',
                'quantity':1,
                'unit_name':'PCS',
                'price':price,
            }),
            DictToObject({
                'full_product_name':'[ST-019] Combo bundle 2',
                'product_only_name':'Combo bundle 2',
                'quantity':1,
                'unit_name':'PCS',
                'price':price,
            })
            ]

            l.bom_components = [DictToObject({
                'full_product_name':'[ST-118] BOM bundle 1',
                'product_only_name':'BOM bundle 1',
                'quantity':1,
                'is_extra':True,
                'unit_name':'PCS',
                'price':price,
            }),
            DictToObject({
                'full_product_name':'[ST-119] BOM bundle 2',
                'product_only_name':'BOM bundle 2',
                'quantity':1,
                'is_extra':False,
                'unit_name':'PCS',
                'price':price,
            })
            ]

        res['is_receipt_combo_info'] = self.is_receipt_combo_info
        res['is_receipt_bom_info'] = self.is_receipt_bom_info
        res['is_display_barcode_ean13'] = self.is_display_barcode_ean13
        res['is_qrcode_link'] = self.is_qrcode_link
        res['is_table_guest_info'] = self.is_table_guest_info
        res['is_receipt_bom_info'] = self.is_receipt_bom_info
        return res