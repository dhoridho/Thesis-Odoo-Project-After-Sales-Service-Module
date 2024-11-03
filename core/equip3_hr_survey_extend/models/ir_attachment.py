# -*- coding: utf-8 -*-
from odoo import api, models, fields, tools


class IrAttachment(models.Model):
    _inherit = "ir.attachment"


    def _get_media_info(self):
        """Return a dict with the values that we need on the media dialog."""
        self.ensure_one()
        return self._read_format(['id', 'name', 'datas', 'description', 'mimetype', 'checksum', 'url', 'type', 'res_id', 'res_model', 'public', 'access_token', 'image_src', 'image_width', 'image_height', 'original_id'])[0]
