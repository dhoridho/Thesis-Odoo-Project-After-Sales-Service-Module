# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MPTiktokStateOrder(models.Model):
    _name = 'mp.tiktok.state.order'
    _description = 'Marketplace Tiktok Status Order'

    code = fields.Integer(string='Code')
    name = fields.Char(string='Status Name')
