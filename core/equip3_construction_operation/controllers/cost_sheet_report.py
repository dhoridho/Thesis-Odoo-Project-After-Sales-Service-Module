from datetime import datetime
from odoo import http
from odoo.http import content_disposition, request
import io
import xlsxwriter


class JobCostSheetReportController(http.Controller):
    @http.route(
        ['/equip3_construction_operation/cost_sheet_report/<model("job.cost.sheet"):data>', ],
        type='http', auth='user', csrf=False)
    def get_job_cost_sheet_report(self, data=None, **args):
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

        # Style Configuration
        text_style_1 = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 8, 'bold': True, 'align': 'left', 'bg_color': 'white',  'left': 0, 'bottom': 0, 'right': 0, 'top': 0,})
        title_text_style = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 12, 'bold': True, 'align': 'left', 'valign': 'vcenter',
             'color': '#C55A11'})
        header_style = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 9, 'bold': True, 'left': 0, 'bottom': 0, 'right': 0, 'top': 0,
             'align': 'center', 'bg_color': '#C0C0C0'})
        number_text_style_1 = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 9, 'bold': True, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1,
             'align': 'center'})
        number_text_style_2 = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 9, 'bold': False, 'left': 1, 'bottom': 1, 'right': 1, 'top': 1,
             'align': 'center'})
        table_content_text_style_1 = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 9, 'bold': True, 'left': 0, 'bottom': 0, 'right': 0, 'top': 0,
             'align': 'left'})
        table_content_text_style_2 = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 9, 'bold': False, 'align': 'left', 'left': 0, 'bottom': 0, 'right': 0,
             'top': 0})
        table_content_text_style_3 = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 9, 'bold': False, 'align': 'center', 'left': 0, 'bottom': 0, 'right': 0,
             'top': 0})
        table_content_text_style_4 = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 9, 'bold': True, 'align': 'center', 'left': 0, 'bottom': 0, 'right': 0,
             'top': 0})
        table_content_text_style_5 = workbook.add_format(
            {'font_name': 'Calibri', 'font_size': 10, 'bold': True, 'left': 0, 'bottom': 0, 'right': 0, 'top': 0,
             'align': 'right'})
        sheet = workbook.add_worksheet("Cost Sheet")
        sheet.set_portrait()
        sheet.set_paper(9)
        sheet.set_margins(0.31, 0.31, 0.59, 0.35)
        sheet.set_column('A:A', 10)
        sheet.set_column('C:C', 40)
        sheet.set_column('D:D', 12)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:G', 15)

        # Currency Formatting
        currency = data.currency_id.name
        if currency == "IDR":
            currency_format = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '"Rp" #,##0.00'})
            currency_format_1 = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 10, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '"Rp" #,##0.00'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': True, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '"Rp" #,##0.00'})
        elif currency == "USD":
            currency_format = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$$-409] #,##0.00'})
            currency_format_1 = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 10, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$$-409] #,##0.00'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': True, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$$-409] #,##0.00'})
        elif currency == "AUD":
            currency_format = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$AUD] #.##0'})
            currency_format_1 = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 10, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$AUD] #.##0'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': True, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$AUD] #.##0'})
        elif currency == "JPY":
            currency_format = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$JPY] #.##0'})
            currency_format_1 = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 10, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$JPY] #.##0'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': True, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$JPY] #.##0'})
        elif currency == "SGD":
            currency_format = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$SGD] #.##0'})
            currency_format_1 = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 10, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$SGD] #.##0'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': True, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$SGD] #.##0'})
        elif currency == "EUR":
            currency_format = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$EUR] #.##0'})
            currency_format_1 = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 10, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$EUR] #.##0'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': True, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$EUR] #.##0'})
        else:
            currency_format = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$$-409] #,##0.00'})
            currency_format_1 = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 10, 'bold': False, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$$-409] #,##0.00'})
            currency_format_bold = workbook.add_format(
                {'font_name': 'Calibri', 'font_size': 9, 'bold': True, 'align': 'right', 'left': 0, 'bottom': 0,
                 'right': 0, 'top': 0, 'num_format': '[$$-409] #,##0.00'})

        # Upper Left
        sheet.write(2, 0, "Project", table_content_text_style_1)
        sheet.write(3, 0, "Customer", table_content_text_style_1)
        sheet.write(4, 0, "Cost Sheet", table_content_text_style_1)

        # Upper Left Value
        sheet.write(2, 1, ': ' + data.project_id.name, table_content_text_style_2)
        sheet.write(3, 1, ': ' + data.project_id.partner_id.name, table_content_text_style_2)
        sheet.write(4, 1, ': ' + data.number, table_content_text_style_2)

        row = 6
        if len(data.material_ids) > 0:
            # Material Estimation
            sheet.merge_range(row, 0, row, 1, "Material Estimation", title_text_style)
            row += 1
            sheet.write(row, 0, "Scope", header_style)
            sheet.write(row, 1, "Section", header_style)
            sheet.write(row, 2, "Description", header_style)
            sheet.write(row, 3, "Quantity", header_style)
            sheet.write(row, 4, "UoM", header_style)
            sheet.write(row, 5, "Unit Price", header_style)
            sheet.write(row, 6, "Amount", header_style)
            sheet.write(row, 7, "Quantity Left", header_style)
            sheet.write(row, 8, "Amount Left", header_style)
            sheet.write(row, 9, "Reserve Quantity", header_style)
            sheet.write(row, 10, "Reserve Amount", header_style)
            sheet.write(row, 11, "Paid Quantity", header_style)
            sheet.write(row, 12, "Paid Amount", header_style)
            sheet.write(row, 13, "Actual Used Quantity", header_style)
            sheet.write(row, 14, "Actual Used Amount", header_style)
            row += 1

            for material in data.material_ids:
                sheet.write(row, 0, material.project_scope.name, table_content_text_style_2)
                sheet.write(row, 1, material.section_name.name, table_content_text_style_2)
                sheet.write(row, 2, material.description, table_content_text_style_2)
                sheet.write(row, 3, material.product_qty, table_content_text_style_3)
                sheet.write(row, 4, material.uom_id.name, table_content_text_style_3)
                sheet.write(row, 5, material.price_unit, currency_format)
                sheet.write(row, 6, material.material_amount_total, currency_format)
                sheet.write(row, 7, material.budgeted_qty_left, table_content_text_style_3)
                sheet.write(row, 8, material.budgeted_amt_left, currency_format)
                sheet.write(row, 9, material.reserved_qty, table_content_text_style_3)
                sheet.write(row, 10, material.reserved_amt, currency_format)
                sheet.write(row, 11, material.purchased_qty, table_content_text_style_3)
                sheet.write(row, 12, material.purchased_amt, currency_format)
                sheet.write(row, 13, material.actual_used_qty, table_content_text_style_3)
                sheet.write(row, 14, material.actual_used_amt, currency_format)
                row += 1

            # Subtotal Material Estimation
            sheet.merge_range(row, 0, row, 1, "Subtotal", table_content_text_style_4)
            sheet.write(row, 6, data.amount_material, currency_format_bold)
            sheet.write(row, 8, data.material_budget_left, currency_format_bold)
            sheet.write(row, 10, data.material_budget_res, currency_format_bold)
            sheet.write(row, 12, data.material_budget_pur, currency_format_bold)
            sheet.write(row, 14, data.material_budget_used, currency_format_bold)
            row += 1

            # Empty Row
            row += 1

        if len(data.material_labour_ids) > 0:
            # Material Labour Estimation
            sheet.merge_range(row, 0, row, 1, "Labour Estimation", title_text_style)
            row += 1
            sheet.write(row, 0, "Scope", header_style)
            sheet.write(row, 1, "Section", header_style)
            sheet.write(row, 2, "Description", header_style)
            sheet.write(row, 3, "Contractors", header_style)
            sheet.write(row, 4, "Time", header_style)
            sheet.write(row, 5, "UoM", header_style)
            sheet.write(row, 6, "Unit Price", header_style)
            sheet.write(row, 7, "Amount", header_style)
            sheet.write(row, 8, "Contractors Left", header_style)
            sheet.write(row, 9, "Time Left", header_style)
            sheet.write(row, 10, "Amount Left", header_style)
            sheet.write(row, 11, "Reserve Contractors", header_style)
            sheet.write(row, 12, "Reserve Time", header_style)
            sheet.write(row, 13, "Reserve Amount", header_style)
            sheet.write(row, 14, "Actual Used Time", header_style)
            sheet.write(row, 15, "Actual Used Amount", header_style)
            row += 1

            for material_labour in data.material_labour_ids:
                sheet.write(row, 0, material_labour.project_scope.name, table_content_text_style_2)
                sheet.write(row, 1, material_labour.section_name.name, table_content_text_style_2)
                sheet.write(row, 2, material_labour.description, table_content_text_style_2)
                sheet.write(row, 3, material_labour.contractors, table_content_text_style_3)
                sheet.write(row, 4, material_labour.time, table_content_text_style_3)
                sheet.write(row, 5, material_labour.uom_id.name, table_content_text_style_3)
                sheet.write(row, 6, material_labour.price_unit, currency_format)
                sheet.write(row, 7, material_labour.labour_amount_total, currency_format)
                sheet.write(row, 8, material_labour.contractors_left, table_content_text_style_3)
                sheet.write(row, 9, material_labour.time_left, table_content_text_style_3)
                sheet.write(row, 10, material_labour.budgeted_amt_left, currency_format)
                sheet.write(row, 11, material_labour.reserved_contractors, table_content_text_style_3)
                sheet.write(row, 12, material_labour.reserved_time, table_content_text_style_3)
                sheet.write(row, 13, material_labour.reserved_amt, currency_format)
                sheet.write(row, 14, material_labour.actual_used_time, table_content_text_style_3)
                sheet.write(row, 15, material_labour.actual_used_amt, currency_format)
                row += 1

            # Subtotal Labour Estimation
            sheet.merge_range(row, 0, row, 1, "Subtotal", table_content_text_style_4)
            sheet.write(row, 7, data.amount_labour, currency_format_bold)
            sheet.write(row, 10, data.labour_budget_left, currency_format_bold)
            sheet.write(row, 13, data.labour_budget_res, currency_format_bold)
            sheet.write(row, 15, data.labour_budget_used, currency_format_bold)
            row += 1

            # Empty Row
            row += 1

        if len(data.material_overhead_ids) > 0:
            # Material Overhead Estimation
            sheet.merge_range(row, 0, row, 1, "Overhead Estimation", title_text_style)
            row += 1
            sheet.write(row, 0, "Scope", header_style)
            sheet.write(row, 1, "Section", header_style)
            sheet.write(row, 2, "Description", header_style)
            sheet.write(row, 4, "Quantity", header_style)
            sheet.write(row, 3, "UoM", header_style)
            sheet.write(row, 5, "Unit Price", header_style)
            sheet.write(row, 6, "Amount", header_style)
            sheet.write(row, 7, "Quantity Left", header_style)
            sheet.write(row, 8, "Amount Left", header_style)
            sheet.write(row, 9, "Reserve Quantity", header_style)
            sheet.write(row, 10, "Reserve Amount", header_style)
            sheet.write(row, 11, "Paid Quantity", header_style)
            sheet.write(row, 12, "Paid Amount", header_style)
            sheet.write(row, 13, "Actual Used Quantity", header_style)
            sheet.write(row, 14, "Actual Used Amount", header_style)
            row += 1

            for material_overhead in data.material_overhead_ids:
                sheet.write(row, 0, material_overhead.project_scope.name, table_content_text_style_2)
                sheet.write(row, 1, material_overhead.section_name.name, table_content_text_style_2)
                sheet.write(row, 2, material_overhead.description, table_content_text_style_2)
                sheet.write(row, 3, material_overhead.uom_id.name, table_content_text_style_3)
                sheet.write(row, 4, material_overhead.product_qty, table_content_text_style_3)
                sheet.write(row, 5, material_overhead.price_unit, currency_format)
                sheet.write(row, 6, material_overhead.overhead_amount_total, currency_format)
                sheet.write(row, 7, material_overhead.budgeted_qty_left, table_content_text_style_3)
                sheet.write(row, 8, material_overhead.budgeted_amt_left, currency_format)
                sheet.write(row, 9, material_overhead.reserved_qty, table_content_text_style_3)
                sheet.write(row, 10, material_overhead.reserved_amt, currency_format)
                sheet.write(row, 11, material_overhead.purchased_qty, table_content_text_style_3)
                sheet.write(row, 12, material_overhead.purchased_amt, currency_format)
                sheet.write(row, 13, material_overhead.actual_used_qty, table_content_text_style_3)
                sheet.write(row, 14, material_overhead.actual_used_amt, currency_format)
                row += 1

            # Subtotal Overhead Estimation
            sheet.merge_range(row, 0, row, 1, "Subtotal", table_content_text_style_4)
            sheet.write(row, 6, data.amount_overhead, currency_format_bold)
            sheet.write(row, 8, data.overhead_budget_left, currency_format_bold)
            sheet.write(row, 10, data.overhead_budget_res, currency_format_bold)
            sheet.write(row, 12, data.overhead_budget_pur, currency_format_bold)
            sheet.write(row, 14, data.overhead_budget_used, currency_format_bold)
            row += 1

            # Empty Row
            row += 1

        if len(data.material_equipment_ids) > 0:
            # Material Equipment Estimation
            sheet.merge_range(row, 0, row, 1, "Equipment Estimation", title_text_style)
            row += 1
            sheet.write(row, 0, "Scope", header_style)
            sheet.write(row, 1, "Section", header_style)
            sheet.write(row, 2, "Description", header_style)
            sheet.write(row, 3, "Quantity", header_style)
            sheet.write(row, 4, "UoM", header_style)
            sheet.write(row, 5, "Unit Price", header_style)
            sheet.write(row, 6, "Amount", header_style)
            sheet.write(row, 7, "Quantity Left", header_style)
            sheet.write(row, 8, "Amount Left", header_style)
            sheet.write(row, 9, "Reserve Quantity", header_style)
            sheet.write(row, 10, "Reserve Amount", header_style)
            sheet.write(row, 11, "Paid Quantity", header_style)
            sheet.write(row, 12, "Paid Amount", header_style)
            sheet.write(row, 13, "Actual Used Quantity", header_style)
            sheet.write(row, 14, "Actual Used Amount", header_style)
            row += 1

            for material_equipment in data.material_equipment_ids:
                sheet.write(row, 0, material_equipment.project_scope.name, table_content_text_style_2)
                sheet.write(row, 1, material_equipment.section_name.name, table_content_text_style_2)
                sheet.write(row, 2, material_equipment.description, table_content_text_style_2)
                sheet.write(row, 3, material_equipment.product_qty, table_content_text_style_3)
                sheet.write(row, 4, material_equipment.uom_id.name, table_content_text_style_3)
                sheet.write(row, 5, material_equipment.price_unit, currency_format)
                sheet.write(row, 6, material_equipment.equipment_amount_total, currency_format)
                sheet.write(row, 7, material_equipment.budgeted_qty_left, table_content_text_style_3)
                sheet.write(row, 8, material_equipment.budgeted_amt_left, currency_format)
                sheet.write(row, 9, material_equipment.reserved_qty, table_content_text_style_3)
                sheet.write(row, 10, material_equipment.reserved_amt, currency_format)
                sheet.write(row, 11, material_equipment.purchased_qty, table_content_text_style_3)
                sheet.write(row, 12, material_equipment.purchased_amt, currency_format)
                sheet.write(row, 13, material_equipment.actual_used_qty, table_content_text_style_3)
                sheet.write(row, 14, material_equipment.actual_used_amt, currency_format)
                row += 1

            # Subtotal Equipment Estimation
            sheet.merge_range(row, 0, row, 1, "Subtotal", table_content_text_style_4)
            sheet.write(row, 6, data.amount_equipment, currency_format_bold)
            sheet.write(row, 8, data.equipment_budget_left, currency_format_bold)
            sheet.write(row, 10, data.equipment_budget_res, currency_format_bold)
            sheet.write(row, 12, data.equipment_budget_pur, currency_format_bold)
            sheet.write(row, 14, data.equipment_budget_used, currency_format_bold)
            row += 1

            # Empty Row
            row += 1

        if len(data.internal_asset_ids) > 0:
            # Material Estimation
            sheet.merge_range(row, 0, row, 1, "Internal Asset Estimation", title_text_style)
            row += 1
            sheet.write(row, 0, "Scope", header_style)
            sheet.write(row, 1, "Section", header_style)
            sheet.write(row, 2, "Description", header_style)
            sheet.write(row, 3, "Quantity", header_style)
            sheet.write(row, 4, "UoM", header_style)
            sheet.write(row, 5, "Unit Price", header_style)
            sheet.write(row, 6, "Amount", header_style)
            sheet.write(row, 7, "Quantity Left", header_style)
            sheet.write(row, 8, "Amount Left", header_style)
            sheet.write(row, 9, "Actual Used Quantity", header_style)
            sheet.write(row, 10, "Actual Used Amount", header_style)
            row += 1

            for internal_asset in data.internal_asset_ids:
                sheet.write(row, 0, internal_asset.project_scope.name, table_content_text_style_2)
                sheet.write(row, 1, internal_asset.section_name.name, table_content_text_style_2)
                sheet.write(row, 2, internal_asset.description, table_content_text_style_2)
                sheet.write(row, 3, internal_asset.budgeted_qty, table_content_text_style_3)
                sheet.write(row, 4, internal_asset.uom_id.name, table_content_text_style_3)
                sheet.write(row, 5, internal_asset.price_unit, currency_format)
                sheet.write(row, 6, internal_asset.budgeted_amt, currency_format)
                sheet.write(row, 7, internal_asset.budgeted_qty_left, table_content_text_style_3)
                sheet.write(row, 8, internal_asset.budgeted_amt_left, currency_format)
                sheet.write(row, 9, internal_asset.actual_used_qty, table_content_text_style_3)
                sheet.write(row, 10, internal_asset.actual_used_amt, currency_format)
                row += 1

            # Subtotal Internal Asset Estimation
            sheet.merge_range(row, 0, row, 1, "Subtotal", table_content_text_style_4)
            sheet.write(row, 6, data.amount_internal_asset, currency_format_bold)
            sheet.write(row, 8, data.internas_budget_left, currency_format_bold)
            sheet.write(row, 10, data.internas_budget_used, currency_format_bold)
            row += 1

            # Empty Row
            row += 1

        if len(data.material_subcon_ids) > 0:
            # Material Subcon Estimation
            sheet.merge_range(row, 0, row, 1, "Subcon Estimation", title_text_style)
            row += 1
            sheet.write(row, 0, "Scope", header_style)
            sheet.write(row, 1, "Section", header_style)
            sheet.write(row, 2, "Description", header_style)
            sheet.write(row, 3, "Quantity", header_style)
            sheet.write(row, 4, "UoM", header_style)
            sheet.write(row, 5, "Unit Price", header_style)
            sheet.write(row, 6, "Amount", header_style)
            sheet.write(row, 7, "Quantity Left", header_style)
            sheet.write(row, 8, "Amount Left", header_style)
            sheet.write(row, 9, "Reserve Quantity", header_style)
            sheet.write(row, 10, "Reserve Amount", header_style)
            sheet.write(row, 11, "Paid Quantity", header_style)
            sheet.write(row, 12, "Paid Amount", header_style)
            sheet.write(row, 13, "Actual Used Quantity", header_style)
            sheet.write(row, 14, "Actual Used Amount", header_style)
            row += 1

            for material_subcon in data.material_subcon_ids:
                sheet.write(row, 0, material_subcon.project_scope.name, table_content_text_style_2)
                sheet.write(row, 1, material_subcon.section_name.name, table_content_text_style_2)
                sheet.write(row, 2, material_subcon.description, table_content_text_style_2)
                sheet.write(row, 3, material_subcon.product_qty, table_content_text_style_3)
                sheet.write(row, 4, material_subcon.uom_id.name, table_content_text_style_3)
                sheet.write(row, 5, material_subcon.price_unit, currency_format)
                sheet.write(row, 6, material_subcon.subcon_amount_total, currency_format)
                sheet.write(row, 7, material_subcon.budgeted_qty_left, table_content_text_style_3)
                sheet.write(row, 8, material_subcon.budgeted_amt_left, currency_format)
                sheet.write(row, 9, material_subcon.reserved_qty, table_content_text_style_3)
                sheet.write(row, 10, material_subcon.reserved_amt, currency_format)
                sheet.write(row, 11, material_subcon.purchased_qty, table_content_text_style_3)
                sheet.write(row, 12, material_subcon.purchased_amt, currency_format)
                sheet.write(row, 13, material_subcon.actual_used_qty, table_content_text_style_3)
                sheet.write(row, 14, material_subcon.actual_used_amt, currency_format)
                row += 1

            # Subtotal Subcon Estimation
            sheet.merge_range(row, 0, row, 1, "Subtotal", table_content_text_style_4)
            sheet.write(row, 6, data.amount_subcon, currency_format_bold)
            sheet.write(row, 8, data.subcon_budget_left, currency_format_bold)
            sheet.write(row, 10, data.subcon_budget_res, currency_format_bold)
            sheet.write(row, 12, data.subcon_budget_pur, currency_format_bold)
            sheet.write(row, 14, data.subcon_budget_used, currency_format_bold)
            row += 1

            # Empty Row
            row += 1

        # empty row
        row += 2

        # Total
        sheet.write(row, 13, "Amount Total:", table_content_text_style_5)
        sheet.write(row+1, 13, "Reserve Amount Total:", table_content_text_style_5)
        sheet.write(row+2, 13, "Paid Amount Total:", table_content_text_style_5)
        sheet.write(row+3, 13, "Actual Used Amount Total:", table_content_text_style_5)

        sheet.write(row, 14, data.amount_total, currency_format_1)
        sheet.write(row+1, 14, data.contract_budget_res, currency_format_1)
        sheet.write(row+2, 14, data.contract_budget_pur, currency_format_1)
        sheet.write(row+3, 14, data.contract_budget_used, currency_format_1)

        sheet.autofit()
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
        return response

    def get_file_name(self, data):
        current_datetime = datetime.now()
        current_datetime_string = current_datetime.strftime("%d-%m-%Y")

        filename = "Cost Sheet - " + data.project_id.name + " - " + data.number + " - " + current_datetime_string + ".xlsx"
        return filename
