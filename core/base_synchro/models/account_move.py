# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from datetime import date, timedelta
from collections import defaultdict
from itertools import zip_longest
from hashlib import sha256
from json import dumps

import ast
import json
import re
import warnings

class AccountMove(models.Model):
    _inherit = "account.move"
     
    # copy_moves = fields.Boolean(string="copy_moves")

    # @api.model_create_multi
    # def create(self, vals_list):
    #     # OVERRIDE
    #     # if any('state' in vals and vals.get('state') == 'posted' for vals in vals_list):
    #     #     print("masuk ke sini")
    #     #     for vals in vals_list:
    #     #         if 'copy_moves' in vals:
    #     #             print(vals['name'])
    #     #             print(vals['copy_moves'])
    #     #             if vals['copy_moves'] == True:
    #     #                 vals['state'] = 'draft'
    #     #                 vals['state1'] = 'draft'
    #     #                 vals['state2'] = 'draft'
    #     #     print("+++++++++++++++++++++++++++++++++++")
    #     # print("for vals in vals_list:")
    #     for vals in vals_list:
    #         print(vals['name'])
    #         print(vals['copy_moves'])
    #         print(vals['state'])
    #         print(vals['state1'])
    #         print(vals['state2'])
    #     print("===============================")
    #     rslt = super(AccountMove, self).create(vals_list)
    #     return rslt