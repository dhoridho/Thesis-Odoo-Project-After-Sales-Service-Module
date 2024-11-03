# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

import pytz
from datetime import timedelta, date, datetime
import datetime
from dateutil import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning, ValidationError




class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    rental_order_ids = fields.Many2many('fleet.vehicle.order', 'rental_order',
                                        string='Rental Orders', copy=False)

    @api.model
    def _compute_reference_prefix(self, values):
        prefix = super(PaymentTransaction, self)._compute_reference_prefix(values)
        if not prefix and values:
            prefix = 'Rental Order'
        return prefix

    def render_rental_button(self, order, submit_txt=None, render_values=None):
        values = {
            'partner_id': order.partner_shipping_id.id or order.partner_invoice_id.id,
            'billing_partner_id': order.partner_invoice_id.id,
        }
        if render_values:
            values.update(render_values)
        # Not very elegant to do that here but no choice regarding the design.
        self._log_payment_transaction_sent()
        return self.acquirer_id.with_context(submit_class='btn btn-primary',
                                             submit_txt=submit_txt or _('Pay Now')).sudo().render(self.reference, order.total_amount, order.pricelist_id.currency_id.id, values=values)

class FleetVehicleOrder(models.Model):
    _name = "fleet.vehicle.order"
    _description = 'FLeet Vehicle Order'
    _rec_name = "res_number"

    def default_partner(self):
        return self.customer_name.id

    res_number = fields.Char(string='Order number', readonly=True, default='New')
    vehicle_name = fields.Many2one('fleet.vehicle', string="Vehicle Name")
    from_date = fields.Datetime(string='From Date')
    to_date = fields.Datetime(string='To Date')
    start_date = fields.Char(string='start Date')
    end_date = fields.Char(string='end Date')
    customer_name = fields.Many2one('res.partner', string='Customer Name')
    book_date = fields.Datetime(string='Booking Date',
                                default=datetime.datetime.now().strftime('%Y-%m-%d'))
    is_driver = fields.Boolean(string="Driver Require?", default=False)
    account_payment_term = fields.Many2one('account.payment.term',
                                           string="Payment Term", require=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('cancel', 'Cancel'), ('close', 'Close')], default="draft")
    is_invoice = fields.Boolean(string="invoice")
    fleet_vehicle_ids = fields.One2many('fleet.vehicle', 'fleet_registration_id', string="Vehicle")
    vehicle_order_lines = fields.One2many('vehicle.order.line', 'vehicle_order_id',
                                          string="Order Line")
    is_agreement = fields.Boolean(string='Contracts Require?', default=True)
    vehicle_order_lines_ids = fields.One2many('vehicle.order.line', 'vehicle_order_id',
                                              string="Order Line ")
    opportunity_id = fields.Char('Customer Reference')
    invoice_count = fields.Integer(compute='_invoice_total', string="Total Invoiced")
    contract_count = fields.Integer(compute='_contract_total', string="Total Contract")
    move_count = fields.Integer(compute='_move_total', string="Total Invoiced ")
    move_ids = fields.One2many('fleet.vehicle.move', 'vehicle_order_rel_id', string="Move Id")
    driver_id = fields.Many2one('hr.employee', string='Driver Id')
    invoice_ids = fields.One2many('account.move', 'rental_order_id', string="Invoice Id")
    contract_ids = fields.One2many('fleet.vehicle.contract', 'rental_id', string="Contract Id")
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")
    extra_charges = fields.Monetary(string='Extra Charges', readonly=True,default=0.0)
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_amount', store=True)
    taxes = fields.Monetary(string='Taxes', compute='_compute_amount', store=True)
    untaxed_amount = fields.Monetary(string='Untaxed Amount', compute='_compute_amount', store=True)
    vehicle_type_id = fields.Many2one('fleet.vehicle.type', string='Vehicle Type')
    user_id = fields.Many2one('res.users', string='Dealer', default=lambda self: self.env.user)
    terms_condition = fields.Text(string='Terms And Condition')
    invoice_status = fields.Char(compute='get_invoice_status', string='Invoice Status')
    station_id = fields.Many2one('fleet.vehicle.station', string="Auto Station")
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id',
                                  store=True, readonly=True)
    count = fields.Integer(string='Count', compute='_compute_count', store=True, invisible=True)
    is_true = fields.Boolean(string="True")
    payment_transaction_id = fields.Many2many('payment.transaction', 'rental_order_id')
    partner_shipping_id = fields.Many2one(
        'res.partner', related='customer_name',
        string='Delivery Address')
    partner_invoice_id = fields.Many2one('res.partner', 'Invoicing Address',
                                         default=default_partner)
    return_date = fields.Datetime("Return Date")

    def _create_payment_transaction(self, vals):
        '''Similar to self.env['payment.transaction'].create(vals) but the values are filled with the
        current sales orders fields (e.g. the partner or the currency).
        :param vals: The values to create a new payment.transaction.
        :return: The newly created payment.transaction record.
        '''
        # Try to retrieve the acquirer. However, fallback to the token's acquirer.
        acquirer_id = int(vals.get('acquirer_id'))
        acquirer = False
        payment_token_id = vals.get('payment_token_id')
        partner = self.env['res.partner'].browse(vals.get('partner_id'))
        if payment_token_id:
            payment_token = self.env['payment.token'].sudo().browse(int(payment_token_id))
            # Check payment_token/acquirer matching or take the acquirer from token
            if acquirer_id:
                acquirer = self.env['payment.acquirer'].browse(acquirer_id)
                if payment_token and payment_token.acquirer_id != acquirer:
                    raise ValidationError(_('Invalid token found! Token acquirer %s != %s') % (
                        payment_token.acquirer_id.name, acquirer.name))
                if payment_token and payment_token.partner_id != partner:
                    raise ValidationError(_('Invalid token found! Token partner %s != %s') % (
                        payment_token.partner_id.name, partner.name))
            else:
                acquirer = payment_token.acquirer_id
        # Check an acquirer is there.
        if not acquirer_id and not acquirer:
            raise ValidationError(_('A payment acquirer is required to create a transaction.'))
        if not acquirer:
            acquirer = self.env['payment.acquirer'].browse(acquirer_id)
        # Check a journal is set on acquirer.
        if not acquirer.journal_id:
            raise ValidationError(_('A journal must be specified of the acquirer %s.' % acquirer.name))
        if not acquirer_id and acquirer:
            vals['acquirer_id'] = acquirer.id
        vals.update({
            'amount': vals.get('amount'),
            'currency_id': vals.get('currency_id'),
            'partner_id': vals.get('partner_id'),
            'rental_order_ids': [(6, 0, self.ids)],
        })
        transaction = self.env['payment.transaction'].create(vals)
        # Process directly if payment_token
        if transaction.payment_token_id:
            transaction.s2s_do_transaction()
        return transaction

    @api.depends('customer_name')
    def _compute_count(self):
        self.ensure_one()
        self.count = len(self.search([('customer_name', '=', self.customer_name.id)]))

    @api.depends('invoice_ids')
    def get_invoice_status(self):
        for order in self:
            self.invoice_status = order.invoice_ids.state

    @api.onchange('customer_name')
    def onchange_customer(self):
        self.account_payment_term = self.customer_name.property_payment_term_id

    @api.depends('move_ids')
    def _move_total(self):
        for order in self:
            order.move_count = len(order.move_ids)

    def action_view_order_moves(self):
        action = self.env.ref('aspl_vehicle_rental.action_rental_move_view_tree').read()[0]
        moves = self.mapped('move_ids')
        if len(moves) > 1:
            action['domain'] = [('id', 'in', moves.ids)]
        elif moves:
            action['views'] = [(self.env.ref('aspl_vehicle_rental.fleet_vehicle_move_form_id').id, 'form')]
            action['res_id'] = moves.id
        return action

    @api.depends('invoice_ids')
    def _invoice_total(self):
        for order in self:
            order.invoice_count = len(order.invoice_ids)

    def action_view_order_invoices(self):
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        invoices = self.mapped('invoice_ids')
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif invoices:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.id
        return action

    @api.depends('contract_ids')
    def _contract_total(self):
        for contract in self:
            contract.contract_count = len(contract.contract_ids)

    def action_view_order_contract(self):
        action = self.env.ref('aspl_vehicle_rental.action_rental_contract_view_tree').read()[0]
        contracts = self.mapped('contract_ids')
        if len(contracts) > 1:
            action['domain'] = [('id', 'in', contracts.ids)]
        elif contracts:
            action['views'] = [(self.env.ref('aspl_vehicle_rental.fleet_vehicle_contract_form').id, 'form')]
            action['res_id'] = contracts.id
        return action

    @api.onchange('customer_name')
    def customer_pricelist(self):
        values = {
            'pricelist_id': self.customer_name.property_product_pricelist and
                            self.customer_name.property_product_pricelist.id or False,
        }
        self.update(values)

    @api.depends('vehicle_order_lines_ids', 'customer_name')
    def _compute_amount(self):
        """
        Compute the total amounts of the RO.
        """
        for order in self:
            untaxed_amount = 0.0
            taxes = 0.0
            for line in order.vehicle_order_lines_ids:
                untaxed_amount += line.sub_total
                taxes += line.price_tax
            order.update({
                'untaxed_amount': order.currency_id.round(untaxed_amount),
                'taxes': order.currency_id.round(taxes),
                'total_amount': untaxed_amount + taxes + order.extra_charges,
            })

    @api.model
    def create(self, vals):
        list1 = []
        if vals.get('is_true'):
            for line in vals.get('vehicle_order_lines_ids'):
                if line[2] and line[0] != 0:
                    list1.append([0, False, line[2]])
                elif line[2] and line[0] == 0:
                    list1.append(line)
            vals.update({'vehicle_order_lines_ids': list1})
        sequence = self.env['ir.sequence'].next_by_code('vehicle_registration') or _('Vehicle Register')
        vals.update({'res_number': sequence})
        res = super(FleetVehicleOrder, self).create(vals)

        from_date, to_date = self.start_end_date_global(res.from_date, res.to_date)
        res.start_date = from_date
        res.end_date = to_date
        return res

    def book(self):
        self.state = "book"

    def confirm(self):
        if self:
            vehicle_order_id = []
            driver_list = []
            print("self.vehicle_order_lines_ids:--", self.vehicle_order_lines_ids)
            for each in self.vehicle_order_lines_ids:

                vehicle_order_id.append((0, 0, {'vehicle_id': each.vehicle_id.id,
                                                'current_odometer': each.vehicle_id.odometer}))
                driver_list.append((0, 0, {'vehicle_id': each.vehicle_id.id,
                                           'from_date': each.vehicle_order_id.from_date,
                                           'to_date': each.vehicle_order_id.to_date,
                                           'status': self.state,
                                           'order_id': self.id,
                                           'order_line_id': each.id
                                           }))
                driver_id = self.env['hr.employee'].search([('id', '=', each.driver_id.id)])
                driver_id.write({'driver_schedule_details_ids': driver_list})
                mail_content = _('<h3>Schedule For Your Route</h3><br/><b>Dear %s,</b> <br/> <br/>'
                                 '<tr><td>Your schedule has been fix <b> on Date-</b>%s <b> From </b>-%s <b>To </b>-%s, Please check customer details which is mention below and contact them As soon as Possible</td></tr><br/>'
                                 '<tr/><tr><td><b>Customer Details:-</b><td/></tr><br/>'
                                 '<td>Customer Name: </td>'
                                 '<td>%s<td/><br/>'
                                 '<td>Address: </td>'
                                 '<td>%s</td>'
                                 '<td> %s</td><br/>'
                                 '<td>City: </td>'
                                 '<td>%s</td><br/>'
                                 '<td>Contact: </td>'
                                 '<td>%s</td>'
                                 '<td>%s</td>'
                                 '<table/>') % \
                               (driver_id.name,
                                self.book_date,
                                self.from_date,
                                self.to_date,
                                self.customer_name.name,
                                self.customer_name.street,
                                self.customer_name.street2,
                                self.customer_name.city,
                                self.customer_name.mobile or '', self.customer_name.phone or '',
                                )
                main_content = {'subject': "Schedule for your Route",
                                'author_id': driver_id.env.user.partner_id.id,
                                'body_html': mail_content,
                                'email_to': driver_id.work_email,
                                }
                self.env['mail.mail'].create(main_content).send()
            move_id = self.env['fleet.vehicle.move'].create({'customer_id': self.customer_name.id,
                                                             'scheduled_date': self.from_date,
                                                             'from_date': self.from_date,
                                                             'to_date': self.to_date,
                                                             'source_document': self.res_number,
                                                             'vehicle_order_rel_id': self.id,
                                                             'vehicle_move_line_id': vehicle_order_id,
                                                             'station_id': self.station_id.id})
            self.state = "confirm"
            if self.is_agreement:
                vehicle_order_id = []
                for each in self.vehicle_order_lines_ids:
                    vehicle_order_id.append((0, 0, {'vehicle_id': each.vehicle_id.id or '',
                                                    'price_based': each.price_based or '',
                                                    'enter_days': each.enter_days or '',
                                                    'enter_kms': each.enter_kms or '',
                                                    'driver_id': each.driver_id.id or '',
                                                    'price': each.price or '',
                                                    'sub_total': each.sub_total or '',
                                                    'tax_id': [(6, 0, each.tax_id.ids)],
                                                    }))
                self.state = "confirm"
                view_id = self.env.ref('aspl_vehicle_rental.fleet_vehicle_contract_form')
                contract = self.env['fleet.vehicle.contract'].create({'partner_id': self.customer_name.id,
                                                                      'from_date': self.from_date,
                                                                      'to_date': self.to_date,
                                                                      'total_amount': self.total_amount,
                                                                      'rental_id': self.id,
                                                                      'vehicle_contract_lines_ids': vehicle_order_id,
                                                                      'cost_frequency': 'no',
                                                                      'contract_date': self.book_date,
                                                                      'account_payment_term': self.account_payment_term.id,
                                                                      'contractor_id': self.user_id.id,
                                                                      'origin': self.res_number,
                                                                      'cost': 12,
                                                                      'move_id': move_id.id,
                                                                      'station_id': self.station_id.id,
                                                                      'company_id': self.company_id.id,
                                                                      'name': 'New',
                                                                      })
                return {
                    'name': _('Fleet Contract'),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'fleet.vehicle.contract',
                    'res_id': contract.id,
                    'view_id': view_id.id,
                }
            self.state = "confirm"

    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_invoice_tree1').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.move_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def cancel(self):
        inv_obj = self.env['account.move']
        for contract in self.contract_ids:
            for cancel_policy in contract.cancel_policy_ids:
                if cancel_policy.from_date and cancel_policy.to_date:
                    if date.today() >= cancel_policy.from_date and date.today() <= cancel_policy.to_date:
                        invoice_browse = self.env['account.move'].search(
                            [('contract_id', '=', contract.id), ('type', '=', 'out_invoice')])
                        for each_invoice in invoice_browse:
                            if each_invoice.state == 'draft':
                                invoice_line_data = []
                                invoice_line_data.append((0, 0, {'vehicle_id': self.vehicle_name.id,
                                                                 'name': 'Cancel Policy ' + self.res_number,
                                                                 'account_id': self.customer_name.property_account_receivable_id.id,
                                                                 'price_unit': (
                                                                                           contract.total_amount * cancel_policy.policy_charged) / 100,
                                                                 'quantity': 1, }))
                                invoice = inv_obj.create({
                                    'name': self.res_number,
                                    'origin': self.res_number,
                                    'partner_id': self.customer_name.id,
                                    'type': 'out_invoice',
                                    'date_invoice': date.today(),
                                    'reference': False,
                                    'account_id': self.customer_name.property_account_receivable_id.id,
                                    'invoice_line_ids': invoice_line_data,
                                })

                            elif each_invoice.state == 'paid':
                                invoice_line_data = []
                                invoice_line_data.append((0, 0, {'vehicle_id': self.vehicle_name.id,
                                                                 'name': 'Cancel Policy ' + self.res_number,
                                                                 'account_id': self.customer_name.property_account_receivable_id.id,
                                                                 'price_unit': each_invoice.total_amount - ((
                                                                                                                        contract.total_amount * cancel_policy.policy_charged) / 100),
                                                                 'quantity': 1, }))
                                invoice = inv_obj.create({
                                    'name': self.res_number,
                                    'origin': self.res_number,
                                    'partner_id': self.customer_name.id,
                                    'type': 'in_refund',
                                    'date_invoice': date.today(),
                                    'reference': False,
                                    'account_id': self.customer_name.property_account_receivable_id.id,
                                    'invoice_line_ids': invoice_line_data,
                                })

                if not cancel_policy.to_date:
                    if date.today() >= cancel_policy.from_date:
                        invoice_browse = self.env['account.move'].search(
                            [('contract_id', '=', contract.id), ('type', '=', 'out_invoice')])
                        for each_invoice in invoice_browse:
                            if each_invoice.state == 'draft':
                                each_invoice.state = 'paid'
        self.state = "cancel"

    def send_vehicle_quote(self):
        '''
           This is Email for send quotation vehicle order inquiry
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = \
                ir_model_data.get_object_reference('aspl_vehicle_rental', 'email_template_vehicle_rental')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'fleet.vehicle.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'mark_so_as_sent': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def close(self):
        view_id = self.env.ref('aspl_vehicle_rental')
        return {
            'name': 'Fleet Service',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.fleet.service',
            'view_id': view_id.id,
            'target': 'new'
        }

    @api.model
    def start_end_date_global(self, start, end):
        tz = pytz.utc
        current_time = datetime.datetime.now(tz)
        hour_tz = int(str(current_time)[-5:][:2])
        min_tz = int(str(current_time)[-5:][3:])
        sign = str(current_time)[-6][:1]
        sdate = str(start)
        edate = str(end)

        if sign == '+':
            start_date = (datetime.datetime.strptime(sdate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                                             minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")
            end_date = (datetime.datetime.strptime(edate, '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                                           minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")

        if sign == '-':
            start_date = (datetime.datetime.strptime(sdate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                                             minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")
            end_date = (datetime.datetime.strptime(edate, '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                                           minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")
        return start_date, end_date

    @api.model
    def start_and_end_date_global(self, start, end):
        tz = pytz.timezone(self.env.user.tz) or 'UTC'
        current_time = datetime.datetime.now(tz)
        hour_tz = int(str(current_time)[-5:][:2])
        min_tz = int(str(current_time)[-5:][3:])
        sign = str(current_time)[-6][:1]
        sdate = str(start)
        edate = str(end)

        if sign == '-':
            start_date = (
                        datetime.datetime.strptime(sdate.split(".")[0], '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                                                         minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")
            end_date = (datetime.datetime.strptime(edate.split(".")[0], '%Y-%m-%d %H:%M:%S') + timedelta(hours=hour_tz,
                                                                                                         minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")

        if sign == '+':
            start_date = (
                        datetime.datetime.strptime(sdate.split(".")[0], '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                                                         minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")
            end_date = (datetime.datetime.strptime(edate.split(".")[0], '%Y-%m-%d %H:%M:%S') - timedelta(hours=hour_tz,
                                                                                                         minutes=min_tz)).strftime(
                "%Y-%m-%d %H:%M:%S")
        return start_date, end_date

    @api.model
    def get_booking_data(self, model_id, fuel_id):
        resourcelist = []
        eventlist = []
        name_list = []
        vehical_booking = self.env['fleet.vehicle.order'].search([('state','in',['confirm'])])
        for data in vehical_booking:
            if data.vehicle_order_lines_ids and data.from_date.date() >= date.today():
                for line in data.vehicle_order_lines_ids:
                    if str(
                            line.vehicle_id.model_id.brand_id.id) == model_id and line.vehicle_id.license_plate not in name_list and str(
                            line.vehicle_id.fuel_type.id) == fuel_id:
                        resourcelist.append({
                            'id': model_id,
                            'building': line.vehicle_id.model_id.name,
                            'title': line.vehicle_id.license_plate,
                            'type': line.vehicle_id.vehicle_type.id or False,
                            'vehicle_id': line.vehicle_id.id,
                        })
                        name_list.append(line.vehicle_id.license_plate)
                    if str(line.vehicle_id.model_id.brand_id.id) == model_id and str(
                            line.vehicle_id.fuel_type.id) == fuel_id:
                        if data.start_date and data.end_date:
                            start = str(
                                datetime.datetime.strptime(data.start_date, '%Y-%m-%d %H:%M:%S').date()) + 'T' + str(
                                datetime.datetime.strptime(data.start_date, '%Y-%m-%d %H:%M:%S').time())
                            end = str(
                                datetime.datetime.strptime(data.end_date, '%Y-%m-%d %H:%M:%S').date()) + 'T' + str(
                                datetime.datetime.strptime(data.end_date, '%Y-%m-%d %H:%M:%S').time())
                        else:
                            start = str(data.from_date.date()) + 'T' + str(data.from_date.time())
                            end = str(data.to_date.date()) + 'T' + str(data.to_date.time())
                        eventlist.append({
                            'id': line.id,
                            'line_id': line.id,
                            'resourceId': model_id,
                            'start': start,
                            'end': end,
                            'title': data.res_number,
                            'type': line.vehicle_id.vehicle_type.id or False,
                            'vehicle_id': line.vehicle_id.id,
                        })

        vehical_model = self.env['fleet.vehicle'].search([])
        for data in vehical_model:
            if str(data.model_id.brand_id.id) == model_id and \
                    data.license_plate not in name_list and str(data.fuel_type.id) == fuel_id:
                name_list.append(data.license_plate)
                resourcelist.append({
                    'id': data.id,
                    'building': data.model_id.name,
                    'title': data.license_plate,
                    'type': data.vehicle_type.id or False,
                    'vehicle_id': data.id,
                })
        if not resourcelist:
            eventlist = []
        return [resourcelist, eventlist]

    @api.model
    def remove_event(self, line_id):
        record_line_id = self.env['vehicle.order.line'].browse(int(line_id))
        if len(record_line_id.vehicle_order_id.vehicle_order_lines_ids.ids) == 1:
            record_line_id.vehicle_order_id.state = 'cancel'
        elif len(record_line_id.vehicle_order_id.vehicle_order_lines_ids.ids) > 1:
            record_line_id.unlink()


class VehicleOrderLine(models.Model):
    _name = "vehicle.order.line"
    _description = 'Vehicles Order Line'

    vehicle_order_id = fields.Many2one('fleet.vehicle.order', string="Vehicle order")
    vehicle_id = fields.Many2one('fleet.vehicle', string="Vehicle")
    price_based = fields.Selection([('per_day', 'Day'), ('per_km', 'KM')],
                                   default="per_day", string="Based On")
    tax_id = fields.Many2many("account.tax", 'vehicle_order_tax_rel', string='Tax')
    enter_kms = fields.Float(string='KM')
    enter_days = fields.Float(string='Days')
    price = fields.Monetary(string='Price')
    currency_id = fields.Many2one('res.currency', related='vehicle_id.company_id.currency_id',
                                  store=True, readonly=True)
    total = fields.Monetary(string='Total')
    driver_id = fields.Many2one('hr.employee', string='Select Driver')
    sub_total = fields.Monetary(string='Sub Total', compute='_get_subtotal', store=True)
    price_tax = fields.Float(compute='_get_subtotal', string='Taxes', store=True)
    price_total = fields.Monetary(compute='_get_subtotal', string='Total', store=True)
    name = fields.Char(string='Description')

    @api.onchange('vehicle_id')
    def get_line_value(self):
        if self.vehicle_order_id.from_date and self.vehicle_order_id.to_date:
            date_from = datetime.datetime.strptime(str(self.vehicle_order_id.from_date), '%Y-%m-%d %H:%M:%S')
            date_to = datetime.datetime.strptime(str(self.vehicle_order_id.to_date), '%Y-%m-%d %H:%M:%S')
            difference = relativedelta.relativedelta(date_from, date_to)
            self.name = self.vehicle_id.model_id.name
            self.enter_days = abs(difference.days)
            self.price = self.vehicle_id.rate_as_per_day
        else:
            raise Warning(_('Please Select From date Or to date!!!'))

    @api.onchange('price_based')
    def get_price_value(self):

        if self.price_based == 'per_day':
            self.price = self.vehicle_id.rate_as_per_day
        else:
            self.enter_days = ''
            self.price = self.vehicle_id.rate_as_per_km

    @api.depends('enter_kms', 'price', 'tax_id')
    def _get_subtotal(self):
        for line in self:
            qty = 0;
            if line.enter_days > 0:
                qty = line.enter_days
            if line.enter_kms > 0:
                qty = line.enter_kms
            taxes = line.tax_id.compute_all(qty, line.vehicle_order_id.currency_id, line.price)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'sub_total': taxes['total_excluded'],
            })


class WizardFleetService(models.TransientModel):
    _name = 'wizard.fleet.service'
    _description = 'Fleet Service'

    is_damaged = fields.Boolean(string='Is Damaged')
    service_location_id = fields.Many2one('fleet.vehicle.location', string='Service Location')
    vehicle_location_id = fields.Many2one('fleet.vehicle.location', string='Vehicle Location')
 
    def confirm_service(self):
        self.state = "confirm"


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    driver_schedule_details_ids = fields.One2many('driver.schedule.line', 'employee_id',
                                                  string='Driver')

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        vehicle_id = {}
        if self._context.get('from_vehicle_order'):
            from_date = self._context.get('from_date')
            to_date = self._context.get('to_date')
            if from_date and to_date:
                self.env.cr.execute("""select id from hr_employee  where id NOT IN
                                       (select dsl.employee_id  from hr_employee hr,fleet_vehicle_order vo,
                                       driver_schedule_line dsl where vo.state NOT IN('cancel','close','draft')
                                       AND hr.id=dsl.employee_id AND vo.id = dsl.order_id AND (((dsl.from_date BETWEEN %s AND %s)
                                       OR (dsl.to_date BETWEEN %s AND %s))OR((%s BETWEEN dsl.from_date AND dsl.to_date)
                                       OR(%s BETWEEN dsl.from_date AND dsl.to_date))))""",
                                    (from_date, to_date, from_date, to_date, from_date, to_date));
                hr_emp = self.env.cr.dictfetchall()
                emp_list = [hr_emp['id'] for hr_emp in hr_emp]
                return self.browse(emp_list).name_get()
            else:
                raise Warning('Please select From Date and To date and Vehicle Type First!!!')
        else:
            return super(HrEmployee, self).name_search(name, args=args, operator=operator, limit=limit)


class AccountMove(models.Model):
    _inherit = "account.move"

    rental_order_id = fields.Many2one('fleet.vehicle.order', string='invoice ref')
    interval_type = fields.Selection([('days', 'Day'), ('weeks', 'Week'), ('months', 'Month')],
                                     string="Interval Type")
    interval_number = fields.Integer(string='Interval Number', readonly=1)
    is_recuuring = fields.Boolean(string='Recurring Invoice', default=False)
    extra_charges = fields.Float(string='Extra Charges')
    contract_id = fields.Many2one('fleet.vehicle.contract', string='Contract')

    @api.model
    def create(self, vals):
        return super(AccountMove, self).create(vals)




class AccountMnvoiceLine(models.Model):
    _inherit = "account.move.line"

    vehicle_id = fields.Many2one("fleet.vehicle", string="Vehicle")


class DriverScheduleLine(models.Model):
    _name = "driver.schedule.line"
    _description = 'Driver Schedule Line'

    employee_id = fields.Many2one('hr.employee', string='Order line')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle Name')
    from_date = fields.Datetime(string='From Date')
    to_date = fields.Datetime(string='To Date')
    order_id = fields.Integer(string='Order Id')
    status = fields.Char(compute='order_status', string='Status')
    order_line_id = fields.Many2one('vehicle.order.line', string='Vehicle Order Line')

    @api.depends('status')
    def order_status(self):
        for each in self:
            if self.env['fleet.vehicle.order'].browse(each.order_id):
                each.status = self.env['fleet.vehicle.order'].browse(each.order_id).state
            else:
                each.status = 'Record Deleted'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
