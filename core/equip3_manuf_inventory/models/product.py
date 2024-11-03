from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _is_lot_auto_generate(self):
        self.ensure_one()
        return self.tracking == 'lot' and self.is_in_autogenerate

    def _is_serial_auto_generate(self):
        self.ensure_one()
        return self.tracking == 'serial' and self.is_sn_autogenerate

    def _is_manual_generate(self):
        self.ensure_one()
        return (self.tracking == 'serial' and not self.is_sn_autogenerate) or (self.tracking == 'lot' and not self.is_in_autogenerate)
