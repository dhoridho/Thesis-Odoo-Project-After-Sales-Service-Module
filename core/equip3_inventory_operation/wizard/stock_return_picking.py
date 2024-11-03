import json
import datetime
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.stock_account.wizard.stock_picking_return import StockReturnPicking


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    return_reason = fields.Many2one("return.reason", string="Reason")
    return_reason_info = fields.Text("Product Return Details")
    is_return_possible = fields.Boolean(
        "Is Return Possible", compute="_compute_is_return_possible")
    action = fields.Selection(
        [('refund', 'Refund'), ('repair', 'Repair'), ('replace', 'Replace'), ('return', "Return")], string='Action',
        default='refund')
    return_line_ids = fields.One2many('stock.return.move.line', 'return_id', string='Return')
    picking_type_code = fields.Selection(related='picking_id.picking_type_code')


    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        move_dest_exists = False
        product_return_moves = [(5,)]
        if self.picking_id and self.picking_id.state != 'done':
            raise UserError(_("You may only return Done pickings."))
        # In case we want to set specific default values (e.g. 'to_refund'), we must fetch the
        # default values for creation.
        line_fields = [f for f in self.env['stock.return.picking.line']._fields.keys()]
        product_return_moves_data_tmpl = self.env['stock.return.picking.line'].default_get(line_fields)
        for move in self.picking_id.move_lines:
            if move.state == 'cancel':
                continue
            if move.scrapped:
                continue
            if move.move_dest_ids:
                move_dest_exists = True
            product_return_moves_data = dict(product_return_moves_data_tmpl)
            product_return_moves_data.update(self._prepare_stock_return_picking_line_vals_from_move(move))

            for move_line in move.move_line_ids:
                move_line_values = product_return_moves_data.copy()
                move_line_values.update({
                    'quantity': move_line.qty_done,
                    'lot_id': move_line.lot_id.id
                })
                product_return_moves.append((0, 0, move_line_values))

        if self.picking_id and not product_return_moves:
            raise UserError(_("No products to return (only lines in Done state and not fully returned yet can be returned)."))
        if self.picking_id:
            self.product_return_moves = product_return_moves
            self.move_dest_exists = move_dest_exists
            self.parent_location_id = self.picking_id.picking_type_id.warehouse_id and self.picking_id.picking_type_id.warehouse_id.view_location_id.id or self.picking_id.location_id.location_id.id
            self.original_location_id = self.picking_id.location_id.id
            location_id = self.picking_id.location_id.id
            if self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.return_location:
                location_id = self.picking_id.picking_type_id.return_picking_type_id.default_location_dest_id.id
            self.location_id = location_id
            if self.picking_id.transfer_id.is_transit and self.picking_id.is_transfer_in:
                location_id = self.picking_id.transfer_id.source_location_id
            self.location_id = location_id

    @api.onchange('product_return_moves')
    def _onchange_product_return_moves(self):
        """ to_refund linked with stock.move not stock.move.line
        so, currently impossible same move have different to_refund value """
        if self.picking_type_code != "incoming":
            return
        product_return_moves = self.product_return_moves
        if product_return_moves:
            bymoves = {}
            for move in product_return_moves.mapped('move_id'):
                bymoves[move.id] = product_return_moves.filtered(lambda o: o.move_id == move)
            for move_id, moves in bymoves.items():
                changed_move = sorted(moves, key=lambda m: m.changed_to_refund_time or datetime.datetime.min)[-1]
                moves.update({'to_refund': changed_move.to_refund})

    @api.depends('picking_id')
    def _compute_is_return_possible(self):
        for rec in self:
            return_date = self.env['stock.picking'].browse(
                self.env.context.get('active_id')).return_date_limit
            rec.is_return_possible = fields.Datetime.now(
            ) < return_date if return_date else False


    def create_returns(self):
        for wizard in self:
            new_picking_id, pick_type_id = wizard._create_returns()
            
            if wizard.picking_id.transfer_id:
                continue

            new_picking = self.env['stock.picking'].browse(new_picking_id)
            
            config_params = self.env['ir.config_parameter'].sudo()
            
            if new_picking.picking_type_code == "incoming":
                approval_matrix_config = config_params.get_param('is_receiving_notes_approval_matrix', False)
                new_picking.is_rn_request_approval_matrix = approval_matrix_config
                new_picking.is_do_request_approval_matrix = False
            elif new_picking.picking_type_code == "outgoing":
                approval_matrix_config = config_params.get_param('is_delivery_order_approval_matrix', False)
                new_picking.is_do_request_approval_matrix = approval_matrix_config
                new_picking.is_rn_request_approval_matrix = False
            

            if wizard.picking_type_code == "outgoing":
                for move in new_picking.move_ids_without_package:
                    return_lines = wizard.return_line_ids.filtered(lambda r: r.product_id.id == move.product_id.id)
                    for move_line in return_lines:
                        move_vals = {
                            'product_id': move_line.product_id.id,
                            'product_uom_id': move_line.uom_id.id,
                            'qty_done': move_line.qty,
                            'location_id': move.location_id.id,
                            'location_dest_id': move.location_dest_id.id,
                            'lot_id': move_line.lot_id and move_line.lot_id.id,
                            'move_id': move.id,
                            'lot_name': move_line.lot_id and move_line.lot_id.name or False,
                            'picking_id': new_picking.id,
                        }
                        self.env['stock.move.line'].create(move_vals)

            elif wizard.picking_type_code == "incoming":
                for move in new_picking.move_ids_without_package:
                    return_moves = wizard.product_return_moves.filtered(lambda line: line.lot_id and line.move_id == move.origin_returned_move_id)
                    if not return_moves:
                        continue
                    move.write({'move_lines_to_return': json.dumps({'lines': [{
                        'lot_id': line.lot_id and line.lot_id.id or False,
                        'quantity': line.quantity,
                        'uom_id': line.uom_id.id
                    } for line in return_moves]}, default=str)})

        # Override the context to disable all the potential filters that could have been set previously
        ctx = dict(self.env.context)
        ctx.update({
            'default_partner_id': self.picking_id.partner_id.id,
            'search_default_picking_type_id': pick_type_id,
            'search_default_draft': False,
            'search_default_assigned': False,
            'search_default_confirmed': False,
            'search_default_ready': False,
            'search_default_planning_issues': False,
            'search_default_available': False,
            'default_transfer_id': True,
            'group_header': False
        })
        if self.picking_id.transfer_id:
            # internal_type = self.env['ir.config_parameter'].sudo(
            # ).get_param('internal_type') or False
            # if internal_type == 'with_transit':
            picking_id_src = self.env['stock.picking'].search(
                [('id', '=', new_picking_id)])
            move_lines = []
            for lines in picking_id_src.move_line_ids_without_package:
                move_lines.append(lines.copy({}))
            transit_location = self.env.ref(
                'equip3_inventory_masterdata.location_transit')
            stock_move_obj = self.env['stock.move']
            for picking in picking_id_src:
                operation_type_src = self.env['stock.picking.type'].search(
                    [('default_location_dest_id', '=', transit_location.id),
                        ('default_location_src_id', '=', picking.location_id.id)], limit=1)
                operation_type_dest = self.env['stock.picking.type'].search(
                    [('default_location_dest_id', '=', picking.location_dest_id.id),
                        ('default_location_src_id', '=', transit_location.id)], limit=1)
                vals_source = {
                    'location_id': picking.location_id.id,
                    'location_dest_id': transit_location.id,
                    'move_type': 'direct',
                    'partner_id': picking.partner_id.id,
                    'scheduled_date': picking.scheduled_date,
                    'picking_type_id': operation_type_src.id,
                    'origin': picking.origin,
                    'transfer_id': picking.transfer_id.id,
                    # 'branch_id': picking.branch_id.id,
                    'is_transfer_out': True,
                    'state': 'draft',
                    'branch_id': picking.location_id.branch_id.id,
                }

                vals_dest = {
                    'location_id': transit_location.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'move_type': 'direct',
                    'partner_id': picking.partner_id.id,
                    'scheduled_date': picking.scheduled_date,
                    'picking_type_id': operation_type_dest.id,
                    'origin': picking.origin,
                    'transfer_id': picking.transfer_id.id,
                    'is_transfer_in': True,
                    # 'branch_id': picking.branch_id.id,
                    'state': 'draft',
                    'branch_id': picking.location_dest_id.branch_id.id,
                }
                src_picking = self.env['stock.picking'].create(vals_source)
                dest_picking = self.env['stock.picking'].create(vals_dest)
                counter = 1
                for move in picking.move_ids_without_package:
                    src_move_data = {
                        'move_line_sequence': counter,
                        'picking_id': src_picking.id,
                        'name': move.product_id.name,
                        'product_id': move.product_id.id,
                        'product_uom_qty': move.product_uom_qty,
                        'product_uom': move.product_uom.id,
                        'location_id': picking.location_id.id,
                        'location_dest_id': transit_location.id,
                        'date': src_picking.scheduled_date,
                    }
                    dest_move_data = {
                        'move_line_sequence': counter,
                        'picking_id': dest_picking.id,
                        'name': move.product_id.name,
                        'product_id': move.product_id.id,
                        'product_uom_qty': move.product_uom_qty,
                        'product_uom': move.product_uom.id,
                        'location_id': transit_location.id,
                        'location_dest_id': picking.location_dest_id.id,
                        'date': src_picking.scheduled_date,
                    }
                    stock_move_obj.create(src_move_data)
                    stock_move_obj.create(dest_move_data)
                    counter += 1
                # asd = self.env['stock.picking'].search(
                #     [('id', '=', picking_id_dest.id)])
                dest_id = self.env['stock.picking'].search(
                    [('id', '=', picking_id_src.id)])
                # if asd:
                #     asd.unlink()
                if dest_id:
                    dest_id.unlink()
                return {
                    'name': _('Returned Picking'),
                    'view_mode': 'form,tree,calendar',
                    'res_model': 'stock.picking',
                    'action' : self.env.ref('equip3_inventory_operation.action_from_interwarehouse_request').read()[0],
                    'res_id': src_picking.id,
                    'type': 'ir.actions.act_window',
                    'context': ctx,
                }
        elif ctx.get('from_return_request_so_po'):
            return {
                'name': _('Returned Picking'),
                'view_mode': 'form,tree,calendar',
                'res_model': 'stock.picking',
                'res_id': new_picking_id,
                'type': 'ir.actions.act_window',
                'context': ctx,
            }
        else:
            # print('Normal PIcking')
            return {
                'name': _('Returned Picking'),
                'view_mode': 'form,tree,calendar',
                'res_model': 'stock.picking',
                'res_id': new_picking_id,
                'type': 'ir.actions.act_window',
                'context': ctx,
            }

    def _prepare_move_default_values(self, return_line, new_picking):
        res = super(ReturnPicking, self)._prepare_move_default_values(
            return_line, new_picking)
        res.update({
            "action": return_line.action,
            "return_reason": return_line.return_reason.id if self.env.context.get(
                "from_return_request_so_po") else self.return_reason.id
        })
        return res


    def _create_returns(self):
        res = super(ReturnPicking, self)._create_returns()
        transfer_id = self.picking_id.transfer_id
        if transfer_id and transfer_id.is_transit and self.picking_id.is_transfer_in:
            for line in self.product_return_moves:
                transfer_lines = transfer_id.product_line_ids.filtered(lambda r: r.product_id.id == line.product_id.id)
                trf_qty = sum(transfer_lines.mapped('transfer_qty'))
                return_qty = trf_qty - line.quantity
                transfer_lines.write({'transfer_qty': return_qty})
        return res


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    return_reason = fields.Many2one("return.reason", string="Return Reason")
    action = fields.Selection(
        [('refund', 'Refund'), ('repair', 'Repair'), ('replace', 'Replace'), ('return', "Return")], string='Action',
        default='refund')
    # quantity = fields.Float(compute='_compute_quantity', inverse="_inverse_quantity", store=True)

    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number')
    allowed_lot_ids = fields.Many2many('stock.production.lot', related='move_id.lot_ids')

    # technical field
    changed_to_refund_time = fields.Datetime()

    # @api.depends('wizard_id', 'wizard_id.return_line_ids', 'wizard_id.return_line_ids.qty')
    # def _compute_quantity(self):
    #     for record in self:
    #         product_line = record.wizard_id.return_line_ids.filtered(lambda r: r.product_id.id == record.product_id.id)
    #         record.quantity = sum(product_line.mapped('qty'))

    # def _inverse_quantity(self):
    #     pass

    @api.onchange('to_refund')
    def _onchange_to_refund(self):
        self.changed_to_refund_time = fields.Datetime.now()

class StockReturnPickingPatch:
    def _create_returns(self):
        new_picking_id, pick_type_id = super(StockReturnPicking, self)._create_returns()
        new_picking = self.env['stock.picking'].browse([new_picking_id])
        for move in new_picking.move_lines:
            return_picking_line = self.product_return_moves.filtered(lambda r: r.move_id == move.origin_returned_move_id)
            if return_picking_line and return_picking_line[0].to_refund:
                move.to_refund = True
        return new_picking_id, pick_type_id

StockReturnPicking._create_returns = StockReturnPickingPatch._create_returns
