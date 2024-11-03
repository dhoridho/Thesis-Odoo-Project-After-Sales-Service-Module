# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools.float_utils import float_round as round
from odoo.exceptions import UserError, ValidationError

import math
import logging

class AccountTax(models.Model):
    _inherit = "account.tax"

    gst_category_code = fields.Char(string='GST Category Code', help='Code List refer to https://www.peppolguide.sg/billing/codelist/SGTaxCat/', )