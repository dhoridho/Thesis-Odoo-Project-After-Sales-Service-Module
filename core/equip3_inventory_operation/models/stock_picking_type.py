
from odoo import _, api, fields, models

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    is_transit = fields.Boolean(string="Transit Operation")
    filter_location_ids = fields.Many2many('stock.location', compute='_get_locations', store=False)
    stock_picking_dasboard_id = fields.Many2one('stock.picking.type.dashboard', string="Dashboard Type")
    picking_ids = fields.One2many('stock.picking', 'picking_type_id', string="Pickings")

    def name_get(self):
        """ Display 'Warehouse_name: PickingType_name' """
        res = []
        for picking_type in self:
            source_location_id = self.env.ref('equip3_inventory_masterdata.location_transit').id
            if picking_type.warehouse_id:
                if picking_type.default_location_src_id.id != source_location_id and picking_type.default_location_src_id:
                    name = picking_type.warehouse_id.name + ' ' + picking_type.default_location_src_id.display_name + ': ' + picking_type.name
                elif picking_type.default_location_dest_id.id != source_location_id and picking_type.default_location_dest_id:
                    name = picking_type.warehouse_id.name + ' ' + picking_type.default_location_dest_id.display_name + ': ' + picking_type.name
                else:
                    name = picking_type.display_name or picking_type.name
            else:
                name = picking_type.display_name or picking_type.name
            res.append((picking_type.id, name))
        return res

    def write(self, vals):
        res = super(StockPickingType, self).write(vals)
        if 'sequence_code' in vals:
            for picking_type in self:
                picking_type.sequence_id.padding = 3
        return res

    def _get_locations(self):
        for record in self:
            data_ids = []
            stock_locations_ids = self.env['stock.location'].search([])
            for location_id in stock_locations_ids:
                source_location_id = self.env.ref('equip3_inventory_masterdata.location_transit').id
                operation_type_id = self.env['stock.picking.type'].search([('code', '=', 'internal'),('is_transit', '=', True),
                                '|', '&', ('default_location_src_id', '=', location_id.id), ('default_location_dest_id', '=', source_location_id),
                                '&', ('default_location_src_id', '=', source_location_id), ('default_location_dest_id', '=', location_id.id)], limit=1)
                if not operation_type_id:
                    data_ids.append(location_id.id)
            record.filter_location_ids = [(6, 0, data_ids)]

    @api.model
    def _create_location_operation_type(self):
        picking_type_id = self.search([], limit=1)
        for location in picking_type_id.filter_location_ids:
            if len(location.location_complete_name.split('/')) >= 2:
                location_complete_name = location.location_complete_name.split('/')
                name = location_complete_name[1]
                location_id = self.env['stock.location'].search([('complete_name', '=', name)], limit=1)
            else:
                location_id = location.location_id
            warehouse_id = self.env['stock.warehouse'].search([('view_location_id', '=', location_id.id)], limit=1)
            if warehouse_id:
                source_location_id = self.env.ref('equip3_inventory_masterdata.location_transit').id
                sequence1_vals = {
                    'name': warehouse_id.name + ' ' + location.name_get()[0][1] + ' Sequence Internal IN',
                    'implementation': 'standard',
                    'prefix': location.name_get()[0][1] + '/INT/IN',
                    'padding': 0,
                    'number_increment': 1,
                    'number_next_actual': 1,
                    'company_id': location.company_id.id,
                }
                sequence1_id = self.env['ir.sequence'].create(sequence1_vals)
                operation1_vals = {
                    'name': 'Internal Transfer IN ',
                    'sequence_code': 'INT/IN',
                    'code': 'internal',
                    'default_location_src_id': source_location_id,
                    'default_location_dest_id': location.id,
                    'warehouse_id': warehouse_id and warehouse_id.id or False,
                    'sequence_id': sequence1_id.id,
                    'is_transit': True,
                    'company_id': location.company_id.id,
                }
                in_operation_id = self.env['stock.picking.type'].create(operation1_vals)
                sequence2_vals = {
                    'name': warehouse_id.name + ' ' + location.name_get()[0][1] + ' Sequence Internal OUT',
                    'implementation': 'standard',
                    'prefix': location.name_get()[0][1] + '/INT/OUT',
                    'padding': 0,
                    'number_increment': 1,
                    'number_next_actual': 1,
                    'company_id': location.company_id.id,
                }
                sequence2_id = self.env['ir.sequence'].create(sequence2_vals)
                operation2_vals = {
                    'name': 'Internal Transit OUT',
                    'sequence_code': 'INT/OUT',
                    'code': 'internal',
                    'default_location_src_id': location.id,
                    'default_location_dest_id': source_location_id,
                    'warehouse_id': warehouse_id and warehouse_id.id or False,
                    'sequence_id': sequence2_id.id,
                    'is_transit': True,
                    'company_id': location.company_id.id,
                }
                out_operation_id = self.env['stock.picking.type'].create(operation2_vals)
        self.env.ref('equip3_inventory_operation.stock_picking_type_cron').active = False

    @api.model
    def create(self, vals):
        res = super(StockPickingType, self).create(vals)
        stock_picking_type_dashboard_id = self.env['stock.picking.type.dashboard'].search(
            [('warehouse_id', '=', res.warehouse_id.id), ('code', '=', res.code), ('company_id', '=', res.company_id.id)], limit=1)
        if stock_picking_type_dashboard_id:
            res.stock_picking_dasboard_id = stock_picking_type_dashboard_id.id
        else:
            dashboard_id = self.env['stock.picking.type.dashboard']
            name = ''
            if res.code == 'incoming':
                name = 'Receipt'
            elif res.code == 'outgoing':
                name = 'Delivery'
            elif res.code == 'internal':
                name = 'Internal Transfer'

            stock_picking_dashbord = dashboard_id.create({
                'name': name,
                'warehouse_id': res.warehouse_id.id,
                'code': res.code,
                'company_id': res.company_id.id,
            })
            res.stock_picking_dasboard_id = stock_picking_dashbord.id
        res.sequence_id.padding = 3
        res.sequence_id.update({'use_date_range': True,
                                'range_reset': 'yearly'})
        return res

    @api.model
    def _create_dashboard_cards(self):
        picking_type_ids = self.search([])
        for res in picking_type_ids:
            stock_picking_type_dashboard_id = self.env['stock.picking.type.dashboard'].search([('warehouse_id', '=', res.warehouse_id.id), ('code', '=', res.code), ('company_id', '=', res.company_id.id)], limit=1)
            if stock_picking_type_dashboard_id:
                res.stock_picking_dasboard_id = stock_picking_type_dashboard_id.id
            else:
                dashboard_id = self.env['stock.picking.type.dashboard']
                name = ''
                if res.code == 'incoming':
                    name = 'Receipt'
                elif res.code == 'outgoing':
                    name = 'Delivery'
                elif res.code == 'internal':
                    name = 'Internal Transfer'

                stock_picking_dashbord = dashboard_id.create({
                        'name': name,
                        'warehouse_id': res.warehouse_id.id,
                        'code': res.code,
                        'company_id': res.company_id.id,
                    })
                res.stock_picking_dasboard_id = stock_picking_dashbord.id

    def update_stock_picking_type_sequence(self):
        operation_type = self.env['stock.picking.type'].search([])
        for rec in operation_type:
            for sequence in rec.sequence_id.filtered(lambda x:not x.use_date_range):
                sequence.write({'use_date_range' : True,
                                'range_reset' : 'yearly'})
