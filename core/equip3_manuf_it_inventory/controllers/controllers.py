from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter
 
 
class ReportController(http.Controller):
    @http.route(['/inbound_reports/excel_report/<model("inbound.reports"):wizard>'], type='http', auth="public")
    def get_inbound_excel_report(self,wizard=None,**args):
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('Laporan Pemasukan Barang' + '.xlsx'))
                        # ('Content-Disposition', content_disposition('Inbound Reports' + '.xlsx'))
                    ]
                )
 
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
 
        title_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 14, 'bold': True, 'align': 'center'})
        header_style = workbook.add_format({'font_name': 'Calibri', 'bold': True, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center'})
        text_style = workbook.add_format({'font_name': 'Calibri', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center'})
        # text_style = workbook.add_format({'font_name': 'Calibri', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'left'})
        # number_style = workbook.add_format({'font_name': 'Calibri', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
        # Inbound Report
        sheet = workbook.add_worksheet("Laporan Pemasukan Barang")
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.set_margins(0.5,0.5,0.5,0.5)

        sheet.set_column('A:A', 20)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 40)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 20)
        sheet.set_column('K:K', 20)
        sheet.set_column('L:L', 20)
        sheet.set_column('M:M', 20)

        sheet.merge_range('A1:M1', 'Laporan Pemasukan Barang', title_style)
        
        sheet.write(1, 0, 'Document Type', header_style)
        sheet.write(1, 1, 'Registration Number', header_style)
        sheet.write(1, 2, 'Registration Date', header_style)
        sheet.write(1, 3, 'Request Number', header_style)
        sheet.write(1, 4, 'Receiving Notes', header_style)
        sheet.write(1, 5, 'Receiving Date', header_style)
        sheet.write(1, 6, 'Purchase Order', header_style)
        sheet.write(1, 7, 'Vendor', header_style)
        sheet.write(1, 8, 'Product Code', header_style)
        sheet.write(1, 9, 'Product', header_style)
        sheet.write(1, 10, 'UoM', header_style)
        sheet.write(1, 11, 'Quantity', header_style)
        sheet.write(1, 12, 'Value', header_style)

        row = 2
        
        for rec in wizard:
            for picking_line in rec.preview_reports_ids:
                sheet.write(row, 0, str(picking_line.document_type_id.document_type), text_style)
                sheet.write(row, 1, str(picking_line.registration_number), text_style)
                sheet.write(row, 2, str(picking_line.registration_date), text_style)
                sheet.write(row, 3, str(picking_line.request_number), text_style)
                sheet.write(row, 4, str(picking_line.note), text_style)
                sheet.write(row, 5, str(picking_line.date_done), text_style)
                sheet.write(row, 6, str(picking_line.group_id.name), text_style)
                sheet.write(row, 7, str(picking_line.partner_id.name), text_style)
                sheet.write(row, 8, str(picking_line.product_code), text_style)
                sheet.write(row, 9, str(picking_line.product_id.name), text_style)
                sheet.write(row, 10, str(picking_line.uom_id.name), text_style)
                sheet.write(row, 11, str(picking_line.quantity), text_style)
                sheet.write(row, 12, str(picking_line.value), text_style)
                row += 1
                                
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

        return response

    
    @http.route(['/outbound_reports/excel_report/<model("outbound.reports"):wizard>'], type='http', auth="public")
    def get_outbound_excel_report(self,wizard=None,**args):
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('Laporan Pengeluaran Barang' + '.xlsx'))
                    ]
                )
 
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
 
        title_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 14, 'bold': True, 'align': 'center'})
        header_style = workbook.add_format({'font_name': 'Calibri', 'bold': True, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center'})
        text_style = workbook.add_format({'font_name': 'Calibri', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center'})
        # text_style = workbook.add_format({'font_name': 'Calibri', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'left'})
        # number_style = workbook.add_format({'font_name': 'Calibri', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
 
        # sheet = workbook.add_worksheet("Outbound Report")
        sheet = workbook.add_worksheet("Laporan Pengeluaran Barang")
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.set_margins(0.5,0.5,0.5,0.5)

        sheet.set_column('A:A', 20)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 40)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 20)
        sheet.set_column('K:K', 20)
        sheet.set_column('L:L', 20)
        sheet.set_column('M:M', 20)

        sheet.merge_range('A1:M1', 'Laporan Pengeluaran Barang', title_style)
        
        sheet.write(1, 0, 'Document Type', header_style)
        sheet.write(1, 1, 'Registration Number', header_style)
        sheet.write(1, 2, 'Registration Date', header_style)
        sheet.write(1, 3, 'Request Number', header_style)
        sheet.write(1, 4, 'Receiving Notes', header_style)
        sheet.write(1, 5, 'Receiving Date', header_style)
        sheet.write(1, 6, 'Sales Order', header_style)
        sheet.write(1, 7, 'Vendor', header_style)
        sheet.write(1, 8, 'Product Code', header_style)
        sheet.write(1, 9, 'Product', header_style)
        sheet.write(1, 10, 'UoM', header_style)
        sheet.write(1, 11, 'Quantity', header_style)
        sheet.write(1, 12, 'Value', header_style)

        row = 2
        
        for rec in wizard:
            for picking_line in rec.preview_reports_ids:
                sheet.write(row, 0, str(picking_line.document_type_id.document_type), text_style)
                sheet.write(row, 1, str(picking_line.registration_number), text_style)
                sheet.write(row, 2, str(picking_line.registration_date), text_style)
                sheet.write(row, 3, str(picking_line.request_number), text_style)
                sheet.write(row, 4, str(picking_line.note), text_style)
                sheet.write(row, 5, str(picking_line.date_done), text_style)
                sheet.write(row, 6, str(picking_line.group_id.name), text_style)
                sheet.write(row, 7, str(picking_line.partner_id.name), text_style)
                sheet.write(row, 8, str(picking_line.product_code), text_style)
                sheet.write(row, 9, str(picking_line.product_id.name), text_style)
                sheet.write(row, 10, str(picking_line.uom_id.name), text_style)
                sheet.write(row, 11, str(picking_line.quantity), text_style)
                sheet.write(row, 12, str(picking_line.value), text_style)
                row += 1
                                
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

        return response

    @http.route(['/raw_material_mutation_reports/excel_report/<model("it.inventory.raw.material"):model>'], type='http', auth="public")
    def get_raw_material_excel_report(self,model=None,**args):
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('Mutation of Raw Materials Reports' + '.xlsx'))
                    ]
                )
 
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
 
        title_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 14, 'bold': True, 'align': 'center'})
        header_style = workbook.add_format({'font_name': 'Calibri', 'bold': True, 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center'})
        text_style = workbook.add_format({'font_name': 'Calibri', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'center'})
        # text_style = workbook.add_format({'font_name': 'Calibri', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'left'})
        # number_style = workbook.add_format({'font_name': 'Calibri', 'left': 1, 'bottom':1, 'right':1, 'top':1, 'align': 'right'})
 
        sheet = workbook.add_worksheet("Mutation of Raw Materials Report")
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.set_margins(0.5,0.5,0.5,0.5)

        sheet.set_column('A:A', 20)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 40)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 20)
        sheet.set_column('K:K', 20)
        sheet.set_column('L:L', 20)
        sheet.set_column('M:M', 20)

        sheet.merge_range('A1:L1', 'Mutation of Raw Materials Report', title_style)
        sheet.merge_range('A3:F3', 'LAPORAN PERTANGGUNGJAWABAN RAW MATERIALS MUTATION', title_style)
        sheet.merge_range('A4:F4', 'KAWASAN BERIKAT COMPANY', title_style)
        sheet.merge_range('A5:F5', 'WAREHOUSE', title_style)
        sheet.merge_range('A6:F6', 'REPORT TYPE: ', title_style)
        sheet.merge_range('A7:F7', 'PERIODE:', title_style)
        
        sheet.write(7, 0, 'No', header_style)
        sheet.write(7, 1, 'Registration Number', header_style)
        sheet.write(7, 2, 'Product', header_style)
        sheet.write(7, 3, 'UoM', header_style)
        sheet.write(7, 4, 'First Balance', header_style)
        sheet.write(7, 5, 'Income', header_style)
        sheet.write(7, 6, 'Outcome', header_style)
        sheet.write(7, 7, 'Adjustment', header_style)
        sheet.write(7, 8, 'Last Balance', header_style)
        sheet.write(7, 9, 'Stock Opname', header_style)
        sheet.write(7, 10, 'Difference', header_style)
        sheet.write(7, 11, 'Decsription', header_style)

        row = 8
        number = 0
        
        for rec in model:
            sheet.write(row, 0, str(number), text_style)
            sheet.write(row, 1, str(rec.registration_number), text_style)
            sheet.write(row, 2, str(rec.product_id.name), text_style)
            sheet.write(row, 3, str(rec.uom_id.name), text_style)
            sheet.write(row, 4, str(rec.first_balance), text_style)
            sheet.write(row, 5, str(rec.income), text_style)
            sheet.write(row, 6, str(rec.outcome), text_style)
            sheet.write(row, 7, str(rec.adjustment), text_style)
            sheet.write(row, 8, str(rec.last_balance), text_style)
            sheet.write(row, 9, str(rec.stock_opname), text_style)
            sheet.write(row, 10, str(rec.difference), text_style)
            sheet.write(row, 11, str(rec.description), text_style)
            row += 1
            number += 1
                                
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

        return response
