from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter
from datetime import datetime
import locale


class AllControllerExcel(http.Controller):
    @http.route(['/asset_report/forecast_excel_report'], type='http', auth="user", csrf=False)
    def test_control_excel_all(self):
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('Forecast Reports' + '.xlsx'))
                    ]
                )

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        header_format = workbook.add_format({'font_name': 'Arial','bold': True, 'font_size': 15,'valign': 'vcenter', 'align': 'center'})
        year_format_15 = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'font_size': 13})
        header_column = workbook.add_format({'font_name': 'Arial', 'bold': True , 'align': 'center', 'valign': 'vcenter', 'font_size': 10, 'text_wrap': True,
                                             'left': 1, 'right' : 1, 'top' : 1, 'fg_color' : '#F2F2F2'})
        body_column = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'font_size': 10,
                                           'left': 1, 'right' : 1, 'top' : 1})
        year_format = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter','font_size': 10,
                                           'left': 1, 'right' : 1, 'top' : 1})
        footer_format = workbook.add_format({'top' : 1})

        sheet = workbook.add_worksheet('timesheet')

        sheet.set_column('A:L', 15)
        sheet.set_row(7, 50)

        sheet.merge_range('A' + str(3) + ':L' + str(3), 'FORECAST HOUR METER MAINTENANCE REPORT', header_format)
        

        tanggal_hari_ini = datetime.now().date()
        if tanggal_hari_ini.month == 1:
            bulan = 'Januari'
        if tanggal_hari_ini.month == 2:
            bulan = 'Februari'
        if tanggal_hari_ini.month == 3:
            bulan = 'Maret'
        if tanggal_hari_ini.month == 4:
            bulan = 'April'
        if tanggal_hari_ini.month == 5:
            bulan = 'Mei'
        if tanggal_hari_ini.month == 6:
            bulan = 'Juni'
        if tanggal_hari_ini.month == 7:
            bulan = 'Juli'
        if tanggal_hari_ini.month == 8:
            bulan = 'Agustus'
        if tanggal_hari_ini.month == 9:
            bulan = 'September'
        if tanggal_hari_ini.month == 10:
            bulan = 'Oktober'
        if tanggal_hari_ini.month == 11:
            bulan = 'November'
        if tanggal_hari_ini.month == 12:
            bulan = 'Desember'
        tanggal_format = tanggal_hari_ini.strftime(f'%d {bulan} %Y')
        sheet.write(5, 5, tanggal_format, year_format_15)

        sheet.write(7,0, 'No', header_column)
        sheet.write(7,1, 'Equipment Name', header_column)
        sheet.write(7,2, 'Serial Number', header_column)
        sheet.write(7,3, 'Brand', header_column)
        sheet.write(7,4, 'Status', header_column)
        sheet.write(7,5, 'Last Date', header_column)
        sheet.write(7,6, 'Current Hour Meter ( Hours )', header_column)
        sheet.write(7,7, 'Hour Meter Threshold (Hours)', header_column)
        sheet.write(7,8, 'Cumulative Hour Meter (Hours)', header_column)
        sheet.write(7,9, 'Hour Meter Type', header_column)
        sheet.write(7,10, 'End Date', header_column)
        sheet.write(7,11, 'Diff', header_column)
        
        row = 8
        no = 1

        forecast_hour_meter = request.env['forecast.hour.meter.maintenance'].search([])

        for rec in forecast_hour_meter:
            last_date = rec.last_date.strftime(f'%d/%m/%Y')
            monthly = rec.monthly.strftime(f'%d/%m/%Y')
            sheet.write(row,0, no, body_column)
            sheet.write(row,1, rec.name, body_column)
            sheet.write(row,2, rec.serial_no, body_column)
            sheet.write(row,3, rec.brand, body_column)
            sheet.write(row,4, rec.state, body_column)
            sheet.write(row,5, last_date, year_format)
            sheet.write(row,6, rec.current_hour, body_column)
            sheet.write(row,7, rec.next_treshold, body_column)
            sheet.write(row,8, rec.cummulative_hour, body_column)
            sheet.write(row,9, rec.unit, body_column)
            sheet.write(row,10, monthly, year_format)
            sheet.write(row,11, rec.difference, body_column)

            row += 1
            no += 1

        sheet.write(row,0, '', footer_format)
        sheet.write(row,1, '', footer_format)
        sheet.write(row,2, '', footer_format)
        sheet.write(row,3, '', footer_format)
        sheet.write(row,4, '', footer_format)
        sheet.write(row,5, '', footer_format)
        sheet.write(row,6, '', footer_format)
        sheet.write(row,7, '', footer_format)
        sheet.write(row,8, '', footer_format)
        sheet.write(row,9, '', footer_format)
        sheet.write(row,10, '', footer_format)
        sheet.write(row,11, '', footer_format)


        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

        return response
    
class AllControllerOdoExcel(http.Controller):
    @http.route(['/asset_report/forecast_odo_excel_report'], type='http', auth="user", csrf=False)
    def test_control_excel_odo_all(self):
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition('Forecast Odo Reports' + '.xlsx'))
                    ]
                )

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        header_format = workbook.add_format({'font_name': 'Arial','bold': True, 'font_size': 15,'valign': 'vcenter', 'align': 'center'})
        year_format_15 = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'font_size': 13})
        header_column = workbook.add_format({'font_name': 'Arial', 'bold': True , 'align': 'center', 'valign': 'vcenter', 'font_size': 10, 'text_wrap': True,
                                             'left': 1, 'right' : 1, 'top' : 1, 'fg_color' : '#F2F2F2'})
        body_column = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter', 'font_size': 10,
                                           'left': 1, 'right' : 1, 'top' : 1})
        year_format = workbook.add_format({'font_name': 'Arial', 'align': 'center', 'valign': 'vcenter','font_size': 10,
                                           'left': 1, 'right' : 1, 'top' : 1})
        footer_format = workbook.add_format({'top' : 1})

        sheet = workbook.add_worksheet('timesheet')

        sheet.set_column('A:L', 15)
        sheet.set_row(7, 50)

        sheet.merge_range('A' + str(3) + ':L' + str(3), 'FORECAST ODOMETER MAINTENANCE REPORT', header_format)
        

        tanggal_hari_ini = datetime.now().date()
        if tanggal_hari_ini.month == 1:
            bulan = 'Januari'
        if tanggal_hari_ini.month == 2:
            bulan = 'Februari'
        if tanggal_hari_ini.month == 3:
            bulan = 'Maret'
        if tanggal_hari_ini.month == 4:
            bulan = 'April'
        if tanggal_hari_ini.month == 5:
            bulan = 'Mei'
        if tanggal_hari_ini.month == 6:
            bulan = 'Juni'
        if tanggal_hari_ini.month == 7:
            bulan = 'Juli'
        if tanggal_hari_ini.month == 8:
            bulan = 'Agustus'
        if tanggal_hari_ini.month == 9:
            bulan = 'September'
        if tanggal_hari_ini.month == 10:
            bulan = 'Oktober'
        if tanggal_hari_ini.month == 11:
            bulan = 'November'
        if tanggal_hari_ini.month == 12:
            bulan = 'Desember'
        tanggal_format = tanggal_hari_ini.strftime(f'%d {bulan} %Y')
        sheet.write(5, 5, tanggal_format, year_format_15)

        sheet.write(7,0, 'No', header_column)
        sheet.write(7,1, 'Equipment Name', header_column)
        sheet.write(7,2, 'Serial Number', header_column)
        sheet.write(7,3, 'Brand', header_column)
        sheet.write(7,4, 'Status', header_column)
        sheet.write(7,5, 'Last Date', header_column)
        sheet.write(7,6, 'Current Odometer ( Km )', header_column)
        sheet.write(7,7, 'Odometer Threshold (Km)', header_column)
        sheet.write(7,8, 'Cumulative Odometer (Km)', header_column)
        sheet.write(7,9, 'Odometer Type', header_column)
        sheet.write(7,10, 'End Date', header_column)
        sheet.write(7,11, 'Diff', header_column)
        
        row = 8
        no = 1

        forecast_hour_meter = request.env['forecast.odo.meter.maintenance'].search([])

        for rec in forecast_hour_meter:
            last_date = rec.last_date.strftime(f'%d/%m/%Y')
            monthly = rec.monthly.strftime(f'%d/%m/%Y')
            sheet.write(row,0, no, body_column)
            sheet.write(row,1, rec.name, body_column)
            sheet.write(row,2, rec.serial_no, body_column)
            sheet.write(row,3, rec.brand, body_column)
            sheet.write(row,4, rec.state, body_column)
            sheet.write(row,5, last_date, year_format)
            sheet.write(row,6, rec.current_odo, body_column)
            sheet.write(row,7, rec.next_treshold, body_column)
            sheet.write(row,8, rec.cummulative_odo, body_column)
            sheet.write(row,9, rec.unit, body_column)
            sheet.write(row,10, monthly, year_format)
            sheet.write(row,11, rec.difference, body_column)

            row += 1
            no += 1

        sheet.write(row,0, '', footer_format)
        sheet.write(row,1, '', footer_format)
        sheet.write(row,2, '', footer_format)
        sheet.write(row,3, '', footer_format)
        sheet.write(row,4, '', footer_format)
        sheet.write(row,5, '', footer_format)
        sheet.write(row,6, '', footer_format)
        sheet.write(row,7, '', footer_format)
        sheet.write(row,8, '', footer_format)
        sheet.write(row,9, '', footer_format)
        sheet.write(row,10, '', footer_format)
        sheet.write(row,11, '', footer_format)


        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

        return response