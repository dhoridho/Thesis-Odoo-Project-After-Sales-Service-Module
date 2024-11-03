# -*- coding: utf-8 -*-

from odoo import fields, models

class PayslipBatchReport(models.TransientModel):
    _name = "purchase.tender.xls.report"
    _description = 'Purchase Tender Xls Report'

    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File', size=256)