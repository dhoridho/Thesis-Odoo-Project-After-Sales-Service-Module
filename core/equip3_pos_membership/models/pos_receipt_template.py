# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PosReceiptTemplate(models.Model):
    _inherit = "pos.receipt.template"

    is_receipt_member_info = fields.Boolean('Loyalty member information')

    def receipt_template_dict_data(self):
        company = self.env.user.company_id
        currency = company.currency_id
        res = super(PosReceiptTemplate, self).receipt_template_dict_data()
        res['is_receipt_member_info'] = self.is_receipt_member_info
        return res

