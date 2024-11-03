from odoo import api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class MPTiktokShop(models.Model):
    _name = 'mp.tiktok.shop'
    _inherit = 'mp.base'
    _description = 'Marketplace Tiktok Shop'
    _rec_name = 'shop_name'

    SHOP_TYPE = [
        ('1', 'CROSS BORDER'),
        ('2', 'LOCAL TO LOCAL'),
    ]

    shop_id = fields.Char(string="Tiktok Shop ID", readonly=True)
    shop_name = fields.Char(string="Tiktok Shop Name", readonly=True)
    shop_cipher = fields.Char(string="Tiktok Shop Cipher", readonly=True)
    region = fields.Char(string="Tiktok Region", readonly=True)
    type = fields.Selection(string="Tiktok Type", selection=SHOP_TYPE, readonly=True)
    shop_code = fields.Char(string="Tiktok Shop Code", readonly=True)
    shop_logistic_ids = fields.One2many(comodel_name="mp.tiktok.logistic", inverse_name="shop_id",
                                        string="Active Logistics", required=False)

    @classmethod
    def _add_rec_mp_field_mapping(cls, mp_field_mappings=None):
        if not mp_field_mappings:
            mp_field_mappings = []

        marketplace = 'tiktok'
        mp_field_mapping = {
            'mp_external_id': ('id', lambda env, r: str(r)),
            'shop_id': ('id', lambda env, r: str(r)),
            'shop_code': ('code', None),
            'shop_name': ('name', None),
            'shop_cipher': ('cipher', None),
            'region': ('region', None),
        }

        def _set_seller_type(env, data):
            if data:
                if data == 'CROSS_BORDER':
                    return '1'
                elif data == 'LOCAL':
                    return '2'
                else:
                    return None
            else:
                return None

        mp_field_mapping.update({
            'type': ('seller_type', _set_seller_type),
        })

        mp_field_mappings.append((marketplace, mp_field_mapping))
        super(MPTiktokShop, cls)._add_rec_mp_field_mapping(mp_field_mappings)

    @api.model
    def _finish_create_records(self, records):
        mp_account_obj = self.env['mp.account']

        context = self._context
        if not context.get('mp_account_id'):
            raise ValidationError("Please define mp_account_id in context!")

        mp_account = mp_account_obj.browse(context.get('mp_account_id'))

        records = super(MPTiktokShop, self)._finish_create_records(records)
        mp_account.write({'tts_shop_id': records[0].id})
        return records


# class MPTiktokShopLogistic(models.Model):
#     _name = 'mp.tiktok.shop.logistic'
#     _inherit = 'mp.base'
#     _description = 'Marketplace Tiktok Shop Logistic'
#     _sql_constraints = [
#         ('unique_shop_logistic', 'UNIQUE(shop_id,logistic_id)', 'Please select one logistic per shop!')
#     ]

#     shop_id = fields.Many2one(comodel_name="mp.tiktok.shop", string="Shop", required=True, ondelete="restrict")
#     logistic_id = fields.Many2one(comodel_name="mp.tiktok.shop", string="Logistic", required=True,
#                                   ondelete="restrict")
#     service_ids = fields.Many2many(comodel_name="mp.tiktok.logistic.service",
#                                    relation="rel_tp_shop_logistic_service", column1="shop_logistic_id",
#                                    column2="service_id", string="Active Service(s)")
#     name = fields.Char(related="logistic_id.shipping_provider_name")
