from itertools import product
from odoo import _, api, fields, models
from datetime import datetime, date, timedelta

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # picking_type_code = fields.Selection(store=True)
    purchase_requisition_id = fields.Many2one('purchase.requisition')
    consignment_id = fields.Many2one('consignment.agreement')

    @api.model
    def create(self, vals):
        if vals.get('is_consignment') and vals.get('consignment_id'):
            warehouse_code = self.env['stock.location'].browse(vals['location_dest_id']).warehouse_id.code.upper()
            vals['name'] = f"{warehouse_code}/CONS/IN{self.env['ir.sequence'].next_by_code('receiving.notes.consignment.sequence')}"
        return super(StockPicking, self).create(vals)

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for picking in self:
            if picking.is_consignment:
                for sm in picking.move_ids_without_package: # stock move
                    # cari stock quant id yang sama dengan stock_move.quant
                    stock_quant = picking.env['stock.quant'].search([('move_id' ,'=' ,sm.id)])
                    if stock_quant:
                        product_list = []
                        for quant in stock_quant:
                            product_list.append(quant.product_id)

                    for sml in sm.move_line_nosuggest_ids: # Stock move line
                        lot_id = sml.lot_id.id
                        if lot_id:
                            stock_production_lot = self.env['stock.production.lot'].search([('id' ,'=' ,lot_id)])
                            stock_production_lot.write({'is_consignment' : True})
                if picking.consignment_id:
                    for sm in picking.move_ids_without_package:
                        for line in picking.consignment_id.line_ids:
                            if sm.product_id.id == line.product_id.id:
                                line.receiving_quantities += sm.quantity_done
                                # line.remaining_quantities = line.product_qty - line.receiving_quantities
                                line.purchase_stock = line.receiving_quantities
                    picking.move_line_ids_without_package.write({'is_consignment': True})
                    lot_ids = picking.move_line_ids_without_package.mapped('lot_id.id') 
                    if lot_ids:
                        sqs = self.env['stock.quant'].search([('lot_id','in',lot_ids)])
                        sqs.sudo().write({'consignment_id': picking.consignment_id.id}) 

            if picking.sale_id:
                picking._update_sale_stock_consignment()
                for sm in picking.move_ids_without_package:
                    sale_order_line = self.env['sale.order.line'].search([('id', '=', sm.sale_line_id.id)])
                    if sale_order_line.is_consignment:
                        for sml in picking.move_line_ids_without_package:
                            sml.is_consignment = True
                            # if sm.product_id.id == sml.product_id.id:
                                # consignment_agremeent_line = self.env['consignment.agreement.line'].search([
                                # ('product_id', '=', sm.product_id.id)], limit=1)
                                # sml.consignment_agreement = consignment_agremeent_line.consignment_id.id
        return res


    def _update_sale_stock_consignment(self):
        self.ensure_one()

        for move in self.move_ids_without_package.filtered(lambda o: o.sale_line_id and o.sale_line_id.product_id == o.product_id):
            svls = move.stock_valuation_layer_ids

            if not svls:
                continue

            svl_lines = svls.line_ids
            agreements = svls.mapped('consignment_id')
            agreement_lines = agreements.line_ids.filtered(lambda o: o.product_id == move.product_id)

            for line in agreement_lines:
                line.sold_quantities += abs(sum(svl_lines.filtered(lambda o: o.consignment_id == line.consignment_id).mapped('quantity')))

    def name_get(self):
        res = super(StockPicking, self).name_get()
        if self._context.get('default_is_assign_owner') and self._context.get('default_is_assign_owner') != None:
            result = []
            for x in self:
                name = x.owner_id.name
                result.append((x.id, name))
            return result
        else:
            return res
