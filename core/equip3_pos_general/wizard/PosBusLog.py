# -*- coding: utf-8 -*-

from odoo import api, models, fields

class PosBusLog(models.TransientModel):
    _name = "pos.bus.log"
    _description = "Transactions of Point Sync"