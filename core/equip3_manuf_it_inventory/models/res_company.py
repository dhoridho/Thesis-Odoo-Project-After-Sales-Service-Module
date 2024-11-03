# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import logging
_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = 'Res Company'

    is_ceisa_it_inventory = fields.Boolean(string='Set Ceisa 4.0', default=False)
