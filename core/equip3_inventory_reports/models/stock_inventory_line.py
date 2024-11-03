
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_advance_inventory_reports.library import xlsxwriter

# class SetuInventoryAgeReport(models.TransientModel):
#     _inherit ="setu.inventory.age.report"

#     warehouse_ids = fields.Many2many("stock.warehouse", string="Warehouse")

#     def get_inventory_age_report_data(self):
#         """
#         :return:
#         """
#         category_ids = company_ids = {}
#         warehouse_ids = {}
#         if self.product_category_ids:
#             categories = self.env['product.category'].search([('id','child_of',self.product_category_ids.ids)])
#             category_ids = set(categories.ids) or {}
#         products = self.product_ids and set(self.product_ids.ids) or {}

#         if self.warehouse_ids:
#             warehouse_ids = self.warehouse_ids and set(self.warehouse_ids.ids) or {}

#         if self.company_ids:
#             companies = self.env['res.company'].search([('id','child_of',self.company_ids.ids)])
#             company_ids = set(companies.ids) or {}
#         else:
#             company_ids = set(self.env.context.get('allowed_company_ids',False) or self.env.user.company_ids.ids) or {}
#         query = """
#                 Select * from inventory_stock_age_report_inv('%s','%s','%s','%s')
#             """%(company_ids, products, category_ids, warehouse_ids)
#         self._cr.execute(query)
#         stock_data = self._cr.dictfetchall()
#         return  stock_data


class StockInventoryLine(models.Model):
    _inherit = "stock.inventory.line"

    difference_qty = fields.Float('Changes', compute='_compute_difference',
                                  help="Indicates the gap between the product's theoretical quantity and its newest quantity.",
                                  readonly=True, digits='Product Unit of Measure', search="_search_difference_qty", store=False)


# class InventoryInternalTransfer(models.Model):
#     _inherit = "internal.transfer"

#     arrival_date = fields.Datetime(
#         string="Arrival Date", default=datetime.now())

#     def action_confirm(self):
#         for transfer in self:
#             if not transfer.product_line_ids:
#                 raise ValidationError(_('Please add product lines'))
#             temp_list = []
#             line_vals_list = []
#             for line in transfer.product_line_ids:
#                 if line.scheduled_date.date() in temp_list:
#                     filter_line = list(filter(lambda r: r.get(
#                         'date') == line.scheduled_date.date(), line_vals_list))
#                     if filter_line:
#                         filter_line[0]['lines'].append(line)
#                 else:
#                     temp_list.append(line.scheduled_date.date())
#                     line_vals_list.append({
#                         'date': line.scheduled_date.date(),
#                         'lines': [line]
#                     })
#             for line_vals in line_vals_list:
#                 if transfer.is_transit:
#                     stock_move_obj = self.env['stock.move']
#                     transit_location = self.env.ref(
#                         'equip3_inventory_masterdata.location_transit')
#                     do_data = {
#                         'location_id': transfer.source_location_id.id,
#                         'location_dest_id': transit_location.id,
#                         'origin_dest_location': transfer.destination_location_id.location_id.name + '/' + transfer.destination_location_id.name,
#                         'move_type': 'direct',
#                         'partner_id': transfer.create_uid.partner_id.id,
#                         'scheduled_date': self.arrival_date,
#                         'analytic_account_group_ids': [(6, 0, transfer.source_location_id.warehouse_id.branch_id.analytic_tag_ids.ids)],
#                         'picking_type_id': transfer.operation_type_out_id.id,
#                         'origin': transfer.name,
#                         'transfer_id': transfer.id,
#                         # 'branch_id': transfer.branch_id and transfer.branch_id.id or False,
#                         'is_transfer_out': True,
#                         'company_id': transfer.company_id.id,
#                         'branch_id': transfer.source_location_id.warehouse_id.branch_id.id,
#                     }
#                     do_picking = self.env['stock.picking'].create(do_data)
#                     receipt_data = {
#                         'location_id': transit_location.id,
#                         'location_dest_id': transfer.destination_location_id.id,
#                         'origin_src_location': transfer.source_location_id.location_id.name + '/' + transfer.source_location_id.name,
#                         'move_type': 'direct',
#                         'partner_id': transfer.create_uid.partner_id.id,
#                         'scheduled_date': line_vals.get('date'),
#                         'picking_type_id': transfer.operation_type_in_id.id,
#                         'analytic_account_group_ids': [(6, 0, transfer.destination_location_id.warehouse_id.branch_id.analytic_tag_ids.ids)],
#                         'origin': transfer.name,
#                         'transfer_id': transfer.id,
#                         'is_transfer_in': True,
#                         'company_id': transfer.company_id.id,
#                         # 'branch_id': transfer.branch_id and transfer.branch_id.id or False,
#                         'branch_id': transfer.destination_location_id.warehouse_id.branch_id.id,
#                     }
#                     receipt_picking = self.env['stock.picking'].create(
#                         receipt_data)
#                     counter = 1
#                     for line in line_vals.get('lines'):
#                         receipt_move_data = {
#                             'move_line_sequence': counter,
#                             'picking_id': receipt_picking.id,
#                             'name': line.product_id.name,
#                             'product_id': line.product_id.id,
#                             'product_uom_qty': line.qty,
#                             'remaining_checked_qty': line.qty,
#                             'product_uom': line.uom.id,
#                             'analytic_account_group_ids': [(6, 0, receipt_picking.analytic_account_group_ids.ids)],
#                             'location_id': transit_location.id,
#                             'location_dest_id': line.destination_location_id.id,
#                             'origin_src_location': transfer.source_location_id.location_id.name + '/' + transfer.source_location_id.name,
#                             'date': self.arrival_date,
#                             'is_transit': True,
#                             'origin': transfer.name,
#                             # 'is_transfer_in': True,
#                         }
#                         receipt_move = stock_move_obj.create(receipt_move_data)
#                         self.check_qc(product=receipt_picking.product_id.id,
#                                       picking_type=receipt_picking.picking_type_id.id, move_id=receipt_move)
#                         do_move_data = {
#                             'move_line_sequence': counter,
#                             'picking_id': do_picking.id,
#                             'name': line.product_id.name,
#                             'product_id': line.product_id.id,
#                             'product_uom_qty': line.qty,
#                             'remaining_checked_qty': line.qty,
#                             'product_uom': line.uom.id,
#                             'analytic_account_group_ids': [(6, 0, do_picking.analytic_account_group_ids.ids)],
#                             'location_id': line.source_location_id.id,
#                             'location_dest_id': transit_location.id,
#                             'origin_dest_location': transfer.destination_location_id.location_id.name + '/' + transfer.destination_location_id.name,
#                             'date': self.arrival_date,
#                             'is_transit': True,
#                             'origin': transfer.name,
#                             # 'is_transfer_out': True,
#                         }
#                         do_move = stock_move_obj.create(do_move_data)
#                         self.check_qc(product=do_picking.product_id.id,
#                                       picking_type=do_picking.picking_type_id.id, move_id=do_move)
#                         counter += 1
#                 if not transfer.is_transit:
#                     do_data = {
#                         'location_id': transfer.source_location_id.id,
#                         'location_dest_id': transfer.destination_location_id.id,
#                         'move_type': 'direct',
#                         'partner_id': transfer.create_uid.partner_id.id,
#                         'scheduled_date': line_vals.get('date'),
#                         'picking_type_id': transfer.operation_type_out_id.id,
#                         'origin': transfer.name,
#                         'company_id': transfer.company_id.id,
#                         'analytic_account_group_ids': [(6, 0, transfer.analytic_account_group_ids.ids)],
#                         'branch_id': transfer.branch_id and transfer.branch_id.id or False,
#                         'transfer_id': transfer.id,
#                     }
#                     do_picking = self.env['stock.picking'].create(do_data)
#                     counter = 1
#                     for line in line_vals.get('lines'):
#                         stock_move_obj = self.env['stock.move']
#                         do_move_data = {
#                             'move_line_sequence': counter,
#                             'picking_id': do_picking.id,
#                             'name': line.product_id.name,
#                             'product_id': line.product_id.id,
#                             'product_uom_qty': line.qty,
#                             'product_uom': line.uom.id,
#                             'analytic_account_group_ids': [(6, 0, transfer.analytic_account_group_ids.ids)],
#                             'location_id': line.source_location_id.id,
#                             'location_dest_id': line.destination_location_id.id,
#                             'date': self.arrival_date,
#                         }
#                         counter += 1
#                         do_move = stock_move_obj.create(do_move_data)
#                 transfer.write({'state': 'confirm'})

#             stock_picking = self.env['stock.picking'].search(
#                 [('transfer_id', '=', self.id)])
#             if stock_picking:
#                 for picking in stock_picking:
#                     self.product_line_ids.write(
#                         {'picking_id': [(4, picking.id)]})
#                 # self.product_line_ids.write({'picking_id': (0, 0, stock_picking.ids)})
