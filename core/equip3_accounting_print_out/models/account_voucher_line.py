from odoo import models,fields,api

class accountVoucherLine(models.Model):
    _inherit  = 'account.voucher.line'
    
    def get_tax_string(self):
        for data in self:
            tax_list  = []
            if data.tax_ids:
                for tax in data.tax_ids:
                    tax_list.append(tax.name)
            return ','.join(tax_list)