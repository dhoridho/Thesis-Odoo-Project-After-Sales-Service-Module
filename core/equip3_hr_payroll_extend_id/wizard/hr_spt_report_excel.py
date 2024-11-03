# -*- coding: utf-8 -*-
from odoo import fields, models

class HrSptReportExcel(models.TransientModel):
    _name = "hr.spt.report.excel"
    _description = "HR SPT Report Excel"

    excel_file = fields.Binary('Excel Report')
    file_name = fields.Char('Excel File')