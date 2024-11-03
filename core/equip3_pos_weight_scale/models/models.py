# -*- coding: utf-8 -*-

from odoo import models, fields


class PosConfWeightMachine(models.Model):
    _inherit = 'pos.config'

    pos_drive_link = fields.Char(string="Localhost link Weight Machine", 
        help="Localhost link for Weight Machine\nProd: http://localhost:9100/get-weight-scale\nTest: http://localhost:9100/api-testing/get-weight-scale", 
        default='http://localhost:9100/get-weight-scale')