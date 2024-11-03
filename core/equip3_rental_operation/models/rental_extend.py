# from dataclasses import field
import datetime

from dateutil.relativedelta import relativedelta

from odoo import fields, models, _, api
from odoo.exceptions import ValidationError
from datetime import date


class RentalOrder(models.Model):
    _inherit = "rental.order"

    final_end_date = fields.Datetime(string='Final End Date', tracking=True)
    rental_extend_id = fields.One2many('rental.extend', 'rental_id', string='Rental Extend Orders', copy=False)
    extend_invoice_count = fields.Integer(
        string='# of Invoices',
        compute='_get_rental_extend_invoice',
        readonly=True
    )
    extend_invoice_ids = fields.Many2many(
        comodel_name="account.move",
        string='Invoices',
        compute='_get_rental_extend_invoice',
        readonly=True
    )

    # @api.constrains('start_date', 'final_end_date', 'rental_line')
    # def _check_rental_buffer(self):
    #     for record in self:
    #         rental_start_date = record.start_date
    #         rental_end_date = record.final_end_date
    #         rental_lines = record.rental_line
    #         rental_id = record.id
    #
    #         for line in rental_lines:
    #             lot_id = line.lot_id.id
    #             product_data = self.env['rental.order.line'].search([('lot_id', '=', lot_id),
    #                          '&', ('buffer_end_time', '>', rental_start_date), ('buffer_start_time', '<', rental_end_date), ('rental_id', '!=', rental_id)])
    #             if product_data:
    #                 raise ValidationError(
    #                     'This product has already been rented in selected date. \n '
    #                     'Please change the start date and end date for the rent or close the already created rental for \n '
    #                     'this product to save rental order.')

    @api.depends('state')
    def _get_rental_extend_invoice(self):
        for rental in self:
            invoice = self.env['account.move'].search([('rental_extend_id', 'in', rental.rental_extend_id.ids)])
            rental.update({
                'extend_invoice_count': len(set(invoice)),
                'extend_invoice_ids': invoice.ids,
            })
    
    @api.depends('state')
    def _get_invoiced(self):
        for rental in self:
            invoice = self.env['account.move'].search([('rental_id', '=', rental.id), ('rental_extend_id', '=', False)])
            rental.update({
                'invoice_count': len(set(invoice)),
                'invoice_ids': invoice.ids,
            })

    def action_view_invoice_rental_extend(self):
        invoice_ids = self.mapped('extend_invoice_ids')
        views = [(self.env.ref('account.view_invoice_tree').id, 'tree'),
                 (self.env.ref('account.view_move_form').id, 'form')]

        result = {
            'name': 'Invoices',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'view_id': False,
            'views': views,
            'res_model': 'account.move',
        }
        if len(invoice_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % invoice_ids.ids
        elif len(invoice_ids) == 1:
            result['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            result['res_id'] = invoice_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result


class RentalRenew(models.TransientModel):
    _inherit = 'rental.renew'

    def get_rental_initial_and_type(self):
        rental = self.env['rental.order'].browse(self._context.get('active_id'))
        if rental:
            return str(rental.rental_initial) + " " + rental.rental_initial_type

    @api.onchange('rental_initial_type', 'rental_initial')
    def _onchange_rental_initial_type(self):
        rental = self.env['rental.order'].browse(self._context.get('active_id'))
        if rental:
            if rental.final_end_date:
                self.date = rental.final_end_date
            else:
                self.date = rental.end_date

    date = fields.Datetime(string="New Extended Date")
    rental_initial_and_type = fields.Char(string="Initial Terms", default=get_rental_initial_and_type)
    extend_term_type = fields.Selection(
        selection=[
            ('hours', 'Hours'),
            ('days', 'Days'),
            ('weeks', 'Weeks'), 
            ('months', 'Months'),
            ('years', 'Years')
        ],
        default="hours",
        string='Extend Term Type'
    )
    extend_term = fields.Integer(string="Extend Term", default=1)
    is_recurring_invoice = fields.Boolean("Recurring Invoice", tracking=True)
    rental_bill_freq = fields.Integer(string='Rental Bill Frequency',default=1, tracking=True)
    rental_bill_freq_type = fields.Selection(
        string="Rental Bill Frequrency Type",
        selection=[
            ('hours', 'Hours'),
            ('days', 'Days'),
            ('weeks', 'Weeks'),
            ('months', 'Months'),
            ('years', 'Years')
        ],
        required=False,
        default="hours",
        copy=False,
        tracking=True
    )    

    @api.onchange(
        "extend_term",
        "extend_term_type",
        "is_recurring_invoice",
        "rental_bill_freq",
        "rental_bill_freq_type",
    )
    def _check_rental_bill_freq_and_extend_term(self):
        for record in self:
            validation_type = False
            if record.is_recurring_invoice:
                if (
                    record.extend_term_type == "hours"
                    and record.rental_bill_freq_type != "hours"
                ):
                    validation_type = True
                elif (
                    record.extend_term_type == "days"
                    and record.rental_bill_freq_type not in ["hours", "days"]
                ):
                    validation_type = True
                elif (
                    record.extend_term_type == "weeks"
                    and record.rental_bill_freq_type not in ["hours", "days", "weeks"]
                ):
                    validation_type = True
                elif (
                    record.extend_term_type == "months"
                    and record.rental_bill_freq_type
                    not in ["hours", "days", "weeks", "months"]
                ):
                    validation_type = True
                
                elif (
                    record.extend_term_type == "years"
                    and record.rental_bill_freq_type
                    not in ["hours", "days", "weeks", "months", "years"]
                ):
                    validation_type = True
                
                if validation_type:
                    raise ValidationError("Rental bill frequency time unit can't be more than initial terms time unit.")

    @api.constrains('extend_term')
    def _check_extend_term(self):
        for record in self:
            if record.extend_term <= 0.00:
                raise ValidationError("Extend Term must be entered")
            if not record.extend_term_type:
                raise ValidationError("Extend Term Type must be selected")

    @api.onchange('extend_term', 'extend_term_type')
    def _onchange_extend_term(self):
        rental = self.env['rental.order'].browse(self._context.get('active_id'))
        prv_final_end_date = rental.end_date
        if rental.final_end_date:
            prv_final_end_date = rental.final_end_date

        for rental_extend in self:
            internal = rental_extend.extend_term or 0
            if rental_extend.extend_term_type == 'days' and prv_final_end_date:
                rental_extend.date = prv_final_end_date + relativedelta(days=internal)
            elif rental_extend.extend_term_type == 'weeks' and prv_final_end_date:
                rental_extend.date = prv_final_end_date + relativedelta(days=7 * internal)
            elif rental_extend.extend_term_type == 'months' and prv_final_end_date:
                rental_extend.date = prv_final_end_date + relativedelta(months=internal)
            elif rental_extend.extend_term_type == 'years' and prv_final_end_date:
                rental_extend.date = prv_final_end_date + relativedelta(years=internal)
            if rental_extend.extend_term_type == 'hours':
                if prv_final_end_date:
                    rental_extend.date = prv_final_end_date + relativedelta(hours=internal)

    def extend_rental(self):
        rental = self.env['rental.order'].browse(self._context.get('active_id'))
        res_data = self.env['rental.extend'].search([('rental_id', '=', rental.id), ('state', '=', 'draft')], limit=1)
        if len(res_data) > 0:
            raise ValidationError("There is an extended rental in rental order that hasn't been confirmed")

        # if self.date.date() == self.rental_start_date.date() and rental.rental_initial_type != 'hours':
        #     raise ValidationError(_("Sorry !!! You cannot change initials terms for same date"))
        # if self.date < self.rental_start_date:
        #     raise ValidationError(_("Please Select Proper Date"))
        prv_final_end_date = rental.end_date
        if rental.final_end_date:
            prv_final_end_date = rental.final_end_date

        # rental.final_end_date = self.date
        # rental.end_date = self.date
        # rental.rental_initial_type = self.rental_initial_type
        # rental.rental_initial = self.rental_initial
        # rental._onchange_rental_initial_type()

        vals_line = []
        for extend_line in rental.rental_line:
            extend_price_unit = 0
            for rental_extend in self:
                if rental_extend.extend_term_type == 'days':
                    extend_price_unit = extend_line.product_id.rent_per_day * rental_extend.extend_term
                elif rental_extend.extend_term_type == 'weeks':
                    extend_price_unit = extend_line.product_id.rent_per_week * rental_extend.extend_term
                elif rental_extend.extend_term_type == 'months':
                    extend_price_unit = extend_line.product_id.rent_per_month * rental_extend.extend_term
                elif rental_extend.extend_term_type == 'years':
                    extend_price_unit = extend_line.product_id.rent_per_year * rental_extend.extend_term
                elif rental_extend.extend_term_type == 'hours':
                    extend_price_unit = extend_line.product_id.rent_per_hour * rental_extend.extend_term

            vals_line.append((0, 0, {
                'name': extend_line.name,
                'sequence': extend_line.sequence,
                'product_categ_id': extend_line.product_categ_id.id,
                'product_id': extend_line.product_id.id,
                'product_uom_qty': extend_line.product_uom_qty,
                'price_unit': extend_price_unit,
                'lot_id': extend_line.lot_id.id,
                'invoice_lines': [(6, 0, extend_line.invoice_lines.ids)],
                'tax_id': [(6, 0, extend_line.tax_id.ids)],
            }))
        created_rental_extend = self.env['rental.extend'].create({
            'rental_id': rental.id,
            'rental_start_date': rental.start_date,
            'rental_initial': rental.rental_initial,
            'rental_initial_type': rental.rental_initial_type,
            'end_date': self.date,
            'start_date': prv_final_end_date,
            'extend_term_type': self.extend_term_type,
            'extend_term': self.extend_term,
            'invoice_id': rental.invoice_id.id,
            'name': rental.name,
            'partner_invoice_id': rental.partner_invoice_id.id,
            'client_order_ref': rental.client_order_ref,
            'user_id': rental.user_id.id,
            'company_id': rental.company_id.id,
            'currency_id': rental.currency_id.id,
            'rental_line': vals_line,
            'state': 'draft',
            'extend_term_and_type': str(self.extend_term) + " " + self.extend_term_type,
            'is_recurring_invoice': self.is_recurring_invoice,
            'rental_bill_freq': self.rental_bill_freq,
            'rental_bill_freq_type': self.rental_bill_freq_type,
        })

        created_rental_extend.confirm_extend()

        return

class RentalOrderExtend(models.Model):
    _name = "rental.extend"
    _order = 'id desc'

    rental_id = fields.Many2one('rental.order', string="Rental Order")
    name = fields.Char(string='Order Reference')
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', help="Invoice address for current sales order.")
    client_order_ref = fields.Char(string='Reference')
    user_id = fields.Many2one('res.users', string='Salesperson')
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get('rental.extend'))
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    rental_start_date = fields.Datetime(string="Rental Start Date")
    rental_initial = fields.Integer(string="Initial Terms")
    rental_initial_type = fields.Selection(string="Initial Terms", related='rental_id.rental_initial_type',
                                           readonly=False)
    end_date = fields.Datetime(string="New Extended Date", required=False)

    start_date = fields.Datetime(string="Start Date")
    extend_term_type = fields.Selection(
        [
            ('hours', 'Hours'),
            ('days', 'Days'),
            ('weeks', 'Weeks'),
            ('months', 'Months'),
            ('years', 'Years')
        ], default='hours', string='Extend Term Type')
    extend_term = fields.Integer(string="Extend Term")
    invoice_id = fields.Many2one('account.move', 'Invoice')
    confirmation_date = fields.Datetime('Confirmation Date', readonly=True)
    amount_untaxed = fields.Float(compute='_amount_all', string='Untaxed Amount', store=True, readonly=True,
                                  track_visibility='onchange')
    amount_tax = fields.Float(compute='_amount_all', string='Taxes', store=True, readonly=True)
    amount_total = fields.Float(compute='_amount_all', string='Total', store=True, readonly=True,
                                track_visibility='always')

    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('reject', 'Reject')], string='State')
    rental_line = fields.One2many('rental.extend.line', 'rental_id', string='Extend Rental Line')
    extend_term_and_type = fields.Char(string="Extend Terms")
    next_counter_invoice = fields.Integer(
        string='Invoice Next Counter',
        default=0,
        readonly=True,
        copy=False
    )
    rental_bill_freq_type = fields.Selection(
        string="Rental Bill Frequrency Type",
        selection=[
            ('hours', 'Hours'),
            ('days', 'Days'),
            ('weeks', 'Weeks'),
            ('months', 'Months'),
            ('years', 'Years')
        ],
        required=False,
        default="hours",
        copy=False,
        tracking=True
    )
    is_recurring_invoice = fields.Boolean("Recurring Invoice", tracking=True)
    rental_bill_freq = fields.Integer(string='Rental Bill Frequency',default=1, tracking=True)
    rec_hours = fields.Float("Counter Hour", compute='check_counter', store=True)
    rec_days = fields.Float("Counter Days", compute='check_counter', store=True)
    rec_weeks = fields.Float("Counter Weeks", compute='check_counter', store=True)
    rec_months = fields.Float("Counter Months", compute='check_counter', store=True)
    rec_years = fields.Float("Counter Years", compute='check_counter', store=True)
    hours = fields.Float("Hours")

    @api.depends('rental_bill_freq_type', 'rental_bill_freq', 'rental_initial_type', 'rental_initial', 'is_recurring_invoice')
    def check_counter(self):
        for rec in self:
            rec.check_rental_bill_freq()

    @api.onchange(
        "rental_bill_freq_type",
        "rental_bill_freq",
        "rental_initial_type",
        "rental_initial",
        "is_recurring_invoice",
    )
    def check_rental_bill_freq(self):
        for rec in self:
            validation_type = False
            validation_freq = False
            validation_qty = False
            rec_hours = 0
            rec_days = 0
            rec_weeks = 0
            rec_months = 0
            rec_years = 0

            if rec.is_recurring_invoice:
                if rec.rental_bill_freq and rec.rental_initial:
                    initial_type_map = {
                        "hours": 1,
                        "days": 24,
                        "weeks": 24 * 7,
                        "months": 24 * 30,
                        "years": 24 * 365,
                    }

                    # Calculate initial hours based on rental_initial_type
                    rec_hours = (
                        rec.rental_initial * initial_type_map[rec.rental_initial_type]
                    )

                    # Check for validation errors
                    if rec.rental_bill_freq_type != rec.rental_initial_type:
                        if (
                            initial_type_map[rec.rental_bill_freq_type]
                            > initial_type_map[rec.rental_initial_type]
                        ):
                            validation_type = True
                    elif rec.rental_bill_freq > rec.rental_initial:
                        validation_freq = True
                    elif rec.rental_initial % rec.rental_bill_freq:
                        validation_qty = True

                    if validation_type:
                        raise ValidationError(
                            "Rental bill frequency time unit can't be more than initial terms time unit."
                        )
                    elif validation_freq:
                        raise ValidationError(
                            "Rental bill frequency can't be more than initial terms."
                        )
                    elif validation_qty:
                        raise ValidationError(
                            "Rental bill frequency you choose is not valid for the initial terms."
                        )

                    # Calculate the respective frequency units
                    if rec.rental_bill_freq_type == "hours":
                        rec_hours = rec_hours / rec.rental_bill_freq
                    elif rec.rental_bill_freq_type == "days":
                        rec_days = rec_hours / (
                            rec.rental_bill_freq
                            * initial_type_map[rec.rental_bill_freq_type]
                        )
                    elif rec.rental_bill_freq_type == "weeks":
                        rec_weeks = rec_hours / (
                            rec.rental_bill_freq
                            * initial_type_map[rec.rental_bill_freq_type]
                        )
                    elif rec.rental_bill_freq_type == "months":
                        rec_months = rec_hours / (
                            rec.rental_bill_freq
                            * initial_type_map[rec.rental_bill_freq_type]
                        )
                    elif rec.rental_bill_freq_type == "years":
                        rec_years = rec_hours / (
                            rec.rental_bill_freq
                            * initial_type_map[rec.rental_bill_freq_type]
                        )

                    rec.update(
                        {
                            "rec_hours": rec_hours,
                            "rec_days": rec_days,
                            "rec_weeks": rec_weeks,
                            "rec_months": rec_months,
                            "rec_years": rec_years,
                        }
                    )
            else:
                rec.rental_bill_freq = 1
                rec.rental_bill_freq_type = "hours"

    @api.depends('rental_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.rental_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    def display_extend(self):
        return {
                'type': 'ir.actions.act_window',
                'res_model': 'rental.extend',
                'view_mode': 'form',
                'target': 'new',
                'res_id': self.id,
                'flags': {'mode': 'readonly'},
                'view_id': self.env.ref('equip3_rental_operation.form_rental_extend_view').id,
        }

    def create_rental_extend_recurring_invoice(self):
        today_date = date.today()
        for rental in self:
            if rental.start_date.date() >= today_date and today_date <= rental.end_date.date():
                if rental.rental_bill_freq_type == 'hours':
                    if rental.hours < rental.rental_bill_freq:
                        rental.hours += 1
                        next_counter_invoice = rental.next_counter_invoice
                    if rental.hours == rental.rental_bill_freq:
                        rental.sudo()._create_invoice_rental_extend()
                        rental.hours = 0
                        next_counter_invoice = rental.next_counter_invoice - 1
                else:
                    rental.sudo()._create_invoice_rental_extend()
                    next_counter_invoice = rental.next_counter_invoice - 1

                rental.sudo().write({
                    'next_counter_invoice' : next_counter_invoice
                })

        return True

    def _create_invoice_rental_extend(self):
        inv_obj = self.env['account.move']
        inv_line = []
        next_counter_invoice = 0

        for rental in self:
            for line in rental.rental_line:
                account_id = False
                if line.product_id.id:
                    account_id = line.product_id.categ_id.property_account_income_categ_id.id
                if not account_id:
                    raise ValidationError(
                        _(
                            'There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.'
                        )
                        % (line.product_id.name,)
                    )
                name = _('Down Payment')

                if rental.is_recurring_invoice:
                    initial_terms = self.get_initial_terms()
                    unit_price_divisor = initial_terms / rental.rental_bill_freq
                    next_counter_invoice = unit_price_divisor - 1
                    price = line.price_unit / unit_price_divisor
                else:
                    price = line.price_unit

                inv_line.append((0, 0, {
                    'name': line.product_id.description_rental or line.name or " ",
                    'account_id': account_id,
                    'price_unit': price,
                    'quantity': 1.0,
                    'rental_extend_line_ids': [(6, 0, [line.id])],
                    'product_uom_id': line.product_id.uom_id.id,
                    'product_id': line.product_id.id,
                    'tax_ids': [(6, 0, line.tax_id.ids)],
                }))
            journal_id = self.env['account.move']._search_default_journal(["sale"])
            invoice = inv_obj.create({
                'invoice_origin': rental.name or " ",
                'move_type': 'out_invoice',
                'rental_id': rental.rental_id.id,
                'rental_extend_id': rental.id,
                'journal_id': journal_id.id,
                'invoice_date': datetime.datetime.now(),
                'branch_id': rental.rental_id.branch_id.id,
                'ref': False,
                'partner_id': rental.partner_invoice_id.id,
                'invoice_line_ids': inv_line,
                'currency_id': rental.currency_id.id,
                'user_id': rental.user_id.id,
                'rental_start_date': rental.start_date,
                'rental_end_date': rental.end_date,
                'from_rent_order': True,
            })
            if rental.state == 'draft':
                rental.next_counter_invoice = next_counter_invoice

        return invoice

    def confirm_extend(self):
        for rental in self:
            invoice_rental_extend = self._create_invoice_rental_extend()
            invoice = self.env['account.move'].search(
                [
                    ('rental_id', '=', rental.rental_id.id),
                    ('rental_extend_id', '!=', False)
                ]
            )
            rental.rental_id.final_end_date = rental.end_date
            self.write({'state': 'confirm'})

    def reject_extend(self):
        self.write({'state': 'reject'})
        self.rental_id.final_end_date = self.start_date

    def get_initial_terms(self):
        conversion_factors = {
            "hours": {
                "hours": 1,
                "days": 1 / 24,
                "weeks": 1 / 168,
                "months": 1 / 720,
                "years": 1 / 8760,
            },
            "days": {
                "hours": 24,
                "days": 1,
                "weeks": 1 / 7,
                "months": 1 / 30,
                "years": 1 / 365,
            },
            "weeks": {
                "hours": 168,
                "days": 7,
                "weeks": 1,
                "months": 1 / 4,
                "years": 1 / 52,
            },
            "months": {
                "hours": 720,
                "days": 30,
                "weeks": 4,
                "months": 1,
                "years": 1 / 12,
            },
            "years": {
                "hours": 8760,
                "days": 365,
                "weeks": 52,
                "months": 12,
                "years": 1,
            },
        }

        initial_terms = 0

        for rental in self:
            initial_terms = (
                rental.extend_term * conversion_factors[rental.extend_term_type][rental.rental_bill_freq_type]
            )

        return initial_terms


class RentalOrderExtendLine(models.Model):
    _name = 'rental.extend.line'

    rental_id = fields.Many2one('rental.extend', string='Rental Reference')
    name = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)])
    product_categ_id = fields.Many2one('product.category', related="product_id.categ_id", string='Product Category')
    product_uom_qty = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Float('Price Unit', required=True, digits='Product Price', default=0.0)
    lot_id = fields.Many2one('stock.production.lot', string='Serial Number')
    invoice_lines = fields.Many2many('account.move.line', string='Invoice Lines')
    tax_id = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use', '!=', 'none')
        , '|', ('active', '=', False), ('active', '=', True)])
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Price Taxes', readonly=True, store=True)
    price_total = fields.Float(compute='_compute_amount', string='Total', readonly=True, store=True)


    @api.depends('price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.tax_id.compute_all(line.price_unit)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

class AccountInvoice(models.Model):
    _inherit = 'account.move'

    rental_extend_id = fields.Many2one('rental.extend')

class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'

    rental_extend_line_ids = fields.Many2many('rental.extend.line', string='Rental Extend Lines', readonly=True, copy=False)
