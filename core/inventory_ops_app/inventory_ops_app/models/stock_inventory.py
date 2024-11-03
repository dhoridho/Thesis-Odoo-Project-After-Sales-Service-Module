# -*- coding: utf-8 -*-
from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from datetime import datetime, date


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    # app_line_ids = fields.One2many('stock.inventory.line.app', 'inventory_id', string='Lines')

    def get_count_list(self, sort='id asc', filter=False, start_date=False, end_date=False):
        data_list = []
        color_dict = {'draft': '#82C7D2', 'confirm': '#92c422', 'completed': '#008000','to_approve': '#efb139', 'approved': '#008000',
                      'done': '#262628'}
        if filter == 'done':
            domain = [('state', '=', 'done'), ('create_date', '>=', start_date), ('create_date', '<=', end_date)]
        else:
            domain = [('state', 'not in', ['cancel', 'rejected', 'done'])]
        for inventory_id in self.env['stock.inventory'].search(domain, order=sort):
            vals = {}
            vals['id'] = inventory_id.id
            vals['inv_ref'] = inventory_id.inv_ref
            vals['name'] = inventory_id.name
            vals['state'] = dict(inventory_id.fields_get(['state'])['state']['selection'])[inventory_id.state]
            vals['date'] = str(inventory_id.create_date)

            if inventory_id.inventoried_product != False:
                vals['inventoried_product'] = dict(inventory_id.fields_get(['inventoried_product'])['inventoried_product']['selection'])[inventory_id.inventoried_product]
            else:
                vals['inventoried_product'] = ''

            vals['color'] = color_dict.get(inventory_id.state, '')

            location_list = [record.name_get()[0][1] for record in list(set(inventory_id.location_ids))]
            vals['locations'] = ", ".join(location_list)

            list_data = []
            for record in list(set(inventory_id.location_ids)):
                dict_vals = {}
                dict_vals['id'] = record.id
                dict_vals['name'] = record.name_get()[0][1]
                list_data.append(dict_vals)
            vals['location_ids'] = list_data
            vals['company_id'] = inventory_id.company_id.id

            if inventory_id.inventoried_product == 'specific_product':
                product_list = [record.name_get()[0][1] for record in list(set(inventory_id.product_ids))]
                vals['products'] = ", ".join(product_list)
            else:
                vals['products'] = ""

            if inventory_id.inventoried_product == 'specific_category':
                product_category_list = [record.name_get()[0][1] for record in list(set(inventory_id.product_categories))]
                vals['product_category'] = ", ".join(product_category_list)
            else:
                vals['product_category'] = ""
            data_list.append(vals)
        return data_list

    def get_count_data(self):
        data_list = []
        for line in self.line_ids:
            vals = {}
            vals['line_id'] = line.id
            vals['product_id'] = line.product_id.id
            vals['pack'] = line.package_id.name if line.package_id else ''
            vals['product'] = line.product_id.name
            vals['barcode'] = line.product_id.barcode or ''
            vals['item_no'] = line.product_id.default_code or ''
            vals['tracking'] = line.product_id.tracking
            vals['scanned_qty'] = line.product_qty
            vals['location_id'] = line.location_id.id
            vals['location'] = line.location_id.name_get()[0][1]
            vals['lot_name'] = line.prod_lot_id.name if line.prod_lot_id else ''
            vals['product_uom_id'] = line.product_uom_id.id
            vals['product_uom'] = line.product_uom_id.name
            vals['category_uom_id'] = line.product_id.uom_id.category_id.id if line.product_id.uom_id.category_id else 0
            vals['uom_id'] = line.uom_id.id if line.uom_id else 0
            vals['uom'] = line.uom_id.name if line.uom_id else ''
            data_list.append(vals)
        return data_list

    def create_stock_count_app(self, data_dict):
        vals = {}
        location_list = []
        analytic_groups_list = []
        product_list = []
        category_list = []
        vals['warehouse_id'] = data_dict.get('warehouse_id', False)
        vals['create_date'] = data_dict['count_date'] if data_dict.get('count_date', False) else str(datetime.now())[:19]
        location_list += [(int(record)) for record in data_dict['location_ids']]
        vals['location_ids'] = [(6,0,location_list)]
        analytic_groups_list += [(int(record)) for record in data_dict['analytic_tag_ids']]
        vals['analytic_tag_ids'] = [(6,0,analytic_groups_list)]
        vals['inventoried_product'] = data_dict['inventoried_product']
        vals['prefill_counted_quantity'] = 'zero'
        if data_dict.get('product_ids', False):
            product_list += [(int(record)) for record in data_dict['product_ids']]
            vals['product_ids'] = [(6, 0, product_list)]
        elif data_dict.get('product_category', False):
            category_list += [(int(record)) for record in data_dict['product_category']]
            vals['product_category'] = [(6, 0, category_list)]
        inventory_id = self.env['stock.inventory'].create(vals)

        vals2 = {}
        color_dict = {'draft': '#82C7D2', 'confirm': '#92c422', 'completed': '#008000', 'to_approve': '#efb139',
                      'approved': '#008000', 'done': '#262628'}
        if inventory_id:
            vals2['id'] = inventory_id.id
            vals2['inv_ref'] = inventory_id.inv_ref
            vals2['name'] = inventory_id.name
            vals2['state'] = dict(inventory_id.fields_get(['state'])['state']['selection'])[inventory_id.state]
            vals2['color'] = color_dict.get(inventory_id.state, '')
            vals2['date'] = str(inventory_id.create_date)
            vals2['inventoried_product'] = \
            dict(inventory_id.fields_get(['inventoried_product'])['inventoried_product']['selection'])[
                inventory_id.inventoried_product]
            location_list = [record.name_get()[0][1] for record in list(set(inventory_id.location_ids))]
            vals2['locations'] = ", ".join(location_list)

            list_data = []
            for record in list(set(inventory_id.location_ids)):
                dict_vals = {}
                dict_vals['id'] = record.id
                dict_vals['name'] = record.name_get()[0][1]
                list_data.append(dict_vals)
            vals2['location_ids'] = list_data
            vals2['company_id'] = inventory_id.company_id.id

            if inventory_id.inventoried_product == 'specific_product':
                product_list = [record.name_get()[0][1] for record in list(set(inventory_id.product_ids))]
                vals2['products'] = ", ".join(product_list)
            else:
                vals2['products'] = ""

            if inventory_id.inventoried_product == 'specific_category':
                product_category_list = [record.name_get()[0][1] for record in list(set(inventory_id.product_categories))]
                vals2['product_category'] = ", ".join(product_category_list)
            else:
                vals2['product_category'] = ""
        return vals2

    def action_app_confirm(self):
        error_message = 'success'
        try:
            self.action_start()
            # return error_message
            # line_list = []
            # for line in self.env['stock.inventory.line'].read_group(domain=[('inventory_id', '=', self.id)], fields=['product_id', 'location_id', 'package_id'], groupby=['location_id', 'product_id', 'package_id'], lazy=False):
            #     vals = {}
            #     vals['product_id'] = line['product_id'][0] if line['product_id'] else False
            #     vals['location_id'] = line['location_id'][0] if line['location_id'] else False
            #     vals['package_id'] = line['package_id'][0] if line['package_id'] else False
            #     line_list.append((0, 0, vals))
            # self.write({'app_line_ids': line_list})
            # return error_message
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'confirm': 'In Progress', 'completed': 'Completed',
                       'to_approve': 'Waiting for Approval', 'approved': 'Approved', 'done': 'Validated'}
        color_dict = {'draft': '#82C7D2', 'confirm': '#92c422', 'completed': '#008000', 'to_approve': '#efb139',
                      'approved': '#008000','done': '#262628'}
        return {'state': status_dict.get(self.state, ''), 'error_message': error_message, 'color': color_dict.get(self.state, '')}

    def action_app_cancel(self):
        error_message = 'success'
        try:
            self.action_cancel_draft()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'confirm': 'In Progress', 'completed': 'Completed',
                       'to_approve': 'Waiting for Approval', 'approved': 'Approved', 'done': 'Validated', 'cancel': 'Cancelled'}
        return {'state': status_dict.get(self.state, ''), 'error_message': error_message,}

    def action_app_request_for_approval(self):
        error_message = 'success'
        try:
            self.inv_request_for_approving()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        status_dict = {'draft': 'Draft', 'confirm': 'In Progress', 'completed': 'Completed',
                       'to_approve': 'Waiting for Approval', 'approved': 'Approved', 'done': 'Validated'}
        color_dict = {'draft': '#82C7D2', 'confirm': '#92c422', 'completed': '#008000', 'to_approve': '#efb139',
                      'approved': '#008000', 'done': '#262628'}
        return {'state': status_dict.get(self.state, ''), 'error_message': error_message, 'color': color_dict.get(self.state, '')}

    def action_app_validate(self):
        status_dict = {'draft': 'Draft', 'confirm': 'In Progress', 'completed': 'Completed',
                       'to_approve': 'Waiting for Approval', 'approved': 'Approved', 'done': 'Validated'}
        color_dict = {'draft': '#82C7D2', 'confirm': '#92c422', 'completed': '#008000', 'to_approve': '#efb139',
                      'approved': '#008000', 'done': '#262628'}
        try:
            if not self.exists():
                return {'error_message': False, 'state': status_dict.get(self.state, ''), 'color': color_dict.get(self.state, '')}
            self.write({'accounting_date': fields.Date.today()})
            self.action_validate()
            return {'error_message': True, 'state': status_dict.get(self.state, ''), 'color': color_dict.get(self.state, '')}
        except:
            self.env.cr.rollback()
            return {'error_message': False, 'state': status_dict.get(self.state, ''), 'color': color_dict.get(self.state, '')}

    def action_push_data(self, data_list):
        status_dict = {'draft': 'Draft', 'confirm': 'In Progress', 'completed': 'Completed',
                       'to_approve': 'Waiting for Approval', 'approved': 'Approved', 'done': 'Validated'}
        color_dict = {'draft': '#82C7D2', 'confirm': '#92c422', 'completed': '#008000', 'to_approve': '#efb139',
                      'approved': '#008000', 'done': '#262628'}
        try:
            for data in data_list:
                if data.get('line_id', False):
                    line_id = self.env['stock.inventory.line'].browse(data['line_id'])
                    if line_id:
                        line_id.write({'product_qty': data.get('qty', 0), 'uom_id': data.get('uom_id', False)})
            return {'error_message': 'True', 'state': status_dict.get(self.state, ''), 'color': color_dict.get(self.state, '')}
        except Exception as e:
            self.env.cr.rollback()
            return {'error_message': str(tools.ustr(e)).replace('\nNone', ''), 'state': status_dict.get(self.state, ''), 'color': color_dict.get(self.state, '')}
        
    # def action_app_inventory_adjustment(self):
    #     for line in self.app_line_ids:
    #         if line.product_id.tracking == 'none':
    #             inv_line = self.env['stock.inventory.line'].search([('product_id', '=', line.product_id.id), ('prod_lot_id', '=', False), ('location_id', '=', line.location_id.id), ('inventory_id', '=', self.id)], limit=1)
    #             if inv_line:
    #                 inv_line.write({'product_qty': inv_line.product_qty + line.count_qty})
    #             else:
    #                 line_vals = {}
    #                 line_vals['product_id'] = line.product_id.id
    #                 line_vals['prod_lot_id'] = False
    #                 line_vals['product_qty'] = line.count_qty
    #                 line_vals['location_id'] = line.location_id.id
    #                 line_vals['inventory_id'] = self.id
    #                 self.env['stock.inventory.line'].create(line_vals)
    #         else:
    #             for quant in line.quant_ids:
    #                 inv_line = self.env['stock.inventory.line'].search([('product_id', '=', line.product_id.id), ('prod_lot_id', '=', quant.lot_id.id if quant.lot_id else False), ('location_id', '=', line.location_id.id), ('inventory_id', '=', self.id)], limit=1)
    #                 if not inv_line:
    #                     line_vals = {}
    #                     line_vals['product_id'] = line.product_id.id
    #                     line_vals['prod_lot_id'] = quant.lot_id.id if quant.lot_id else False
    #                     line_vals['product_qty'] = 0
    #                     line_vals['location_id'] = line.location_id.id
    #                     line_vals['inventory_id'] = self.id
    #                     self.env['stock.inventory.line'].create(line_vals)
    #             for count_quant in line.count_lot_ids:
    #                 inv_line = self.env['stock.inventory.line'].search([('product_id', '=', line.product_id.id), ('prod_lot_id', '=', count_quant.lot_id.id if count_quant.lot_id else False), ('location_id', '=', line.location_id.id),('inventory_id', '=', self.id)])
    #                 if inv_line:
    #                     inv_line.write({'product_qty': inv_line.product_qty + count_quant.qty})
    #                 else:
    #                     line_vals = {}
    #                     line_vals['product_id'] = line.product_id.id
    #                     line_vals['prod_lot_id'] = count_quant.lot_id.id if count_quant.lot_id else False
    #                     line_vals['product_qty'] = count_quant.qty
    #                     line_vals['location_id'] = line.location_id.id
    #                     line_vals['inventory_id'] = self.id
    #                     self.env['stock.inventory.line'].create(line_vals)

    def action_app_complete(self):
        error_message = 'success'
        status_dict = {'draft': 'Draft', 'confirm': 'In Progress', 'completed': 'Completed',
                       'to_approve': 'Waiting for Approval', 'approved': 'Approved', 'done': 'Validated'}
        color_dict = {'draft': '#82C7D2', 'confirm': '#92c422', 'completed': '#008000', 'to_approve': '#efb139',
                      'approved': '#008000', 'done': '#262628'}
        try:
            self.action_complete()
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
        return {'state': status_dict.get(self.state, ''), 'error_message': error_message, 'color': color_dict.get(self.state, '')}

    def app_add_inventory_line(self,  line_dict):
        vals = {}
        error_message = 'success'
        try:
            product_id = self.env['product.product'].browse(line_dict.get('product_id', False))
            vals['product_id'] = line_dict.get('product_id', False)
            vals['location_id'] = line_dict.get('location_id', False)
            vals['prod_lot_id'] = line_dict.get('prod_lot_id', False)
            vals['package_id'] = line_dict.get('package_id', False)
            vals['product_qty'] = line_dict.get('product_qty', 0)
            vals['product_uom_id'] = product_id.uom_id.id if product_id.uom_id else False
            vals['uom_id'] = line_dict.get('uom_id', False)
            vals['inventory_id'] = line_dict.get('inventory_id', False)
            self.env['stock.inventory.line'].create(vals)
            return error_message
        except Exception as e:
            self.env.cr.rollback()
            error_message = tools.ustr(e)
            return error_message


StockInventory()

# class StockInventoryLineApp(models.Model):
#     _name = 'stock.inventory.line.app'
#     _description = 'Stock Inventory Line App'
#
#     inventory_id = fields.Many2one('stock.inventory', string='Stock Count')
#     state = fields.Selection(related='inventory_id.state', copy=False, store=True, string='Status')
#     location_id = fields.Many2one('stock.location', string='Location')
#     product_id = fields.Many2one('product.product', required=True, string='Product')
#     package_id = fields.Many2one(
#         'stock.quant.package', 'Pack', index=True, check_company=True,
#         domain="[('location_id', '=', location_id)]",
#     )
#     existing_qty = fields.Float(compute='compute_existing_qty', store=False, string='Existing Qty')
#     quant_ids = fields.Many2many('stock.quant', compute='_get_stock_quant', string='Quants')
#     count_qty = fields.Float(string='Count Quantity')
#     count_lot_ids = fields.One2many('stock.inventory.quant', 'count_line_id', string='Lot/Serial Nos')
#     tracking = fields.Selection(related='product_id.tracking', string='Tracking')
#
#     @api.depends('quant_ids', 'state', 'quant_ids.quantity', 'quant_ids.lot_id')
#     def compute_existing_qty(self):
#         for record in self:
#             record.existing_qty = sum([x.quantity for x in record.quant_ids])
#
#     @api.depends('product_id', 'state')
#     def _get_stock_quant(self):
#         for record in self:
#             if record.product_id:
#                 quant_ids = self.env['stock.quant'].search([('product_id', '=', record.product_id.id), ('location_id', '=', record.location_id.id), ('package_id', '=', record.package_id.id if record.package_id else False)]).ids
#             else:
#                 quant_ids = []
#             record.quant_ids = [(6, 0, quant_ids)]
#
#     @api.constrains('product_id', 'inventory_id', 'location_id', 'package_id')
#     def _check_product(self):
#         for record in self:
#             ids = self.env['stock.inventory.line.app'].search([('product_id', '=', record.product_id.id), ('inventory_id', '=', record.inventory_id.id), ('location_id', '=', record.location_id.id), ('package_id', '=', record.package_id.id if record.package_id else False)])
#             if len(ids) > 1:
#                 raise ValidationError('Duplicate Products is not allowed.')
#
#     def find_lot_number(self, lot_name):
#         self.ensure_one()
#         lot_id = self.env['stock.production.lot'].search([('product_id', '=', self.product_id.id), ('name', '=', lot_name)], limit=1)
#         if lot_id:
#             vals = {}
#             vals['lot_name'] = lot_id.name
#             return vals
#         else:
#             return {}
#
#     def action_recount(self):
#         for record in self:
#             record.count_qty = 0
#             record.count_lot_ids.unlink()
#
#     def view_existing_data(self):
#         return {
#             'name': 'Lot/Serial Numbers',
#             'type': 'ir.actions.act_window',
#             'view_type': 'form',
#             'view_mode': 'form',
#             'view_id': self.env['ir.model.data'].xmlid_to_res_id('inventory_ops_app.stock_count_lot_form'),
#             'res_model': 'stock.inventory.line.app',
#             'target': 'new',
#             'res_id': self.ids[0],
#         }
#
#     def view_count_data(self):
#         if self.tracking == 'none':
#             view_id = self.env['ir.model.data'].xmlid_to_res_id('inventory_ops_app.stock_count_lot_form3')
#         else:
#             view_id = self.env['ir.model.data'].xmlid_to_res_id('inventory_ops_app.stock_count_lot_form2')
#         return {
#             'name': 'Lot/Serial Numbers',
#             'type': 'ir.actions.act_window',
#             'view_type': 'form',
#             'view_mode': 'form',
#             'view_id': view_id,
#             'res_model': 'stock.inventory.line.app',
#             'target': 'new',
#             'res_id': self.ids[0],
#         }
#
#     def save(self):
#         return {'type': 'ir.actions.act_window_close'}
#
#     def action_cancel(self):
#         for record in self:
#             record.write({'state': 'cancel'})
#             if all(x.state == 'cancel' for x in record.inventory_id.line_ids):
#                 record.inventory_id.action_cancel()
#
# StockInventoryLineApp()
#
#
# class StockInventoryQuant(models.Model):
#     _name = 'stock.inventory.quant'
#     _description = 'Stock Count Quant'
#     _rec_name = 'product_id'
#     _order = 'id desc'
#
#     count_line_id = fields.Many2one('stock.inventory.line.app', string='Count Line')
#     product_id = fields.Many2one('product.product', required=True, string='Product')
#     lot_id = fields.Many2one('stock.production.lot', required=False, string='Lot/Serial No')
#     qty = fields.Float()
#
#
# StockInventoryQuant()