from odoo import models, fields
from datetime import timedelta


class MrpConsumption(models.Model):
    _inherit = 'mrp.consumption'

    expiry_days = fields.Integer('Expiry Days', related='product_id.expiration_time')
    product_use_expiration_date = fields.Boolean(related='product_id.use_expiration_date')

    def _get_expiration_date(self):
        self.ensure_one()
        if self.product_use_expiration_date:
            now = fields.Datetime.now()
            return now + timedelta(days=self.expiry_days)
        return False
