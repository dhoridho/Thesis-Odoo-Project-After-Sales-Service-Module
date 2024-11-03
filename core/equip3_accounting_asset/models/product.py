from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)

class Product(models.Model):
    _inherit = 'product.template'

    # type = fields.Selection(selection_add=[('asset', 'Asset')], ondelete='cascade')
    type = fields.Selection(selection_add=[('asset', 'Asset'),], ondelete={'asset': 'cascade'})
    asset_category_id = fields.Many2one('account.asset.category', string='Asset Category')
    asset_entry_perqty = fields.Boolean('Asset Entry Perquantity')
    
    def _is_invisible_standard_price(self):
        return super(Product, self)._is_invisible_standard_price() or self.type == 'asset'

    @api.onchange('type')
    def _onchange_type_trigger_attrs(self):
        self._compute_attrs_standard_price()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _is_invisible_standard_price(self):
        return super(ProductProduct, self)._is_invisible_standard_price() or self.type == 'asset'

    @api.onchange('type')
    def _onchange_type_trigger_attrs(self):
        self._compute_attrs_standard_price()
