# -*- coding: utf-8 -*-
from odoo import models, fields


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    delete_old = fields.Boolean('Delete if old', default=False,
                                help="It can be removed if it is old.")
