# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import models, api


class BookingPdf(models.AbstractModel):
    _name = 'report.tis_venue_booking.report_bookingreport_template'
    _description = "Booking Report PDF Format"

    @api.model
    def _get_report_values(self, docids, data):
        """Getting values from wizard.
        Search using domain and find ids from class.
        Assign field values to dictionary doc """

        global inv_status, states
        start_date = data['form']['start_date']
        end_date = data['form']['end_date']
        customer_ids = data['form']['customer_id']
        venue_ids = data['form']['venue_id']
        booking_status = data['form']['booking_status']
        invoice_status = data['form']['invoice_status']
        docs = []
        active_id = self._context.get('active_id')
        domain = [
            ('from_date', '>=', start_date),
            ('to_date', '<=', end_date),
        ]
        if customer_ids:
            domain = domain + [('partner_id', '=', customer_ids)]
        if venue_ids:
            domain = domain + [('venue_id', '=', venue_ids)]
        if booking_status:
            domain = domain + [('state', '=', booking_status)]
        if invoice_status:
            domain = domain + [('invoice_status', '=', invoice_status)]
        booking = self.env['booking.booking'].search(domain)
        for booking in booking:
            if invoice_status:
                if booking.invoice_status == invoice_status:
                    if booking.state == 'draft':
                        states = "Enquiry"
                    elif booking.state == 'confirm':
                        states = "Confirmed"
                    elif booking.state == 'cancel':
                        states = "Cancelled"
                    if booking.invoice_status == 'no':
                        inv_status = "Nothing to Invoice"
                    elif booking.invoice_status == 'invoiced':
                        inv_status = "Fully Invoiced"
                    elif booking.invoice_status == 'to invoice':
                        inv_status = "To Invoice"
                    docs.append({
                        'name': booking.name,
                        'venue': booking.venue_id.name,
                        'customer': booking.partner_id.name,
                        'start_date': booking.from_date,
                        'end_date': booking.to_date,
                        'venue_booking_charge': booking.venue_booking_charge,
                        'additional_booking_charge': booking.additional_booking_charge,
                        'amenities_amount_untaxed': booking.amenities_amount_untaxed,
                        'total_amount': booking.amount_total,
                        'currency': booking.currency_id,
                        'amount_received': booking.down_payment_amount,
                        'amount_due': booking.total_amount_due,
                        'state': states,
                        'invoice_status': inv_status
                    })
            else:
                if booking.state == 'draft':
                    states = "Enquiry"
                elif booking.state == 'confirm':
                    states = "Confirmed"
                elif booking.state == 'cancel':
                    states = "Cancelled"
                if booking.invoice_status == 'no':
                    inv_status = "Nothing to Invoice"
                elif booking.invoice_status == 'invoiced':
                    inv_status = "Fully Invoiced"
                elif booking.invoice_status == 'to invoice':
                    inv_status = "To Invoice"
                docs.append({
                    'name': booking.name,
                    'venue': booking.venue_id.name,
                    'customer': booking.partner_id.name,
                    'start_date': booking.from_date,
                    'end_date': booking.to_date,
                    'venue_booking_charge': booking.venue_booking_charge,
                    'additional_booking_charge': booking.additional_booking_charge,
                    'amenities_amount_untaxed': booking.amenities_amount_untaxed,
                    'total_amount': booking.amount_total,
                    'currency': booking.currency_id,
                    'amount_received': booking.down_payment_amount,
                    'amount_due': booking.total_amount_due,
                    'state': states,
                    'invoice_status': inv_status
                })

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'docs': docs,
            'start_date': start_date,
            'end_date': end_date,
            'customer_ids': customer_ids,
            'venue_ids': venue_ids

        }
