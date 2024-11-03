from datetime import datetime
from email import header

from requests import head
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter

from odoo.addons.equip3_construction_sales_operation.controllers.job_estimate_excel_report import JobEstimateReportController  # Import the original controller


class JobEstimateReportControllerInherit(JobEstimateReportController):

    # override
    def sheet_format(self, sheet, data):
        boq = data.job_estimate_id
        sheet.set_portrait()
        sheet.set_paper(9)

        sheet.set_margins(0.31, 0.31, 0.59, 0.35)
        sheet.set_column('A:A', 5)
        sheet.set_column('C:C', 40)

        if boq.contract_category != 'var':
            sheet.set_column('I:I', 12)
            sheet.set_column('J:J', 15)
        else:
            sheet.set_column('D:D', 12)
            sheet.set_column('E:E', 12)
            sheet.set_column('F:F', 14)
            sheet.set_column('G:G', 14)
            sheet.set_column('H:H', 12)
            sheet.set_column('I:I', 12)
            sheet.set_column('K:K', 12)
            sheet.set_column('L:L', 12)
            sheet.set_column('M:M', 15)
        
        return sheet    
    
    # override
    def write_headers(self, sheet, workbook, data, cur_row, cur_col):
        boq = data.job_estimate_id

        title_text_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'bold': True, 'align': 'center', 'valign': 'vcenter','bg_color': '#C0C0C0' })

        # Title
        if boq.contract_category == 'var':
            sheet.merge_range('A1:M2', "BOQ", title_text_style)
        else:
            sheet.merge_range('A1:J2', "BOQ", title_text_style)

        # content
        header, header2 = self.get_header(workbook, boq)
        right_header_col = 6

        if boq.contract_category == 'var':
            right_header_col = 9

        # Upper Left
        cur_row = 2
        cur_col = 0
        for name, values in header.items():
            data_field = self.get_field(boq, values['field'])
            data_field = data_field if data_field else ''
            sheet.merge_range(cur_row, cur_col, cur_row + values['span'][0], cur_col + values['span'][1], name, values['style'][0])
            cur_col += values['span'][1] + 1
            sheet.write(cur_row, cur_col, ': ' + data_field, values['style'][0])
            cur_row += 1
            cur_col = 0
        
        # Upper Right
        cur_row = 2
        cur_col = right_header_col
        for name, values in header2.items():
            data_field = self.get_field(boq, values['field'])
            data_field = data_field if data_field else ''
            sheet.merge_range(cur_row, cur_col, cur_row + values['span'][0], cur_col + values['span'][1], name, values['style'][0])
            cur_col += values['span'][1] + 1
            sheet.merge_range(cur_row, cur_col, cur_row + values['span'][0], cur_col + values['span'][1], ': ' + data_field, values['style'][0])
            cur_row += 1
            cur_col = right_header_col
        
        return cur_row, cur_col

    # override
    def write_rows(self, sheet, workbook, data, cur_row, cur_col, report_data_array, table_headers):
        boq = data.job_estimate_id

        qty_change_format = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'center', 'border': 1, 'bg_color': '#FFE699'})
        item_add_format = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'left', 'border': 1, 'bg_color': '#A9D08E'})
        item_del_format = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'left', 'border': 1, 'bg_color': '#FF5050'})
        currency = boq.currency_id.name
        currency_dict = {
            'IDR' : '"Rp" #,##0.00',
            'USD' : '[$$-409] #,##0.00',
            'AUD' : '[$AUD] #.##0',
            'JPY' : '[$JPY] #.##0',
            'SGD' : '[$SGD] #.##0',
            'EUR' : '[$EUR] #.##0',
        }
        currency_format_dict = {'font_name': 'Arial', 'font_size': 8, 'align': 'right', 'border': 1, 'bold': False}
        if currency_dict.get(currency, False):
            currency_format_dict['num_format'] = currency_dict[currency]
        else:
            currency_format_dict['num_format'] = '[$$-409] #,##0.00'
        currency_change_format = workbook.add_format(currency_format_dict)

        cur_row += 1
        cur_col = 0

        for item in report_data_array:
            cur_col = 0
            for field, values in table_headers.items():
                data_field = self.get_field(item, values['field'])
                style_format = values['style'][item['style']]
                
                if boq.contract_category == 'var' and item['style'] == 2:
                    if field == 'Quantity':
                        if item['field'] != 'labour_estimation_ids':
                            style_format = qty_change_format if item['qty'] != item['qty_before'] else style_format
                    
                    if field == 'Contractors':
                        if item['field'] == 'labour_estimation_ids':
                            style_format = qty_change_format if item['contractor'] != item['contractor_before'] else style_format
                    
                    if field == 'Time':
                        if item['field'] == 'labour_estimation_ids':
                            style_format = qty_change_format if item['time'] != item['time_before'] else style_format

                    if field == 'Unit Price':
                        style_format = currency_change_format if item['unit_price'] != item['unit_price_before'] else style_format

                    if field == 'Job Description':
                        if item['field'] != 'labour_estimation_ids':
                            if item['qty'] == 0 or item['qty_before'] == 0: 
                                style_format = item_add_format if item['qty'] - item['qty_before'] > 0 else item_del_format
                        else:
                            if item['contractor'] == 0 or item['contractor_before'] == 0: 
                                style_format = item_add_format if item['contractor'] - item['contractor_before'] > 0 else item_del_format

                if values['span'] == (0, 0):
                    sheet.write(cur_row, cur_col, data_field, style_format)
                else:
                    sheet.merge_range(cur_row, cur_col, cur_row + values['span'][0], cur_col + values['span'][1], data_field, style_format)
                cur_col += values['span'][1] + 1
            cur_row += 1
        
        return cur_row, cur_col

    # override
    def get_table_headers(self, workbook, data):
        boq = data.job_estimate_id
        number_text_style_1 = workbook.add_format({'font_name': 'Arial', 'font_size': 9 ,'bold': True, 'border': 1, 'align': 'center'})
        number_text_style_2 = workbook.add_format({'font_name': 'Arial', 'font_size': 8 ,'bold': False, 'border': 1, 'align': 'center'})
        
        table_content_text_style_1 = workbook.add_format({'font_name': 'Arial', 'font_size': 9 ,'bold': True, 'border': 1, 'align': 'left'})
        table_content_text_style_2 = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'left', 'border': 1})
        table_content_text_style_3 = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'center', 'border': 1})
        table_content_text_style_4 = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': True, 'align': 'center', 'border': 1})

        # Currency Formatting
        currency = boq.currency_id.name
        currency_dict = {
            'IDR' : '"Rp" #,##0.00',
            'USD' : '[$$-409] #,##0.00',
            'AUD' : '[$AUD] #.##0',
            'JPY' : '[$JPY] #.##0',
            'SGD' : '[$SGD] #.##0',
            'EUR' : '[$EUR] #.##0',
        }
        currency_format_dict = {'font_name': 'Arial', 'font_size': 8, 'align': 'right', 'border': 1, 'bold': False}
        if currency_dict.get(currency, False):
            currency_format_dict['num_format'] = currency_dict[currency]
        else:
            currency_format_dict['num_format'] = '[$$-409] #,##0.00'

        currency_format = workbook.add_format(currency_format_dict)
        currency_format_dict['bold'] = True
        currency_format_bold = workbook.add_format(currency_format_dict)
        currency_format_dict['bg_color'] = '#C0C0C0'
        currency_format_bold_header = workbook.add_format(currency_format_dict)

        table_headers = {
            'No.' : {
                'name' : 'No',
                'field' : 'obj["no"]',
                'span' : (0, 0),
                'style' : [number_text_style_1, number_text_style_1, number_text_style_2, number_text_style_2],
            },
            'Job Description' : {
                'name' : 'Job Description',
                'field' : 'obj["name"]',
                'span' : (0, 1),
                'style' : [table_content_text_style_1, table_content_text_style_1, table_content_text_style_2, table_content_text_style_4],
            },
            'Quantity Before' : {
                'name' : 'Quantity Before',
                'field' : 'obj["qty_before"]',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'Quantity' : {
                'name' : 'Current Quantity',
                'field' : 'obj["qty"]',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'Contractors Before' : {
                'name' : 'Contractors Before',
                'field' : 'obj["contractor_before"]',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'Contractors' : {
                'name' : 'Current Contractors',
                'field' : 'obj["contractor"]',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'Time Before' : {
                'name' : 'Time Before',
                'field' : 'obj["time_before"]',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'Time' : {
                'name' : 'Current Time',
                'field' : 'obj["time"]',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'Coeff' : {
                'name' : 'Coeff',
                'field' : 'obj["coefficient"]',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'UOM' : {
                'name' : 'UOM',
                'field' : 'obj["uom"] or " "',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'Unit Price Before' : {
                'name' : 'Unit Price Before',
                'field' : 'obj["unit_price_before"]',
                'span' : (0, 0),
                'style' : [currency_format, currency_format_bold, currency_format, currency_format_bold],
            },
            'Unit Price' : {
                'name' : 'Current Unit Price',
                'field' : 'obj["unit_price"]',
                'span' : (0, 0),
                'style' : [currency_format, currency_format_bold, currency_format, currency_format_bold],
            },
            'Subtotal' : {
                'name' : 'Subtotal',
                'field' : 'obj["total"]',
                'span' : (0, 0),
                'style' : [currency_format, currency_format_bold, currency_format, currency_format_bold],
            }
        }
        
        if boq.contract_category != 'var':
            del table_headers['Quantity Before']
            del table_headers['Contractors Before']
            del table_headers['Time Before']
            del table_headers['Unit Price Before']
            table_headers['Quantity']['name']    = 'Quantity'
            table_headers['Contractors']['name'] = 'Contractors'
            table_headers['Time']['name']        = 'Time'
            table_headers['Unit Price']['name']  = 'Unit Price'
        else:
            del table_headers['Coeff']
        
        if data.print_level_option == '2_level':
            del table_headers['Contractors']
            del table_headers['Time']
            del table_headers['Unit Price']
            if table_headers.get('Coeff', False):
                del table_headers['Coeff']

        return table_headers

    # override
    def get_header(self, workbook, boq):
        text_style_1 = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'left','bg_color': 'white'})
        # content
        header = {
            'Project' : {
                'field' : 'obj.project_id.name',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Customer': {
                'field' : 'obj.partner_id.name',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Planned Start Date' : {
                'field' : 'obj.start_date.strftime("%m/%d/%Y")',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Planned End Date' : {
                'field' : 'obj.end_date.strftime("%m/%d/%Y")',
                'span' : (0, 1),
                'style' : [text_style_1],
            }
        }

        header2 = {
            'Company' : {
                'field' : 'obj.company_id.name',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Category': {
                'field' : '{"main":"Main Contract", "var":"Variation Order"}[obj.contract_category]',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Main Contract' : {
                'field' : 'obj.main_contract_ref.name',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Cost Sheet' : {
                'field' : 'obj.project_id.cost_sheet_ids.filtered(lambda x: x.state in ["in_progress", "done"]).name',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Construction Location' : {
                'field' : 'obj.project_id.street',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            ' ' : {
                'field' : 'obj.project_id.street_2',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            '  ' : {
                'field' : 'obj.project_id.city + " " + obj.project_id.state_id.name + " "  + obj.project_id.zip_code',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            '   ' : {
                'field' : 'obj.project_id.country_id.name',
                'span' : (0, 1),
                'style' : [text_style_1],
            }
        }

        if boq.contract_category != 'var':
            del header2['Main Contract']
            del header2['Cost Sheet']

        return header, header2
