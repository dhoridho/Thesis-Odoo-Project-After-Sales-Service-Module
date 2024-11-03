# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

from odoo import api, fields, models, _
from odoo.tools import float_is_zero
from itertools import groupby


class POSProductBom(models.Model):
    _name = 'pos.product.bom'
    _rec_name = "name"
    _description = 'POS Product Bom'

    product_id = fields.Many2one(
        'product.product', string='Product',
        required=True, domain=[('is_pos_bom', '=', True)])
    name = fields.Char(string='Reference', compute='_compute_structure_name')
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product Template',
        related='product_id.product_tmpl_id', readonly=False)
    product_qty = fields.Float(
        'Quantity', default=1.0, digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure', required=True)
    product_bom_line_ids = fields.One2many(
        'pos.product.bom.line', 'pos_bom_id', string='Product BoM Lines', copy=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, default='draft')
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)

    @api.depends('product_id')
    def _compute_structure_name(self):
        for product in self:
            if product.product_id:
                product.name = product.product_id.display_name + '-Structure'
            else:
                product.name = ' '

    @api.onchange('product_id')
    def onchange_product_name(self):
        for product in self:
            if product.product_id:
                product.product_uom_id = product.product_id.uom_id.id

    def set_to_draft(self):
        return self.write({'state': 'draft'})

    def confirm_bom(self):
        return self.write({'state': 'confirmed'})

    def cancel_bom(self):
        return self.write({'state': 'cancelled'})


class POSProductBomLine(models.Model):
    _name = 'pos.product.bom.line'
    _description = 'POS Product Bom Line'
    _rec_name = 'product_id'

    pos_bom_id = fields.Many2one(
        'pos.product.bom', string='Parent Product BoM',
        index=True, ondelete='cascade', required=True)
    product_id = fields.Many2one(
        'product.product', string='Component',
        domain="[('type', 'in', ['product', 'consu'])]")
    product_qty = fields.Float(
        string='Quantity', default=1.0,
        digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', string='Product Unit of Measure', required=True)

    @api.onchange('product_id')
    def onchange_product_name(self):
        for product in self:
            if product.product_id:
                product.product_uom_id = product.product_id.uom_id.id


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_pos_bom = fields.Boolean('Is POS BoM Product?')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_pos_bom = fields.Boolean(
        'Is POS BoM Product?', related="product_tmpl_id.is_pos_bom")
    product_bom_id = fields.One2many(
        'pos.product.bom', 'product_id', string='Product BOM Structure')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # OVERRIDE
    def _create_move_from_pos_order_lines(self, lines):
        self.ensure_one()
        lines_by_product = groupby(sorted(lines, key=lambda l: l.product_id.id), key=lambda l: l.product_id.id)
        for product, lines in lines_by_product:
            order_lines = self.env['pos.order.line'].concat(*lines)
            first_line = order_lines[0]
            current_move = self.env['stock.move'].create(
                self._prepare_stock_move_vals(first_line, order_lines)
            )
            if order_lines.product_id.is_pos_bom and order_lines.product_id.product_bom_id:
                for bom in order_lines.product_id.product_bom_id.product_bom_line_ids:
                    bom_order_lines = {
                        'name': bom.product_id.name,
                        'product_uom': bom.product_id.uom_id.id,
                        'picking_id': current_move.picking_id.id,
                        'picking_type_id': current_move.picking_type_id.id,
                        'product_id': bom.product_id.id,
                        'product_uom_qty': abs(bom.product_qty * order_lines.qty),
                        'quantity_done': abs(bom.product_qty * order_lines.qty),
                        'state': 'draft',
                        'location_id': current_move.location_id.id,
                        'location_dest_id': current_move.location_dest_id.id,
                        'company_id': current_move.company_id.id,
                    }
                    current_bom_move = self.env['stock.move'].create(bom_order_lines)
            if first_line.product_id.tracking != 'none' and (self.picking_type_id.use_existing_lots or self.picking_type_id.use_create_lots):
                for line in order_lines:
                    sum_of_lots = 0
                    for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
                        if line.product_id.tracking == 'serial':
                            qty = 1
                        else:
                            qty = abs(line.qty)
                        ml_vals = current_move._prepare_move_line_vals()
                        ml_vals.update({'qty_done':qty})
                        if self.picking_type_id.use_existing_lots:
                            existing_lot = self.env['stock.production.lot'].search([
                                ('company_id', '=', self.company_id.id),
                                ('product_id', '=', line.product_id.id),
                                ('name', '=', lot.lot_name)
                            ])
                            if not existing_lot and self.picking_type_id.use_create_lots:
                                existing_lot = self.env['stock.production.lot'].create({
                                    'company_id': self.company_id.id,
                                    'product_id': line.product_id.id,
                                    'name': lot.lot_name,
                                })
                            ml_vals.update({
                                'lot_id': existing_lot.id,
                            })
                        else:
                            ml_vals.update({
                                'lot_name': lot.lot_name,
                            })
                        self.env['stock.move.line'].create(ml_vals)
                        sum_of_lots += qty
                    if abs(line.qty) != sum_of_lots:
                        difference_qty = abs(line.qty) - sum_of_lots
                        ml_vals = current_move._prepare_move_line_vals()
                        if line.product_id.tracking == 'serial':
                            ml_vals.update({'qty_done': 1})
                            for i in range(int(difference_qty)):
                                self.env['stock.move.line'].create(ml_vals)
                        else:
                            ml_vals.update({'qty_done': difference_qty})
                            self.env['stock.move.line'].create(ml_vals)
            else:
                current_move.quantity_done = abs(sum(order_lines.mapped('qty')))
