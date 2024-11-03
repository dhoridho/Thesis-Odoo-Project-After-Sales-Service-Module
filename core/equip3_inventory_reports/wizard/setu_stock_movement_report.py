
from odoo import fields, models, api
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_advance_inventory_reports.library import xlsxwriter
from . import setu_excel_formatter
from datetime import datetime, timedelta, date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import base64
from io import BytesIO
from odoo.exceptions import  ValidationError
from dateutil.relativedelta import relativedelta


# class StockScrap(models.Model):
#     _inherit = 'stock.scrap'

#     product_state = fields.Selection([('draft', 'Draft'),
#                               ('confirmed', 'Confirmed'),
#                               ('to_approve', 'Waiting for Approval'),
#                               ('approved', 'Approved'),
#                               ('rejected', 'Rejected'),
#                               ('validated', 'Validated'),
#                               ('cancel', 'Cancelled')
#                               ], string='Status',related='scrap_id.state')

#     usage_type = fields.Many2one('usage.type', string="Scrap Type", related='scrap_id.scrap_type')
#     warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", related='scrap_id.warehouse_id')
#     date_done = fields.Datetime(related="scrap_id.date_done",string="Done Date")


class StockAgeReport(models.TransientModel):
    _inherit = "setu.inventory.age.report"

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        company_wise_data = {}
        for data in stock_data:
            key = (data.get('company_id'), data.get('company_name'))
            if not company_wise_data.get(key,False):
                company_wise_data[key] = {data.get('product_id') : data}
            else:
                company_wise_data.get(key).update({data.get('product_id') : data})
            product_id = self.env['product.product'].browse([data.get('product_id')])
            data.update({
                'product_name': product_id.display_name,
            })
        return company_wise_data

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook,setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 8, "Inventory Age Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook,worksheet)
        self.set_column_width(workbook, worksheet)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)

        worksheet.write(row, 0, 'Product', normal_left_format)
        worksheet.write(row, 1, 'Product Category', normal_left_format)
        worksheet.write(row, 2, 'Current Stock', odd_normal_right_format)
        worksheet.write(row, 3, 'Stock Value', even_normal_right_format)
        worksheet.write(row, 4, 'Stock Qty (%)', odd_normal_right_format)
        worksheet.write(row, 5, 'Stock Value (%)', even_normal_right_format)
        worksheet.write(row, 6, "Oldest Stock Age", odd_normal_right_format)
        worksheet.write(row, 7, "Oldest Qty", even_normal_right_format)
        worksheet.write(row, 8, "Oldest Stock Value", odd_normal_right_format)

        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        odoo_normal_center_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_CENTER)
        # odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('product_name',''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name',''), normal_left_format)
        worksheet.write(row, 2, data.get('current_stock',''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('current_stock_value',''), even_normal_right_format)
        worksheet.write(row, 4, data.get('stock_qty_ratio',''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('stock_value_ratio',''), even_normal_right_format)
        worksheet.write(row, 6, data.get('days_old',''), odd_normal_right_format)
        worksheet.write(row, 7, data.get('oldest_stock_qty', ''), even_normal_right_format)
        worksheet.write(row, 8, data.get('oldest_stock_value', ''), odd_normal_right_format)
        return worksheet

class StockAgeBreakdownReport(models.TransientModel):
    _inherit = "setu.inventory.age.breakdown.report"

    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        company_wise_data = {}
        for data in stock_data:
            key = (data.get('company_id'), data.get('company_name'))
            if not company_wise_data.get(key,False):
                company_wise_data[key] = {data.get('product_id') : data}
            else:
                company_wise_data.get(key).update({data.get('product_id') : data})
            product_id = self.env['product.product'].browse([data.get('product_id')])
            data.update({
                'product_name': product_id.display_name,
            })
        return company_wise_data

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook,setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 17, "Inventory Age Breakdown Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook,worksheet)
        self.set_column_width(workbook, worksheet)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)

        odd_normal_center_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_CENTER)
        even_normal_center_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_CENTER)

        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)

        worksheet.write(row, 0, 'Product', normal_left_format)
        worksheet.write(row, 1, 'Product Category', normal_left_format)
        worksheet.write(row, 2, 'Total Stock', odd_normal_right_format)
        worksheet.write(row, 3, 'Stock Value', even_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row-1, 4, self.get_column_header(1), odd_normal_center_format)
        worksheet.write(row, 4, "Stock" ,odd_normal_right_format)
        worksheet.write(row, 5, "Value", odd_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 6, self.get_column_header(2), even_normal_center_format)
        worksheet.write(row, 6, "Stock", even_normal_right_format)
        worksheet.write(row, 7, "Value", even_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 8, self.get_column_header(3), odd_normal_center_format)
        worksheet.write(row, 8, "Stock", odd_normal_right_format)
        worksheet.write(row, 9, "Value", odd_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 10, self.get_column_header(4), even_normal_center_format)
        worksheet.write(row, 10, "Stock", odd_normal_right_format)
        worksheet.write(row, 11, "Value", odd_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 12, self.get_column_header(5), odd_normal_center_format)
        worksheet.write(row, 12, "Stock", odd_normal_right_format)
        worksheet.write(row, 13, "Value", odd_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 14, self.get_column_header(6), even_normal_center_format)
        worksheet.write(row, 14, "Stock", odd_normal_right_format)
        worksheet.write(row, 15, "Value", odd_normal_right_format)

        self.set_breakdown_header(workbook, worksheet, row - 1, 16, self.get_column_header(7), odd_normal_center_format)
        worksheet.write(row, 16, "Stock", odd_normal_right_format)
        worksheet.write(row, 17, "Value", odd_normal_right_format)

        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        odoo_normal_center_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_CENTER)
        # odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('product_name',''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name',''), normal_left_format)
        worksheet.write(row, 2, data.get('total_stock',''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('total_stock_value',''), even_normal_right_format)
        worksheet.write(row, 4, data.get('breakdown1_qty',''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('breckdown1_value',''), odd_normal_right_format)
        worksheet.write(row, 6, data.get('breakdown2_qty', ''), even_normal_right_format)
        worksheet.write(row, 7, data.get('breckdown2_value', ''), even_normal_right_format)
        worksheet.write(row, 8, data.get('breakdown3_qty', ''), odd_normal_right_format)
        worksheet.write(row, 9, data.get('breckdown3_value', ''), odd_normal_right_format)
        worksheet.write(row, 10, data.get('breakdown4_qty', ''), even_normal_right_format)
        worksheet.write(row, 11, data.get('breckdown4_value', ''), even_normal_right_format)
        worksheet.write(row, 12, data.get('breakdown5_qty', ''), odd_normal_right_format)
        worksheet.write(row, 13, data.get('breckdown5_value', ''), odd_normal_right_format)
        worksheet.write(row, 14, data.get('breakdown6_qty', ''), even_normal_right_format)
        worksheet.write(row, 15, data.get('breckdown6_value', ''), even_normal_right_format)
        worksheet.write(row, 16, data.get('breakdown7_qty', ''), odd_normal_right_format)
        worksheet.write(row, 17, data.get('breckdown7_value', ''), odd_normal_right_format)
        return worksheet

class StockTurnoverReport(models.TransientModel):
    _inherit = "setu.inventory.turnover.analysis.report"

    @api.onchange('end_date')
    def date_validation_end(self):
        for record in self:
            if record.start_date:
                if record.end_date < record.start_date:
                    raise ValidationError('End Date Must not precede the start date...')

    @api.onchange('start_date')
    def date_validation_start(self):
        for record in self:
            if record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError('End Date Must not precede the start date...')

    @api.onchange('product_category_ids')
    def filter_product_check(self):
        for record in self:
            categ_list = []
            if record.product_category_ids:
                for categ in record.product_category_ids:
                    categ_list.append(categ.name)
            for product in self.product_ids:
                if product.categ_id.name not in categ_list:
                    record.write({'product_ids': [(3, product.id)]})



    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        warehouse_wise_data = {}
        for data in stock_data:
            key = (data.get('warehouse_id'), data.get('warehouse_name'))
            if not warehouse_wise_data.get(key,False):
                warehouse_wise_data[key] = {data.get('product_id') : data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id') : data})
            product_id = self.env['product.product'].browse([data.get('product_id')])
            data.update({
                'product_name': product_id.display_name,
            })
        return warehouse_wise_data

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 6, "Inventory Turnover Analysis Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

        worksheet.write(2, 0, "Report Start Date", wb_format_left)
        worksheet.write(3, 0, "Report End Date", wb_format_left)

        wb_format_center = self.set_format(workbook, {'num_format': 'dd/mm/yy', 'align' : 'center', 'bold':True ,'font_color' : 'red'})
        worksheet.write(2, 1, self.start_date, wb_format_center)
        worksheet.write(3, 1, self.end_date, wb_format_center)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook,worksheet)
        self.set_column_width(workbook, worksheet)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)

        worksheet.write(row, 0, 'Product', normal_left_format)
        worksheet.write(row, 1, 'Product Category', normal_left_format)
        worksheet.write(row, 2, 'Opening Stock', odd_normal_right_format)
        worksheet.write(row, 3, 'Closing Stock', even_normal_right_format)
        worksheet.write(row, 4, 'Average Stock', odd_normal_right_format)
        worksheet.write(row, 5, 'Sales', even_normal_right_format)
        worksheet.write(row, 6, 'Turnover Ratio', odd_normal_right_format)

        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_left_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_LEFT)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('product_name',''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name',''), normal_left_format)
        worksheet.write(row, 2, data.get('opening_stock',''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('closing_stock',''), even_normal_right_format)
        worksheet.write(row, 4, data.get('average_stock',''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('sales',''), even_normal_right_format)
        worksheet.write(row, 6, data.get('turnover_ratio',''), odd_normal_right_format)
        return worksheet


class SetuInventoryOutOfStockReport(models.TransientModel):

    _inherit = 'setu.inventory.outofstock.report'

    @api.onchange('end_date')
    def date_validation_end(self):
        for record in self:
            if record.start_date:
                if record.end_date < record.start_date:
                    raise ValidationError('End Date Must not precede the start date...')

    @api.onchange('start_date')
    def date_validation_start(self):
        for record in self:
            if record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError('End Date Must not precede the start date...')

    @api.onchange('product_category_ids')
    def filter_product_check(self):
        for record in self:
            categ_list = []
            if record.product_category_ids:
                for categ in record.product_category_ids:
                    categ_list.append(categ.name)
            for product in self.product_ids:
                if product.categ_id.name not in categ_list:
                    record.write({'product_ids': [(3, product.id)]})


    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        warehouse_wise_data = {}
        for data in stock_data:
            key = (data.get('warehouse_id'), data.get('warehouse_name'))
            if not warehouse_wise_data.get(key,False):
                warehouse_wise_data[key] = {data.get('product_id') : data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id') : data})
            product_id = self.env['product.product'].browse([data.get('product_id')])
            data.update({
                'product_name': product_id.display_name,
            })
        return warehouse_wise_data

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 20, "Inventory Out Of Stock Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

        report_string = ""

        report_string = "Inventory Analysis For Next"
        worksheet.merge_range(2, 0, 2, 1, report_string, wb_format_left)
        worksheet.write(2, 2, str(self.advance_stock_days) + " Days", wb_format_center)

        worksheet.merge_range(3, 0, 3, 1, "Sales History Taken From", wb_format_left)
        worksheet.merge_range(4, 0, 4, 1, "Sales History Taken Upto", wb_format_left)

        wb_format_center = self.set_format(workbook, {'num_format': 'dd/mm/yy', 'align' : 'center', 'bold':True ,'font_color' : 'red'})
        worksheet.write(3, 2, self.start_date, wb_format_center)
        worksheet.write(4, 2, self.end_date, wb_format_center)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook,worksheet)
        self.set_column_width(workbook, worksheet)

        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()

        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        normal_center_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        even_normal_left_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_LEFT)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_LEFT)

        worksheet.write(row, 0, 'Product', normal_left_format)
        worksheet.write(row, 1, 'Product Category', normal_left_format)
        worksheet.write(row, 2, 'Current Stock', odd_normal_right_format)
        worksheet.write(row, 3, 'Outgoing', even_normal_right_format)
        worksheet.write(row, 4, 'Incoming', odd_normal_right_format)
        worksheet.write(row, 5, 'Virtual Stock', even_normal_right_format)
        worksheet.write(row, 6, 'Sales', odd_normal_right_format)
        worksheet.write(row, 7, 'ADS', even_normal_right_format)
        worksheet.write(row, 8, 'Demanded Qty', odd_normal_right_format)
        worksheet.write(row, 9, 'In Stock Days', even_normal_right_format)
        worksheet.write(row, 10, 'OutOfStock Days', odd_normal_right_format)
        worksheet.write(row, 11, 'OutOfStock Ratio', even_normal_right_format)
        worksheet.write(row, 12, 'Cost Price', odd_normal_right_format)
        worksheet.write(row, 13, 'OutOfStock Qty', even_normal_right_format)
        worksheet.write(row, 14, 'OutOfStock Value', odd_normal_right_format)
        worksheet.write(row, 15, 'OutOfStock Qty (%)', even_normal_right_format)
        worksheet.write(row, 16, 'OutOfStock Value (%)', odd_normal_right_format)
        worksheet.write(row, 17, 'Turnover Ratio(%)', even_normal_right_format)
        worksheet.write(row, 18, 'FSN Classification', odd_normal_left_format)
        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_left_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_LEFT)
        even_normal_center_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('product_name',''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name',''), normal_left_format)
        worksheet.write(row, 2, data.get('qty_available',''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('outgoing',''), even_normal_right_format)
        worksheet.write(row, 4, data.get('incoming',''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('forecasted_stock',''), even_normal_right_format)
        worksheet.write(row, 6, data.get('sales',''), odd_normal_right_format)
        worksheet.write(row, 7, data.get('ads',''), even_normal_right_format)
        worksheet.write(row, 8, data.get('demanded_qty',''), odd_normal_right_format)
        worksheet.write(row, 9, data.get('in_stock_days',''), even_normal_right_format)
        worksheet.write(row, 10, data.get('out_of_stock_days',''), odd_normal_right_format)
        worksheet.write(row, 11, data.get('out_of_stock_ratio',''), even_normal_center_format)
        worksheet.write(row, 12, data.get('cost_price',''), odd_normal_right_format)
        worksheet.write(row, 13, data.get('out_of_stock_qty',''), even_normal_right_format)
        worksheet.write(row, 14, data.get('out_of_stock_value',''), odd_normal_right_format)
        worksheet.write(row, 15, data.get('out_of_stock_qty_per',''), even_normal_right_format)
        worksheet.write(row, 16, data.get('out_of_stock_value_per',''), odd_normal_right_format)
        worksheet.write(row, 17, data.get('turnover_ratio',''), even_normal_right_format)
        worksheet.write(row, 18, data.get('stock_movement',''), odd_normal_left_format)
        return worksheet

class SetuInventoryOverstockReport(models.TransientModel):

    _inherit = 'setu.inventory.overstock.report'

    @api.onchange('end_date')
    def date_validation_end(self):
        for record in self:
            if record.start_date:
                if record.end_date < record.start_date:
                    raise ValidationError('End Date Must not precede the start date...')

    @api.onchange('start_date')
    def date_validation_start(self):
        for record in self:
            if record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError('End Date Must not precede the start date...')

    @api.onchange('product_category_ids')
    def filter_product_check(self):
        for record in self:
            categ_list = []
            if record.product_category_ids:
                for categ in record.product_category_ids:
                    categ_list.append(categ.name)
            for product in self.product_ids:
                if product.categ_id.name not in categ_list:
                    record.write({'product_ids': [(3, product.id)]})

    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        warehouse_wise_data = {}
        for data in stock_data:
            key = (data.get('warehouse_id'), data.get('warehouse_name'))
            if not warehouse_wise_data.get(key,False):
                warehouse_wise_data[key] = {data.get('product_id') : data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id') : data})
            product_id = self.env['product.product'].browse([data.get('product_id')])
            data.update({
                'product_name': product_id.display_name,
            })
        return warehouse_wise_data

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 20, "Inventory Overstock Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

        report_string = ""

        report_string = "Inventory Analysis For Next"
        worksheet.merge_range(2, 0, 2, 1, report_string, wb_format_left)
        worksheet.write(2, 2, str(self.advance_stock_days) + " Days", wb_format_center)

        worksheet.merge_range(3, 0, 3, 1, "Sales History Taken From", wb_format_left)
        worksheet.merge_range(4, 0, 4, 1, "Sales History Taken Upto", wb_format_left)

        wb_format_center = self.set_format(workbook, {'num_format': 'dd/mm/yy', 'align' : 'center', 'bold':True ,'font_color' : 'red'})
        worksheet.write(3, 2, self.start_date, wb_format_center)
        worksheet.write(4, 2, self.end_date, wb_format_center)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook,worksheet)
        self.set_column_width(workbook, worksheet)

        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()

        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        normal_center_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        even_normal_left_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_LEFT)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_LEFT)

        worksheet.write(row, 0, 'Product', normal_left_format)
        worksheet.write(row, 1, 'Product Category', normal_left_format)
        worksheet.write(row, 2, 'Sales', odd_normal_right_format)
        worksheet.write(row, 3, 'ADS', even_normal_right_format)
        worksheet.write(row, 4, 'Current Stock', odd_normal_right_format)
        worksheet.write(row, 5, 'Outgoing', even_normal_right_format)
        worksheet.write(row, 6, 'Incoming', odd_normal_right_format)
        worksheet.write(row, 7, 'Virtual Stock', even_normal_right_format)
        worksheet.write(row, 8, 'Demanded Qty', odd_normal_right_format)
        worksheet.write(row, 9, 'Coverage Days', even_normal_right_format)
        worksheet.write(row, 10, 'Overstock Qty', odd_normal_right_format)
        worksheet.write(row, 11, 'Overstock Value', even_normal_right_format)
        worksheet.write(row, 12, 'Turnover Ratio', odd_normal_right_format)
        worksheet.write(row, 13, 'FSN Classification', even_normal_right_format)
        worksheet.write(row, 14, 'Overstock Qty (%)', odd_normal_right_format)
        worksheet.write(row, 15, 'Overstock Value (%)', even_normal_right_format)
        worksheet.write(row, 16, 'Last PO Date', odd_normal_right_format)
        worksheet.write(row, 17, 'Last PO Qty', even_normal_right_format)
        worksheet.write(row, 18, 'Last PO Price', odd_normal_right_format)
        worksheet.write(row, 19, 'Currency', even_normal_left_format)
        worksheet.write(row, 20, 'Vendor', odd_normal_left_format)
        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        ODD_FONT_MEDIUM_NORMAL_RIGHT_WITH_DATE = setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT.copy()
        ODD_FONT_MEDIUM_NORMAL_RIGHT_WITH_DATE.update({'num_format': 'dd/mm/yy', 'align' : 'center'})
        odd_normal_right_format_with_date = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT_WITH_DATE)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_left_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_LEFT)
        even_normal_center_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('product_name',''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name',''), normal_left_format)
        worksheet.write(row, 2, data.get('sales',''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('ads',''), even_normal_right_format)
        worksheet.write(row, 4, data.get('qty_available',''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('outgoing',''), even_normal_right_format)
        worksheet.write(row, 6, data.get('incoming',''), odd_normal_right_format)
        worksheet.write(row, 7, data.get('forecasted_stock',''), even_normal_right_format)
        worksheet.write(row, 8, data.get('demanded_qty',''), odd_normal_right_format)
        worksheet.write(row, 9, data.get('coverage_days',''), even_normal_right_format)
        worksheet.write(row, 10, data.get('overstock_qty',''), odd_normal_right_format)
        worksheet.write(row, 11, data.get('overstock_value',''), even_normal_right_format)
        worksheet.write(row, 12, data.get('turnover_ratio',''), odd_normal_right_format)
        worksheet.write(row, 13, data.get('stock_movement',''), even_normal_center_format)
        worksheet.write(row, 14, data.get('wh_overstock_qty_per',''), odd_normal_right_format)
        worksheet.write(row, 15, data.get('wh_overstock_value_per',''), even_normal_right_format)
        worksheet.write(row, 16, data.get('last_purchase_date',''), odd_normal_right_format_with_date)
        worksheet.write(row, 17, data.get('last_purchase_qty',''), even_normal_right_format)
        worksheet.write(row, 18, data.get('last_purchase_price',''), odd_normal_right_format)
        worksheet.write(row, 19, data.get('currency_name',''), even_normal_left_format)
        worksheet.write(row, 20, data.get('vendor_name',''), odd_normal_left_format)
        return worksheet

class SetuInventoryFSNXYZAnalysisReport(models.TransientModel):
    _inherit = 'setu.inventory.fsn.analysis.report'

    @api.onchange('end_date')
    def date_validation_end(self):
        for record in self:
            if record.start_date:
                if record.end_date < record.start_date:
                    raise ValidationError('End Date Must not precede the start date...')

    @api.onchange('start_date')
    def date_validation_start(self):
        for record in self:
            if record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError('End Date Must not precede the start date...')

    @api.onchange('product_category_ids')
    def filter_product_check(self):
        for record in self:
            categ_list = []
            if record.product_category_ids:
                for categ in record.product_category_ids:
                    categ_list.append(categ.name)
            for product in self.product_ids:
                if product.categ_id.name not in categ_list:
                    record.write({'product_ids': [(3, product.id)]})

    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        warehouse_wise_data = {}
        for data in stock_data:
            key = (data.get('warehouse_id'), data.get('warehouse_name'))
            if not warehouse_wise_data.get(key,False):
                warehouse_wise_data[key] = {data.get('product_id') : data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id') : data})
            product_id = self.env['product.product'].browse([data.get('product_id')])
            data.update({
                'product_name': product_id.display_name,
            })
        return warehouse_wise_data

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 7, "Inventory FSN Analysis Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

        worksheet.write(2, 0, "Report Start Date", wb_format_left)
        worksheet.write(3, 0, "Report End Date", wb_format_left)

        wb_format_center = self.set_format(workbook, {'num_format': 'dd/mm/yy', 'align' : 'center', 'bold':True ,'font_color' : 'red'})
        worksheet.write(2, 1, self.start_date, wb_format_center)
        worksheet.write(3, 1, self.end_date, wb_format_center)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook,worksheet)
        self.set_column_width(workbook, worksheet)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)

        worksheet.write(row, 0, 'Product', normal_left_format)
        worksheet.write(row, 1, 'Product Category', normal_left_format)
        worksheet.write(row, 2, 'Opening Stock', odd_normal_right_format)
        worksheet.write(row, 3, 'Closing Stock', even_normal_right_format)
        worksheet.write(row, 4, 'Average Stock', odd_normal_right_format)
        worksheet.write(row, 5, 'Sales', even_normal_right_format)
        worksheet.write(row, 6, 'Turnover Ratio', odd_normal_right_format)
        worksheet.write(row, 7, 'FSN Classification', even_normal_right_format)

        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_center_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('product_name',''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name',''), normal_left_format)
        worksheet.write(row, 2, data.get('opening_stock',''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('closing_stock',''), even_normal_right_format)
        worksheet.write(row, 4, data.get('average_stock',''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('sales',''), even_normal_right_format)
        worksheet.write(row, 6, data.get('turnover_ratio',''), odd_normal_right_format)
        worksheet.write(row, 7, data.get('stock_movement',''), even_normal_center_format)
        return worksheet

class SetuInventoryXYZAnalysisReport(models.TransientModel):
    _inherit = 'setu.inventory.xyz.analysis.report'

    @api.onchange('product_category_ids')
    def filter_product_check(self):
        for record in self:
            categ_list = []
            if record.product_category_ids:
                for categ in record.product_category_ids:
                    categ_list.append(categ.name)
            for product in self.product_ids:
                if product.categ_id.name not in categ_list:
                    record.write({'product_ids': [(3, product.id)]})

    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        warehouse_wise_data = {}
        for data in stock_data:
            key = (data.get('warehouse_id'), data.get('warehouse_name'))
            if not warehouse_wise_data.get(key,False):
                warehouse_wise_data[key] = {data.get('product_id') : data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id') : data})
            product_id = self.env['product.product'].browse([data.get('product_id')])
            data.update({
                'product_name': product_id.display_name,
            })
        return warehouse_wise_data

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook,setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 6, "Inventory XYZ Analysis Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook,worksheet)
        self.set_column_width(workbook, worksheet)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)

        worksheet.write(row, 0, 'Product', normal_left_format)
        worksheet.write(row, 1, 'Product Category', normal_left_format)
        worksheet.write(row, 2, 'Current Stock', odd_normal_right_format)
        worksheet.write(row, 3, 'Stock Value', even_normal_right_format)
        worksheet.write(row, 4, 'Stock Value (%)', odd_normal_right_format)
        worksheet.write(row, 5, 'Cumulative (%)', even_normal_right_format)
        worksheet.write(row, 6, 'XYZ Classification', odd_normal_right_format)

        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        odoo_normal_center_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('product_name',''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name',''), normal_left_format)
        worksheet.write(row, 2, data.get('current_stock',''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('stock_value',''), even_normal_right_format)
        worksheet.write(row, 4, data.get('stock_value_per',''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('cum_stock_value_per',''), even_normal_right_format)
        worksheet.write(row, 6, data.get('analysis_category',''), odoo_normal_center_format)
        return worksheet

class SetuInventoryFSNXYZAnalysisReport(models.TransientModel):
    _inherit = 'setu.inventory.fsn.xyz.analysis.report'

    @api.onchange('end_date')
    def date_validation_end(self):
        for record in self:
            if record.start_date:
                if record.end_date < record.start_date:
                    raise ValidationError('End Date Must not precede the start date...')

    @api.onchange('start_date')
    def date_validation_start(self):
        for record in self:
            if record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError('End Date Must not precede the start date...')

    @api.onchange('product_category_ids')
    def filter_product_check(self):
        for record in self:
            categ_list = []
            if record.product_category_ids:
                for categ in record.product_category_ids:
                    categ_list.append(categ.name)
            for product in self.product_ids:
                if product.categ_id.name not in categ_list:
                    record.write({'product_ids': [(3, product.id)]})

    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        warehouse_wise_data = {}
        for data in stock_data:
            key = (data.get('warehouse_id'), data.get('warehouse_name'))
            if not warehouse_wise_data.get(key,False):
                warehouse_wise_data[key] = {data.get('product_id') : data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id') : data})
            product_id = self.env['product.product'].browse([data.get('product_id')])
            data.update({
                'product_name': product_id.display_name,
            })
        return warehouse_wise_data

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 9, "Inventory FSN-XYZ Analysis Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

        worksheet.write(2, 0, "Report Start Date", wb_format_left)
        worksheet.write(3, 0, "Report End Date", wb_format_left)

        wb_format_center = self.set_format(workbook, {'num_format': 'dd/mm/yy', 'align' : 'center', 'bold':True ,'font_color' : 'red'})
        worksheet.write(2, 1, self.start_date, wb_format_center)
        worksheet.write(3, 1, self.end_date, wb_format_center)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook,worksheet)
        self.set_column_width(workbook, worksheet)
        worksheet.set_row(row, 28)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        odd_normal_right_format.set_text_wrap()
        even_normal_right_format.set_text_wrap()
        normal_left_format.set_text_wrap()

        worksheet.write(row, 0, 'Product', normal_left_format)
        worksheet.write(row, 1, 'Product Category', normal_left_format)
        worksheet.write(row, 2, 'Average Stock', odd_normal_right_format)
        worksheet.write(row, 3, 'Sales', even_normal_right_format)
        worksheet.write(row, 4, 'Turnover Ratio', odd_normal_right_format)
        worksheet.write(row, 5, 'Current Stock', even_normal_right_format)
        worksheet.write(row, 6, 'Stock Value', odd_normal_right_format)
        worksheet.write(row, 7, 'FSN Classification', even_normal_right_format)
        worksheet.write(row, 8, 'XYZ Classification', odd_normal_right_format)
        worksheet.write(row, 9, 'FSN-XYZ Classification', even_normal_right_format)

        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_center_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_center_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('product_name',''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name',''), normal_left_format)
        worksheet.write(row, 2, data.get('average_stock',''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('sales',''), even_normal_right_format)
        worksheet.write(row, 4, data.get('turnover_ratio',''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('current_stock',''), even_normal_right_format)
        worksheet.write(row, 6, data.get('stock_value',''), odd_normal_right_format)
        worksheet.write(row, 7, data.get('fsn_classification',''), even_normal_center_format)
        worksheet.write(row, 8, data.get('xyz_classification',''), odd_normal_center_format)
        worksheet.write(row, 9, data.get('combine_classification',''), even_normal_center_format)
        return worksheet

class StockMovementReport(models.TransientModel):
    _inherit = "setu.stock.movement.report"

    company_id = fields.Many2one('res.company', readonly=True, string='Company', default=lambda self: self.env.company)
    is_product_daily = fields.Boolean("Display Each Product Daily")
    is_movement_daily = fields.Boolean("Display Each Movement Daily")
    cluster_area_id = fields.Many2one('cluster.area', string='Cluster Area')
    is_date_swapped = fields.Boolean()

    @api.model
    def default_get(self, fields):
        result = super(StockMovementReport, self).default_get(fields)
        if not result.get('start_date'):
            result['start_date'] = date.today().strftime('%Y-%m-%d')

        return result

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date:
            self.end_date = self.start_date - timedelta(days=30)


    @api.onchange('is_product_daily')
    def onchange_is_product_daily(self):
        if not self.is_product_daily:
            self.is_movement_daily = False

    @api.onchange('cluster_area_id')
    def _onchange_cluster_area_id(self):
        self.warehouse_ids = [(6, 0, self.cluster_area_id.warehouse_line.mapped('warehouse_id').ids)]

    def get_product_stock_movements(self):
        """
            This method is used to get all stock transactions according to the filters
            which has been selected by users.
        :return: This methods returns List of dictionaries in which following data will be there
        -   Company
        -   Product
        -   Product Category
        -   Warehouse
        -   Opening Stock
        -   Purchase
        -   Value
        -   Sales
        -   Purchase Return
        -   Sales Return
        -   Internal Transfer In
        -   Internal Transfer Out
        -   Inventory Adjustment In
        -   Inventory Adjustment Out
        -   Stock To Transit (Transit IN)
        -   Transit To Stock (Transit Out)
        -   Production IN
        -   Production Out
        -   Closing Stock
        """

        # If user choose to get report up to a certain data then
        # start date should be pass null and
        # end date should be the selected date

        start_date, end_date = self.get_report_date_range()

        category_ids = company_ids = {}
        if self.product_category_ids:
            categories = self.env['product.category'].search([('id','child_of',self.product_category_ids.ids)])
            category_ids = set(categories.ids) or {}
        products = self.product_ids and set(self.product_ids.ids) or {}

        if self.company_ids:
            companies = self.env['res.company'].search([('id','child_of',self.company_ids.ids)])
            company_ids = set(companies.ids) or {}
        elif self.company_id:
            companies = self.env['res.company'].search([('id','child_of',self.company_id.ids)])
            company_ids = set(companies.ids) or {}
        else:
            company_ids = set(self.env.context.get('allowed_company_ids',False) or self.env.user.company_ids.ids) or {}

        warehouses = self.warehouse_ids and set(self.warehouse_ids.ids) or {}
        query = """
            Select * from get_products_stock_movements('%s','%s','%s','%s','%s','%s')
        """%(company_ids, products, category_ids, warehouses, start_date, end_date)
        # print(query)
        self._cr.execute(query)
        stock_data = self._cr.dictfetchall()
        return stock_data

    def set_report_title(self, workbook, worksheet, is_cluster=False):
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 16, "Stock Card Report", wb_format)
        
        start_date, end_date = self.get_report_date_range()
        if self.is_date_swapped:
            # revert swapped date for reports
            start_date, end_date = end_date, start_date

        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        report_string = ""
        if self.company_id:
            worksheet.write(2, 0, "Company", wb_format_left)
            worksheet.merge_range(2, 1, 2, 2, self.company_id.name, wb_format_left)
        worksheet.write(3, 0, "Cluster" if is_cluster else "Warehouse", wb_format_left)
        worksheet.merge_range(3, 1, 3, 2, worksheet.name, wb_format_left)
        if start_date == '1900-01-01':
            report_string = "Stock Cart up to"
            worksheet.merge_range(4, 0, 4, 1, report_string, wb_format_left)
            worksheet.write(4, 2, end_date, wb_format_center)
        else:
            worksheet.write(4, 0, "From Date", wb_format_left)
            worksheet.write(4, 1, end_date, wb_format_center)
            worksheet.write(5, 0, "To Date", wb_format_left)
            worksheet.write(5, 1, start_date, wb_format_center)


    def set_column_width(self, workbook, worksheet):
        worksheet.set_column(0, 2, 20)
        worksheet.set_column(3, 3, 30)
        worksheet.set_column(4, 16, 12)

    def write_report_data_header(self, workbook, worksheet, row, is_cluster=False):
        self.set_report_title(workbook,worksheet, is_cluster=is_cluster)
        self.set_column_width(workbook, worksheet)

        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()

        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)

        column = 0
        worksheet.write(row, column, 'No', normal_left_format)
        column += 1
        # product name = 2 column
        worksheet.write(row, column, 'Product', normal_left_format)
        column += 1
        worksheet.write(row, column, 'Unit Of Measure', normal_left_format)
        column += 1
        worksheet.write(row, column, 'Product Category', normal_left_format)
        column += 1
        if self.is_product_daily:
            worksheet.write(row, column, 'Date', normal_left_format)
            column += 1
        worksheet.write(row, column, 'Value', odd_normal_right_format)
        column += 1
        # opening stock = 4 column
        worksheet.write(row, column, 'Opening Stock', even_normal_right_format)
        column += 1
        # sales = 5 column
        worksheet.write(row, column, 'Opening Value', odd_normal_right_format)
        column += 1
        # sales = 5 column
        worksheet.write(row, column, 'Sales / Delivery', odd_normal_right_format)
        column += 1
        # sales_return = 6 column
        worksheet.write(row, column, 'Sales Return', even_normal_right_format)
        column += 1
        # purchase = 7 colum
        worksheet.write(row, column, 'Purchase / Receiving', odd_normal_right_format)
        column += 1
        # purchase_return = 8 column
        worksheet.write(row, column, 'Purchase Return', even_normal_right_format)
        column += 1
        # internal_in = 9 column
        worksheet.write(row, column, 'Internal IN', odd_normal_right_format)
        column += 1
        # internal_out = 10 column
        worksheet.write(row, column, 'Internal OUT', even_normal_right_format)
        column += 1
        # usage
        worksheet.write(row, column, 'Usage', odd_normal_right_format)
        column += 1
        # scrap
        worksheet.write(row, column, 'Scrap', even_normal_right_format)
        column += 1
        # adjustment_in = 11 column
        worksheet.write(row, column, 'Adjustment IN', odd_normal_right_format)
        column += 1
        # adjustment_out = 12 column
        worksheet.write(row, column, 'Adjustment OUT', even_normal_right_format)
        column += 1
        # production_in = 13 column
        worksheet.write(row, column, 'Production IN', odd_normal_right_format)
        column += 1
        # production_out = 14 column
        worksheet.write(row, column, 'Production OUT', even_normal_right_format)
        column += 1
        # transit_in = 15 column
        worksheet.write(row, column, 'Transit IN', odd_normal_right_format)
        column += 1
        # transit_out = 16 column
        worksheet.write(row, column, 'Transit OUT', even_normal_right_format)
        column += 1
        # closing = 16 column
        worksheet.write(row, column, 'Closing', odd_normal_right_format)
        column += 1
        worksheet.write(row, column, 'Closing Value', odd_normal_right_format)
        column += 1
        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, warehouse_id, warehouse_values, start_date, end_date, row, counter=False):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        row += 1
        for movement_data_key, data in warehouse_values.items():
            counter += 1

            if self.is_product_daily:
                date_wise_data = self.get_product_date_wise(data, self.start_date, self.end_date)
                data['date_wise_data'] = date_wise_data
            odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
            even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
            normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

            column = 0
            worksheet.write(row, column, counter, normal_left_format)
            column += 1
            worksheet.write(row, column, data.get('product_name',''), normal_left_format)
            column += 1
            worksheet.write(row, column, data.get('product_uom',''), normal_left_format)
            column += 1
            # category name = 3 column
            worksheet.write(row, column, data.get('category_name',''), normal_left_format)
            column += 1
            if self.is_product_daily:
                column += 1
            # opening stock = 4 column
            worksheet.write(row, column, data.get('value',''), odd_normal_right_format)
            column += 1
            worksheet.write(row, column, data.get('opening_stock',''), even_normal_right_format)
            column += 1

            worksheet.write(row, column, data.get('opening_value',''), odd_normal_right_format)
            column += 1
            # sales = 5 column
            worksheet.write(row, column, data.get('sales',''), odd_normal_right_format)
            column += 1
            # sales_return = 6 column
            worksheet.write(row, column, data.get('sales_return',''), even_normal_right_format)
            column += 1
            # purchase = 7 column
            worksheet.write(row, column, data.get('purchase',''), odd_normal_right_format)
            column += 1
            # purchase_return = 8 column
            worksheet.write(row, column, data.get('purchase_return',''), even_normal_right_format)
            column += 1
            # internal_in = 9 column
            worksheet.write(row, column, data.get('internal_in',''), odd_normal_right_format)
            column += 1
            # internal_out = 10 column
            worksheet.write(row,  column, data.get('internal_out',''), even_normal_right_format)
            column += 1
            # usage
            worksheet.write(row, column, data.get('product_usage_quantity', ''), odd_normal_right_format)
            column += 1
            # scrap
            worksheet.write(row, column, data.get('product_scrap_quantity', ''), even_normal_right_format)
            column += 1
            # adjustment_in = 11 column
            worksheet.write(row,  column, data.get('adjustment_in',''), odd_normal_right_format)
            column += 1
            # adjustment_out = 12 column
            worksheet.write(row,  column, data.get('adjustment_out',''), even_normal_right_format)
            column += 1
            # production_in = 13 column
            worksheet.write(row,  column, data.get('production_in',''), odd_normal_right_format)
            column += 1
            # production_out = 14 column
            worksheet.write(row,  column, data.get('production_out',''), even_normal_right_format)
            column += 1
            # transit_in = 15 column
            worksheet.write(row,  column, data.get('transit_in',''), odd_normal_right_format)
            column += 1
            # transit_out = 16 column
            worksheet.write(row,  column, data.get('transit_out',''), even_normal_right_format)
            column += 1
            # closing = 16 column
            worksheet.write(row,  column, data.get('closing',''), odd_normal_right_format)
            column += 1
            # closing = 18 column
            worksheet.write(row,  column, data.get('closing_value',''), odd_normal_right_format)
            column += 1
            row += 1

            if self.is_product_daily:
                for lines in data.get('date_wise_data'):
                    for date_wise_line in lines.get('data'):
                        date_wise_col = 0
                        worksheet.write(row, date_wise_col, '', normal_left_format)
                        date_wise_col += 1
                        worksheet.write(row, date_wise_col, '', normal_left_format)
                        date_wise_col += 1
                        worksheet.write(row, date_wise_col, '', normal_left_format)
                        date_wise_col += 1
                        worksheet.write(row, date_wise_col, '', normal_left_format)
                        date_wise_col += 1
                        worksheet.write(row, date_wise_col, lines.get('date').strftime(DEFAULT_SERVER_DATE_FORMAT), normal_left_format)
                        date_wise_col += 1
                        worksheet.write(row, date_wise_col, date_wise_line.get('opening_stock',''), even_normal_right_format)
                        date_wise_col += 1
                        # sales = 5 date_wise_col
                        worksheet.write(row, date_wise_col, date_wise_line.get('value',''), odd_normal_right_format)
                        date_wise_col += 1
                        worksheet.write(row, date_wise_col, date_wise_line.get('sales',''), odd_normal_right_format)
                        date_wise_col += 1
                        # sales_return = 6 date_wise_col
                        worksheet.write(row, date_wise_col, date_wise_line.get('sales_return',''), even_normal_right_format)
                        date_wise_col += 1
                        # purchase = 7 date_wise_col
                        worksheet.write(row, date_wise_col, date_wise_line.get('purchase',''), odd_normal_right_format)
                        date_wise_col += 1
                        # purchase_return = 8 date_wise_col
                        worksheet.write(row, date_wise_col, date_wise_line.get('purchase_return',''), even_normal_right_format)
                        date_wise_col += 1
                        # internal_in = 9 date_wise_col
                        worksheet.write(row, date_wise_col, date_wise_line.get('internal_in',''), odd_normal_right_format)
                        date_wise_col += 1
                        # internal_out = 10 date_wise_col
                        worksheet.write(row,  date_wise_col, date_wise_line.get('internal_out',''), even_normal_right_format)
                        date_wise_col += 1
                        # adjustment_in = 11 date_wise_col
                        worksheet.write(row,  date_wise_col, date_wise_line.get('adjustment_in',''), odd_normal_right_format)
                        date_wise_col += 1
                        # adjustment_out = 12 date_wise_col
                        worksheet.write(row,  date_wise_col, date_wise_line.get('adjustment_out',''), even_normal_right_format)
                        date_wise_col += 1
                        # production_in = 13 date_wise_col
                        worksheet.write(row,  date_wise_col, date_wise_line.get('production_in',''), odd_normal_right_format)
                        date_wise_col += 1
                        # production_out = 14 date_wise_col
                        worksheet.write(row,  date_wise_col, date_wise_line.get('production_out',''), even_normal_right_format)
                        date_wise_col += 1
                        # transit_in = 15 date_wise_col
                        worksheet.write(row,  date_wise_col, date_wise_line.get('transit_in',''), odd_normal_right_format)
                        date_wise_col += 1
                        # transit_out = 16 date_wise_col
                        worksheet.write(row,  date_wise_col, date_wise_line.get('transit_out',''), even_normal_right_format)
                        date_wise_col += 1
                        # closing = 16 date_wise_col
                        worksheet.write(row,  date_wise_col, date_wise_line.get('closing',''), odd_normal_right_format)
                        date_wise_col += 1
                        row += 1
        # return worksheet

    def get_file_name(self):
        filename = "Stock Card"
        if self.get_report_from_beginning:
            filename = filename + " upto_" + self.upto_date.strftime("%Y-%m-%d") + ".xlsx"
        else:
            filename = filename + " from_" + self.start_date.strftime("%Y-%m-%d") + "_to_" + self.end_date.strftime("%Y-%m-%d") + ".xlsx"
        return filename

    def _add_usage_scrap(self, warehouse_wise_stock_data):
        day_before = self.start_date - relativedelta(days=1)
        day_after = self.end_date + relativedelta(days=1)

        def _where_clause(product_ids):
            product_ids_str = ','.join([str(pid) for pid in product_ids if pid])
            return ' AND '.join([
                "ss.product_id in (%s)" % product_ids_str,
                "ss.date_done > '%s'" % day_before,
                "ss.date_done < '%s'" % day_after,
                "ut.usage_type in ('usage', 'scrap')",
                "ssr.state = 'validated'"
            ])

        def _stock_scrap(warehouse_data):
            product_ids = [o['product_id'] for o in warehouse_data.values()]
            self._cr.execute('''SELECT
                ut.usage_type, ss.product_id, sum(ss.scrap_qty) as scrap_qty, ss.product_uom_id
            FROM
                stock_scrap ss
            LEFT JOIN
                stock_scrap_request ssr ON (ssr.id = ss.scrap_id)
            LEFT JOIN
                usage_type ut ON (ut.id = ssr.scrap_type)
            WHERE
                %s
            GROUP BY
                ut.usage_type, ss.product_id, ss.product_uom_id''' % _where_clause(product_ids))

            records = self._cr.dictfetchall()
            scraps = {}
            usages = {}
            for x in records:
                uom_from = self.env['uom.uom'].search([('id', '=', x.get('product_uom_id'))])
                product_id = self.env['product.product'].browse(x['product_id'])
                if x['usage_type'] == 'scrap':
                    if uom_from and product_id:
                        converted_qty = uom_from._compute_quantity(x.get('scrap_qty', 0.0), product_id.uom_id)

                        if x['product_id'] in scraps:
                            scraps[x['product_id']] += converted_qty
                        else:
                            scraps[x['product_id']] = converted_qty

                if x['usage_type'] == 'usage':
                    if uom_from and product_id:
                        converted_qty = uom_from._compute_quantity(x.get('scrap_qty', 0.0), product_id.uom_id)

                        if x['product_id'] in usages:
                            usages[x['product_id']] += converted_qty
                        else:
                            usages[x['product_id']] = converted_qty
            # usages = {o['product_id']: o['scrap_qty'] for o in records if o['usage_type'] == 'usage'}
            # scraps = {o['product_id']: o['scrap_qty'] for o in records if o['usage_type'] == 'scrap'}
            return usages, scraps

        for (warehouse_id, warehouse_name), stock_data in warehouse_wise_stock_data.items():
            if not warehouse_id:
                continue

            usage_data, scrap_data = _stock_scrap(stock_data)

            for key, data in stock_data.items():
                product_id = self.env['product.product'].browse(data['product_id'])
                usage_qty = usage_data.get(product_id.id, 0.0)
                scrap_qty = scrap_data.get(product_id.id, 0.0)

                # ????????  
                if data.get('adjustment_out', 0.0) == 0.0:
                    adjustment_out = data.get('adjustment_out', 0.0)
                else:
                    adjustment_out = data.get('adjustment_out', 0.0)
                    if usage_qty > 0:
                        adjustment_out -= usage_qty
                    if scrap_qty > 0:
                        adjustment_out -= scrap_qty

                data.update({
                    'product_uom': product_id.uom_id.name,
                    'product_name': product_id.display_name,
                    'product_usage_quantity': usage_qty,
                    'product_scrap_quantity': scrap_qty,
                    'adjustment_out': adjustment_out
                })
        return warehouse_wise_stock_data

    def _add_valuations(self, warehouse_wise_stock_data):
        tommorow_of_end = self.end_date + relativedelta(days=1)
        warehouse_ids = [o[0] for o in warehouse_wise_stock_data.keys()]
        warehouse_ids_str = ','.join([str(wid) for wid in warehouse_ids if wid])

        def _svl_until(to_date, operator='<'):
            self._cr.execute('''SELECT
                warehouse_id, product_id, sum(value) as value
            FROM
                stock_valuation_layer
            WHERE
                create_date %s '%s' AND warehouse_id in (%s)
            GROUP BY
                warehouse_id, product_id''' % (operator, to_date, warehouse_ids_str))

            valuations = {}
            for o in self._cr.dictfetchall():
                if o['warehouse_id'] not in valuations:
                    valuations[o['warehouse_id']] = {o['product_id']: o['value']}
                else:
                    valuations[o['warehouse_id']][o['product_id']] = o['value']
            return valuations

        # start_date excluded
        opening_valuations = _svl_until(self.start_date)
        closing_valuations = _svl_until(tommorow_of_end)
        current_valuations = _svl_until(fields.Datetime.now(), operator='<=')

        for (warehouse_id, warehouse_name), stock_data in warehouse_wise_stock_data.items():
            if not warehouse_id:
                continue
            for key, data in stock_data.items():
                opening_value = opening_valuations.get(warehouse_id, {}).get(data['product_id'], 0.0)
                closing_value = closing_valuations.get(warehouse_id, {}).get(data['product_id'], 0.0)
                current_value = current_valuations.get(warehouse_id, {}).get(data['product_id'], 0.0)
                data.update({
                    'value': current_value,
                    'opening_value': opening_value,
                    'closing_value': closing_value,
                })
        return warehouse_wise_stock_data
    
    def _add_internal_transfer(self, warehouse_wise_stock_data):
        def _get_product_domain():
            if self.product_ids:
                product_ids = tuple(self.product_ids.ids + [0]) if len(self.product_ids) == 1 else tuple(self.product_ids.ids)
                return f'AND sm.product_id IN {product_ids}'
            return ''

        domain_product = _get_product_domain()

        def _execute_query(is_transfer_in=None, is_transfer_out=None, location_field=None, transfer_filter=False):
            base_query = f'''
                SELECT sm.product_qty, sm.product_id, sp.is_transfer_in, sp.is_transfer_out, 
                    sp.transfer_id, sw.id AS warehouse_id
                FROM stock_move AS sm
                JOIN stock_picking AS sp ON sm.picking_id = sp.id
                JOIN stock_location AS sl ON sp.{location_field} = sl.id
                JOIN stock_warehouse AS sw ON sl.warehouse_id = sw.id
                WHERE sm.create_date >= '{self.start_date} 00:00:00'
                AND sm.create_date < '{self.end_date} 23:59:59'
                AND sm.state = 'done'
                {domain_product}
            '''

            if transfer_filter:
                base_query += " AND sp.transfer_id IS NOT NULL AND sp.is_transfer_in IS NULL AND sp.is_transfer_out IS NULL"
            else:
                base_query += " AND (sp.is_transfer_in = %s OR sp.is_transfer_out = %s)"

            base_query += " ORDER BY sp.id DESC"

            params = (is_transfer_in, is_transfer_out) if not transfer_filter else ()
            self._cr.execute(base_query.format(location_field=location_field), params)
            return {o['warehouse_id']: {o['product_id']: {
                'internal_in': o['is_transfer_in'],
                'internal_out': o['is_transfer_out'],
                'product_qty': o['product_qty']
            }} for o in self._cr.dictfetchall()}

        
        def _get_transfer_values():
            return (
                _execute_query(is_transfer_in=False, is_transfer_out=True, location_field='location_id'),
                _execute_query(is_transfer_in=True, is_transfer_out=False, location_field='location_dest_id'),
                _execute_query(location_field='location_id', transfer_filter=True),
                _execute_query(location_field='location_dest_id', transfer_filter=True)
            )

        transit_values_out, transit_values_in, internal_values_out, internal_values_in = _get_transfer_values()

        for (warehouse_id, warehouse_name), stock_data in warehouse_wise_stock_data.items():
            if not warehouse_id:
                continue

            for key, data in stock_data.items():
                product_id = data['product_id']

                transit_out_data = transit_values_out.get(warehouse_id, {}).get(product_id, {})
                transit_in_data = transit_values_in.get(warehouse_id, {}).get(product_id, {})
                internal_out_data = internal_values_out.get(warehouse_id, {}).get(product_id, {})
                internal_in_data = internal_values_in.get(warehouse_id, {}).get(product_id, {})

                data.update({
                    'transit_in': transit_in_data.get('product_qty', 0.0),
                    'transit_out': transit_out_data.get('product_qty', 0.0),
                    'internal_in': internal_in_data.get('product_qty', 0.0),
                    'internal_out': internal_out_data.get('product_qty', 0.0),
                })

                data['closing'] = (
                    data['opening_stock'] - data['sales'] + data['sales_return'] + data['purchase'] - data['purchase_return']
                    + data['internal_in'] - data['internal_out'] + data['adjustment_in'] - data['adjustment_out']
                    + data['production_in'] - data['production_out'] + data['transit_in'] - data['transit_out']
                )

        return warehouse_wise_stock_data
    
    
    def write_cluster_sheet(self, workbook, warehouse_wise_stock_data):
        worksheet = self.create_excel_worksheet(workbook, self.cluster_area_id.display_name)
        to_merge = [
            'opening_stock',
            'sales',
            'sales_return',
            'purchase',
            'purchase_return',
            'internal_in',
            'internal_out',
            'product_usage_quantity',
            'product_scrap_quantity',
            'adjustment_in',
            'adjustment_out',
            'production_in',
            'production_out',
            'transit_in',
            'transit_out',
            'closing',
            'value',
            'opening_value',
            'closing_value'
        ]

        self.write_report_data_header(workbook, worksheet, 7, is_cluster=True)

        cluster_data = dict()
        for warehouse, stock_data_value in warehouse_wise_stock_data.items():
            for line in stock_data_value.values():
                product_id = line['product_id']
                if product_id not in cluster_data:
                    cluster_data[product_id] = line.copy()
                else:
                    for name in to_merge:
                        cluster_data[product_id][name] += line[name]
        self.write_data_to_worksheet(workbook, worksheet, False, cluster_data, self.start_date, self.end_date, row=7, counter=0)

    def download_report(self):
        if self.start_date > self.end_date:
            # swap date for whole process
            self.start_date, self.end_date = self.end_date, self.start_date
            self.is_date_swapped = True

        file_name = self.get_file_name()
        file_pointer = BytesIO()
        stock_data = self.get_product_stock_movements()
        warehouse_wise_stock_data = self.prepare_data_to_write(stock_data=stock_data)

        if not warehouse_wise_stock_data:
            return False

        warehouse_wise_stock_data = self._add_usage_scrap(warehouse_wise_stock_data)
        warehouse_wise_stock_data = self._add_valuations(warehouse_wise_stock_data)
        # warehouse_wise_stock_data = self._add_internal_transfer(warehouse_wise_stock_data)

        workbook = self.create_excel_workbook(file_pointer)
        if self.cluster_area_id:
            self.write_cluster_sheet(workbook, warehouse_wise_stock_data)

        for warehouse, stock_data_value in warehouse_wise_stock_data.items():
            warehouse_id, warehouse_name = warehouse
            if not warehouse_id:
                continue
            worksheet = self.create_excel_worksheet(workbook, warehouse_name)
            self.write_report_data_header(workbook, worksheet, 7)
            self.write_data_to_worksheet(workbook, worksheet, warehouse_id, stock_data_value, self.start_date, self.end_date, row=7, counter=0)

        # workbook.save(file_name)
        workbook.close()
        file_pointer.seek(0)
        file_data = base64.encodestring(file_pointer.read())
        self.write({'stock_file_data' : file_data})
        file_pointer.close()

        if self.is_date_swapped:
            # revert back date, in case user click download again for the same wizard record
            self.start_date, self.end_date = self.end_date, self.start_date
            self.is_date_swapped = False

        return {
            'name' : 'Stock Card Report',
            'type' : 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=setu.stock.movement.report&field=stock_file_data&id=%s&filename=%s'%(self.id, file_name),
            'target': 'self',
        }

    def get_product_date_wise(self, movement_data_value, start_date, end_date):
        product_id = movement_data_value.get('product_id')
        company_id = movement_data_value.get('company_id')
        product_category_id = movement_data_value.get('product_category_id')
        warehouse_id = movement_data_value.get('warehouse_id')
        lines_data = []
        while start_date <= end_date:
            query = """
                Select * from get_products_stock_movements('%s','%s','%s','%s','%s','%s')
            """%({company_id}, {product_id}, {product_category_id}, {warehouse_id}, start_date, start_date)
            self._cr.execute(query)
            stock_data = self._cr.dictfetchall()
            lines_data.append({
                'date': start_date,
                'data': stock_data
            })
            start_date += timedelta(days=1)
        return lines_data
