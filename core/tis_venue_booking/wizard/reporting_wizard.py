# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models, _
from odoo.tools.misc import xlwt
import io
import base64
from datetime import datetime
from datetime import timedelta


class ReportingWizard(models.TransientModel):
    _name = 'reporting.wizard'
    _description = 'Reporting Wizard'

    customer_ids = fields.Many2many("res.partner", string="Customers")
    date_start = fields.Datetime(string="Booking From")
    date_end = fields.Datetime(string="To")
    venue_id = fields.Many2many('venue.venue', string="Venue")
    booking_summary_file = fields.Binary('Booking Summary Report')
    file_name = fields.Char('File Name')
    booking_report_printed = fields.Boolean('Booking Report Printed')
    currency_id = fields.Many2one('res.currency', 'Currency', default=lambda self: self.env.user.company_id.currency_id)
    booking_status = fields.Selection([
        ('draft', 'Enquiry'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),],string="Booking Status")
    invoice_status = fields.Selection([('no', 'Nothing To Invoice'),
                                       ('invoiced', 'Fully Invoiced'),
                                       ('to invoice', 'To Invoice'),],string="Invoice status")

    def print_pdf_report(self, context=None):
        context = self._context
        data = {
            'ids': context.get('active_ids', []),
            'model': self._name,
            'form': {
                'customer_id': self.customer_ids.ids,
                'start_date': self.date_start,
                'end_date': self.date_end,
                'venue_id': self.venue_id.ids,
                'booking_status': self.booking_status,
                'invoice_status': self.invoice_status,

            },
        }
        return self.env.ref('tis_venue_booking.print_pdf_report').report_action(self, data=data)

    def print_xls_report(self, context=None):
        global states, inv_status
        lines = []
        s_date = self.date_start - timedelta(days=1)
        domain = [
            ('from_date', '>=', s_date),
            ('to_date', '<=', self.date_end),
        ]
        if self.customer_ids:
            domain.append(('partner_id', '=', self.customer_ids.ids))
        if self.venue_id:
            domain.append(('venue_id', '=', self.venue_id.ids))
        if self.booking_status:
            domain.append(('state', '=', self.booking_status))
        if self.invoice_status:
            domain.append(('invoice_status', '=', self.invoice_status))
        booking = self.env['booking.booking'].search(domain)
        for value in booking:
            state = value.state
            currency = value.currency_id.symbol
            vals = {
                'name': value.name,
                'venue': value.venue_id.name,
                'customer': value.partner_id.name,
                'start_date': value.from_date,
                'end_date': value.to_date,
                'type': value.booking_type,
                'duration': value.days_count,
                'venue_booking_charge': value.venue_booking_charge,
                'additional_booking_charge': value.additional_booking_charge,
                'amenities_amount_untaxed': value.amenities_amount_untaxed,
                'amount': value.amount_total,
                'amount_received': value.down_payment_amount,
                'amount_due': value.total_amount_due,
                'state': state,
                'invoice_status': value.invoice_status,
                'currency': currency
            }

            lines.append(vals)
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Booking Summary Report', cell_overwrite_ok=True)
        money_format = xlwt.XFStyle()
        money_format.num_format_str = self.currency_id.symbol + '#,##0.00'
        total_money_style = xlwt.easyxf('font:height 200;align: horiz right;'
                                        'font: color black;',
                                        num_format_str=self.currency_id.symbol + '#,##0.00')

        bold = xlwt.easyxf('font:bold True; align: horiz center; font:height 220;')
        text = xlwt.easyxf('font:height 200; align: horiz left;')
        header = xlwt.easyxf('font:bold True; font:height 400; align: horiz center; pattern: pattern solid,'
                             ' fore_colour gray25;')
        sub_header = xlwt.easyxf('font:bold True; font:height 350; align: horiz right; '
                                 'pattern: pattern solid, fore_colour gray25;')
        dates = xlwt.easyxf('font:bold True; font:height 350; align: horiz left; '
                            'pattern: pattern solid, fore_colour gray25;')
        worksheet.col(0).width = 5000
        worksheet.col(1).width = 5000
        worksheet.col(2).width = 5000
        worksheet.col(3).width = 7000
        worksheet.col(4).width = 7000
        worksheet.col(5).width = 5000
        worksheet.col(6).width = 5000
        worksheet.col(7).width = 5000
        worksheet.col(8).width = 5000
        worksheet.col(9).width = 5000
        worksheet.col(10).width = 5000
        worksheet.col(11).width = 5000
        worksheet.col(12).width = 5000
        worksheet.col(13).width = 5000
        worksheet.col(14).width = 5000
        worksheet.row(6).height = 300
        worksheet.write(6, 0, 'Booking Reference', bold)
        worksheet.write(6, 1, 'Venue', bold)
        worksheet.write(6, 2, 'Customer', bold)
        worksheet.write(6, 3, 'From', bold)
        worksheet.write(6, 4, 'To', bold)
        worksheet.write(6, 5, 'Type', bold)
        worksheet.write(6, 6, 'Duration', bold)
        worksheet.write(6, 7, 'Booking Charge', bold)
        worksheet.write(6, 8, 'Additional Charge', bold)
        worksheet.write(6, 9, 'Amenities charge', bold)
        worksheet.write(6, 10, 'Total Amount', bold)
        worksheet.write(6, 11, 'Payment Received', bold)
        worksheet.write(6, 12, 'Amount Due', bold)
        worksheet.write(6, 13, 'Status', bold)
        worksheet.write(6, 14, 'Invoice Status', bold)
        worksheet.write_merge(0, 2, 0, 14, "Venue Booking Report", header)
        worksheet.write_merge(3, 4, 0, 3, "From: ", sub_header)
        worksheet.write_merge(3, 4, 4, 5, datetime.strptime(str(self.date_start), '%Y-%m-%d %H:%M:%S').strftime(
            '%d-%m-%Y %H:%M:%S'), dates)
        worksheet.write_merge(3, 4, 6, 6, "To: ", sub_header)
        worksheet.write_merge(3, 4, 7, 14, datetime.strptime(str(self.date_end), '%Y-%m-%d %H:%M:%S').strftime(
            '%d-%m-%Y %H:%M:%S'), dates)
        row = 8
        col = 0
        for res in lines:
            if res['state'] == 'draft':
                states = "Enquiry"
            elif res['state'] == 'confirm':
                states = "Confirmed"
            elif res['state'] == 'cancel':
                states = "Cancelled"
            if res['invoice_status'] == 'no':
                inv_status = "Nothing to Invoice"
            elif res['invoice_status'] == 'invoiced':
                inv_status = "Fully Invoiced"
            elif res['invoice_status'] == 'to invoice':
                inv_status = "To Invoice"
            worksheet.write(row, col, res['name'], text)
            worksheet.write(row, col + 1, res['venue'], text)
            worksheet.write(row, col + 2, res['customer'], text)
            worksheet.write(row, col + 3, datetime.strptime(
                str(res['start_date']), '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%Y %H:%M:%S'), text)
            worksheet.write(row, col + 4, datetime.strptime(
                str(res['end_date']), '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%Y %H:%M:%S'), text)
            worksheet.write(row, col + 5, res['type'], total_money_style)
            if res['type'] == 'day':
                duration = str(res['duration']) + ' days'
                worksheet.write(row, col + 6, duration, total_money_style)
            elif res['type'] == 'hourly':
                duration = str(res['duration']) + ' hours'
                worksheet.write(row, col + 6, duration, total_money_style)
            worksheet.write(row, col + 7, res['venue_booking_charge'], total_money_style)
            worksheet.write(row, col + 8, res['additional_booking_charge'], total_money_style)
            worksheet.write(row, col + 9, res['amenities_amount_untaxed'], total_money_style)
            worksheet.write(row, col + 10, res['amount'], total_money_style)
            worksheet.write(row, col + 11, res['amount_received'], total_money_style)
            worksheet.write(row, col + 12, res['amount_due'], total_money_style)
            worksheet.write(row, col + 13, states)
            worksheet.write(row, col + 14, inv_status)
            row = row + 1

        fp = io.BytesIO()
        workbook.save(fp)
        excel_file = base64.encodestring(fp.getvalue())
        self.booking_summary_file = excel_file
        self.file_name = 'Booking Summary Report.xls'
        self.booking_report_printed = True
        fp.close()
        return {
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'reporting.wizard',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
