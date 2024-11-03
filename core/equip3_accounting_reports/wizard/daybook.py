import time
from datetime import date
from datetime import timedelta, datetime
from odoo import fields, models, api, _
import io
import json
from odoo.exceptions import AccessError, UserError, AccessDenied

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class AgeingView(models.TransientModel):
    _inherit = 'account.day.book'

    def get_dynamic_xlsx_report(self, data, response, report_data, dfr_data):
        report_data_main = json.loads(report_data)
        output = io.BytesIO()
        filters = json.loads(data)
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'bold': True})
        sub_heading = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black'})
        txt = workbook.add_format({'border': 1})
        txt_num = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        txt_l = workbook.add_format({'border': 1, 'bold': True})
        txt_l_num = workbook.add_format({'border': 1, 'bold': True, 'num_format': '#,##0.00'})
        sheet.merge_range('A2:D3', filters.get('company_name') + ':' + ' Day Book', head)
        date_head = workbook.add_format({'bold': True})
        date_style = workbook.add_format({})
        if filters.get('date_from'):
            sheet.merge_range('A4:B4', 'From: ' + filters.get('date_from'), date_head)
        if filters.get('date_to'):
            sheet.merge_range('C4:D4', 'To: ' + filters.get('date_to'), date_head)
        sheet.write('A5', 'Journals: ' + ', '.join([lt or '' for lt in filters['journals']]), date_head)

        sheet.merge_range('E4:F4', 'Target Moves: ' + filters.get('target_move'), date_head)
        sheet.merge_range('B5:D5', 'Account Type: ' + ', '.join([lt or '' for lt in filters['accounts']]), date_head)

        sheet.merge_range('A7:E7', 'Date', sub_heading)
        sheet.write('F7', 'Debit', sub_heading)
        sheet.write('G7', 'Credit', sub_heading)
        sheet.write('H7', 'Balance', sub_heading)

        row = 6
        col = 0

        
        sheet.set_column('A:A', 15, '')
        sheet.set_column('B:B', 15, '')
        sheet.set_column('C:C', 20, '')
        sheet.set_column('D:D', 20, '')
        sheet.set_column('E:E', 50, '')
        sheet.set_column('F:F', 20, '')
        sheet.set_column('G:G', 20, '')
        sheet.set_column('H:H', 20, '')
        sheet.set_column('I:I', 20, '')

        for rec_data in report_data_main:
            one_lst = []
            two_lst = []
            row += 1
            sheet.merge_range(row, col, row, col + 4, rec_data['date'], txt_l)
            sheet.write(row, col + 5, rec_data['debit'], txt_l_num)
            sheet.write(row, col + 6, rec_data['credit'], txt_l_num)
            sheet.write(row, col + 7, rec_data['balance'], txt_l_num)
            for line_data in rec_data['child_lines']:
                row += 1
                sheet.write(row, col, line_data.get('ldate'), txt)
                sheet.write(row, col + 1, line_data.get('lcode'), txt)
                sheet.write(row, col + 2, line_data.get('partner_name'),
                            txt)
                sheet.write(row, col + 3, line_data.get('move_name'), txt)
                sheet.write(row, col + 4, line_data.get('lname'), txt)
                sheet.write(row, col + 5, line_data.get('debit'), txt_num)
                sheet.write(row, col + 6, line_data.get('credit'), txt_num)
                sheet.write(row, col + 7, line_data.get('balance'), txt_num)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()