# -*- coding: utf-8 -*-
from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def search_product(self, arg):
        product_id = self.env['product.product'].search([('barcode', '=', str(arg))], limit=1)
        if not product_id:
            product_id = self.env['product.product'].search([('default_code', '=', str(arg))], limit=1)
        product_list = []
        if product_id:
            vals = {}
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['item_no'] = product_id.default_code or ''
            vals['barcode'] = product_id.barcode or ''
            vals['tracking'] = product_id.tracking
            product_list.append(vals)
        else:
            for product_id in self.env['product.product'].search([('name', 'ilike', str(arg))]):
                vals = {}
                vals['product_id'] = product_id.id
                vals['product'] = product_id.name
                vals['item_no'] = product_id.default_code or ''
                vals['barcode'] = product_id.barcode or ''
                vals['tracking'] = product_id.tracking
                product_list.append(vals)
        return product_list

    def app_search_product(self, arg, company_id):
        product_id = self.env['product.product'].search([('barcode', '=', str(arg))], limit=1)
        if not product_id:
            product_id = self.env['product.product'].search([('default_code', '=', str(arg))], limit=1)
        product_list = []
        if product_id:
            vals = {}
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['barcode'] = product_id.barcode or ''
            vals['tracking'] = product_id.tracking
            vals['category_id'] = product_id.uom_id.category_id.id if product_id.uom_id.category_id else False

            list_lot_serial = []
            for record in self.env['stock.production.lot'].search([('product_id', '=', product_id.id), ('company_id', '=', company_id)]):
                lot_vals = {}
                lot_vals['id'] = record.id
                lot_vals['name'] = record.name
                list_lot_serial.append(lot_vals)
            vals['lot_serial_list'] = list_lot_serial
            product_list.append(vals)
        else:
            for product_id in self.env['product.product'].search([('name', 'ilike', str(arg))]):
                vals = {}
                vals['product_id'] = product_id.id
                vals['product'] = product_id.name
                vals['barcode'] = product_id.barcode or ''
                vals['tracking'] = product_id.tracking
                vals['category_id'] = product_id.uom_id.category_id.id if product_id.uom_id.category_id else False

                list_lot_serial = []
                for record in self.env['stock.production.lot'].search(
                        [('product_id', '=', product_id.id), ('company_id', '=', company_id)]):
                    lot_vals = {}
                    lot_vals['id'] = record.id
                    lot_vals['name'] = record.name
                    list_lot_serial.append(lot_vals)
                vals['lot_serial_list'] = list_lot_serial
                product_list.append(vals)
        return product_list

    def app_search_product_barcode(self, arg):
        product_id = self.env['product.product'].search([('barcode', '=', str(arg))], limit=1)
        product_list = []
        if product_id:
            vals = {}
            vals['product_id'] = product_id.id
            vals['product'] = product_id.name
            vals['item_no'] = product_id.default_code or ''
            vals['barcode'] = product_id.barcode or ''
            vals['tracking'] = product_id.tracking
            product_list.append(vals)
        return product_list