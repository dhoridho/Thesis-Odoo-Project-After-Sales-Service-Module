from datetime import datetime
import io
import xlsxwriter
from odoo import http
from odoo.http import content_disposition, request

class PropertyWizardController(http.Controller):
    @http.route(['/property/property_wizard'], type='http', auth="user", csrf=False)
    def get_contract_record(self, id, start, end):
        response = request.make_response(
            None,
            headers=[
                ('Content-Type', 'application/vnd.ms-excel'),
                ('Content-Disposition', content_disposition('Revenue Forecast' + str(datetime.now().date()) + '.xlsx'))
            ]
        )

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Styles
        title_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 33, 'bold': False, 'align': 'left'})
        text_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 11, 'align': 'left', 'valign': 'vcenter'})
        header_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 16, 'align': 'left', 'valign': 'vcenter'})
        header_style2 = workbook.add_format({'font_name': 'Calibri', 'font_size': 22, 'align': 'left', 'valign': 'vcenter'})
        date_format = workbook.add_format({'font_name': 'Calibri', 'align': 'left', 'font_size': 11, 'num_format': 'dd/mm/yy'})
        sub_total = workbook.add_format({'num_format': '#,##0.00', 'align': 'right', 'font_size': 11, 'bold': True})

        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()

        now = datetime.now()
        date_time = now.strftime("%d %B %Y")

        wiz_id = request.env['revenue.forecast.report'].sudo().search([('id', '=', id)])

        for rec in wiz_id.property_ids.sorted(key=lambda r: r.create_date):
            sheet = workbook.add_worksheet(rec.name)

            sheet.set_column('B:B', 30)
            sheet.set_column('C:C', 15)

            sheet.write(0, 0, date_time, text_style)
            sheet.write(1, 9, 'Revenue Forecast', title_style)
            sheet.write(2, 9, f'Periode: {start_date.strftime("%d %B %Y")} - {end_date.strftime("%d %B %Y")}', header_style)
            sheet.write(3, 9, f'{rec.name}', header_style2)

            agreement_ids = request.env['agreement'].sudo().search([('property_id', '=', rec.id)])

            row = 9
            col_statis = 0
            col_contract_maintenance = 0
            row_date = 7
            row_revenue = 13
            row_revenue_maintenance = 14
            row_total_contract_maintenance = 18
            row_all_total = 18

            row_expected_revenue_for_this_contract = 11

            for agreement_id in agreement_ids:
                col_statis = 0
                sheet.write(row, col_statis, 'Title:', text_style)
                col_statis += 1
                sheet.write(row, col_statis, agreement_id.name, text_style)
                row += 1
                sheet.write(row, col_statis, 'Description', text_style)
                row += 1
                sheet.write(row, col_statis, 'Expected Revenue From This Contract', text_style)
                row += 2
                sheet.write(row, col_statis, 'Invoice Price', text_style)
                row += 1
                sheet.write(row, col_statis, 'Maintenance Price', text_style)
                row += 1
                sheet.write(row, col_statis, 'Invoice Price', text_style)
                row += 1
                sheet.write(row, 1, 'Taxes', text_style)
                row += 1
                sheet.write(row, 1, 'Tax', text_style)
                row += 1
                sheet.write(row, 1, 'Total', text_style)
                row += 1
                sheet.write(row, 1, 'Renter', text_style)
                col_statis += 2
                sheet.write(row, col_statis, agreement_id.partner_id.name, text_style)
                row += 5

                col = 5
                col_total_revenue = 8
                total_revenue = 0
                total_revenue_maintenance = 0
                col_all_total = 8
                invoice_date_after_write = False
                invoice_ids = request.env['account.move'].search([
                    ('agreement_id', '=', agreement_id.id),
                    ('invoice_date', '>=', start_date),
                    ('invoice_date', '<=', end_date)
                ]).sorted(key=lambda r: r.invoice_date)

                total_bottom_contract = 0
                total_bottom_maintenance = 0
                total_bottom_contract_maintenance = 0

                for invoice in invoice_ids:
                    if start_date <= invoice.invoice_date <= end_date:
                        if invoice.invoice_date == invoice_date_after_write:
                            col -= 3
                            col_total_revenue -= 3
                            col_all_total -= 3

                            total_bottom_contract += invoice.amount_untaxed if not invoice.property_maintenance_id else 0
                            total_bottom_maintenance += invoice.amount_untaxed if invoice.property_maintenance_id else 0
                            total_bottom_contract_maintenance = total_bottom_contract + total_bottom_maintenance

                            total_revenue += invoice.amount_untaxed if not invoice.property_maintenance_id else 0
                            total_revenue_maintenance += invoice.amount_untaxed if invoice.property_maintenance_id else 0

                            sheet.write(row_revenue, col, total_bottom_contract, sub_total)
                            sheet.write(row_revenue_maintenance, col, total_bottom_maintenance, sub_total)
                            sheet.write(row_total_contract_maintenance, col, total_bottom_contract_maintenance, sub_total)
                        else:
                            sheet.set_column(col, col, 15)
                            sheet.set_column(col_total_revenue, col_total_revenue, 15)

                            total_revenue += invoice.amount_untaxed if not invoice.property_maintenance_id else 0
                            total_revenue_maintenance += invoice.amount_untaxed if invoice.property_maintenance_id else 0

                            sheet.write(row_date, col, invoice.invoice_date, date_format)
                            invoice_date_after_write = invoice.invoice_date

                            sheet.write(row_revenue, col, invoice.amount_untaxed if not invoice.property_maintenance_id else 0, sub_total)
                            sheet.write(row_revenue_maintenance, col, invoice.amount_untaxed if invoice.property_maintenance_id else 0, sub_total)
                            sheet.write(row_total_contract_maintenance, col, invoice.amount_untaxed if invoice.property_maintenance_id else 0 + invoice.amount_untaxed if not invoice.property_maintenance_id else 0, sub_total)

                            total_bottom_contract = invoice.amount_untaxed if not invoice.property_maintenance_id else 0
                            total_bottom_maintenance = invoice.amount_untaxed if invoice.property_maintenance_id else 0

                            total_bottom_contract_maintenance = total_bottom_contract + total_bottom_maintenance

                        col += 3
                        col_total_revenue += 3
                        col_all_total += 3

                sheet.write(row_expected_revenue_for_this_contract, 2, total_revenue + total_revenue_maintenance, sub_total)

                sheet.write(row_date, col_total_revenue - 3, 'Total', text_style)
                sheet.write(row_revenue, col_total_revenue - 3, total_revenue, sub_total)
                sheet.write(row_revenue_maintenance, col_total_revenue - 3, total_revenue_maintenance, sub_total)
                sheet.write(row_all_total, col_all_total - 3, total_revenue + total_revenue_maintenance, sub_total)

                row_date += 14
                row_revenue += 14
                row_revenue_maintenance += 14
                row_total_contract_maintenance += 14
                row_all_total += 14
                row_expected_revenue_for_this_contract += 15

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

        return response
