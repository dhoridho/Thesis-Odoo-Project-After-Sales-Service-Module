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

        # Create Workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Style Configuration
        text_style_1 = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'left', 'bg_color': 'white'})
        title_text_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 12, 'bold': True, 'align': 'center', 'valign': 'vcenter',
             'bg_color': '#C0C0C0'})
        header_style = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 9, 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1,
             'align': 'center', 'bg_color': '#C0C0C0'})
        number_text_style_1 = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 9, 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1,
             'align': 'center'})
        number_text_style_2 = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1,
             'align': 'center'})
        table_content_text_style_1 = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 9, 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1,
             'align': 'left'})
        table_content_text_style_2 = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'left', 'left': 1, 'bottom': 1, 'right': 1,
             'top': 1})
        table_content_text_style_3 = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'center', 'left': 1, 'bottom': 1, 'right': 1,
             'top': 1})
        table_content_text_style_4 = workbook.add_format(
            {'font_name': 'Arial', 'font_size': 8, 'bold': True, 'align': 'center', 'left': 1, 'bottom': 1, 'right': 1,
             'top': 1})
        sheet = workbook.add_worksheet(self.get_title(data))
        sheet.set_portrait()
        sheet.set_paper(9)
        sheet.set_margins(0.31, 0.31, 0.59, 0.35)
        sheet.set_column('A:A', 5)
        sheet.set_column('C:C', 40)
        sheet.set_column('D:D', 10)
        sheet.set_column('E:E', 6)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 15)

        # Currency Formatting
        currency = data.sale_order_id.currency_id.name
        if currency == "IDR":
            currency_format = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '"Rp" #,##0.00'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': True, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '"Rp" #,##0.00'})
        elif currency == "USD":
            currency_format = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$$-409]#,##0.00'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': True, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$$-409]#,##0.00'})
        elif currency == "AUD":
            currency_format = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$AUD] #.##0'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': True, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$AUD] #.##0'})
        elif currency == "JPY":
            currency_format = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$JPY] #.##0'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': True, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$JPY] #.##0'})
        elif currency == "SGD":
            currency_format = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$SGD] #.##0'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$SGD] #.##0'})
        elif currency == "EUR":
            currency_format = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$EUR] #.##0'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$EUR] #.##0'})
        else:
            currency_format = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$$-409]#,##0.00'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Arial', 'font_size': 8, 'bold': False, 'align': 'right', 'left': 1, 'bottom': 1,
                 'right': 1, 'top': 1, 'num_format': '[$$-409]#,##0.00'})

        # Title
        sheet.merge_range('A1:G2', self.get_title(data), title_text_style)

        # Upper Left
        sheet.write(2, 0, "Project", text_style_1)
        sheet.write(3, 0, "Customer", text_style_1)
        sheet.write(4, 0, "Planned Start Date", text_style_1)
        sheet.write(5, 0, "Planned End Date", text_style_1)
        sheet.write(6, 0, "Location", text_style_1)
        sheet.write(9, 0, "", text_style_1)
        sheet.write(10, 0, "", text_style_1)

        sheet.write(2, 1, "", text_style_1)
        sheet.write(3, 1, "", text_style_1)
        sheet.write(4, 1, "", text_style_1)
        sheet.write(5, 1, "", text_style_1)
        sheet.write(6, 1, "", text_style_1)
        sheet.write(7, 1, "", text_style_1)
        sheet.write(10, 1, "", text_style_1)

        sheet.write(2, 2, ": " + data.sale_order_id.project_id.name, text_style_1)
        sheet.write(3, 2, ": " + data.sale_order_id.partner_id.name, text_style_1)

        if data.sale_order_id.start_date:
            sheet.write(4, 2, ": " + data.sale_order_id.start_date.strftime("%m/%d/%Y"), text_style_1)
        else:
            sheet.write(4, 2, ": ", text_style_1)
        if data.sale_order_id.end_date:
            sheet.write(5, 2, ": " + data.sale_order_id.end_date.strftime("%m/%d/%Y"), text_style_1)
        else:
            sheet.write(5, 2, ": ", text_style_1)

        sheet.write(6, 2, ": " + self.get_construction_address(data)[0], text_style_1)
        sheet.write(7, 2, "  " + self.get_construction_address(data)[1], text_style_1)
        sheet.write(10, 2, "", text_style_1)

        if data.sale_order_id.contract_category == "main":
            sheet.write(8, 0, "", text_style_1)
            sheet.write(9, 0, "", text_style_1)
            sheet.write(8, 1, "", text_style_1)
            sheet.write(9, 1, "", text_style_1)
            sheet.write(8, 2, "", text_style_1)
            sheet.write(9, 2, "", text_style_1)
        else:
            sheet.write(8, 0, "Main Contract", text_style_1)
            sheet.write(9, 0, "Cost Sheet", text_style_1)
            sheet.write(8, 1, "", text_style_1)
            sheet.write(9, 1, "", text_style_1)
            sheet.write(8, 2, ": " + data.sale_order_id.main_contract_ref.name, text_style_1)
            # TO DO : Fix this later with filtered cost sheet
            sheet.write(9, 2, ": " + data.sale_order_id.cost_sheet_ref.name, text_style_1)

            # Upper Right
        sheet.write(2, 3, "Company", text_style_1)
        sheet.write(3, 3, "Category", text_style_1)
        sheet.write(4, 3, "Down Payment", text_style_1)
        sheet.write(5, 3, "Retention 1", text_style_1)
        sheet.write(6, 3, "Retention 1 Term", text_style_1)
        sheet.write(7, 3, "Retention 2", text_style_1)
        sheet.write(8, 3, "Retention 2 Term", text_style_1)
        sheet.write(9, 3, "Taxes", text_style_1)
        sheet.write(10, 3, "Payment Term", text_style_1)
        sheet.write(2, 4, "", text_style_1)
        sheet.write(3, 4, "", text_style_1)
        sheet.write(4, 4, "", text_style_1)
        sheet.write(5, 4, "", text_style_1)
        sheet.write(6, 4, "", text_style_1)
        sheet.write(7, 4, "", text_style_1)
        sheet.write(8, 4, "", text_style_1)
        sheet.write(9, 4, "", text_style_1)
        sheet.write(10, 4, "", text_style_1)

        sheet.merge_range('F3:G3', ": " + data.sale_order_id.company_id.name, text_style_1)
        sheet.merge_range('F4:G4', ": " + self.get_selection_value(data.sale_order_id.contract_category), text_style_1)

        if data.sale_order_id.dp_method == "fix":
            sheet.merge_range('F5:G5', ": " + str(data.sale_order_id.down_payment), text_style_1)
        else:
            sheet.merge_range('F5:G5', ": " + str(data.sale_order_id.down_payment) + "%", text_style_1)

        if data.sale_order_id.retention1:
            sheet.merge_range('F6:G6', ": " + str(data.sale_order_id.retention1) + "%", text_style_1)
        else:
            sheet.merge_range('F6:G6', ": 0", text_style_1)

        if data.sale_order_id.retention_term_1.name:
            sheet.merge_range('F7:G7', ": " + data.sale_order_id.retention_term_1.name, text_style_1)
        else:
            sheet.merge_range('F7:G7', ": ", text_style_1)

        if data.sale_order_id.retention2:
            sheet.merge_range('F8:G8', ": " + str(data.sale_order_id.retention2) + "%", text_style_1)
        else:
            sheet.merge_range('F8:G8', ": 0", text_style_1)

        if data.sale_order_id.retention_term_2.name:
            sheet.merge_range('F9:G9', ": " + data.sale_order_id.retention_term_2.name, text_style_1)
        else:
            sheet.merge_range('F9:G9', ": ", text_style_1)

        if data.sale_order_id.tax_id:
            sheet.merge_range('F10:G10', ": " + self.get_tax_value(data), text_style_1)
        else:
            sheet.merge_range('F10:G10', ": 0", text_style_1)

        if data.sale_order_id.payment_term_id.name:
            sheet.merge_range('F11:G11', ": " + data.sale_order_id.payment_term_id.name, text_style_1)
        else:
            sheet.merge_range('F11:G11', ": ", text_style_1)

        # Table Header
        sheet.write(12, 0, "No.", header_style)
        sheet.merge_range('B13:C13', "Job Description", header_style)
        sheet.write(12, 3, "Quantity", header_style)
        sheet.write(12, 4, "UOM", header_style)
        sheet.write(12, 5, "Unit Price", header_style)
        sheet.write(12, 6, "Subtotal", header_style)

        # Table Content
        char_inc = 'A'
        row_num = 13
        i_char = 0
        total = 0

        scope_sect_prod_dict = data.sale_order_id.get_report_data(data.print_level_option)
        for scope_name, scope in scope_sect_prod_dict.items():
            i_num = 1
            temp_subtotal = 0
            sheet.write(row_num, 0, chr(ord(char_inc) + i_char), number_text_style_1)
            sheet.merge_range(row_num, 1, row_num, 2, scope_name, table_content_text_style_1)
            sheet.write(row_num, 3, "", table_content_text_style_1)
            sheet.write(row_num, 4, "", table_content_text_style_1)
            sheet.write(row_num, 5, "", table_content_text_style_1)
            sheet.write(row_num, 6, "", table_content_text_style_1)
            row_num += 1
            i_char += 1

            for section_name, section in scope['children'].items():
                variable_char_num = 'a'
                i_var = 0
                # Section row
                sheet.write(row_num, 0, i_num, number_text_style_1)
                sheet.merge_range(row_num, 1, row_num, 2, section_name, table_content_text_style_1)
                sheet.write(row_num, 3, section['qty'], table_content_text_style_4)
                sheet.write(row_num, 4, section['uom'] or '', table_content_text_style_4)
                sheet.write(row_num, 5, '', table_content_text_style_4)
                sheet.write(row_num, 6, section['total'], currency_format_bold)
                row_num += 1
                i_num += 1
                temp_subtotal += section['total']

                for product_name, product in section['children'].items():
                    sheet.write(row_num, 0, chr(ord(variable_char_num) + i_var), number_text_style_2)
                    sheet.merge_range(row_num, 1, row_num, 2, product_name, table_content_text_style_2)
                    sheet.write(row_num, 3, product['qty'], table_content_text_style_3)
                    sheet.write(row_num, 4, product['uom'] or '', table_content_text_style_4)
                    sheet.write(row_num, 5, product['unit_price'], currency_format_bold)
                    sheet.write(row_num, 6, product['total'], currency_format_bold)
                    row_num += 1
                    i_var += 1

            # Subtotal Scope Row
            sheet.write(row_num, 0, "", number_text_style_2)
            sheet.merge_range(row_num, 1, row_num, 5, "SUBTOTAL " + data.sale_order_id.getRoman(i_char),
                              table_content_text_style_4)
            # sheet.write(row_num, 3, "", number_text_style_2)
            # sheet.write(row_num, 4, "", number_text_style_2)
            sheet.write(row_num, 6, scope['total'], currency_format_bold)
            row_num += 1
            # Empty Row
            sheet.write(row_num, 0, "", number_text_style_2)
            sheet.merge_range(row_num, 1, row_num, 2, "", table_content_text_style_1)
            sheet.write(row_num, 3, "", number_text_style_2)
            sheet.write(row_num, 4, "", number_text_style_2)
            sheet.write(row_num, 5, "", table_content_text_style_2)
            sheet.write(row_num, 6, "", table_content_text_style_2)
            row_num += 1

        # Tax Amount Row
        sheet.write(row_num, 0, "", number_text_style_2)
        sheet.merge_range(row_num, 1, row_num, 2, "Tax Amount", table_content_text_style_1)
        sheet.write(row_num, 3, "", number_text_style_2)
        sheet.write(row_num, 4, "", number_text_style_2)
        sheet.write(row_num, 5, "", table_content_text_style_2)
        sheet.write(row_num, 6, data.sale_order_id.amount_tax, currency_format_bold)
        row_num += 1

        # Total Row
        sheet.write(row_num, 0, "", number_text_style_2)
        sheet.merge_range(row_num, 1, row_num, 2, "Total", table_content_text_style_1)
        sheet.write(row_num, 3, "", number_text_style_2)
        sheet.write(row_num, 4, "", number_text_style_2)
        sheet.write(row_num, 5, "", currency_format_bold)
        sheet.write(row_num, 6, data.sale_order_id.amount_total, currency_format_bold)

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
