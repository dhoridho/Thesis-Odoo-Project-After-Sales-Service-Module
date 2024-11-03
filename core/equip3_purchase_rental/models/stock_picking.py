
from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from re import findall as regex_findall
from re import split as regex_split
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_rental_orders = fields.Boolean(string='Is Rental', compute='_compute_is_rental', store=True)

    # def button_validate(self):
    #     self.env.context = dict(self.env.context)
    #     if 'rentals_orders' in self.env.context:
    #         self.env.context.update({'from_picking': True})
    #     res = super(StockPicking, self).button_validate()
    #     return res

    @api.depends('purchase_ids', 'purchase_order_id')
    def _compute_is_rental(self):
        for record in self:
            if record.purchase_order_id and record.purchase_order_id.is_rental_orders or \
                record.purchase_ids and any(order.is_rental_orders for order in record.purchase_ids):
                record.is_rental_orders = True
            else:
                record.is_rental_orders = False

    def _create_delivery_order(self):
        record = self
        for purchase in record.purchase_ids:
            warehouse = record.picking_type_id.warehouse_id
            location_id = warehouse.out_type_id.default_location_src_id.id
            location_dest_id = self.env.ref('stock.stock_location_customers').id
            vals = {
                'partner_id': record.partner_id.id,
                'picking_type_id': warehouse.out_type_id.id,
                'location_id': location_id,
                'location_dest_id': location_dest_id,
                'origin': record.name,
                'scheduled_date': purchase.expected_return_date,
                'company_id': record.company_id.id,
                'branch_id': record.branch_id.id,
                'purchase_order_id': purchase.id
            }
            picking_id = self.env['stock.picking'].create(vals)
            for move in record.move_ids_without_package:
                new_move = move.copy({
                    'picking_id': picking_id.id,
                    'picking_type_id': picking_id.picking_type_id.id,
                    'location_id': location_id,
                    'location_dest_id': location_dest_id,
                    "scheduled_date": purchase.expected_return_date,
                })
            picking_id.write({
                'scheduled_date': purchase.expected_return_date,
            })
            picking_id.action_confirm()
            picking_id.action_assign()

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for record in self:
            if record.picking_type_id.code == "incoming" or not record.is_rental_orders:
                for move in record.move_ids_without_package:
                    next_serial_count_number = int(move.quantity_done) + int(move.product_id.product_tmpl_id.current_sequence)
                    current_sequence = str(next_serial_count_number).zfill(move.product_id.product_tmpl_id.digits)
                    move.product_id.product_tmpl_id.current_sequence = current_sequence
            if record.is_rental_orders and record.picking_type_id.code == "incoming" and record.state == "done":
                record._create_delivery_order()
        return res

class StockMove(models.Model):
    _inherit = "stock.move"

    @api.constrains('fulfillment')
    def _check_fulfillment(self):
        for rec in self:
            if (rec.picking_id.is_rental_orders and rec.picking_id.picking_type_code == 'incoming') \
            or (rec.product_id.product_tmpl_id.is_rented and not rec.picking_id.is_rental_orders):
                continue
            else:
                return super(StockMove, self)._check_fulfillment()

    def _generate_serial_numbers(self, next_serial_count=False, is_sn_autogenerate=True):
        if (self.picking_id.is_rental_orders and self.picking_id.picking_type_code == 'incoming') \
            or (self.product_id.product_tmpl_id.is_rented and not self.picking_id.is_rental_orders):
            self.ensure_one()
            next_serial_count = self.next_serial_count
            # We look if the serial number contains at least one digit.
            caught_initial_number = regex_findall("\d+", self.next_serial)
            if not caught_initial_number:
                raise UserError(_('The serial number must contain at least one digit.'))
            # We base the serie on the last number find in the base serial number.
            initial_number = caught_initial_number[-1]
            padding = len(self.product_id.product_tmpl_id.current_sequence)
            # We split the serial number to get the prefix and suffix.
            splitted = regex_split(initial_number, self.next_serial)
            # initial_number could appear several times in the SN, e.g. BAV023B00001S00001
            prefix = self.product_id.product_tmpl_id.sn_prefix
            suffix = self.product_id.product_tmpl_id.suffix or ''
            initial_number = int(self.product_id.product_tmpl_id.current_sequence) + 1

            lot_names = []
            for i in range(0, next_serial_count):
                lot_names.append('%s%s%s' % (
                    prefix,
                    str(initial_number + i).zfill(padding),
                    suffix
                ))
            move_lines_commands = self._generate_serial_move_line_commands(lot_names)
            self.write({'move_line_ids': move_lines_commands})
            return True
        else:
            return super(StockMove, self)._generate_serial_numbers(next_serial_count=next_serial_count)

class StockAssignSerialNumbers(models.TransientModel):
    _inherit = 'stock.assign.serial'

    def generate_serial_numbers(self):
        if (self.move_id.picking_id.is_rental_orders and self.move_id.picking_id.picking_type_code == 'incoming') \
            or (self.product_id.product_tmpl_id.is_rented and not self.move_id.picking_id.is_rental_orders):
            self.ensure_one()
            self.move_id.next_serial = self.next_serial_number or ""
            return self.move_id._generate_serial_numbers(next_serial_count=self.next_serial_count)
        else:
            return super(StockAssignSerialNumbers, self).generate_serial_numbers()
