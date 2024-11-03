
from odoo import models, fields, api, _
from odoo.exceptions import Warning, ValidationError

class IntrawarehouseTransfer(models.TransientModel):
    _name = 'intrawarehouse.transfer'
    _description = "Intrawarehouse Transfer"

    def default_intra_transfer_line(self):
        context = dict(self.env.context) or {}
        if context.get('active_model') == 'material.request':
            material_request_id = self.env['material.request'].browse(self._context.get('active_ids'))
            intra_tra = []
            count = 1
            error_lines = []
            counter = 1
            for line in material_request_id.product_line:
                vals = {
                    'no': count,
                    'mr_id': line.material_request_id.id,
                    'product_id' : line.product.id,
                    'description' : line.description,
                    'uom_id' : line.product.uom_id.id,
                    'qty_transfer' : line.quantity,
                    'mr_line_id': line.id,
                }
                intra_tra.append((0,0, vals))
                count = count+1
            return intra_tra
        else:
            material_request_line_ids = self.env['material.request.line'].browse(self._context.get('active_ids'))
            intra_tra = []
            count = 1
            error_lines = []
            counter = 1
            for line in material_request_line_ids:
                vals = {
                    'no': count,
                    'mr_id': line.material_request_id.id,
                    'product_id' : line.product.id,
                    'description' : line.description,
                    'uom_id' : line.product.uom_id.id,
                    'qty_transfer' : line.quantity,
                    'mr_line_id': line.id,
                }
                intra_tra.append((0,0, vals))
                count = count+1
            return intra_tra

    interawarehouse_transfer_ids = fields.One2many('intrawarehouse.transfer.line', 'intra_transfer_wizard_id', default=default_intra_transfer_line)

    def create_intra_transfer(self):
        mr_id = self.interawarehouse_transfer_ids[0].mr_id
        mr_id._check_processed_record(mr_id.id)
        for record in self:
            temp_data = []
            final_data = []
            for line in record.interawarehouse_transfer_ids:
                # quantity = line.qty_transfer + line.mr_line_id.itr_requested_qty + line.mr_line_id.pr_requested_qty + line.mr_line_id.itw_requested_qty
                # if quantity > line.mr_line_id.quantity:
                #     raise ValidationError(_('You cannot create a ITW for %s with more quantity then you Requested.') %
                #     (line.product_id.name))
                if {'source_loc_id': line.source_loc_id.id, 'dest_loc_id': line.dest_loc_id.id} in temp_data:
                    filter_lines = list(filter(lambda r:r.get('source_loc_id') == line.source_loc_id.id and r.get('dest_loc_id') == line.dest_loc_id.id, final_data))
                    if filter_lines:
                        filter_lines[0]['lines'].append({
                                'product_id' : line.product_id.id,
                                'description': line.description,
                                'product_uom': line.uom_id.id,
                                'product_uom_qty': line.qty_transfer,
                                'mr_line_id': line.mr_line_id.id,
                            })
                else:
                    temp_data.append({
                        'source_loc_id': line.source_loc_id.id,
                        'dest_loc_id': line.dest_loc_id.id
                    })
                    final_data.append({
                        'source_loc_id': line.source_loc_id.id,
                        'dest_loc_id': line.dest_loc_id.id,
                        'warehouse_id': line.warehouse_id,
                        'mr_id': line.mr_id,
                        'lines': [{
                            'product_id' : line.product_id.id,
                            'description': line.description,
                            'product_uom': line.uom_id.id,
                            'mr_line_id': line.mr_line_id.id,
                            'product_uom_qty': line.qty_transfer,
                        }]
                    })
            for data in final_data:
                vals = {
                     'warehouse_id': data.get('warehouse_id').id,
                     'picking_type_id': data.get('warehouse_id').int_type_id.id,
                     'location_id' : data.get('source_loc_id'),
                     'location_dest_id': data.get('dest_loc_id'),
                     'mr_id': data.get('mr_id').id,
                     'origin': data.get('mr_id').name,
                     'scheduled_date': data.get('mr_id').schedule_date,
                     'is_interwarehouse_transfer': True ,
                     'branch_id': data.get('mr_id').branch_id.id,
                     'move_ids_without_package':[(0, 0, {
                        'product_id': line.get('product_id'),
                        'mr_line_id': line.get('mr_line_id'),
                        'description_picking': line.get('description'),
                        'name': line.get('description'),
                        'product_uom_qty': line.get('product_uom_qty'),
                        'product_uom': line.get('product_uom'),
                    }) for line in data.get('lines')]
                }
                stock_picking_id = self.env['stock.picking'].create(vals)

        return True

class IntrawarehouseTransferLine(models.TransientModel):
    _name = 'intrawarehouse.transfer.line'
    _description = "Intrawarehouse Transfer Line"

    intra_transfer_wizard_id = fields.Many2one('intrawarehouse.transfer')
    no = fields.Integer(string="No")
    product_id = fields.Many2one('product.product', 'Product')
    description = fields.Text(string="Description")
    uom_id = fields.Many2one('uom.uom', string="Unit of Measure")
    source_loc_id = fields.Many2one('stock.location', string="Source Location")
    dest_loc_id = fields.Many2one('stock.location', string="Destination Location")
    qty_transfer = fields.Float(string="Quantity Transfer")
    filter_location_ids = fields.Many2many('stock.location', compute="_compute_location", store=False)
    warehouse_id = fields.Many2one(related="mr_id.destination_warehouse_id")
    mr_id = fields.Many2one('material.request', 'Material Request')
    mr_line_id = fields.Many2one('material.request.line')

    @api.depends('warehouse_id')
    def _compute_location(self):
        for record in self:
            location_ids = []
            if record.warehouse_id:
                location_obj = record.env['stock.location']
                store_location_id = record.warehouse_id.view_location_id.id
                addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_ids.append(location.id)
                child_location_ids = record.env['stock.location'].search([('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                final_location = child_location_ids + location_ids
                record.filter_location_ids = [(6, 0, final_location)]
            else:
                record.filter_location_ids = [(6, 0, [])]
