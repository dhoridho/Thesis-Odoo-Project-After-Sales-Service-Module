from odoo import models, fields, _
from odoo.exceptions import ValidationError
from datetime import timedelta

class MRInternalTransfer(models.TransientModel):
    _inherit = 'mr.internal_transfer'

    # def create_ir(self):
    #     source_warehouse = []
    #     for line in self.ir_wizard_line:
    #         if line.source_warehouse_id.id not in source_warehouse:
    #             source_warehouse.append(line.source_warehouse_id.id)
    #         if not line.source_warehouse_id.id:
    #             raise ValidationError("Please Add Warehouse For Internal Transfer")
    #         quantity = line.qty_transfer + line.mr_line_id.itr_requested_qty + line.mr_line_id.pr_requested_qty + line.mr_line_id.itw_requested_qty
    #         if quantity > line.mr_line_id.quantity:
    #             raise ValidationError(_('You cannot create a ITR for %s with more quantity then you Requested.') %
    #             (line.product_id.name))
    #         view_id = self.env.ref('equip3_inventory_operation.material_request_form_view').id
    #         if 'default_schedule_date' in self._context:
    #             return {
    #                 'name': 'Create Material Request',
    #                 'type': 'ir.actions.act_window',
    #                 'res_model': 'material.request',
    #                 'res_id': self.id,
    #                 'view_mode': 'form',
    #                 'view_id': view_id,
    #                 'target': 'new',
    #                 'context': {},
    #             }
    #     ir_id_list = []
    #     for loc in source_warehouse:
    #         ir_line = []
    #         source_location_id = self.env['stock.location'].search([('warehouse_id', '=', loc), ('usage', '=', 'internal')], limit=1, order="id")
    #         mr_id = self.ir_wizard_line.mapped('mr_id')
    #         destination_location_id = self.env['stock.location'].search([('warehouse_id', '=', mr_id.destination_warehouse_id.id), ('usage', '=', 'internal')], limit=1, order="id")
    #         for line in self.ir_wizard_line:
    #             if loc == line.source_warehouse_id.id:
    #                 vals = {
    #                     'product_id' : line.product_id.id,
    #                     # 'name' : line.description,
    #                     'uom' : line.uom_id.id,
    #                     'qty' : line.qty_transfer,
    #                     'scheduled_date' : self.ir_wizard_line.mr_id.schedule_date,
    #                     'destination_location_id': destination_location_id.id,
    #                     'source_location_id': source_location_id.id,
    #                     'description': line.description or line.product_id.display_name,
    #                     'source_document': self.ir_wizard_line.mr_id.name,
    #                     'requested_by': self.ir_wizard_line.mr_id.requested_by.id,
    #                     'company_id': self.ir_wizard_line.mr_id.company_id.id,
    #                 }
    #                 ir_line.append((0,0, vals))
    #                 warehouse_id = self.env['stock.warehouse'].search([('lot_stock_id','=',self.ir_wizard_line.mr_id.destination_location_id.id)])
    #                 warehouse_id_source = self.env['stock.warehouse'].search([('lot_stock_id','=',line.source_location.id)])


    #         #compute eexpiry date
    #         IrConfigParam = self.env['ir.config_parameter'].sudo()
    #         itr_expiry_days = IrConfigParam.get_param('mr_expiry_days', 'before')
    #         itr_ex_period = IrConfigParam.get_param('ex_period', 0)
    #         # if self.scheduled_date:
    #         if itr_expiry_days == 'before':
    #             expiry_date = self.ir_wizard_line.mr_id.schedule_date - timedelta(days=int(itr_ex_period))
    #         else:
    #             expiry_date = self.ir_wizard_line.mr_id.schedule_date + timedelta(days=int(itr_ex_period))
    #         ir_line_id = self.env['internal.transfer'].create({'product_line_ids': ir_line,
    #                                                     # 'mr_id': self.ir_wizard_line.mr_id.id,
    #                                                     'source_document': self.ir_wizard_line.mr_id.name,
    #                                                     'scheduled_date': self.ir_wizard_line.mr_id.schedule_date,
    #                                                     'expiry_date': expiry_date,
    #                                                     'source_location_id': source_location_id.id,
    #                                                     'analytic_account_group_ids': [(6, 0, self.ir_wizard_line.mr_id.analytic_account_group_ids.ids)],
    #                                                     'destination_location_id': destination_location_id.id,
    #                                                     'source_warehouse_id' : loc,
    #                                                     'destination_warehouse_id': self.ir_wizard_line.mr_id.destination_warehouse_id.id
    #                                                     })
    #         ir_line_id.write({'mr_id': [(4, self.ir_wizard_line.mr_id.id)]})
    #         ir_id_list.append(ir_line_id)
    #         ir_line_id.onchange_source_loction_id()
    #         ir_line_id.onchange_dest_loction_id()


    #     for line in ir_id_list:
    #         for ir_line in line.product_line_ids:
    #             mr_lines_id = self.env['material.request.line'].search([('material_request_id','=',self.ir_wizard_line.mr_id.id),('product', '=', ir_line.product_id.id)])
    #             if mr_lines_id:
    #                 mr_lines_id.write({'ir_lines_ids': [(4, ir_line.id)]})

    #     return