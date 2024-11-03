# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleInvoiceSummaryExcelReport(models.TransientModel):
    _name = "warehouse.capacity.excel.report"
    _description = "Warehouse Capacity Excel Report"

    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File', size=256)