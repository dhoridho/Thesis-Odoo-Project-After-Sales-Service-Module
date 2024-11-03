
from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    name = fields.Char(
        'Name',
        default='/',
        copy=False, required=True, readonly=True)
    internal_name = fields.Char(
        'Repair Reference',
        default='/',
        copy=False, required=True, readonly=True)
    state = fields.Selection(selection_add=[
        ('availability', 'Waiting for availability'),
        ('draft', 'Draft')
    ], ondelete={'availability': 'set default'})
    delivery_order_id = fields.Many2one("stock.picking", "Delivery Order")
    is_create_delivery_order = fields.Boolean()
    repair_order_ids = fields.Many2many('repair.order', 'repair_order_product_id',
                                        'repair_id', 'product_id', string="Repaired Order", readonly="1")
    available_qty = fields.Float(
        related='product_id.qty_available', string="Available Quantity")
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")
    internal_repair = fields.Boolean(default=False)
    source_doc = fields.Char('Source Document')
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial',
        help="Products repaired are all belonging to this lot")
    repair_type = fields.Selection([("customer_repair", "Customer Repair"), (
        "internal_repair", "Internal Repair")], string='Repair Type')
    check_parts_availability = fields.Boolean()
    check_availability = fields.Boolean()
    hide_button = fields.Boolean(compute="compute_hide_button")
    product_qty = fields.Float(
        'Product Quantity',
        default=1.0, digits='Product Unit of Measure',
        readonly=True, required=True, states={'draft': [('readonly', False)]})
    warehouse_id = fields.Many2one(
        'stock.warehouse', related='location_id.warehouse_id')

    @api.onchange('location_id')
    def get_warehouse(self):
        for line in self.operations:
            if line.type == 'add':
                line.location_id = self.location_id.id
            if line.type == 'remove':
                line.location_dest_id = self.location_id.id

    @api.model
    def create(self, vals):
        seq = self.env['ir.sequence'].sudo().search(
            [('name', '=', 'Customer Repair')])
        seq1 = self.env['ir.sequence'].sudo().search(
            [('name', '=', 'Internal Repair')])
        repair_seq = self.env['ir.sequence'].sudo().search(
            [('name', '=', 'Repair Order')])
        if repair_seq:
            repair_seq.unlink()

        context = self.env.context.get('default_repair_type')
        if context == 'internal_repair' or vals['repair_type'] == 'internal_repair':
            internal_seq = self.env['ir.sequence'].next_by_code(
                'internal.repair')
            # seq1.number_next_actual += 1
            vals['name'] = internal_seq
        if context == 'customer_repair' or vals['repair_type'] == 'customer_repair':
            customer_seq = self.env['ir.sequence'].next_by_code(
                'customer.repair')
            # seq.number_next_actual += 1
            vals['name'] = customer_seq
        res = super(RepairOrder, self).create(vals)
        res.repair_order_ids = [(6, 0, res.ids)]

        return res

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.guarantee_limit = False
        # if (self.product_id and self.lot_id and self.lot_id.product_id != self.product_id) or not self.product_id:
        #     self.lot_id = False
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id

    def action_valuation(self):
        self.ensure_one()
        move_ids = self.operations.mapped('move_id')
        return {
            'name': _('Valuation'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.valuation.layer',
            'target': 'current',
            'domain': [('stock_move_id', 'in', move_ids.ids)],
        }

    def action_accounting_entries(self):
        self.ensure_one()
        return {
            'name': _('Accounting Entries'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'target': 'current',
            'domain': [('repair_id', '=', self.id), ('move_type', '=', 'entry')],
        }

    def action_repair_start(self):
        res = super(RepairOrder, self).action_repair_start()
        self.start_date = datetime.now()

        return res

    def action_repair_cancel_draft(self):
        self.ensure_one()

        res = super(RepairOrder, self).action_repair_cancel_draft()
        self.hide_button = True
        self.check_availability = False
        return res

    def action_repair_end(self):
        self = self.with_context(end_repair=True, repair_id=self.id)
        res = super(RepairOrder, self).action_repair_end()
        type_list = []
        sum_of_products = 0
        add_type_sum = 0
        for line in self.operations:
            if line.type == 'add':
                type_list.append('add')
                add_type_sum += line.product_id.standard_price * line.product_uom_qty
                sum_of_products += (line.product_id.standard_price *
                                    line.product_uom_qty) + self.product_id.standard_price
            if line.type == 'remove':
                type_list.append('remove')
                if not line.move_id:
                    move = self.env['stock.move']
                    move_id = move.create({
                        'name': self.name,
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.product_uom_qty,
                        'product_uom': line.product_uom.id,
                        'partner_id': self.address_id.id,
                        'location_id': line.location_id.id,
                        'location_dest_id': line.location_dest_id.id,
                        'repair_id': self.id,
                        'origin': self.name,
                        'company_id': self.company_id.id,
                    })
                    if line.lot_id:
                        move.move_line_ids.lot_id = line.lot_id
                    move_id._action_done()
                    move_id.write({'state': 'done'})
                    line.write({'move_id': move_id.id, 'state': 'done'})
                    # print('move',move_id)

        for line in self.operations:
            if 'add' not in type_list and 'remove' in type_list:
                stock_valuation = self.env['stock.valuation.layer'].search(
                    [('product_id', '=', line.product_id.id), ('stock_move_id', '=', line.move_id.id)])
                # print('sv1', stock_valuation)
                if not stock_valuation:
                    description = line.move_id.reference + ' - ' + line.product_id.name
                    vals2 = {
                        'create_date': datetime.now(),
                        'product_id': line.product_id.id,
                        'stock_move_id': line.move_id.id,
                        'warehouse_id': self.location_id.warehouse_id.id,
                        'quantity': self.product_qty,
                        'uom_id': self.product_id.uom_id.id,
                        'unit_cost': line.product_id.standard_price,
                        'value': line.product_uom_qty * line.product_id.standard_price,
                        'remaining_qty': line.product_id.qty_available,
                        'company_id': self.company_id.id,
                        'description': description,
                    }
                    svl2 = self.env['stock.valuation.layer'].sudo().create(
                        vals2)

            if 'add' in type_list and 'remove' in type_list:
                stock_valuation = self.env['stock.valuation.layer'].search(
                    [('product_id', '=', line.product_id.id), ('stock_move_id', '=', line.move_id.id)])
                # print('sv2', stock_valuation)
                if stock_valuation:
                    for sv in stock_valuation:
                        sv.value = sv.quantity * line.product_id.standard_price
                if not stock_valuation:
                    description = line.move_id.reference + ' - ' + line.product_id.name
                    if line.type == 'add':
                        vals3 = {
                            'create_date': datetime.now(),
                            'product_id': line.product_id.id,
                            'stock_move_id': line.move_id.id,
                            'warehouse_id': self.location_id.warehouse_id.id,
                            'quantity': -(line.product_uom_qty),
                            'uom_id': line.product_id.uom_id.id,
                            'unit_cost': line.product_id.standard_price,
                            'value': -(line.product_uom_qty) * line.product_id.standard_price,
                            'remaining_qty': line.product_id.qty_available,
                            'company_id': self.company_id.id,
                            'description': description,
                        }
                        svl3 = self.env['stock.valuation.layer'].sudo().create(
                            vals3)
                    if line.type == 'remove':
                        vals1 = {
                            'create_date': datetime.now(),
                            'product_id': line.product_id.id,
                            'stock_move_id': line.move_id.id,
                            'warehouse_id': self.location_id.warehouse_id.id,
                            'quantity': line.product_uom_qty,
                            'uom_id': line.product_id.uom_id.id,
                            'unit_cost': line.product_id.standard_price,
                            'value': line.product_uom_qty * line.product_id.standard_price,
                            'remaining_qty': line.product_id.qty_available,
                            'company_id': self.company_id.id,
                            'description': description,
                        }
                        svl1 = self.env['stock.valuation.layer'].sudo().create(
                            vals1)
                if 'add' in type_list and 'remove' not in type_list:
                    stock_valuation = self.env['stock.valuation.layer'].search(
                        [('product_id', '=', line.product_id.id), ('stock_move_id', '=', line.move_id.id)])
                    # print('sv3', stock_valuation)
                    if not stock_valuation:
                        description = line.move_id.reference + ' - ' + line.product_id.name
                        vals4 = {
                            'create_date': datetime.now(),
                            'product_id': line.product_id.id,
                            'stock_move_id': line.move_id.id,
                            'warehouse_id': self.location_id.warehouse_id.id,
                            'quantity': -(self.product_qty),
                            'uom_id': self.product_id.uom_id.id,
                            'unit_cost': line.product_id.standard_price,
                            'value': -(line.product_uom_qty) * line.product_id.standard_price,
                            'remaining_qty': line.product_id.qty_available,
                            'company_id': self.company_id.id,
                            'description': description,
                        }
                        svl2 = self.env['stock.valuation.layer'].sudo().create(
                            vals4)

        for line in self.operations:
            if 'add' in type_list and 'remove' in type_list:
                description = line.move_id.reference + ' - ' + self.product_id.name
                vals1 = {
                    'create_date': datetime.now(),
                    'product_id': self.product_id.id,
                    'stock_move_id': line.move_id.id,
                    'warehouse_id': self.location_id.warehouse_id.id,
                    'quantity': -(self.product_qty),
                    'uom_id': self.product_id.uom_id.id,
                    'unit_cost': self.product_id.standard_price,
                    'value': -(self.product_qty) * self.product_id.standard_price,
                    'remaining_qty': self.product_id.qty_available,
                    'company_id': self.company_id.id,
                    'description': description,
                }
                svl1 = self.env['stock.valuation.layer'].sudo().create(vals1)

                vals = {
                    'create_date': datetime.now(),
                    'product_id': self.product_id.id,
                    'stock_move_id': line.move_id.id,
                    'warehouse_id': self.location_id.warehouse_id.id,
                    'quantity': self.product_qty,
                    'uom_id': self.product_id.uom_id.id,
                    'unit_cost': self.product_id.standard_price,
                    'value': add_type_sum,
                    'remaining_qty': self.product_id.qty_available,
                    'company_id': self.company_id.id,
                    'description': description,
                }
                svl = self.env['stock.valuation.layer'].sudo().create(vals)
            if 'add' in type_list and 'remove' not in type_list:
                description = line.move_id.reference + ' - ' + self.product_id.name
                vals = {
                    'create_date': datetime.now(),
                    'product_id': self.product_id.id,
                    'stock_move_id': line.move_id.id,
                    'warehouse_id': self.location_id.warehouse_id.id,
                    'quantity': -(self.product_qty),
                    'uom_id': self.product_id.uom_id.id,
                    'unit_cost': self.product_id.standard_price,
                    'value': -(self.product_qty) * self.product_id.standard_price,
                    'remaining_qty': self.product_id.qty_available,
                    'company_id': self.company_id.id,
                    'description': description,
                }
                svl = self.env['stock.valuation.layer'].sudo().create(vals)
                vals1 = {
                    'create_date': datetime.now(),
                    'product_id': self.product_id.id,
                    'stock_move_id': line.move_id.id,
                    'warehouse_id': self.location_id.warehouse_id.id,
                    'quantity': self.product_qty,
                    'uom_id': self.product_id.uom_id.id,
                    'unit_cost': sum_of_products,
                    'value': self.product_qty * sum_of_products,
                    'remaining_qty': self.product_id.qty_available,
                    'company_id': self.company_id.id,
                    'description': description,
                }
                svl1 = self.env['stock.valuation.layer'].sudo().create(vals1)
            if 'add' not in type_list and 'remove' in type_list:
                description = line.move_id.reference + ' - ' + self.product_id.name
                vals1 = {
                    'create_date': datetime.now(),
                    'product_id': self.product_id.id,
                    'stock_move_id': line.move_id.id,
                    'warehouse_id': self.location_id.warehouse_id.id,
                    'quantity': -(self.product_qty),
                    'uom_id': self.product_id.uom_id.id,
                    'unit_cost': self.product_id.standard_price,
                    'value': -(self.product_qty) * self.product_id.standard_price,
                    'remaining_qty': self.product_id.qty_available,
                    'company_id': self.company_id.id,
                    'description': description,
                }
                svl1 = self.env['stock.valuation.layer'].sudo().create(vals1)

                vals = {
                    'create_date': datetime.now(),
                    'product_id': self.product_id.id,
                    'stock_move_id': line.move_id.id,
                    'warehouse_id': self.location_id.warehouse_id.id,
                    'quantity': self.product_qty,
                    'uom_id': self.product_id.uom_id.id,
                    'unit_cost': self.product_id.standard_price,
                    'value': 0,
                    'remaining_qty': self.product_id.qty_available,
                    'company_id': self.company_id.id,
                    'description': description,
                }
                svl = self.env['stock.valuation.layer'].sudo().create(vals)
            break

        return res

    def action_item_available(self):
        self.ensure_one()

        repair_order_vals = {"state": "draft"}
        if self.is_create_delivery_order:
            picking_type_id = self.env["stock.picking.type"].search([("name", "=", "Delivery Orders"),
                                                                    ("default_location_src_id",
                                                                     "=", self.location_id.id),
                                                                    ("code", "=", "outgoing")])
            vals = {
                "picking_type_code": "outgoing",
                "is_expired_tranfer": False,
                "location_id": self.location_id.id,
                "is_from_repair_order": True,
                "picking_type_id": picking_type_id.id,
                "move_line_ids_without_package": [(0, 0, {"product_id": self.product_id.id,
                                                          "product_uom_id": self.product_uom.id,
                                                          "location_id": self.location_id.id,
                                                          "location_dest_id": self.env.ref("stock.stock_location_customers").id,
                                                          "product_uom_qty": self.product_qty})]
            }
            delivery_order_id = self.env["stock.picking"].with_context({"picking_type_code": "outgoing",
                                                                        "outgoing": False,
                                                                        "incoming_location": True}).create(vals)
            delivery_order_id.action_confirm()
            repair_order_vals.update(
                {"delivery_order_id": delivery_order_id.id})

        self.write(repair_order_vals)
        return True

    def action_cancel_repair(self):
        self.ensure_one()

        self.state = "cancel"

    def action_create_delivery_order(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Delivery Order',
            'res_model': 'stock.picking',
            'res_id': self.delivery_order_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'current',
        }

    def action_check_availability(self):
        self.ensure_one()

        view = self.env.ref(
            'equip3_inventory_other_operations.check_ro_availability_wizard_form_view')
        wiz = self.env['ro.check_availability'].create(
            {'repair_order_id': self.id})
        # wiz.repair_order_id = record
        record = wiz.repair_order_id
        throw_error = False
        if len(record.operations) == 1:
            for line in record.operations:
                # stock_in_loc = self.env['stock.quant'].search([('product_id', '=', line.product_id.id), ('location_id', '=', line.location_id.id)]).mapped('inventory_quantity')
                stock_in_loc = self.env['stock.quant'].search(
                    [('product_id', '=', line.product_id.id), ('location_id', '=', line.location_id.id)])
                # print('stock_in_loc', sum(stock_in_loc.mapped('available_quantity')))
                qty_in_loc = sum(stock_in_loc.mapped('available_quantity'))
                if line.type == 'add':
                    if qty_in_loc < line.product_uom_qty:
                        required_qty = line.product_uom_qty - qty_in_loc
                        throw_error = True
                        wiz.message_id = 'There is not enough stock for {} on location {}, you need {} more.'.format(
                            line.product_id.name, line.location_id.display_name, required_qty)
                        # record.check_parts_availability = True
        # print(shshs)
        if len(record.operations) > 1:
            multiple_lines = []
            multiple_lines.append('There is not enough stock for: \n')
            count = 1
            for line in record.operations:
                if line.type == 'add':
                    stock_in_loc = self.env['stock.quant'].search(
                        [('product_id', '=', line.product_id.id), ('location_id', '=', line.location_id.id)])
                    qty_in_loc = sum(stock_in_loc.mapped('available_quantity'))
                    if qty_in_loc < line.product_uom_qty:
                        required_qty = line.product_uom_qty - qty_in_loc
                        # if line.product_id.qty_available == 0:
                        throw_error = True
                        multiple_lines.append('{}. {} on location {}, you need {} more. \n'.format(
                            count, line.product_id.name, line.location_id.display_name, required_qty))
                        count += 1
            wiz.message_id = ' '.join(str(x) for x in multiple_lines)
            # raise UserError(_(' '.join(str(x) for x in multiple_lines)))
        self.check_availability = True
        if throw_error == True:
            return {
                'name': _('User Error'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'ro.check_availability',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'target': 'new',
                'res_id': wiz.id,
                'context': self.env.context
            }

    def action_submit_material_request(self):
        material_req_id = self.env['material.request'].create(
            {'requested_by': self.user_id.id, 'company_id': self.company_id.id, 'source_document': self.name, 'schedule_date': datetime.now()})
        view = self.env.ref(
            'equip3_inventory_operation.material_request_form_view')
        return {
            'name': _('Material Request'),
            'view_mode': 'form',
            'res_model': 'material.request',
            'view_id': view.id,
            'views': [(view.id, 'form')],
            'type': 'ir.actions.act_window',
            # 'context': {'default_picking_id': self.id, 'product_ids': products.ids,
            #             'default_company_id': self.company_id.id},
            'target': 'new',
            'res_id': material_req_id.id,
            'context': self.env.context
        }

    def compute_hide_button(self):
        for record in self:
            parts_stock = False
            type_list = []
            for line in record.operations:
                stock_in_loc = self.env['stock.quant'].search(
                    [('product_id', '=', line.product_id.id), ('location_id', '=', line.location_id.id)])
                qty_in_loc = sum(stock_in_loc.mapped('available_quantity'))
                if qty_in_loc < line.product_uom_qty and line.type == 'add':
                    parts_stock = True
                    break
            if parts_stock == True:
                record.check_parts_availability = True
                record.hide_button = True
            else:
                record.check_parts_availability = False
            # if record.check_availability == True and parts_stock == True:
            #     record.hide_button = False
            if record.check_availability == False:
                record.hide_button = True
                record.check_parts_availability = False
            elif record.check_availability == True and parts_stock == False:
                record.hide_button = False
            # else:
            #     record.hide_button = False

            for line in record.operations:
                type_list.append(line.type)
            if 'add' not in type_list:
                record.hide_button = False

            # print('rhb', record.hide_button)
            # print('check_av', record.check_parts_availability)
            # print('parts_stock', parts_stock)

    def action_validate(self):
        res = super(RepairOrder, self).action_validate()
        # print('===========zzzz====')
        invalid_lines = self.operations.filtered(
            lambda x: x.product_id.tracking != 'none' and not x.lot_id)
        if invalid_lines:
            products = invalid_lines.product_id
            raise ValidationError(_(
                "Serial number is required for operation lines with products: %s",
                ", ".join(products.mapped('display_name')),
            ))
        return res


class RepairLine(models.Model):
    _inherit = 'repair.line'

    check_stock = fields.Boolean(compute='check_product_stock')
    repair_id = fields.Many2one(
        'repair.order', 'Repair Order Reference', required=True,
        index=True, ondelete='cascade', check_company=True)
    ro_location_id = fields.Many2one(
        'stock.location', related='repair_id.location_id')
    warehouse_id = fields.Many2one(
        'stock.warehouse', related='repair_id.warehouse_id')
    filter_location_ids = fields.Many2many('stock.location', store=False)
    filter_lot_ids = fields.Many2many(
        'stock.production.lot', compute='get_filter_lot_ids', store=False)

    @api.constrains('lot_id', 'product_id')
    def constrain_lot_id(self):
        pass
        # print('pass')
        # for line in self.filtered(lambda x: x.product_id.tracking != 'none' and not x.lot_id):
        #     raise ValidationError(
        #         _("Serial number is required for operation line with product '%s'") % (line.product_id.name))

    @api.depends('product_id')
    def get_filter_lot_ids(self):
        for record in self:
            if record.type == 'add':
                domain = [
                    ('product_id', '=', record.product_id.id),
                    ('location_id.warehouse_id', '=',
                     record.location_id.warehouse_id.id)
                ]
            elif record.type == 'remove':
                domain = [
                    ('product_id', '=', record.product_id.id),
                    ('location_id.warehouse_id', '=',
                     record.location_dest_id.warehouse_id.id)
                ]
            else:
                domain = []

            stock_quants = self.env['stock.quant'].search(
                domain).mapped('lot_id').ids
            # print("➡ stock_quants :", len(stock_quants))
            record.filter_lot_ids = [(6, 0, stock_quants)]

    # @api.onchange('product_id')
    # def onchange_get_filter_lot_ids(self):
    #     stock_quant = self.env['stock.quant'].search([('product_id', '=', self.product_id.id)])
    #     print(stock_quant)
    #     lot_list = []
    #     for quant in stock_quant:
    #         if self.type == 'add':
    #             print('===in==')
    #             if quant.location_id.warehouse_id == self.location_id.warehouse_id:
    #                 print('add-lot')
    #                 lot_list.append(quant.lot_id.id)
    #         if self.type == 'remove':
    #             print('===out==')
    #             if quant.location_id.warehouse_id == self.location_dest_id.warehouse_id:
    #                 print('remove-lot')
    #                 lot_list.append(quant.lot_id.id)
    #     print('lot-list', lot_list)
    #     print('lot-product', self.product_id.name)
        # self.filter_lot_ids = [(6, 0, lot_list)]

    @api.constrains('lot_id', 'product_id')
    def constrain_lot_id(self):
        pass
        # print('pass')
    #     invalid_lines = self.operations.filtered(lambda x: x.product_id.tracking != 'none' and not x.lot_id)
    #     if invalid_lines:
    #         products = invalid_lines.product_id
    #         raise ValidationError(_(
    #             "Serial number is required for operation lines with products: %s",
    #             ", ".join(products.mapped('display_name')),
    #         ))

    @api.onchange('type')
    def get_src_dest_loc(self):
        if self.type == 'add':
            # print('add')
            self.location_id = self.ro_location_id.id
        if self.type == 'remove':
            # print('rem')
            self.location_dest_id = self.ro_location_id.id
            # print('des', self.location_dest_id.display_name)

    @api.onchange('type')
    def get_src_dest_loc(self):
        if self.type == 'add':
            # print('add')
            self.location_id = self.ro_location_id.id
        if self.type == 'remove':
            # print('rem')
            self.location_dest_id = self.ro_location_id.id
            # print('des', self.location_dest_id.display_name)

    def check_product_stock(self):
        for record in self:
            if record.product_id.qty_available > 0:
                record.check_stock = True
            else:
                record.check_stock = False

    @api.onchange('location_id')
    def get_location_id(self):
        location_rec = self._get_table_records('stock.location')
        virtual_location = self.env['stock.location'].search(
            [('name', '=', 'Virtual Locations')], limit=1)
        location_list = []
        location_list.append(virtual_location.id)
        for loc in location_rec:
            if loc.id == self.repair_id.location_id.id:
                location_list.append(loc.id)
            if loc.location_id:
                if self.repair_id.location_id.display_name in loc.location_id.display_name:
                    location_list.append(loc.id)
            if loc.location_id.id == virtual_location.id:
                location_list.append(loc.id)
        if self.location_id.id not in location_list:
            self.location_id = False

        return {'domain': {'location_id': [('id', 'in', location_list)]}}

    @api.onchange('location_dest_id')
    def get_location_dest_id(self):
        location_rec = self._get_table_records('stock.location')
        virtual_location = self.env['stock.location'].search(
            [('name', '=', 'Virtual Locations')], limit=1)
        location_list = []
        location_list.append(virtual_location.id)
        for loc in location_rec:
            if loc.id == self.repair_id.location_id.id:
                location_list.append(loc.id)
            if loc.location_id:
                if self.repair_id.location_id.display_name in loc.location_id.display_name:
                    location_list.append(loc.id)
            if loc.location_id.id == virtual_location.id:
                location_list.append(loc.id)
        if self.location_dest_id.id not in location_list:
            self.location_dest_id = False

        return {'domain': {'location_dest_id': [('id', 'in', location_list)]}}

    def _get_table_records(self, table):
        formatted_table = table.replace('.', '_')
        query = f"SELECT id FROM {formatted_table}"
        self.env.cr.execute(query)
        data = tuple(item[0] for item in self.env.cr.fetchall())
        return self.env[table].browse(data)
