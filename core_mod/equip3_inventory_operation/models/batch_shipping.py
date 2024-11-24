# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from lxml import etree
from odoo.exceptions import ValidationError


class BatchShippingPicking(models.Model):
    _inherit = "stock.picking"

    is_batch_shipping_picking = fields.Boolean(
        string="Is Batch Shipping Picking")
    is_batch_shipping_packing = fields.Boolean(
        string="Is Batch Shipping Packing")
    is_batch_shipping_delivery = fields.Boolean(
        string="Is Batch Shipping Delivery")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    batch_shipping_line = fields.One2many(
        'batch.shipping.line', 'batch_shipping_id', string="Batch Shipping Line")
    state = fields.Selection(selection_add=[("deployed", "Deployed")])
    is_deployed = fields.Boolean(
        string="Is Deployed", compute="check_is_deployed")

    def button_create_picking(self):
        all_warehouse = []
        selected_picking_obj = []
        picking_ids = []

        for rec in self:
            if rec.state == 'done':
                raise ValidationError(
                    _("You can only create a picking state not in done."))
            else:
                all_warehouse.append(rec.warehouse_id.id)
                selected_picking_obj.append(rec)
                picking_ids.append(rec.id)
        result = all(element == all_warehouse[0] for element in all_warehouse)
        if not result:
            raise ValidationError(
                _("The selected Record need to within the same Warehouse."))
        else:
            for line in selected_picking_obj:
                batch_data = {}
                batch_data['user_id'] = line.user_id.id
                batch_data['warehouse_id'] = line.warehouse_id.id
                batch_data['location_ids'] = [(6, 0, [line.location_id.id])]
                batch_data['company_id'] = line.company_id.id
                batch_data['scheduled_date'] = line.scheduled_date
                batch_data['branch_id'] = line.branch_id.id
                batch_data['picking_type_id'] = line.picking_type_id.id
                batch_data['picking_ids'] = [(6, 0, picking_ids)]
                batch_obj = self.env['stock.picking.batch'].create(batch_data)
                break

        return True

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        context = self.env.context
        result = super(BatchShippingPicking, self).fields_view_get(
            view_id, view_type, toolbar=toolbar, submenu=submenu)
        if context.get('default_is_batch_shipping_packing'):
            doc = etree.XML(result['arch'])
            location_id = doc.xpath("//field[@name='location_id']")
            picking_type_id = doc.xpath("//field[@name='picking_type_id']")
            if location_id and picking_type_id:
                location_id[0].set('domain',
                                   "[('warehouse_delivery_steps','=', 'pick_pack_ship'),('usage','=','internal'),('name', '=', 'Packing Zone')]")
                picking_type_id[0].set(
                    'domain', "[('warehouse_id','=', warehouse_id),('code','=','internal')]")
            result['arch'] = etree.tostring(doc, encoding='unicode')
            return result
        elif context.get('default_is_batch_shipping_delivery'):
            doc = etree.XML(result['arch'])
            location_id = doc.xpath("//field[@name='location_id']")
            picking_type_id = doc.xpath("//field[@name='picking_type_id']")
            if location_id and picking_type_id:
                location_id[0].set('domain',
                                   "[('warehouse_delivery_steps','=', 'pick_pack_ship'),('usage','=','internal'),('name', '=', 'Output')]")
                picking_type_id[0].set(
                    'domain', "[('warehouse_id','=', warehouse_id),('code','=','internal')]")
            result['arch'] = etree.tostring(doc, encoding='unicode')
            return result
        return result

    @api.depends('state')
    def check_is_deployed(self):
        for record in self:
            if record.state == 'assigned':
                for line in record.batch_shipping_line:
                    line.picking_id.state = 'deployed'
                record.is_deployed = True
            else:
                record.is_deployed = False

    @api.onchange('location_id', 'location_dest_id')
    def onchange_location_id(self):
        result = super(BatchShippingPicking, self).onchange_location_id()
        context = self.env.context
        if context.get('default_is_batch_shipping_packing'):
            for location in self.location_id:
                self.warehouse_id = location.warehouse_id.id
                delivery_zone = self.env['stock.location'].search(
                    [('name', '=', 'Output'), ('warehouse_id', '=', location.warehouse_id.id)])
                picking_type_id = self.env['stock.picking.type'].search(
                    [('warehouse_id', '=', self.warehouse_id.id), ('code', '=', 'internal'),
                     ('name', '=', 'Pack'), ('default_location_src_id', '=', location.id)])
                self.picking_type_id = picking_type_id
                self.location_dest_id = delivery_zone
            return result
        elif context.get('default_is_batch_shipping_delivery'):
            for location in self.location_id:
                self.warehouse_id = location.warehouse_id.id
                delivery_zone = self.env['stock.location'].search(
                    [('name', '=', 'Customers'), ('usage', '=', 'customer'), ('warehouse_id', '=', False)])
                picking_type_id = self.env['stock.picking.type'].search(
                    [('warehouse_id', '=', self.warehouse_id.id), ('code', '=', 'outgoing'),
                     ('name', '=', 'Delivery Orders'), ('default_location_src_id', '=', location.id)])
                self.picking_type_id = picking_type_id
                self.location_dest_id = delivery_zone
            return result
        else:
            return result

    @api.model
    def create(self, vals):
        picking = super(BatchShippingPicking, self).create(vals)

        if picking.is_batch_shipping_packing:
            for operation in picking.picking_type_id:
                code = operation.sequence_code
                for record in picking:
                    picking_seq = record.name
                    picking_seq = picking_seq.replace(str(code), "PACK")
                    record.name = picking_seq

        elif picking.is_batch_shipping_delivery:
            for operation in picking.picking_type_id:
                code = operation.sequence_code
                for record in picking:
                    picking_seq = record.name
                    picking_seq = picking_seq.replace(str(code), "OUT")
                    record.name = picking_seq
        mail_message = self.env['mail.message'].search(
            [('res_id', '=', picking.id)])
        for record in mail_message:
            record.body = "Transfer created"
        return picking

    @api.onchange('batch_shipping_line')
    def get_detailed_operations_line(self):
        serial_no = 1
        data_list = []
        used_picking_ids = []
        if self.batch_shipping_line:
            for line in self.batch_shipping_line:
                if line.picking_id:
                    used_picking_ids.append(line.picking_id.id)
                    for move in line.picking_id.move_ids_without_package:
                        vals = {'name': move.product_id.default_code,
                                'reference': self.name,
                                'product_id': move.product_id.id,
                                'location_id': move.location_id.id,
                                'location_dest_id': move.location_dest_id.id,
                                'product_uom_qty': move.product_uom_qty,
                                'product_uom': move.product_id.uom_id.id,
                                'date': self.scheduled_date,
                                'picking_type_id': self.picking_type_id.id,
                                'picking_id': self.id,
                                'source_picking_id': line.picking_id.id,
                                'source_move_id': move.id,
                                'is_batch_shipping_packing': self.is_batch_shipping_packing
                                }
                        data_list.append([0, 0, vals])
                        serial_no += 1
            if len(data_list) != 0:
                self.move_ids_without_package = False
                self.move_ids_without_package = data_list
                self.batch_shipping_line.used_picking_ids = False
                self.batch_shipping_line.used_picking_ids = used_picking_ids
        else:
            self.move_ids_without_package = False
            self.move_line_ids_without_package = False


class BatchShippingLine(models.Model):
    _name = "batch.shipping.line"
    _description = "Batch Shipping Line"

    serial_number = fields.Integer(string='No')
    picking_id = fields.Many2one('stock.picking', string="Picking")
    warehouse_id = fields.Many2one(
        related="batch_shipping_id.warehouse_id", string="Warehouse")
    batch_shipping_id = fields.Many2one(
        'stock.picking', string="Batch Shipping Ref")
    used_picking_ids = fields.Many2many('stock.picking', string="Used Picking")

    @api.onchange('picking_id')
    def get_picking_domain(self):
        context = self.env.context
        if context.get('is_batch_shipping_packing') == True:
            return {
                'domain': {
                    'picking_id': "[('warehouse_id', '=', warehouse_id),('id', 'not in', used_picking_ids),('state', '=', 'done')]"
                }
            }
        elif context.get('is_batch_shipping_delivery') == True:
            return {
                'domain': {
                    'picking_id': "[('warehouse_id', '=', warehouse_id),('is_batch_shipping_packing', '=', True),('id', 'not in', used_picking_ids),('state', '=', 'done')]"
                }
            }

    @api.model
    def default_get(self, fields):
        res = super(BatchShippingLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'batch_shipping_line' in context_keys:
                if len(self._context.get('batch_shipping_line')) > 0:
                    next_sequence = len(self._context.get(
                        'batch_shipping_line')) + 1
            res.update({'serial_number': next_sequence})
        return res


BatchShippingLine()
