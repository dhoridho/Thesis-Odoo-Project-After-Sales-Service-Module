
from odoo import models, fields, api, _

class ProductCategory(models.Model):
    _inherit = 'product.category'

    def _get_default_rental_account(self):
        return self.env['account.account'].search([('code','=','6#######')]).id

    rental_account = fields.Many2one('account.account', string="Rental Account", default=_get_default_rental_account, tracking=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_rented = fields.Boolean(string='Can be Rented')

    @api.onchange('is_rented')
    def _change_is_rented(self):
        if self.is_rented:
            self.tracking = 'serial'
        else:
            self.tracking = 'none'
