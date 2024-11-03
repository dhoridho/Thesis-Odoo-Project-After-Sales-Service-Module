from datetime import datetime
from email import header

from requests import head
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter


class SaleOrderReportController(http.Controller):
    @http.route(
        ['/equip3_construction_sales_operation/sale_order_excel_report/<model("construction.sale.order.report.wizard"):data>', ],
        type='http', auth='user', csrf=False)
    def get_so_cons_report(self, data=None, **args):
        response = request.make_response(
            None,
            headers=[
                ('Content-Type', 'application/vnd.ms-excel'),
                ('Content-Disposition', content_disposition(self.get_filename(data)))
            ]
        )
        def get_field(obj, field_chains):
            def get_construction_address(sale_order_id):
                if sale_order_id.street and sale_order_id.city and sale_order_id.state_id.name and sale_order_id.country_id.name and sale_order_id.zip_code:
                    if sale_order_id.street_2:
                        address_street = sale_order_id.street + ", " + sale_order_id.street_2 + ", " + sale_order_id.city + ", "
                    else:
                        address_street = sale_order_id.street + ", " + sale_order_id.city + ", "
                    address_country = sale_order_id.state_id.name + ", " + str(
                        sale_order_id.country_id.name) + ", " + sale_order_id.zip_code
                    return address_street, address_country
                else:
                    return "", ""
            try:
                result = eval(field_chains)
            except Exception as e:
                result = ''
            finally:
                return result

        sale = data.sale_order_id

        # Create Workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        sheet = workbook.add_worksheet(self.get_title(data))
        sheet.set_portrait()
        sheet.set_paper(9)

        sheet.set_margins(0.31, 0.31, 0.59, 0.35)
        sheet.set_column('A:A', 5)
        sheet.set_column('C:C', 40)

        right_header_col = 5

        if sale.contract_category != 'var':
            sheet.set_column('H:H', 12)
            sheet.set_column('I:I', 15)
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
            right_header_col = 9

        # Style Configuration
        text_style_1 = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'left','bg_color': 'white'})
        title_text_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'bold': True, 'align': 'center', 'valign': 'vcenter','bg_color': '#C0C0C0' })
        header_style = workbook.add_format({'font_name': 'Arial', 'font_size': 9, 'bold': True, 'border': 1, 'align': 'center','bg_color': '#C0C0C0'})
        number_text_style_1 = workbook.add_format({'font_name': 'Arial', 'font_size': 9 ,'bold': True, 'border': 1, 'align': 'center'})
        number_text_style_2 = workbook.add_format({'font_name': 'Arial', 'font_size': 8 ,'bold': False, 'border': 1, 'align': 'center'})
        
        table_content_text_style_1 = workbook.add_format({'font_name': 'Arial', 'font_size': 9 ,'bold': True, 'border': 1, 'align': 'left'})
        table_content_text_style_2 = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'left', 'border': 1})
        table_content_text_style_3 = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'center', 'border': 1})
        table_content_text_style_4 = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': True, 'align': 'center', 'border': 1})

        
        # Currency Formatting
        currency = data.sale_order_id.currency_id.name
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

        qty_change_format = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'center', 'border': 1, 'bg_color': '#FFE699'})

        currency_format_dict['bold'] = False
        currency_format_dict['bg_color'] = '#FFE699'
        currency_change_format = workbook.add_format(currency_format_dict)

        item_add_format = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'left', 'border': 1, 'bg_color': '#A9D08E'})
        item_del_format = workbook.add_format({'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'left', 'border': 1, 'bg_color': '#FF5050'})
        
        border_format = workbook.add_format({
            'border': 1
        })
        # Title
        if sale.contract_category == 'var':
            sheet.merge_range('A1:K2', self.get_title(data), title_text_style)
        else:
            sheet.merge_range('A1:I2', self.get_title(data), title_text_style)

        # Upper Left
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
            },
            'Location' : {
                'field' : 'get_construction_address(obj)[0]',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            ' ' : {
                'field' : 'get_construction_address(obj)[1]',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Main Contract' : {
                'field' : 'obj.main_contract_ref.name',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Cost Sheet' : {
                'field' : 'obj.cost_sheet_ref.name',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
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
            'Down Payment' : {
                'field' : 'str(obj.down_payment) if obj.dp_method == "fix" else str(obj.down_payment) + "%"',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Retention 1' : {
                'field' : 'str(obj.retention1) + "%" if obj.retention1 else "0"',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Retention 1 Term' : {
                'field' : 'obj.retention_term_1.name',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Retention 2' : {
                'field' : 'str(obj.retention2) + "%" if obj.retention2 else "0"',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Retention 1 Term' : {
                'field' : 'obj.retention_term_2.name',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Taxes' : {
                'field' : '", ".join([ x.name + " " + str(x.amount) + "%" fox x in obj.tax_id])',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
            'Payment Term' : {
                'field' : 'obj.payment_term_id.name',
                'span' : (0, 1),
                'style' : [text_style_1],
            },
        }

        if sale.contract_category != 'var':
            del header['Main Contract']
            del header['Cost Sheet']
        
        # Upper Left
        cur_row = 2
        cur_col = 0
        for name, values in header.items():
            data_field = get_field(sale, values['field'])
            data_field = data_field if data_field else ''
            sheet.merge_range(cur_row, cur_col, cur_row + values['span'][0], cur_col + values['span'][1], name, values['style'][0])
            cur_col += values['span'][1] + 1
            sheet.write(cur_row, cur_col, ': ' + str(data_field), values['style'][0])
            cur_row += 1
            cur_col = 0
        
        # Upper Right
        cur_row = 2
        cur_col = right_header_col
        for name, values in header2.items():
            data_field = get_field(sale, values['field'])
            data_field = data_field if data_field else ''
            sheet.merge_range(cur_row, cur_col, cur_row + values['span'][0], cur_col + values['span'][1], name, values['style'][0])
            cur_col += values['span'][1] + 1
            sheet.merge_range(cur_row, cur_col, cur_row + values['span'][0], cur_col + values['span'][1], ': ' + str(data_field), values['style'][0])
            cur_row += 1
            cur_col = right_header_col
            
        # Table Content
        char_inc = 'A'
        row_num = 13
        i_char = 0
        total = 0

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
        
        if sale.contract_category != 'var':
            del table_headers['Quantity Before']
            del table_headers['Contractors Before']
            del table_headers['Time Before']
            del table_headers['Unit Price Before']
            table_headers['Quantity']['name']    = 'Quantity'
            table_headers['Contractors']['name'] = 'Contractors'
            table_headers['Time']['name']        = 'Time'
            table_headers['Unit Price']['name']  = 'Unit Price'

        cur_row = 13

        row_start = cur_row
        cur_col = 0
        for name, values in table_headers.items():
            if values['span'] == (0, 0):
                sheet.write(cur_row, cur_col, values['name'], header_style)
            else:
                sheet.merge_range(cur_row, cur_col, cur_row + values['span'][0], cur_col + values['span'][1], values['name'], header_style)
            cur_col += values['span'][1] + 1
        
        scope_sect_prod_dict = data.sale_order_id.get_report_data(data.print_level_option)
        report_data_array = data.sale_order_id.report_data2array(scope_sect_prod_dict)

        cur_row += 1
        cur_col = 0

        for item in report_data_array:
            cur_col = 0
            for field, values in table_headers.items():
                data_field = get_field(item, values['field'])
                style_format = values['style'][item['style']]
                if sale.contract_category == 'var' and item['style'] == 2:
                    if field == 'Quantity':
                        if item['field'] != 'labour_line_ids':
                            style_format = qty_change_format if item['qty'] != item['qty_before'] else style_format
                    
                    if field == 'Contractors':
                        if item['field'] == 'labour_line_ids':
                            style_format = qty_change_format if item['contractor'] != item['contractor_before'] else style_format
                    
                    if field == 'Time':
                        if item['field'] == 'labour_line_ids':
                            style_format = qty_change_format if item['time'] != item['time_before'] else style_format

                    if field == 'Unit Price':
                        style_format = currency_change_format if item['unit_price'] != item['unit_price_before'] else style_format

                    if field == 'Job Description':
                        if item['field'] != 'labour_line_ids':
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

        # # Tax Amount Row
        sheet.write(cur_row, 0, "", number_text_style_2)
        sheet.write(cur_row, 1, "Tax Amount", table_content_text_style_1)
        for col in range(2, cur_col-1):
                sheet.write_blank(cur_row, col, None, border_format)
        sheet.write(cur_row, cur_col - 1, data.sale_order_id.amount_tax, currency_format_bold)  

        cur_row += 1

        # Total BOQ Row
        sheet.write(cur_row, 0, "", number_text_style_2)
        sheet.write(cur_row, 1, "Total", table_content_text_style_1)
        for col in range(2, cur_col-1):
                sheet.write_blank(cur_row, col, None, border_format)
        sheet.write(cur_row, cur_col - 1, data.sale_order_id.amount_total, currency_format_bold)  

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
        return response

    def get_title(self, data):
        if data.sale_order_id.state == "sale":
            return "Sale Order"
        else:
            return "Quotation"

    def get_filename(self, data):
        current_datetime = datetime.now()
        current_datetime_string = current_datetime.strftime("%d-%m-%Y")

        filename = self.get_title(
            data) + "(" + data.sale_order_id.name + ")" + " - " + data.sale_order_id.project_id.name + " - " + current_datetime_string + '.xlsx'
        return filename

    def get_construction_address(self, data):
        if data.sale_order_id.street and data.sale_order_id.city and data.sale_order_id.state_id.name and data.sale_order_id.country_id.name and data.sale_order_id.zip_code:
            if data.sale_order_id.street_2:
                address_street = data.sale_order_id.street + ", " + data.sale_order_id.street_2 + ", " + data.sale_order_id.city + ", "
            else:
                address_street = data.sale_order_id.street + ", " + data.sale_order_id.city + ", "
            address_country = data.sale_order_id.state_id.name + ", " + str(
                data.sale_order_id.country_id.name) + ", " + data.sale_order_id.zip_code
            return address_street, address_country
        else:
            return "", ""

    def get_selection_value(self, selection):
        if selection == 'main':
            return "Main Contract"
        else:
            return "Variation Order"

    def get_tax_value(self, data):
        temp_tax = list()
        for tax in data.sale_order_id.tax_id:
            temp_str = tax.name + " " + str(tax.amount) + "%"
            temp_tax.append(temp_str)

        return ", ".join(temp_tax)

    def check_scope_labour_line(self, data):
        if data.sale_order_id.labour_line_ids:
            for labour in data.sale_order_id.labour_line_ids:
                if not labour.project_scope.name:
                    return False
        return True

    def check_scope_internal_asset(self, data):
        if data.sale_order_id.internal_asset_line_ids:
            for internal in data.sale_order_id.internal_asset_line_ids:
                if not internal.project_scope.name:
                    return False
        return True

    def check_scope_equipment_lease(self, data):
        if data.sale_order_id.equipment_line_ids:
            for equipment in data.sale_order_id.equipment_line_ids:
                if not equipment.project_scope.name:
                    return False
        return True
