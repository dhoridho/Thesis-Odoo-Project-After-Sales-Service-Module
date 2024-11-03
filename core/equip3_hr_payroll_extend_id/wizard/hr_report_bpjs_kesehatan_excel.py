# -*- coding: utf-8 -*-
from odoo import fields, models

class HrReportBpjsKesehatanExcel(models.TransientModel):
    _name = "hr.report.bpjs.kesehatan.excel"
    _description = "Bpjs Kesehatan Report Excel"

    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File')