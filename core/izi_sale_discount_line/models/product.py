# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

ACCOUNT_DOMAIN = "['&', '&', '&', ('deprecated', '=', False), ('internal_type','=','other'), ('company_id', '=', current_company_id), ('is_off_balance', '=', False)]"

class ProductTemplate(models.Model):
    _inherit = "product.template"

    property_account_giveaway_id = fields.Many2one('account.account', company_dependent=True,
        string="Giveaway Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the expense account on the product category will be used.")

    property_account_discount_id = fields.Many2one('account.account', company_dependent=True,
        string="Discount Account",
        domain=ACCOUNT_DOMAIN,
        help="Keep this field empty to use the default value from the product category. If anglo-saxon accounting with automated valuation method is configured, the discount account on the product category will be used.")

    def _get_product_accounts(self):
        """ Add the stock accounts related to product to the result of super()
        @return: dictionary which contains information regarding stock accounts and super (income+expense accounts)
        """
        accounts = super(ProductTemplate, self)._get_product_accounts()
        accounts.update({
            'giveaway': self.property_account_giveaway_id or self.categ_id.property_account_giveaway_categ_id,
            'discount': self.property_account_discount_id or self.categ_id.property_account_discount_categ_id,
        })
        return accounts
class ProductCategory(models.Model):
    _inherit = "product.category"

    property_account_giveaway_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Giveaway Account",
        domain=ACCOUNT_DOMAIN,
        help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon accounting with perpetual inventory valuation in which case the expense (Cost of Goods Sold account) is recognized at the customer invoice validation.")
    
    property_account_discount_categ_id = fields.Many2one('account.account', company_dependent=True,
        string="Discount Account",
        domain=ACCOUNT_DOMAIN,
        help="The expense is accounted for when a vendor bill is validated, except in anglo-saxon accounting with perpetual inventory valuation in which case the expense (Cost of Goods Sold account) is recognized at the customer invoice validation.")
