from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, timedelta
from re import findall as regex_findall
from re import split as regex_split
from xlrd import open_workbook
import json
import math
import base64
from odoo.tools.misc import OrderedSet
import pytz
from collections import defaultdict
from odoo.osv import expression


class StockMove(models.Model):
    _inherit = "stock.move"

    def write(self, vals):
        if self.env.context.get('do_not_confirm_moves', False) and 'state' in vals:
            del vals['state']
        return super(StockMove, self).write(vals)

    is_adjustable_picking = fields.Boolean(
        string="Adjustable Picking", compute="_is_adjus_picking")
    package_measure_selection = fields.Selection([
        ('weight', 'Weight'),
        ('length', 'Length'),
        ('width', 'Width'),
        ('height', 'Height'),
        ('volume', 'Volume'),
    ], string="Package Measured By", default="weight")
    picking_state = fields.Selection(related='picking_id.state', store=False, string='Picking Status')
    # filter_value_ids = fields.Many2many('product.attribute.value', string="Product Attribute")
    is_existing_package = fields.Boolean(
        string='Put in Existing Packages', default=False)
    move_package_id = fields.Many2one(
        'stock.quant.package', string='Packages Existing')
    filter_move_package_ids = fields.Many2many(
        'stock.quant.package', compute='_compute_filter_move_package_ids', store=False)
    source_picking_id = fields.Many2one(
        'stock.picking', string="Source Picking")
    source_move_id = fields.Many2one('stock.move', string="Source Move")
    is_batch_shipping_packing = fields.Boolean(
        string="Is Batch Shipping Packing")
    is_batch_shipping_delivery = fields.Boolean(
        string="Is Batch Shipping Delivery")
    mr_line_id = fields.Many2one(
        'material.request.line', string="Material Request Line")
    move_line_sequence = fields.Integer(string='No')
    picking_type_code = fields.Selection(
        related='picking_id.picking_type_code', store=True)

    export_file = fields.Binary("Upload File")
    export_name = fields.Char('Export Name', size=64)

    next_serial_not_autogenerate = fields.Char(string='New Serial Number Start From')
    next_lot_not_autogenerate = fields.Char(string='New Lot Number Start From')
    is_import = fields.Boolean(string="import file")
    is_record_confirm = fields.Boolean(string='Is Record Confirmed')
    product_type = fields.Selection(related='product_id.type')

    is_serial_auto = fields.Boolean(related="product_id.is_sn_autogenerate")
    is_lot_auto = fields.Boolean(related="product_id.is_in_autogenerate")

    next_lot = fields.Char(string='First Lot')
    next_lot_count = fields.Integer(string='Number of Lots')
    qty_per_lot = fields.Integer(string="Quantity Per Lot")

    picking_code = fields.Selection(related='picking_id.picking_type_code', string='Picking Code')
    is_product_service_operation = fields.Boolean(related='product_id.is_product_service_operation',
                                                  string='Is Product Service Operation')
    is_product_service_operation_delivery = fields.Boolean(related='product_id.is_product_service_operation_delivery',
                                                           string='Is Product Service Operation Delivery')
    is_product_service_operation_receiving = fields.Boolean(related='product_id.is_product_service_operation_receiving',
                                                            string='Is Product Service Operation Receiving')
    initial_demand = fields.Float(string='Initial Demand')
    move_progress = fields.Float(string='Progress (%)')
    analytic_account_group_ids = fields.Many2many('account.analytic.tag', 'stock_move_analytic_rel', 'tag_id',
                                                  'move_id', copy=True, string="Analytic Groups",
                                                  default=lambda self: self.env.user.analytic_tag_ids.filtered(lambda a: a.company_id == self.env.company).ids)
    remaining = fields.Float(
        string="Remaining", compute="_compute_remaining", store=True)
    fulfillment = fields.Float(
        string="Fulfillment (%)", compute="_compute_fulfillment", store=True)

    current_qty = fields.Float(
        compute="_compute_current_quantity", string="Current Quantity")
    scheduled_date = fields.Datetime(string="Scheduled Date")
    responsible = fields.Many2one(
        related='picking_id.user_id', string="Responsible", store=True)
    late_time = fields.Float(
        string="Late Time", compute="_compute_late_time", store=True)
    late_time_hours = fields.Float(
        string="Late Time Hours", compute="_compute_late_time", store=True)
    process_status = fields.Selection([('late', 'Late'),
                                       ('on_time', 'On Time')], compute="_compute_process_status",
                                      string="Process Status", store=True)
    process_time = fields.Char(related="picking_id.process_time", store=True)
    process_time_hours = fields.Float(
        related="picking_id.process_time_hours", store=True)
    package_type = fields.Many2one('product.packaging', string="Package Type")
    qty_in_pack = fields.Integer(
        string="Quantity To Put in Package", default=0)
    packaging_ids = fields.Many2many(
        'product.packaging', compute="_compute_package_ids", string='Packaging')
    package_quant_ids = fields.Many2many('stock.quant', 'package_quant_receiving_note_rel', 'package_id', 'quant_id',
                                         string="Package Quant")
    measure_ids = fields.Many2many(
        'measure.for.packaging', string="Measure For Packaging", compute="_compute_measure_ids")
    product_id_domain = fields.Char(
        'Product Domain', compute="_product_id_domain")
    return_qty = fields.Float(string='Return Qty', copy=False)

    display_assign = fields.Boolean(compute='_compute_display_assign')

    # technical fields to save returned move line from return wizard
    move_lines_to_return = fields.Char()

    # fields to delete when module upgraded
    is_serial_number = fields.Char()
    is_autogenerate = fields.Char()

    transfer_out_id = fields.Many2one('stock.move', string='Transfer Out Move')

    m2m_account_move_ids = fields.Many2many('account.move', 'account_move_stock_move_rel', 'stock_move_id', 'account_move_id', string='Journal Entries', copy=False)
    initial_unit_of_measure = fields.Many2one('uom.uom', string='Initial Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")

    @api.onchange('product_id')
    def _onchange_product_id_initial_uom(self):
        if self.product_id:
            self.initial_unit_of_measure = self.product_id.uom_id.id

    @api.depends('has_tracking', 'picking_type_id.use_create_lots', 'picking_type_id.use_existing_lots', 'state')
    def _compute_display_assign(self):
        for move in self:
            move.display_assign = (
                move.has_tracking in ('lot', 'serial') and
                move.state in ('partially_available', 'assigned', 'confirmed') and
                move.picking_type_id.use_create_lots and
                not move.picking_type_id.use_existing_lots
                and not move.origin_returned_move_id.id
            )

    @api.onchange('qty_per_lot')
    def _onchange_qty_per_lot(self):
        next_lot_count = 0
        if self.qty_per_lot:
            next_lot_count = self.product_uom_qty / self.qty_per_lot

        if int(next_lot_count) < next_lot_count:
            next_lot_count = int(next_lot_count) + 1
        else:
            next_lot_count = int(next_lot_count)
        self.next_lot_count = next_lot_count

    # this function cause duplicate DO
    # def _search_picking_for_assignation(self):
    #     # override
    #     # return empty stock.picking to force _assign_picking create a new one.
    #     return self.env['stock.picking']

    @api.depends('product_id', 'package_type', 'qty_in_pack')
    def _compute_filter_move_package_ids(self):
        for record in self:
            filter_package_ids = []
            if record.qty_in_pack > 0:
                warehouse_id = record.picking_type_id.warehouse_id.id
                product_weight = 1 * record.product_id.weight
                package_ids = self.env['stock.quant.package'].search([
                    ('packaging_id', '=', record.package_type.id),
                    ('package_measure_selection', '=', 'weight'),
                    ('location_id_new', '=', record.location_dest_id.id),
                    ('warehouse_id', '=', warehouse_id),
                ])
                for package in package_ids:
                    diff_weight = package.max_weight - package.weight
                    if diff_weight >= product_weight:
                        filter_package_ids.append(package.id)
            record.filter_move_package_ids = [(6, 0, filter_package_ids)]

    def _action_done(self, cancel_backorder=False):
        if any(move._is_internal() for move in self):
            self = self.with_context(should_order_valued_types=True)
        
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)

        """ The relations still pending, need to call `invalidate_cache` """
        svls_to_do = self.filtered(lambda o: o._is_internal()).stock_valuation_layer_ids
        if svls_to_do:
            svls_to_do.invalidate_cache()

        """ `stock_account` doesnt create JE for null svl value 
        but ITR has possibility to have difference amount on its JE even though the svl value is null """
        for svl in svls_to_do.filtered(lambda o: not o.account_move_id):
            if not svl.product_id.valuation == 'real_time':
                continue
            if svl.stock_move_id._is_transit_in() or (svl.stock_move_id._is_in_and_out() and svl.move_internal_type == 'in'):
                svl.stock_move_id._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)

        return res

    def _is_adjus_picking(self):
        self.is_adjustable_picking = eval(self.env['ir.config_parameter'].sudo().get_param('is_adj_picking', 'False'))

    def _location_id(self):
        if self._is_internal():
            internal_type = self.env.context.get('internal_type')
            if self._is_transit_in(is_internal=True) or internal_type == 'in':
                return self.location_dest_id.id
            elif self._is_transit_out(is_internal=True) or internal_type == 'out':
                return self.location_id.id
        return super(StockMove, self)._location_id()

    def _prepare_common_svl_vals(self):
        res = super(StockMove, self)._prepare_common_svl_vals()
        if self._is_internal():
            move_internal_type = False
            internal_type = self.env.context.get('internal_type')
            if self._is_transit_in(is_internal=True) or internal_type == 'in':
                move_internal_type = 'in'
            elif self._is_transit_out(is_internal=True) or internal_type == 'out':
                move_internal_type = 'out'
            res['move_internal_type'] = move_internal_type
        return res

    @api.model
    def _get_valued_types(self):
        valued_types = super(StockMove, self)._get_valued_types()
        """ `in` and `out` valued_types order matters for internal transfer,
        because it's need to done out moves first. """
        if self.env.context.get('should_order_valued_types', False):
            if 'in' in valued_types and 'out' in valued_types:
                valued_types.remove('in')
                valued_types.insert(valued_types.index('out') + 1, 'in')
        return valued_types

    def _is_in(self):
        res = super(StockMove, self)._is_in()
        return res or self._is_internal_in()

    def _is_out(self):
        res = super(StockMove, self)._is_out()
        return res or self._is_internal_out()

    def _get_in_move_lines(self):
        move_lines = super(StockMove, self)._get_in_move_lines()
        is_internal = self._is_internal()
        is_transit_in = self._is_transit_in(is_internal=is_internal)
        is_in_and_out = self._is_in_and_out(is_internal=is_internal, is_transit_in=is_transit_in)
        if is_transit_in:
            move_lines |= self._get_transit_in_move_lines()
        elif is_in_and_out:
            move_lines |= self._get_internal_move_lines()
        return move_lines

    def _get_out_move_lines(self):
        move_lines = super(StockMove, self)._get_out_move_lines()
        is_internal = self._is_internal()
        is_transit_out = self._is_transit_out(is_internal=is_internal)
        is_in_and_out = self._is_in_and_out(is_internal=is_internal, is_transit_out=is_transit_out)
        if is_transit_out:
            move_lines |= self._get_transit_out_move_lines()
        elif is_in_and_out:
            move_lines |= self._get_internal_move_lines()
        return move_lines

    def _get_internal_move_lines(self):
        self.ensure_one()
        return self.move_line_ids.filtered(lambda o: o.location_id._should_be_valued() and o.location_dest_id._should_be_valued())

    def _get_transit_in_move_lines(self):
        self.ensure_one()
        transit_location = self.env.ref('equip3_inventory_masterdata.location_transit')
        return self.move_line_ids.filtered(lambda o: o.location_id == transit_location and o.location_dest_id._should_be_valued())

    def _get_transit_out_move_lines(self):
        self.ensure_one()
        transit_location = self.env.ref('equip3_inventory_masterdata.location_transit')
        return self.move_line_ids.filtered(lambda o: o.location_id._should_be_valued() and o.location_dest_id == transit_location)

    def _is_internal(self):
        """ Since Virtual Location/Transit is internal, e.g.:
        - MWH/Stock => MWH/Input
        - MWH/Stock => Virtual Location/Transit
        - Virtual Location/Transit => MWH/Stock
         """
        self.ensure_one()
        if self._get_internal_move_lines():
            return True
        return False

    def _is_transit_in(self, is_internal=None):
        """ e.g. Virtual Location/Transit => MWH/Stock """
        self.ensure_one()
        if is_internal is None:
            is_internal = self._is_internal()
        if is_internal and self._get_transit_in_move_lines():
            return True
        return False

    def _is_transit_out(self, is_internal=None):
        """ e.g. MWH/Stock => Virtual Location/Transit """
        self.ensure_one()
        if is_internal is None:
            is_internal = self._is_internal()
        if is_internal and self._get_transit_out_move_lines():
            return True
        return False

    def _is_in_and_out(self, is_internal=None, is_transit_in=None, is_transit_out=None):
        """ e.g. MWH/Stock => MWH/Input or vice versa """
        self.ensure_one()
        if is_internal is None:
            is_internal = self._is_internal()
        if is_transit_in is None:
            is_transit_in = self._is_transit_in(is_internal=is_internal)
        if is_transit_out is None:
            is_transit_out = self._is_transit_out(is_internal=is_internal)
        return is_internal and not is_transit_in and not is_transit_out

    def _is_internal_in(self, is_internal=None, is_transit_in=None, is_in_and_out=None):
        """ e.g.:
        - MWH/Stock => MWH/Input or vice versa
        - Virtual Location/Transit => MWH/Stock
         """
        self.ensure_one()
        if is_internal is None:
            is_internal = self._is_internal()
        if is_transit_in is None:
            is_transit_in = self._is_transit_in(is_internal=is_internal)

        if is_transit_in:
            return True

        if is_in_and_out is None:
            is_in_and_out = self._is_in_and_out(is_internal=is_internal, is_transit_in=is_transit_in)
        return is_in_and_out

    def _is_internal_out(self, is_internal=None, is_transit_out=None, is_in_and_out=None):
        """ e.g.:
        - MWH/Input => MWH/Stock or vice versa
        - MWH/Stock => Virtual Location/Transit
         """
        self.ensure_one()
        if is_internal is None:
            is_internal = self._is_internal()
        if is_transit_out is None:
            is_transit_out = self._is_transit_out(is_internal=is_internal)

        if is_transit_out:
            return True

        if is_in_and_out is None:
            is_in_and_out = self._is_in_and_out(is_internal=is_internal, is_transit_out=is_transit_out)

        return is_in_and_out

    def _create_in_svl(self, forced_quantity=None):
        if any(move._is_in_and_out() for move in self):
            self = self.with_context(internal_type='in')
        return super(StockMove, self)._create_in_svl(forced_quantity=forced_quantity)

    def _create_out_svl(self, forced_quantity=None):
        if any(move._is_in_and_out() for move in self):
            self = self.with_context(internal_type='out')
        return super(StockMove, self)._create_out_svl(forced_quantity=forced_quantity)

    def _sanity_check_for_valuation(self):
        """ Basic odoo doesn't allow a move to be `in` and `out` at the same time """
        moves_to_check = self.filtered(lambda o: not o._is_in_and_out())
        in_and_out_moves = self - moves_to_check
        in_and_out_moves._sanity_check_for_in_and_out_valuation()
        return super(StockMove, moves_to_check)._sanity_check_for_valuation()

    def _sanity_check_for_in_and_out_valuation(self):
        """ This is simply `_sanity_check_for_valuation` but without checking a move `_is_in` and `_is_out` """
        for move in self:
            company_src = move.mapped('move_line_ids.location_id.company_id')
            company_dst = move.mapped('move_line_ids.location_dest_id.company_id')
            try:
                if company_src:
                    company_src.ensure_one()
                if company_dst:
                    company_dst.ensure_one()
            except ValueError:
                raise UserError(_("The move lines are not in a consistent states: they do not share the same origin or destination company."))
            if company_src and company_dst and company_src.id != company_dst.id:
                raise UserError(_("The move lines are not in a consistent states: they are doing an intercompany in a single step while they should go through the intercompany transit location."))

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None,
                                  owner_id=None, strict=True):
        self.ensure_one()
        if not package_id and self.picking_id.picking_type_code == 'outgoing' and self.picking_id.delivery_package_level_ids:
            package_level_ids = self.picking_id.delivery_package_level_ids.filtered(
                lambda r: self.product_id.id in r.package_id.quant_ids.mapped('product_id').ids)
            if package_level_ids:
                package_id = package_level_ids[0].package_id
        res = super(StockMove, self)._update_reserved_quantity(need=need, available_quantity=available_quantity,
                                                               location_id=location_id, lot_id=lot_id,
                                                               package_id=package_id, owner_id=owner_id, strict=strict)
        self.picking_id._reset_sequence()
        return res


    @api.depends('product_id', 'product_description')
    def _compute_total_packages(self):
        for line in self:
            line.product_description = False
            if line.picking_code == 'incoming':
                if not line.product_id.description_pickingin:
                    line.product_description = line.name
                else:
                    line.product_description = line.name + ' ' + (
                        line.product_id.description_pickingin)

            if line.picking_code == 'outgoing':
                if not line.product_id.description_pickingout:
                    line.product_description = line.name
                else:
                    line.product_description = line.name + ' ' + (
                        line.product_id.description_pickingout)
            if line.picking_code == 'internal':
                if not line.description_picking:
                    line.product_description = line.name
                else:
                    line.product_description = line.name + ' ' + (
                        line.description_picking)

    @api.model
    def default_get(self, fields):
        res = super(StockMove, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'move_ids_without_package' in context_keys:
                if len(self._context.get('move_ids_without_package')) > 0:
                    next_sequence = len(self._context.get(
                        'move_ids_without_package')) + 1
            res.update({'move_line_sequence': next_sequence})
            if 'move_line_nosuggest_ids' in context_keys:
                if len(self._context.get('move_line_nosuggest_ids')) > 0:
                    next_sequence = len(self._context.get(
                        'move_line_nosuggest_ids')) + 1
            res.update({'move_line_sequence': next_sequence})
        return res

    @api.depends('location_id')
    def _product_id_domain(self):
        for rec in self:
            rec.product_id_domain = False
            quant_ids = self.env['stock.quant'].search(
                [('location_id', '=', rec.location_id.id)])
            product_ids = self.env['product.product'].search(
                [('id', 'in', (quant_ids.product_id.ids))])
            rec.product_id_domain = json.dumps([('type', 'in', ['product', 'consu', 'asset']), '|', (
                'company_id', '=', False), ('company_id', '=', rec.company_id.id), ('id', '=', product_ids.ids)])

    @api.onchange('package_type')
    def _compute_measure_ids(self):
        for rec in self:
            measure_ids = self.env['product.packaging'].search(
                [('id', '=', rec.package_type.id)])
            rec.measure_ids = [(6, 0, measure_ids.measure_ids.ids)]

    def _compute_package_ids(self):
        for rec in self:
            packaging_ids = self.env['product.packaging'].search(
                [('product_id', 'in', self.product_id.ids)])
            rec.packaging_ids = [(6, 0, packaging_ids.ids)]

    @api.depends('product_uom_qty', 'quantity_done')
    def _compute_remaining(self):
        for rec in self:
            rec.remaining = rec.product_uom_qty - rec.quantity_done

    @api.depends('date', 'scheduled_date')
    def _compute_process_status(self):
        for record in self:
            if record.date and record.scheduled_date:
                if record.date > record.scheduled_date:
                    record.process_status = 'late'
                elif record.date <= record.scheduled_date:
                    record.process_status = 'on_time'

    @api.onchange('product_id', 'picking_type_id')
    def onchange_product(self):
        if self.picking_code == 'incoming':
            if self.product_id:
                self.package_type = self.product_id.def_packaging_id
        else:
            return super(StockMove, self).onchange_product()

    def action_put_in_package(self):
        for record in self:
            if record.quantity_done <= 0 and record.qty_in_pack <= 0:
                raise ValidationError(
                    "Please add 'Done' quantities to the picking to create a new pack.")
            if record.qty_in_pack <= 0:
                raise ValidationError(
                    "Quantity to Put in Package must have a value in it and not 0.")
            if record.picking_id:
                if len(record.picking_id.move_line_nosuggest_ids) > 1:
                    move_line_sequence = len(
                        record.picking_id.move_line_nosuggest_ids) + 1
                else:
                    move_line_sequence = 1
            product_weight = record.product_id.weight
            product_total_weight = record.qty_in_pack * product_weight
            package_total_weight = record.qty_in_pack * product_weight
            final_package_id = False
            warehouse_id = record.picking_type_id.warehouse_id.id
            package_ids = self.env['stock.quant.package'].search([
                ('packaging_id', '=', record.package_type.id),
                ('package_measure_selection', '=', 'weight'),
                ('location_id_new', '=', record.location_dest_id.id),
                ('warehouse_id', '=', warehouse_id),
            ])
            import math
            Quant = self.env['stock.quant']
            empty_packages = []
            lot_name = ''
            remaining_qty_in_pack = record.qty_in_pack
            if record.is_existing_package:
                if record.is_existing_package and record.move_package_id:
                    remaining_weight = record.move_package_id.max_weight - record.move_package_id.weight
                    if remaining_weight <= 0 or remaining_qty_in_pack <= 0:
                        pass
                    else:
                        available_qty_slot = math.floor(
                            remaining_weight / product_weight)
                        if available_qty_slot > 0:
                            if available_qty_slot > remaining_qty_in_pack:
                                available_qty_slot = remaining_qty_in_pack
                            remaining_qty_in_pack -= available_qty_slot
                            package_weight = available_qty_slot * product_weight
                            empty_packages.append(
                                {'package': record.move_package_id, 'qty_done': available_qty_slot, 'weight': package_weight})
                for package in package_ids:
                    if record.package_measure_selection == "weight":
                        remaining_weight = package.max_weight - package.weight
                        if remaining_weight <= 0 or remaining_qty_in_pack <= 0 or (package.id == record.move_package_id.id):
                            continue
                        available_qty_slot = math.floor(
                            remaining_weight / product_weight)
                        if available_qty_slot > 0:
                            if available_qty_slot > remaining_qty_in_pack:
                                available_qty_slot = remaining_qty_in_pack
                            remaining_qty_in_pack -= available_qty_slot
                            package_weight = available_qty_slot * product_weight
                            empty_packages.append(
                                {'package': package, 'qty_done': available_qty_slot, 'weight': package_weight})
            if not empty_packages:
                packages = []
                package_product_weight = 0
                last_package_weight = 0
                counter = 0
                for rec in range(1, math.ceil(record.qty_in_pack) + 1):
                    counter += 1
                    package_product_weight += (1 * product_weight)
                    if package_product_weight <= record.package_type.max_weight:
                        last_package_weight = package_product_weight
                    if package_product_weight > record.package_type.max_weight:
                        packages.append({
                            'package_measure_selection': 'weight',
                            'packaging_id': record.package_type.id,
                            'location_id_new': record.location_dest_id.id,
                            'warehouse_id': warehouse_id,
                            'weight': last_package_weight,
                            'qty_done': (last_package_weight / product_weight),
                            'barcode_packaging': record.package_type.packages_barcode_prefix if record.package_type.packages_barcode_prefix else '' + record.package_type.current_sequence if record.package_type.current_sequence else '',
                            'create_automatic': True,
                        })
                        package_diff_weight = (
                            package_product_weight - last_package_weight)
                        if counter == record.qty_in_pack:
                            packages.append({
                                'package_measure_selection': 'weight',
                                'packaging_id': record.package_type.id,
                                'location_id_new': record.location_dest_id.id,
                                'warehouse_id': warehouse_id,
                                'weight': package_diff_weight,
                                'qty_done': (package_diff_weight / product_weight),
                                'barcode_packaging': record.package_type.packages_barcode_prefix if record.package_type.packages_barcode_prefix else '' + record.package_type.current_sequence if record.package_type.current_sequence else '',
                                'create_automatic': True,
                            })
                            last_package_weight = 0
                            package_product_weight = 0
                        else:
                            last_package_weight = package_diff_weight
                            package_product_weight = package_diff_weight
                if last_package_weight > 0:
                    packages.append({
                        'package_measure_selection': 'weight',
                        'packaging_id': record.package_type.id,
                        'location_id_new': record.location_dest_id.id,
                        'warehouse_id': warehouse_id,
                        'weight': last_package_weight,
                        'qty_done': (last_package_weight / product_weight),
                        'barcode_packaging': record.package_type.packages_barcode_prefix if record.package_type.packages_barcode_prefix else '' + record.package_type.current_sequence if record.package_type.current_sequence else '',
                        'create_automatic': True,
                    })
                lot_data = []
                move_line_data = []
                for line in record.move_line_nosuggest_ids:
                    lot_data.append(
                        {'lot_name': line.lot_name, 'qty': line.qty_done})
                for package_line_data in packages:
                    qty_done = package_line_data.get('qty_done')
                    package_line_data.pop('qty_done')
                    final_package_id = self.env['stock.quant.package'].create(
                        package_line_data)
                    lot_name = False
                    if record.product_id.tracking != 'none' and not lot_data:
                        lot_names = self._generate_lot_numbers(1)
                        if lot_names:
                            lot_name = lot_names[0]
                    final_qty_done = qty_done
                    if lot_data:
                        qty_counter = 0
                        for line in lot_data:
                            if qty_counter >= final_qty_done or line['qty'] == 0:
                                continue
                            elif line['qty'] > final_qty_done:
                                difference = final_qty_done - qty_counter
                                line['qty'] -= difference
                                qty_counter += difference
                                move_line_data.append((0, 0, {
                                    'move_line_sequence': move_line_sequence,
                                    'location_dest_id': record.location_dest_id.id,
                                    'location_id': record.location_id.id,
                                    'picking_id': record.picking_id.id,
                                    'result_package_id': final_package_id.id,
                                    'qty_done': difference,
                                    'product_uom_id': record.product_id.uom_id.id,
                                    'product_id': record.product_id.id,
                                    'lot_name': line['lot_name'],
                                }))
                                move_line_sequence += 1
                            elif line['qty'] <= final_qty_done:
                                qty_counter += line['qty']
                                difference = qty_counter - final_qty_done
                                move_line_data.append((0, 0, {
                                    'move_line_sequence': move_line_sequence,
                                    'location_dest_id': record.location_dest_id.id,
                                    'location_id': record.location_id.id,
                                    'picking_id': record.picking_id.id,
                                    'result_package_id': final_package_id.id,
                                    'qty_done': difference if difference > 0 else line['qty'],
                                    'product_uom_id': record.product_id.uom_id.id,
                                    'product_id': record.product_id.id,
                                    'lot_name': line['lot_name'],
                                }))
                                line['qty'] = difference if difference > 0 else 0
                                move_line_sequence += 1
                    else:
                        move_line_data.append((0, 0, {
                            'move_line_sequence': move_line_sequence,
                            'location_dest_id': record.location_dest_id.id,
                            'location_id': record.location_id.id,
                            'picking_id': record.picking_id.id,
                            'result_package_id': final_package_id.id,
                            'qty_done': final_qty_done,
                            'product_uom_id': record.product_id.uom_id.id,
                            'product_id': record.product_id.id,
                            'lot_name': lot_name,
                        }))
                        move_line_sequence += 1
                if record.move_line_nosuggest_ids:
                    record.move_line_nosuggest_ids.unlink()
                record.move_line_nosuggest_ids = move_line_data
                if record.product_id.tracking != 'none':
                    record.picking_id._get_next_sequence_and_serial(
                        moves=record)
            elif empty_packages:
                for empty_package_line in empty_packages:
                    lot_name = False
                    if record.product_id.tracking != 'none':
                        lot_names = self._generate_lot_numbers(1)
                        if lot_names:
                            lot_name = lot_names[0]
                    qty_done = empty_package_line.get('qty_done')
                    record.move_line_nosuggest_ids = [(0, 0, {
                        'move_line_sequence': move_line_sequence,
                        'location_dest_id': record.location_dest_id.id,
                        'location_id': record.location_id.id,
                        'picking_id': record.picking_id.id,
                        'result_package_id': empty_package_line.get('package').id,
                        'qty_done': qty_done,
                        'product_uom_id': record.product_id.uom_id.id,
                        'product_id': record.product_id.id,
                        'lot_name': lot_name,
                    })]
                    move_line_sequence += 1
                if record.product_id.tracking != 'none':
                    record.picking_id._get_next_sequence_and_serial(
                        moves=record)
                if remaining_qty_in_pack > 0:
                    packages = []
                    package_product_weight = 0
                    last_package_weight = 0
                    counter = 0
                    for rec in range(1, math.ceil(remaining_qty_in_pack) + 1):
                        counter += 1
                        package_product_weight += (1 * product_weight)
                        if package_product_weight <= record.package_type.max_weight:
                            last_package_weight = package_product_weight
                        if package_product_weight > record.package_type.max_weight:
                            packages.append({
                                'package_measure_selection': 'weight',
                                'packaging_id': record.package_type.id,
                                'location_id_new': record.location_dest_id.id,
                                'warehouse_id': warehouse_id,
                                'weight': last_package_weight,
                                'barcode_packaging': record.package_type.packages_barcode_prefix if record.package_type.packages_barcode_prefix else '' + record.package_type.current_sequence if record.package_type.current_sequence else '',
                                'create_automatic': True,
                            })
                            package_diff_weight = (
                                package_product_weight - last_package_weight)
                            if counter == record.qty_in_pack:
                                packages.append({
                                    'package_measure_selection': 'weight',
                                    'packaging_id': record.package_type.id,
                                    'location_id_new': record.location_dest_id.id,
                                    'warehouse_id': warehouse_id,
                                    'weight': package_diff_weight,
                                    'barcode_packaging': record.package_type.packages_barcode_prefix if record.package_type.packages_barcode_prefix else '' + record.package_type.current_sequence if record.package_type.current_sequence else '',
                                    'create_automatic': True,
                                })
                                last_package_weight = 0
                                package_product_weight = 0
                            else:
                                last_package_weight = package_diff_weight
                                package_product_weight = package_diff_weight
                    if last_package_weight > 0:
                        packages.append({
                            'package_measure_selection': 'weight',
                            'packaging_id': record.package_type.id,
                            'location_id_new': record.location_dest_id.id,
                            'warehouse_id': warehouse_id,
                            'weight': last_package_weight,
                            'barcode_packaging': record.package_type.packages_barcode_prefix if record.package_type.packages_barcode_prefix else '' + record.package_type.current_sequence if record.package_type.current_sequence else '',
                            'create_automatic': True,
                        })
                    for package_line_data in packages:
                        qty_done = package_line_data.get('weight')
                        final_package_id = self.env['stock.quant.package'].create(
                            package_line_data)
                        lot_name = False
                        if record.product_id.tracking != 'none':
                            lot_names = self._generate_lot_numbers(1)
                            if lot_names:
                                lot_name = lot_names[0]
                        record.move_line_nosuggest_ids = [(0, 0, {
                            'move_line_sequence': move_line_sequence,
                            'location_dest_id': record.location_dest_id.id,
                            'location_id': record.location_id.id,
                            'picking_id': record.picking_id.id,
                            'result_package_id': final_package_id.id,
                            'qty_done': qty_done * (1 / product_weight),
                            'product_uom_id': record.product_id.uom_id.id,
                            'product_id': record.product_id.id,
                            'lot_name': lot_name,
                        })]
                        move_line_sequence += 1
                    if record.product_id.tracking != 'none':
                        record.picking_id._get_next_sequence_and_serial(
                            moves=record)
            record.quantity_done = sum(
                record.move_line_nosuggest_ids.mapped('qty_done'))
            for line in record.move_line_nosuggest_ids.filtered(lambda r: not r.is_quant_update):
                line.is_quant_update = True
                Quant.with_context({'move_id': record.id})._update_available_quantity(line.product_id,
                                                                                      line.location_dest_id,
                                                                                      line.qty_done, lot_id=line.lot_id,
                                                                                      package_id=line.result_package_id,
                                                                                      owner_id=line.owner_id)
        return True


    @api.depends('date', 'scheduled_date')
    def _compute_late_time(self):
        for record in self:
            record.late_time_hours = 0
            record.late_time = 0
            if record.date and record.scheduled_date:
                time = record.date - record.scheduled_date
                hours = time.total_seconds() / 3600
                record.late_time_hours = hours
                final_hour = round(hours / 24, 2)
                record.late_time = final_hour

    @api.depends('product_id', 'location_id')
    def _compute_current_quantity(self):
        for record in self:
            stock_quant_ids = self.env['stock.quant'].search([('product_id', '=', record.product_id.id),
                                                              ('location_id', '=', record.location_id.id)])
            record.current_qty = sum(
                stock_quant_ids.mapped('available_quantity'))

    @api.depends('initial_demand', 'quantity_done', 'remaining', 'product_uom_qty', 'move_line_nosuggest_ids',
                 'move_line_nosuggest_ids.qty_done')
    def _compute_fulfillment(self):
        for record in self:
            if record.initial_demand > 0:
                record.fulfillment = (
                    record.quantity_done / record.initial_demand) * 100

    @api.constrains('fulfillment')
    def _check_fulfillment(self):
        for rec in self:
            product_limit = rec.product_id.categ_id.product_limit

            if rec.product_id.product_limit == 'limit':
                product_limit = rec.product_id.product_limit

            if product_limit == 'no_limit':
                if rec.fulfillment > 100 and rec.product_id.tracking == 'serial':
                    raise ValidationError(
                        'Serial Numbers are already Assigned.')
                elif rec.fulfillment > 100 and rec.product_id.tracking == 'lot':
                    raise ValidationError('Lot Numbers are already Assigned.')

    def _prepare_move_split_vals(self, qty):
        res = super(StockMove, self)._prepare_move_split_vals(qty)
        res['initial_demand'] = self.initial_demand
        res['move_progress'] = self.move_progress
        return res

    def _generate_serial_move_line_commands(self, lot_names, origin_move_line=None):
        commands = super(StockMove, self)._generate_serial_move_line_commands(lot_names, origin_move_line=origin_move_line)
        for no, command in enumerate(commands):
            command[-1]['move_line_sequence'] = no
        return commands

    def _generate_lot_move_line_commands(self, lot_names, origin_move_line=None):
        self.ensure_one()

        quantity = self.qty_per_lot
        if quantity <= 0:
            raise ValidationError(_("Quantity per lot must be positive!"))

        if origin_move_line:
            location_dest = origin_move_line.location_dest_id
        else:
            location_dest = self.location_dest_id._get_putaway_strategy(self.product_id)

        move_line_vals = {
            'picking_id': self.picking_id.id,
            'location_dest_id': location_dest.id or self.location_dest_id.id,
            'location_id': self.location_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'qty_done': quantity,
        }

        move_lines_commands = [(5,)]
        for no, lot_name in enumerate(lot_names):
            move_line_cmd = dict(move_line_vals, move_line_sequence=no+1, lot_name=lot_name)
            move_lines_commands.append((0, 0, move_line_cmd))

        qty_mod = self.product_uom_qty % quantity
        if qty_mod and move_lines_commands:
            move_lines_commands[-1][-1]['qty_done'] = qty_mod
        return move_lines_commands

    def _generate_lot_numbers(self, next_serial_count=False):
        self.ensure_one()
        product_id = self.product_id or self.env['product.product']
        is_autogenerate = product_id.is_in_autogenerate
        product_prefix = product_id.in_prefix
        product_suffix = product_id.in_suffix

        if is_autogenerate:
            next_lot = self.next_lot
        else:
            last_digit_check = self.next_lot_not_autogenerate and self.next_lot_not_autogenerate[-1] or ''
            if not last_digit_check.isdigit():
                raise ValidationError(
                    _('New Lot Number Start From must contain digits behind it.'))
            next_lot = self.next_lot_not_autogenerate

        if product_suffix:
            next_lot = next_lot.replace(product_suffix, '')

        caught_initial_number = regex_findall("\d+", next_lot)
        if not caught_initial_number:
            raise UserError(
                _('The serial number must contain at least one digit.'))

        initial_number = str(caught_initial_number[-1])
        padding = len(initial_number)
        splitted = regex_split(initial_number, next_lot)

        prefix = initial_number.join(splitted[:-1])
        if is_autogenerate and product_prefix:
            prefix = product_prefix

        suffix = splitted[-1]
        if product_suffix:
            suffix = product_suffix

        if is_autogenerate:
            initial_number = int(product_id.in_current_sequence)
        else:
            initial_number = self.next_lot_not_autogenerate

        lot_names = []
        if is_autogenerate:
            for i in range(int(next_serial_count)):
                lot_names.append('%s%s%s' % (
                    prefix,
                    str(initial_number + i).zfill(padding),
                    suffix,
                ))
            return lot_names
        else:
            get_number_actual = ''.join(filter(str.isdigit, initial_number))
            lot_name = str(initial_number).replace(get_number_actual, "")
            padding = len(str(get_number_actual))

            for i in range(int(next_serial_count)):
                get_number = int(get_number_actual) + i
                show_val = str(get_number).zfill(padding)
                lot_names.append('%s%s' % (
                    lot_name,
                    show_val,
                ))
            return lot_names

    def action_show_details(self):
        self.ensure_one()
        action = super().action_show_details()
        picking_type_id = self.picking_type_id or self.picking_id.picking_type_id
        action['context']['default_export_file'] = False
        action['context']['default_export_name'] = False
        action['context']['default_is_import'] = False
        return action

    @api.onchange('export_file')
    def onchage_import_button_validate(self):
        if self.export_file:
            self.is_import = True
        else:
            self.is_import = False

    def import_file_data(self):
        self.ensure_one()

        self.action_import_template()
        self.export_file = False
        self.export_name = False
        self.is_import = False
        self.is_record_confirm = True

        return True

    def action_full_quantity_done(self):
        for record in self:
            if record.move_line_ids:
                for line in record.move_line_ids:
                    qty_done = round(record.product_uom_qty /
                                     len(record.move_line_ids), 2)
                    line.qty_done = qty_done
            else:
                record.quantity_done = record.product_uom_qty
        return True

    def action_partial_quantity_done(self):
        self.ensure_one()

        context = dict(self.env.context) or {}
        context.update(
            {'default_product_id': self.product_id.id, 'default_move_id': self.id})
        view = self.env.ref(
            'equip3_inventory_operation.view_partial_quantity_done_wizard')
        return {
            'name': _('Service Product Partial Done'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'partial.quantity.done',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    def action_save(self):
        self.ensure_one()

        if self.move_line_nosuggest_ids:
            self.is_record_confirm = True
        else:
            self.is_record_confirm = False

        return True

    def _assign_return_moves(self):
        UoM = self.env['uom.uom']
        Lot = self.env['stock.production.lot']
        StockMove = self.env['stock.move']

        assigned_moves_ids = OrderedSet()
        partially_available_moves_ids = OrderedSet()
        for move in self:
            lines = json.loads(move.move_lines_to_return)['lines']
            rounding = move.product_id.uom_id.rounding
            location_id = move.location_id
            product_uom = move.product_id.uom_id

            taken_quantity = 0.0
            for line in lines:
                line_uom = UoM.browse(line['uom_id'])
                need = line_uom._compute_quantity(line['quantity'], product_uom)
                lot_id = Lot.browse(line['lot_id'])
                available_quantity = move._get_available_quantity(location_id, lot_id=lot_id, strict=True)
                if float_is_zero(available_quantity, precision_rounding=rounding):
                    continue
                taken_quantity += move._update_reserved_quantity(need, available_quantity, location_id, lot_id)

            if float_is_zero(move.product_qty - taken_quantity, precision_rounding=rounding):
                assigned_moves_ids.add(move.id)
            else:
                partially_available_moves_ids.add(move.id)

        StockMove.browse(partially_available_moves_ids).write({'state': 'partially_available'})
        StockMove.browse(assigned_moves_ids).write({'state': 'assigned'})
        self.mapped('picking_id')._check_entire_pack()

    def _action_assign(self):
        for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available'] and m.product_id.tracking == 'lot'):
            move.write({
                'next_lot_count': 1,
                'qty_per_lot': move.product_uom_qty
            })

        moves_to_ignore = self.filtered(lambda m: not m.move_orig_ids or not m.move_lines_to_return)
        moves_to_process = self - moves_to_ignore
        super(StockMove, moves_to_ignore)._action_assign()
        moves_to_process._assign_return_moves()

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None, owner_id=None, strict=True):
        self.ensure_one()
        context = self.env.context
        product = self.product_id
        if not context.get('skip_transfer_check', False) and self.picking_id and self.picking_id.is_transfer_in and product.tracking in ('lot', 'serial'):
            transfer_out = self.env['stock.picking'].search([
                ('transfer_id', '=', self.picking_id.transfer_id.id),
                ('is_transfer_out', '=', True)
            ], limit=1)
            move_lines_out = transfer_out.move_lines.filtered(lambda o: o.product_id == product).filtered(lambda o: o.state == 'done').mapped('move_line_ids')
            if need == sum(move_lines_out.mapped('qty_done')):
                taken_qty = 0.0
                for move_line_out in move_lines_out:
                    out_available_quantity = self._get_available_quantity(location_id, lot_id=move_line_out.lot_id, package_id=package_id)
                    if out_available_quantity <= 0:
                        continue
                    taken_qty += self.with_context(skip_transfer_check=True)._update_reserved_quantity(move_line_out.qty_done, out_available_quantity, location_id, lot_id=move_line_out.lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
                return taken_qty

        if context.get('picking_type_code') != 'outgoing' and not context.get('default_origin'):
            return super()._update_reserved_quantity(need, available_quantity, location_id, lot_id, package_id, owner_id, strict)

        if not lot_id:
            lot_id = self.env['stock.production.lot']
        if not package_id:
            package_id = self.env['stock.quant.package']
        if not owner_id:
            owner_id = self.env['res.partner']

        taken_quantity = min(available_quantity, need)

        if not strict and self.product_id.uom_id != self.product_uom:
            taken_quantity_move_uom = self.product_id.uom_id._compute_quantity(
                taken_quantity, self.product_uom, rounding_method='DOWN')
            taken_quantity = self.product_uom._compute_quantity(
                taken_quantity_move_uom, self.product_id.uom_id, rounding_method='HALF-UP')

        quants = []
        rounding = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')

        if self.product_id.tracking == 'serial':
            if float_compare(taken_quantity, int(taken_quantity), precision_digits=rounding) != 0:
                taken_quantity = 0

        try:
            with self.env.cr.savepoint():
                if not float_is_zero(taken_quantity, precision_rounding=self.product_id.uom_id.rounding):
                    boss = self.picking_id.partner_id
                    scheduled_date = self.picking_id.scheduled_date
                    domain = [('is_customer', '=', boss.id),
                              '|',
                              ('category_ids', '=', self.product_id.categ_id.id),
                              ('product_ids', '=',  self.product_id.id)]

                    stock_life = self.env['stock.life'].search(domain)
                    if not stock_life:

                        quants = self.env['stock.quant']._update_reserved_quantity(
                            self.product_id, location_id, taken_quantity, lot_id=lot_id,
                            package_id=package_id, owner_id=owner_id, strict=strict
                        )

                    if stock_life:
                        quants = self.env['stock.quant']._update_reserved_quantity_life(
                            self.product_id, location_id, taken_quantity, lot_id=lot_id,
                            package_id=package_id, owner_id=owner_id, strict=strict, boss=boss, scheduled_date=scheduled_date
                        )

        except UserError:
            taken_quantity = 0

        # Find a candidate move line to update or create a new one.
        for reserved_quant, quantity in quants:
            to_update = self.move_line_ids.filtered(
                lambda ml: ml._reservation_is_updatable(quantity, reserved_quant))
            if to_update:
                uom_quantity = self.product_id.uom_id._compute_quantity(
                    quantity, to_update[0].product_uom_id, rounding_method='HALF-UP')
                uom_quantity = float_round(
                    uom_quantity, precision_digits=rounding)
                uom_quantity_back_to_product_uom = to_update[0].product_uom_id._compute_quantity(
                    uom_quantity, self.product_id.uom_id, rounding_method='HALF-UP')
            if to_update and float_compare(quantity, uom_quantity_back_to_product_uom, precision_digits=rounding) == 0:
                to_update[0].with_context(
                    bypass_reservation_update=True).product_uom_qty += uom_quantity
            else:
                if self.product_id.tracking == 'serial':
                    for i in range(0, int(quantity)):
                        self.env['stock.move.line'].create(self._prepare_move_line_vals(
                            quantity=1, reserved_quant=reserved_quant))
                else:
                    self.env['stock.move.line'].create(self._prepare_move_line_vals(
                        quantity=quantity, reserved_quant=reserved_quant))
        return taken_quantity

    def action_unlink_data(self):
        self.ensure_one()

        if not self.is_record_confirm:
            self.move_line_nosuggest_ids.unlink()
        self.export_file = False
        self.export_name = False
        self.is_import = False
        if self.picking_id.picking_type_code == "incoming" \
                and self.package_quant_ids:
            packages = self.package_quant_ids.mapped('package_id')
            self.package_quant_ids.sudo().unlink()
            packages.write({'move_location_id': self.location_dest_id.id})
        return True

    def action_import_template(self):
        self.ensure_one()

        if self.export_name:
            import_name_extension = self.export_name.split('.')[1]
            if import_name_extension not in ['xls', 'xlsx']:
                raise ValidationError('File format must be in xlsx or xls.')
        context = dict(self.env.context) or {}
        if not self.export_file:
            context.update({'show_upload_file': False})
        else:
            workbook = open_workbook(
                file_contents=base64.decodestring(self.export_file))
            for sheet in workbook.sheets():
                line_list = []
                for count in range(1, sheet.nrows):
                    line_vals = {}
                    line = sheet.row_values(count)
                    if line[1] != '':
                        package_id = self.env['stock.quant.package'].search(
                            [('name', 'ilike', line[1])], limit=1)
                        if not package_id:
                            package_id = self.env['stock.quant.package'].create(
                                {'name': line[1]})
                        line_vals['result_package_id'] = package_id and package_id.id or False
                    is_float = False
                    if line[2] != '':
                        try:
                            is_float = float(line[2])
                        except ValueError:
                            pass
                        if not is_float:
                            raise ValidationError(
                                _("Done Value Must be in digits!"))
                        line_vals['qty_done'] = line[2]
                    categories_id = self.product_id.categ_id

                    if self.is_serial_auto and self.product_id.tracking == 'serial':
                        current_name = ''
                        if self.product_id.is_use_product_code == True:
                            if self.product_id.sn_prefix:
                                current_name = self.product_id.default_code + self.product_id.sn_prefix
                            else:
                                current_name = self.product_id.default_code
                        else:
                            current_name = self.product_id.sn_prefix
                        if current_name and line[0] and not line[0].startswith(current_name):
                            raise ValidationError(
                                _("The Lot/Serial Number that you imported must match prefix of the product Serial Number Master Data."))
                        if line[0] and self.product_id.suffix and not line[0].endswith(self.product_id.suffix):
                            raise ValidationError(
                                _("The Lot/Serial Number that you imported must match suffix of the product Serial Number Master Data."))

                    if self.is_lot_auto and self.product_id.tracking == 'lot':
                        current_name = ''
                        if self.product_id.is_in_use_product_code == True:
                            if self.product_id.in_prefix:
                                current_name = self.product_id.default_code + self.product_id.in_prefix
                            else:
                                current_name = self.product_id.default_code
                        else:
                            current_name = self.product_id.in_prefix
                        if current_name and line[0] and not line[0].startswith(current_name):
                            raise ValidationError(
                                _("The Lot/Serial Number that you imported must match prefix of the product Serial Number Master Data."))
                        if line[0] and self.product_id.in_suffix and not line[0].endswith(self.product_id.in_suffix):
                            raise ValidationError(
                                _("The Lot/Serial Number that you imported must match suffix of the product Serial Number Master Data."))

                    line_vals['lot_name'] = line[0]
                    line_vals['product_id'] = self.product_id.id
                    line_vals['product_uom_id'] = self.product_uom.id
                    if self.product_id.use_expiration_date:
                        line_vals['expiration_date'] = fields.Datetime.today() + datetime.timedelta(
                            days=self.product_id.expiration_time)
                        line_vals['alert_date'] = fields.Datetime.today() + datetime.timedelta(
                            days=self.product_id.expiration_time) - datetime.timedelta(days=self.product_id.alert_time)
                    if line[0] != '':
                        line_list.append((0, 0, line_vals))
            self.write({'move_line_nosuggest_ids': line_list})
            self.export_file = False
            context.update({'show_upload_file': True})
        return self.with_context(context).action_show_details()

    def _generate_lot_serial_numbers(self):
        self.ensure_one()
        product = self.product_id
        if product._is_sn_auto():
            self._generate_serial_numbers_auto()
        elif product._is_lot_auto():
            self._generate_lots_auto()

    def _generate_lots_auto(self):
        self.ensure_one()
        product = self.product_id
        if not product._is_lot_auto():
            return

        product_qty = self.product_uom_qty
        last_qty_should_be_revised = False

        self.write({
            'next_lot': product._get_next_lot_and_serial(),
            # 'next_lot_count': int(product_qty) / int(self.qty_per_lot)
            'next_lot_count': math.ceil(int(product_qty) / int(self.qty_per_lot))
        })

        self._generate_lots()
        product._update_current_sequence(moves=self)

    def _generate_serial_numbers_auto(self):
        self.ensure_one()
        product = self.product_id
        if not product._is_sn_auto():
            return

        product_qty = self.product_qty
        last_qty_should_be_revised = False

        next_serial_count = int(product_qty)
        if int(product_qty) < product_qty:
            last_qty_should_be_revised = True
            next_serial_count += 1

        self.write({
            'next_serial': product._get_next_lot_and_serial(),
            'next_serial_count': next_serial_count
        })

        self._generate_serial_numbers()

        if last_qty_should_be_revised:
            self.move_line_ids[-1].qty_done = product_qty - int(product_qty)

        product._update_current_sequence(moves=self)

    def _generate_serial_numbers(self, next_serial_count=False):
        """ This method will generate `lot_name` from a string (field
        `next_serial`) and create a move line for each generated `lot_name`.
        """
        self.ensure_one()

        if not next_serial_count:
            next_serial_count = self.next_serial_count
        # We look if the serial number contains at least one digit.
        caught_initial_number = regex_findall("\d+", self.next_serial)
        if not caught_initial_number:
            raise UserError(_('The serial number must contain at least one digit.'))
        # We base the serie on the last number find in the base serial number.
        initial_number = caught_initial_number[-1]
        padding = len(initial_number)
        # We split the serial number to get the prefix and suffix.
        splitted = regex_split(initial_number, self.next_serial)
        # initial_number could appear several times in the SN, e.g. BAV023B00001S00001
        prefix = initial_number.join(splitted[:-1])
        suffix = splitted[-1]
        initial_number = int(initial_number)

        lot_names = []
        i = 0
        while True:
            lot_name = '%s%s%s' % (
                prefix,
                str(initial_number + i).zfill(padding),
                suffix
            )
            if not self.env['stock.production.lot'].search([
                ('name', '=', lot_name),
                ('product_id', '=', self.product_id.id)
            ], limit=1):
                lot_names.append(lot_name)
            
            if len(lot_names) == next_serial_count:
                break
            i += 1
        
        move_lines_commands = self._generate_serial_move_line_commands(lot_names)
        self.write({'move_line_ids': move_lines_commands})
        return True

    def _generate_lots(self, next_lot_count=False):
        """ This method will generate `lot_name` from a string (field
        `next_lot`) and create a move line for each generated `lot_name`.
        """
        self.ensure_one()

        if not next_lot_count:
            next_lot_count = self.next_lot_count
        # We look if the lot contains at least one digit.
        caught_initial_number = regex_findall("\d+", self.next_lot)
        if not caught_initial_number:
            raise UserError(_('The lot must contain at least one digit.'))
        # We base the serie on the last number find in the base lot.
        initial_number = caught_initial_number[-1]
        padding = len(initial_number)
        # We split the lot to get the prefix and suffix.
        splitted = regex_split(initial_number, self.next_lot)
        # initial_number could appear several times in the SN, e.g. BAV023B00001S00001
        prefix = initial_number.join(splitted[:-1])
        suffix = splitted[-1]
        initial_number = int(initial_number)

        lot_names = []
        i = 0
        while True:
            lot_name = '%s%s%s' % (
                prefix,
                str(initial_number + i).zfill(padding),
                suffix
            )
            if not self.env['stock.production.lot'].search([
                ('name', '=', lot_name),
                ('product_id', '=', self.product_id.id)
            ], limit=1):
                lot_names.append(lot_name)
            
            if len(lot_names) == next_lot_count:
                break
            i += 1
            
        move_lines_commands = self._generate_lot_move_line_commands(lot_names)
        self.write({'move_line_ids': move_lines_commands})
        return True

    def action_assign_serial_show_details(self):
        if self.product_id._is_sn_auto():
            self.next_serial = self.product_id._get_next_lot_and_serial()
        return super(StockMove, self).action_assign_serial_show_details()

    def action_assign_lot_show_details(self):
        self.ensure_one()
        if self.product_id._is_lot_auto():
            self.next_lot = self.product_id._get_next_lot_and_serial()
        if not self.next_lot:
            raise UserError(_("You need to set a Lot before generating more."))
        self._generate_lots()
        return self.action_show_details()

    def action_assign_serial(self):
        action = super(StockMove, self).action_assign_serial()
        if self.product_id._is_sn_auto():
            action['context']['default_next_serial_number'] = self.product_id._get_next_lot_and_serial()
        return action

    def action_clear_lines_show_details(self):
        self.ensure_one()
        if self.picking_code == 'incoming':
            if self.picking_type_id.show_reserved:
                self.move_line_ids = self.move_line_ids
                if self.move_line_ids:
                    query = '''DELETE FROM stock_move_line WHERE id IN %s'''
                    self.env.cr.execute(query, (tuple(self.move_line_ids.ids),))
                else:
                    raise ValidationError(_('There is no lot / serial number to clear'))
            else:
                self.move_line_ids = self.move_line_nosuggest_ids
                if self.move_line_ids:
                    query = '''DELETE FROM stock_move_line WHERE id IN %s'''
                    self.env.cr.execute(query, (tuple(self.move_line_nosuggest_ids.ids),))
                else:
                    raise ValidationError(_('There is no lot / serial number to clear'))
            return self.action_show_details()
        else:
            if self.picking_type_id.show_reserved:
                move_lines = self.move_line_ids
            else:
                move_lines = self.move_line_nosuggest_ids
            move_lines.unlink()
            return self.action_show_details()
    
    # def action_clear_lines_show_details(self):
    #     self.ensure_one()
    #     if self.picking_type_id.show_reserved:
    #         move_lines = self.move_line_ids
    #     else:
    #         move_lines = self.move_line_nosuggest_ids
    #     move_lines.unlink()
    #     return self.action_show_details()

    def action_assign_lot_number(self):
        pass

    def unlink(self):
        approval = self.picking_id
        res = super(StockMove, self).unlink()
        approval._reset_sequence()
        return res

    @api.onchange('sequence')
    def set_sequence_line(self):
        for record in self:
            record.picking_id._reset_sequence()

    # @api.model
    # def create(self, vals):
    #     res = super(StockMove, self).create(vals)
    #     res.picking_id._reset_sequence()
    #     return res

    def _account_entry_move(self, qty, description, svl_id, cost):
        if not self._is_internal():
            return super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
        return self._account_entry_move_internal(qty, description, svl_id, cost)

    def _account_entry_move_internal(self, qty, description, svl_id, cost):
        self.ensure_one()

        is_interwarehouse_transfer_journal = eval(self.env['ir.config_parameter'].get_param('interwarehouse_transfer_journal', 'False'))
        
        if not is_interwarehouse_transfer_journal:
            return False

        if self.product_id.type != 'product':
            return False
        
        if self.restrict_partner_id:
            return False

        company_from = self._is_out() and self.mapped('move_line_ids.location_id.company_id') or False
        company_to = self._is_in() and self.mapped('move_line_ids.location_dest_id.company_id') or False

        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()

        if self._is_in_and_out():
            svl = self.env['stock.valuation.layer'].browse(svl_id)
            if svl.move_internal_type == 'in': # 1 JE for direct ITR
                self.with_company(company_from).with_context(internal_type=svl.move_internal_type)._create_account_move_line(acc_valuation, acc_valuation, journal_id, qty, description, svl_id, cost)
        else:
            transit_account = self.product_id.categ_id.stock_transfer_transit_account_id.id
            if self._is_transit_out():
                self.with_company(company_from)._create_account_move_line(acc_valuation, transit_account, journal_id, qty, description, svl_id, cost * -1)
            else:
                self.with_company(company_to)._create_account_move_line(transit_account, acc_valuation, journal_id, qty, description, svl_id, cost)

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description):
        if (self._is_in_and_out() or self._is_transit_in()) and self.product_id.with_company(self.company_id).cost_method == 'standard':
            return self._generate_valuation_lines_data_internal(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description)
        return super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description)

    def _generate_valuation_lines_data_internal(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, description):
        # This method returns a dictionary to provide an easy extension hook to modify the valuation lines (see purchase for an example)
        self.ensure_one()

        currency = self.company_id.currency_id

        if self._is_in_and_out():
            out_svls = self.stock_valuation_layer_ids.filtered(lambda o: o.location_id == self.location_id)
            out_value = abs(sum(out_svls.mapped('value')))
            if self.env.context.get('internal_type') == 'out':
                in_value = out_value
            else:
                in_svls = self.stock_valuation_layer_ids.filtered(lambda o: o.location_id == self.location_dest_id)
                in_value = sum(in_svls.mapped('value'))
        else:
            out_svls = self.transfer_out_id.stock_valuation_layer_ids
            in_svls = self.stock_valuation_layer_ids
            out_value = abs(sum(out_svls.mapped('value')))
            in_value = sum(in_svls.mapped('value'))

        if out_value == in_value and currency.is_zero(out_value):
            return {}

        debit_line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
            'debit': in_value,
            'credit': 0,
            'account_id': debit_account_id,
        }

        credit_line_vals = {
            'name': description,
            'product_id': self.product_id.id,
            'quantity': qty,
            'product_uom_id': self.product_id.uom_id.id,
            'ref': description,
            'partner_id': partner_id,
            'credit': out_value,
            'debit': 0,
            'account_id': credit_account_id,
        }

        rslt = {}
        if not currency.is_zero(out_value):
            rslt['credit_line_vals'] = credit_line_vals
        if not currency.is_zero(in_value):
            rslt['debit_line_vals'] = debit_line_vals

        if in_value != out_value:
            # for supplier returns of product in average costing method, in anglo saxon mode
            diff_amount = in_value - out_value
            
            if diff_amount > 0.0:
                price_diff_account = self.product_id.categ_id.property_account_creditor_price_difference_categ
            else:
                price_diff_account = self.product_id.categ_id.property_account_debitor_price_difference_categ

            if not price_diff_account:
                raise UserError(_('You don\'t have any %s price difference account defined on your product category. You must define one before processing this operation.' % (diff_amount > 0 and 'gain' or 'loss',)))

            rslt['price_diff_line_vals'] = {
                'name': self.name,
                'product_id': self.product_id.id,
                'quantity': qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
                'credit': diff_amount > 0 and diff_amount or 0,
                'debit': diff_amount < 0 and -diff_amount or 0,
                'account_id': price_diff_account.id,
            }
        return rslt

    def product_price_update_get_price_unit(self):
        first_fifo_price_unit = 0.0
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        if is_cost_per_warehouse and self.product_id.cost_method == 'fifo' and self._is_transit_in() and self.move_line_ids:
            first_fifo_price_unit = self.move_line_ids[0].price_unit
        return first_fifo_price_unit or super(StockMove, self).product_price_update_get_price_unit()

    def _create_account_move_line(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        self.ensure_one()

        AccountMove = self.env['account.move'].with_context(default_journal_id=journal_id)
        journal = self.env['account.journal'].browse(journal_id)

        move_lines = self._prepare_account_move_line(qty, cost, credit_account_id, debit_account_id, description)

        if move_lines:
            date = self._context.get('force_period_date', fields.Date.context_today(self))
            # From module stock_force_date_app
            if self.env.user.has_group('stock_force_date_app.group_stock_force_date'):
                if self.picking_id.force_date:
                    date = self.picking_id.force_date.date()
                if self.inventory_id.force_date:
                    date = self.inventory_id.force_date.date()

            branch = False
            if self.picking_id.branch_id:
                branch = self.picking_id.branch_id.id
            if self.inventory_id.branch_id:
                branch = self.inventory_id.branch_id.id

            if not branch:
                branch = self.env.branch.id

            period = self.env['sh.account.period'].sudo().search([('date_start', '<=', date), ('date_end', '>=', date)], limit=1)
            svl = self.env['stock.valuation.layer'].browse(svl_id)

            svls_to_assign = [svl_id]
            if self._is_in_and_out():
                svls_to_assign = svl.stock_move_id.stock_valuation_layer_ids.ids

            state = 'posted'
            linked_svl = svl.stock_valuation_layer_id
            if period.state == 'done' and linked_svl:
                period = self.env['sh.account.period'].sudo().search([
                    ('date_start', '<=', linked_svl.stock_move_id.date),
                    ('date_end', '>=', linked_svl.stock_move_id.date),
                    ('state', '!=', 'done')
                ], limit=1)
                state = 'draft'

            datetime_now = datetime.now()
            context = dict(self._context) or {}

            timezone_waktu = '+00:00' #set default avoid error
            # ini jika dari picking biasa
            if self.env.context.get('tz'):
                currenttimezone = pytz.timezone(self.env.context.get('tz'))
                user_datetime = datetime.now(currenttimezone)
                timezone_str = user_datetime.strftime('%z')

                if '+' in timezone_str:
                    timezone_waktu = '-' + user_datetime.strftime('%z')[1:3]

                elif '-' in timezone_str:
                    timezone_waktu = '-' + user_datetime.strftime('%z')[1:3]

                else:
                    timezone_waktu = '+00:00'

            # ini jika dari cron
            if self.env.context.get('create_picking_from_cron'):
                # timezone_system = self.env['res.users'].browse(SUPERUSER_ID).tz
                # currenttimezone = pytz.timezone(timezone_system)
                # user_datetime = datetime.now(currenttimezone)
                # timezone_str = user_datetime.strftime('%z')

                # if '+' in timezone_str:
                #     timezone_waktu = '-' + user_datetime.strftime('%z')[1:3]

                # elif '-' in timezone_str:
                #     timezone_waktu = '-' + user_datetime.strftime('%z')[1:3]

                # else:
                timezone_waktu = '+00:00'


            move_data = {
                'journal_id': journal_id,
                'date': datetime_now,
                'date_obj' : date,
                'ref': description,
                'stock_move_id': self.id,
                'move_type': 'entry',

                'create_uid': self.env.user.id,
                'write_uid': self.env.user.id,
                'name': journal.sequence_id.next_by_id(),
                'state': state,
                'company_id': self.company_id.id,
                'currency_id': self.company_id.currency_id.id,
                'auto_reverse_date_mode': 'custom',
                'branch_id': branch or None,
                'period_id': period.id or None,
                'fiscal_year': period.fiscal_year_id.id or None,
                'is_from_query': True
            }

            pos_general_installed = self.env['ir.module.module'].search([('name', '=', 'equip3_pos_general'), ('state', '=', 'installed')])
            if pos_general_installed:
                query_create_move = """
                    INSERT INTO account_move (create_date, write_date, journal_id, date, ref, stock_move_id, move_type, create_uid, write_uid, name, state, company_id, currency_id, auto_reverse_date_mode, branch_id, pos_branch_id, period_id, fiscal_year, is_from_query)
                    VALUES (%s + %s, %s + %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """
                values_create_move = [
                    datetime_now,
                    timezone_waktu,
                    datetime_now,
                    timezone_waktu,
                    move_data['journal_id'],
                    move_data['date_obj'],
                    move_data['ref'],
                    move_data['stock_move_id'],
                    move_data['move_type'],

                    move_data['create_uid'],
                    move_data['write_uid'],
                    move_data['name'],
                    move_data['state'],
                    move_data['company_id'],
                    move_data['currency_id'],
                    move_data['auto_reverse_date_mode'],
                    move_data['branch_id'],
                    move_data['branch_id'],
                    move_data['period_id'],
                    move_data['fiscal_year'],
                    move_data['is_from_query']
                ]
            else:
                query_create_move = """
                    INSERT INTO account_move (create_date, write_date, journal_id, date, ref, stock_move_id, move_type, create_uid, write_uid, name, state, company_id, currency_id, auto_reverse_date_mode, branch_id, period_id, fiscal_year, is_from_query)
                    VALUES (%s + %s, %s + %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                """
                values_create_move = [
                    datetime_now,
                    timezone_waktu,
                    datetime_now,
                    timezone_waktu,
                    move_data['journal_id'],
                    move_data['date'],
                    move_data['ref'],
                    move_data['stock_move_id'],
                    move_data['move_type'],

                    move_data['create_uid'],
                    move_data['write_uid'],
                    move_data['name'],
                    move_data['state'],
                    move_data['company_id'],
                    move_data['currency_id'],
                    move_data['auto_reverse_date_mode'],
                    move_data['branch_id'],
                    move_data['period_id'],
                    move_data['fiscal_year'],
                    move_data['is_from_query'],
                ]

            should_create_move = not self.picking_id or (self.picking_id and not self.picking_id.account_move_id)
            if should_create_move:
                self.env.cr.execute(query_create_move, values_create_move)
                # print('EXECUTE 1 ➡ ACCOUNT_MOVE : DONE')
                am_id = self.env.cr.fetchone()[0]
                self.picking_id.account_move_id = am_id
            else:
                am_id = self.picking_id.account_move_id.id

            if self.inventory_id:
                self.inventory_id.account_move_ids = [(4, am_id)]

            query_update_svl = """
                UPDATE stock_valuation_layer
                SET stock_move_id = %s, account_move_id = %s
                WHERE id IN %s;
            """
            values_update_svl = [move_data['stock_move_id'], am_id, tuple(svls_to_assign)]
            self.env.cr.execute(query_update_svl, values_update_svl)

            # if pos_general_installed:
            #     query = query_insert_account_move_line = """
            #         INSERT INTO account_move_line (create_date, write_date, create_uid, write_uid, company_id, currency_id, name, product_id, quantity, product_uom_id, ref, partner_id, debit, credit, balance, amount_currency, account_id, branch_id, move_id, period_id, fiscal_year, date, company_currency_id, is_from_query)
            #         VALUES
            #     """
            # else:
            query = query_insert_account_move_line = """
                INSERT INTO account_move_line (create_date, write_date, create_uid, write_uid, company_id, currency_id, name, product_id, quantity, product_uom_id, ref, partner_id, debit, credit, balance, amount_currency, account_id, branch_id, move_id, period_id, fiscal_year, date, company_currency_id, is_from_query)
                VALUES
            """

            values = []
            count = 0
            for move_line in move_lines:
                count += 1
                aml = move_line[2]

                aml['create_uid'] = self.env.user.id
                aml['write_uid'] = self.env.user.id
                aml['company_id'] = self.company_id.id
                aml['currency_id'] = self.company_id.currency_id.id

                conversion_rate = self.company_id.currency_id._convert(aml['debit']-aml['credit'], self.purchase_line_id.order_id.currency_id, self.company_id, self.date)
                purchase_currency = self.purchase_line_id.order_id.currency_id.id
                company_currency = self.purchase_line_id.order_id.company_id.currency_id.id
                amount_currency = conversion_rate if purchase_currency != company_currency else aml['debit']-aml['credit']


                if count > 1:
                    query += ","

                if pos_general_installed:
                    query += """
                        (%s + %s, %s + %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                else:
                    query += """
                    (%s + %s, %s + %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values.extend([
                    #26
                    datetime_now, # create date
                    timezone_waktu, # create date
                    datetime_now, # write_date
                    timezone_waktu, # write_date
                    aml['create_uid'], # create uid
                    aml['write_uid'], # write uid
                    aml['company_id'], # company id
                    purchase_currency if purchase_currency != company_currency else aml['currency_id'], # currency id

                    aml['name'], # name
                    aml['product_id'], # product id
                    aml['quantity'], # quantity
                    aml['product_uom_id'], #product uom id

                    aml['ref'], # ref
                    aml['partner_id'] or None, # partner
                    aml['debit'], # debit
                    aml['credit'], # credit
                    aml['debit']-aml['credit'], # balance
                    amount_currency, # amount currency

                    aml['account_id'], # account id
                    move_data['branch_id'] or None, # branch id

                    am_id, # move id

                    move_data['period_id'], # period id
                    move_data['fiscal_year'], # fiscal year
                    move_data['date'], #date
                    aml['currency_id'], # company currency
                    move_data['is_from_query'] # is from query
                ])
                # if pos_general_installed:
                #     values.extend([
                #         move_data['branch_id'] or None])
            self.env.cr.execute(query, values)
            # print('EXECUTE 2 ➡ ACCOUNT_MOVE_LINE : DONE', values)

            if should_create_move:
                for analytic in self.picking_id.branch_id.analytic_tag_ids:
                    self.env.cr.execute("""
                        INSERT INTO account_analytic_tag_account_move_rel (account_move_id, account_analytic_tag_id)
                        VALUES (%s, %s)
                    """, (am_id, analytic.id,))

            self.env.cr.execute("""
                UPDATE account_move am set amount_total = sub.total, amount_total_signed = sub.total
                from (SELECT sum(debit) as total, move_id from account_move_line aml where move_id = %s group by move_id) as sub
                where sub.move_id = am.id
                and am.id = %s
            """, (am_id, am_id,))

            if self.picking_id:
                self.env.cr.execute("SELECT * FROM account_move_stock_move_rel WHERE account_move_id = %s AND stock_move_id = %s", (am_id, self.id))
                exists = self.env.cr.fetchall()
                if not exists:
                    self.env.cr.execute("INSERT INTO account_move_stock_move_rel (account_move_id, stock_move_id) VALUES (%s, %s)", (am_id, self.id))
    
    def action_get_account_moves(self):
        self.ensure_one()
        action_data = super(StockMove, self).action_get_account_moves()
        old_domain = action_data.get('domain', [])
        new_domain = expression.OR([old_domain, [('id', 'in', self.m2m_account_move_ids.ids)]])
        action_data['domain'] = new_domain
        return action_data


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _prepare_in_svl_vals(self, quantity, unit_cost):
        res = super(StockMoveLine, self)._prepare_in_svl_vals(quantity, unit_cost)
        if self.product_id.cost_method == 'standard':
            res['standard_remaining_qty'] = res.get('quantity', 0.0)

        move = self.move_id
        is_internal = move._is_internal()
        if is_internal:
            res.update({
                'svl_source_line_id': self.svl_source_line_id.id,
                'svl_source_id': self.svl_source_id.id,
            })
        return res

    def _prepare_out_svl_vals(self, quantity, fifo_vals):
        res = super(StockMoveLine, self)._prepare_out_svl_vals(quantity, fifo_vals)
        res.update({
            'svl_source_line_id': fifo_vals.get('svl_source_line_id', False),
            'svl_source_id': fifo_vals.get('svl_source_id', False),
        })
        return res


class TmpStockMove(models.TransientModel):
    _inherit = 'tmp.stock.move'

    def _is_in_and_out(self, is_internal=None, is_transit_in=None, is_transit_out=None):
        return False


class TmpStockMoveLine(models.TransientModel):
    _inherit = 'tmp.stock.move.line'

    price_unit = fields.Float('Unit Price', help="Technical field used to record the product cost set by the user during a picking confirmation (when costing "
        "method used is 'average price' or 'real'). Value given in company currency and in product uom.", copy=False)

    svl_source_line_id = fields.Many2one('stock.valuation.layer.line', string='Valuation Line Source')
    svl_source_id = fields.Many2one(related='svl_source_line_id.svl_id')

    def _prepare_in_svl_vals(self, quantity, unit_cost):
        res = super(TmpStockMoveLine, self)._prepare_in_svl_vals(quantity, unit_cost)
        if self.product_id.cost_method == 'standard':
            res['standard_remaining_qty'] = res.get('quantity', 0.0)
        
        res.update({
            'svl_source_line_id': self.svl_source_line_id.id,
            'svl_source_id': self.svl_source_id.id,
        })
        return res

    def _prepare_out_svl_vals(self, quantity, fifo_vals):
        res = super(TmpStockMoveLine, self)._prepare_out_svl_vals(quantity, fifo_vals)
        res.update({
            'svl_source_line_id': fifo_vals.get('svl_source_line_id', False),
            'svl_source_id': fifo_vals.get('svl_source_id', False),
        })
        return res
