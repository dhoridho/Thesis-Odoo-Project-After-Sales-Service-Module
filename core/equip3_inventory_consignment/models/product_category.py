from odoo import api, fields, models, _


class ProductCategory(models.Model):
    _inherit = 'product.category'

    consignment_commision_account = fields.Many2one('account.account', 'Consignment Commision Account',
                                                    domain="[('deprecated', '=', False), ('company_id', '=', current_company_id),('user_type_id.type','not in', ('receivable','payable')),('is_off_balance', '=', False)]",
                                                    tracking=True)
