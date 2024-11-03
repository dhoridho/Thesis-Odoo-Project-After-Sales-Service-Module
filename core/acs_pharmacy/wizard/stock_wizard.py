# -*- coding: utf-8 -*-

import time
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

class StockReturnPickingLine(models.TransientModel):
    _name = "stock.picking.barcode.line"
    _rec_name = 'product_id'
    _description = "Picking Barcode Line"

    product_id = fields.Many2one('product.product', string="Product", required=True)
    quantity = fields.Integer(string="Quantity", default=1, required=True)
    wizard_id = fields.Many2one('stock.picking.barcode', string="Wizard")
    lot_id = fields.Many2one('stock.production.lot',string='Serial Number', help="Used to choose the lot/serial number of the product returned")


class StockReturnPicking(models.TransientModel):
    _name = 'stock.picking.barcode'
    _description = 'Picking Barcode'

    @api.depends('rows','columns')
    def _starting_position(self):
        for rec in self:
            rec.starting_position = (((rec.rows-1)*5) + rec.columns)-1

    columns = fields.Integer(string="Columns", default=1)
    rows = fields.Integer(string="Rows", default=1)
    starting_position = fields.Integer(compute=_starting_position, string="Position", readonly="True")
    product_barcode_line = fields.One2many('stock.picking.barcode.line', 'wizard_id', string='Barcode Wizard')

    @api.model
    def default_get(self,fields):
        res = super(StockReturnPicking, self).default_get(fields)
        lines = []
        context = self._context or {}
        if context and context.get('active_ids', False):
            if len(context.get('active_ids')) > 1:
                raise UserError(_("You may only return one picking at a time!"))
        record_id = context and context.get('active_id', False) or False
        pick_obj = self.env['stock.picking']
        pick = pick_obj.browse(record_id)
        for move in pick.move_line_ids:
            lines.append((0,0,{
                'product_id': move.product_id.id,
                'lot_id': move.lot_id.id,
                'quantity': move.qty_done,
            }))
        res['product_barcode_line'] = lines
        return res

    def print_report(self):
        datas = {'ids': [self.id]}
        res = self.read([])
        res = res and res[0] or {}
        datas['form'] = res
        return self.env.ref('acs_pharmacy.action_stock_picking_barcode').report_action([], data=datas)


class StockProductionReport(models.TransientModel):
    _name = 'stock.production.report'
    _description = "ACS Stock Production Report"

    @api.depends('rows','columns')
    def _starting_position(self):
        for rec in self:
            rec.starting_position = (((rec.rows-1)*5) + rec.columns)-1

    columns = fields.Integer(string="Columns", default=1)
    rows = fields.Integer(string="Rows", default=1)
    quantity = fields.Integer(string="Quantity", default=1)
    starting_position = fields.Integer(compute=_starting_position,string="Position",readonly="True")

    def print_report(self):
        datas = {'ids': self.env.context.get('active_ids', [])}
        res = self.read([])
        res = res and res[0] or {}
        datas['form'] = res
        return self.env.ref('acs_pharmacy.action_stock_product_barcode').report_action([], data=datas)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: