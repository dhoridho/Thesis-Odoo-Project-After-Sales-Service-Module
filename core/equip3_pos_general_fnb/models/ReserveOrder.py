# -*- coding: utf-8 -*

import pytz
from datetime import timedelta,datetime

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class ReserveOrder(models.Model):
    _name = 'reserve.order'
    _description = 'Reserve Order'
    _order = 'create_date desc'

    name = fields.Char(string="Reservation ID", readonly=True)
    state = fields.Selection([('reserved', 'Reserved'),('arrived', 'Arrived'),('cancel', 'Cancelled')],string="State",default='reserved')
    customer_name = fields.Char(string="Customer Name", required=True)
    cust_phone_no = fields.Char(string="Phone Number")
    reservation_from = fields.Datetime(string="Reservation From", required=True)
    reservation_to = fields.Datetime(string="Reservation To", required=True)
    table_no = fields.Many2one('restaurant.table',string="Table No")
    table_floor = fields.Many2one('restaurant.floor',string="Table Floor")
    reservation_seat = fields.Char(string="Reservation Seat")
    arrived_time = fields.Datetime()
    guest = fields.Char(string="Cashier Guest")
    company_id = fields.Many2one('res.company','Company', default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch','Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    
    def guest_arrived(self):
        self.state = 'arrived'

    def guest_cancel_order(self):
        self.state = 'cancel'

    @api.model
    def create(self, vals):
        sequence_no = self.env['ir.sequence'].next_by_code('reserve.order')
        vals.update({'name': sequence_no})
        return super(ReserveOrder, self).create(vals)
    
    def write(self, vals):
        for rec in self:
            if 'state' in vals and vals.get('state') == 'arrived' and rec.state != 'arrived':
                vals.update({'arrived_time': datetime.now()})
        return super(ReserveOrder, self).write(vals)

    @api.model
    def check_customer_arrived_time(self, floor_id, config_id):
        orders = self.search([('state', '=', 'arrived'),('arrived_time','!=',False),('table_floor','=',floor_id)])
        seat_time = self.env['pos.config'].browse(config_id).seat_time
        result =[]
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        for order in orders:
            estimated_time = (order.arrived_time + timedelta(minutes=seat_time))
            display_time = datetime.strftime(pytz.utc.localize(datetime.strptime(order.arrived_time.strftime("%Y-%m-%d %H:%M:%S"), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),"%H:%M:%S")
            vals = {
                'table_no': order.table_no.id,
                'arrived_time': display_time,
                'in_time':1 if estimated_time > datetime.now() else 0
            }
            result.append(vals)
        return result

    def cancel_order(self):
        self.write({ 'state': 'cancel' })
        return {
            'id': self.id,
            'state': self.state
        }