from odoo import api, fields, models


class MPTiktokLogistic(models.Model):
    _name = 'mp.tiktok.logistic'
    _inherit = 'mp.base'
    _description = 'Marketplace Tiktok Logistic'
    _rec_name = 'delivery_option_name'

    delivery_option_id = fields.Char(string="Delivery Option ID", readonly=True)
    delivery_option_name = fields.Char(string="Delivery Option Name", readonly=True)
    item_max_weight = fields.Integer(string="Item Max Weight", readonly=True)
    item_min_weight = fields.Integer(string="Item Min Weight", readonly=True)
    item_dimension_length_limit = fields.Integer(string="Item Dimension Lenght Limit", readonly=True)
    item_dimension_width_limit = fields.Integer(string="Item Dimension Width Limit", readonly=True)
    item_dimension_height_limit = fields.Integer(string="Item Dimension Height Limit", readonly=True)
    provider_ids = fields.One2many(comodel_name="mp.tiktok.logistic.provider",
                                   inverse_name="logistic_id", readonly=True)
    product_id = fields.Many2one(comodel_name="product.product",
                                 string="Delivery Product", readonly=True)
    shop_id = fields.Many2one(comodel_name="mp.tiktok.shop", string="Shop", required=True, ondelete="restrict")


class MPTiktokLogisticProvider(models.Model):
    _name = 'mp.tiktok.logistic.provider'
    _inherit = 'mp.base'
    _description = 'Marketplace Tiktoc Logistic Provider'
    _rec_name = 'shipping_provider_name'

    shipping_provider_id = fields.Char(string="Shipping Provider ID", readonly=True)
    shipping_provider_name = fields.Char(string="Shipping Provider Name", readonly=True)
    logistic_id = fields.Many2one(comodel_name="mp.tiktok.logistic", readonly=True)
    product_id = fields.Many2one(comodel_name="product.product", string="Delivery Product", readonly=True)

    # @api.multi
    def get_delivery_product(self):
        self.ensure_one()
        if self.product_id:
            return self.product_id
        if self.logistic_id.product_id:
            return self.logistic_id.product_id
        return self.env['product.product']
