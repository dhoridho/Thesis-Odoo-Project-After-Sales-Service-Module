# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round as round
import math

class AccountTax(models.Model):
    _inherit = 'account.tax'
    
    
    def tax_round(self, tax_amount, precision_rounding=0.01):
        res_config = self.env['res.config.settings'].sudo().search([], order="id desc", limit=1)
        tax_rounding_type = res_config.tax_rounding_type
        frac , whole  = math.modf(tax_amount)
        
        frac_num = round(frac/precision_rounding, precision_rounding=1e-14)

        def round_half_up(n, value, decimals=0):
            multiplier = value**decimals
            return math.floor(n * multiplier + 0.5) / multiplier

        if tax_rounding_type == 'round_type_up':
            frac_num = math.ceil(frac_num)
        elif tax_rounding_type == 'round_type_down':
            frac_num = math.floor(frac_num)
        else:
            # if frac_num != 0:
            #     return round_half_up(tax_amount, frac_num)
            return round(tax_amount, precision_rounding=precision_rounding)

        frac = frac_num*precision_rounding
        result = whole + frac
        return result