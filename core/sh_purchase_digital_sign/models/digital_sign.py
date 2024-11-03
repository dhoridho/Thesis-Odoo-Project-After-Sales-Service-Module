# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import models, fields, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    purchase_show_signature = fields.Boolean(
        "Show digital sign in Purchase Orders ?")
    chk_sign_confirm = fields.Boolean("Check sign before Confirmation")

    purchase_enable_other_sign_option = fields.Boolean(
        "Enable Other Sign Option")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_show_signature = fields.Boolean(
        "Show digital sign in Purchase Orders ?", related="company_id.purchase_show_signature", readonly=False)
    chk_sign_confirm = fields.Boolean(
        "Check sign before Confirmation", related="company_id.chk_sign_confirm", readonly=False)

    purchase_enable_other_sign_option = fields.Boolean(
        "Enable Other Sign Option", related="company_id.purchase_enable_other_sign_option", readonly=False)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    digital_sign = fields.Binary("Signature")
    purchase_show_signature = fields.Boolean(
        "Show digital sign in Purchase Orders ?", related="company_id.purchase_show_signature")
    chk_sign_confirm = fields.Boolean(
        "Check sign before Confirmation", related="company_id.chk_sign_confirm")

    purchase_show_enable_other_sign = fields.Boolean(
        "Enable Other sign Option", related="company_id.purchase_enable_other_sign_option")
    sign_by = fields.Char("Signed By")
    designation = fields.Char("Designation")
    sign_on = fields.Datetime(
        'Sign on', default=lambda self: fields.Datetime.now())

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        if self.chk_sign_confirm:
            if not self.digital_sign:
                raise UserError(_('There is no Signature'))
        return res
