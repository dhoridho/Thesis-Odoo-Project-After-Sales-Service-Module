import base64
import io

import xlsxwriter

from odoo import models, api, fields


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model
    def summary_for_principal_xlsx_report(self, records):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        bold = workbook.add_format({'bold': True})

        c = 0
        sheet.set_column(c, c, 30)
        c += 1
        sheet.set_column(c, c, 15)
        c += 1
        sheet.set_column(c, c, 20)
        c += 1
        sheet.set_column(c, c, 40)
        c += 1
        sheet.set_column(c, c, 15)
        c += 1
        sheet.set_column(c, c, 20)
        c += 1
        sheet.set_column(c, c, 20)

        r = 0
        c = 0

        sheet.write(r, c, 'Squence Number', bold)
        c += 1
        sheet.write(r, c, 'Brand', bold)
        c += 1
        sheet.write(r, c, 'Product /Product Code', bold)
        c += 1
        sheet.write(r, c, 'Product/Name', bold)
        c += 1
        sheet.write(r, c, 'Quantity', bold)
        c += 1
        sheet.write(r, c, 'Delivered Quantity', bold)
        c += 1
        sheet.write(r, c, 'Unit Of Measure', bold)
        c += 1

        r += 1
        for rec in records:
            c = 0
            sheet.write(r, c, rec.sequence_no)
            c += 1
            sheet.write(r, c, rec.brand_ids.display_name)
            c += 1
            sheet.write(r, c, rec.product_id.default_code)
            c += 1
            sheet.write(r, c, rec.product_id.name)
            c += 1
            sheet.write(r, c, rec.product_uom_qty)
            c += 1
            sheet.write(r, c, rec.qty_delivered)
            c += 1
            sheet.write(r, c, rec.product_id.uom_id.display_name)
            r += 1
        filename = ('Summary_for_Principal' + '.xlsx')
        workbook.close()

        export_id = self.env['summary.principal.report.xls'].sudo().create({
            'excel_file': base64.encodebytes(output.getvalue()),
            'file_name': filename,
        })
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=summary.principal.report.xls&field=excel_file&download=true&id=%s&filename=%s' % (export_id.id, filename),
            'target': 'self',
        }

class SummaryForPrincipalReportXlsx(models.TransientModel):
    _name = 'summary.principal.report.xls'
    _description = 'Summary for Principal'
    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64, readonly=True)
