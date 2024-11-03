# -*- coding: utf-8 -*-
# Copyright (C) 2021-TODAY CoderLab Technology Pvt Ltd
# https://coderlabtechnology.com

from odoo import fields, models


class SaleInvoiceSummaryExcelReport(models.TransientModel):
    _name = "sale.commission.excel.report"
    _description = "Sale Commission Excel Report"

    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File', size=256)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sale.commission.excel.report&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }