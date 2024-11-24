

from re import findall as regex_findall
from re import split as regex_split

# import packaging

from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    from odoo.addons.setu_advance_inventory_reports.library import xlsxwriter


class StockMove(models.Model):
    _inherit = 'stock.move'

    dpl_quantity = fields.Float(string='DPL Quantity')
    dpl_roll_qty = fields.Float(string='DPL Roll Quantity')
    move_note = fields.Char(string='Note')

    # remaining_mod = fields.Float(string='Initial Remaining', compute='_compute_remaining')
    # roll_remaining_mod = fields.Float(string='Roll Remaining', compute='_compute_roll_remaining')

    # @api.depends('initial_demand', 'quantity_done', 'roll_qty', 'actual_roll')
    # def _compute_remaining(self):
    #     for rec in self:
    #         rec.remaining_mod = rec.initial_demand - rec.quantity_done
    #         rec.roll_remaining_mod = rec.roll_qty - rec.actual_roll
    
    internal_transfer_line = fields.Many2one('internal.transfer.line', string='internal transfer line')

    # def _generate_lot_numbers(self, next_serial_count=False):
    #     self.ensure_one()
    #     if self.is_autogenerate:
    #         next_lot = self.next_lot
    #
    #     else:
    #         last_digit_check = self.next_lot_not_autogenerate and self.next_lot_not_autogenerate[-1] or ''
    #         if not last_digit_check.isdigit():
    #             raise ValidationError(
    #                 'New Lot Number Start From must contain digits behind it.')
    #         next_lot = self.next_lot_not_autogenerate
    #     if self.product_id and self.product_id.in_suffix:
    #         next_lot = next_lot.replace(self.product_id.in_suffix, '')
    #
    #     if '(' in next_lot and ')' in next_lot:
    #         start_index = next_lot.find("(")
    #         end_index = next_lot.find(")")
    #         next_lot = next_lot[:start_index] + next_lot[end_index+1:]
    #
    #     caught_initial_number = regex_findall("\d+", next_lot)
    #
    #     if not caught_initial_number:
    #         raise UserError(
    #             _('The serial number must contain at least one digit.'))
    #     initial_number = str(caught_initial_number[-1])
    #     padding = len(initial_number)
    #     splitted = regex_split(initial_number, next_lot)
    #     prefix = initial_number.join(splitted[:-1])
    #     # untuk menambah nama di lotnya
    #     # if self.picking_id.batch_id :
    #     #     batch = self.picking_id.batch_id
    #     #     if batch.no_container :
    #     #         prefix = "("+batch.no_container +")"+ prefix
    #     suffix = splitted[-1]
    #     if self.product_id and self.product_id.in_suffix:
    #         suffix = self.product_id.in_suffix
    #     initial_number = regex_findall(
    #         "\d+", self.product_id.in_current_sequence)
    #     initial_number = int(initial_number[-1])
    #     self.product_id.in_current_sequence = initial_number if self.product_id.in_current_sequence != initial_number else False
    #     lot_names = []
    #     for i in range(0, int(next_serial_count)):
    #         lot_names.append('%s%s%s' % (
    #             prefix,
    #             str(initial_number + i).zfill(padding),
    #             suffix
    #         ))
    #     return lot_names

    @api.onchange('dpl_quantity')
    def onchange_to_generate(self):
        for res in self:
            res.qty_to_generate = res.dpl_quantity


class StockMoveLineMod(models.Model):
    _inherit = 'stock.move.line'

    # batch_id = fields.Many2one('stock.picking.batch', string='Batch Reference', compute='_compute_batch_id', store=True)
    # no_container = fields.Char(string='No Container', compute='_compute_no_container')

    # @api.depends('move_id.no_container', 'batch_id.no_container')
    # def _compute_no_container(self):
    #     for record in self:
    #         record.no_container = record.move_id.no_container or record.batch_id.no_container or 'False'
            
    # @api.depends('picking_id.batch_id')
    # def _compute_batch_id(self):
    #     for move_line in self:
    #         move_line.batch_id = move_line.picking_id.batch_id.id if move_line.picking_id.batch_id else False

# class InventoryInternalTransfer(models.Model):
#     _inherit = "internal.transfer"
#
#     arrival_date = fields.Datetime(string="Arrival Date", default=datetime.now())
#
#
#     def action_confirm(self): # disini guys
#         for transfer in self:
#             if not transfer.product_line_ids:
#                 raise ValidationError(_('Please add product lines'))
#             temp_list = []
#             line_vals_list = []
#             for line in transfer.product_line_ids:
#                 if line.scheduled_date.date() in temp_list:
#                     filter_line = list(filter(lambda r:r.get('date') == line.scheduled_date.date(), line_vals_list))
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
#                     transit_location = self.env.ref('equip3_inventory_masterdata.location_transit')
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
#                     receipt_picking = self.env['stock.picking'].create(receipt_data)
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
#                             'internal_transfer_line': line.id,
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
#                         self.check_qc(product=receipt_picking.product_id.id, picking_type=receipt_picking.picking_type_id.id, move_id=receipt_move)
#                         do_move_data = {
#                             'move_line_sequence': counter,
#                             'picking_id': do_picking.id,
#                             'name': line.product_id.name,
#                             'product_id': line.product_id.id,
#                             'product_uom_qty': line.qty,
#                             'remaining_checked_qty': line.qty,
#                             'product_uom': line.uom.id,
#                             'internal_transfer_line': line.id,
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
#                         self.check_qc(product=do_picking.product_id.id, picking_type=do_picking.picking_type_id.id, move_id=do_move)
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
#                             'internal_transfer_line': line.id,
#                             'product_uom': line.uom.id,
#                             'analytic_account_group_ids': [(6, 0, transfer.analytic_account_group_ids.ids)],
#                             'location_id': line.source_location_id.id,
#                             'location_dest_id': line.destination_location_id.id,
#                             'date': self.arrival_date,
#                         }
#                         counter += 1
#                         do_move = stock_move_obj.create(do_move_data)
#                 transfer.write({'state': 'confirm'})
#
#             stock_picking = self.env['stock.picking'].search([('transfer_id','=', self.id)])
#             if stock_picking:
#                 for picking in stock_picking:
#                     self.product_line_ids.write({'picking_id': [(4, picking.id)]})
#                 # self.product_line_ids.write({'picking_id': (0, 0, stock_picking.ids)})