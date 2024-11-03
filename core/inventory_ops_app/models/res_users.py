# -*- coding: utf-8 -*-
from odoo import _, fields, models, api
from datetime import datetime


class ResUsers(models.Model):
    _inherit = "res.users"

    picking_date = fields.Datetime(string="Picking Date")
    picking_line_date = fields.Datetime(string="Picking Line Date")
    move_line_date = fields.Datetime(string="Move Line Date")
    stock_count_date = fields.Datetime(string="Count Date")
    stock_count_line_date = fields.Datetime(string="Count Line Date")
    is_auto_sync_check = fields.Boolean(string="Auto Sync App", compute="_compute_app_auto_sync")

    interwarehouse_request_date = fields.Datetime(string="Interwarehouse Request Date")
    interwarehouse_request_line_date = fields.Datetime(string="Interwarehouse Request Line Date")

    package_date = fields.Datetime(string="Stock Quant Package Date")
    package_line_date = fields.Datetime(string="Stock Quant Package Line Date")

    stock_quant_date = fields.Datetime(string="Stock Quant Date")

    # master record for dynamic sync in app
    product_date =  fields.Datetime(string="Product Date")
    partner_date =  fields.Datetime(string="Partner Date")
    stock_location_date =  fields.Datetime(string="Stock Location Date")
    res_branch_date =  fields.Datetime(string="Res Branch Date")
    stock_warehouse_date = fields.Datetime(string="Warehouse Date")
    product_category_date = fields.Datetime(string="Product Category Date")
    account_analytic_tag_date = fields.Datetime(string="Account Analytic Date")
    product_template_barcode_date = fields.Datetime(string="Product Template Barcode Date")
    stock_production_lot_date = fields.Datetime(string="Lot/Serial Number Date")
    stock_package_date = fields.Datetime(string="Package Date")

    # unlink field for dynamic sync in app
    stock_quant_unlink_data = fields.Char(string="Stock Quant Unlink")

    stock_count_unlink_data = fields.Char(string="Stock Count Unlink")
    stock_count_line_unlink_data = fields.Char(string="Stock Count Line Unlink")

    picking_unlink_data = fields.Char(string="Picking Unlink")
    picking_line_unlink_data = fields.Char(string="Picking Line Unlink")  # stock.move
    move_line_unlink_data = fields.Char(string="Move Line Unlink")  # stock.move.line

    interwarehouse_request_unlink_data = fields.Char(string="Interwarehouse Request Unlink")
    interwarehouse_line_request_unlink_data = fields.Char(string="Interwarehouse Request Line Unlink")

    package_unlink_data = fields.Char(string="Package Unlink")

    def _compute_app_auto_sync(self):
        check_sync = self.env['ir.config_parameter'].sudo().get_param('is_auto_sync')
        duration = self.env['ir.config_parameter'].sudo().get_param('duration')
        for record in self:
            record.is_auto_sync_check = check_sync




