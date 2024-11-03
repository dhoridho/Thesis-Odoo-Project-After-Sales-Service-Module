from odoo import models, fields, _
from odoo.exceptions import ValidationError


class PurchaseRequestRequest(models.TransientModel):
    _inherit = 'purchase.request.wizard'

    # def create_pr(self):
    #     pr_line = []
    #     mr_id_line = []
    #     warehouse_id = False
    #     for line in self.pr_wizard_line:
    #         quantity = line.qty_purchase + line.mr_line_id.itr_requested_qty + line.mr_line_id.pr_requested_qty + line.mr_line_id.itw_requested_qty
    #         if quantity > line.mr_line_id.quantity:
    #             raise ValidationError(_('You cannot create a PR for %s with more quantity then you Requested.') %
    #             (line.product_id.name))
    #         vals = {
    #             'product_id' : line.product_id.id,
    #             'name' : line.description,
    #             'product_uom_id' : line.uom_id.id,
    #             'product_qty' : line.qty_purchase,
    #             'is_goods_orders': True,
    #             'date_required' : line.request_date,
    #             'company_id' : line.mr_id.company_id.id,
    #             'dest_loc_id': line.mr_id.destination_warehouse_id.id,
    #             # 'procurement_id' : line.procurement_order.id,
    #         }
    #         pr_line.append((0,0, vals))
    #         warehouse_id = line.mr_id.destination_warehouse_id

    #     # print "self.env.context.get('active_id')..............................",self.env.context.get('active_id')
    #     pr_id = self.env['purchase.request'].create({'line_ids': pr_line,
    #                                                    'is_goods_orders': True, 'origin': self.pr_wizard_line and self.pr_wizard_line[-1].mr_id.name or '',
    #                                                    'picking_type_id': warehouse_id.in_type_id.id,
    #                                                    'branch_id': line.mr_line_id.material_request_id.branch_id.id})
    #     pr_id.write({'mr_id': [(4, self.pr_wizard_line.mr_id.id)]})
    #     print('prl', pr_id)
    #     for line in pr_id.line_ids:
    #         mr_lines_id = self.env['material.request.line'].search([('material_request_id','=',self.pr_wizard_line.mr_id.id),('product','=',line.product_id.id)])
    #         if mr_lines_id:
    #             mr_lines_id.write({'pr_lines_ids': [(4, line.id)]})

    #     # print('prldo', pr_line.is_goods_orders)
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
    #     return
