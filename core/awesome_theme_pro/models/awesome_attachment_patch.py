# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os

from odoo import api, fields, models, tools, _

_logger = logging.getLogger(__name__)


class IrAttachmentPatch(models.Model):
    """
    IrAttachmentPatch
    """
    _inherit = 'ir.attachment'

    @api.model
    def _file_read(self, fname):
        """
        check the file exsits
        :param fname:
        :return:
        """
        full_path = self._full_path(fname)
        if not os.path.exists(full_path):
            return b''
        try:
            with open(full_path, 'rb') as f:
                return f.read()
        except (IOError, OSError):
            _logger.info("_read_file reading %s", full_path, exc_info=True)
        return b''
