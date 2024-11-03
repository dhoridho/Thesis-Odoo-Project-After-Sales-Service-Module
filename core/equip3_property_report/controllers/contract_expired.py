from odoo import api, fields, models, tools, _
import datetime
import time
import json
import io
import xlsxwriter
from odoo import http
from datetime import datetime,date
from odoo.http import content_disposition, request
from odoo.tools import date_utils
from odoo.exceptions import ValidationError

class ExpiredContractWizardController(http.Controller):
    @http.route(['/expired-contract/expired_wizard'], type='http', auth="user", csrf=False)
    def get_contract_record(self,id,start,end):

        response = request.make_response(
                        None,
                        headers=[
                            ('Content-Type', 'application/vnd.ms-excel'),
                            ('Content-Disposition', content_disposition('Expired Contract' +  str(datetime.now().date()) + '.xlsx'))
                        ]
                    )
            
        output = io.BytesIO()   
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # style
        title_style = workbook.add_format({'font_name': 'Calibri', 'font_size': 33, 'bold': False, 'align' : 'center', 'valign': 'vcenter'})
        text_style = workbook.add_format({'font_name': 'Calibri','font_size': 11,'align': 'left', 'valign': 'vcenter'})
        text_style2 = workbook.add_format({'font_name': 'Calibri','font_size': 16,'align': 'center', 'valign': 'vcenter'})
        header_style = workbook.add_format({'font_name': 'Calibri','font_size': 16,'align': 'left', 'valign': 'vcenter'})
        header_style2 = workbook.add_format({'font_name': 'Calibri','font_size': 11,'align': 'center', 'valign': 'vcenter'})
        date_format1 = workbook.add_format({'font_name': 'Calibri', 'align': 'left', 'font_size': 11,'num_format': 'dd/mm/yy'})
        date_format2 = workbook.add_format({'font_name': 'Calibri', 'align': 'left', 'font_size': 11,'num_format': 'd mmm yyyy'})
        sub_total = workbook.add_format({'num_format': '#,##0.00', 'align': 'right', 'font_size': 11,'bold': True})


        now = datetime.now()
        date_time = now.strftime("%d %B %Y")

        start_date = datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.strptime(end, '%Y-%m-%d').date()

        wiz_id = request.env['contract.expired'].sudo().browse(int(id))

        
        sheet = workbook.add_worksheet('Expired Contract')

         # layout
        sheet.set_column(0, 0, 15)

        sheet.set_column(0, 6, 10)
        sheet.set_column(0, 7, 20)
        sheet.set_column(0, 8, 20)
        sheet.set_column(0, 9, 20)
        sheet.set_column(0, 10, 20)
        sheet.set_column(0, 11, 20)
        sheet.set_column(0, 12, 20)
        sheet.set_column(0, 13, 20)
        sheet.set_column(0, 14, 20)


        # table
        sheet.write(0, 0, date_time, date_format2)
        sheet.write(1, 6, 'Contract Expired Report', title_style)
        sheet.write(2, 6, f'Period : {start_date.strftime("%d %B %Y")} - {end_date.strftime("%d %B %Y")}', text_style2)


        sheet.write(6, 2, 'Code', header_style2)
        sheet.write(6, 3, 'Name', header_style2)
        sheet.write(6, 4, 'Start Date', header_style2)
        sheet.write(6, 5, 'Expired Date', header_style2)
        sheet.write(6, 6, 'Property Name', header_style2)
        sheet.write(6, 7, 'Property Transaction', header_style2)
        sheet.write(6, 8, 'Payment Type', header_style2)
        sheet.write(6, 9, 'Price', header_style2)
        sheet.write(6, 10, 'Deposite', header_style2)
        sheet.write(6, 11, 'Total Price', header_style2)



        agreement = request.env['agreement'].sudo().search([('expired_date','>=', start_date),('expired_date','<=', end_date),('property_id','!=',False)])
        if agreement:
            row, col = 8, 2
            for rec in agreement:
                if rec.property_book_for == 'rent':
                    property_type = 'Rent'
                elif rec.property_book_for == 'sale':
                    property_type = 'Sale'
                else:
                    proeprety_type = ''

                if rec.payment_type == 'daily':
                    payment_type = 'Daily'
                elif rec.payment_type == 'monthly':
                    payment_type = 'Monthly'
                elif rec.payment_type == 'yearly':
                    payment_type = 'Yearly'
                else:
                    payment_type = ''

                account_move = request.env['account.move'].sudo().search([('agreement_id','=',rec.id)])
                total_price = rec.expected_revenue * len(account_move)


                sheet.write(row, col, rec.code, text_style)
                sheet.write(row, col+1, rec.name, text_style)
                sheet.write(row, col+2, rec.start_date if rec.start_date else '', date_format1)
                sheet.write(row, col+3, rec.expired_date, date_format1)
                sheet.write(row, col+4, rec.property_id.name if rec.property_id else '', text_style)
                sheet.write(row, col+5, property_type if rec.property_book_for else '', text_style)
                sheet.write(row, col+6, payment_type, text_style)
                sheet.write(row, col+7, rec.expected_revenue, sub_total)
                sheet.write(row, col+8, rec.expected_revenue, sub_total)
                sheet.write(row, col+9, total_price, sub_total)

                row += 1

                

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

        return response
