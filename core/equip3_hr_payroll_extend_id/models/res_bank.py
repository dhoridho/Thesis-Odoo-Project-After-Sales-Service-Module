# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def name_get(self):
        result = []
        for bank in self:
            bank_name = bank.bank_id.name if bank.bank_id else ''
            name = bank_name + (bank.acc_number and (' - ' + bank.acc_number) or '')
            result.append((bank.id, name))
        return result