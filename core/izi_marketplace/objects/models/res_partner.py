# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    mp_account_ids = fields.Many2many(
        comodel_name='mp.account',
        relation='res_partner_mp_account_rel',
        string='Marketplace Account'
    )
    phone = fields.Char(index=True)
