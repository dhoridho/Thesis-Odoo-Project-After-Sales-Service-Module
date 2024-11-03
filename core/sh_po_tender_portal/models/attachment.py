# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    sh_is_publish_in_portal = fields.Boolean('Publish in tender portal ?')