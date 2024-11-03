# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import fields, models, tools, api, _


class BookingReport(models.Model):
    _name = "booking.report"
    _description = 'Booking Analysis Report'
    _auto = False

    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    name = fields.Char(string='Order Reference', readonly=True)
    from_date = fields.Datetime(string="Booking From", readonly=True)
    to_date = fields.Datetime(string="Booking Till", readonly=True)
    venue_id = fields.Many2one('venue.venue', readonly=True, string="Venue")
    state = fields.Selection([
        ('draft', 'Booked'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'), ],
        string='Status', readonly=True)
    partner_name = fields.Char("Customer Name", readonly=True)
    lost_reason = fields.Char(string="Cancel Reason", readonly=True)
    venue_booking_charge = fields.Float(string="Total Venue charge", readonly=True)
    additional_booking_charge = fields.Float(string="Additional Booking Charge",  readonly=True)
    amenities_amount_untaxed = fields.Float(string="Amenities Amount", readonly=True)
    amount_total = fields.Float(string="Total Amount", readonly=True)
    booking_type = fields.Selection([
        ('day', 'Day Basis'),
        ('hourly', 'Hourly Basis')], string="Booking Type", readonly=True)

    total_tax = fields.Float(string="Tax amount", readonly=True)
    down_payment_amount = fields.Float(string="Payment Received", readonly=True)
    amount_due = fields.Float(string="Amount Due", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""CREATE or REPLACE VIEW %s as (
                %s
                FROM booking_booking as b
                left join venue_venue v on (v.id = b.venue_id )
                %s
                )""" % (self._table, self._select(), self._group_by()))

    def _select(self):
        select_str = """
        SELECT
            min(b.id) as id,
            b.name as name,
            b.partner_id as partner_id,
            b.from_date as from_date,
            b.to_date as to_date,
            b.venue_id as venue_id,
            b.state as state,
            b.booking_type as booking_type,
            b.lost_reason as lost_reason,
            b.partner_name as partner_name,
            b.venue_booking_charge as venue_booking_charge,
            b.additional_booking_charge as additional_booking_charge,
            b.amenities_amount_untaxed as amenities_amount_untaxed,
            b.amount_total as amount_total,
            (SELECT SUM(i.amount_total_signed - i.amount_residual_signed)
                 FROM account_move i
                  WHERE (i.invoice_origin = b.name) and (i.state = 'draft' or i.state = 'posted')) 
             as down_payment_amount,
            (SELECT b.amount_total - SUM(i.amount_total_signed - i.amount_residual_signed) FROM account_move as i
                 WHERE (i.invoice_origin = b.name) and (i.state = 'draft' or i.state = 'posted')) as amount_due,
            b.total_tax
            """

        return select_str

    def _from(self):
        from_str = """
               booking_booking as b
                join account_move as am on (am.invoice_origin = b.name)"""
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
            b.name,
            b.partner_id,
            b.from_date,
            b.to_date,
            b.venue_id,
            b.state,
            b.partner_name,
            b.lost_reason,
            b.booking_type,
            b.venue_booking_charge,
            b.additional_booking_charge,
            b.amenities_amount_untaxed,
            b.total_tax,
            b.amount_total
        """
        return group_by_str
