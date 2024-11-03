from odoo import models, fields, api, _
from datetime import date, timedelta
from dateutil import relativedelta


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    contracted_price = fields.Float(string='Contracted Price', compute='_compute_contracted_price', store=True)
    
    @api.depends('agreement_id.stage_id', 'property_book_for', 'deposite', 'discounted_price')
    def _compute_contracted_price(self):
        for product in self:
            if product.agreement_id:
                if product.agreement_id.stage_id.is_recurring_invoice == True or product.agreement_id.stage_id.is_non_recurring_invoice == True:
                    if product.property_book_for == 'rent':
                        product.contracted_price = product.deposite
                    elif product.property_book_for == 'sale':
                        product.contracted_price = product.discounted_price
                else:
                    product.contracted_price = 0
            else:
                product.contracted_price = 0
                
