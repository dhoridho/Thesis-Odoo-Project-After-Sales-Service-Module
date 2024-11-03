# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class PosNote(models.Model):
    _name = "pos.note"
    _description = "Management Order Note"

    name = fields.Text('Note', required=1)