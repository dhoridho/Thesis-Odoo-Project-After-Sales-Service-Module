from odoo import models, fields, api, _

class AgreementLine(models.Model):
    _inherit = 'agreement.line'

    unit_price = fields.Float(compute='compute_unit_price_property')
    
    @api.depends('product_id')
    def compute_unit_price_property(self):
        for line in self:
            if line.product_id:
                if line.product_id.is_property == True:
                    if line.product_id.property_book_for == 'rent':
                        line.unit_price = line.product_id.deposite
                    elif line.product_id.property_book_for == 'sale':
                        line.unit_price = line.product_id.discounted_price
                    else:
                        line.unit_price = line.product_id.lst_price
                else:
                    line.unit_price = line.product_id.lst_price
            else:
                line.unit_price = 0.0

AgreementLine()
    
    
   