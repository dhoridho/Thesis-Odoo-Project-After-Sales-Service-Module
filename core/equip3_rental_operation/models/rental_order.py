# from dataclasses import field
import datetime
from locale import currency

import pytz

from odoo import tools, api , fields , models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError, Warning
from num2words import num2words
import logging
from datetime import datetime, date, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare

from . import amount_to_text
try:
    from num2words import num2words
except ImportError:
    logging.getLogger(__name__).warning(
        "The num2words python library is not installed, l10n_mx_edi features won't be fully available.")
    num2words = None

class RentalOrder(models.Model):
    _name = "rental.order"
    _inherit = ["rental.order",'mail.thread','mail.activity.mixin']

    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    @api.depends('amount_total')
    def _amount_in_words(self):
        for obj in self:
            if obj.partner_id.lang == 'nl_NL':
                obj.amount_to_text = amount_to_text.amount_to_text_nl(
                    obj.amount_total, currency='euro')
            else:
                try:
                    if obj.partner_id.lang:
                        obj.amount_to_text = num2words(
                            obj.amount_total, lang=obj.partner_id.lang).title()
                    else:
                        obj.amount_to_text = num2words(
                            obj.amount_total, lang='en').title()
                except NotImplementedError:
                    obj.amount_to_text = num2words(
                        obj.amount_total, lang='en').title()

    @api.constrains('rental_bill_freq', 'rental_initial')
    def _check_rental(self):
        for rec in self:
            if not rec.rental_bill_freq and not rec.rental_initial:
                raise ValidationError("Rental bill frequency or initial terms can't be 0.")

    @api.model
    def _domain_partner_id(self):
        return [
            ('company_id','in', self.env.companies.ids),
            ('is_customer', '=', True),
            ('type', '=', 'contact')
        ]

    @api.model
    def _get_state_options(self):
        return [
            ("draft", "Quotation"),
            ("waiting", "Waiting for Approval"),
            ("confirm", "Confirmed Rental"),
            ("running", "Running"),
            ("close", "Closed Rental"),
            ("canceled", "Canceled"),
            ("rejected", "Rejected")
        ]

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', tracking=True)
    amount = fields.Monetary(string="Amount Deposit", tracking=True)
    invoice_deposit_received = fields.Boolean(compute='_compute_invoice_deposit_received', string='Deposit Received?', copy=False)
    is_invoice_deposit_return = fields.Boolean(compute='_compute_invoice_deposit_return', string='Deposit Returned?', copy=False)
    count_deposit = fields.Integer(compute="_compute_deposit", string="Deposit Count")
    is_checking = fields.Boolean(string="Checking", default=False)
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")
    checklist_line_ids = fields.One2many('rental.order.checklist.line', 'order_id' ,string="Checklist Line")
    total_accessories = fields.Float(string='Total (Checklist Item)',readonly=True, compute="_compute_price_total")
    missing_cost = fields.Float(string="Total Missing Cost", readonly=True, invisible=True, compute="_compute_price_total")
    damage_cost = fields.Float(string="Total Damage Cost", readonly=True )
    damage_order_cost = fields.Float(string="Damage Cost")
    total = fields.Float(string="Total", readonly=True)
    notes = fields.Text(string="Detail & Notes")
    is_verified = fields.Boolean(string="Verified", default=False)
    state = fields.Selection(selection_add=[("waiting", "Waiting for Approval"), ("running", "Running"), ('close',),("canceled", "Canceled"), ("rejected", "Rejected")])
    is_return = fields.Boolean(string="Return")
    is_in_validate = fields.Boolean(string="Validate")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=False, help="Pricelist for current sales order.")
    amount_total = fields.Monetary(compute='_amount_all',string='Total', store=True, readonly=True,  track_visibility='always')
    state2 = fields.Selection([
		('pending', 'Pending'),
		('picked', 'Picked-up'),
		('returned', 'Returned'),
	], string='Status', readonly=True, default='pending')
    amount_to_text = fields.Char(compute='_amount_in_words', string='In Words', help="The amount in words")
    new_rental_bill_freq_type = fields.Selection(string="Freq Type",
        selection=[
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
        ], required=False, default="hours", copy=False, tracking=True
    )
    rental_bill_freq_type = fields.Selection(string="Freq Type", related='new_rental_bill_freq_type', store=True)
    is_reccuring_invoice = fields.Boolean("Recurring Invoice", tracking=True)
    rental_bill_freq = fields.Integer(string='Rental Bill Frequency',default=1, tracking=True)
    rec_hours = fields.Float("Counter Hour", compute='check_counter', store=True)
    rec_days = fields.Float("Counter Days", compute='check_counter', store=True)
    rec_weeks = fields.Float("Counter Weeks", compute='check_counter', store=True)
    rec_months = fields.Float("Counter Months", compute='check_counter', store=True)
    rec_years = fields.Float("Counter Years", compute='check_counter', store=True)
    hours = fields.Float("Hours")
    expiry_date = fields.Datetime(string='Expiry Date', required=True, tracking=True)
    is_expiry_date = fields.Boolean(string="Use end date as expiry date", default=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True, domain=_domain_partner_id)
    agrement_ok = fields.Boolean(string='Agreement Received?', default=False, tracking=True)
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', required=True, help="Invoice address for current sales order.", tracking=True)
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', required=True, help="Delivery address for current sales order.", tracking=True)
    rental_initial = fields.Integer(string='Initial Terms', tracking=True)
    start_date = fields.Datetime(string='Start Date', tracking=True)
    end_date = fields.Datetime(string='End Date', tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
								   required=True,default=_default_warehouse_id, tracking=True)
    close_date = fields.Datetime(string='Close Date', readonly = True)
    renew_date = fields.Date('Date Of Next Invoice', copy=False, tracking=True)
    date_order = fields.Datetime(string='Order Date', required=True, readonly=True, default=fields.Datetime.now, tracking=True)#,states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    client_order_ref = fields.Char(string='Reference', tracking=True)
    confirmation_date = fields.Datetime('Confirmation Date', readonly=True, tracking=True)
    rental_line = fields.One2many('rental.order.line', 'rental_id', string=' Asset Rental Line ' ,copy =False, tracking=True)
    rental_initial_type = fields.Selection(string="Initial Terms Type", selection=[
		('hours', 'Hours'), 
		('days', 'Days'), 
		('weeks', 'Weeks'), 
		('months', 'Months'),
        ('years', 'Years')], required=False, default="days" , copy=False, tracking=True)
    branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    rental_closed = fields.Boolean('Rental Closed', default=False)
    damage_cost_line_ids = fields.One2many(
        comodel_name='rental.order.damage.cost.line',
        inverse_name='rental_order_id',
        string="Damage Cost Line"
    )
    is_need_deposit = fields.Boolean()
    is_hide_deposit = fields.Boolean()
    return_rental_order_count = fields.Integer(
        string='Return',
        compute='_compute_return_rental_count'
    )
    replace_product_delivery_count = fields.Integer(
        string="Replace Product Delivery Count",
        compute="_compute_replace_product_delivery_count"
    )
    is_single_delivery_address = fields.Boolean(string="Single Delivery Address", default=True, tracking=True)
    is_intercompany_transaction = fields.Boolean(string="Intercompany Transaction", default=False, tracking=True)
    is_rental_order_approval_matrix = fields.Boolean(string="Is Rental Order Approval Matrix")
    approval_matrix_id = fields.Many2one(comodel_name="rental.order.approval.matrix", string="Approval Matrix")
    rental_approval_line_ids = fields.One2many(
        comodel_name="rental.approval.matrix",
        inverse_name="rental_order_id",
        string='Rental Approval Matrix',
        compute='_compute_rental_approval_line_ids',
        store=True
    )
    is_need_approval = fields.Boolean(string='Need Approval', compute='_compute_is_need_approval')
    state_confirmed = fields.Selection(selection=_get_state_options, string="State for Confrimed", compute='_compute_state')
    state_rejected = fields.Selection(selection=_get_state_options, string="State for Rejected", compute='_compute_state')
    state_default = fields.Selection(selection=_get_state_options, string="State Default", compute='_compute_state')
    state_need_approval_hide_waiting = fields.Selection(selection=_get_state_options, string="State Need Approval", compute='_compute_state')

    @api.depends('state')
    def _compute_state(self):
        for rental in self:
            state = rental.state or 'draft'
            rental.state_confirmed = state
            rental.state_rejected = state
            rental.state_default = state
            rental.state_need_approval_hide_waiting = state

    @api.model
    def default_get(self, fields):
        res = super(RentalOrder, self).default_get(fields)
        company = self.env.company
        if company.rental and company.is_rental_order_approval_matrix:
            res.update({
                'is_rental_order_approval_matrix' : company.is_rental_order_approval_matrix
            })

        if res.get('branch_id'):
            approval_matrix = self.env['rental.order.approval.matrix'].search(
                [('branch_id', '=', res.get('branch_id'))]
            )
            res.update({"approval_matrix_id": approval_matrix.id})

        return res

    def action_request_approaval(self):
        for record in self:
            record.write({"state": "waiting"})

    @api.depends("approval_matrix_id")
    def _compute_is_need_approval(self):
        for record in self:
            approval_matrix = record.approval_matrix_id
            approver_user_ids, approved_user_ids = (
                record.get_approver_and_approved_user_ids()
            )
            current_user = self.env.uid
            if (
                approval_matrix
                and current_user in approver_user_ids
                and current_user not in approved_user_ids
            ):
                record.is_need_approval = True
            else:
                record.is_need_approval = False

    def get_approver_and_approved_user_ids(self):
        approver_user_ids = []
        approved_user_ids = []
        for record in self:
            next_approval_line = record.rental_approval_line_ids.filtered(
                lambda line: len(line.approved_user_ids) < len(line.user_ids)
            ).sorted(key=lambda line: line.sequence)
            if next_approval_line:
                for line in next_approval_line[0]:
                    for approver_id in line.user_ids.ids:
                        approver_user_ids.append(approver_id)

                    for approved_id in line.approved_user_ids.ids:
                        approved_user_ids.append(approved_id)

        return approver_user_ids, approved_user_ids

    @api.onchange('branch_id')
    def get_approval_matrix_iu(self):
        for record in self:
            if record.branch_id:
                approval_matrix = self.env['rental.order.approval.matrix'].search(
                    [('branch_id', '=', record.branch_id.id)]
                )
                record.approval_matrix_id = approval_matrix.id
            else:
                record.approval_matrix_id = False

    @api.depends('approval_matrix_id')
    def _compute_rental_approval_line_ids(self):
        for record in self:
            if record.is_rental_order_approval_matrix and record.approval_matrix_id:
                record.get_approval_matrix(record.approval_matrix_id)
            else:
                record.rental_approval_line_ids = [(5, 0, 0)]

    def get_approval_matrix(self, matrix):
        for record in self:
            if matrix:
                data_approvers = []
                for line in matrix.approval_matrix_line_ids:
                    data_approvers.append(
                        (
                            0,
                            0,
                            {
                                "sequence": line.sequence,
                                "minimum_approver": line.minimum_approver,
                                "user_ids": [(6, 0, line.user_ids.ids)],
                            },
                        )
                    )
                record.rental_approval_line_ids = [(5, 0, 0)] + data_approvers
            else:
                record.rental_approval_line_ids = [(5, 0, 0)]

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.rental_approval_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(
            RentalOrder, self.with_context(keep_line_sequence=True)
        ).copy(default)

        return res

    def action_approve(self):
        for record in self:
            user = self.env.user
            for line in record.rental_approval_line_ids:

                if user.id in line.user_ids.ids:
                    approved_time = line.approved_time or ""
                    if approved_time != "":
                        approved_time += "\n• %s: Approved - %s" % (
                            user.name,
                            datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        )
                    else:
                        approved_time += "• %s: Approved - %s" % (
                            user.name,
                            datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        )
                    line.write({"approved_user_ids": [(4, user.id)]})
                    if len(line.approved_user_ids) < line.minimum_approver:
                        line.write(
                            {
                                "state": "waiting",
                                "approval_status": "Waiting for Approval",
                                "approved_time": approved_time
                            }
                        )
                    else:
                        line.write(
                            {
                                "state": "confirmed",
                                "approval_status": "Confirmed Order",
                                "approved_time": approved_time
                            }
                        )

            confrimed_approvals = record.rental_approval_line_ids.filtered(
                lambda line: line.state == "confirmed"
                and len(line.user_ids.ids) == len(line.approved_user_ids.ids)
            )
            if len(confrimed_approvals.ids) == len(
                record.approval_matrix_id.approval_matrix_line_ids.ids
            ):
                record.action_button_confirm_rental()

    def action_reject(self, reason):
        for record in self:
            user = self.env.user
            for line in record.rental_approval_line_ids:
                feedback = line.feedback or ""
                if feedback != "":
                    feedback += "\n• %s:  %s" % (user.name, reason)
                else:
                    feedback += "• %s: %s" % (user.name, reason)

                if user.id in line.user_ids.ids:
                    line.write(
                        {
                            "approved_user_ids": [(4, user.id)],
                            "total_reject_users": line.total_reject_users + 1,
                        }
                    )
                    if (
                        line.total_reject_users == line.minimum_approver
                        and line.total_reject_users != len(line.user_ids.ids)
                    ):
                        line.write(
                            {
                                "approval_status": "Waiting for Approval",
                                "feedback": feedback,
                            }
                        )
                    else:
                        line.write(
                            {
                                "approval_status": "Rejected",
                                "state": "rejected",
                                "feedback": feedback,
                            }
                        )
            confrimed_approvals = record.rental_approval_line_ids.filtered(
                lambda line: line.state == "confirmed"
            )
            rejected_approvals = record.rental_approval_line_ids.filtered(
                lambda line: line.state == "rejected"
            )
            if len(confrimed_approvals.ids) == len(
                record.approval_matrix_id.approval_matrix_line_ids.ids
            ):
                record.action_button_confirm_rental()
            elif rejected_approvals:
                record.state = "rejected"

    def action_open_fedback_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rental.order.feedback.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Reject Reason",
            'target': 'new',
            'context':{'default_rental_id':self.id},
        }

    def _compute_picking_ids(self):
        for order in self:
            procurement_group_id = self.env['procurement.group'].search([('name', '=', order.name)])
            pickings = self.env['stock.picking'].search([
                ('group_id', 'in', procurement_group_id.ids),
                ('picking_type_code', '=', 'outgoing'),
                ('is_replace_product', '=', False)
            ])
            order.picking_ids = self.env['stock.picking'].search([('group_id', 'in', procurement_group_id.ids)])
            order.delivery_count = len(pickings)

    def action_view_delivery_rental(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''

        result = {
            'name': 'Picking',
            'type': 'ir.actions.act_window',
            'binding_view_types': 'list,form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
        }
        pick_ids = sum([rental.picking_ids.ids for rental in self], [])

        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',["+','.join(map(str, pick_ids))+"]), ('picking_type_code', '=', 'outgoing'), ('is_replace_product', '=', False)]"
        elif len(pick_ids) == 1:
            form = self.env.ref('stock.view_picking_form', False)
            form_id = form.id if form else False
            result['views'] = [(form_id, 'form')]
            result['res_id'] = pick_ids[0]
        return result

    def _compute_return_rental_count(self):
        for order in self:
            pickings = self.env['stock.picking'].search([
                ('rental_id', '=', order.id),
                ('picking_type_code', '=', 'incoming'),
                ('is_from_intercompany_transaction', '=', False)
            ])
            order.return_rental_order_count = len(pickings)

    def action_return_rental(self):
        result = {
			'name': 'Return',
			'type': 'ir.actions.act_window',
			'binding_view_types': 'list,form',
			'view_mode': 'tree,form',
			'res_model': 'stock.picking',
		}
        pick_ids = sum([rental.picking_ids.ids for rental in self], [])

        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',["+','.join(map(str, pick_ids))+"]), ('picking_type_code', '=', 'incoming'), ('is_from_intercompany_transaction', '=', False)]"
        elif len(pick_ids) == 1:
            form = self.env.ref('stock.view_picking_form', False)
            form_id = form.id if form else False
            result['views'] = [(form_id, 'form')]
            result['res_id'] = pick_ids[0]
        return result

    def _compute_replace_product_delivery_count(self):
        for order in self:
            pickings = self.env['stock.picking'].search([
                ('rental_id', '=', order.id),
                ('picking_type_code', '!=', 'incoming'),
                ('is_replace_product', '=', True)
            ])
            order.replace_product_delivery_count = len(pickings)

    def action_replace_product_delivery(self):
        result = {
			'name': 'Replace Product Delivery',
			'type': 'ir.actions.act_window',
			'binding_view_types': 'list,form',
			'view_mode': 'tree,form',
			'res_model': 'stock.picking',
		}
        pick_ids = sum([rental.picking_ids.ids for rental in self], [])

        if len(pick_ids) > 1:
            result["domain"] = (
                "[('id','in',["
                + ",".join(map(str, pick_ids))
                + "]), ('is_replace_product', '=', True), ('picking_type_code', '!=', 'incoming')]"
            )
        elif len(pick_ids) == 1:
            form = self.env.ref('stock.view_picking_form', False)
            form_id = form.id if form else False
            result['views'] = [(form_id, 'form')]
            result['res_id'] = pick_ids[0]
        return result

    @api.constrains('is_need_deposit','amount')
    def _check_amount_deposit(self):
        if self.is_need_deposit and self.amount < 0 or self.is_need_deposit and self.amount  == 0:
            raise  ValidationError(_("Amount Deposit value can’t be zero"))

    @api.constrains('rental_initial','rental_bill_freq', 'rental_initial_type', 'rental_bill_freq_type')
    def _check_amount(self):
        if self.is_reccuring_invoice:
            if self.rental_bill_freq == 0:
                raise UserError(_('Rental Bill Frequency can not set to Zero !!!'))
        else:
            if self.rental_initial_type == 'hours':
                if (self.rental_initial % self.rental_bill_freq) != 0:
                    raise ValidationError(_('Rental Bill Frequency Must be In multiple of Initial Rental Terms.'))
        if self.rental_initial > 24 and self.rental_initial_type == 'hours':
            raise ValidationError(_('Sorry !!! You Cannot Enter More then 24 hrs'))

    @api.onchange('branch_id','company_id')
    def set_warehouse_id(self):
        for res in self:
            stock_warehouse = res.env['stock.warehouse'].search([('company_id', '=', res.company_id.id),('branch_id', '=', res.branch_id.id)], order="id", limit=1)
            res.warehouse_id = stock_warehouse or False

    @api.onchange("end_date","is_expiry_date")
    def on_change_expiry_date(self):
        for rec in self:
            rental_order_expiry_date_setting = int(self.env['ir.config_parameter'].sudo().get_param('equip3_rental_operation.rental_order_expiry_date'))
            if rental_order_expiry_date_setting > 0:
                rental_order_expiry_date = rental_order_expiry_date_setting
            else:
                rental_order_expiry_date = 0

            if rec.end_date and rec.is_expiry_date:
                rec.expiry_date = rec.end_date
            elif rec.end_date and not rec.is_expiry_date:
                rec.expiry_date = rec.end_date + relativedelta(days=rental_order_expiry_date)

    @api.constrains('end_date','expiry_date')
    def _check_expiry_date(self):
        for rec in self:
            if rec.expiry_date < rec.end_date:
                raise ValidationError("Expiration date cannot be before the end date")

    @api.constrains('start_date')
    def _check_start_date(self):
        for rec in self:
            # (fields.Datetime.today() - timedelta(hours=7)
            today_date = date.today()
            today_date = today_date.strftime('%Y-%m-%d')

            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)
            start_date_timezone = pytz.utc.localize(rec.start_date).astimezone(user_tz)
            start_date = start_date_timezone.strftime('%Y-%m-%d')
            if start_date < today_date:
                raise ValidationError("Cannot create Rental Order with backdate")

    def auto_expiry_rental(self):
        rental_order = self.env['rental.order'].search([
            ('expiry_date','<',datetime.now()),
            ('state', '=', 'confirm')
            ])
        for expiry in rental_order:
            expiry.write({
                'state': 'canceled',
                'next_invoice_counter': 0
            })
            if expiry.picking_ids:
                for picking in expiry.picking_ids:
                    user = self.env.user
                    journal_cancel = picking.journal_cancel
                    name = " Cancelled by %s at %s. Reason: " % (user.name, datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
                    if journal_cancel:
                        picking.cancel_reason = name + "Expired Rental Order"
                    if picking.transfer_id and picking.transfer_id.is_transit and picking.is_transfer_in and not picking.backorder_id:
                        for line in picking.move_line_ids_without_package:
                            transist_line = picking.transfer_id.product_line_ids.filtered(lambda r: r.product_id.id == line.product_id.id)
                            transist_line.write({'qty_cancel': line.qty_done})
                    picking.action_cancel()

    def auto_close_rental(self):
        today = datetime.now()
        rental_orders = self.env['rental.order'].search([
            ('end_date', '<', today),
            ('state', '=', 'running'),
            ('state2', '=', 'returned')
        ])

        if rental_orders:
            for rental_order in rental_orders:
                unpaid_invoices = rental_order.invoice_ids.filtered(lambda line:line.payment_state != 'paid')
                if len(unpaid_invoices) == 0:
                    rental_order.write({
                        'state': 'close',
                        'rental_closed': True,
                        'next_invoice_counter': 0
                    })
    @api.model  
    def check_contract(self):
        today_date = date.today()
        rental_extends = self.env['rental.extend'].search(
            [
                ('state', 'in', ('confirm', 'running')),
                ('next_counter_invoice', '>', 0)
            ]
        )
        rental_orders = self.search(
            [
                ('state', 'in', ('confirm', 'running')),
                ('next_invoice_counter', '>', 0)
            ]
        )

        for record in rental_orders:
            renew_date = False
            if record.renew_date == today_date and today_date <= record.end_date.date():
                if record.rental_bill_freq_type == 'hours':
                    if record.hours < record.rental_bill_freq:
                        record.hours += 1
                        next_invoice_counter = record.next_invoice_counter
                    if record.hours == record.rental_bill_freq:
                        record.sudo()._create_invoice_rental()
                        record.hours = 0
                        next_invoice_counter = record.next_invoice_counter - 1
                    renew_date = date.today() + relativedelta(hours=record.rental_bill_freq)
                elif record.rental_bill_freq_type == 'days':
                    record.sudo()._create_invoice_rental()
                    renew_date = date.today() + relativedelta(days=record.rental_bill_freq)
                    next_invoice_counter = record.next_invoice_counter - 1
                elif record.rental_bill_freq_type == 'months':
                    record.sudo()._create_invoice_rental()
                    renew_date = date.today() + relativedelta(months=record.rental_bill_freq)
                    next_invoice_counter = record.next_invoice_counter - 1
                elif record.rental_bill_freq_type == 'weeks':
                    record.sudo()._create_invoice_rental()
                    renew_date = date.today() + relativedelta(days=7*record.rental_bill_freq)
                    next_invoice_counter = record.next_invoice_counter - 1
                elif record.rental_bill_freq_type == 'years':
                    record.sudo()._create_invoice_rental()
                    renew_date = date.today() + relativedelta(years=record.rental_bill_freq)
                    next_invoice_counter = record.next_invoice_counter - 1

                record.sudo().write({
                    'renew_date' : renew_date,
                    'next_invoice_counter' : next_invoice_counter
                })

        for rental_extend in rental_extends:
            rental_extend.create_rental_extend_recurring_invoice()

        return True

    @api.depends('rental_bill_freq_type','rental_bill_freq','rental_initial_type','rental_initial','is_reccuring_invoice')
    def check_counter(self):
        for rec in self:
            rec.check_rental_bill_freq()

    @api.onchange('rental_bill_freq_type','rental_bill_freq','rental_initial_type','rental_initial','is_reccuring_invoice')
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

            if rec.is_reccuring_invoice:
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
                    rec.onchange_rental_product_lines(0)
            else:
                rec.rental_bill_freq = 1
                rec.rental_bill_freq_type = "hours"

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        address = self.set_address(address)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        address = self.set_address(address)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def set_address(self, address):
        address = address.split(", ")
        rec_address = ""
        j = 0
        k = 1
        if "" in address:
            for i in address:
                if i == "":
                    address.pop(j)
                j += 1
        for res in address:
            rec_address += res
            if k != len(address):
                rec_address += ", "
            k += 1
        return rec_address

    def action_return(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'rental.order.return',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Return Rental Order",
            'target': 'new',
            'context':{'default_rental_id':self.id},
        }
        # self.is_return = True
        # pick_obj = self.env['stock.picking']
        # move_lines = []
        # group_id = self.env['procurement.group'].search([('name', '=', self.name)])
        # for rental in self:
        #     pick_type = self.env['stock.picking.type'].search([('name', '=', _('Receipts')), ('warehouse_id', '=', rental.warehouse_id.id)]).id
        #     picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'incoming'),
        #                                                                     ('warehouse_id.company_id', '=', rental.company_id.id)], limit=1)
        #     picking_id = pick_obj.search([
        #         ('group_id.rental_id', '=', self.id)
        #     ], limit=1)
        #     source_document = "Return of" + " " + picking_id.name
        #     new_picking = picking_id.copy({
        #         'picking_type_id': picking_type_id.id,
        #         'is_confirm': False,
        #         'origin': source_document,
        #         'location_id': picking_id.location_dest_id.id,
        #         'location_dest_id': picking_id.location_id.id,
        #     })
        # return False

    def action_open_cancel_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cancel.rental.order.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Cancel Rental Order",
            'target': 'new',
            'context':{'default_rental_id':self.id},
        }

    def action_cancel_rental_order(self, message):
        for rental in self:
            state_before = rental.state.capitalize()
            rental.state = "canceled"
            current_state = rental.state.capitalize()
            if message:
                rental.message_post(
                    body=_(f"{state_before} → {current_state}<br/>Reaons: {message}")
                )
            else:
                rental.message_post(
                    body=_(f"{state_before} → {current_state}<br/>Reaons: ")
                )

    def action_button_confirm_rental(self):
        self = self.with_context({"rental_order": self.id})
        res = super(RentalOrder, self).action_button_confirm_rental()
        self._check_rental_buffer()
        if self.is_reccuring_invoice:
            if self.rental_bill_freq_type == 'hours':
                self.renew_date = date.today() + relativedelta(hours=self.rental_bill_freq)

            initial_terms = self.get_initial_terms()
            unit_price_divisor = initial_terms / self.rental_bill_freq
            next_invoice_counter = unit_price_divisor - 1

            self.write(
                {
                    "next_invoice_counter": next_invoice_counter,
                    "confirmation_date": datetime.now(),
                }
            )

        for product in self.rental_line:
            product.lot_id.is_available_today = False
        for order in self:
            procurement_group_id = self.env["procurement.group"].search(
                [("name", "=", order.name)]
            )
            picking_ids = self.env["stock.picking"].search(
                [("group_id", "in", procurement_group_id.ids)]
            )
            for picking in picking_ids:
                moves = picking.move_ids_without_package.filtered(
                    lambda m: m.picking_id.id == picking.id
                )
                if moves:
                    for move in moves:
                        picking._change_rental_lines(move.lot_id.id)
                if picking.state == "confirmed" or (
                    picking.state in ["waiting", "assigned"] and not picking.printed
                ):
                    picking.action_assign()

        return res

    def action_close_rental(self):
        self.write({
            'state': 'close',
            'rental_closed': True
        })

    # def check_contract(self):
    #     pass
    def write(self, vals):
        for rec in self:
            if not rec.rental_bill_freq and not rec.rental_initial:
                raise ValidationError("Rental bill frequency and Initial Terms must be greater than 0")
            if 'next_invoice_counter' in vals and self.next_invoice_counter == 0:
                if rec.rental_bill_freq_type == 'hours':
                    vals['next_invoice_counter'] = self.rec_hours -1
                elif rec.rental_bill_freq_type == 'days':
                    vals['next_invoice_counter'] = self.rec_days -1
                elif rec.rental_bill_freq_type == 'weeks':
                    vals['next_invoice_counter'] = self.rec_weeks -1
                elif rec.rental_bill_freq_type == 'months':
                    vals['next_invoice_counter'] = self.rec_months -1
                elif rec.rental_bill_freq_type == 'years':
                    vals['next_invoice_counter'] = self.rec_years -1
            if rec.rental_initial:
                rec.onchange_rental_product_lines(self.rental_initial)
        res = super(RentalOrder, self).write(vals)
        return res

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('rental.order.new') or _('New')
        record = super(RentalOrder, self).create(vals)
        if not record.rental_bill_freq and not record.rental_initial:
            raise ValidationError("Rental bill frequency and Initial Terms must be greater than 0")

        return record

    @api.constrains('start_date', 'end_date', 'rental_line')
    def _check_rental_orders(self):
        for record in self:
            if any(line.price_unit < 0 for line in record.rental_line):
                raise ValidationError("Product Unit Price must be positive!")
            lot_ids = record.rental_line.mapped("lot_id").ids
            order_ids = self.search(
                [
                    ("id", "!=", record.id),
                    ("state", "in", ["confirm", "running"]),
                    "|",
                    "&",
                    ("start_date", "<=", record.start_date),
                    ("final_end_date", ">=", record.start_date),
                    "&",
                    ("start_date", "<=", record.end_date),
                    ("final_end_date", ">=", record.end_date),
                ]
            )
            rental_lot_ids = order_ids.mapped("rental_line.lot_id").ids
            if order_ids and any(lot in rental_lot_ids for lot in lot_ids):
                raise ValidationError(
                    "This product has already been rented in selected date."
                    + "Please change the start date and end date for the rent or close the already created rental for"
                    + " this product to save rental order."
                )

    def _create_invoice_with_saleable(self, force=False):
        inv_obj = self.env["account.move"]
        inv_line = []

        for rental in self:
            for line in rental.rental_line:
                account_id = False
                if line.product_id.id:
                    account_id = (
                        line.product_id.categ_id.property_account_income_categ_id.id
                    )
                if not account_id:
                    raise UserError(
                        _(
                            'There is no income account defined for this product: "%s". '
                            + 'You may have to install a chart of account from Accounting app, settings menu.'
                        )
                        % (line.product_id.name,)
                    )
                name = _("Down Payment")
                if self.is_reccuring_invoice:
                    initial_terms = self.get_initial_terms()
                    unit_price_divisor = initial_terms / rental.rental_bill_freq
                    price = line.price_unit / unit_price_divisor
                else:
                    price = line.price_unit
                inv_line.append(
                    (
                        0,
                        0,
                        {
                            "name": line.product_id.description_rental
                            or line.name
                            or " ",
                            "account_id": account_id,
                            "price_unit": price,
                            "quantity": 1.0,
                            "rental_line_ids": [(6, 0, [line.id])],
                            "product_uom_id": line.product_id.uom_id.id,
                            "product_id": line.product_id.id,
                            "serial_number_id": line.lot_id.id,
                            "tax_ids": [(6, 0, line.tax_id.ids)],
                        },
                    )
                )
            if rental.check_saleable:
                for line in rental.sale_line:
                    account_id = False
                    if line.product_id.id:
                        account_id = (
                            line.product_id.categ_id.property_account_income_categ_id.id
                        )
                    if not account_id:
                        raise UserError(
                            _(
                                'There is no income account defined for this product: "%s". '
                                + 'You may have to install a chart of account from Accounting app, settings menu.'
                            )
                            % (line.product_id.name,)
                        )
                    name = _("Down Payment")
                    inv_line.append(
                        (
                            0,
                            0,
                            {
                                "name": line.product_id.description_rental
                                or line.name
                                or " ",
                                "account_id": account_id,
                                "price_unit": line.price_unit
                                / line.rental_id.rental_bill_freq,
                                "quantity": line.product_uom_qty,
                                "sale_rental_line_ids": [(6, 0, [line.id])],
                                "product_uom_id": line.product_id.uom_id.id,
                                "product_id": line.product_id.id,
                                "tax_ids": [(6, 0, line.tax_id.ids)],
                            },
                        )
                    )
            journal_id = self.env["account.move"]._search_default_journal(["sale"])
            invoice = inv_obj.create(
                {
                    "invoice_origin": rental.name or " ",
                    "move_type": "out_invoice",
                    "rental_id": rental.id,
                    "journal_id": journal_id.id,
                    "ref": False,
                    "partner_id": rental.partner_invoice_id.id,
                    "invoice_line_ids": inv_line,
                    "currency_id": rental.currency_id.id,
                    "user_id": rental.user_id.id,
                    "rental_start_date": rental.start_date,
                    "rental_end_date": rental.end_date,
                    "branch_id": rental.branch_id.id,
                    "from_rent_order": True,
                    "is_invoice_from_rental": True,
                }
            )
            # invoice.action_post()
        return invoice

    def _create_picking(self):
        res = super()._create_picking()
        res.branch_id = res.rental_ref_id.branch_id.id
        return res

    def action_button_checking_rental(self):
        self.write({'is_checking': True})

    def action_button_close_rental(self):
        # if self.checklist_line_ids and not self.is_verified:
        #     raise ValidationError('Can’t close rental order if the checklist not verified yet. Please verify the checklist first.')
        return super(RentalOrder, self).action_button_close_rental()

    def _compute_deposit(self):
        obj = self.env['account.move']
        for record in self:
            record.count_deposit = obj.search_count([
                ('rental_order_id', '=', record.id),
            ])

    def action_button_verify_rental(self):
        self.write({'is_in_validate': False})
        self._create_invoice()

    @api.depends('checklist_line_ids', 'checklist_line_ids.price', 'damage_order_cost', 'checklist_line_ids.is_initem', 'damage_cost_line_ids')
    def _compute_price_total(self):
        for record in self:
            record.total_accessories = sum(record.checklist_line_ids.mapped('price'))
            record.missing_cost = sum(record.checklist_line_ids.filtered(lambda m: not m.is_initem and m.is_outitem).mapped('price'))
            record.damage_cost = sum(record.damage_cost_line_ids.mapped('damage_cost'))
            record.total = record.missing_cost + record.damage_cost

    def _create_invoice_rental(self, force=False):
        inv_obj = self.env["account.move"]
        inv_line = []
        for rental in self:
            for line in rental.rental_line:
                account_id = False
                if line.product_id.id:
                    account_id = (
                        line.product_id.categ_id.property_account_income_categ_id.id
                    )
                if not account_id:
                    raise UserError(
                        _(
                            'There is no income account defined for this product: "%s". '
                            + "You may have to install a chart of account from Accounting app, settings menu."
                        )
                        % (line.product_id.name,)
                    )
                name = _("Down Payment")
                if self.is_reccuring_invoice:
                    initial_terms = self.get_initial_terms()
                    unit_price_divisor = initial_terms / rental.rental_bill_freq
                    price = line.price_unit / unit_price_divisor
                else:
                    price = line.price_unit
                inv_line.append(
                    (
                        0,
                        0,
                        {
                            "name": line.product_id.description_rental
                            or line.name
                            or " ",
                            "account_id": account_id,
                            "price_unit": price,
                            "quantity": 1.0,
                            "rental_line_ids": [(6, 0, [line.id])],
                            "product_uom_id": line.product_id.uom_id.id,
                            "product_id": line.product_id.id,
                            "serial_number_id": line.lot_id.id,
                            "tax_ids": [(6, 0, line.tax_id.ids)],
                        },
                    )
                )
            invoice = inv_obj.create(
                {
                    "invoice_origin": rental.name or " ",
                    "move_type": "out_invoice",
                    "rental_id": rental.id,
                    "ref": False,
                    "partner_id": rental.partner_invoice_id.id,
                    "invoice_line_ids": inv_line,
                    "currency_id": rental.pricelist_id.currency_id.id,
                    "user_id": rental.user_id.id,
                    "rental_start_date": rental.start_date,
                    "rental_end_date": rental.end_date,
                    "from_rent_order": True,
                    "is_invoice_from_rental": True,
                    "branch_id": rental.branch_id.id,
                }
            )
        return invoice

    def _create_invoice(self):
        inv_obj = self.env["account.move"]
        inv_line = []
        for checklist in self:
            account_id = False
            product_id = (
                checklist.rental_line and checklist.rental_line[0].product_id or False
            )
            if product_id:
                account_id = product_id.categ_id.property_account_income_categ_id.id
            if not account_id:
                raise UserError(
                    _(
                        'There is no income account defined for this product: "%s". '
                        + 'You may have to install a chart of account from Accounting app, settings menu.'
                    )
                    % (checklist.name,)
                )
            if checklist.damage_cost_line_ids:
                for data in checklist.damage_cost_line_ids:
                    inv_line.append(
                        (
                            0,
                            0,
                            {
                                "name": data.damage_notes,
                                "product_id": data.product_id.id,
                                "serial_number_id": data.lot_id.id,
                                "account_id": data.product_id.categ_id.property_account_income_categ_id.id,
                                "price_unit": data.damage_cost,
                                "quantity": 1.0,
                                "product_uom_id": data.product_id.uom_id.id,
                            },
                        )
                    )
            # missing_cost_name = 'Missing Cost (Detail missing item: '
            # missing_cost_name += ', '.join(checklist.checklist_line_ids.filtered(lambda r: not r.is_available).mapped('item_id.name'))
            # missing_cost_name += ')'
            missing_cost = checklist.checklist_line_ids.filtered(
                lambda line: not line.is_initem
            )
            if missing_cost:
                for data in missing_cost:
                    inv_line.append(
                        (
                            0,
                            0,
                            {
                                "name": data.product_id.name,
                                "product_id": data.product_id.id,
                                "account_id": data.product_id.categ_id.property_account_income_categ_id.id,
                                "price_unit": data.price,
                                "quantity": 1.0,
                                "serial_number_id": data.lot_id.id,
                                "product_uom_id": data.product_id.uom_id.id,
                            },
                        )
                    )
            journal_id = self.env["account.move"]._search_default_journal(["sale"])
            invoice = inv_obj.create(
                {
                    # 'name': sequence,
                    "invoice_origin": checklist.name or " ",
                    "move_type": "out_invoice",
                    "rental_id": checklist.id,
                    "ref": False,
                    "partner_id": checklist.partner_invoice_id.id,
                    "invoice_line_ids": inv_line,
                    "currency_id": checklist.currency_id.id,
                    "branch_id": self.branch_id.id,
                    "user_id": checklist.user_id.id,
                    "rental_start_date": checklist.start_date,
                    "rental_end_date": checklist.end_date,
                    "from_rent_order": True,
                    "is_invoice_from_rental": True,
                }
            )
            # invoice.action_post()
        return invoice

    @api.depends('amount')
    def _compute_invoice_deposit_return(self):
        for record in self:
            credit_ids = self.env['account.move'].search([
                ('rental_order_id', '=', record.id),
                ('move_type', '=', 'out_refund'),
                ('state', 'in', ['posted']),
                ('is_deposit_return_invoice', '=', True)
            ])
            residual_amt = 0.0
            record.is_invoice_deposit_return = False
            if credit_ids:
                residual_amt = sum(
                    [credit_inv.amount_residual for credit_inv in
                     credit_ids if credit_inv.amount_residual > 0.0])
                if residual_amt > 0.0:
                    record.is_invoice_deposit_return = False
                else:
                    record.is_invoice_deposit_return = True

    @api.depends('amount')
    def _compute_invoice_deposit_received(self):
        for record in self:
            deposit_ids = self.env['account.move'].search([
                ('rental_order_id', '=', record.id),
                ('move_type', '=', 'out_invoice'),
                ('state', 'in', ['posted']),
                ('is_deposit_invoice', '=', True)
            ])
            residua_amt = 0.0
            record.invoice_deposit_received = False
            if deposit_ids:
                residua_amt = sum(
                    [dp_inv.amount_residual for dp_inv in
                     deposit_ids if dp_inv.amount_residual > 0.0])
                if residua_amt > 0.0:
                    record.invoice_deposit_received = False
                else:
                    record.invoice_deposit_received = True

    def action_deposite_return(self):
        for record in self:
            deposit_ids = self.env["account.move"].search(
                [
                    ("rental_order_id", "=", record.id),
                    ("state", "in", ("draft", "posted")),
                    ("payment_state", "!=", "paid"),
                ]
            )
            if deposit_ids:
                raise UserError(
                    _(
                        "Deposit Return invoice is already Pending\n"
                        "Please proceed that Return invoice first"
                    )
                )
            self.ensure_one()
            purch_journal = record.env["account.journal"].search(
                [("type", "=", "sale")], limit=1
            )
            invoice_line_value = {
                "name": "Deposit Return" or "",
                "quantity": 1,
                "account_id": False,
                "price_unit": record.amount or 0.00,
            }
            invoice_id = record.env["account.move"].create(
                {
                    "invoice_origin": "Deposit Return For" + record.name or "",
                    "move_type": "out_refund",
                    "branch_id": record.branch_id.id,
                    "partner_id": record.partner_id.id or False,
                    "invoice_line_ids": [(0, 0, invoice_line_value)],
                    "invoice_date": fields.Date.today() or False,
                    "rental_order_id": record.id,
                    "is_deposit_return_invoice": True,
                    "journal_id": purch_journal and purch_journal.id or False,
                }
            )
            record.write({"invoice_id": invoice_id.id})
        return True

    def action_deposite_receive(self):
        for record in self:
            if record.amount < 1:
                raise UserError(
                    _(
                        "Deposit amount should not be zero.\n"
                        "Please Enter Deposit Amount."
                    )
                )
            deposit_ids = self.env["account.move"].search(
                [
                    ("rental_order_id", "=", record.id),
                    ("payment_state", "!=", "paid"),
                    ("state", "in", ("draft", "posted")),
                ]
            )
            if deposit_ids:
                raise UserError(
                    _(
                        "Deposit invoice is already Pending\n"
                        "Please proceed that deposit invoice first"
                    )
                )
            invoice_line = {
                "name": "Deposit Receive" or "",
                "quantity": 1,
                "price_unit": record.amount or 0.00,
            }
            invoice_id = record.env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "branch_id": record.branch_id.id,
                    "partner_id": record.partner_id.id or False,
                    "invoice_line_ids": [(0, 0, invoice_line)],
                    "invoice_date": fields.Date.today() or False,
                    "rental_order_id": record.id,
                    "is_deposit_invoice": True,
                }
            )
            record.write({"invoice_id": invoice_id.id, "is_hide_deposit": True})
            return True

    @api.onchange(
        "rental_initial",
        "rental_initial_type",
        "start_date",
        "rental_bill_freq",
        "rental_bill_freq_type",
        "is_reccuring_invoice",
    )
    def _onchange_rental_initial_type(self):
        for rental in self:
            internal = rental.rental_initial or 0
            if rental.rental_initial_type == "days" and rental.start_date:
                rental.end_date = rental.start_date + relativedelta(days=internal)
            elif rental.rental_initial_type == "weeks" and rental.start_date:
                rental.end_date = rental.start_date + relativedelta(days=7 * internal)
            elif rental.rental_initial_type == "months" and rental.start_date:
                rental.end_date = rental.start_date + relativedelta(months=internal)
            elif rental.rental_initial_type == "years" and rental.start_date:
                rental.end_date = rental.start_date + relativedelta(years=internal)
            if rental.rental_initial_type == "hours":
                rental.rental_bill_freq_type = "days"
                if rental.start_date:
                    rental.end_date = rental.start_date + relativedelta(hours=internal)
            rental.final_end_date = rental.end_date
            self.onchange_rental_product_lines(internal)

    def onchange_rental_product_lines(self, internal):
        rit = self.rental_initial_type
        for line in self.rental_line:
            if rit == 'hours':
                line.price_unit = line.product_id.rent_per_hour * self.rental_initial 
            elif rit == 'days':
                line.price_unit = line.product_id.rent_per_day * self.rental_initial
            elif rit == 'weeks':
                line.price_unit = line.product_id.rent_per_week * self.rental_initial
            elif rit == 'months':
                line.price_unit = line.product_id.rent_per_month * self.rental_initial
            elif rit == 'years':
                line.price_unit = line.product_id.rent_per_year * self.rental_initial

    @api.constrains('rental_line')
    def check_serial_numbers(self):
        for rental in self:
            assigned_lot_ids = [line.lot_id.id for line in rental.rental_line if line.lot_id]
            if len(assigned_lot_ids) != len(set(assigned_lot_ids)):
                raise ValidationError("You are not allowed to select the same Serial Number")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("company_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("branch_id", "in", context.get("allowed_branch_ids")),
                ("branch_id", "=", False),
            ]

        result = super(RentalOrder, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain.extend([("company_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("branch_id", "in", context.get("allowed_branch_ids")),
                    ("branch_id", "=", False),
                ]
            )
        return super(RentalOrder, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )

    def get_initial_terms(self):
        initial_terms = 0

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

        for record in self:
            initial_terms = (
                record.rental_initial * conversion_factors[record.rental_initial_type][record.rental_bill_freq_type]
            )

        return initial_terms


class RantalOrderLine(models.Model):
    _inherit = 'rental.order.line'

    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids
    
    @api.model
    def domain_warehouse(self):
        return [('company_id','=', self.env.company.id)]

    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
    product_id = fields.Many2one('product.product', string='Product', domain=[('rent_ok', '=', True)], required=True)
    lot_avail_ids = fields.Many2many('stock.production.lot',compute='_compute_lot_avail_ids')
    com_avail = fields.Char(default="Avail")
    is_single_delivery_address = fields.Boolean(string="Single Destination", related='rental_id.is_single_delivery_address')
    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        help="Delivery address for current sales order.",
        tracking=True
    )
    partner_shipping_id_new = fields.Many2one(
        comodel_name='res.partner',
        string='Delivery Address',
        related='partner_shipping_id',
        store=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        related='rental_id.partner_id'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='rental_id.company_id'
    )
    branch_id = fields.Many2one(
        comodel_name='res.branch',
        string='Branch',
        related='rental_id.branch_id'
    )

    @api.model
    def default_get(self, fields):
        res = super(RantalOrderLine, self).default_get(fields)
        if self.is_single_delivery_address:
            res.update({
                'partner_shipping_id_new' : self.rental_id.partner_shipping_id.id
            })

        return res
    
    def _prepare_procurement_values_custom(self, group_id=False):
        """ Prepare specific key for moves or other components that will be created from a procurement rule
        comming from a sale order line. This method could be override in order to add other custom key that could
        be used in move/po creation.
        """
        values = {}
        self.ensure_one()
        date_planned = self.rental_id.date_order
        values.update({
            'group_id': group_id,
            'rental_line_id': self.id,
            'date_planned': date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'warehouse_id': self.rental_id.warehouse_id or False,
            'lot_id': self.lot_id.id,
            'for_rental_move': True,
            'partner_shipping_id': self.rental_id.partner_shipping_id.id or False,
            'branch_id': self.branch_id.id
        })

        if not self.rental_id.is_single_delivery_address:
            values.update(
                {
                    'partner_shipping_id': self.partner_shipping_id_new.id
                }
            )

        return values

    def _action_launch_procurement_rule_custom(self):
        """
        This function overrides from browseinfo_rental_management.
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        temp_list = []
        line_list_vals = []

        for line in self:
            if {'partner_shipping_id': line.partner_shipping_id.id} in temp_list:
                filter_line = list(
                    filter(lambda r: r.get('partner_shipping_id') == line.partner_shipping_id.id, line_list_vals)
                )
                if filter_line:
                    filter_line[0]['lines'].append(line)
            else:
                temp_list.append({'partner_shipping_id': line.partner_shipping_id.id})
                line_list_vals.append({
                    'partner_shipping_id': line.partner_shipping_id.id,
                    'lines': [line]
                })

        for value in line_list_vals:
            procurements = []
            group_id = False

            lines = value.get('lines')
            # Create a single group_id if there are multiple lines for the same partner_shipping_id
            if len(lines) > 1:
                group_id = self.env['procurement.group'].create({
                    'name': lines[0].rental_id.name,
                    'move_type': 'direct',
                    'rental_id': lines[0].rental_id.id,
                    'partner_id': lines[0].rental_id.partner_id.id,
                })

            for line in lines:
                if not line.product_id.type in ('consu', 'product', 'asset'):
                    continue

                qty = 0.0

                # If there is only one line, create a new group_id for each line
                if len(lines) == 1:
                    group_id = self.env['procurement.group'].create({
                        'name': line.rental_id.name,
                        'move_type': 'direct',
                        'rental_id': line.rental_id.id,
                        'partner_id': line.rental_id.partner_id.id,
                    })

                line.rental_id.procurement_group = group_id
                values = line._prepare_procurement_values_custom(group_id=group_id)
                product_qty = line.product_uom_qty - qty

                procurements.append(self.env['procurement.group'].Procurement(
                    line.product_id,
                    product_qty,
                    line.product_id.uom_id,
                    line.rental_id.partner_id.property_stock_customer,
                    line.product_id.name,
                    line.rental_id.name,
                    line.rental_id.company_id,
                    values
                ))

            if procurements:
                self.env['procurement.group'].run(procurements)

        return True

    
    @api.depends('com_avail')
    def _compute_lot_avail_ids(self):
        for data in self:
            if data.com_avail:
                stock_quant = self.env['stock.quant'].sudo().search([('on_hand','=',True)]).filtered(lambda line:line.available_quantity >0 and line.lot_id)
                if stock_quant:
                    data.lot_avail_ids = [(6,0,[lot.lot_id.id for lot in stock_quant])]
                else:
                    data.lot_avail_ids = False
            else:
                data.lot_avail_ids = False
                
    

    def check_price_unit(self, hours, days, weeks, months, rental_bill_freq_type):
        if rental_bill_freq_type == 'hours':
            return self.price_unit / hours
        if rental_bill_freq_type == 'days':
            return self.price_unit / days
        if rental_bill_freq_type == 'weeks':
            return self.price_unit / weeks
        if rental_bill_freq_type == 'months':
            return self.price_unit / months

class ReplaceNewProductLine(models.Model):
    _inherit = "replace.new.product.line"
    _description = "Replace New Product Line"

    lot_avail_ids = fields.Many2many('stock.production.lot',compute='_compute_lot_avail_ids')
    
    @api.depends('product_id')
    def _compute_lot_avail_ids(self):
        for data in self:
            if data.product_id:
                stock_quant = self.env['stock.quant'].sudo().search([('on_hand','=',True),('product_id','=',data.product_id.id)]).filtered(lambda line:line.available_quantity >0 and line.lot_id)
                if stock_quant:
                    data.lot_avail_ids = [(6,0,[lot.lot_id.id for lot in stock_quant])]
                else:
                    data.lot_avail_ids = False
            else:
                data.lot_avail_ids = False
