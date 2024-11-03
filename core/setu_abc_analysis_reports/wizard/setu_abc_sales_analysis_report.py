from odoo import fields, models, api, _

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_abc_analysis_reports.library import xlsxwriter

from . import setu_excel_formatter
import base64
from io import BytesIO
from datetime import datetime

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    date_order = fields.Datetime(string='Order Date', related='order_id.date_order', store=True)

class SetuABCSalesAnalysisReport(models.TransientModel):
    _name = 'setu.abc.sales.analysis.report'
    _description = """
        ABC Sales Analysis Report / ABC Analysis Report
        Based ABC-analysis – is the famous Pareto principle, which states that 20% of efforts give 80% of the result.    
    """

    stock_file_data = fields.Binary('Stock Movement File')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    company_ids = fields.Many2many("res.company", string="Companies")
    product_category_ids = fields.Many2many("product.category", string="Product Categories")
    product_ids = fields.Many2many("product.product", string="Products")
    warehouse_ids = fields.Many2many("stock.warehouse", string="Warehouses")
    abc_analysis_type = fields.Selection([('all', 'All'),
                                          ('high_sales', 'High Sales (A)'),
                                          ('medium_sales', 'Medium Sales (B)'),
                                          ('low_sales', 'Low Sales (C)')], "ABC Classification", default="all")

    @api.onchange('product_category_ids')
    def onchange_product_category_id(self):
        if self.product_category_ids:
            return {'domain': {'product_ids': [('categ_id', 'child_of', self.product_category_ids.ids)]}}

    @api.onchange('company_ids')
    def onchange_company_id(self):
        if self.company_ids:
            return {'domain': {'warehouse_ids': [('company_id', 'child_of', self.company_ids.ids)]}}

    def get_file_name(self):
        filename = "abc_sales_analysis_report.xlsx"
        return filename

    def create_excel_workbook(self, file_pointer):
        workbook = xlsxwriter.Workbook(file_pointer)
        return workbook

    def create_excel_worksheet(self, workbook, sheet_name):
        worksheet = workbook.add_worksheet(sheet_name)
        worksheet.set_default_row(22)
        # worksheet.set_border()
        return worksheet

    def set_column_width(self, workbook, worksheet):
        worksheet.set_column(0, 1, 25)
        worksheet.set_column(2, 6, 16)

    def set_format(self, workbook, wb_format):
        wb_new_format = workbook.add_format(wb_format)
        wb_new_format.set_border()
        return wb_new_format

    def set_report_title(self, workbook, worksheet):
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_TITLE_CENTER)
        worksheet.merge_range(0, 0, 1, 6, "ABC Sales Analysis Report", wb_format)
        wb_format_left = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        wb_format_center = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)

        worksheet.write(2, 0, "Sales Start Date", wb_format_left)
        worksheet.write(3, 0, "Sales End Date", wb_format_left)

        wb_format_center = self.set_format(workbook, {'num_format': 'dd/mm/yy', 'align': 'center', 'bold': True,
                                                      'font_color': 'red'})
        worksheet.write(2, 1, self.start_date, wb_format_center)
        worksheet.write(3, 1, self.end_date, wb_format_center)

    def get_abc_sales_analysis_report_data(self):
        """
        :return:
        """
        start_date = datetime(self.start_date.year, self.start_date.month, self.start_date.day)
        end_date = datetime(self.end_date.year, self.end_date.month, self.end_date.day).strftime("%Y-%m-%d 23:59:59")
        category_ids = company_ids = {}
        self.env.cr.execute("""
            SELECT id
            FROM sale_order_line
            WHERE (is_down_payment = True or is_downpayment = True or is_delivery = True or is_promotion_product_line = True or is_reward_line = True or is_service = True or discount_line = True) AND date_order >= '%s' AND date_order <= '%s' AND state in ('sale','done')
        """ % (start_date, end_date))
        so_line = self.env.cr.fetchall()
        so_line = list(sum(so_line, ()))
        except_line = set(so_line) or {}
        if self.product_category_ids:
            categories = self.env['product.category'].search([('id', 'child_of', self.product_category_ids.ids)])
            category_ids = set(categories.ids) or {}
        products = self.product_ids and set(self.product_ids.ids) or {}
        if self.company_ids:
            companies = self.env['res.company'].search([('id', 'child_of', self.company_ids.ids)])
            company_ids = set(companies.ids) or {}
        else:
            company_ids = set(self.env.context.get('allowed_company_ids', False) or self.env.user.company_ids.ids) or {}

        warehouses = self.warehouse_ids and set(self.warehouse_ids.ids) or {}

        # get_products_overstock_data(company_ids, product_ids, category_ids, warehouse_ids, start_date, end_date, advance_stock_days)
        query = """
                Select * from get_abc_sales_analysis_data('%s','%s','%s','%s','%s','%s', '%s', '%s')
            """ % (company_ids, products, category_ids, warehouses, self.start_date, self.end_date, self.abc_analysis_type, except_line)
        # print(query)
        self._cr.execute(query)
        sales_data = self._cr.dictfetchall()
        return sales_data

    def prepare_data_to_write(self, stock_data={}):
        """

        :param stock_data:
        :return:
        """
        warehouse_wise_data = {}
        for data in stock_data:
            product_id = self.env['product.product'].browse([data.get('product_id')])
            key = (data.get('warehouse_id'), data.get('warehouse_name'))
            if not warehouse_wise_data.get(key, False):
                warehouse_wise_data[key] = {data.get('product_id'): data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id'): data})
            data.update({
                'product_name': product_id.display_name,
            })
        return warehouse_wise_data

    def download_report(self):
        file_name = self.get_file_name()
        file_pointer = BytesIO()
        stock_data = self.get_abc_sales_analysis_report_data()
        warehouse_wise_analysis_data = self.prepare_data_to_write(stock_data=stock_data)
        if not warehouse_wise_analysis_data:
            return False
        workbook = self.create_excel_workbook(file_pointer)
        for stock_data_key, stock_data_value in warehouse_wise_analysis_data.items():
            sheet_name = stock_data_key[1]
            wb_worksheet = self.create_excel_worksheet(workbook, sheet_name)
            row_no = 5
            self.write_report_data_header(workbook, wb_worksheet, row_no)
            for abc_data_key, abc_data_value in stock_data_value.items():
                row_no = row_no + 1
                self.write_data_to_worksheet(workbook, wb_worksheet, abc_data_value, row=row_no)

        # workbook.save(file_name)
        workbook.close()
        file_pointer.seek(0)
        file_data = base64.encodestring(file_pointer.read())
        self.write({'stock_file_data': file_data})
        file_pointer.close()

        return {
            'name': 'ABC Sales Analysis Report',
            'type': 'ir.actions.act_url',
            'url': '/web/binary/download_document?model=setu.abc.sales.analysis.report&field=stock_file_data&id=%s&filename=%s' % (
                self.id, file_name),
            'target': 'self',
        }

    def download_report_in_listview(self):
        stock_data = self.get_abc_sales_analysis_report_data()
        #print(stock_data)
        for abc_data_value in stock_data:
            abc_data_value['wizard_id'] = self.id
            self.create_data(abc_data_value)

        graph_view_id = self.env.ref('setu_abc_analysis_reports.setu_abc_sales_analysis_bi_report_graph').id
        tree_view_id = self.env.ref('setu_abc_analysis_reports.setu_abc_sales_analysis_bi_report_tree').id
        is_graph_first = self.env.context.get('graph_report', False)
        report_display_views = []
        viewmode = ''
        if is_graph_first:
            report_display_views.append((graph_view_id, 'graph'))
            report_display_views.append((tree_view_id, 'tree'))
            viewmode = "graph,tree"
        else:
            report_display_views.append((tree_view_id, 'tree'))
            report_display_views.append((graph_view_id, 'graph'))
            viewmode = "tree,graph"
        return {
            'name': _('ABC Sales Analysis'),
            'domain': [('wizard_id', '=', self.id)],
            'res_model': 'setu.abc.sales.analysis.bi.report',
            'view_mode': viewmode,
            'type': 'ir.actions.act_window',
            'views': report_display_views,
        }

    def create_data(self, data):
        del data['company_name']
        del data['product_name']
        del data['warehouse_name']
        del data['category_name']
        return self.env['setu.abc.sales.analysis.bi.report'].create(data)

    def write_report_data_header(self, workbook, worksheet, row):
        self.set_report_title(workbook, worksheet)
        self.set_column_width(workbook, worksheet)
        wb_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_CENTER)
        wb_format.set_text_wrap()
        worksheet.set_row(row, 30)
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_BOLD_RIGHT)
        odd_normal_right_format.set_text_wrap()
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_BOLD_RIGHT)
        even_normal_right_format.set_text_wrap()
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_BOLD_LEFT)
        normal_left_format.set_text_wrap()

        worksheet.write(row, 0, 'Product Name', normal_left_format)
        worksheet.write(row, 1, 'Category', normal_left_format)
        worksheet.write(row, 2, 'Sales Qty', odd_normal_right_format)
        worksheet.write(row, 3, 'Sales Amount', even_normal_right_format)
        worksheet.write(row, 4, 'Sales Amount (%)', odd_normal_right_format)
        worksheet.write(row, 5, 'Cum. Sales Amount (%)', even_normal_right_format)
        worksheet.write(row, 6, 'ABC Classification', odd_normal_right_format)
        return worksheet

    def write_data_to_worksheet(self, workbook, worksheet, data, row):
        # Start from the first cell. Rows and
        # columns are zero indexed.
        odd_normal_right_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_right_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_RIGHT)
        even_normal_center_format = self.set_format(workbook, setu_excel_formatter.EVEN_FONT_MEDIUM_NORMAL_CENTER)
        odd_normal_left_format = self.set_format(workbook, setu_excel_formatter.ODD_FONT_MEDIUM_NORMAL_LEFT)
        normal_left_format = self.set_format(workbook, setu_excel_formatter.FONT_MEDIUM_NORMAL_LEFT)

        worksheet.write(row, 0, data.get('product_name', ''), normal_left_format)
        worksheet.write(row, 1, data.get('category_name', ''), normal_left_format)
        worksheet.write(row, 2, data.get('sales_qty', ''), odd_normal_right_format)
        worksheet.write(row, 3, data.get('sales_amount', ''), even_normal_right_format)
        worksheet.write(row, 4, data.get('sales_amount_per', ''), odd_normal_right_format)
        worksheet.write(row, 5, data.get('cum_sales_amount_per', ''), even_normal_right_format)
        worksheet.write(row, 6, data.get('analysis_category', ''), odd_normal_right_format)
        return worksheet


class SetuABCSalesAnalysisBIReport(models.TransientModel):
    _name = 'setu.abc.sales.analysis.bi.report'
    _description = """It helps to organize ABC sales analysis data in listview and graphview"""

    product_id = fields.Many2one("product.product", "Product")
    product_category_id = fields.Many2one("product.category", "Category")
    warehouse_id = fields.Many2one("stock.warehouse")
    company_id = fields.Many2one("res.company", "Company")
    sales_qty = fields.Float("Total Sales")
    sales_amount = fields.Float("Total Sales Amount")
    total_orders = fields.Float("Total Orders")
    sales_amount_per = fields.Float("Total Sales Amount (%)")
    cum_sales_amount_per = fields.Float("Cumulative Total Sales Amount (%)")
    analysis_category = fields.Char("ABC Classification")
    wizard_id = fields.Many2one("setu.abc.sales.analysis.report")
    # sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')

