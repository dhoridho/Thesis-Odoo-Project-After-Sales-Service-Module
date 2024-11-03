# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from datetime import datetime
import xlwt
import xlrd
import base64
import tempfile
import os
from io import BytesIO
from xlrd import open_workbook, xldate_as_tuple
import tempfile
import binascii
import re
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import pytz
from dateutil import tz


class full_inv_adjustment_import(models.TransientModel):
    _name = 'full.inv.adjustment.import'
    _description = 'Full Inv Adjustment Import'

    import_type = fields.Selection([('inv_value', 'Inventory Value'), ('inv_stock', 'Inventory Stock'), (
        'inv_with_value', 'Inventory With Value')], string="For Adjustment", default='with_value')
    import_file = fields.Binary("Import File", required=True)
    import_name = fields.Char('Import Name', size=64)
    export_file = fields.Binary("Export File")
    export_name = fields.Char('Export Name', size=64)
    is_export = fields.Boolean('Export')

    def import_inv_adjustment(self):
        import_name_extension = self.import_name.split('.')[1]
        if import_name_extension not in ['xls', 'xlsx'] and self.import_type == 'inv_stock':
            raise ValidationError(
                'The upload file is using the wrong format. Please upload your Inventory Stock file in xlsx and xls format.')
        if import_name_extension not in ['xls', 'xlsx'] and self.import_type == 'inv_value':
            raise ValidationError(
                'The upload file is using the wrong format. Please upload your Inventory Adjustment file in xlsx and xls format.')
        if import_name_extension not in ['xls', 'xlsx'] and self.import_type == 'inv_with_value':
            raise ValidationError(
                'The upload file is using the wrong format. Please upload your Inventory Adjustment with Value file in xlsx and xls format.')

        workbook = open_workbook(
            file_contents=base64.decodestring(self.import_file))
        stock_inventory_id = False
        if self.import_type == 'inv_value':
            for sheet in workbook.sheets():
                vals = {'is_adj_value': False}
                location_ids = False
                for count in range(2, 7):
                    row = sheet.row_values(count)
                    if row[0] == 'Company' and row[1] != '':
                        company_id = self.env['res.company'].search(
                            [('name', '=', row[1])], limit=1)
                        vals['company_id'] = company_id.id
                    elif row[0] == 'Branch' and row[1] != '':
                        branch_id = self.env['res.branch'].search(
                            [('name', '=', row[1])], limit=1)
                        vals['branch_id'] = branch_id.id
                    elif row[0] == 'Warehouse' and row[1] != '':
                        warehouse_id = self.env['stock.warehouse'].search(
                            [('name', '=', row[1])], limit=1)
                        vals['warehouse_id'] = warehouse_id.id
                    elif row[0] == 'Locations' and row[1] != '':
                        location_ids = self.env['stock.location'].search(
                            [('location_display_name', '=', row[1])], limit=1)
                        vals['location_ids'] = [(6, 0, location_ids.ids)]
                    elif row[0] == 'Description' and row[1] != '':
                        vals['description'] = row[1]
                line_list = []
                product_ids = []
                for count in range(9, sheet.nrows):
                    line_vals = {}
                    lot = {}
                    line = sheet.row_values(count)
                    line_vals['sequence'] = line[0]
                    if line[1] != '':
                        product_id = self.env['product.product'].search(
                            [('product_display_name', '=', line[1])], limit=1)
                        line_vals['uom_id'] = product_id.product_tmpl_id.uom_id.category_id.id
                        if not product_id:
                            product_template_id = self.env['product.template'].search(
                                [('name', '=', line[1])], limit=1)
                            product_id = self.env['product.product'].search(
                                [('product_tmpl_id', '=', product_template_id.id)], limit=1)
                            line_vals['uom_id'] = product_id.uom_id.category_id.id or False
                        line_vals['product_id'] = product_id.id or false
                        product_ids.append(product_id.id)
                    if line[2] != '':
                        prod_lot_id = self.env['stock.production.lot'].search(
                            [('name', '=', line[2])], limit=1)
                        if prod_lot_id:
                            line_vals['prod_lot_id'] = prod_lot_id and prod_lot_id.id or False
                        else:
                            product_id = self.env['product.product'].search(
                                [('product_display_name', '=', line[1])], limit=1)
                            stock_production_lot_id = self.env['stock.production.lot'].create({
                                'name': line[2],
                                'company_id': company_id.id,
                                'product_id': product_id.id,
                                'product_qty': line[3],
                            })
                            line_vals['prod_lot_id'] = stock_production_lot_id.id
                    line_vals['product_qty'] = line[3]
                    line_vals['location_id'] = location_ids.id
                    line_vals['category_uom_id'] = product_id.uom_id.category_id.id
                    line_list.append((0, 0, line_vals))
                if len(vals.items()) > 0:
                    vals['line_ids'] = []
                    vals['date'] = datetime.now()
                    vals['inventoried_product'] = 'specific_product'
                    vals['state'] = 'confirm'
                    stock_inventory_id = self.env['stock.inventory'].create(
                        vals)
                    stock_inventory_id.write(
                        {'line_ids': line_list, 'product_ids': product_ids})
        elif self.import_type == 'inv_with_value':
            for sheet in workbook.sheets():
                vals = {'is_adj_value': True}
                location_ids = False
                for count in range(2, 7):
                    row = sheet.row_values(count)
                    if row[0] == 'Company' and row[1] != '':
                        company_id = self.env['res.company'].search(
                            [('name', '=', row[1])], limit=1)
                        vals['company_id'] = company_id.id
                    elif row[0] == 'Branch' and row[1] != '':
                        branch_id = self.env['res.branch'].search(
                            [('name', '=', row[1])], limit=1)
                        vals['branch_id'] = branch_id.id
                    elif row[0] == 'Warehouse' and row[1] != '':
                        warehouse_id = self.env['stock.warehouse'].search(
                            [('name', '=', row[1])], limit=1)
                        vals['warehouse_id'] = warehouse_id.id
                    elif row[0] == 'Locations' and row[1] != '':
                        location_ids = self.env['stock.location'].search(
                            [('location_display_name', 'ilike', row[1])], limit=1)
                        vals['location_ids'] = [(6, 0, location_ids.ids)]
                    elif row[0] == 'Description' and row[1] != '':
                        vals['description'] = row[1]
                line_list = []
                product_ids = []
                for count in range(9, sheet.nrows):
                    line_vals = {}
                    line = sheet.row_values(count)
                    line_vals['sequence'] = line[0]
                    if line[1] != '':
                        product_id = self.env['product.product'].search(
                            [('product_display_name', '=', line[1])], limit=1)
                        line_vals['product_id'] = product_id and product_id.id or False
                        product_ids.append(product_id.id)
                    if line[2] != '':
                        prod_lot_id = self.env['stock.production.lot'].search(
                            [('name', '=', line[2])], limit=1)
                        line_vals['prod_lot_id'] = prod_lot_id and prod_lot_id.id or False
                    line_vals['product_qty'] = line[4]
                    line_vals['unit_price'] = line[3]
                    line_vals['location_id'] = location_ids.id
                    line_list.append((0, 0, line_vals))
                if len(vals.items()) > 0:
                    vals['line_ids'] = []
                    vals['date'] = datetime.now()
                    vals['inventoried_product'] = 'specific_product'
                    vals['state'] = 'confirm'
                    stock_inventory_id = self.env['stock.inventory'].create(
                        vals)
                    stock_inventory_id.write(
                        {'line_ids': line_list, 'product_ids': [(6, 0, product_ids)]})
        elif self.import_type == 'inv_stock':
            for sheet in workbook.sheets():
                vals = {'is_adj_value': False}
                location_ids = False
                for count in range(2, 8):
                    row = sheet.row_values(count)
                    if row[0] == 'Company' and row[1] != '':
                        company_id = self.env['res.company'].search(
                            [('name', '=', row[1])], limit=1)
                        vals['company_id'] = company_id.id
                    elif row[0] == "Accounting Date" and row[1] != '':
                        y, m, d, h, i, s = xlrd.xldate_as_tuple(
                            row[1], workbook.datemode)
                        vals['accounting_date'] = datetime.strptime(
                            "{0}/{1}/{2}".format(m, d, y), '%m/%d/%Y')
                    elif row[0] == 'Branch' and row[1] != '':
                        branch_id = self.env['res.branch'].search(
                            [('name', '=', row[1])], limit=1)
                        vals['branch_id'] = branch_id.id
                    elif row[0] == 'Warehouse' and row[1] != '':
                        warehouse_id = self.env['stock.warehouse'].search(
                            [('name', '=', row[1])], limit=1)
                        vals['warehouse_id'] = warehouse_id.id
                    elif row[0] == 'Locations' and row[1] != '':
                        location_ids = self.env['stock.location'].search(
                            [('location_display_name', 'ilike', row[1])], limit=1)
                        vals['location_ids'] = [(6, 0, location_ids.ids)]
                    elif row[0] == 'Description' and row[1] != '':
                        vals['description'] = row[1]
                line_list = []
                product_ids = []
                adjustment_account_id = False
                for count in range(10, sheet.nrows):
                    line_vals = {}
                    line = sheet.row_values(count)
                    line_vals['sequence'] = line[0]
                    if line[1] != '':
                        product_id = self.env['product.product'].search(
                            [('product_display_name', '=', line[1])], limit=1)
                        line_vals['product_id'] = product_id and product_id.id or False
                        product_ids.append(product_id.id)
                    if line[2] != '':
                        uom_id = self.env['uom.uom'].search(
                            [('name', '=', line[2])], limit=1)
                        line_vals['uom_id'] = uom_id and uom_id.id or False
                    if line[3] != '':
                        location_id = self.env['stock.location'].search(
                            [('location_display_name', 'ilike', line[3])], limit=1)
                        line_vals['location_id'] = location_id and location_id.id or False
                    if line[4] != '':
                        prod_lot_id = self.env['stock.production.lot'].search(
                            [('name', '=', line[4])], limit=1)
                        line_vals['prod_lot_id'] = prod_lot_id and prod_lot_id.id or False
                    if line[5] != '':
                        package_id = self.env['stock.quant.package'].search(
                            [('name', '=', line[5])], limit=1)
                        line_vals['package_id'] = package_id and package_id.id or False
                    if line[6] != '':
                        owner_id = self.env['res.partner'].search(
                            [('name', '=', line[6])], limit=1)
                        line_vals['partner_id'] = owner_id and owner_id.id or False
                    line_vals['product_qty'] = line[7]
                    line_vals['unit_price'] = line[8]
                    if line[9] != '':
                        mylist = line[9].split(" ")
                        account_id = self.env['account.account'].search(
                            [('code', '=', mylist[0])], limit=1)
                        line_vals['adjustment_account_id'] = account_id and account_id.id or False
                        vals.update({'is_adj_value': True})
                        if count == 10:
                            adjustment_account_id = account_id.id
                    if 'product_id' in line_vals and line_vals.get('product_id'):
                        line_list.append((0, 0, line_vals))
                if len(vals.items()) > 0:
                    vals['line_ids'] = []
                    vals['date'] = datetime.now()
                    vals['inventoried_product'] = 'specific_product'
                    is_stock_count_approval = self.env['ir.config_parameter'].sudo(
                    ).get_param('is_stock_count_approval')
                    if is_stock_count_approval:
                        vals['state'] = 'approved'
                    else:
                        vals['state'] = 'completed'
                    vals['adjustment_account_id'] = adjustment_account_id
                    stock_inventory_id = self.env['stock.inventory'].create(
                        vals)
                    stock_inventory_id.write(
                        {'line_ids': line_list, 'product_ids': [(6, 0, product_ids)]})
        # return {
        #     'name': "Inventory Import",
        #     'view_type': 'tree',
        #     'view_mode': 'tree',
        #     'view_id': self.env.ref('stock.view_inventory_tree').id,
        #     'res_model': 'stock.inventory',
        #     'type': 'ir.actions.act_window',
        #     # 'res_id': stock_inventory_id.id,
        #     'target': 'new',
        # }
        tree_view_id = self.env['ir.model.data'].xmlid_to_res_id(
            'stock.view_inventory_tree')
        form_view_id = self.env['ir.model.data'].xmlid_to_res_id(
            'stock.view_inventory_form')
        return {
            'name': "Inventory Import",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.inventory',
            'views': [[tree_view_id, 'tree'], [form_view_id, 'form']],
            'context': {
                'active_model': 'stock.inventory',
                'active_id': stock_inventory_id.id}
        }

    def convert_to_utc(self, date):
        timezone_tz = 'Asia/Kolkata'
        if self.env.user and self.env.user.tz:
            timezone_tz = self.env.user.tz
        else:
            timezone_tz = 'Asia/Kolkata'
        date_from = datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT).replace(
            tzinfo=tz.gettz(timezone_tz)).astimezone(tz.tzutc())
        return date_from.strftime(DEFAULT_SERVER_DATETIME_FORMAT)


full_inv_adjustment_import()
