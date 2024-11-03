from odoo import models, fields, _
from odoo.exceptions import ValidationError


class IntrawarehouseTransfer(models.TransientModel):
    _inherit = 'intrawarehouse.transfer'

    # def create_intra_transfer(self):
    #     print('ASSET')
    #     for record in self:
    #         temp_data = []
    #         final_data = []
    #         for line in record.interawarehouse_transfer_ids:
    #             quantity = line.qty_transfer + line.mr_line_id.itr_requested_qty + line.mr_line_id.pr_requested_qty + line.mr_line_id.itw_requested_qty
    #             if quantity > line.mr_line_id.quantity:
    #                 raise ValidationError(_('You cannot create a ITW for %s with more quantity then you Requested.') %
    #                 (line.product_id.name))
    #             if {'source_loc_id': line.source_loc_id.id, 'dest_loc_id': line.dest_loc_id.id} in temp_data:
    #                 filter_lines = list(filter(lambda r:r.get('source_loc_id') == line.source_loc_id.id and r.get('dest_loc_id') == line.dest_loc_id.id, final_data))
    #                 if filter_lines:
    #                     filter_lines[0]['lines'].append({
    #                             'product_id' : line.product_id.id,
    #                             'description': line.description,
    #                             'product_uom': line.uom_id.id,
    #                             'product_uom_qty': line.qty_transfer,
    #                             'mr_line_id': line.mr_line_id.id,
    #                         })
    #             else:
    #                 temp_data.append({
    #                     'source_loc_id': line.source_loc_id.id,
    #                     'dest_loc_id': line.dest_loc_id.id
    #                 })
    #                 final_data.append({
    #                     'source_loc_id': line.source_loc_id.id,
    #                     'dest_loc_id': line.dest_loc_id.id,
    #                     'warehouse_id': line.warehouse_id,
    #                     'mr_id': line.mr_id,
    #                     'lines': [{
    #                         'product_id' : line.product_id.id,
    #                         'description': line.description,
    #                         'product_uom': line.uom_id.id,
    #                         'mr_line_id': line.mr_line_id.id,
    #                         'product_uom_qty': line.qty_transfer,
    #                     }]
    #                 })
    #         for data in final_data:
    #             vals = {
    #                  'warehouse_id': data.get('warehouse_id').id,
    #                  'picking_type_id': data.get('warehouse_id').int_type_id.id,
    #                  'location_id' : data.get('source_loc_id'),
    #                  'location_dest_id': data.get('dest_loc_id'),
    #                  'mr_id': data.get('mr_id').id,
    #                  'origin': data.get('mr_id').name,
    #                  'scheduled_date': data.get('mr_id').schedule_date,
    #                  'is_interwarehouse_transfer': True ,
    #                  'branch_id': data.get('mr_id').branch_id.id,
    #                  'move_ids_without_package':[(0, 0, {
    #                     'product_id': line.get('product_id'),
    #                     'mr_line_id': line.get('mr_line_id'),
    #                     'description_picking': line.get('description'),
    #                     'name': line.get('description'),
    #                     'product_uom_qty': line.get('product_uom_qty'),
    #                     'product_uom': line.get('product_uom'),
    #                 }) for line in data.get('lines')]
    #             }
    #             stock_picking_id = self.env['stock.picking'].create(vals)
    #     view_id = self.env.ref('equip3_inventory_operation.material_request_form_view').id
    #     if 'default_schedule_date' in self._context:
    #         return {
    #             'name': 'Create Material Request',
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'material.request',
    #             'res_id': self.id,
    #             'view_mode': 'form',
    #             'view_id': view_id,
    #             'target': 'new',
    #             'context': {},
    #         }
