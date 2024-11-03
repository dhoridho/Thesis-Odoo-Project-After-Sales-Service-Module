# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import float_is_zero
from odoo.tools import float_compare, float_round, float_repr
from odoo.tools.misc import formatLang, format_date
from odoo.exceptions import UserError, ValidationError

import time
import math
import base64
import re


class AccountBankStatement(models.Model): 
    _inherit = 'account.bank.statement'


    def button_reopen(self):
        ''' Move the bank statements back to the 'open' state. '''
        self.ensure_one()
        if any(statement.state == 'draft' for statement in self):
            raise UserError(_("Only validated statements can be reset to new."))

        self.write({'state': 'open'})
        # self.line_ids.move_id
        for line in self.line_ids:
            line.move_id.button_draft()
        self.line_ids.sudo().button_undo_reconciliation()


    
