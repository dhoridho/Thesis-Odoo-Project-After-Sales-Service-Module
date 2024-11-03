
from odoo import _, api, fields, models
import json
# from odoo.exceptions import ValidationError, UserError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_expired_stock_location = fields.Boolean(string="Is Expired Stock Location", readonly=True)
    occupied_unit = fields.Float('Qty Occupied',
                                 digits='Product Unit of Measure',
                                 copy=False,
                                 readonly=True,
                                 compute="_compute_occupied_unit")

    to_trigger_occupied_unit = fields.Boolean(compute="_compute_trigger_occupied_unit")
    responsible_users = fields.Many2many("res.users", "stock_location_res_users_rel", "location_id", "user_id", "Responsible User")
    additional_transfer_note = fields.Boolean("Putaway Require Additional Transfer Note")
    on_max_capacity = fields.Boolean("On Max capacity")
    putaway_destination = fields.Many2one("stock.location", "Destination Location")
    is_putaway_max_capacity = fields.Boolean(compute="_compute_is_putaway_max_capacity")
    description = fields.Char("Description")
    removal_priority = fields.Integer("Removal Priority")
    capacity_type = fields.Selection(selection_add=[
        ('weight', 'Weight'),
        ('volume', 'Volume'),
        ('length', 'Length'),
        ('width', 'Width'),
        ('height', 'Height'),
    ], ondelete={
        'weight': lambda recs: recs.write({'capacity_type': 'unit', 'active': False}),
        'volume': lambda recs: recs.write({'capacity_type': 'unit', 'active': False}),
        'length': lambda recs: recs.write({'capacity_type': 'unit', 'active': False}),
        'width': lambda recs: recs.write({'capacity_type': 'unit', 'active': False}),
        'height': lambda recs: recs.write({'capacity_type': 'unit', 'active': False}),
    })
    occupied_weight = fields.Float('Weight Occupied', digits='Stock Weight', compute='compute_occupied_weight')
    occupied_volume = fields.Float('Volume Occupied', compute='compute_occupied_volume')
    occupied_length = fields.Float('Length Occupied', compute='compute_occupied_length')
    occupied_width = fields.Float('Width Occupied', compute='compute_occupied_width')
    occupied_height = fields.Float('Height Occupied', compute='compute_occupied_height')
    capacity_length = fields.Float('Length Max')
    capacity_width = fields.Float('Width Max')
    capacity_height = fields.Float('Height Max')
    occupied_percent = fields.Integer('Occupied(%)', compute='_compute_occupied', store=False)
    branch_id = fields.Many2one('res.branch', string='Branch',default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)],)
    company_id_domain = fields.Char(string='Company Domain', compute='compute_company_id_domain')


    # @api.model
    # def action_update_operation_type(self):
    #     operation_type = self.env['stock.picking.type'].search([])
    #     for rec in operation_type:
    #         if rec.sequence_id and rec.warehouse_id:
    #             if rec.sequence_code == 'IN':
    #                 rec.sequence_id.prefix = rec.warehouse_id.code + '/IN' + '/%(y)s/%(month)s/%(day)s/'
    #             if rec.sequence_code == 'INT':
    #                 rec.sequence_id.prefix = rec.warehouse_id.code + '/INT' + '/%(y)s/%(month)s/%(day)s/'
    #             if rec.sequence_code == 'INT/IN':
    #                 rec.sequence_id.prefix = rec.warehouse_id.code + '/INT/IN' + '/%(y)s/%(month)s/%(day)s/'
    #             if rec.sequence_code == 'INT/OUT':
    #                 rec.sequence_id.prefix = rec.warehouse_id.code + '/INT/OUT' + '/%(y)s/%(month)s/%(day)s/'
    #             if rec.sequence_code == 'MO':
    #                 rec.sequence_id.prefix = rec.warehouse_id.code + '/MO' + '/%(y)s/%(month)s/%(day)s/'
    #             if rec.sequence_code == 'OUT':
    #                 rec.sequence_id.prefix = rec.warehouse_id.code + '/OUT' + '/%(y)s/%(month)s/%(day)s/'
    #             if rec.sequence_code == 'POS':
    #                 rec.sequence_id.prefix = rec.warehouse_id.code + '/POS' + '/%(y)s/%(month)s/%(day)s/'
    #     return True

    def compute_occupied_length(self):
        for record in self:
            stock_move_in = self.env['stock.move'].search([('location_dest_id', '=', record.id)]).mapped('length')
            stock_move_out = self.env['stock.move'].search([('location_id', '=', record.id)]).mapped('length')
            record.occupied_length = abs(sum(stock_move_in) - sum(stock_move_out))

    def compute_occupied_width(self):
        for record in self:
            stock_move_in = self.env['stock.move'].search([('location_dest_id', '=', record.id)]).mapped('width')
            stock_move_out = self.env['stock.move'].search([('location_id', '=', record.id)]).mapped('width')
            record.occupied_width = abs(sum(stock_move_in) - sum(stock_move_out))

    def compute_occupied_height(self):
        for record in self:
            stock_move_in = self.env['stock.move'].search([('location_dest_id', '=', record.id)]).mapped('height')
            stock_move_out = self.env['stock.move'].search([('location_id', '=', record.id)]).mapped('height')
            record.occupied_height = abs(sum(stock_move_in) - sum(stock_move_out))

    #@api.depends('capacity_type', 'occupied_order', 'capacity_unit', 'occupied_unit', 'occupied_length', 'occupied_width', 'occupied_height', 'capacity_length', 'capacity_width', 'capacity_height')
    def _compute_occupied(self):
        for rec in self:
            occupied_percent = 0
            if rec.usage in ('internal', 'transit'):
                if rec.capacity_type == 'unit':
                    try:
                        occupied_percent = 100.0 * (rec.occupied_unit / rec.capacity_unit)
                        # if occupied_percent > 100:
                        #     occupied_percent = 100
                    except:
                        occupied_percent = 0
                elif rec.capacity_type == 'weight':
                    try:
                        occupied_percent = 100.0 * (rec.occupied_weight / rec.capacity_weight)
                        # if occupied_percent > 100:
                        #     occupied_percent = 100
                    except:
                        occupied_percent = 0
                elif rec.capacity_type == 'volume':
                    try:
                        occupied_percent = 100.0 * (rec.occupied_volume / rec.capacity_volume)
                        # if occupied_percent > 100:
                        #     occupied_percent = 100
                    except:
                        occupied_percent = 0
                elif rec.capacity_type == 'length':
                    try:
                        occupied_percent = 100.0 * (rec.occupied_length / rec.capacity_length)
                    except:
                        occupied_percent = 0
                elif rec.capacity_type == 'width':
                    try:
                        occupied_percent = 100.0 * (rec.occupied_width / rec.capacity_width)
                    except:
                        occupied_percent = 0
                elif rec.capacity_type == 'height':
                    try:
                        occupied_percent = 100.0 * (rec.occupied_height / rec.capacity_height)
                    except:
                        occupied_percent = 0

            rec.occupied_percent = occupied_percent


    @api.onchange('capacity_volume', 'occupied_volume')
    def _compute_occupied_volume_percentage(self):
        for rec in self:
            occupied_percent = 0
            if rec.usage in ('internal', 'transit'):
                if rec.capacity_type == 'volume':
                    try:
                        occupied_percent = 100.0 * (rec.occupied_volume / rec.capacity_volume)
                        # if occupied_percent > 100:
                        #     occupied_percent = 100
                    except:
                        occupied_percent = 0
            rec.occupied_percent = occupied_percent

    @api.onchange('capacity_weight', 'occupied_weight')
    def _compute_occupied_weight_percentage(self):
        for rec in self:
            occupied_percent = 0
            if rec.usage in ('internal', 'transit'):
                if rec.capacity_type == 'weight':
                    try:
                        occupied_percent = 100.0 * (rec.occupied_weight / rec.capacity_weight)
                        # if occupied_percent > 100:
                        #     occupied_percent = 100
                    except:
                        occupied_percent = 0
            rec.occupied_percent = occupied_percent


    def compute_occupied_weight(self):
        for record in self:
            stock_move_in = self.env['stock.move'].search([('location_dest_id', '=', record.id)]).mapped('weight')
            stock_move_out = self.env['stock.move'].search([('location_id', '=', record.id)]).mapped('weight')
            # print('smi', stock_move_in)
            # print('smo', stock_move_out)
            record.occupied_weight = abs(sum(stock_move_in) - sum(stock_move_out))
            # print('row',record.occupied_weight)

    def compute_occupied_volume(self):
        for record in self:
            stock_move_in = self.env['stock.move'].search([('location_dest_id', '=', record.id)])
            stock_move_out = self.env['stock.move'].search([('location_id', '=', record.id)])
            move_in = 0
            move_out = 0
            for sm in stock_move_in:
                move_in = move_in + (sm.product_id.volume * sm.product_uom_qty)
            for sm in stock_move_out:
                move_out = move_out + (sm.product_id.volume * sm.product_uom_qty)
            # print('move_out',move_out)
            # print('move_in',move_in)
            record.occupied_volume = abs(move_in - move_out)
            # print('ov',record.occupied_volume)

    @api.model
    def create(self, vals):
        res = super(StockLocation, self).create(vals)
        # if len(res.location_complete_name.split('/')) >= 2:
            # location_complete_name = res.location_complete_name.split('/')
            # name = location_complete_name[1]
            # location_id = self.search([('complete_name', '=', name)], limit=1)
        # else:
        #     location_id = res.location_id
        # warehouse_id = self.env['stock.warehouse'].search([('view_location_id', '=', location_id.id)], limit=1)
        # all_warehouse = self.env['stock.warehouse'].search([])
        # for ware in all_warehouse:
        #     code = ware.code + '/'
        #     print('code',code)
        #     if code in res.location_id.display_name:
        #         print('warename', ware.name)
        res.create_operation_types()
        # print(aaa)
        return res

    # def create_operation_types(self):
    #     warehouse_id = self.env['stock.warehouse'].search([('code', '=', self.location_id.name),
    #                                                        ('company_id', '=', self.env.company.id)], limit=1)
    #     all_warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])
    #     # warehouse_id = False
    #     for ware in all_warehouse:
    #         code = ware.code + '/'
    #         # print('code',code)
    #         if self.location_id and code in self.location_id.display_name:
    #             # print('warename', ware.name)
    #             warehouse_id = ware

    #         # if ware.code == self.location_id.name or ware.code == self.location_id.location_id.name:
    #         #     warehouse_id = ware
    #     if warehouse_id:
    #         sequence1_vals = {
    #             'name': warehouse_id.name + ' ' + self.name_get()[0][1] + ' Sequence in',
    #             'implementation': 'standard',
    #             'prefix': warehouse_id.code + '/IN',
    #             'padding': 3,
    #             'number_increment': 1,
    #             'number_next_actual': 1,
    #             'company_id': self.company_id.id,
    #         }
    #         sequence1_id = self.env['ir.sequence'].create(sequence1_vals)
    #         operation1_vals = {
    #             'name': 'Receipts ',
    #             'sequence_code': 'IN',
    #             'code': 'incoming',
    #             # 'default_location_src_id': source_location_id,
    #             'default_location_dest_id': self.id,
    #             'warehouse_id':  warehouse_id.id or False,
    #             'sequence_id': sequence1_id.id,
    #             'return_picking_type_id': warehouse_id and warehouse_id.out_type_id.id,
    #             'company_id': self.company_id.id,
    #         }
    #         in_operation_id = self.env['stock.picking.type'].create(operation1_vals)

    #         sequence2_vals = {
    #             'name': warehouse_id.name + ' ' + self.name_get()[0][1] + ' Sequence internal',
    #             'implementation': 'standard',
    #             'prefix': warehouse_id.code + '/INT' + '/%(y)s/%(month)s/%(day)s/',
    #             'padding': 3,
    #             'number_increment': 1,
    #             'number_next_actual': 1,
    #             'company_id': self.company_id.id,
    #         }
    #         sequence2_id = self.env['ir.sequence'].create(sequence2_vals)
    #         operation2_vals = {
    #             'name': 'Internal Transfers',
    #             'sequence_code': 'INT',
    #             'code': 'internal',
    #             'default_location_src_id': self.id,
    #             'default_location_dest_id': self.id,
    #             'warehouse_id':  warehouse_id and warehouse_id.id or False,
    #             'sequence_id': sequence2_id.id,
    #             'company_id': self.company_id.id,
    #             # 'return_picking_type_id': warehouse_id.out_type_id.id,
    #         }
    #         int_operation_id = self.env['stock.picking.type'].create(operation2_vals)

    #         sequence3_vals = {
    #             'name': warehouse_id.name + ' ' + self.name_get()[0][1] + ' Sequence out',
    #             'implementation': 'standard',
    #             'prefix': warehouse_id.code + '/OUT',
    #             'padding': 3,
    #             'number_increment': 1,
    #             'number_next_actual': 1,
    #             'company_id': self.company_id.id,
    #         }
    #         sequence3_id = self.env['ir.sequence'].create(sequence3_vals)
    #         operation3_vals = {
    #             'name': 'Delivery Orders',
    #             'sequence_code': 'OUT',
    #             'code': 'outgoing',
    #             'default_location_src_id': self.id,
    #             'warehouse_id':  warehouse_id.id or False,
    #             'sequence_id': sequence3_id.id,
    #             'company_id': self.company_id.id,
    #             'return_picking_type_id': warehouse_id.in_type_id.id,
    #         }
    #         out_operation_id = self.env['stock.picking.type'].create(operation3_vals)
    

    def create_operation_types(self):
        warehouse = self.env['stock.warehouse'].search([
            ('code', '=', self.location_id.name),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        
        if not warehouse:
            all_warehouses = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])
            warehouse = next(
                (ware for ware in all_warehouses if self.location_id and f"{ware.code}/" in self.location_id.display_name),
                None
            )

        if not warehouse:
            return

        name_get = self.name_get()[0][1]
        location_id = self.id
        location_name = self.name
        company_id = self.company_id.id

        def create_sequence(name, prefix):
            return self.env['ir.sequence'].create({
                'name': name,
                'implementation': 'standard',
                'prefix': prefix,
                'padding': 3,
                'number_increment': 1,
                'number_next_actual': 1,
                'company_id': company_id,
            })

        def create_operation_type(sequence, name, sequence_code, code, 
                                  default_location_src_id=None, default_location_dest_id=None, 
                                  return_picking_type_id=None, is_transit=False):
            return {
                'name': name,
                'sequence_code': sequence_code,
                'code': code,
                'default_location_src_id': default_location_src_id,
                'default_location_dest_id': default_location_dest_id,
                'warehouse_id': warehouse.id or False,
                'sequence_id': sequence.id,
                'company_id': company_id,
                'return_picking_type_id': return_picking_type_id,
                'is_transit': is_transit,
            }

        sequences = [
            create_sequence(f"{warehouse.name} {name_get} Sequence In", f"{warehouse.code}/{location_name}/IN"),
            create_sequence(f"{warehouse.name} {name_get} Sequence internal", f"{warehouse.code}/{location_name}/INT"),
            create_sequence(f"{warehouse.name} {name_get} Sequence Out", f"{warehouse.code}/{location_name}/OUT"),
            create_sequence(f"{warehouse.name} {name_get} Sequence Internal IN", f"{warehouse.code}/{location_name}/INT/IN"),
            create_sequence(f"{warehouse.name} {name_get} Sequence Internal OUT", f"{warehouse.code}/{location_name}/INT/OUT"),
        ]

        source_location_id = self.env.ref('equip3_inventory_masterdata.location_transit').id

        picking_types = [
            create_operation_type(sequences[0], 'Receipts', 'IN', 'incoming', default_location_dest_id=location_id, return_picking_type_id=warehouse.out_type_id.id),
            create_operation_type(sequences[1], 'Internal Transfers', 'INT', 'internal', default_location_src_id=location_id, default_location_dest_id=location_id),
            create_operation_type(sequences[2], 'Delivery Orders', 'OUT', 'outgoing', default_location_src_id=location_id, return_picking_type_id=warehouse.in_type_id.id),
            create_operation_type(sequences[3], 'Internal Transfer IN', 'INT/IN', 'internal', default_location_src_id=source_location_id, default_location_dest_id=location_id, is_transit=True),
            create_operation_type(sequences[4], 'Internal Transit OUT', 'INT/OUT', 'internal', default_location_src_id=location_id, default_location_dest_id=source_location_id, is_transit=True),
        ]

        self.env['stock.picking.type'].create(picking_types)

        return True


    # @api.model
    # def action_custom_method(self):
    #     chk_installed = self.env['ir.module.module'].search([('name', '=', 'equip3_inventory_masterdata')])
    #     if chk_installed.state == 'to install':
    #         stock_location = self.env['stock.location'].search([('usage','=','internal')])
    #         for loc in stock_location:
    #             # if loc.location_complete_name:
    #             #     if len(loc.location_complete_name.split('/')) >= 2:
    #             #         location_complete_name = loc.location_complete_name.split('/')
    #             #         name = location_complete_name[1]
    #             #         location_id = self.search([('complete_name', '=', name)], limit=1)
    #             # else:
    #             location_id = loc.location_id.id
    #             warehouse_id = self.env['stock.warehouse'].search([('lot_stock_id', '=', location_id)], limit=1)
    #             if warehouse_id:
    #                 picking_type = self.env['stock.picking.type'].search([('code', '=', 'incoming'),('default_location_dest_id', '=', loc.id)])
    #                 if not picking_type:
    #                     sequence1_vals = {
    #                         'name': warehouse_id.name + ' ' + loc.name_get()[0][1] + ' Sequence IN',
    #                         'implementation': 'standard',
    #                         'prefix': warehouse_id.code + '/IN' + '/%(y)s/%(month)s/%(day)s/',
    #                         'padding': 3,
    #                         'number_increment': 1,
    #                         'number_next_actual': 1,
    #                     }
    #                     sequence1_id = self.env['ir.sequence'].create(sequence1_vals)
    #                     operation1_vals = {
    #                         'name': 'Receipts ',
    #                         'sequence_code': 'IN',
    #                         'code': 'incoming',
    #                         # 'default_location_src_id': source_location_id,
    #                         'default_location_dest_id': loc.id,
    #                         'warehouse_id':  warehouse_id.id or False,
    #                         'sequence_id': sequence1_id.id,
    #                         'return_picking_type_id': warehouse_id.out_type_id.id,
    #                     }
    #                     in_operation_id = self.env['stock.picking.type'].create(operation1_vals)

    #                 picking_type_in_transfer = self.env['stock.picking.type'].search([('code', '=', 'internal'),('default_location_dest_id', '=', loc.id)
    #                                                                                      ,('default_location_src_id', '=', loc.id )])
    #                 if not picking_type_in_transfer:
    #                     sequence2_vals = {
    #                         'name': warehouse_id.name + ' ' + loc.name_get()[0][1] + ' Sequence internal',
    #                         'implementation': 'standard',
    #                         'prefix': warehouse_id.code + '/INT' + '/%(y)s/%(month)s/%(day)s/',
    #                         'padding': 3,
    #                         'number_increment': 1,
    #                         'number_next_actual': 1,
    #                     }
    #                     sequence2_id = self.env['ir.sequence'].create(sequence2_vals)
    #                     operation2_vals = {
    #                         'name': 'Internal Transfers',
    #                         'sequence_code': 'INT',
    #                         'code': 'internal',
    #                         'default_location_src_id': loc.id,
    #                         'default_location_dest_id': loc.id,
    #                         'warehouse_id':  warehouse_id.id or False,
    #                         'sequence_id': sequence2_id.id,
    #                         # 'return_picking_type_id': warehouse_id.out_type_id.id,
    #                     }
    #                     int_operation_id = self.env['stock.picking.type'].create(operation2_vals)

    #                 picking_type_out = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('default_location_src_id', '=', loc.id )])
    #                 if not picking_type_out:
    #                     sequence3_vals = {
    #                         'name': warehouse_id.name + ' ' + loc.name_get()[0][1] + ' Sequence out',
    #                         'implementation': 'standard',
    #                         'prefix': warehouse_id.code + '/OUT' + '/%(y)s/%(month)s/%(day)s/',
    #                         'padding': 3,
    #                         'number_increment': 1,
    #                         'number_next_actual': 1,
    #                     }
    #                     sequence3_id = self.env['ir.sequence'].create(sequence3_vals)
    #                     operation3_vals = {
    #                         'name': 'Delivery Orders',
    #                         'sequence_code': 'OUT',
    #                         'code': 'outgoing',
    #                         'default_location_src_id': loc.id,
    #                         'warehouse_id':  warehouse_id.id or False,
    #                         'sequence_id': sequence3_id.id,
    #                         'return_picking_type_id': warehouse_id.in_type_id.id,
    #                     }
    #                     out_operation_id = self.env['stock.picking.type'].create(operation3_vals)
    #     return True

    # @api.model
    # def create_picking_type(self):
    #     chk_installed1 = self.env['ir.module.module'].search([('name', '=', 'equip3_inventory_masterdata')])
    #     if chk_installed1.state == 'to upgrade' or chk_installed1.state == 'to install':
    #         stock_location = self.env['stock.location'].search([('usage','=','internal')])
    #         for loc in stock_location:
    #             # location_id = loc.location_id.id
    #             warehouse_id = self.env['stock.warehouse'].search([('lot_stock_id', '=', loc.id)], limit=1)
    #             if warehouse_id:
    #                 transit_location_id = self.env.ref('equip3_inventory_masterdata.location_transit').id
    #                 picking_type1 = self.env['stock.picking.type'].search([('warehouse_id','=',warehouse_id.id)])
    #                 is_transfer = False
    #                 for type in picking_type1:
    #                     if type.default_location_src_id.id == transit_location_id and type.default_location_dest_id.id == loc.id:
    #                         is_transfer = True
    #                 if is_transfer == False:
    #                     # print('create picking typeeeee is transfer falseeeeeeeeeeeeee', warehouse_id.code)
    #                     # break
    #                     # else:
    #                     sequence4_vals = {
    #                         'name': warehouse_id.name + ' ' + loc.name_get()[0][1] + ' Sequence Internal IN',
    #                         'implementation': 'standard',
    #                         'prefix': warehouse_id.code + '/INT/IN',
    #                         'padding': 3,
    #                         'number_increment': 1,
    #                         'number_next_actual': 1,
    #                         'company_id': warehouse_id.lot_stock_id.company_id.id,
    #                     }
    #                     sequence4_id = self.env['ir.sequence'].create(sequence4_vals)
    #                     operation4_vals = {
    #                         'name': 'Internal Transfer IN ',
    #                         'sequence_code': 'INT/IN',
    #                         'code': 'internal',
    #                         'default_location_src_id': transit_location_id,
    #                         'default_location_dest_id': loc.id,
    #                         'warehouse_id': warehouse_id.id or False,
    #                         'company_id': warehouse_id.lot_stock_id.company_id.id,
    #                         'sequence_id': sequence4_id.id,
    #                         'is_transit': True,
    #                     }
    #                     in_operation_id4 = self.env['stock.picking.type'].create(operation4_vals)
    #                 picking_type2 = self.env['stock.picking.type'].search([('warehouse_id','=',warehouse_id.id)])
    #                 is_transfer_out = False
    #                 for type in picking_type1:
    #                     if type.default_location_src_id.id == loc.id and type.default_location_dest_id.id == transit_location_id:
    #                         is_transfer_out = True
    #                 if is_transfer_out == False:
    #                     sequence5_vals = {
    #                         'name': warehouse_id.name + ' ' + loc.name_get()[0][1] + ' Sequence Internal OUT',
    #                         'implementation': 'standard',
    #                         'prefix': warehouse_id.code + '/INT/OUT',
    #                         'padding': 3,
    #                         'number_increment': 1,
    #                         'number_next_actual': 1,
    #                         'company_id': warehouse_id.lot_stock_id.company_id.id,
    #                     }
    #                     sequence5_id = self.env['ir.sequence'].create(sequence5_vals)
    #                     operation5_vals = {
    #                         'name': 'Internal Transit OUT',
    #                         'sequence_code': 'INT/OUT',
    #                         'code': 'internal',
    #                         'default_location_src_id': loc.id,
    #                         'default_location_dest_id': transit_location_id,
    #                         'warehouse_id': warehouse_id.id or False,
    #                         'company_id': warehouse_id.lot_stock_id.company_id.id,
    #                         'sequence_id': sequence5_id.id,
    #                         'is_transit': True,
    #                     }
    #                     out_operation_id = self.env['stock.picking.type'].create(operation5_vals)
    #             all_warehouse = self.env['stock.warehouse'].search([])
    #             warehouse_id_child_loc = False
    #             for ware in all_warehouse:
    #                 code = ware.code + '/'
    #                 # print('code',code)

    #                 if loc.location_id and code in loc.location_id.display_name:
    #                     # print('warename', ware.name)
    #                     warehouse_id_child_loc = ware
    #             if warehouse_id_child_loc:
    #                 transit_location_id = self.env.ref('equip3_inventory_masterdata.location_transit').id
    #                 picking_type1 = self.env['stock.picking.type'].search([('warehouse_id','=', warehouse_id_child_loc.id)])
    #                 is_receipts = False
    #                 for type in picking_type1:
    #                     if type.default_location_dest_id.id == loc.id and type.code == 'incoming':
    #                         is_receipts = True
    #                 if is_receipts == False:
    #                     sequence1_vals = {
    #                         'name': warehouse_id_child_loc.name + ' ' + loc.name_get()[0][1] + ' Sequence in',
    #                         'implementation': 'standard',
    #                         'prefix': warehouse_id.code + '/IN',
    #                         'padding': 3,
    #                         'number_increment': 1,
    #                         'number_next_actual': 1,
    #                         'company_id': warehouse_id_child_loc.lot_stock_id.company_id.id,
    #                         }
    #                     sequence1_id = self.env['ir.sequence'].create(sequence1_vals)
    #                     operation1_vals = {
    #                         'name': 'Receipts ',
    #                         'sequence_code': 'IN',
    #                         'code': 'incoming',
    #                         # 'default_location_src_id': source_location_id,
    #                         'default_location_dest_id': loc.id,
    #                         'warehouse_id':  warehouse_id_child_loc.id or False,
    #                         'sequence_id': sequence1_id.id,
    #                         # 'return_picking_type_id': warehouse_id_child_loc.out_type_id.id,
    #                         'company_id': warehouse_id_child_loc.lot_stock_id.company_id.id,
    #                     }
    #                     in_operation_id = self.env['stock.picking.type'].create(operation1_vals)

    #                 is_internal_transfers = False
    #                 for type in picking_type1:
    #                     if type.default_location_src_id.id == loc.id and type.default_location_dest_id.id == loc.id and type.name == 'Internal Transfers':
    #                         is_internal_transfers = True
    #                 if is_internal_transfers == False:
    #                     sequence2_vals = {
    #                         'name': warehouse_id_child_loc.name + ' ' + loc.name_get()[0][1] + ' Sequence internal',
    #                         'implementation': 'standard',
    #                         'prefix': warehouse_id.code + '/INT' + '/%(y)s/%(month)s/%(day)s/',
    #                         'padding': 3,
    #                         'number_increment': 1,
    #                         'number_next_actual': 1,
    #                         'company_id': warehouse_id_child_loc.lot_stock_id.company_id.id,
    #                         }
    #                     sequence2_id = self.env['ir.sequence'].create(sequence2_vals)
    #                     operation2_vals = {
    #                         'name': 'Internal Transfers',
    #                         'sequence_code': 'INT',
    #                         'code': 'internal',
    #                         'default_location_src_id': loc.id,
    #                         'default_location_dest_id': loc.id,
    #                         'warehouse_id':  warehouse_id_child_loc.id or False,
    #                         'sequence_id': sequence2_id.id,
    #                         # 'return_picking_type_id': warehouse_id.out_type_id.id,
    #                         'company_id': warehouse_id_child_loc.lot_stock_id.company_id.id,
    #                     }
    #                     int_operation_id = self.env['stock.picking.type'].create(operation2_vals)

    #                 is_delivery_orders = False
    #                 for type in picking_type1:
    #                     if type.default_location_src_id.id == loc.id and type.name == 'Delivery Orders':
    #                         is_delivery_orders = True
    #                 if is_delivery_orders == False:
    #                     sequence3_vals = {
    #                         'name': warehouse_id_child_loc.name + ' ' + loc.name_get()[0][1] + ' Sequence out',
    #                         'implementation': 'standard',
    #                         'prefix': warehouse_id.code + '/OUT' + '/%(y)s/%(month)s/%(day)s/',
    #                         'padding': 3,
    #                         'number_increment': 1,
    #                         'number_next_actual': 1,
    #                         'company_id': warehouse_id_child_loc.lot_stock_id.company_id.id,
    #                         }
    #                     sequence3_id = self.env['ir.sequence'].create(sequence3_vals)
    #                     operation3_vals = {
    #                         'name': 'Delivery Orders',
    #                         'sequence_code': 'OUT',
    #                         'code': 'outgoing',
    #                         'default_location_src_id': loc.id,
    #                         'warehouse_id':  warehouse_id_child_loc.id or False,
    #                         'sequence_id': sequence3_id.id,
    #                         # 'return_picking_type_id': warehouse_id.in_type_id.id,
    #                         'company_id': warehouse_id_child_loc.lot_stock_id.company_id.id,
    #                     }
    #                     out_operation_id = self.env['stock.picking.type'].create(operation3_vals)


    #                 is_transfer = False
    #                 for type in picking_type1:
    #                     if type.default_location_src_id.id == transit_location_id and type.default_location_dest_id.id == loc.id:
    #                         is_transfer = True
    #                 if is_transfer == False:
    #                     sequence4_vals = {
    #                         'name': warehouse_id_child_loc.name + ' ' + loc.name_get()[0][1] + ' Sequence Internal IN',
    #                         'implementation': 'standard',
    #                         'prefix': warehouse_id.code + '/INT/IN',
    #                         'padding': 3,
    #                         'number_increment': 1,
    #                         'number_next_actual': 1,
    #                         'company_id': warehouse_id_child_loc.lot_stock_id.company_id.id,
    #                     }
    #                     sequence4_id = self.env['ir.sequence'].create(sequence4_vals)
    #                     operation4_vals = {
    #                         'name': 'Internal Transfer IN ',
    #                         'sequence_code': 'INT/IN',
    #                         'code': 'internal',
    #                         'default_location_src_id': transit_location_id,
    #                         'default_location_dest_id': loc.id,
    #                         'warehouse_id': warehouse_id_child_loc.id or False,
    #                         'company_id': warehouse_id_child_loc.lot_stock_id.company_id.id,
    #                         'sequence_id': sequence4_id.id,
    #                         'is_transit': True,
    #                     }
    #                     in_operation_id4 = self.env['stock.picking.type'].create(operation4_vals)
    #                 # picking_type2 = self.env['stock.picking.type'].search([('warehouse_id','=',warehouse_id.id)])
    #                 is_transfer_out = False
    #                 for type in picking_type1:
    #                     if type.default_location_src_id.id == loc.id and type.default_location_dest_id.id == transit_location_id:
    #                         is_transfer_out = True
    #                 if is_transfer_out == False:
    #                     sequence5_vals = {
    #                         'name': warehouse_id_child_loc.name + ' ' + loc.name_get()[0][1] + ' Sequence Internal OUT',
    #                         'implementation': 'standard',
    #                         'prefix': warehouse_id.code + '/INT/OUT',
    #                         'padding': 3,
    #                         'number_increment': 1,
    #                         'number_next_actual': 1,
    #                         'company_id': warehouse_id_child_loc.lot_stock_id.company_id.id,
    #                     }
    #                     sequence5_id = self.env['ir.sequence'].create(sequence5_vals)
    #                     operation5_vals = {
    #                         'name': 'Internal Transit OUT',
    #                         'sequence_code': 'INT/OUT',
    #                         'code': 'internal',
    #                         'default_location_src_id': loc.id,
    #                         'default_location_dest_id': transit_location_id,
    #                         'warehouse_id': warehouse_id_child_loc.id or False,
    #                         'company_id': warehouse_id_child_loc.lot_stock_id.company_id.id,
    #                         'sequence_id': sequence5_id.id,
    #                         'is_transit': True,
    #                     }
    #                     out_operation_id = self.env['stock.picking.type'].create(operation5_vals)

    #         #update prefix in ir.sequence
    #         operation_types = self.env['stock.picking.type'].search([])
    #         for op_type in operation_types:
    #             op_type.sequence_id.padding = 3
    #             if '%(y)s' not in op_type.sequence_id.prefix and '%(month)s' not in op_type.sequence_id.prefix:
    #                 if op_type.sequence_id.prefix[-1] == '/':
    #                     op_type.sequence_id.prefix += '%(y)s/%(month)s/%(day)s/'
    #                 else:
    #                     op_type.sequence_id.prefix += '/%(y)s/%(month)s/%(day)s/'
    #     return True

    def _compute_trigger_occupied_unit(self):
        for rec in self:
            self._compute_occupied_unit()
            rec.to_trigger_occupied_unit = False

    #@api.depends("capacity_type")
    def _compute_occupied_unit(self):
        for record in self:
            total_qty = sum(self.env["stock.quant"].search([('location_id','=',record.id)]).mapped("quantity"))
            # original_location_obj = self.env["stock.location"].browse(rec._origin.id)
            # if rec.capacity_type == "unit":
            #     total_qty = sum(self.env["stock.quant"].search([('location_id',
            #                                                  'child_of',
            #                                                   rec._origin.id)]).mapped("quantity"))
            #     rec.occupied_unit = total_qty
            #     original_location_obj.occupied_unit = total_qty
            # else:
            #     original_location_obj.occupied_unit = 0

            #stock_move_in = self.env['stock.move'].search([('location_dest_id', '=', record.id), ('state', '=', 'done')]).mapped('product_uom_qty')
            #stock_move_out = self.env['stock.move'].search([('location_id', '=', record.id), ('state', '=', 'done')]).mapped('product_uom_qty')
            # print('smi', sum(stock_move_in))
            # print('smo', sum(stock_move_out))
            #record.occupied_unit = abs(sum(stock_move_in) - sum(stock_move_out))
            record.occupied_unit = total_qty

    def _customize_get_putaway_strategy(self, product):
        ''' Returns the location where the product has to be put, if any compliant putaway strategy is found. Otherwise returns None.'''
        current_location = self
        putaway_location = self.env['stock.location']
        while current_location and not putaway_location:
            # Looking for a putaway about the product.
            # putaway_rules = current_location.putaway_rule_ids.filtered(lambda x: x.product_id == product)
            prod_putaway = False

            # if putaway_rules:
            #     putaway_location = putaway_rules[0].location_out_id
            # If not product putaway found, we're looking with category so.
            # else:
            # if prod_putaway == False:
            categ = product.categ_id
            while categ:
                putaway_rules = current_location.putaway_rule_ids.filtered(lambda x: categ.id in x.category_id.ids)
                if putaway_rules:
                    putaway_location = putaway_rules[0].location_out_id
                    prod_putaway = True
                    break
                categ = categ.parent_id

            if prod_putaway == False:
                for loc in current_location.putaway_rule_ids:
                    for prod in loc.product_ids:
                        if prod == product:
                            putaway_location = loc.location_out_id
                            # prod_putaway = True
                            break
            current_location = current_location.location_id
        return putaway_location

    def _get_putaway_strategy(self, product):
        ''' Returns the location where the product has to be put, if any compliant putaway strategy is found. Otherwise returns None.'''
        current_location = self
        putaway_location = self.env['stock.location']

        stock_move = False
        product_qty = 0
        if self.env.context.get("stock_move_id"):
            stock_move = self.env["stock.move"].browse(self.env.context.get("stock_move_id"))
            product_qty = stock_move.product_qty
        diff_unit = current_location.capacity_unit - current_location.occupied_unit

        if current_location.additional_transfer_note:
            if current_location.on_max_capacity:
                if diff_unit < product_qty:
                    putaway_location = current_location
                    source_loc = current_location
                    destination_loc = current_location.putaway_destination
                    putaway_dest = False
                    source_loc_temp = current_location
                    while putaway_dest == False:
                        # print('sourloc', source_loc)
                        if source_loc.on_max_capacity and source_loc.putaway_destination.id != current_location.id:
                            if (source_loc.occupied_unit > source_loc.capacity_unit) or (diff_unit < product_qty):
                                source_loc_temp = source_loc
                                source_loc = source_loc.putaway_destination
                            else:
                                source_loc = source_loc_temp
                                putaway_dest = True
                        else:
                            source_loc = source_loc_temp
                            putaway_dest = True
                    self.create_interwarehouse_transfer(current_location, source_loc.putaway_destination, stock_move, "waiting")
                else:
                    putaway_location = current_location
            else:
                # print("qwert")
                putaway_location = current_location
                new_product_move_location = current_location._customize_get_putaway_strategy(product)
                if current_location != new_product_move_location:
                    # print('newpro', new_product_move_location)
                    if new_product_move_location:
                        self.create_interwarehouse_transfer(current_location, new_product_move_location, stock_move, "waiting")
        else:
            if current_location.on_max_capacity:
                if diff_unit < product_qty:
                    putaway_location = current_location
                    source_loc = current_location
                    destination_loc = current_location.putaway_destination
                    putaway_dest = False
                    source_loc_temp = current_location
                    while putaway_dest == False:
                        # print('sourloc', source_loc)
                        if source_loc.on_max_capacity and source_loc.putaway_destination.id != current_location.id:
                            if (source_loc.occupied_unit > source_loc.capacity_unit) or (diff_unit < product_qty):
                                source_loc_temp = source_loc
                                source_loc = source_loc.putaway_destination
                            else:
                                source_loc = source_loc_temp
                                putaway_dest = True
                        else:
                            source_loc = source_loc_temp
                            putaway_dest = True
                    putaway_location = current_location
                    # self.create_interwarehouse_transfer(current_location, source_loc.putaway_destination, stock_move, "done")
                else:
                    putaway_location = current_location._customize_get_putaway_strategy(product)
            else:
                putaway_location = current_location._customize_get_putaway_strategy(product)
        return putaway_location

    # def _get_putaway_strategy(self, product):
    #     ''' Returns the location where the product has to be put, if any compliant putaway strategy is found. Otherwise returns None.'''
    #     current_location = self
    #     putaway_location = self.env['stock.location']

    #     stock_move = False
    #     product_qty = 0
    #     if self.env.context.get("stock_move_id"):
    #         stock_move = self.env["stock.move"].browse(self.env.context.get("stock_move_id"))
    #         product_qty = stock_move.product_qty

    #     if not current_location.additional_transfer_note:
    #         while current_location and not putaway_location:
    #             # Looking for a putaway about the product.
    #             # putaway_rules = current_location.putaway_rule_ids.filtered(lambda x: x.product_id == product)
    #             putaway_rules = False
    #             rule_ids = current_location.putaway_rule_ids
    #             if rule_ids.filtered(lambda x: x.on_max_capacity):
    #                 putaway_rules = rule_ids.filtered(lambda x: x.on_max_capacity)
    #             else:
    #                 putaway_rules = rule_ids.filtered(lambda x: x.product_id == product)

    #             diff_unit = current_location.capacity_unit - current_location.occupied_unit
    #             if putaway_rules:
    #                 if self.env.context.get("stock_move_id") and putaway_rules[0].is_putaway_max_capacity:
    #                     putaway_location = putaway_rules[0].location_in_id
    #                     if diff_unit < product_qty:
    #                         putaway_location = putaway_rules[0].location_out_id
    #                         self.create_interwarehouse_transfer(putaway_rules[0].location_in_id, putaway_rules[0].location_out_id, stock_move, "done")
    #                 else:
    #                     putaway_location = putaway_rules[0].location_out_id
    #             # If not product putaway found, we're looking with category so.
    #             else:
    #                 categ = product.categ_id
    #                 while categ:
    #                     putaway_rules = current_location.putaway_rule_ids.filtered(lambda x: x.category_id == categ)
    #                     if putaway_rules:
    #                         putaway_location = putaway_rules[0].location_out_id
    #                         break
    #                     categ = categ.parent_id
    #             current_location = current_location.location_id
    #     elif current_location.additional_transfer_note and self.env.context.get("stock_move_id"):
    #         putaway_rules = current_location.putaway_rule_ids
    #         putaway_location = putaway_rules[0].location_in_id
    #         self.create_interwarehouse_transfer(putaway_rules[0].location_in_id, putaway_rules[0].location_out_id, stock_move, "waiting")
    #     return putaway_location

    def create_interwarehouse_transfer(self, location_in_id, location_out_id, stock_move, state):
        warehouse = location_in_id.get_warehouse()
        # print('stockmove', stock_move)
        # print('location_in_id', location_in_id.display_name)
        # print('location_out_id',location_out_id.display_name)
        if stock_move:
            for loc in stock_move.location_dest_id:
                remain_qty = loc.capacity_unit - loc.occupied_unit
                done_qty = stock_move.product_qty
                if remain_qty > 0 and remain_qty < stock_move.product_qty:
                    # stock_move.product_uom_qty = remain_qty
                    done_qty = done_qty - remain_qty
                    # stock_move.remaining = remain_qty
                    # stock_move.quantity_done = remain_qty
                    # stock_move.reserved_availability = remain_qty
            vals = {
                "is_interwarehouse_transfer": True,
                "warehouse_id": warehouse.id,
                "location_id": location_in_id.id,
                "location_dest_id": location_out_id.id,
                "picking_type_id": warehouse.int_type_id.id,
                "branch_id": warehouse.int_type_id.branch_id.id,
                "move_ids_without_package": [(0, 0, {
                    'name': stock_move.product_id.name,
                    'product_id': stock_move.product_id.id,
                    'product_uom': stock_move.product_uom.id,
                    'quantity_done': done_qty,
                    'location_id': stock_move.location_id.id,
                    'location_dest_id': stock_move.location_dest_id.id
                })],
            }
            picking_id = self.env["stock.picking"].with_context(not_create_interwarehouse_transfer=True).create(vals)
            picking_id.state = state
        return True

    def _compute_is_putaway_max_capacity(self):
        for rec in self:
            rec.is_putaway_max_capacity = bool(self.env["ir.config_parameter"].sudo().get_param("putaway_max_capacity", False))
            if not rec.is_putaway_max_capacity:
                rec.on_max_capacity = False
                rec.putaway_destination = False

    @api.model
    def default_get(self, fields):
        res = super(StockLocation, self).default_get(fields)
        res.update({ "is_putaway_max_capacity": bool(self.env["ir.config_parameter"].sudo().get_param("putaway_max_capacity", False))})
        return res

    @api.onchange('location_id')
    def onchange_location_id(self):
        return {'domain' : { 'putaway_destination' : [('id','child_of', self.location_id.id), ('id', '!=', self.location_id.id)] }}

    @api.model
    def get_warehouse_location_values(self, values=None):
        if values:
            values = list(values.values())[0]
            if values['warehouse_id'] != -1:
                if '-1' in values['warehouses']:
                    del values['warehouses']['-1']
                values['locations'] = {-1: 'Please Select Location'}
                if self.env.context.get("is_change_warehouse"):
                    values['location_id'] = -1
                for location_id in self.env['stock.location'].search([('warehouse_id', '=', int(values['warehouse_id'])), ('usage', '=', 'internal')]):
                    values['locations'][location_id.id] = location_id.display_name

            if '-1' in values['locations'] and values['location_id'] != -1:
                del values['locations']['-1']
            return values

        result = {
			'warehouses': {-1: 'Please Select Warehouse'},
			'warehouse_id': -1,
            'locations': {-1: 'Please Select Location'},
            'location_id': -1,
		}
        for warehouse_id in self.env['stock.warehouse'].search([]):
            result['warehouses'][warehouse_id.id] = warehouse_id.name

        return result

    @api.model
    def get_related_child_location(self, values=None):
        child_location = self.env["stock.location"].search([("location_id", "=", values.get("location_id"))])
        return child_location.ids

    @api.model
    def reset_location_priority(self, values=None):
        for rec in self.env["stock.location"].browse(values.get("location_ids")):
            rec.removal_priority = False
        return values.get("location_ids")


    @api.depends('company_id')
    def compute_company_id_domain(self):
        for record in self:
            record.company_id_domain = False
            company_ids = self.env['res.company'].search([('id', 'in', self.env.user.company_ids.ids)])
            if company_ids:
                record.company_id_domain = json.dumps([('id', 'in', company_ids.ids)])
