# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    auto_print = fields.Boolean(string='Automatic printing')
    preview_print = fields.Boolean(string='Preview print')

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "auto_print", "preview_print"
        }
