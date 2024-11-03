# -*- coding: utf-8 -*-

from email.policy import default

# from numpy import product
from odoo import api, models, fields
from odoo.http import request

class GravioLog(models.Model):
    _name = 'gravio.log'
    _description = 'Gravio Log'

    button_pressed = fields.Char(string='Button Pressed')
    distance = fields.Float(string='Distance')
    sensor_id = fields.Char(string='Sensor ID')
    length = fields.Float(string='Length')
    width = fields.Float(string='Width')
    height = fields.Float(string='Height')
    data = fields.Char(string='Data')
    area = fields.Char(string='Area')
    log = fields.Char(string='Data')
    layer = fields.Char(string='Layer')
    timestamp = fields.Char(string='Timestamp')
    datetime = fields.Datetime(string='DateTime')

    sync = fields.Boolean(string='Sync', default=False)
    
    
    def create_rn(self):
        # get all un sync data
        line__ids = self.env['gravio.log'].search([('sync', '=', False)])
        
        layer_ids = line__ids.read_group(
            [('sync', '=', False)], 
            fields=['layer'],
            groupby=['layer'], 
            lazy=False
        )
        
        print('line_ids', layer_ids)
        
        for layer in layer_ids:
            print(layer.get('layer'))
            location = self.env['stock.location'].search([('layer_label', '=', layer.get('layer'))], limit=1)
            print('location', location)
            if location:
                product_ids = line__ids.read_group(
                    [('sync', '=', False),('layer', '=', layer.get('layer'))], 
                    fields=['layer','log','area'],
                    groupby=['log'], 
                    lazy=False
                )
                print('product_ids', product_ids)
                # Ready component data
                comp_ids_rn = []
                comp_ids_do = []
                for product in product_ids:
                    product_temp = self.env['product.template'].search([('rfid_label', '=', product.get('log'))], limit=1)
                    if product:
                        comp_ids_rn.append((0, 0, {
                            'name': product_temp.name,
                            'product_id': product_temp.product_variant_id,
                            'product_uom_qty': product.get('__count'),
                            'product_uom': product_temp.uom_id.id,
                        }))
                        
                        comp_ids_do.append((0, 0, {
                            'name': product_temp.name,
                            'product_id': product_temp.product_variant_id,
                            'product_uom_qty': product.get('__count'),
                            'product_uom': product_temp.uom_id.id,
                        }))
                if len(comp_ids_rn) > 0:
                    print('comp_ids', comp_ids_rn)
                    #  CREATE RN
                    # Check RFID Mapping for this Location
                    rfid_mapping_rn = self.env['rfid.mapping'].search([('location_id', '=', location.id), ('process_type', '=', 'rn')], limit=1)
                    if rfid_mapping_rn:
                        stock_warehouse = self.env['stock.warehouse'].search([], order="id", limit=1)
                        picking_type_rn = self.env['stock.picking.type'].search([('default_location_dest_id', '=', location.id), ('sequence_code', '=', 'IN')], limit=1)
                        if picking_type_rn:
                            picking_id_rn = self.env['stock.picking'].create({
                                'date': fields.datetime.now(),
                                'picking_type_id': picking_type_rn.id,
                                'location_id': self.env.ref('stock.stock_location_suppliers').id,
                                'location_dest_id': location.id,
                                'move_type': 'direct',
                                'move_ids_without_package': comp_ids_rn,
                                'picking_type_code': 'incoming'
                            })
                            
                            # Update sync status
                            if picking_id_rn:
                                picking_id_rn.action_confirm()
                                picking_id_rn.action_assign()
                                if picking_id_rn.state == 'assigned':
                                    #Set Done Qty
                                    for move in picking_id_rn.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                                        for move_line in move.move_line_ids:
                                            move_line.qty_done = move_line.product_uom_qty
                                    picking_id_rn.button_validate()
                
                if len(comp_ids_do) > 0:
                    print('comp_ids', comp_ids_do)
                    #  CREATE DO
                    # Check RFID Mapping for this Location
                    rfid_mapping_do = self.env['rfid.mapping'].search([('location_id', '=', location.id), ('process_type', '=', 'do')], limit=1)
                    if rfid_mapping_do:
                        stock_warehouse = self.env['stock.warehouse'].search([], order="id", limit=1)
                        picking_type_do = self.env['stock.picking.type'].search([('default_location_src_id', '=', location.id), ('sequence_code', '=', 'OUT')], limit=1)
                        if picking_type_do:
                            picking_id_do = self.env['stock.picking'].create({
                                'date': fields.datetime.now(),
                                'picking_type_id': picking_type_do.id,
                                'location_id': location.id,
                                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
                                'move_type': 'direct',
                                'move_ids_without_package': comp_ids_do,
                                'picking_type_code': 'outgoing'
                            })
                            
                            # Update sync status
                            if picking_id_do:
                                picking_id_do.action_confirm()
                                picking_id_do.action_assign()
                                if picking_id_do.state == 'assigned':
                                    #Set Done Qty
                                    for move in picking_id_do.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                                        for move_line in move.move_line_ids:
                                            move_line.qty_done = move_line.product_uom_qty
                                    picking_id_do.button_validate()
        
        line__ids.write({
            'sync': True
        })
        return True
    
    
    def delete_log(self):
        # get all un sync data
        line_ids = self.env['gravio.log'].search([('sync', '=', True)])
        
        line_ids.sudo().unlink()
        
        return True
    
    def refresh_page(self):
        return True