# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MPLazadaLogistic(models.Model):
    _name = 'mp.lazada.logistic'
    _inherit = 'mp.base'
    _description = 'Marketplace Lazada Logistic'

    name = fields.Char(string='Logistic Name')
    cod = fields.Boolean(string='is COD ?')
    is_default = fields.Boolean(string='is Default ?')
    tracking_url = fields.Char(string='Logistic Tracking URL')
    tracking_code_example = fields.Char(string='Tracking Code Example'),
    tracking_code_validation_regex = fields.Char(string='Tracking Code Validation Regex')
    product_id = fields.Many2one(comodel_name="product.product", string="Delivery Product", required=False,
                                 default=lambda self: self._get_default_product_id())

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'lazada'
        mp_field_mapping = {
            'name': ('name', None),
            'mp_external_id': ('name', None),
            'tracking_url': ('tracking_url', None),
            'tracking_code_example': ('tracking_code_example', None),
            'tracking_code_validation_regex': ('tracking_code_validation_regex', None),
        }

        def _handle_boolean_logistic(env, data):
            if data == 0:
                return False
            elif data == 1:
                return True
            else:
                return None

        mp_field_mapping.update({
            'cod': ('cod', _handle_boolean_logistic),
            'is_default': ('is_default', _handle_boolean_logistic),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPLazadaLogistic, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _get_default_product_id(self):
        mp_delivery_product_tmpl = self.env.ref('izi_marketplace.product_tmpl_mp_delivery', raise_if_not_found=False)
        if mp_delivery_product_tmpl:
            return mp_delivery_product_tmpl.product_variant_id.id
        return False

    def get_delivery_product(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id
        return self.env['product.product']

    # @api.model
    # def lazada_get_sanitizers(self, mp_field_mapping):
    #     default_sanitizer = self.get_default_sanitizer(mp_field_mapping, root_path='data')
    #     return {
    #         'shipping_info': default_sanitizer
    #     }
