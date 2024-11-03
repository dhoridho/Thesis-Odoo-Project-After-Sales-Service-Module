import time
from datetime import timedelta, datetime
from odoo import api, fields, models
from odoo.exceptions import Warning

class RentalOrder(models.Model):
    _inherit = "rental.order"

    @api.constrains('start_date', 'final_end_date', 'rental_line')
    def _check_rental_buffer(self):
        for record in self:
            rental_start_date = record.start_date
            rental_end_date = record.final_end_date
            rental_lines = record.rental_line
            rental_id = record.id

            for line in rental_lines:
                lot_id = line.lot_id.id
                product_data = self.env['rental.order.line'].search([
                    ('lot_id', '=', lot_id),
                    '&',
                    ('buffer_end_time', '>', rental_start_date),
                    ('buffer_start_time', '<', rental_end_date),
                    ('rental_id', '!=', rental_id),
                    ('rental_id.state', 'in', ['confirm', 'running'])
                ])
                if product_data:
                    raise Warning(
                        'This product has already been rented in selected date. \n '
                        'Please change the start date and end date for the rent or close the already created rental for \n '
                        'this product to save rental order.')

    @api.model
    def create(self, vals):
        result = super(RentalOrder, self).create(vals)
        rental_start_date = result.start_date
        rental_end_date = result.end_date
        for line in result.rental_line:
            buffer_start_time = rental_start_date - timedelta(minutes=round((line.product_id.backup_start_time) * 60))
            buffer_end_time = rental_end_date + timedelta(minutes=round((line.product_id.backup_end_time) * 60))
            line.write({'buffer_start_time': buffer_start_time})
            line.write({'buffer_end_time': buffer_end_time})
        return result

    def write(self, vals):
            result = super(RentalOrder, self).write(vals)
            for rec in self:
                rental_start_date = rec.start_date
                rental_end_date = rec.end_date
                for line in self.rental_line:
                    buffer_start_time = rental_start_date - timedelta(minutes=round((line.product_id.backup_start_time) * 60))
                    buffer_end_time = rental_end_date + timedelta(minutes=round((line.product_id.backup_end_time) * 60))
                    line.write({'buffer_start_time': buffer_start_time})
                    line.write({'buffer_end_time': buffer_end_time})
            return result

    def action_button_confirm_rental(self):
        res = super(RentalOrder, self).action_button_confirm_rental()
        for order in self:
            state = order.state
            order_name = order.name
            if state == 'confirm':
                for line in order.rental_line:
                    buffer_start_time = line.buffer_start_time
                    buffer_end_time = line.buffer_end_time
                    serial_number = line.lot_id.id
                    product_id = line.product_id.id
                    lot_name = line.lot_id.name
                    product_name = line.product_id.name
                    rental_buffer_time = order_name+" - "+product_name+" - "+lot_name
                    line_vals = [{
                        'name': rental_buffer_time,
                        'rental_order_line_id': line.id,
                        'buffer_start_time': buffer_start_time,
                        'buffer_end_time': buffer_end_time,
                        'serial_no': serial_number,
                        'product_id': product_id,
                        'state': 'confirm',
                    }]
                    rbt_res = self.env['rental.buffer.time'].create(line_vals)
                    line.write({'rental_buffer_time_id': rbt_res.id})
                    line.write({'name': rental_buffer_time})
        return res
