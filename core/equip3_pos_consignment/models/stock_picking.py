# -*- coding: utf-8 -*-

from odoo import fields, api, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        pickings = super(StockPicking, self)._create_picking_from_pos_order_lines(location_dest_id, lines, picking_type, partner=partner)
        #TODO: Set field "Is Consignment" to True if serial number created from Consignments
        lots_ids = []
        for picking in pickings:
            is_consignment = False
            for sml in picking.move_line_ids_without_package:  
                if sml.lot_id.is_consignment:
                    is_consignment = True
                    sml.sudo().write({ 'is_consignment': True })
                    lots_ids += [sml.lot_id.id]
                    
            if is_consignment:
                picking.sudo().write({ 'is_consignment': True })

        if lots_ids:
            domain = [('is_consignment','=',False), ('lot_id','in',lots_ids)]
            sq = self.env['stock.quant'].search(domain)
            sq.sudo().write({ 'is_consignment': True })

        return pickings

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for picking in self:
            if picking.pos_order_id and not picking.sale_id: # if picking from pos.order
                picking._update_pos_order_stock_consignment() 
        return res

    def _update_pos_order_stock_consignment(self):
        self.ensure_one()
        moves = self.move_ids_without_package.filtered(lambda o: o.pos_order_line_id and o.pos_order_line_id.product_id == o.product_id)
        for move in moves:
            svls = move.stock_valuation_layer_ids
            if not svls:
                continue

            svl_lines = svls.line_ids
            agreements = svls.mapped('consignment_id')
            agreement_lines = agreements.line_ids.filtered(lambda o: o.product_id == move.product_id)

            for line in agreement_lines:
                line.sold_quantities += abs(sum(svl_lines.filtered(lambda o: o.consignment_id == line.consignment_id).mapped('quantity')))