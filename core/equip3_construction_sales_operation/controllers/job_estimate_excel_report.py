from datetime import datetime
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter


class JobEstimateReportController(http.Controller):

    def get_field(self, obj, field_chains):
        try:
            result = eval(field_chains)
        except Exception as e:
            result = ''
        finally:
            return result
            
    @http.route(['/equip3_construction_sales_operation/job_estimate_excel_report/<model("job.estimate.report"):data>',],type='http', auth='user', csrf=False)
    def get_job_estimate_report(self, data=None, **args):
        response = request.make_response(
                    None,
                    headers=[
                        ('Content-Type', 'application/vnd.ms-excel'),
                        ('Content-Disposition', content_disposition(self.get_file_name(data))),
                    ]
        )

        # Create Workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("BOQ")
        sheet = self.sheet_format(sheet, data)

        cur_row = 0
        cur_col = 0
        cur_row, cur_col = self.write_headers(sheet, workbook, data, cur_row, cur_col)
        cur_row, cur_col = self.write_body(sheet, workbook, data, cur_row, cur_col)
        
        # List of all error types
        error_types = [
            'calculation',
            'number_stored_as_text',
            'two_digit_text_year',
            'unlocked_formula',
            'empty_cell_reference',
            'data_validation',
            'row_column_ends_with_space',
            'inconsistent_formula',
            'formula_differs_from_other_formula_in_region',
            'locked_formula',
            'misleading_number',
            'misleading_text',
            'overlapping',
        ]

        # Set the 'ignore_errors' option to ignore all errors in the entire worksheet.
        for error_type in error_types:
            sheet.ignore_errors({error_type: 'A1:XFD1048576'})  # Range for the entire sheet

        # sheet.autofit()
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
        return response

    def sheet_format(self, sheet, data):
        boq = data.job_estimate_id
        sheet.set_portrait()
        sheet.set_paper(9)

        sheet.set_margins(0.31, 0.31, 0.59, 0.35)
        sheet.set_column('A:A', 5)
        sheet.set_column('C:C', 40)

        sheet.set_column('H:H', 12)
        sheet.set_column('I:I', 15)

        return sheet

    def write_headers(self, sheet, workbook, data, cur_row, cur_col):
        title_text_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'bold': True, 'align': 'center', 'valign': 'vcenter','bg_color': '#C0C0C0' })
        sheet.merge_range('A1:I2', "BOQ", title_text_style)
        
        boq = data.job_estimate_id
        
        # content
        header, header2 = self.get_header(workbook, boq)
        right_header_col = 5

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

    def write_rows(self, sheet, workbook, data, cur_row, cur_col, report_data_array, table_headers):
        cur_row += 1
        cur_col = 0

        for item in report_data_array:
            cur_col = 0
            for field, values in table_headers.items():
                data_field = self.get_field(item, values['field'])
                style_format = values['style'][item['style']]

                if values['span'] == (0, 0):
                    sheet.write(cur_row, cur_col, data_field, style_format)
                else:
                    sheet.merge_range(cur_row, cur_col, cur_row + values['span'][0], cur_col + values['span'][1], data_field, style_format)
                cur_col += values['span'][1] + 1
            cur_row += 1
        
        return cur_row, cur_col

    def write_body(self, sheet, workbook, data, cur_row, cur_col):
        boq = data.job_estimate_id
        header_style = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'bold': True, 'border': 1, 'align': 'center','bg_color': '#C0C0C0'})
        number_text_style_1 = workbook.add_format({'font_name': 'Arial', 'font_size': 9 ,'bold': True, 'border': 1, 'align': 'center'})
        number_text_style_2 = workbook.add_format({'font_name': 'Arial', 'font_size': 8 ,'bold': False, 'border': 1, 'align': 'center'})
        table_content_text_style_1 = workbook.add_format({'font_name': 'Arial', 'font_size': 9 ,'bold': True, 'border': 1, 'align': 'left'})
        border_format = workbook.add_format({'border': 1})

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

        table_headers = self.get_table_headers(workbook, data)

        cur_row += 1
        row_start = cur_row
        cur_col = 0
        for name, values in table_headers.items():
            if values['span'] == (0, 0):
                sheet.write(cur_row, cur_col, values['name'], header_style)
            else:
                sheet.merge_range(cur_row, cur_col, cur_row + values['span'][0], cur_col + values['span'][1], values['name'], header_style)
            cur_col += values['span'][1] + 1
        
        scope_sect_prod_dict = data.job_estimate_id.get_report_data(data.print_level_option)
        report_data_array = data.job_estimate_id.report_data2array(scope_sect_prod_dict)

        cur_row, cur_col = self.write_rows(sheet, workbook, data, cur_row, cur_col, report_data_array, table_headers)
        
        # Total BOQ Row
        sheet.write(cur_row, 0, "", number_text_style_2)
        sheet.write(cur_row, 1, "Total BOQ", table_content_text_style_1)
        for col in range(2, cur_col-1):
                sheet.write_blank(cur_row, col, None, border_format)
        sheet.write(cur_row, cur_col - 1, data.job_estimate_id.total_job_estimate, currency_format_bold)  
        
        return cur_row, cur_col

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
            'Quantity' : {
                'name' : 'Quantity',
                'field' : 'obj["qty"]',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'Contractors' : {
                'name' : 'Contractors',
                'field' : 'obj["contractor"]',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'Time' : {
                'name' : 'Time',
                'field' : 'obj["time"]',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'UOM' : {
                'name' : 'UOM',
                'field' : 'obj["uom"] or " "',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'Coeff' : {
                'name' : 'Coeff',
                'field' : 'obj["coefficient"]',
                'span' : (0, 0),
                'style' : [table_content_text_style_1, table_content_text_style_4, table_content_text_style_3, number_text_style_2],
            },
            'Unit Price' : {
                'name' : 'Unit Price',
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

        if data.print_level_option == '2_level':
            del table_headers['Contractors']
            del table_headers['Time']
            del table_headers['Coeff']
            del table_headers['Unit Price']

        return table_headers

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

        return header, header2

    def get_file_name(self, data):
        current_datetime = datetime.now()
        current_datetime_string = current_datetime.strftime("%d-%m-%Y")

        filename = "BOQ - " + data.job_estimate_id.project_id.name + " - " + current_datetime_string + ".xlsx"
        return filename
    