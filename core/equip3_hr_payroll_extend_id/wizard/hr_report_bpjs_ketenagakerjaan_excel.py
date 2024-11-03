# -*- coding: utf-8 -*-
from odoo import fields, models

class HrReportBpjsKetenagakerjaanExcel(models.TransientModel):
    _name = "hr.report.bpjs.ketenagakerjaan.excel"
    _description = "Bpjs Ketenagakerjaan Report Excel"

    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File')