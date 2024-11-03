# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.
from dateutil import parser

from odoo import fields, models, api, _
from datetime import datetime, timedelta
import pytz
from odoo.osv import expression
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class BookingBooking(models.Model):
    _name = "booking.booking"
    _description = 'Venue Booking Details'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def _compute_invoice_count(self):
        """Calculating invoice count(including refund ids)"""
        for booking in self:
            invoice_ids = self.env['account.move'].search([('invoice_origin', '=', booking.name)])
            domain_inv = expression.OR([
                ['&', ('invoice_origin', '=', inv.name), ('journal_id', '=', inv.journal_id.id)]
                for inv in invoice_ids if inv.name
            ])
            if domain_inv:
                refund_ids = self.env['account.move'].search(expression.AND([
                    ['&', ('move_type', '=', 'out_refund'), ('invoice_origin', '!=', False)],
                    domain_inv
                ]))
            else:
                refund_ids = self.env['account.move'].browse()
            booking.update({'invoice_ids': invoice_ids.ids + refund_ids.ids,
                            'invoice_count': len(set(invoice_ids.ids + refund_ids.ids))
                            })

    partner_id = fields.Many2one('res.partner', string='Customer')
    name = fields.Char(string='Reference Number', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]},
                       index=True, default=lambda self: _('New'))
    from_date = fields.Datetime(string="Booking From", index=True, required=True)
    to_date = fields.Datetime(string="Booking Till", index=True, required=True)
    venue_id = fields.Many2one('venue.venue', string="Venue", required=True)
    state = fields.Selection([
        ('draft', 'Enquiry'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'), ],
        string='Status', readonly=True, default='draft')
    confirmation_date = fields.Datetime(string='Confirmation Date', readonly=True, copy=False)
    booking_type = fields.Selection([
        ('day', 'Day Basis'),
        ('hourly', 'Hourly Basis')], string="Booking Type", default='day', store=True, required=True)
    booking_amenities_ids = fields.One2many('booking.amenities', 'booking_id', string='Amenities', copy=False)
    currency_id = fields.Many2one(
        'res.currency', 'Currency', compute='_compute_currency_id')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account",
                                          related='venue_id.analytic_account_id')
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('booking.amenities'), index=1)

    partner_name = fields.Char("Customer")
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    zip = fields.Char('Zip', change_default=True)
    city = fields.Char('City')
    state_id = fields.Many2one("res.country.state", string='State', domain="[('country_id', '=', country_id)]")
    country_id = fields.Many2one('res.country', string='Country')
    phone = fields.Char('Phone')
    mobile = fields.Char('Mobile')
    email_from = fields.Char('Email', track_visibility='onchange',
                             track_sequence=4, index=True)
    website = fields.Char('Website')
    lost_reason = fields.Char(string="Reason")
    description = fields.Text(string="Description")
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange',
                              track_sequence=2, default=lambda self: self.env.user)
    total_hours = fields.Float(string="Hours", compute='_compute_days_count', rounding_method='UP', store=True)
    days_count = fields.Float(string="Days count", rounding_method='UP')
    days = fields.Float(string="Days", compute='_compute_days_count', rounding_method='UP', store=True)
    venue_tax_ids = fields.Many2many('account.tax', string='Venue Taxes', compute='_depends_venue_id', store=True)
    booking_charge = fields.Monetary(string="Venue Charge", compute='_depends_venue_id', store=True)
    additional_charge = fields.Monetary(string="Additional Charges", compute='_depends_venue_id', store=True, help="Mandatory additional charges will be applicable for this venue such as for any services.")
    venue_booking_charge = fields.Monetary(string="Venue Charge", compute='_amount_all', store=True)
    additional_booking_charge = fields.Monetary(compute='_amount_all', string="Additional Charge", store=True)
    amenities_amount_untaxed = fields.Monetary(string='Extra Amenities Charge', store=True, readonly=True,
                                               compute='_amount_all', track_visibility='onchange', track_sequence=5)
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all',
                                   track_visibility='always', track_sequence=6)
    total_tax = fields.Monetary(string='Tax', readonly=True, compute='_amount_all', store=True)

    invoice_ids = fields.Many2many("account.move", string='Invoices', readonly=True,
                                   copy=False, compute='_compute_invoice_count')
    invoice_count = fields.Integer(string='Invoice Count', readonly=True, compute='_compute_invoice_count')
    advance_amount = fields.Float(string="Advance Amount", store=True)
    venue_qty_to_invoice = fields.Float(compute='_qty_to_invoice')
    additional_charge_to_invoice = fields.Float(compute='_qty_to_invoice')
    down_payment_to_invoice = fields.Float(compute='_qty_to_invoice')
    down_payment_amount = fields.Monetary(string="Full Down Payment Amount", readonly=True,
                                          compute='_compute_amount_due')
    total_amount_due = fields.Monetary(string="Amount Due", readonly=True, compute='_compute_amount_due',
                                       track_visibility='always')
    invoice_status = fields.Selection([
        ('no', 'Nothing To Invoice'),
        ('invoiced', 'Fully Invoiced'),
        ('to invoice', 'To Invoice'),
    ], string='Invoice Status', compute='_qty_to_invoice')
    narration = fields.Text(string="Note")
    from_time = fields.Float(related='venue_id.start_time')
    end_time = fields.Float(related='venue_id.end_time')

    _sql_constraints = [
        ('date_check2', "CHECK ((from_date <= to_date))", "The start date must be anterior to the end date.")

    ]

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange('venue_id')
    def _onchange_amenities(self):
        self.booking_amenities_ids = [(5, 0, 0)]
        inclusive_amenities = self.venue_id.venue_amenities_ids.filtered(lambda x: x.type == 'inclusive')
        for rec in inclusive_amenities:
            vals2 = {
                'amenities_id': rec.id,
                'types': rec.type,
                'quantity': 0,
                'price': 0,
                'duration': 0,
                'price_subtotal': 0,
                'booking_id': self.id,
                'fl': True
            }
            result = self.env['booking.amenities'].create(vals2)

    def _compute_currency_id(self):
        main_company = self.env['res.company']._get_main_company()
        for template in self:
            template.currency_id = template.company_id.sudo().currency_id.id or main_company.currency_id.id

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('booking.booking') or _('New')
        bookings = self.env['booking.booking'].search([
            ('venue_id', '=', vals['venue_id']), ('state', '=', 'confirm'),
            '|', '|',
            '&', ('from_date', '<=', vals['from_date']), ('to_date', '>=', vals['from_date']),
            '&', ('from_date', '<=', vals['to_date']), ('to_date', '>=', vals['to_date']),
            '&', ('from_date', '>', vals['from_date']), ('to_date', '<', vals['to_date'])]
        )
        if bookings:
            raise UserError(_('Venue is not available for selected period .'))
        print(vals)
        res1 = super(BookingBooking, self).create(vals)
        return res1

    def write(self, vals):
        if 'from_date' in vals or 'to_date' in vals or 'venue_id' in vals:
            from_date = vals.get('from_date', self.from_date)
            to_date = vals.get('to_date', self.to_date)
            venue = vals.get('venue_id', self.venue_id.id)
            bookings = self.env['booking.booking'].search([
                ('venue_id', '=', venue), ('state', '=', 'confirm'),
                '|', '|',
                '&', ('from_date', '<=', from_date), ('to_date', '>=', from_date),
                '&', ('from_date', '<=', to_date), ('to_date', '>=', to_date),
                '&', ('from_date', '>', from_date), ('to_date', '<', to_date), ]
            )
            if bookings:
                raise UserError(_('Venue is not available for selected period .'))
            record1 = super(BookingBooking, self).write(vals)
        return super(BookingBooking, self).write(vals)

    def _onchange_partner_id_values(self, partner_id):
        """ returns the new values when partner_id has changed """
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            partner_name = partner.parent_id.name
            if not partner_name and partner.is_company:
                partner_name = partner.name
            return {
                'partner_name': partner_name,
                'street': partner.street,
                'street2': partner.street2,
                'city': partner.city,
                'state_id': partner.state_id.id,
                'country_id': partner.country_id.id,
                'email_from': partner.email,
                'phone': partner.phone,
                'mobile': partner.mobile,
                'zip': partner.zip,
                'website': partner.website,
            }
        return {}

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        values = self._onchange_partner_id_values(self.partner_id.id if self.partner_id else False)
        self.update(values)

    @api.depends('from_date', 'to_date', 'booking_type')
    def _compute_days_count(self):
        """Calculating booking duration"""
        for booking in self:
            # active = self.env['ir.config_parameter'].sudo().get_param('tis_venue_booking.activate_day')
            ftime = self.from_time
            etime = self.end_time
            if ftime == 0.0 and etime == 0.0:
                if booking.from_date and booking.to_date:
                    delta = datetime.strptime(str(booking.to_date), '%Y-%m-%d %H:%M:%S') - datetime.strptime(
                        str(booking.from_date), '%Y-%m-%d %H:%M:%S')
                    if booking.booking_type == 'day':
                        booking.days = float(delta.days + 1)
                    else:
                        booking.total_hours = float(delta.total_seconds()) / 3600
            else:
                hours = int(float(ftime))
                st_seconds, st_minutes = divmod(ftime * 60, 3600)
                st_hours, st_minutes = divmod(st_minutes, 60)
                minutes = int(st_minutes)
                seconds = (minutes * 3600) % 60
                ehours = int(float(etime))
                end_seconds, end_minutes = divmod(etime * 60, 3600)
                end_hours, end_minutes = divmod(end_minutes, 60)
                eminutes = int(end_minutes)
                eseconds = (eminutes * 3600) % 60

                if booking.from_date and booking.to_date:

                    delta = datetime.strptime(str(booking.to_date), '%Y-%m-%d %H:%M:%S') - datetime.strptime(
                        str(booking.from_date), '%Y-%m-%d %H:%M:%S')

                    if booking.booking_type == 'day':
                        booking.from_date = booking.from_date.replace(hour=hours, minute=minutes, second=seconds)
                        booking.to_date = booking.to_date.replace(hour=ehours, minute=eminutes, second=eseconds)
                        user_tz = self.env.user.tz or pytz.utc
                        local = pytz.timezone(user_tz)
                        now = datetime.strftime(pytz.utc.localize(
                            datetime.strptime(str(booking.from_date), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(
                            local), "%Y-%m-%d %H:%M:%S")
                        now_to_object = parser.parse(now)
                        diff = now_to_object - booking.from_date
                        hour_to_subtract = diff.seconds // 3600
                        min_to_subtract = (diff.seconds // 60) % 60
                        booking.from_date = booking.from_date - timedelta(hours=hour_to_subtract,
                                                                          minutes=min_to_subtract)
                        booking.to_date = booking.to_date - timedelta(hours=hour_to_subtract, minutes=min_to_subtract)
                        booking.days = float(delta.days + 1)
                    else:
                        booking.total_hours = float(delta.total_seconds()) / 3600
                # else:
                #     if booking.from_date and booking.to_date:
                #
                #         delta = datetime.strptime(str(booking.to_date), '%Y-%m-%d %H:%M:%S') - datetime.strptime(
                #             str(booking.from_date), '%Y-%m-%d %H:%M:%S')
                #
                #         if booking.booking_type == 'day':
                #             booking.days = float(delta.days + 1)
                #         else:
                #             booking.total_hours = float(delta.total_seconds()) / 3600

    def calculate_days_count(self):
        for booking in self:
            if booking.from_date and booking.to_date:
                delta = datetime.strptime(str(booking.to_date), '%Y-%m-%d %H:%M:%S') - datetime.strptime(
                    str(booking.from_date),
                    '%Y-%m-%d %H:%M:%S')
                if booking.booking_type == 'day':
                    return float(delta.days + 1)
                else:
                    return float(delta.total_seconds()) / 3600

    @api.depends('venue_id', 'booking_type')
    def _depends_venue_id(self):
        for booking in self:
            booking.venue_tax_ids = booking.venue_id.taxes
            if booking.booking_type == 'day':
                booking.booking_charge = booking.venue_id.charges_per_day \
                    if booking.venue_id.charges_per_day else 0
                booking.additional_charge = booking.venue_id.additional_charges_per_day \
                    if booking.venue_id.additional_charges_per_day else 0
            else:
                booking.booking_charge = booking.venue_id.charges_per_hour \
                    if booking.venue_id.charges_per_hour else 0
                booking.additional_charge = booking.venue_id.additional_charges_per_hour \
                    if booking.venue_id.additional_charges_per_hour else 0

    @api.depends('booking_charge', 'additional_charge', 'booking_amenities_ids.price_total',
                 'venue_tax_ids', 'days', 'total_hours')
    def _amount_all(self):
        """ Compute the total amounts of the Booking Order."""
        for booking in self:
            booking.days_count = booking.calculate_days_count()
            booking.venue_booking_charge = booking.booking_charge * booking.days_count
            booking.additional_booking_charge = booking.additional_charge * booking.days_count
            tax = booking.venue_tax_ids.compute_all(booking.booking_charge, booking.currency_id, booking.days_count,
                                                    product=booking.venue_id, partner=booking.partner_id)
            tax_calc = sum(t.get('amount', 0.0) for t in tax.get('taxes', []))
            amenities_amount_untaxed = amenities_amount_tax = 0.0
            for line in booking.booking_amenities_ids:
                amenities_amount_untaxed += line.price_subtotal
                amenities_amount_tax += line.price_tax
            booking.amenities_amount_untaxed = amenities_amount_untaxed
            booking.total_tax = tax_calc + amenities_amount_tax
            booking.amount_total = booking.venue_booking_charge + booking.additional_booking_charge + booking.total_tax \
                                   + booking.amenities_amount_untaxed

    @api.onchange('booking_amenities_ids', 'venue_id', 'booking_type')
    def _onchange_booking_amenities_ids(self):
        """On changing venue this function checks the amenities already present is available for the new venue"""
        for booking in self:
            if booking.booking_amenities_ids:
                for amenity in booking.booking_amenities_ids:
                    # if amenity.amenities_id.id not in booking.venue_id.venue_amenities_ids.mapped('amenities_id').ids:
                    #     raise UserError(_('The amenity %s is not available %s ') %
                    #                     (amenity.amenities_id.name, booking.venue_id.name))
                    # else:
                    line_id = booking.venue_id.venue_amenities_ids.filtered(
                        lambda line: line.amenities_id.id == amenity.amenities_id.id)
                    if not amenity.fl:
                        if line_id.type == 'inclusive':
                            raise UserError(_('The selected amenity %s is already included in the %s Package') %
                                            (amenity.amenities_id.amenities_id.name, booking.venue_id.name))

                        # else:
                        #     amenity.taxes = line_id.taxes
                        #     if booking.booking_type == 'hourly':
                        #         amenity.price = line_id.charge_per_hour
                        #     elif booking.booking_type == 'day':
                        #         amenity.price = line_id.charge_per_day

    def action_cancel(self):
        return self.write({'state': 'cancel'})

    def print_booking_order(self):
        return self.env.ref('tis_venue_booking.action_report_booking_order').report_action(self)

    def reset_to_enquiry(self):
        if self.invoice_status == 'invoiced':
            raise UserError(_('Cant change to enquiry.'))
        else:
            self.state = 'draft'

    def send_whatsapp_msg_link(self):
        if self.mobile:
            mobile_num = self.mobile.replace(" ", "").replace("+", "").replace("-", "").replace("(", "").replace(
                ")", "")
            return {
                'type': 'ir.actions.act_url',
                'url': "https://api.whatsapp.com/send?phone=" + mobile_num,
                'target': '_blank',
                'res_id': self.id,
            }

    def send_whatsapp_msg(self):
        state = ''
        if self.state == 'draft':
            state = '*Booked*'
        elif self.state == 'confirm':
            state = '*Booking Confirmed*'
        elif self.state == 'cancel':
            state = '*Booking Cancelled*'
        booking_type = ' *Number of Days* ' + str(self.days) if self.booking_type == 'day' else ' *Total Hours* ' + str(
            round(self.total_hours, 2))
        message = state + ' %0a' + ' *Booking Number:* ```' + self.name + '```' + ',%0a' + ' *From:* ' \
                  + str(self.from_date) + ',%0a' + ' *Till:* ' + str(self.to_date) + ',%0a' + \
                  booking_type + ',%0a' + ' *Amount Total:* ' + str(self.amount_total) + str(self.currency_id.symbol)
        message_string = ''
        message = message.split(' ')
        for msg in message:
            message_string = message_string + msg + '%20'
        message_string = message_string[:(len(message_string) - 3)]
        mobile = self.mobile or self.partner_id.mobile
        if mobile:
            mobile_num = mobile.replace(" ", "")
            mobile_num = mobile_num.replace("+", "")
            return {
                'type': 'ir.actions.act_url',
                'url': "https://api.whatsapp.com/send?phone=" + mobile_num + "&text=" + message_string,
                'target': '_blank',
                'res_id': self.id,
            }
        else:
            raise UserError(_('Please Configure Whatsapp Number with country code  to Customer.'))

    def action_confirm_booking(self):
        all_dates = {}
        all_dates_list = []
        bookings = self.env['booking.booking'].search([
            ('venue_id', '=', self.venue_id.id), ('state', '=', 'confirm'),
            '|', '|',
            '&', ('from_date', '<=', self.from_date), ('to_date', '>=', self.from_date),
            '&', ('from_date', '<=', self.to_date), ('to_date', '>=', self.to_date),
            '&', ('from_date', '>', self.from_date), ('to_date', '<', self.to_date), ]
        )
        if bookings:
            raise UserError(_('Venue is not available for selected period .'))
        else:
            if self.partner_id:
                self.confirmation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.state = 'confirm'
            else:
                return {
                    'name': _('Confirm Booking'),
                    'view_mode': 'form',
                    'res_model': 'partner.binding',
                    'view_id': self.env.ref('tis_venue_booking.booking_confirming_form').id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                }

    def action_booking_confirmation_send(self):
        """This function opens a window to compose an email, with the edi booking template message loaded by default"""
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data.get_object_reference('tis_venue_booking', 'email_template_edi_booking_final_3')[
                1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False

        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'booking.booking',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
        })
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def _qty_to_invoice(self):
        """calculating qty to invoice.
        This function tracks id venues and addidtional charges id from configuration.
        using the id , function finds the qty invoiced from the invoice generated and calculate the remaining qty to invoice.
        Based on the qty to invoice and the invoice line status of amenities booking orer status will be calculated"""
        for booking in self:
            booking.days_count = booking.calculate_days_count()
            venue_id = booking.env['product.product'].browse(int(
                booking.env['ir.config_parameter'].sudo().get_param('tis_venue_booking.venue_product_id')))
            additional_charge_id = booking.env['product.product'].browse(int(
                booking.env['ir.config_parameter'].sudo().get_param(
                    'tis_venue_booking.additional_charge_product_id')))
            down_payment_product_id = booking.env['product.product'].browse(int(
                booking.env['ir.config_parameter'].sudo().get_param('tis_venue_booking.down_payment_product_id')))
            invoices = booking.mapped('invoice_ids')
            venue_to_invoice = 0
            charge_to_invoice = 0
            dp_to_invoice = 0
            if invoices:
                for val in invoices:
                    if val.move_type != 'out_refund':
                        to_invoice_venue = val.invoice_line_ids.filtered(lambda x: x.product_id == venue_id).quantity
                        invoiced_venue_price = val.invoice_line_ids.filtered(
                            lambda x: x.product_id == venue_id).price_subtotal
                        venue_to_invoice = venue_to_invoice + to_invoice_venue
                        booking.venue_qty_to_invoice = booking.days_count - venue_to_invoice
                        to_invoice_charge = val.invoice_line_ids.filtered \
                            (lambda x: x.product_id == additional_charge_id).quantity
                        if booking.additional_charge:
                            charge_to_invoice = charge_to_invoice + to_invoice_charge
                            booking.additional_charge_to_invoice = booking.days_count - charge_to_invoice
                        else:
                            booking.additional_charge_to_invoice = 0
                        down_invoiced = val.invoice_line_ids.filtered(
                            lambda x: x.product_id == down_payment_product_id).price_subtotal
                        dp_to_invoice = dp_to_invoice + down_invoiced
                        booking.down_payment_to_invoice = dp_to_invoice
            else:
                booking.venue_qty_to_invoice = booking.days_count
                if booking.additional_charge:
                    booking.additional_charge_to_invoice = booking.days_count
                else:
                    booking.additional_charge_to_invoice = 0
                booking.down_payment_to_invoice = booking.advance_amount
            line_status = ''
            if booking.booking_amenities_ids:
                for vals in booking.booking_amenities_ids:
                    if vals.invoice_stat == 'to invoice':
                        line_status = 'to invoice'
                    else:
                        line_status = 'invoiced'
            if (
                    booking.venue_qty_to_invoice > 0 or booking.additional_charge_to_invoice > 0 or booking.down_payment_to_invoice > 0) or line_status == 'to invoice':
                booking.invoice_status = 'to invoice'
            else:
                booking.invoice_status = 'invoiced'
            if booking.state == 'cancel':
                booking.invoice_status = 'no'
            elif booking.state == 'draft':
                booking.invoice_status = 'to invoice'

    @api.depends('invoice_ids', 'amount_total')
    def _compute_amount_due(self):
        for booking in self:
            inv_amount_paid = 0
            for invoice in booking.invoice_ids:
                if invoice.state in 'posted':
                    inv_amount_paid += (invoice.amount_total_signed - invoice.amount_residual_signed)
            booking.update({
                'total_amount_due': booking.amount_total - inv_amount_paid,
                'down_payment_amount': inv_amount_paid})

    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    def _compute_access_url(self):
        super(BookingBooking, self)._compute_access_url()
        for booking in self:
            booking.access_url = '/my/bookings/%s' % (booking.id)

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s ' % (self.name)


class BookingAmenities(models.Model):
    _name = "booking.amenities"
    _description = "Amenities for booking"
    _order = 'booking_id, id'

    booking_id = fields.Many2one('booking.booking')
    # amenities_id = fields.Many2one("amenities.amenities", string='Name')
    ref_venue_id = fields.Many2one("venue.venue", related="booking_id.venue_id")
    amenities_id = fields.Many2one("venue.amenities", string='Name')
    charge = fields.Float(string="Charge")
    taxes = fields.Many2many('account.tax', string='Taxes')
    quantity = fields.Float(string="Quantity", default=1.0)
    price = fields.Float(string="Unit Price")
    price_subtotal = fields.Float(compute='_compute_amount', string="Sub Total", readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('booking.amenities'), index=1)
    currency_id = fields.Many2one(
        'res.currency', 'Currency', compute='_compute_currency_id')
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)
    state = fields.Selection([
        ('draft', 'Booked'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'), ],
        related='booking_id.state', string='Order Status', readonly=True, copy=False, store=True, default='draft')
    invoice_lines = fields.Many2many('account.move.line', 'booking_order_line_invoice_rel',
                                     'amenities_line_id', 'invoice_line_id', string='Invoice Lines', copy=False)
    qty_to_invoice = fields.Float(
        compute='_get_to_invoice_qty', string='To Invoice Quantity', store=True, readonly=True,
        digits='Product Unit of Measure')
    qty_invoiced = fields.Float(
        compute='_get_invoice_qty', string='Invoiced Quantity', store=True, readonly=True,
        digits='Product Unit of Measure')
    invoice_stat = fields.Selection([
        ('invoiced', 'Fully Invoiced'),
        ('to invoice', 'To Invoice'),
        ('no', 'Nothing to Invoice')
    ], string='Invoice Status', default='no', compute='_get_to_invoice_qty')
    duration = fields.Float(string="Duration", related='booking_id.days_count')
    fl = fields.Boolean(string="flag", default=False)
    types = fields.Selection([
        ('inclusive', 'Inclusive'),
        ('additional', 'Additional')], default='additional', string="Type", readonly=True)

    def create(self, vals_list):
        return super(BookingAmenities, self).create(vals_list)

    @api.onchange('amenities_id')
    def _onchange_amenities_id(self):

        amenities = self.env['venue.amenities'].search([('venue_id', '=', self.ref_venue_id.id)])
        for lines in amenities:
            if lines.type == 'additional':
                if lines.amenities_id.name == self.amenities_id.amenities_id.name:
                    if self.booking_id.booking_type == 'day':
                        self.price = lines.charge_per_day
                    else:
                        self.price = lines.charge_per_hour


    def _compute_currency_id(self):
        main_company = self.env['res.company']._get_main_company()
        for template in self:
            template.currency_id = template.company_id.sudo().currency_id.id or main_company.currency_id.id


    @api.depends('quantity', 'discount', 'price', 'taxes', 'duration')
    def _compute_amount(self):
        for line in self:
            prices = line.price * (1 - (line.discount or 0.0) / 100.0)
            tax = line.taxes.compute_all(prices, line.booking_id.currency_id, line.quantity * line.duration,
                                         product=line.amenities_id, partner=line.booking_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in tax.get('taxes', [])),
                'price_total': tax['total_included'],
                'price_subtotal': tax['total_excluded'],
            })


    @api.depends('qty_invoiced', 'quantity', 'booking_id.state', 'duration')
    def _get_to_invoice_qty(self):
        """
        Compute the quantity to invoice. If the invoice policy is order, the quantity to invoice is
        calculated from the ordered quantity. Otherwise, the quantity delivered is used.
        """
        for line in self:
            if line.state in ['confirm']:
                line.qty_to_invoice = (line.quantity * line.duration) - line.qty_invoiced
            else:
                line.qty_to_invoice = 0
            if line.qty_to_invoice > 0:
                line.update({'invoice_stat': 'to invoice'})
            else:
                line.update({'invoice_stat': 'invoiced'})


    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity')
    def _get_invoice_qty(self):
        for line in self:
            qty_invoiced = 0.0
            for invoice_line in line.invoice_lines:
                if invoice_line.move_id.state != 'cancel':
                    if invoice_line.move_id.move_type == 'out_invoice':
                        qty_invoiced += invoice_line.quantity
                    elif invoice_line.move_id.move_type == 'out_refund':
                        qty_invoiced -= invoice_line.quantity
            line.qty_invoiced = qty_invoiced


class LostReason(models.Model):
    _name = "lost.reason"
    _description = 'Lost Reason'

    name = fields.Char(string="Reason")
