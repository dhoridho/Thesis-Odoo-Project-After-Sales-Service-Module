import json
import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero
from collections import defaultdict
from odoo.osv import expression


class MrpUnbuild(models.Model):
    _inherit = 'mrp.unbuild'

    product_id = fields.Many2one(domain=[('has_bom', '=', True)], tracking=True)
    company_id = fields.Many2one(tracking=True)
    product_qty = fields.Float(digits='Product Unit of Measure', compute='_compute_product_qty')
    product_uom_id = fields.Many2one(tracking=True)
    bom_id = fields.Many2one(domain="""[
    ('type', '=', 'normal'),
    ('equip_bom_type', '=', 'mrp'),
    '|',
        ('product_id', '=', product_id),
        '&',
            ('product_tmpl_id.product_variant_ids', '=', product_id),
            ('product_id','=',False),
    '|',
        ('company_id', '=', company_id),
        ('company_id', '=', False),
    '|',
        ('branch_id', '=', branch_id),
        ('branch_id', '=', False),
    ]
    """, tracking=True)
    mo_id = fields.Many2one(string="Production Order", tracking=True)
    location_dest_id = fields.Many2one('stock.location', required=False)

    is_branch_required = fields.Boolean(related='company_id.show_branch')
    branch_id = fields.Many2one('res.branch', 
        string='Branch', 
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)], 
        states={'done': [('readonly', True)]})

    line_raw_ids = fields.One2many('mrp.unbuild.line', 'unbuild_raw_id', string='Materials')
    line_byproduct_ids = fields.One2many('mrp.unbuild.line', 'unbuild_byproduct_id', string='By-Products')
    line_finished_ids = fields.One2many('mrp.unbuild.line', 'unbuild_finished_id', string='Finished')

    @api.depends('company_id', 'branch_id', 'product_id')
    def _compute_allowed_mo_ids(self):
        for unbuild in self:
            domain = [
                ('state', '=', 'done'),
                ('company_id', '=', unbuild.company_id.id),
            ]
            if unbuild.company_id.show_branch:
                domain = expression.AND([domain, [('branch_id', '=', unbuild.branch_id.id)]])
            if unbuild.product_id:
                domain = expression.AND([domain, [('product_id', '=', unbuild.product_id.id)]])
            allowed_mos = self.env['mrp.production'].search_read(domain, ['id'])
            if allowed_mos:
                unbuild.allowed_mo_ids = [mo['id'] for mo in allowed_mos]
            else:
                unbuild.allowed_mo_ids = False

    @api.depends('line_finished_ids', 'line_finished_ids.to_unbuild_qty')
    def _compute_product_qty(self):
        for record in self:
            lines = record.line_finished_ids
            record.product_qty = lines and sum(lines.mapped('to_unbuild_qty')) or 1.0

    @api.onchange('bom_id', 'mo_id', 'location_id')
    def _onchange_bom_id(self, product_qty=None):
        company = self.company_id

        should_update_finished = False
        if product_qty is None:
            product_qty = self.bom_id.product_qty
            should_update_finished = True

        line_dict = defaultdict(lambda: 0.0)
        for line in self.bom_id.bom_line_ids:
            line_dict[line] = (product_qty / self.bom_id.product_qty) * line.product_qty
        for line in self.bom_id.byproduct_ids:
            line_dict[line] = (product_qty / self.bom_id.product_qty) * line.product_qty

        line_raw_values = [(5,)]
        line_byproduct_values = [(5,)]
        line_finished_values = [(5,)]
        if self.mo_id:
            factor = product_qty / self.mo_id.product_qty

            taken_qty = defaultdict(lambda: 0.0)
            for move_line in self.mo_id.move_raw_ids.mapped('move_line_ids'):
                bom_line = move_line.move_id.bom_line_id

                if move_line.product_id.tracking == 'serial':
                    if move_line.unbuild_qty:
                        continue
                    to_unbuild_qty = 1.0
                    taken_qty[bom_line] += 1.0
                    if taken_qty[bom_line] > line_dict[bom_line]:
                        continue
                else:
                    to_unbuild_qty = move_line.qty_done * factor
                
                line_raw_values += [(0, 0, {
                    'move_line_id': move_line.id,
                    'bom_line_id': bom_line.id,
                    'product_id': move_line.product_id.id,
                    'lot_id': move_line.lot_id.id,
                    'product_uom_qty': move_line.qty_done,
                    'to_unbuild_qty': to_unbuild_qty,
                    'product_uom': move_line.product_uom_id.id,
                    'location_id': move_line.location_dest_id.id,
                    'location_dest_id': move_line.location_id.id
                })]
            
            taken_qty = defaultdict(lambda: 0.0)
            for move_line in self.mo_id.move_byproduct_ids.mapped('move_line_ids'):
                byproduct = move_line.move_id.byproduct_id

                if move_line.product_id.tracking == 'serial':
                    if move_line.unbuild_qty:
                        continue
                    to_unbuild_qty = 1.0
                    taken_qty[byproduct] += 1.0
                    if taken_qty[byproduct] > line_dict[byproduct]:
                        continue
                else:
                    to_unbuild_qty = move_line.qty_done * factor
                
                line_byproduct_values += [(0, 0, {
                    'move_line_id': move_line.id,
                    'byproduct_id': move_line.move_id.byproduct_id.id,
                    'product_id': move_line.product_id.id,
                    'lot_id': move_line.lot_id.id,
                    'product_uom_qty': move_line.qty_done,
                    'to_unbuild_qty': to_unbuild_qty,
                    'product_uom': move_line.product_uom_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': move_line.location_id.id
                })]

            if should_update_finished:
                for move_line in self.mo_id.move_finished_only_ids.mapped('move_line_ids'):
                    line_finished_values += [(0, 0, {
                        'move_line_id': move_line.id,
                        'finished_id': move_line.move_id.finished_id.id,
                        'product_id': move_line.product_id.id,
                        'lot_id': move_line.lot_id.id,
                        'product_uom_qty': move_line.qty_done,
                        'to_unbuild_qty': max(0, move_line.qty_done - move_line.unbuild_qty),
                        'product_uom': move_line.product_uom_id.id,
                        'location_id': self.location_id.id,
                        'location_dest_id': move_line.location_id.id
                    })]
        else:
            for bom_line in self.bom_id.bom_line_ids:
                line_product_qty = line_dict[bom_line]
                tracking = bom_line.product_id.tracking
                arange = math.ceil(line_product_qty) if tracking == 'serial' else 1
                qty = 1 if tracking == 'serial' else line_product_qty

                production_location = bom_line.product_id.with_company(company).property_stock_production
                workcenter_location = bom_line.operation_id._get_workcenter().location_id

                for i in range(arange):
                    line_raw_values += [(0, 0, {
                        'bom_line_id': bom_line.id,
                        'product_id': bom_line.product_id.id,
                        'product_uom_qty': qty,
                        'to_unbuild_qty': qty,
                        'product_uom': bom_line.product_uom_id.id,
                        'location_id': production_location.id,
                        'location_dest_id': workcenter_location.id
                    })]

            last_operation = self.bom_id.operation_ids and self.bom_id.operation_ids[-1] or False
            last_operation_location_id = last_operation and last_operation._get_workcenter().location_finished_id.id or False

            for byproduct in self.bom_id.byproduct_ids:
                line_product_qty = line_dict[bom_line]
                tracking = byproduct.product_id.tracking
                arange = math.ceil(line_product_qty) if tracking == 'serial' else 1
                qty = 1 if tracking == 'serial' else line_product_qty

                production_location = byproduct.product_id.with_company(company).property_stock_production

                for i in range(arange):
                    line_byproduct_values += [(0, 0, {
                        'byproduct_id': byproduct.id,
                        'product_id': byproduct.product_id.id,
                        'product_uom_qty': qty,
                        'to_unbuild_qty': qty,
                        'product_uom': byproduct.product_uom_id.id,
                        'location_id': self.location_id.id or last_operation_location_id,
                        'location_dest_id': production_location.id
                    })]

            if should_update_finished:
                for finished in self.bom_id.finished_ids:
                    tracking = finished.product_id.tracking
                    arange = math.ceil(line_product_qty) if tracking == 'serial' else 1
                    qty = 1 if tracking == 'serial' else finished.product_qty

                    production_location = finished.product_id.with_company(company).property_stock_production

                    for i in range(arange):
                        line_finished_values += [(0, 0, {
                            'finished_id': finished.id,
                            'product_id': finished.product_id.id,
                            'product_uom_qty': qty,
                            'to_unbuild_qty': qty,
                            'product_uom': finished.product_uom_id.id,
                            'location_id': self.location_id.id or last_operation_location_id,
                            'location_dest_id': production_location.id
                        })]

        self.line_raw_ids = line_raw_values
        self.line_byproduct_ids = line_byproduct_values

        if should_update_finished:
            self.line_finished_ids = line_finished_values

    @api.onchange('mo_id')
    def _onchange_mo_id(self):
        production = self.mo_id
        unbuild_qty = sum(max(0, move_line.qty_done - move_line.unbuild_qty) for move_line in production.move_finished_only_ids.move_line_ids)

        self.product_id = production.product_id.id
        self.bom_id = production.bom_id
        self.product_uom_id = production.product_uom_id
        self.product_qty = production.product_id.uom_id._compute_quantity(unbuild_qty, production.product_uom_id)
        self.location_id = production.location_dest_id.id
        self.location_dest_id = False

    @api.onchange('line_finished_ids')
    def _onchange_line_finished(self):
        self._onchange_bom_id(product_qty=sum(self.line_finished_ids.mapped('to_unbuild_qty')))

    @api.onchange('location_dest_id')
    def _onchange_location_dest_id(self):
        self.line_raw_ids.update({'location_dest_id': self.location_dest_id.id})

    def action_validate(self):
        self.ensure_one()

        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in (self.line_finished_ids | self.line_raw_ids | self.line_byproduct_ids):
            if line.product_id.tracking != 'none' and not line.lot_id:
                raise UserError(_('You should provide a lot/serial number for product %s.' % (line.product_id.display_name,)))

            if float_compare(line.available_qty, line.to_unbuild_qty, precision_digits=precision) < 0:
                raise UserError(_('The product %s is not available in sufficient quantity in %s' % (line.product_id.display_name, line.location_id.display_name)))

        if sum(self.line_finished_ids.mapped('to_unbuild_qty')) <= 0:
            raise UserError(_("There's nothing to unbuild!"))

        for line in self.line_finished_ids:
            if self.mo_id and float_compare(line.product_uom_qty - line.unbuild_qty, line.to_unbuild_qty, precision_digits=precision) < 0:
                raise UserError(_('Cannot unbuild more than Production Order quantity!'))
        
        return self.action_unbuild()

    def _prepare_move_vals(self, product, qty, uom, location, location_dest, warehouse, **kwargs):
        self.ensure_one()
        return {
            'name': self.name,
            'date': self.create_date,
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': uom.id,
            'procure_method': 'make_to_stock',
            'location_dest_id': location_dest.id,
            'location_id': location.id,
            'warehouse_id': warehouse.id,
            'unbuild_id': self.id,
            'company_id': self.company_id.id,
            'unbuild_move_id': kwargs.get('move_id', False),
            'bom_line_id': kwargs.get('bom_line_id', False),
            'byproduct_id': kwargs.get('byproduct_id', False),
            'finished_id': kwargs.get('finished_id', False)
        }

    def _generate_consume_moves(self):
        move_vals_list = []
        for unbuild in self:
            unbuild_finished_lines = unbuild.line_finished_ids | unbuild.line_byproduct_ids

            if unbuild.mo_id:
                for finished_move in unbuild_finished_lines.mapped('move_line_id').mapped('move_id'):
                    finished_move_lines = unbuild_finished_lines.filtered(lambda o: o.move_line_id.move_id == finished_move)
                    to_unbuild_qty = sum(finished_move_lines.mapped('to_unbuild_qty'))

                    if float_is_zero(to_unbuild_qty, precision_rounding=finished_move.product_id.uom_id.rounding):
                        continue

                    move_vals = unbuild._prepare_move_vals(
                        finished_move.product_id, to_unbuild_qty, finished_move.product_uom, 
                        finished_move.location_dest_id, finished_move.location_id, finished_move.location_id.get_warehouse(),
                        move_id=finished_move.id)

                    if finished_move.product_id.tracking != 'none':
                        move_line_values = []
                        for line in finished_move_lines:
                            if float_is_zero(line.to_unbuild_qty, precision_rounding=line.product_id.uom_id.rounding):
                                continue
                            move_line_values += [(0, 0, {
                                'lot_id': line.lot_id.id,
                                'qty_done': line.to_unbuild_qty,
                                'product_id': line.product_id.id,
                                'product_uom_id': line.product_uom.id,
                                'location_id': finished_move.location_dest_id.id,
                                'location_dest_id': finished_move.location_id.id,
                            })]
                        move_vals['move_line_ids'] = move_line_values
                    else:
                        move_vals['quantity_done'] = to_unbuild_qty

                    move_vals_list += [move_vals]
            else:
                for line in unbuild_finished_lines:
                    if float_is_zero(line.to_unbuild_qty, precision_rounding=line.product_id.uom_id.rounding):
                        continue

                    product_prod_location = line.product_id.with_company(unbuild.company_id).property_stock_production
                    location_id = unbuild.location_id
                    location_dest_id = product_prod_location
                    warehouse = location_dest_id.get_warehouse()

                    move_vals = unbuild._prepare_move_vals(
                        line.product_id, line.to_unbuild_qty, line.product_uom, 
                        location_id, location_dest_id, warehouse,
                        byproduct_id=line.byproduct_id.id, finished_id=line.finished_id.id)

                    if line.product_id.tracking != 'none':
                        move_line_values = [(0, 0, {
                            'lot_id': line.lot_id.id,
                            'qty_done': line.to_unbuild_qty,
                            'product_id': line.product_id.id,
                            'product_uom_id': line.product_uom.id,
                            'location_id': location_id.id,
                            'location_dest_id': location_dest_id.id,
                        })]
                        move_vals['move_line_ids'] = move_line_values
                    else:
                        move_vals['quantity_done'] = line.to_unbuild_qty

                    move_vals_list += [move_vals]
        return self.env['stock.move'].create(move_vals_list)

    def _generate_produce_moves(self):
        move_vals_list = []
        for unbuild in self:
            unbuild_raw_lines = unbuild.line_raw_ids
            if unbuild.mo_id:
                for raw_move in unbuild_raw_lines.mapped('move_line_id').mapped('move_id'):
                    raw_move_lines = unbuild_raw_lines.filtered(lambda o: o.move_line_id.move_id == raw_move)
                    to_unbuild_qty = sum(raw_move_lines.mapped('to_unbuild_qty'))

                    if float_is_zero(to_unbuild_qty, precision_rounding=raw_move.product_id.uom_id.rounding):
                        continue

                    move_vals = unbuild._prepare_move_vals(
                        raw_move.product_id, to_unbuild_qty, raw_move.product_uom, 
                        raw_move.location_dest_id, raw_move.location_id, raw_move.location_id.get_warehouse(),
                        move_id=raw_move.id)

                    if raw_move.product_id.tracking != 'none':
                        move_line_values = []
                        for line in raw_move_lines:
                            if float_is_zero(line.to_unbuild_qty, precision_rounding=line.product_id.uom_id.rounding):
                                continue
                            move_line_values += [(0, 0, {
                                'lot_id': line.lot_id.id,
                                'qty_done': line.to_unbuild_qty,
                                'product_id': line.product_id.id,
                                'product_uom_id': line.product_uom.id,
                                'location_id': raw_move.location_dest_id.id,
                                'location_dest_id': raw_move.location_id.id,
                            })]
                        move_vals['move_line_ids'] = move_line_values
                    else:
                        move_vals['quantity_done'] = to_unbuild_qty

                    move_vals_list += [move_vals]
            else:
                for line in unbuild_raw_lines:
                    if float_is_zero(line.to_unbuild_qty, precision_rounding=line.product_id.uom_id.rounding):
                        continue
                    
                    product_prod_location = line.product_id.with_company(unbuild.company_id).property_stock_production
                    location_id = product_prod_location
                    location_dest_id = unbuild.location_dest_id
                    warehouse = location_dest_id.get_warehouse()

                    move_vals = unbuild._prepare_move_vals(
                        line.product_id, line.to_unbuild_qty, line.product_uom, 
                        location_id, location_dest_id, warehouse,
                        bom_line_id=line.bom_line_id.id)

                    if line.product_id.tracking != 'none':
                        move_line_values = [(0, 0, {
                            'lot_id': line.lot_id.id,
                            'qty_done': line.to_unbuild_qty,
                            'product_id': line.product_id.id,
                            'product_uom_id': line.product_uom.id,
                            'location_id': location_id.id,
                            'location_dest_id': location_dest_id.id,
                        })]
                        move_vals['move_line_ids'] = move_line_values
                    else:
                        move_vals['quantity_done'] = line.to_unbuild_qty

                    move_vals_list += [move_vals]
        return self.env['stock.move'].create(move_vals_list)

    def action_unbuild(self):
        self.ensure_one()
        self._check_company()

        if self.mo_id and self.mo_id.state != 'done':
            raise UserError(_('You cannot unbuild a undone production order.'))

        consume_moves = self._generate_consume_moves() # byproduct & fg moves
        consume_moves._action_confirm()
        produce_moves = self._generate_produce_moves() # material moves
        produce_moves._action_confirm()

        finished_moves = consume_moves.filtered(lambda m: m.product_id == self.product_id)
        consume_moves -= finished_moves

        if any(produce_move.has_tracking != 'none' and not self.mo_id for produce_move in produce_moves):
            raise UserError(_('Some of your components are tracked, you have to specify a production order in order to retrieve the correct components.'))

        if any(consume_move.has_tracking != 'none' and not self.mo_id for consume_move in consume_moves):
            raise UserError(_('Some of your byproducts are tracked, you have to specify a production order in order to retrieve the correct byproducts.'))

        finished_moves._action_done()
        consume_moves._action_done()
        produce_moves._action_done()
        produced_move_line_ids = produce_moves.mapped('move_line_ids').filtered(lambda ml: ml.qty_done > 0)
        consume_moves.mapped('move_line_ids').write({'produce_line_ids': [(6, 0, produced_move_line_ids.ids)]})

        for move in (finished_moves | consume_moves | produce_moves):
            origin_move_lines = move.unbuild_move_id.move_line_ids

            for move_line in move.move_line_ids:
                move_line_lot_id = move_line.lot_id.id # include False
                lot_origin_move_lines = origin_move_lines.filtered(lambda o: o.lot_id.id == move_line_lot_id)
                for origin_move_line in lot_origin_move_lines:
                    origin_move_line.unbuild_qty += move_line.product_uom_id._compute_quantity(move_line.qty_done, move_line.product_id.uom_id)

        return self.write({'state': 'done'})


class MrpUnbuildLine(models.Model):
    _name = 'mrp.unbuild.line'
    _description = 'MRP Unbuild Line'

    unbuild_raw_id = fields.Many2one('mrp.unbuild', 'Unbuild Material', index=True, ondelete='cascade')
    unbuild_byproduct_id = fields.Many2one('mrp.unbuild', 'Unbuild By-Product', index=True, ondelete='cascade')
    unbuild_finished_id = fields.Many2one('mrp.unbuild', 'Unbuild Finished', index=True, ondelete='cascade')

    product_id = fields.Many2one('product.product', 'Component', required=True, check_company=False, domain="[]")
    product_uom_qty = fields.Float('Quantity', default=1.0, digits='Product Unit of Measure', required=True)
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure', required=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control")
    location_id = fields.Many2one('stock.location', string='Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', required=True)

    move_line_id = fields.Many2one('stock.move.line', string='Stock Move Line')
    bom_line_id = fields.Many2one('mrp.bom.line', string='BoM Line')
    byproduct_id = fields.Many2one('mrp.bom.byproduct', string='Byproduct')
    finished_id = fields.Many2one('mrp.bom.finished', string='Finished')

    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial Number')
    unbuild_qty = fields.Float(related='move_line_id.unbuild_qty')
    to_unbuild_qty = fields.Float(digits='Product Unit of Measure', string='To Unbuild')
    available_qty = fields.Float(compute='_compute_available_qty', string='Available Quantity')

    has_tracking = fields.Selection(related='product_id.tracking')
    lot_domain = fields.Char(compute='_compute_lot_domain')

    @api.depends('product_id', 'location_id')
    def _compute_lot_domain(self):
        Quant = self.env['stock.quant']
        for record in self:
            product = record.product_id
            lots = self.env['stock.production.lot']
            if product.tracking != 'none':
                quants = Quant._gather(product, record.location_id)
                for lot in quants.mapped('lot_id'):
                    available_qty = sum(quants.filtered(lambda o: o.lot_id == lot).mapped('available_quantity'))
                    if available_qty > 0.0:
                        lots |= lot
            record.lot_domain = json.dumps([('id', 'in', lots.ids)])

    @api.depends('product_id', 'lot_id', 'location_id')
    def _compute_available_qty(self):
        Quant = self.env['stock.quant']
        for record in self:
            record.available_qty = Quant._get_available_quantity(record.product_id, record.location_id, lot_id=record.lot_id or None, strict=True)
