# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class PurchaseOrderTemplate(models.Model):
    _inherit = "purchase.order"
    _description = "Purchase Report Template"

    order_report_id = fields.Many2one(
        comodel_name="sh.report.template",
        string="Purchase Order Template"
    )
    rfq_report_id = fields.Many2one(
        comodel_name="sh.report.template",
        string="RFQ Template"
    )
