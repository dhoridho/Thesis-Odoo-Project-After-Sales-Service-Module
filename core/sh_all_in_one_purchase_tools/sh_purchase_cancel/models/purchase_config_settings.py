# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    po_operation_type = fields.Selection([('cancel', 'Cancel Only'), ('cancel_draft', 'Cancel and Reset to Draft'), ('cancel_delete', 'Cancel and Delete')],
                                         default='cancel', string="Opration Type")

    cancel_receipt = fields.Boolean("Cancel Receipt")
    cancel_bill = fields.Boolean("Cancel Bill and Payment")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    po_operation_type = fields.Selection(string="Opration Type", related="company_id.po_operation_type", readonly=False)

    cancel_receipt = fields.Boolean(
        "Cancel Receipt", related='company_id.cancel_receipt', readonly=False)
    cancel_bill = fields.Boolean(
        "Cancel Bill and Payment", related='company_id.cancel_bill', readonly=False)
