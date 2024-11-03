# -*- coding: utf-8 -*-
#################################################################################
# Author : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import fields, api, models, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError, Warning


class FleetVehicleContract(models.Model):
    _name = 'fleet.vehicle.contract'
    _description = 'Vehicle Rental Contract'

    name = fields.Char(readonly=True, default='New')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    driver_id = fields.Many2one('hr.employee', string='Driver')
    rental_id = fields.Many2one('fleet.vehicle.order', string='Rental Order Id')
    contract_date = fields.Date(string='Contract Date', )
    contractor_id = fields.Many2one('res.users', string='Contractor Name')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    account_payment_term = fields.Many2one('account.payment.term', string="Payment Term", require=True)
    security_deposit = fields.Monetary(string='Security Deposit')
    damage_charge = fields.Float(string='Damage Charge')
    additional_charges = fields.Float(string='Additional Charges')
    subtotal = fields.Monetary(string='Sub Total', readonly=True)
    taxes = fields.Monetary(string='Taxes', compute='_compute_amount', readonly=True)
    untaxed_amount = fields.Monetary(string='Untaxed Amount', compute='_compute_amount', )
    extra_charges = fields.Monetary(string='Extra Charges',default=0.0 )
    invoice_ids = fields.One2many('account.move', 'cotract_order_id', string="Invoice Id ")

    signature = fields.Binary(string='Signature')
    button_name = fields.Char('Button Name')
    signature_contractor = fields.Binary(string='Contractor Signature')
    signature_customer = fields.Binary(string='Customer Signature')
    terms_condition = fields.Text(string='Terms and Condition')
    vehicle_contract_lines_ids = fields.One2many('vehicle.contract.lines', 'vehicle_contract_id', string='Order Line')
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")
    total_amount = fields.Float(string='Total Amount')
    total = fields.Float(string='Total', compute='_compute_total')
    cost_generated = fields.Float(string='Recurring Cost',
                                  help="Costs paid at regular intervals, depending on the cost frequency")
    cost_frequency = fields.Selection([('no', 'No'), ('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'),
                                       ('yearly', 'Yearly')], string="Recurring Cost Frequency", required=True)
    state = fields.Selection([('futur', 'Incoming'), ('open', 'In Progress'),
                              ('expired', 'Expired'), ('diesoon', 'Expiring Soon'),
                              ('closed', 'Closed')], 'Status', default='open', readonly=True, )
    cost = fields.Float(string="Rent Cost", help="This fields is to determine the cost of rent", required=True)
    account_type = fields.Many2one('account.account', 'Account',
                                   default=lambda self: self.env['account.account'].search([('id', '=', 17)]))
    recurring_line = fields.One2many('fleet.rental.line', 'rental_number', readonly=True)
    attachment_ids = fields.Many2many('ir.attachment', 'vehicle_rent_ir_attachments_rel', 'rental_id', 'attachment_id',
                                      string="Attachments")
    sum_cost = fields.Float(compute='_compute_sum_cost', string='Indicative Costs Total')
    auto_generated = fields.Boolean('Automatically Generated', readonly=True)
    generated_cost_ids = fields.One2many('fleet.rental.line', 'rental_number', string='Generated Costs')
    invoice_count = fields.Integer(compute='_invoice_count', string='# Invoice', copy=False)
    first_payment = fields.Float(string='First Payment', compute='_compute_amount')
    first_invoice_created = fields.Boolean(string="First Invoice Created", default=False)
    origin = fields.Char(string="Order Reference")
    move_id = fields.Many2one('fleet.vehicle.move', string='Vehicle Move')
    document_ids = fields.One2many('customer.document', 'contract_id', string='Contract')
    station_id = fields.Many2one('fleet.vehicle.station', string='Auto Station')
    company_id = fields.Many2one('res.company', string='Company')
    # currency_id = fields.Many2one('res.currency', related='invoice_ids.currency_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True, readonly=True)
    cancel_policy_ids = fields.One2many('rental.policy', 'contract_id', string='Cancel Policy')
    number_of_slot = fields.Integer(string='Number of Slot')

    def generate_policy(self):
        if not self.cancel_policy_ids:
            if self.number_of_slot != 0:
                number_of_days = self.from_date - self.contract_date
                cancel_policy_list = []
                if number_of_days.days >= (self.number_of_slot * 2):
                    day_per_slot = int(number_of_days.days/self.number_of_slot - 1)
                    day = 0
                    for i in range(self.number_of_slot - 1):
                        cancel_policy_list.append((0, 0, {'from_date': self.contract_date + timedelta(day),
                                                          'to_date': self.contract_date + timedelta(day_per_slot + day)}))

                        day += (day_per_slot + 1)
                    cancel_policy_list.append((0, 0, {'from_date': self.contract_date + timedelta(day),
                                                      'to_date': self.from_date - timedelta(days=2)}))
                    cancel_policy_list.append((0, 0, {'from_date': self.from_date - timedelta(days=1),
                                                      'policy_charged': 100}))
                    self.cancel_policy_ids = cancel_policy_list
                else:
                    raise Warning(_('Please enter the sufficient Number of Slot'))

    def write(self, vals):
        if 'button_name' in vals.keys():
            if vals['button_name'] == 'signature_contractor':
                vals['signature_contractor'] = vals['signature']
            elif vals['button_name'] == 'signature_customer':
                vals['signature_customer'] = vals['signature']
        return super(FleetVehicleContract, self).write(vals)

    @api.onchange('security_deposit')
    def add_security_deposite(self):
        if self.security_deposit:
            # vehicle_list = []
            # deposit_updated = False
            if self.vehicle_contract_lines_ids:
                line_id = self.vehicle_contract_lines_ids.filtered(lambda x: x.desciption == 'Deposite')
                if line_id:
                    line_id.price = self.security_deposit
                else:
                    self.write({
                        'vehicle_contract_lines_ids': [(0, 0, {
                            'desciption': 'Deposite',
                            'enter_days': 1.0,
                            'price': self.security_deposit}
                                                        )]
                    })

    @api.depends('vehicle_contract_lines_ids', 'security_deposit')
    def _compute_amount(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            untaxed_amount = taxes = total_amount = order.security_deposit = 0.0
            for line in order.vehicle_contract_lines_ids:
                untaxed_amount += line.sub_total
                taxes += line.price_tax
                total_amount += line.sub_total + line.price_tax
            order.update({
                'untaxed_amount': untaxed_amount,
                'taxes': taxes,
                'total_amount': untaxed_amount + taxes + order.security_deposit,
                'first_payment': untaxed_amount + taxes + order.security_deposit,
            })

    @api.depends('recurring_line.recurring_amount')
    def _compute_sum_cost(self):
        for contract in self:
            contract.sum_cost = sum(contract.recurring_line.mapped('recurring_amount'))

    def _invoice_count(self):
        invoice_ids = self.env['account.move'].search([('cotract_order_id', '=', self.id)])
        self.invoice_count = len(invoice_ids)

    @api.model
    def create(self, vals):
        sequence_no = self.env['ir.sequence'].next_by_code('vehicle_contract') or _('Vehicle Contract')
        vals.update({'name': sequence_no})
        return super(FleetVehicleContract, self).create(vals)

    @api.depends('vehicle_contract_lines_ids', 'damage_charge')
    def _compute_total(self):
        self.total = self.total_amount + self.damage_charge

    def contract_close(self):
        invoice_ids = self.env['account.move'].search([('cotract_order_id', '=', self.id)])
        fleet_order_ids = self.env['fleet.vehicle.order'].search([('res_number', '=', self.origin)])
        is_paid = 0
        for each in invoice_ids:
            if each.state != 'paid':
                is_paid = 1
                break
        if is_paid == 0:
            self.state = 'closed'
            fleet_order_ids.state = 'close'
        else:
            raise UserError("Please Check invoices There are Some Invoices are pending")

    def contract_open(self):
        for record in self:
            record.state = 'open'

    def act_renew_contract(self):
        vehicle_list = []
        for vehicle_line in self.vehicle_contract_lines_ids:
            vehicle_list.append(
                (0, 0, {'vehicle_id': vehicle_line.vehicle_id.id, 'price_based': vehicle_line.price_based,
                        'enter_days': vehicle_line.enter_days, 'price': vehicle_line.price,
                        'enter_kms': vehicle_line.enter_kms,
                        }))
        assert len(
            self.ids) == 1, "This operation should only be done for 1 single contract at a time, as it it suppose to open a window as result"
        for element in self:
            # compute end date
            startdate = fields.Date.from_string(element.from_date)
            enddate = fields.Date.from_string(element.to_date)
            diffdate = (enddate - startdate)
            default = {
                'date': fields.Date.context_today(self),
                'from_date': fields.Date.to_string(fields.Date.from_string(element.to_date) + relativedelta(days=1)),
                'to_date': fields.Date.to_string(enddate + diffdate),
                'cost_generated': self.cost_generated,
                'vehicle_contract_lines_ids': vehicle_list,
            }
            newid = element.copy(default).id
        return {
            'name': _("Renew Contract"),
            'view_mode': 'form',
            'view_id': self.env.ref('aspl_vehicle_rental.fleet_vehicle_contract_form').id,
            'res_model': 'fleet.vehicle.contract',
            'type': 'ir.actions.act_window',
            'res_id': newid,
        }

    def send_vehicle_contract(self):
        '''
           This is Email for send contract Detail
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = \
            ir_model_data.get_object_reference('aspl_vehicle_rental', 'email_template_vehicle_contract')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'fleet.vehicle.contract',
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

    def send_email_for_firstpayment(self, inv_id, contracts):
        '''
           Send email for payment.
        '''
        mail_content = _(
            '<h3>First Payment!</h3><br/>Hi %s, <br/> This is to notify that You have to pay amount as per mention below.<br/><br/>'
            'Please find the details below:<br/><br/>'
            '<table><tr><td>Reference Number<td/><td> %s<td/><tr/>'
            '<tr><td>Date<td/><td> %s <td/><tr/><tr><td>Amount <td/><td> %s<td/><tr/><table/>') % \
                       (contracts.partner_id.name, inv_id.ref, date.today(), inv_id.amount_total)
        main_content = {
            'subject': _('You First Payment For: %s') % inv_id.ref,
            'author_id': contracts.env.user.partner_id.id,
            'body_html': mail_content,
            'email_to': contracts.partner_id.email,
        }
        self.env['mail.mail'].create(main_content).send()

    def notification_email_for_expire_contract(self, contracts):
        mail_content = _('<h3>Expiration Of Rental Contract</h3><br/>Dear %s, <br/>'
                         'Our record indicate that your rental contract <b>%s,</b> expire soon,<br/>'
                         'If you want to renew this contract Then contact to our agency before last date of contract.'
                         '<br/><br/>'
                         '<br/><br/>'
                         '<table><tr><td>Contract Ref<td/><td>%s<td/><tr/>'
                         '<tr/><tr><td>Responsible Person <td/><td> %s - %s<td/><tr/><table/>') % \
                       (contracts.partner_id.name, contracts.name,
                        contracts.name,
                        contracts.contractor_id.name,
                        contracts.contractor_id.mobile
                        )
        main_content = {'subject': "Expiration Of Rental Contract!",
                        'author_id': contracts.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': contracts.partner_id.email,
                       }
        self.env['mail.mail'].create(main_content).send()

    def send_email_for_recurring_invoice(self, inv_id, contracts):
        mail_content = _('<h3>Reminder Recurrent Payment!</h3><br/>Hi %s, <br/> This is to remind you that the '
                         'recurrent payment for the ''rental contract has to be done.'
                         'Please make the payment at the earliest.''<br/><br/>'
                         'Please find the details below:<br/><br/>'
                         '<table><tr><td>Contract Ref<td/><td>%s<td/><tr/>'
                         '<tr/><tr><td>Amount <td/><td> %s<td/><tr/>'
                         '<tr/><tr><td>Due Date <td/><td> %s<td/><tr/>'
                         '<tr/><tr><td>Responsible Person <td/><td> %s, %s<td/><tr/><table/>') % \
                        (contracts.partner_id.name, contracts.name, inv_id.amount_total, date.today(),
                        inv_id.user_id.name,
                        inv_id.user_id.mobile)
        main_content = {'subject': "Reminder Recurrent Payment!",
                        'author_id': contracts.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': contracts.partner_id.email,
                       }
        self.env['mail.mail'].create(main_content).send()

    def create_invoice(self):
        # if self.signature_contractor and self.signature_customer:
        inv_obj = self.env['account.move']
        journal_id = self.env['account.move'].default_get(['journal_id'])['journal_id']

        # journal = self.env['account.journal'].browse(journal_id)
        for contracts in self:
            inv_line_data = []
            if contracts.first_invoice_created == False:
                contracts.first_invoice_created = True
                supplier = contracts.partner_id
                for each_vehicle in contracts.vehicle_contract_lines_ids:
                    if each_vehicle.price_based == 'per_day':
                        total_qty = each_vehicle.enter_days
                    else:
                        total_qty = each_vehicle.enter_kms
                    account_id = self.env['account.account'].search([('code', 'like', 'RO100100')])
                    inv_line_data.append((0, 0, {'name': each_vehicle.vehicle_id.name or 'Deposite',
                                     'vehicle_id': each_vehicle.vehicle_id.id or False,
                                     'account_id': account_id.id,
                                     'price_unit': each_vehicle.price or 0.0,
                                     'quantity': total_qty or 1.0,
                                     }))
                    if contracts.extra_charges:
                        inv_line_data.append((0, 0, {'name': 'Extra Charges',
                                                     'vehicle_id': each_vehicle.vehicle_id.id or False,
                                                     'account_id': account_id.id,
                                                     'price_unit': contracts.extra_charges or 0.0,
                                                     'quantity': 1,
                                                     }))

                inv_data = {
                    'move_type': 'out_invoice',
                    'currency_id': contracts.company_id.currency_id.id,
                    'journal_id': journal_id,
                    'company_id': contracts.company_id.id,
                    'partner_id': supplier.id,
                    'account_id': supplier.property_account_payable_id.id,
                    'invoice_date_due': self.to_date,
                    'cotract_order_id': contracts.id,
                    'contract_id': self.id,
                    'rental_order_id': self.rental_id.id,
                    'ref': self.name,
                    'invoice_line_ids': inv_line_data,
                    'l10n_in_gst_treatment': supplier.l10n_in_gst_treatment or 'regular',
                }
                inv_id = inv_obj.create(inv_data)
                inv_id.action_post()


    @api.model
    def scheduler_manage_invoice(self):
        journal_id = self.env['account.move'].default_get(['journal_id'])['journal_id']
        inv_obj = self.env['account.move']
        inv_line_obj = self.env['account.move.line']
        recurring_obj = self.env['fleet.rental.line']
        account_id = self.env['account.account'].search([('code', 'like', 'RO100100')])
        inv_line_data = {}
        _inv_line_data = {}
        today = date.today()
        for contracts in self.search([]):
            start_date = datetime.strptime(str(contracts.from_date), '%Y-%m-%d').date()
            end_date = datetime.strptime(str(contracts.to_date), '%Y-%m-%d').date()
            if end_date >= date.today():
                is_recurring = 0
                if contracts.cost_frequency == 'daily':
                    is_recurring = 1
                elif contracts.cost_frequency == 'weekly':
                    week_days = (date.today() - start_date).days
                    if week_days % 7 == 0 and week_days != 0:
                        is_recurring = 1
                elif contracts.cost_frequency == 'monthly':
                    if start_date.day == date.today().day and start_date != date.today():
                        is_recurring = 1
                elif contracts.cost_frequency == 'yearly':
                    if start_date.day == date.today().day and start_date.month == date.today().month and \
                            start_date != date.today():
                        is_recurring = 1
                if is_recurring == 1 and contracts.cost_frequency != "no" and contracts.state != "expire" and contracts.state != "close" and contracts.state != 'futur' and contracts.first_invoice_created == True:
                    supplier = contracts.partner_id
                    inv_data = {
                        'name': supplier.name,
                        'account_id': supplier.property_account_payable_id.id,
                        'partner_id': supplier.id,
                        'currency_id': contracts.account_type.company_id.currency_id.id,
                        'journal_id': journal_id,
                        'invoice_origin': contracts.name,
                        'company_id': contracts.account_type.company_id.id,
                        'invoice_date_due': contracts.to_date,
                    }
                    inv_id = inv_obj.create(inv_data)
                    line_len = len(contracts.vehicle_contract_lines_ids)
                    for each_vehicle in contracts.vehicle_contract_lines_ids:
                        inv_line_data = {'product_id': '',
                                         'name': each_vehicle.vehicle_id.name or '',
                                         'vehicle_id': each_vehicle.vehicle_id.id or '',
                                         'account_id': account_id.id or '',
                                         'price_unit': (contracts.cost_generated) / line_len or '',
                                         'quantity': 1 or '',
                                         'invoice_id': inv_id.id or '',
                                         }
                        if inv_line_data:
                            inv_line_obj.create(inv_line_data)
                    inv_id.action_post()
                    payment_id = self.env['account.payment'].create({'invoice_ids': [(4, inv_id.id)],
                                                                     'payment_type': 'inbound',
                                                                     'partner_type': 'supplier',
                                                                     'partner_id': supplier.id,
                                                                     'amount': inv_id.amount_total,
                                                                     'journal_id': journal_id,
                                                                     'payment_date': date.today(),
                                                                     'payment_method_id': '1',
                                                                     'account_id': supplier.property_account_payable_id.id or False,
                                                                     'communication': inv_id.number})
                    if payment_id:
                        payment_id.post()
                    recurring_data = {
                        'name': 'demo',
                        'date_today': today,
                        'rental_number': contracts.id,
                        'recurring_amount': contracts.cost_generated,
                        'invoice_number': inv_id.id,
                        'invoice_ref': inv_id.id,
                    }
                    recurring_obj.create(recurring_data)
                    self.send_email_for_recurring_invoice(inv_id, contracts)
                else:
                    if contracts.first_invoice_created == False and contracts.state != 'futur' and contracts.state != 'expired':
                        contracts.first_invoice_created = True
                        supplier = contracts.partner_id
                        inv_data = {
                            'name': supplier.name,
                            'account_id': supplier.property_account_payable_id.id,
                            'partner_id': supplier.id,
                            'currency_id': contracts.account_type.company_id.currency_id.id,
                            'journal_id': journal_id,
                            'invoice_origin': contracts.name,
                            'company_id': contracts.account_type.company_id.id,
                            'invoice_date_due': self.to_date,
                        }
                        inv_id = inv_obj.create(inv_data)
                        for each_vehicle in contracts.vehicle_contract_lines_ids:
                            if each_vehicle.price_based == 'per_day':
                                total_qty = each_vehicle.enter_days
                            else:
                                total_qty = each_vehicle.enter_kms
                            inv_line_data = {'product_id': '',
                                             'name': each_vehicle.vehicle_id.name or '',
                                             'vehicle_id': each_vehicle.vehicle_id.id or '',
                                             'account_id': supplier.property_account_payable_id.id or False,
                                             'price_unit': each_vehicle.price or '',
                                             'quantity': total_qty or '',
                                             'invoice_line_tax_ids': [(6, 0, each_vehicle.tax_id.ids)],
                                             'invoice_id': inv_id.id or '', }
                            if inv_line_data:
                                inv_line_obj.create(inv_line_data)
                        recurring_data = {
                            'name': 'demo',
                            'date_today': today,
                            'rental_number': contracts.id,
                            'recurring_amount': contracts.first_payment,
                            'invoice_number': inv_id.id,
                            'invoice_ref': inv_id.id,
                        }
                        recurring_obj.create(recurring_data)
                        self.send_email_for_firstpayment(inv_id, contracts)

    @api.model
    def shedule_manage_contract(self):
        date_today = fields.Date.from_string(fields.Date.today())
        in_fifteen_days = fields.Date.to_string(date_today + relativedelta(days=+15))
        nearly_expired_contracts = self.search([('state', '=', 'open'), ('to_date', '<', in_fifteen_days)])
        res = {}
        for contract in nearly_expired_contracts:
            if contract.partner_id.id in res:
                res[contract.partner_id.id] += 1
            else:
                res[contract.partner_id.id] = 1
            contract.notification_email_for_expire_contract(contract)

        nearly_expired_contracts.write({'state': 'diesoon'})

        expired_contracts = self.search([('state', '!=', 'expired'), ('to_date', '<', fields.Date.today())])
        expired_contracts.write({'state': 'expired'})

        futur_contracts = self.search(
            [('state', 'not in', ['futur', 'closed']), ('from_date', '>', fields.Date.today())])
        futur_contracts.write({'state': 'futur'})

        now_running_contracts = self.search([('state', '=', 'futur'), ('from_date', '<=', fields.Date.today())])
        now_running_contracts.write({'state': 'open'})

    @api.model
    def run_scheduler(self):
        self.shedule_manage_contract()
        self.scheduler_manage_invoice()

    def action_view_contract_invoices(self):
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        invoices = self.mapped('invoice_ids')
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif invoices:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.id
        return action


class VehicleConLines(models.Model):
    _name = 'vehicle.contract.lines'
    _description = 'Vehicle Retnal Contract Lines'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle Name')
    price_based = fields.Selection([('per_day', 'Day'), ('per_km', 'K/M')], default='per_day', string='Based On')
    sub_total = fields.Monetary(string='Sub Total', compute='_get_subtotal', store=True)
    enter_kms = fields.Float(string='KM')
    enter_days = fields.Float(string='Days')
    driver_id = fields.Many2one('hr.employee', string="Driver")
    price = fields.Monetary(string='Price')
    total = fields.Monetary(string='Total')
    vehicle_contract_id = fields.Many2one('fleet.vehicle.contract', string='Contract')
    odometer_unit = fields.Float(string='Odometer Unit', require=True)
    tax_id = fields.Many2many("account.tax", 'vehicle_contract_tax_rel', string='Tax')
    sub_total = fields.Monetary(string='Sub Total', compute='_get_subtotal', store=True)
    price_tax = fields.Float(compute='_get_subtotal', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_get_subtotal', string='Total ', readonly=True, store=True)
    desciption = fields.Char(string='Description')
    currency_id = fields.Many2one('res.currency', related='vehicle_contract_id.currency_id',
                                  string='Currency')

    @api.depends('enter_kms', 'enter_days', 'price', 'tax_id')
    def _get_subtotal(self):
        for line in self:
            qty = 0;
            if line.enter_days > 0:
                qty = line.enter_days
            if line.enter_kms > 0:
                qty = line.enter_kms
            taxes = line.tax_id.compute_all(qty, line.vehicle_contract_id.currency_id, line.price)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'sub_total': taxes['total_excluded'],
            })


class FleetRentalLine(models.Model):
    _name = 'fleet.rental.line'
    _description = 'Rental Lines'

    date_today = fields.Date('Date')
    recurring_amount = fields.Monetary('Amount')
    rental_number = fields.Many2one('fleet.vehicle.contract', string='Rental Number')
    payment_info = fields.Char(compute='paid_info', string='Payment Stage', default='draft')
    auto_generated = fields.Boolean('Automatically Generated', readonly=True)
    invoice_number = fields.Integer(string='Invoice ID')
    invoice_ref = fields.Many2one('account.move', string='Invoice Ref')
    currency_id = fields.Many2one('res.currency', related='rental_number.currency_id',
                                  string='Currency')

    @api.depends('payment_info')
    def paid_info(self):
        for each in self:
            if self.env['account.move'].browse(each.invoice_number):
                each.payment_info = self.env['account.move'].browse(each.invoice_number).state
            else:
                each.payment_info = 'Record Deleted'


class AccountMove(models.Model):
    _inherit = "account.move"

    cotract_order_id = fields.Many2one('fleet.vehicle.contract', string='invoice ref')
    account_id = fields.Many2one('account.account',string='Account')


class CustomerDocument(models.Model):
    _name = 'customer.document'

    name = fields.Binary(string='Document')
    id_number = fields.Char(string='ID Number')
    contract_id = fields.Many2one('fleet.vehicle.contract', string='Conrtract')


class RentalPolicy(models.Model):
    _name = 'rental.policy'

    contract_id = fields.Many2one('fleet.vehicle.contract', string='Contract')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    policy_charged = fields.Float(string='Charge(In Percentage)')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
