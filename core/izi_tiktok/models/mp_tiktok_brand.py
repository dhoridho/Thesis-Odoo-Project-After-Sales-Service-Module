from odoo import api, fields, models


class MPTiktokBrand(models.Model):
    _name = 'mp.tiktok.brand'
    _inherit = 'mp.base'
    _description = 'Marketplace Tiktok Brand'

    brand_id = fields.Char(string="Brand ID", readonly=True)
    brand_name = fields.Char(string="Brand Name", readonly=True)
