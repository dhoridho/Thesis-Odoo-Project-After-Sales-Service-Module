# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from datetime import datetime, date
from odoo.exceptions import ValidationError


class StockCount(models.Model):
    _name = 'stock.count'
    _inherit = ['mail.thread']
    _description = 'Stock Count'
    _order = 'id desc'

    name = fields.Char('Reference', copy=False, default='/', required=True)
    state = fields.Selection(
        [('open', 'Open'), ('cancel', 'Cancelled'), ('in_progress', 'In Progress'), ('close', 'Closed')], copy=False,
        track_visibility='onchange', default='open', string='Status')
    count_date = fields.Date('Count Date', copy=False, default=date.today())
    remarks = fields.Text('Notes')

    inventoried_product = fields.Selection([
        ('all_product', 'All Products'),('specific_product', 'Specific Products'),
        ('specific_category', 'Specific Categories')], default='all_product', string='Inventoried Product')

    product_ids = fields.Many2many('product.product', string='Products',
                  domain="[('type', '=', 'product'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    product_category = fields.Many2many('product.category', string="Product Category")

    line_ids = fields.One2many('stock.count.line', 'count_id', string='Lines')
    product = fields.Char(compute='_compute_product', search='_search_by_product', string='Product')
    inv_id = fields.Many2one('stock.inventory', copy=False, string='Inventory Adjustment')

    company_id = fields.Many2one('res.company', 'Company', readonly=True, index=True, required=True,
                 states={'draft': [('readonly', False)]}, default=lambda self: self.env.company)

    user_id = fields.Many2one('res.users', string="Responsible", tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", tracking=True, required=True)
    location_ids = fields.Many2many('stock.location', required=True, string='Locations', domain="[('company_id', '=', company_id), ('usage', 'in', ['internal', 'transit'])]")

    branch_id = fields.Many2one('res.branch', string="Branch", related='warehouse_id.branch_id', tracking=True)

    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Groups',
                                        default=lambda self: self.env.user.analytic_tag_ids.ids)
    is_analytic_mandatory = fields.Boolean(compute='compute_is_analytic_mandatory')
    is_analytic_readonly_dup = fields.Boolean(compute="compute_is_analytic_readonly", default=True)

    @api.depends('is_analytic_readonly_dup')
    def compute_is_analytic_mandatory(self):
        user = self.env.user
        for record in self:
            if user.has_group('analytic.group_analytic_tags'):
                record.is_analytic_mandatory = True
            else:
                record.is_analytic_mandatory = False

    def compute_is_analytic_readonly(self):
        for record in self:
            group_allow_validate_inventory_adjustment = self.env['ir.config_parameter'].sudo().get_param(
                'is_inventory_adjustment_with_value', False)
            if not group_allow_validate_inventory_adjustment:
                record.is_analytic_readonly_dup = False
            else:
                record.is_analytic_readonly_dup = True

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.count')
        return super(StockCount, self).create(vals)

    def create_stock_count_app(self, data_dict):
        vals = {}
        location_list = []
        analytic_groups_list = []
        product_list = []
        category_list = []
        vals['warehouse_id'] = data_dict.get('warehouse_id', False)
        vals['count_date'] = data_dict['count_date'] if data_dict.get('count_date', False) else str(datetime.now())[:19]
        location_list += [(int(record)) for record in data_dict['location_ids']]
        vals['location_ids'] = [(6,0,location_list)]
        analytic_groups_list += [(int(record)) for record in data_dict['analytic_tag_ids']]
        vals['analytic_tag_ids'] = [(6,0,analytic_groups_list)]
        vals['inventoried_product'] = data_dict['inventoried_product']
        if data_dict.get('product_ids', False):
            product_list += [(int(record)) for record in data_dict['product_ids']]
            vals['product_ids'] = [(6, 0, product_list)]
        elif data_dict.get('product_category', False):
            category_list += [(int(record)) for record in data_dict['product_category']]
            vals['product_category'] = [(6, 0, category_list)]
        self.env['stock.count'].create(vals)
        return True

    def get_count_list(self, sort='id asc', filter=False, start_date=False, end_date=False):
        data_list = []
        color_dict = {'open': '#82C7D2', 'in_progress': '#008000', 'close': '#262628'}
        if filter == 'close':
            domain = [('state', '=', 'close'), ('count_date', '>=', start_date), ('count_date', '<=', end_date)]
        else:
            domain = [('state', 'in', ['open', 'in_progress'])]
        for count_id in self.env['stock.count'].search(domain, order=sort):
            vals = {}
            vals['id'] = count_id.id
            vals['name'] = count_id.name
            vals['state'] = dict(count_id.fields_get(['state'])['state']['selection'])[count_id.state]
            vals['date'] = str(count_id.count_date)
            vals['inventoried_product'] = dict(count_id.fields_get(['inventoried_product'])['inventoried_product']['selection'])[count_id.inventoried_product]
            vals['color'] = color_dict.get(count_id.state, '')

            location_list = [record.name_get()[0][1] for record in list(set(count_id.location_ids))]
            vals['locations'] = ", ".join(location_list)

            product_list = [record.name_get()[0][1] for record in list(set(count_id.product_ids))]
            vals['products'] = ", ".join(product_list)

            product_category_list = [record.name_get()[0][1] for record in list(set(count_id.product_category))]
            vals['product_category'] = ", ".join(product_category_list)
            data_list.append(vals)
        return data_list

    def get_count_data(self):
        data_list = []
        for line in self.line_ids:
            vals = {}
            vals['line_id'] = line.id
            vals['product_id'] = line.product_id.id
            vals['product'] = line.product_id.name
            vals['barcode'] = line.product_id.barcode or ''
            vals['item_no'] = line.product_id.default_code or ''
            vals['tracking'] = line.product_id.tracking
            vals['scanned_qty'] = line.count_qty
            vals['location_id'] = line.location_id.id
            vals['location'] = line.location_id.name_get()[0][1]
            vals['scanned_list'] = []
            if line.product_id.tracking != 'none':
                vals['scanned_list'] = [{'lot_name': x.lot_id.name if x.lot_id else '', 'qty': x.qty} for x in
                                        line.count_lot_ids]
            data_list.append(vals)
        return data_list

    def action_push_data(self, data_list):
        try:
            for data in data_list:
                if data.get('line_id', False):
                    line_id = self.env['stock.count.line'].browse(data['line_id'])
                else:
                    line_id = self.env['stock.count.line'].create(
                        {'count_id': self.id, 'product_id': data.get('product_id')})
                line_id.count_lot_ids.unlink()
                scanned_list = []
                if line_id.product_id.tracking != 'none':
                    for lot_dict in data.get('scanned_data', []):
                        if lot_dict.get('qty', 0):
                            vals = {}
                            lot_id = self.env['stock.production.lot'].search(
                                [('product_id', '=', line_id.product_id.id),
                                 ('name', '=', lot_dict.get('lot_name', ''))], limit=1)
                            if not lot_id:
                                lot_id = self.env['stock.production.lot'].create(
                                    {'name': lot_dict.get('lot_name', ''), 'product_id': line_id.product_id.id})
                            vals['product_id'] = line_id.product_id.id
                            vals['lot_id'] = lot_id.id
                            vals['qty'] = lot_dict.get('qty', 0)
                            scanned_list.append((0, 0, vals))
                line_id.write({'count_qty': data.get('qty', 0), 'count_lot_ids': scanned_list})
            return 'True'
        except Exception as e:
            self.env.cr.rollback()
            return str(tools.ustr(e)).replace('\nNone', '')

    @api.onchange('inventoried_product')
    def onchange_inventoried_product(self):
        if self.inventoried_product == 'all_product':
            self.product_ids = False
            self.product_category = False
        else:
            if self.inventoried_product != 'specific_product':
                self.product_ids = False
            if self.inventoried_product != 'specific_category':
                self.product_category = False

    def action_confirm(self):
        error_message = 'success'
        try:
            product_list = []
            if self.inventoried_product == 'all_product':
                product_list += [product_id.id for product_id in self.env['product.product'].search([])]
            else:
                if self.inventoried_product == 'specific_category':
                    product_list += [product_id.id for product_id in self.env['product.product'].search(
                        [('categ_id', 'in', self.product_category.ids)])]
                elif self.inventoried_product == 'specific_product':
                    product_list += self.product_ids.ids
            vals = {}
            vals['state'] = 'in_progress'
            line_list = []
            for location_id in self.location_ids.ids:
                line_list += [(0, 0, {'product_id': product_id, 'location_id': location_id}) for product_id in
                              list(set(product_list))]
            vals['line_ids'] = line_list
            self.write(vals)
            return error_message
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
            return error_message

    def action_done(self):
        error_message = 'success'
        try:
            self.action_inventory_adjustment()
            self.inv_id.action_complete()
            self.inv_id.action_validate()
            self.write({'state': 'close'})
            return error_message
        except Exception as e:
            error_message = tools.ustr(e)
            self.env.cr.rollback()
            return error_message

    def action_recount(self):
        for record in self:
            record.line_ids.action_recount()
        return True

    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    def action_inventory_adjustment(self):
        vals = {}
        vals['name'] = 'INV ADJUST: ' + self.name
        vals['create_date'] = str(datetime.now())
        vals['warehouse_id'] = self.warehouse_id.id
        vals['location_ids'] = [(6, 0, self.location_ids.ids)]
        vals['company_id'] = self.env.user.company_id.id
        vals['inventoried_product'] = self.inventoried_product
        vals['product_categories'] = [(6, 0, self.product_category.ids)]
        vals['product_ids'] = [(6, 0, self.product_ids.ids)]
        vals['analytic_tag_ids'] = [(6, 0, self.analytic_tag_ids.ids)]
        vals['prefill_counted_quantity'] = 'zero'
        inv_id = self.env['stock.inventory'].create(vals)
        self.write({'inv_id': inv_id.id})
        inv_id.action_start()
        for line in self.line_ids:
            if line.product_id.tracking == 'none':
                inv_line = self.env['stock.inventory.line'].search([('product_id', '=', line.product_id.id), ('prod_lot_id', '=', False), ('location_id', '=', line.location_id.id), ('inventory_id', '=', inv_id.id)])
                if inv_line:
                    inv_line.write({'product_qty': inv_line.product_qty + line.count_qty})
                else:
                    line_vals = {}
                    line_vals['product_id'] = line.product_id.id
                    line_vals['prod_lot_id'] = False
                    line_vals['product_qty'] = line.count_qty
                    line_vals['location_id'] = line.location_id.id
                    line_vals['inventory_id'] = inv_id.id
                    self.env['stock.inventory.line'].create(line_vals)
            else:
                for quant in line.quant_ids:
                    inv_line = self.env['stock.inventory.line'].search([('product_id', '=', line.product_id.id), ('prod_lot_id', '=', quant.lot_id.id if quant.lot_id else False), ('location_id', '=', line.location_id.id), ('inventory_id', '=', inv_id.id)])
                    if not inv_line:
                        line_vals = {}
                        line_vals['product_id'] = line.product_id.id
                        line_vals['prod_lot_id'] = quant.lot_id.id if quant.lot_id else False
                        line_vals['product_qty'] = 0
                        line_vals['location_id'] = line.location_id.id
                        line_vals['inventory_id'] = inv_id.id
                        self.env['stock.inventory.line'].create(line_vals)
                for count_quant in line.count_lot_ids:
                    inv_line = self.env['stock.inventory.line'].search([('product_id', '=', line.product_id.id), ('prod_lot_id', '=', count_quant.lot_id.id if count_quant.lot_id else False), ('location_id', '=', line.location_id.id),('inventory_id', '=', inv_id.id)])
                    if inv_line:
                        inv_line.write({'product_qty': inv_line.product_qty + count_quant.qty})
                    else:
                        line_vals = {}
                        line_vals['product_id'] = line.product_id.id
                        line_vals['prod_lot_id'] = count_quant.lot_id.id if count_quant.lot_id else False
                        line_vals['product_qty'] = count_quant.qty
                        line_vals['location_id'] = line.location_id.id
                        line_vals['inventory_id'] = inv_id.id
                        self.env['stock.inventory.line'].create(line_vals)


    @api.onchange('warehouse_id')
    def set_domain_for_location_ids(self):
        location_ids = []
        final_location = []
        if self.warehouse_id:
            location_obj = self.env['stock.location']
            store_location_id = self.warehouse_id.view_location_id.id
            addtional_ids = location_obj.search(
                [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
            for location in addtional_ids:
                if location.location_id.id not in addtional_ids.ids:
                    location_ids.append(location.id)
            child_location_ids = self.env['stock.location'].search(
                [('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
            final_location = child_location_ids + location_ids
        res = {}
        res['domain'] = {'location_ids': [('id', 'in', final_location)]}
        return res


StockCount()


class StockCountLine(models.Model):
    _name = 'stock.count.line'
    _description = 'Stock Count Lines'

    count_id = fields.Many2one('stock.count', string='Stock Count')
    state = fields.Selection(related='count_id.state', copy=False, store=True, string='Status')
    location_id = fields.Many2one('stock.location', string='Location')
    product_id = fields.Many2one('product.product', required=True, string='Product')
    existing_qty = fields.Float(compute='compute_existing_qty', store=False, string='Existing Qty')
    quant_ids = fields.Many2many('stock.quant', compute='_get_stock_quant', string='Quants')
    count_qty = fields.Float(string='Count Quantity')
    count_lot_ids = fields.One2many('stock.count.quant', 'count_line_id', string='Lot/Serial Nos')
    tracking = fields.Selection(related='product_id.tracking', string='Tracking')

    @api.depends('quant_ids', 'state', 'quant_ids.quantity', 'quant_ids.lot_id')
    def compute_existing_qty(self):
        for record in self:
            record.existing_qty = sum([x.quantity for x in record.quant_ids])

    @api.depends('product_id', 'state')
    def _get_stock_quant(self):
        for record in self:
            if record.product_id:
                quant_ids = self.env['stock.quant'].search(
                    [('product_id', '=', record.product_id.id), ('location_id', '=', record.location_id.id)]).ids
            else:
                quant_ids = []
            record.quant_ids = [(6, 0, quant_ids)]

    @api.constrains('product_id', 'count_id', 'location_id')
    def _check_product(self):
        for record in self:
            ids = self.env['stock.count.line'].search(
              [('product_id', '=', record.product_id.id), ('count_id', '=', record.count_id.id), ('location_id', '=', record.location_id.id)])
            if len(ids) > 1:
                raise ValidationError('Duplicate Products is not allowed.')

    def find_lot_number(self, lot_name):
        self.ensure_one()
        lot_id = self.env['stock.production.lot'].search([('product_id', '=', self.product_id.id), ('name', '=', lot_name)], limit=1)
        if lot_id:
            vals = {}
            vals['lot_name'] = lot_id.name
            return vals
        else:
            return {}

    def action_recount(self):
        for record in self:
            record.count_qty = 0
            record.count_lot_ids.unlink()

    def view_existing_data(self):
        return {
            'name': 'Lot/Serial Numbers',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env['ir.model.data'].xmlid_to_res_id('inventory_ops_app.stock_count_lot_form'),
            'res_model': 'stock.count.line',
            'target': 'new',
            'res_id': self.ids[0],
        }

    def view_count_data(self):
        if self.tracking == 'none':
            view_id = self.env['ir.model.data'].xmlid_to_res_id('inventory_ops_app.stock_count_lot_form3')
        else:
            view_id = self.env['ir.model.data'].xmlid_to_res_id('inventory_ops_app.stock_count_lot_form2')
        return {
            'name': 'Lot/Serial Numbers',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'stock.count.line',
            'target': 'new',
            'res_id': self.ids[0],
        }

    def save(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})
            if all(x.state == 'cancel' for x in record.count_id.line_ids):
                record.count_id.action_cancel()

StockCountLine()


class StockCountQuant(models.Model):
    _name = 'stock.count.quant'
    _description = 'Stock Count Quant'
    _rec_name = 'product_id'
    _order = 'id desc'

    count_line_id = fields.Many2one('stock.count.line', string='Count Line')
    product_id = fields.Many2one('product.product', required=True, string='Product')
    lot_id = fields.Many2one('stock.production.lot', required=False, string='Lot/Serial No')
    qty = fields.Float()


StockCountQuant()
