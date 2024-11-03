from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError, UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for res in self:
            check = False
            for rec in res.move_ids_without_package:
                if rec.quantity_done > 0:
                    check = True
                    break
            if check:
                for line in res.move_ids_without_package:
                    line_ids = []
                    bundle = 0
                    break_for = False
                    if line.is_pack:
                        if line.purchase_line_id or line.sale_line_id:
                            line_ids = self.env['stock.move'].search([('picking_id', '=', res.id), ('purchase_line_id', '=', line.purchase_line_id.id), ('sale_line_id', '=', line.sale_line_id.id)])
                            if line_ids:
                                j = 0
                                for l in line_ids:
                                    if l.quantity_done > 0:
                                        break_for = True
                                if not break_for:
                                    break
                                for i in line_ids:
                                    qty_per_pack = i.qty_pack
                                    if i.sale_line_id:
                                        qty_per_pack = i.sale_line_id.product_uom_qty / i.sale_line_id.product_qty
                                    elif i.purchase_line_id:
                                        qty_per_pack = i.purchase_line_id.product_uom_qty / i.purchase_line_id.product_qty
                                    qty_per_uom = i.qty_pack * qty_per_pack
                                    if j == 0 and bundle == 0:
                                        if i.quantity_done >= qty_per_uom and i.quantity_done % qty_per_uom == 0:
                                            bundle = i.quantity_done / qty_per_uom
                                        else:
                                            raise ValidationError("The done quantity for product %s must be multiple of %s" % (i.product_id.name, qty_per_uom))
                                    else:
                                        if i.quantity_done / qty_per_uom != bundle:
                                            raise ValidationError("The done quantity for product %s must be %s" % (i.product_id.name, str(qty_per_uom * bundle)))
                                    j += 1
        res = super(StockPicking, self).button_validate()
        return res

    # def write(self, vals):
    #     res = super(StockPicking, self).write(vals)
    #     self.change_product_line_pack(self.move_ids_without_package)
    #     self.change_product_line_pack2(self.move_line_ids_without_package)
    #     return res

    def change_product_line_pack(self, lines, line_seq):
        for res in self:
            seq = line_seq
            sequence = 1
            for move in lines:
                move.move_line_sequence = seq
                if move.product_id.is_pack:
                    qty = move.product_uom_qty
                    if move.product_id.bi_pack_ids:
                        val = []
                        i = 1
                        for line in move.product_id.bi_pack_ids:
                            if i > 1:
                                seq += 1
                                val.append({
                                    'name': line.product_id.name,
                                    'product_id': line.product_id.id,
                                    'move_line_sequence': seq,
                                    'company_id': move.company_id.id,
                                    'product_uom': line.product_id.uom_id.id,
                                    'product_uom_qty': line.qty_uom * qty,
                                    'initial_demand': line.qty_uom * qty,
                                    'partner_id': move.partner_id.id,
                                    'location_id': move.location_id.id,
                                    'location_dest_id': move.location_dest_id.id,
                                    'rule_id': move.rule_id.id,
                                    'origin': move.origin,
                                    'picking_type_id': move.picking_type_id.id,
                                    'warehouse_id': move.warehouse_id.id,
                                    'qty_pack': line.qty_uom,
                                    'picking_id': move.picking_id.id,
                                    'sale_line_id': move.sale_line_id.id,
                                    'purchase_line_id': move.purchase_line_id.id,
                                    'is_pack':move.product_id.is_pack,
                                    'analytic_account_group_ids': [(6,0,move.analytic_account_group_ids.ids)]
                                })
                            else:
                                move.write({
                                    'name': line.product_id.name,
                                    'product_id': line.product_id.id,
                                    'product_uom': line.product_id.uom_id.id,
                                    'product_uom_qty': line.qty_uom * qty,
                                    'initial_demand': line.qty_uom * qty,
                                    'qty_pack': line.qty_uom,
                                    'remaining': line.qty_uom * qty,
                                    'is_pack':move.product_id.is_pack,
                                    'analytic_account_group_ids': [(6,0,move.analytic_account_group_ids.ids)]
                                })
                            i+=1
                            sequence += 1
                        self.env['stock.move'].create_line_pack(val)

    def change_product_line_pack2(self, lines, line_seq):
        for res in self:
            seq = line_seq
            for move in lines:
                move.move_line_sequence = seq
                if move.product_id.is_pack:
                    qty = move.product_uom_qty
                    move_id = self.env['stock.move'].search([('picking_id', '=', res.id), ('product_id', '=', move.product_id.id)])
                    if move.product_id.bi_pack_ids:
                        val = []
                        i = 1
                        for line in move.product_id.bi_pack_ids:
                            if i > 1:
                                seq += 1
                                val.append({
                                    'picking_id': res.id,
                                    'move_id': move_id.id,
                                    'move_line_sequence': seq,
                                    'product_id': line.product_id.id,
                                    'product_uom_id': line.product_id.uom_id.id,
                                    'product_uom_qty': line.qty_uom * qty,
                                    'qty_done': 0,
                                    'location_id': move.location_id.id,
                                    'location_dest_id': move.location_dest_id.id,
                                    'lot_id': move.lot_id.id,
                                    'lot_name': move.lot_name,
                                })
                            else:
                                state = move.state
                                move.state = 'draft'
                                move.write({
                                    'product_id': line.product_id.id,
                                    'product_uom_id': line.product_id.uom_id.id,
                                    'product_uom_qty': line.qty_uom * qty,
                                })
                                move.state = state
                            i+=1
                        self.env['stock.move.line'].create_line_pack(val)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def write(self, vals):
        res = super(SaleOrderLine, self).write(vals)
        return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        for line in self.order_line:
            if line.product_id.is_pack:
                vals = []
                for pack in line.product_id.bi_pack_ids:
                    vals.append(pack.product_id.id)
                for i in vals:
                    qty_done = 0
                    qty_per_pack = 0
                    qty_per_uom = 0
                    done = 0
                    products = self.env['stock.move'].search([('sale_line_id', '=', line.id), ('product_id', '=', i), ('state', '=', 'done')])
                    for i in products:
                        qty_per_uom = i.sale_line_id.product_uom_qty / i.sale_line_id.product_qty
                        qty_done += i.quantity_done
                        qty_per_pack = i.qty_pack * qty_per_uom
                    if qty_per_pack > 0:
                        done = qty_done // qty_per_pack
                    if line.qty_delivered == 0:
                        line.qty_delivered = done
                    else:
                        if line.qty_delivered >= done:
                            line.qty_delivered = done
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    qty_pack = fields.Integer("Qty")
    is_pack = fields.Boolean("Pack")

    @api.model
    def create(self, vals):
        res = super(StockMove, self).create(vals)
        context = self.env.context or {}
        if context.get('from_action_confirm') and not res.picking_id:
            res._assign_picking()
        if res.product_id.is_pack and res.picking_id:
            counter = len(res.picking_id.move_ids_without_package)
            res.picking_id.change_product_line_pack(res, counter)
            move_line_counter = len(res.picking_id.move_line_ids)
            res.picking_id.change_product_line_pack2(res.move_line_ids, move_line_counter)
        return res

    def _assign_picking(self):
        res = super(StockMove, self)._assign_picking()
        counter = 1
        move_line_counter = 1
        for record in self:
            if record.product_id.is_pack and record.picking_id:
                product_pack_len = len(record.product_id.bi_pack_ids)
                record.picking_id.change_product_line_pack(record, counter)
                counter += product_pack_len
                record.picking_id.change_product_line_pack2(record.move_line_ids, move_line_counter)
                move_line_counter += len(record.picking_id.move_line_ids)
        return res

    def create_line_pack(self, val):
        self.create(val)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def create_line_pack(self, val):
        self.create(val)