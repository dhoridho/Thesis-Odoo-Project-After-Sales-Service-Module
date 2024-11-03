# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

from odoo.addons.izi_lazada.objects.utils.lazada.logistic import LazadaLogistic


class MPLazadaSeller(models.Model):
    _name = 'mp.lazada.seller'
    _inherit = 'mp.base'
    _description = 'Marketplace Lazada Seller'

    name = fields.Char(string='Seller Name', readonly=True)
    active = fields.Boolean(string='Active')
    seller_company = fields.Char(string='Seller Company Name', readonly=True)
    seller_logo = fields.Char(string='Seller Logo', readonly=True)
    seller_location = fields.Char(string='Seller Location', readonly=True)
    seller_verified = fields.Boolean(string='Seller is Verified', readonly=True)
    seller_id = fields.Char(string='Seller ID', readonly=True)
    seller_email = fields.Char(string='Seller Email', readonly=True)
    short_code = fields.Char(string='Short Code', readonly=True)
    seller_cb = fields.Boolean(string='Seller CB ', readonly=True)
    seller_logistic_ids = fields.One2many(comodel_name="mp.lazada.seller.logistic", inverse_name="shop_id",
                                          string="Logistics",
                                          required=False)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'lazada'
        mp_field_mapping = {
            'name': ('name', None),
            'mp_external_id': ('seller_id', lambda env, r: str(r)),
            'seller_id': ('seller_id', lambda env, r: str(r)),
            'seller_company': ('name_company', None),
            'seller_logo': ('logo_url', None),
            'seller_location': ('location', None),
            'seller_email': ('email', None),
            'short_code': ('short_code', None),
            'seller_cb': ('cb', None),
            'seller_verified': ('verified', None),
        }

        def _handle_seller_active(env, data):
            if data:
                if data == 'ACTIVE':
                    return True
                else:
                    return False
            else:
                return None

        mp_field_mapping.update({
            'active': ('status', _handle_seller_active)
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPLazadaSeller, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _finish_create_records(self, records):
        mp_account_obj = self.env['mp.account']

        context = self._context
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        mp_account = mp_account_obj.browse(context.get('mp_account_id'))

        records = super(MPLazadaSeller, self)._finish_create_records(records)
        mp_account.write({'lz_seller_id': records[0].id})
        return records

    def get_seller_logistics(self):
        mp_lazada_logistic_obj = self.env['mp.lazada.logistic']
        mp_lazada_seller_logistic_obj = self.env['mp.lazada.seller.logistic']

        for shop in self:
            mp_account = shop.mp_account_id
            if mp_account.mp_token_id.state == 'valid':
                kwargs = {'access_token': mp_account.mp_token_id.name}
                lz_account = mp_account.lazada_get_account(host=mp_account.lz_country, **kwargs)
                lz_logistic = LazadaLogistic(lz_account)
                lz_response = lz_logistic.get_shipping_info()
                logistic_list_raws = lz_response['shipment_providers']
                for active_logistic_raw in logistic_list_raws:
                    lz_logistic = mp_lazada_logistic_obj.search_mp_records(shop.marketplace,
                                                                           active_logistic_raw['name'])
                    existing_shop_logistic = mp_lazada_seller_logistic_obj.search([
                        ('shop_id', '=', shop.id), ('logistic_id', '=', lz_logistic.id)
                    ])
                    shop_logistic_values = {
                        'shop_id': shop.id,
                        'logistic_id': lz_logistic.id,
                        'mp_account_id': mp_account.id,
                        'cod_enabled': False if active_logistic_raw['cod'] == 0 else True,
                    }
                    if not existing_shop_logistic.exists():
                        shop_logistic = mp_lazada_seller_logistic_obj.create(shop_logistic_values)
                        shop.write({'seller_logistic_ids': [(4, shop_logistic.id)]})
                    else:
                        existing_shop_logistic.write(shop_logistic_values)


class MPLazadaSellerLogistic(models.Model):
    _name = 'mp.lazada.seller.logistic'
    _inherit = 'mp.base'
    _description = 'Marketplace Lazada Seller Logistic'
    _sql_constraints = [
        ('unique_shop_logistic', 'UNIQUE(shop_id,logistic_id)', 'Please select one logistic per shop!')
    ]

    shop_id = fields.Many2one(comodel_name="mp.lazada.seller", string="Seller", required=True, ondelete="restrict")
    logistic_id = fields.Many2one(comodel_name="mp.lazada.logistic", string="Logistic", required=True,
                                  ondelete="restrict")
    name = fields.Char(related="logistic_id.name")
    cod_enabled = fields.Boolean(string='COD Enabled', readonly=True)
