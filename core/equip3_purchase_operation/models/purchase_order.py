# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from concurrent.futures import process

from odoo import tools
from odoo import api, fields, models, SUPERUSER_ID, tools, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date
from odoo.http import request
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, float_compare
import pytz
from pytz import timezone, UTC
import requests
from odoo.tools.float_utils import float_is_zero, float_round
from itertools import groupby
from datetime import datetime, date
import logging
import json

from lxml import etree
import json as simplejson
import time
from odoo.addons.purchase_stock.models.purchase import PurchaseOrderLine as BasicPurchaseOrderLine
from odoo.addons.equip3_approval_hierarchy.models.approval_hierarchy import ApprovalHierarchy

_logger = logging.getLogger(__name__)

headers = {'content-type': 'application/json'}

class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def create(self, vals):
        if vals.get('model') and \
            vals.get('model') == 'purchase.request' and vals.get('tracking_value_ids'):
            purchase_req_1 = self.env['ir.model.fields']._get('purchase.request', 'purchase_req_state_1').id
            purchase_req_2 = self.env['ir.model.fields']._get('purchase.request', 'purchase_req_state_2').id
            pr_state = self.env['ir.model.fields']._get('purchase.request', 'pr_state').id
            vals['tracking_value_ids'] = [rec for rec in vals.get('tracking_value_ids') if
                                        rec[2].get('field') not in (purchase_req_1, purchase_req_2, pr_state)]
        if vals.get('model') and \
            vals.get('model') == 'purchase.order' and vals.get('tracking_value_ids'):
            state1 = self.env['ir.model.fields']._get('purchase.order', 'state1').id
            po_state = self.env['ir.model.fields']._get('purchase.order', 'po_state').id
            vals['tracking_value_ids'] = [rec for rec in vals.get('tracking_value_ids') if
                                        rec[2].get('field') not in (state1, po_state)]
        return super(MailMessage, self).create(vals)

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    origin = fields.Text('Source Document', copy=False,
                         help="Reference of the document that generated this purchase order "
                              "request (e.g. a sales order)")

    product_receive_qty = fields.Boolean("Product Receive Qty")

    # OVERRIDER Purchase TOOLS/ sh_purchase_order_history
    #All Lines Reorder Button
    def action_all_purchase_reorder(self):
        if any(rec.state == 'purchase' for rec in self):
            raise ValidationError(_("You Cannot Reorder which state is purchase order"))
        order_history = self.env["purchase.order.history"].search(
            [("order_id", "=", self.id)])
        if all(not order.purchase_reorder for order in order_history):
            for rec in order_history:
                vals = {"price_unit": rec.price_unit,
                        "product_qty": rec.product_qty,
                        "price_subtotal": rec.price_subtotal,
                        "date_planned": fields.Datetime.now(),
                        "analytic_tag_ids": [(6,0,rec.order_id.analytic_account_group_ids.ids)],
                        }
                if rec.product_id:
                    vals.update({"name": rec.product_id.display_name,
                                "product_id": rec.product_id.id})

                if rec.product_uom:
                    vals.update({"product_uom": rec.product_uom.id})

                if rec.order_id:
                    vals.update({"order_id": rec.order_id.id,
                                "analytic_tag_ids": [(6,0,rec.order_id.analytic_account_group_ids.ids)],
                                })
                rec.order_id.write({"order_line": [(0, 0, vals)]})
                self._cr.commit()
        else:
            for rec in order_history:
                if rec.purchase_reorder:
                    vals = {"price_unit": rec.price_unit,
                            "product_qty": rec.product_qty,
                            "price_subtotal": rec.price_subtotal,
                            "date_planned": fields.Datetime.now(),
                            }
                    if rec.product_id:
                        vals.update({"name": rec.product_id.display_name,
                                    "product_id": rec.product_id.id})

                    if rec.product_uom:
                        vals.update({"product_uom": rec.product_uom.id})

                    if rec.order_id:
                        vals.update({"order_id": rec.order_id.id,
                                    "analytic_tag_ids": [(6,0,rec.order_id.analytic_account_group_ids.ids)],
                                    })
                    rec.order_id.write({"order_line": [(0, 0, vals)]})
                    self._cr.commit()

        return {"type": "ir.actions.client", "tag": "reload"}
        
    # OVERRIDE _get_invoiced | basic/purchase
    # @api.depends('state', 'order_line.qty_to_invoice')
    # def _get_invoiced(self):
    #     precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    #     for order in self:
    #         if order.state not in ('purchase', 'done'):
    #             order.invoice_status = 'no'
    #             continue
    #
    #         lines = order.order_line.filtered(lambda x: x.product_id.purchase_method == 'receive')
    #         is_break = False
    #         if lines:
    #             order.product_receive_qty = True
    #             for line in lines:
    #                 if line.qty_received != line.product_qty:
    #                     order.invoice_status = 'to invoice'
    #                     is_break = True
    #                     break
    #         if is_break:
    #             break
    #         if any(
    #             not float_is_zero(line.qty_to_invoice, precision_digits=precision)
    #             for line in order.order_line.filtered(lambda l: not l.display_type)
    #         ):
    #             order.invoice_status = 'to invoice'
    #         elif (
    #             all(
    #                 float_is_zero(line.qty_to_invoice, precision_digits=precision)
    #                 for line in order.order_line.filtered(lambda l: not l.display_type)
    #             )
    #             and any(inv.state == 'draft' for inv in order.invoice_ids)
    #         ):
    #             order.invoice_status = 'to invoice'
    #         elif (
    #             all(
    #                 float_is_zero(line.qty_to_invoice, precision_digits=precision)
    #                 for line in order.order_line.filtered(lambda l: not l.display_type)
    #             )
    #             and all(inv.state == 'posted' for inv in order.invoice_ids)
    #         ):
    #             order.invoice_status = 'invoiced'
    #         else:
    #             order.invoice_status = 'no'

    # OVERRIDER Purchase TOOLS/ sh_purchase_order_history
    @api.model
    @api.onchange("partner_id")
    def _onchange_partner(self):
        context = dict(self.env.context or {})
        self.order_history_line = None
        if self.partner_id:
            limit = self.env.user.company_id.sh_purchase_configuration_limit
            domain_query = "partner_id = %s and state = 'purchase'" % self.partner_id.id
            order = "date_order desc"
            if context.get('goods_order'):
                domain_query += "AND is_goods_orders = True"
            elif context.get('services_good'):
                domain_query += "AND is_services_orders = True"
            elif context.get('assets_orders'):
                domain_query += "AND is_assets_orders = True"
            elif context.get('rentals_orders'):
                domain_query += "AND is_rental_orders = True"
            query = """
                SELECT id
                FROM purchase_order
                WHERE {} ORDER BY {} LIMIT {}
            """
            self.env.cr.execute(query.format(domain_query,order,limit))
            purchase_order_search = self.env.cr.dictfetchall()
            if purchase_order_search:
                self.env.cr.execute("""
                    SELECT p.name,l.id,l.product_id,l.price_unit,l.product_qty,l.product_uom,l.price_subtotal
                    FROM purchase_order_line as l
                    INNER JOIN purchase_order as p
                    ON l.order_id = p.id
                    WHERE p.id in %s
                """, [tuple([(v['id']) for v in purchase_order_search])])
                purchase_line_search = self.env.cr.dictfetchall()
                purchase_order_line = []
                for rec in purchase_line_search:
                    purchase_order_line.append((0, 0, {
                        "po_id": rec['name'],
                        "name": rec['id'],
                        "product_id": rec['product_id'],
                        "price_unit": rec['price_unit'],
                        "product_qty": rec['product_qty'],
                        "product_uom": rec['product_uom'],
                        "price_subtotal": rec['price_subtotal']
                    }))

                self.order_history_line = purchase_order_line


    def _default_date(self):
        for rec in self:
            if rec.is_assets_orders:
                rec.date_order = rec.date_order_assets
            elif rec.is_services_orders and rec.create_date:
                rfq_exp_date_services = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_services')
                # rfq_exp_date_services = self.env.company.rfq_exp_date_services
                rec.date_order = rec.create_date + timedelta(days=int(rfq_exp_date_services))
            elif rec.create_date:
                rfq_exp_date_goods = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_goods')
                # rfq_exp_date_goods = self.env.company.rfq_exp_date_goods
                rec.date_order = rec.create_date + timedelta(days=int(rfq_exp_date_goods))

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False

    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        domain=lambda self: "[('id', 'in', %s), ('company_id','=', company_id)]" % self.env.branches.ids,
        default = _default_branch,
        readonly=False)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, states=READONLY_STATES,
        default=lambda self: self.env.company.currency_id.id, tracking=True)
    po_expiry_date = fields.Datetime('PO Expiry Date', tracking=True)
    po = fields.Boolean('PO')
    exp_po = fields.Boolean('EXP PO')
    sent = fields.Boolean(string='Sent')
    is_goods_orders = fields.Boolean(string="Goods Orders", default=False, store=True)
    is_services_orders = fields.Boolean(string="Services Orders", default=False, store=True)
    is_hold_purchase_order = fields.Boolean(compute="_compute_hold_purchase_order", string="Hold Purchase Order", store=False)
    approval_matrix_id = fields.Many2one('approval.matrix.purchase.order', compute="_compute_approval_matrix_id", string="Approval Matrix", store=True)
    is_approval_matrix = fields.Boolean(compute="_compute_approval_matrix", string="Approving Matrix", store=False)
    state = fields.Selection(selection_add=[
        ('waiting_for_approve', 'Waiting For Approval'),
        ('rfq_approved', 'RFQ Approved'),
        ('purchase', 'Purchase Order'),
        ('reject', 'Rejected'),
        ('done', 'Locked'),
        ('on_hold', 'On Hold'),
        ('cancel','Cancel'),
        ('closed','Closed')
        ])
    state1 = fields.Selection(related="state")
    po_state = fields.Selection(related="state")
    approved_matrix_ids = fields.One2many('approval.matrix.purchase.order.line', 'order_id', compute="_compute_approving_matrix_lines", store=True, string="Approved Matrix")
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.purchase.order.line', string='Purchase Order Approval Matrix Line', compute='_get_approve_button', store=False)
    def _domain_analytic_group(self):
        return [('company_id','=',self.env.company.id)]
    analytic_account_group_ids = fields.Many2many('account.analytic.tag', string='Analytic Group',domain=_domain_analytic_group)
    company_id = fields.Many2one(readonly=True)
    # branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    destination_location_id = fields.Many2one('stock.location', string='Destination Location')
    is_delivery_receipt = fields.Boolean(string="Delivery With Receipt Date")
    date_planned = fields.Datetime(inverse='_inverse_date_planned', string='Expected Date', compute='')
    destination_warehouse_id = fields.Many2one('stock.warehouse', string='Destination', copy=True)
    discount_type = fields.Selection(string='Discount Type')
    is_single_delivery_destination = fields.Boolean(string="Single Delivery Destination")
    analytic_accounting = fields.Boolean("Analyic Account", compute="get_analytic_accounting", store=True)
    is_revision_po = fields.Boolean(string="Revison PO")
    is_revision_created = fields.Boolean(string='Revison Created', copy=False)
    revision_order_id = fields.Many2one('purchase.order', string='Revison Order')
    # The revision order is archived, so the relation is always false; just store the ID.
    int_revision_order_id = fields.Integer(string='ID Revision Order')
    custom_checklist_template_ids = fields.Many2many(
        'purchase.custom.checklist.template', 'purchase_checklist_rel', 'order_id', 'checlist_id')
    readonly_price = fields.Boolean("Readonly Price", compute='compute_retail')
    timezone_date = fields.Char(compute="_compute_timezone_date", store=True, string='Date')
    request_partner_id = fields.Many2one('res.partner', string='Requesting Partner')
    # date_order_goods = fields.Datetime(compute='_compute_date_order_goods', string="RFQ Expiry Date", default=fields.Datetime.now())
    # date_order_services = fields.Datetime(compute='_compute_date_order_services', string="RFQ Expiry Date", default=fields.Datetime.now())
    date_order_assets = fields.Datetime(string="RFQ Expiry Date", default=fields.Datetime.now())
    name2 = fields.Char(string="RFQ Reference", readonly="1")
    date_order = fields.Datetime(string="RFQ Expiry Date", default=_default_date, tracking=True)
    is_assets_orders = fields.Boolean(string="Assets Orders", default=False)

    milestone_template_id = fields.Many2one(comodel_name='milestone.contract.template', string='Milestone and Contract Terms', tracking=True)
    milestone_purchase_ids = fields.One2many(comodel_name='milestone.contract.template.purchase', inverse_name='purchase_order_id', string='Milestone and Contract Term Line')
    is_group_good_services_order = fields.Boolean(string='is_good_service_order', compute="_compute_is_group_good_services_order")
    have_product_service = fields.Boolean(string='Have product service', compute="_compute_have_product_service")
    swo_ids = fields.One2many(comodel_name='service.work.order', inverse_name='purchase_order_id', string='Service Work Order')
    swo_count = fields.Integer(string='SWO Count', compute="_compute_swo_count")
    is_taxes = fields.Boolean(compute="_compute_taxes", store=False, string="Taxes Type")
    actual_progress = fields.Char(string='Actual Progress', compute="_compute_swo_progress", store=True)
    remaining_progress = fields.Char(string='Remaining Progress (%)', compute="_compute_swo_progress", store=True)
    progress_paid = fields.Float(string='Progress Paid (%)', compute="_compute_swo_progress", store=True)
    paid_swo = fields.Float(string='SWO Paid')

    partner_invoice_id = fields.Many2one(comodel_name='res.partner', string='Vendor Bill Address', required=True,domain="[('id','in',available_partner_invoice_ids)]", tracking=True)
    available_partner_invoice_ids = fields.Many2many(comodel_name='res.partner', string='Available Bill Address', compute="_compute_available_partner_invoice_ids")

    product_brand_ids = fields.Many2many(comodel_name='product.brand', string='Brand')
    is_product_brand_filter = fields.Boolean(string='Is Product Brand Filter', compute="_compute_is_product_brand_filter")
    is_service_work_order = fields.Boolean(string='Is Service Work Order', compute="_compute_is_service_work_order")
    is_purchase_vendor_rating_warning = fields.Boolean(string='Purchase Vendor Rating Warning', compute="_compute_vendor_rating_warning")
    is_product_service_operation_receiving = fields.Boolean(string="Product Service Operation Receiving", compute="_compute_service_receiving", store=True)
    is_service = fields.Boolean('Service')
    show_analytic_tags = fields.Boolean("Show Analytic Tags", compute="compute_analytic_tags", store=True)
    client_order_ref = fields.Char(string='Reference')

    amount_untaxed = fields.Monetary(string='Total Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=True)
    amount_tax = fields.Monetary(string='Total Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Grand Total', store=True, readonly=True, compute='_amount_all')

    discount_amt_before = fields.Monetary(related="discount_amt", string='- Discount', store=True, readonly=True)
    discount_amt_line_before = fields.Float(related="discount_amt_line", string='- Line Discount', digits='Line Discount', store=True, readonly=True)
    amount_subtotal = fields.Monetary(compute='_amount_all', string='Subtotal', store=True, readonly=True)
    tax_discount_policy = fields.Char(string="Tax Applies on",
                           default=lambda self: self.env.company.tax_discount_policy)
    log_po = fields.Boolean(string="Log Purchase Order", compute='_compute_log_po')
    approver_ids = fields.Many2many('res.users', 'approver_pr_rel', 'approver_id', 'pr_id', string="Approver", compute='_compute_approver_ids', store=True)
    down_payment_amount_percentage = fields.Float(string='Down Payment (%)', compute='_compute_down_payment_amount', store=True)
    revision_reference_id = fields.Many2one('purchase.order', 'Revision Reference')
    hide_milestone = fields.Boolean(compute='_compute_hide_milestone')
    sh_purchase_revision_config = fields.Boolean("Enable Purchase Revisions")

    @api.depends('order_line', 'order_line.is_down_payment', 'order_line.price_unit')
    def _compute_down_payment_amount(self):
        res = super()._compute_down_payment_amount()
        for record in self:
            record.down_payment_amount_percentage = (record.down_payment_amount / record.amount_total) * 100 if record.amount_total else 100
        return res

    @api.depends('state','approved_matrix_ids','approved_matrix_ids.approved')
    def _compute_approver_ids(self):
        for record in self:
            approver_ids = []
            for line in record.approved_matrix_ids:
                approver_ids.extend(line.user_ids.ids)
            record.approver_ids = [(6,0,approver_ids)]

    @api.depends('order_line.product_id')
    def _compute_hide_milestone(self):
        categ_reward_id = self.env.ref('equip3_sale_promo_coupon.product_category_product_rewards').id
        discount_products = self.env['coupon.program'].sudo().search([]).mapped('discount_line_product_id')
        for order in self:
            hide = False
            for line in order.order_line:
                if line.product_id.type == 'service' and (
                        line.product_id.categ_id.id == categ_reward_id or line.product_id in discount_products):
                    hide = True
                    break
            order.hide_milestone = hide
            if hide:
                order.is_service_work_order = False
                order.have_product_service = False


    def _compute_log_po(self):
        for rec in self:
            rec.log_po = self.env['ir.config_parameter'].sudo().get_param('log_po')
            # rec.log_po = self.env.company.log_po


    @api.depends('order_line.move_ids')
    def _compute_picking(self):
        for order in self:
            pickings = self.env['stock.picking']
            for line in order.order_line.filtered(lambda x: x.move_ids):
                # We keep a limited scope on purpose. Ideally, we should also use move_orig_ids and
                # do some recursive search, but that could be prohibitive if not done correctly.
                moves = line.move_ids | line.move_ids.mapped('returned_move_ids')
                moves = moves.filtered(lambda r: r.state != 'cancel')
                pickings |= moves.mapped('picking_id')
            order.picking_ids = pickings
        for order in self:
            if order.merged:
                for a in self.env['stock.picking'].search([]):
                    if a.purchase_ids:
                        for b in a.purchase_ids:
                            if order.id == b.id:
                                order.picking_ids = [(4, a.id)]
        for order in self:
            order.picking_count = len(order.picking_ids)

    @api.onchange('branch_id','company_id')
    def set_warehouse_id(self):
        for res in self:
            # stock_warehouse = res.env['stock.warehouse'].search([('company_id', '=', res.company_id.id),('branch_id', '=', res.branch_id.id)], order="id", limit=1)
            stock_warehouse = False
            allowed_warehouse_ids = self.env.user.warehouse_ids.ids
            if not allowed_warehouse_ids:
                raise ValidationError("You need to set up the allowed warehouse.")
            if res.company_id and res.branch_id:
                self.env.cr.execute("""
                        SELECT id
                        FROM stock_warehouse
                        WHERE company_id = %s AND branch_id = %s AND id in (%s) AND active = True ORDER BY id LIMIT 1
                    """ % (res.company_id.id, res.branch_id.id, str(allowed_warehouse_ids)[1:-1]))
                stock_warehouse = self.env.cr.fetchall()
            res.destination_warehouse_id = stock_warehouse[0][0] if stock_warehouse else False

    @api.onchange('is_single_delivery_destination')
    def _onchange_is_single_delivery_destination(self):
        for record in self:
            if record.is_single_delivery_destination:
                stock_warehouse = False
                if record.company_id and record.branch_id:
                    self.env.cr.execute("""
                        SELECT id
                        FROM stock_warehouse
                        WHERE company_id = %s AND branch_id = %s AND active = True ORDER BY sequence LIMIT 1
                    """ % (record.company_id.id, record.branch_id.id))
                    stock_warehouse = self.env.cr.fetchall()
                # stock_warehouse = record.env['stock.warehouse'].search([('company_id', '=', record.company_id.id),('branch_id', '=', record.branch_id.id)], order="id", limit=1)
                record.destination_warehouse_id = stock_warehouse[0][0] if stock_warehouse else False
            if record.is_single_delivery_destination and record.destination_warehouse_id:
                for line in record.order_line:
                    line.picking_type_id = record.destination_warehouse_id.in_type_id.id

    @api.depends('company_id')
    def compute_analytic_tags(self):
        for rec in self:
            rec.show_analytic_tags = self.env['ir.config_parameter'].sudo().get_param('group_analytic_tags')

    @api.depends('is_services_orders')
    def _compute_service_receiving(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        for rec in self:
            if rec.is_services_orders:
                rec.is_product_service_operation_receiving = IrConfigParam.get_param('is_product_service_operation_receiving', False)
                # rec.is_product_service_operation_receiving = self.env.company.is_product_service_operation_receiving

    @api.depends('partner_id')
    def _compute_vendor_rating_warning(self):
        for i in self:
            is_purchase_vendor_rating_warning = bool(self.env['ir.config_parameter'].sudo().get_param('is_purchase_vendor_rating_warning'))
            # is_purchase_vendor_rating_warning = self.env.company.is_purchase_vendor_rating_warning
            if is_purchase_vendor_rating_warning and (i.visible_eval and int(i.visible_eval)<3):
                i.is_purchase_vendor_rating_warning = True
            else:
                i.is_purchase_vendor_rating_warning = False


    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault("date_order", self.date_order)
        if self.is_revision_po:
            default.setdefault("origin", self.origin)
        default.setdefault("exp_po", False)
        res = super(PurchaseOrder, self).copy(default)
        return res

    def action_extract(self):
        res = super(PurchaseOrder, self).action_extract()
        return{
            'name': 'Extract RFQ',
            'res_model': 'extract.rfq.wizard',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'target': 'new'
        }
        return res

    @api.depends('partner_id')
    def _compute_is_product_brand_filter(self):
        for i in self:
            i.is_product_brand_filter = bool(self.env['ir.config_parameter'].sudo().get_param('is_product_brand_filter'))
            # i.is_product_brand_filter = self.env.company.is_product_brand_filter


    @api.depends('partner_id')
    def _compute_is_service_work_order(self):
         for i in self:
            i.is_service_work_order = bool(self.env['ir.config_parameter'].sudo().get_param('is_service_work_order'))
            # i.is_service_work_order = self.env.company.is_service_work_order

    @api.onchange('partner_id')
    def _onchange_partner_invoice_id(self):
        available_partner_invoice = False
        if self.partner_id:
            vendor = self.partner_id
            child_invoice_ids = vendor.child_ids.filtered(lambda p:p.type == 'invoice')
            if child_invoice_ids:
                default_partner_invoice_id = child_invoice_ids[0]
            else:
                default_partner_invoice_id = vendor
            available_partner_invoice = vendor.ids + child_invoice_ids.ids
            self.partner_invoice_id = default_partner_invoice_id
            domain = {
                    'partner_invoice_id':[('id','in',available_partner_invoice)],
                    }
        else:
            domain = {
                    'partner_invoice_id':[('id','in',available_partner_invoice)],
                    }
        return {'domain':domain}

    @api.depends('partner_id')
    def _compute_available_partner_invoice_ids(self):
        for rec in self:
            available_partner_invoice = []
            if rec.partner_id:
                vendor = rec.partner_id
                child_invoice_ids = vendor.child_ids.filtered(lambda p:p.type == 'invoice')
                available_partner_invoice = vendor.ids + child_invoice_ids.ids
            rec.available_partner_invoice_ids = [(6,0,[])]
            rec.available_partner_invoice_ids = [(6,0,available_partner_invoice)]

    # OVERRIDE from addons dev_purchase_down_payment
    def action_create_invoice(self):
        context = dict(self.env.context) or {}
        self.env.context = context
        if context.get('down_payment'):
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

            # 1) Prepare invoice vals and clean-up the section lines
            invoice_vals_list = []
            for order in self:
                if order.invoice_status != 'to invoice' and context.get('down_payment_by') not in ('percentage', 'fixed'):
                    continue

                order = order.with_company(order.company_id)
                pending_section = None
                # Invoice values.
                invoice_vals = order._prepare_invoice()
                if order.partner_invoice_id:
                    invoice_vals.update({
                        'partner_id': order.partner_invoice_id.id,
                    })
                else:
                    invoice_vals.update({
                        'partner_id': self.partner_id.id,
                    })

                # Invoice line values (keep only necessary sections).
                if context.get('down_payment_by') not in ('percentage', 'fixed'):
                    for line in order.order_line:
                        if line.display_type == 'line_section':
                            pending_section = line
                            continue
                        if not float_is_zero(line.qty_to_invoice, precision_digits=precision) or line.is_down_payment:
                            if pending_section:
                                invoice_vals['invoice_line_ids'].append((0, 0, pending_section._prepare_account_move_line()))
                                pending_section = None
                            invoice_line_vals = line._prepare_account_move_line()
                            if line.is_down_payment:
                                invoice_line_vals.update({
                                    'tax_ids': [(6, 0, [])],
                                    'price_unit': - (line.price_unit),
                                    'is_down_payment': line.is_down_payment,
                                })
                            invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))
                else:
                    ICP = self.env['ir.config_parameter'].sudo()
                    product_id = self.env['product.product'].browse(int(ICP.get_param('down_payment_product_id')))
                    if not product_id:
                        product_id = self.env.ref('equip3_purchase_masterdata.down_payment_product_data').id
                    amount = 0
                    is_down_payment = False
                    if context.get('down_payment_by') == "percentage":
                        amount_untaxed = self.amount_total
                        # if self.discount_method == 'per':
                        #    amount_untaxed -= (amount_untaxed * self.discount_amount) / 100
                        # elif self.discount_method == 'fix':
                        #    amount_untaxed -= self.discount_amount
                        amount = round((amount_untaxed * context.get('amount', 0.0)) / 100, 2)
                        is_down_payment = True
                    elif context.get('down_payment_by') == "fixed":
                        amount = context.get('amount')
                        is_down_payment = True
                    if is_down_payment:
                        dp_line = order.order_line.filtered(lambda x: x.is_down_payment)
                        invoice_vals['is_down_payment'] = True
                        invoice_vals["invoice_line_ids"].append((0, 0, {
                            'product_id': product_id.id,
                            'name': product_id.display_name,
                            'quantity': 1,
                            'tax_ids': [(6, 0, [])],
                            'price_unit': amount,
                            'purchase_line_id': dp_line.id,
                            'purchase_order_id': order.id,
                            "is_down_payment": True,
                        }))

                invoice_vals_list.append(invoice_vals)

            # 2) group by (company_id, partner_id, currency_id) for batch creation
            new_invoice_vals_list = []
            for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

            # 3) Create invoices.
            moves = self.env['account.move']
            AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
            for vals in invoice_vals_list:
                vals.update({
                    'analytic_group_ids': [(6, 0, self.analytic_account_group_ids.ids)]
                })
                move = AccountMove.with_company(vals['company_id']).create(vals)
                move._compute_down_payment_amount()
                move._onchange_invoice_line_ids()
                if move.is_down_payment:
                    move._compute_down_payment_lines()
                move._check_down_payment_balance()
                moves |= move
                # dicomment agar bill dp tetap muncul pada smartbutton bill
                # self.env.context.update({
                #     'invoice_dp': moves.ids
                # })
                self._compute_invoice()
            # 4) Some moves might actually be refunds: convert them if the total amount is negative
            # We do this after the moves have been created since we need taxes, etc. to know if the total
            # is actually negative or not
            moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

            return self.action_view_invoice(moves)
        else:
            res = super(PurchaseOrder, self).action_create_invoice()
            self._compute_invoice()
            return res


    def hide_create_bill_status(self):
        res = super(PurchaseOrder, self).hide_create_bill_status()
        if self.paid_swo >= 100:
            self.hide_create_bill = True
        else:
            self.hide_create_bill = False
        # if self.product_receive_qty:
        #     for line in self.order_line:
        #         if line.product_id.purchase_method == 'receive':
        #             if line.qty_received != line.product_qty:
        #                 self.hide_create_bill = True
        if self.is_services_orders:
            work_orders = self.env['service.work.order'].search_count([
                ('purchase_order_id', '=', self.id),
                ('state', '=', 'done')
            ])
            if work_orders == 0:
                self.hide_create_bill = True
            else:
                self.hide_create_bill = False
        if sum(self.order_line.mapped('product_qty')) == sum(self.order_line.mapped('qty_invoiced')):
            self.hide_create_bill = True
        return res

    def action_dev_purchase_down_payment(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Bill',
            'view_mode': 'form',
            'res_model': 'purchase.down.payment',
            'context':{'purchase_id': self.id},
            'target': 'new'
        }

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        if 'partner_id' in res:
            res['partner_id']['options'] = {'no_create':True,'no_create_edit':True}
        if 'branch_id' in res:
            res['branch_id']['options'] = {'no_create':True,'no_create_edit':True}
        return res


    @api.model
    def fields_view_get(
            self,
            view_id=None,
            view_type="form",
            toolbar=False,
            submenu=False,
    ):
        try:
            res = super(PurchaseOrder, self).fields_view_get(
                view_id=view_id,
                view_type=view_type,
                toolbar=toolbar,
                submenu=submenu,
            )
        except:
            res = super(PurchaseOrder, self).fields_view_get(view_id=self.env.ref('sh_po_status.sh_inherit_view_purchase_order_filter').id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        doc = etree.XML(res['arch'])
        if view_type == 'form':
            for node in doc.xpath("//field"):
                if node.get("name") == 'origin':
                    print("yes")
                modifiers = simplejson.loads(node.get("modifiers", '{}'))  # Get current modifiers or empty dict if none
                if 'readonly' in modifiers:
                    # If readonly already exists, append the new condition to it
                    existing_condition = modifiers['readonly']
                    if isinstance(existing_condition, list):
                        # If it's already a complex condition (list), append using an OR ('|') if necessary
                        next = False
                        for i in modifiers['readonly']:
                            if i[0] == 'state':
                                if i[1] == 'in':
                                    i[2].append('closed')
                                    next = True
                                if i[1] == '=':
                                    i[1] = 'in'
                                    i[2] = [i[2],'closed']
                                    next = True
                        if existing_condition[0] != '|' and not next:
                            # Make it an OR condition if the first element isn't already '|'
                            modifiers['readonly'] = ['|'] + existing_condition
                        # Append the new condition
                        if not next:
                            modifiers['readonly'] += [['state', '=', 'closed']]
                    else:
                        if not modifiers['readonly']:
                            # If it's a simple condition, convert to a list and append
                            modifiers['readonly'] = ['|', existing_condition, ['state', '=', 'closed']]
                else:
                    # If readonly is not defined, set it as a new condition
                    modifiers['readonly'] = [['state', '=', 'closed']]
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def _compute_taxes(self):
        show_line_subtotals_tax_selection = self.env['ir.config_parameter'].sudo().get_param('show_line_subtotals_tax_selection', "tax_excluded")
        for record in self:
            record.is_taxes = True
            if show_line_subtotals_tax_selection == "tax_excluded":
                record.is_taxes = False

    @api.depends('swo_ids','order_line','order_line.progress_paid','order_line.remaining_progress','invoice_ids')
    def _compute_swo_progress(self):
        for rec in self:
            paid = 0
            if rec.swo_ids:
                progress_paid = sum(rec.order_line.mapped('progress_paid')) or 0
                actual_progress = progress_paid
                remaining_progress = sum(rec.order_line.mapped('remaining_progress')) or 0
                if len(rec.order_line) > 0:
                    rec.update({
                        'actual_progress': actual_progress / len(rec.order_line),
                    })
                else:
                    rec.update({
                        'actual_progress': "0%",
                    })
                if rec.invoice_ids:
                    res_inv = rec.invoice_ids.filtered(lambda x: x.swo)
                    for inv in res_inv:
                        percentage = 0
                        if inv.total_down_payment_amount:
                            percentage = (inv.total_down_payment_amount - inv.amount_residual) * 100 / inv.total_down_payment_amount
                        else:
                            percentage = (inv.amount_total - inv.amount_residual) * 100 / inv.amount_total
                        inv.swo_ids.update({
                            'progress_paid': percentage
                        })
                for swo in rec.swo_ids:
                    paid += swo.contract_term / 100 * swo.progress_paid
                    milestone = rec.milestone_purchase_ids.filtered(lambda r: r.name == swo.milestone_name)
                    if milestone:
                        milestone.progress_paid = swo.progress_paid
            rec.progress_paid = round(paid, 2)
            remaining = 100 - paid
            rec.remaining_progress = round(remaining, 2)

    @api.depends('swo_ids')
    def _compute_swo_count(self):
        for rec in self:
            rec.swo_count = len(rec.swo_ids)
            if rec.swo_count > 0:
                rec._compute_swo_progress()

    def _compute_is_group_good_services_order(self):
        for rec in self:
            rec.is_group_good_services_order = (self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') and self.is_services_orders == True) and True or False

    @api.depends('order_line','order_line.product_template_id','order_line.product_id')
    def _compute_have_product_service(self):
        for rec in self:
            rec.have_product_service = self.order_line.filtered(lambda x: x.product_id.type == 'service') or False

    @api.onchange('milestone_template_id')
    def _onchange_milestone_template_id(self):
        if self.milestone_purchase_ids:
            self.milestone_purchase_ids = [(5,0,0)]
        if self.milestone_template_id:
            milestone_purchase_ids = []
            for line in self.milestone_template_id.line_ids:
                vals = {
                    'name':line.name,
                    'checklist_template_id':line.checklist_template_id.id,
                    'contract_term':line.contract_term
                }
                milestone_purchase_ids.append((0,0,vals))
            self.milestone_purchase_ids = milestone_purchase_ids

    @api.constrains('milestone_purchase_ids')
    def _check_miletone_purchase(self):
        if not self.hide_milestone:
            if self.id != False and self.have_product_service and self.is_service_work_order and len(self.milestone_purchase_ids) < 1:
                # pass
                raise ValidationError(_("Milestone and Contract Term must have minimum 1 line"))

    def action_view_service_work_order(self):
        return {
                'type': 'ir.actions.act_window',
                'name': 'Service Work Order',
                'view_mode': 'tree,form',
                'res_model': 'service.work.order',
                'domain':[('purchase_order_id','=',self.id)]
            }

    def button_approve(self, force=False):
        res = super(PurchaseOrder, self).button_approve()
        for line in self.order_line:
            if not line.display_type:
                query_statement_2 = """UPDATE product_template set last_purchase_date = %s, last_purchase_price = %s, last_supplier_id = %s where id = %s"""
                self.sudo().env.cr.execute(query_statement_2, [line.date_order, line.price_unit_uom, line.partner_id.id, line.product_id.product_tmpl_id.id])
                query_statement = """UPDATE product_product set last_purchase_date = %s, last_purchase_price = %s, last_supplier_id = %s where id = %s"""
                self.sudo().env.cr.execute(query_statement, [line.date_order, line.price_unit_uom, line.partner_id.id, line.product_id.id])
        self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'purchase'})
        return res

    # def _compute_date_order(self):
    #     for rec in self:
    #         if rec.is_assets_orders:
    #             rec.date_order = rec.date_order_assets
    #         elif rec.is_services_orders:
    #             rec.date_order = rec.date_order_services
    #         else:
    #             rec.date_order = rec.date_order_goods
    #
    # def _compute_date_order_goods(self):
    #     rfq_exp_date_goods = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_goods')
    #     for record in self:
    #         record.date_order_goods = record.create_date + timedelta(days=int(rfq_exp_date_goods))
    #
    # def _compute_date_order_services(self):
    #     rfq_exp_date_services = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_services')
    #     for record in self:
    #         record.date_order_services = record.create_date + timedelta(days=int(rfq_exp_date_services))

    @api.depends('state')
    def _compute_timezone_date(self):
        for record in self:
            record.timezone_date = ""
            if record.state == 'purchase':
                timezone_date = record.date_approve
            else:
                timezone_date = record.create_date
            if timezone_date:
                deadline_timezone_date = pytz.timezone(self.env.user.tz or 'UTC')
                time_zone_date = timezone_date.replace(tzinfo=pytz.utc)
                time_zone_date = time_zone_date.astimezone(deadline_timezone_date).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                record.timezone_date = time_zone_date

    @api.model
    def retrieve_dashboard(self):
        res = super(PurchaseOrder, self).retrieve_dashboard()
        po = self.env['purchase.order']
        context = dict(self.env.context) or {}
        one_week_ago = fields.Datetime.to_string(fields.Datetime.now() - relativedelta(days=7))
        query = """SELECT AVG(COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total)),
                          AVG(extract(epoch from age(po.date_approve,po.create_date)/(24*60*60)::decimal(16,2))),
                          SUM(CASE WHEN po.date_approve >= %s THEN COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total) ELSE 0 END),
                          MIN(curr.decimal_places)
                   FROM purchase_order po
                   JOIN res_company comp ON (po.company_id = comp.id)
                   JOIN res_currency curr ON (comp.currency_id = curr.id)
                   WHERE po.state in ('purchase', 'done')
                    AND po.is_goods_orders = %s
                    AND po.company_id = %s
                """
        if context.get('goods_order'):
            res['all_to_send'] = po.search_count([('state', '=', 'draft'), ('is_goods_orders', '=', True)])
            res['my_to_send'] = po.search_count([('state', '=', 'draft'), ('user_id', '=', self.env.uid), ('is_goods_orders', '=', True)])
            res['all_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('is_goods_orders', '=', True)])
            res['my_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('user_id', '=', self.env.uid), ('is_goods_orders', '=', True)])
            res['all_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now()), ('is_goods_orders', '=', True)])
            res['my_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now()), ('user_id', '=', self.env.uid), ('is_goods_orders', '=', True)])
            self._cr.execute(query, (one_week_ago, True, self.env.company.id))
        elif context.get('services_good'):
            res['all_to_send'] = po.search_count([('state', '=', 'draft'), ('is_goods_orders', '=', False)])
            res['my_to_send'] = po.search_count([('state', '=', 'draft'), ('user_id', '=', self.env.uid), ('is_goods_orders', '=', False)])
            res['all_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('is_goods_orders', '=', False)])
            res['my_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('user_id', '=', self.env.uid), ('is_goods_orders', '=', False)])
            res['all_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now()), ('is_goods_orders', '=', False)])
            res['my_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now()), ('user_id', '=', self.env.uid), ('is_goods_orders', '=', False)])
        else:
            res['all_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now())])
            res['my_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('user_id', '=', self.env.uid)])
        if not context.get('goods_order'):
            self._cr.execute(query, (one_week_ago, False, self.env.company.id))
        values = self.env.cr.fetchone()
        res['all_avg_order_value'] = round(values[0] or 0, values[3])
        res['all_avg_days_to_purchase'] = round(values[1] or 0, 2)
        res['all_total_last_7_days'] = round(values[2] or 0, values[3])
        order_value = res['all_avg_order_value']
        res['all_avg_order_value'] = f'{order_value:,}'
        last_7_days = res['all_total_last_7_days']
        res['all_total_last_7_days'] = f'{last_7_days:,}'
        return res

    @api.depends('name')
    def compute_retail(self):
        for res in self:
            if self.env['ir.config_parameter'].sudo().get_param('retail') == 'True':
            # if self.env.company.retail:
                if not self.dp:
                    res.readonly_price = True
                else:
                    res.readonly_price = False
            else:
                res.readonly_price = False

    def action_quotation_send_wp(self):
        res = super(PurchaseOrder, self).action_quotation_send_wp()
        res['context'].update({'hide_send_button' : True})
        return res

    def sh_quotation_revision(self, default=None):
        if self:
            self.ensure_one()
            self.is_revision_created = True
            if default is None:
                default = {}
            if self.is_revision_po:
                po_count = self.search([("int_revision_order_id", '=', self.int_revision_order_id), ('is_revision_po', '=', True)])
            else:
                po_count = self.search([("int_revision_order_id", '=', self.id), ('is_revision_po', '=', True)])
            if 'name' not in default:
                default['state'] = 'draft'
                default['origin'] = self.name
                default['revision_reference_id'] = self.id
                default['sh_purchase_order_id'] = self.id
                default['is_revision_po'] = True
                default['po'] = False
                default['name2'] = False
                default['date_order'] = self.date_order if self.date_order >= fields.datetime.today() else fields.datetime.today()
                if self.is_delivery_receipt:
                    default['date_planned'] = self.date_planned if self.date_planned >= fields.datetime.today() else fields.datetime.today()

                if self.is_revision_po:
                    default['revision_order_id'] = self.revision_order_id.id
                    default['int_revision_order_id'] = self.revision_order_id.id
                else:
                    default['revision_order_id'] = self.id
                    default['int_revision_order_id'] = self.id
                default['is_revision_created'] = False
                self.sh_po_number += 1
            default['is_goods_orders'] = self.is_goods_orders
            date_planned = self.date_planned
            list_date_planned_line = []
            list_dest_warehouse_line = []
            for line in self.order_line:
                list_date_planned_line.append(line.date_planned if line.date_planned >= fields.datetime.today() else fields.datetime.today())
                list_dest_warehouse_line.append(line.destination_warehouse_id.id or False)
            new_purchase_id = self.with_context({'goods_order': self.is_goods_orders, 'services_order': self.is_services_orders, 'assets_orders': self.is_assets_orders,  'rentals_orders': self.is_rental_orders, 'is_revision_po': True, 'list_date_planned_line':list_date_planned_line, 'list_dest_warehouse_line': list_dest_warehouse_line}).copy(default=default)
            self.date_planned = date_planned
            # if name.startswith('RFQ'):
            #     new_purchase_id.name = name
            if self.is_revision_po:
                new_purchase_id.sh_revision_po_id = [(6, 0, self.revision_order_id.ids + po_count.ids)]
            else:
                new_purchase_id.sh_revision_po_id = [(6, 0, self.ids)]
        return self.open_quality_check()

    @api.model
    def action_purchase_order_menu(self):
        is_service_work_order = bool(self.env['ir.config_parameter'].sudo().get_param('is_service_work_order'))
        is_purchase_request_assign_user = bool(self.env['ir.config_parameter'].sudo().get_param('is_purchase_request_assign_user'))
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        # is_service_work_order = self.env.company.is_service_work_order
        # is_purchase_request_assign_user = self.env.company.is_purchase_request_assign_user
        is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
        is_pr_department = IrConfigParam.get_param('is_pr_department', False)
        po_action = self.env.ref('equip3_purchase_operation.action_approval_matrix_purchase_order')
        pr_action = self.env.ref('equip3_purchase_operation.action_approval_matrix_purchase_request')
        if is_pr_department and not is_good_services_order:
            pr_action.write({
                'context': {'department_invisible': False}
            })
        elif is_good_services_order and not is_pr_department:
            po_action.write({
                'context': {'order_type_invisible': False}
            })
            pr_action.write({
                'context': {'order_type_invisible': False}
            })
        elif is_good_services_order and is_pr_department:
            po_action.write({
                'context': {'order_type_invisible': False}
            })
            pr_action.write({
                'context': {'order_type_invisible': False, 'department_invisible': False}
            })
        else:
            po_action.write({
                'context': {'order_type_invisible': True}
            })
            pr_action.write({
                'context': {'order_type_invisible': True, 'department_invisible': True}
            })
        if is_good_services_order:
            self.env.ref("equip3_purchase_operation.menu_purchase_services_goods").active = True
            self.env.ref("purchase.menu_procurement_management").active = True
            self.env.ref("equip3_purchase_operation.menu_orders").active = False

        else:
            self.env.ref("equip3_purchase_operation.menu_purchase_services_goods").active = False
            self.env.ref("purchase.menu_procurement_management").active = False
            self.env.ref("equip3_purchase_operation.menu_orders").active = True

        if is_service_work_order:
            self.env.ref("equip3_purchase_operation.menu_services_purchase_service_work_order").active = True
            self.env.ref("equip3_purchase_operation.menu_swo_orders").active = True
            self.env.ref("equip3_purchase_operation.milestone_contract_template_menu_act").active = True
        else:
            self.env.ref("equip3_purchase_operation.menu_services_purchase_service_work_order").active = False
            self.env.ref("equip3_purchase_operation.menu_swo_orders").active = False
            self.env.ref("equip3_purchase_operation.milestone_contract_template_menu_act").active = False

        if self.is_purchase_request_assign_user:
            # self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_categ").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_assigned").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_not_assigned").active = True
            # self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_categ").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_assigned").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_not_assigned").active = True
            # self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_categ").active = True
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line").active = False
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_assigned").active = True
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_not_assigned").active = True
        else:
            # self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_categ").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_assigned").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_not_assigned").active = False
            # self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_categ").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_assigned").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_not_assigned").active = False
            # self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_categ").active = False
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line").active = True
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_assigned").active = False
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_not_assigned").active = False

    @api.depends('company_id')
    def get_analytic_accounting(self):
        for res in self:
            res.analytic_accounting = self.user_has_groups('analytic.group_analytic_accounting')

    @api.onchange('destination_warehouse_id', 'is_single_delivery_destination')
    def _onchange_destination_warehouse(self):
        if self.is_single_delivery_destination:
            self.picking_type_id = self.destination_warehouse_id.in_type_id.id
            self.order_line.update({
                'destination_warehouse_id': self.destination_warehouse_id.id,
                'picking_type_id': self.destination_warehouse_id.in_type_id.id
            })
            for line in self.order_line:
                line._onchange_destination_warehouse()


    @api.depends('order_line', 'order_line.date_planned')
    def _compute_date_planned(self):
        res = super()._compute_date_planned()
        return res
    #     """ date_planned = the earliest date_planned across all order lines. """
    #     for order in self:
    #         dates_list = False
    #         for line in order.order_line:
    #             if not line.display_type and line.date_planned:
    #                 if not dates_list:
    #                     dates_list = line.date_planned
    #                 else:
    #                     dates_list = line.date_planned if dates_list < line.date_planned else dates_list
    #         if dates_list:
    #             order.date_planned = dates_list
    #         else:
    #             order.date_planned = False

    def _inverse_date_planned(self):
        for record in self:
            record.date_planned = record.date_planned

    def _create_picking(self):
        StockPicking = self.env['stock.picking']
        context = dict(self.env.context) or {}
        dest_list = self.order_line.mapped('destination_warehouse_id')
        if context.get('goods_order') or context.get('orders') or context.get('active_model') == 'purchase.agreement':
            for order in self:
                sorted_line = sorted(order.order_line, key=lambda x: x.date_planned and x.destination_warehouse_id.id)
                final_data = [list(result) for key, result in groupby(
                    sorted_line, key=lambda x: x.date_planned and x.destination_warehouse_id.id)]
                # temp_data = []
                # final_data = []
                # for line in order.order_line:
                #     if {'date_planned': line.date_planned, 'warehouse_id': line.destination_warehouse_id.id} in temp_data:
                #         filter_lines = list(filter(lambda r:r.get('date_planned') == line.date_planned and r.get('warehouse_id') == line.destination_warehouse_id.id, final_data))
                #         if filter_lines:
                #             filter_lines[0]['lines'].append(line)
                #     else:
                #         temp_data.append({
                #             'date_planned': line.date_planned,
                #             'warehouse_id': line.destination_warehouse_id.id
                #         })
                #         final_data.append({
                #             'date_planned': line.date_planned,
                #             'warehouse_id': line.destination_warehouse_id.id,
                #             'lines': [line]
                #         })
                for line_data in final_data:
                    if any(product.type in ['product', 'consu'] for product in order.order_line.product_id):
                        order = order.with_company(order.company_id)
                        pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                        warehouse_id = line_data[0].mapped('destination_warehouse_id')
                        date_planned = line_data[0].mapped('date_planned')[0]
                        picking_type_id = self.env['stock.picking.type'].search([('warehouse_id', '=', warehouse_id.id), ('code', '=', 'incoming')], limit=1)
                        branch_id = line_data[0].mapped('destination_warehouse_id').branch_id.id
                        if len(dest_list) > 1:
                            res = order.with_context({'branch_id': branch_id, 'picking_type_id': picking_type_id})._prepare_picking()
                        else:
                            res = order._prepare_picking()
                        if picking_type_id:
                            res.update({
                                'picking_type_id': picking_type_id.id,
                                'location_dest_id': picking_type_id.default_location_dest_id.id,
                                'date': date_planned,
                                # 'date': line_data.get('date_planned'),
                            })
                        if warehouse_id.default_receipt_location_id:
                            res.update({
                                'location_dest_id':warehouse_id.default_receipt_location_id.id,
                            })
                        if warehouse_id:
                            res.update({
                                # 'branch_id': warehouse_id.branch_id.id or False
                            })
                        picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                        lines = self.env['purchase.order.line']
                        for new_line in line_data:
                            lines += new_line
                        # ctx = {
                        #     'res_sequence': 5
                        # }
                        moves = lines._create_stock_moves(picking)
                        moves.write({'location_dest_id': picking.location_dest_id.id})
                        moves = moves._action_confirm()
                        self.env.ref("equip3_purchase_operation.increment_five").number_next = 5
                        # moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                        # seq = 0
                        # for move in moves:
                        #     seq += 5
                        #     move.sequence = seq
                        moves._action_assign()
                        picking.message_post_with_view('mail.message_origin_link',
                            values={'self': picking, 'origin': order},
                            subtype_id=self.env.ref('mail.mt_note').id)
            return True
        else:
            return super()._create_picking()

    @api.onchange('date_planned', 'is_delivery_receipt')
    def onchange_date_planned(self):
        if self.date_planned and self.is_delivery_receipt:
            for line in self.order_line:
                if not line.display_type:
                    line.date_planned = self.date_planned

    def action_apply(self):
        for record in self:
            record.order_line.write({'destination_warehouse_id' : record.destination_warehouse_id})

    def _compute_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        approval =  IrConfigParam.get_param('is_purchase_order_approval_matrix')
        # approval = self.env.company.is_purchase_order_approval_matrix
        for record in self:
            record.is_approval_matrix = approval

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
            if len(matrix_line) == 0:
                record.is_approve_button = False
                record.approval_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button = True
                    record.approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button = False
                    record.approval_matrix_line_id = False
            else:
                record.is_approve_button = False
                record.approval_matrix_line_id = False


    @api.depends('approval_matrix_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            counter = 0
            record.approved_matrix_ids = []
            hierarchy = ApprovalHierarchy()
            for line in record.approval_matrix_id.approval_matrix_purchase_order_line_ids:
                if line.approver_types == "specific_approver":
                    counter += 1
                    data.append((0, 0, {
                        'sequence' : counter,
                        'user_ids' : [(6, 0, line.user_ids.ids)],
                        'minimum_approver' : line.minimum_approver,
                    }))
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data_seq = 0
                    approvers = hierarchy.get_hierarchy(self, self.env.user.employee_id, data_seq, manager_ids, seq,
                                                        line.minimum_approver)
                    for user in approvers:
                        counter += 1
                        data.append((0, 0, {
                            'sequence': counter,
                            'user_ids': [(6, 0, [user])],
                            'minimum_approver': 1,
                        }))
            record.approved_matrix_ids = data

    @api.onchange('name')
    def onchange_purchase_name(self):
        self._compute_approval_matrix()
        self._compute_approval_matrix_id()
        self._compute_taxes()

    @api.onchange('name')
    def onchange_checklist_template(self):
        if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order'):
        # if self.env.company.is_good_services_order:
            if self.is_goods_orders:
                # ids = self.env['purchase.custom.checklist.template'].search([('order', '=', 'goods')]).ids
                b = {'domain': {'custom_checklist_template_ids': [('order', '=', 'goods')]}}
            else:
                # ids = self.env['purchase.custom.checklist.template'].search([('order', '=', 'services')]).ids
                b = {'domain': {'custom_checklist_template_ids': [('order', '=', 'services')]}}
        else:
            b = {'domain': {'custom_checklist_template_ids': []}}
        return b

    @api.onchange('name')
    def onchange_partner(self):
        b = {}
        if self.env['ir.config_parameter'].sudo().get_param('is_vendor_approval_matrix'):
        # if self.env.company.is_vendor_approval_matrix:
            b = {'domain': {'partner_id': [('state2', '=', 'approved'),('supplier_rank', '>', 0), ('is_vendor', '=', True)]}}
        else:
            b = {'domain': {'partner_id': [('supplier_rank', '>', 0), ('is_vendor', '=', True)]}}
        return b


    @api.depends('amount_untaxed', 'branch_id', 'currency_id', 'order_line')
    def _compute_approval_matrix_id(self):
        is_good_services_order = self.env['ir.config_parameter'].sudo().get_param('is_good_services_order', False)
        # is_good_services_order = self.env.company.is_good_services_order
        for record in self:
            record.approval_matrix_id = False
            if record.is_approval_matrix and record.company_id and record.branch_id:
                approval_matrix_id = False
                if record.is_goods_orders:
                    # approval_matrix_id = self.env['approval.matrix.purchase.order'].search([
                    #             ('minimum_amt', '<=', record.amount_untaxed),
                    #             ('maximum_amt', '>=', record.amount_untaxed),
                    #             ('branch_id', '=', record.branch_id.id),
                    #             ('company_id', '=', record.company_id.id),
                    #             ('order_type', '=', "goods_order")], limit=1)
                    self.env.cr.execute("""
                        select id
                        from approval_matrix_purchase_order
                        where minimum_amt <= %s and
                        maximum_amt >= %s and
                        branch_id = %s and
                        company_id = %s and
                        currency_id = %s and
                        order_type = 'goods_order' order by id desc limit 1
                    """ % (record.amount_untaxed,record.amount_untaxed,record.branch_id.id,record.company_id.id, record.currency_id.id))
                    approval_matrix_id = self.env.cr.fetchall()
                    approval_matrix_id = approval_matrix_id[0][0] if approval_matrix_id else False
                elif record.is_services_orders:
                    self.env.cr.execute("""
                        select id
                        from approval_matrix_purchase_order
                        where minimum_amt <= %s and
                        maximum_amt >= %s and
                        branch_id = %s and
                        company_id = %s and
                        currency_id = %s and
                        order_type = 'services_order' order by id desc limit 1
                    """ % (record.amount_untaxed,record.amount_untaxed,record.branch_id.id,record.company_id.id, record.currency_id.id))
                    approval_matrix_id = self.env.cr.fetchall()
                    approval_matrix_id = approval_matrix_id[0][0] if approval_matrix_id else False
                else:
                    if not is_good_services_order:
                        self.env.cr.execute("""
                            select id
                            from approval_matrix_purchase_order
                            where minimum_amt <= %s and
                            maximum_amt >= %s and
                            branch_id = %s and
                            company_id = %s and
                            currency_id = %s
                            order by id desc limit 1
                        """ % (record.amount_untaxed,record.amount_untaxed,record.branch_id.id,record.company_id.id, record.currency_id.id))
                        approval_matrix_id = self.env.cr.fetchall()
                        approval_matrix_id = approval_matrix_id[0][0] if approval_matrix_id else False
                record.approval_matrix_id = approval_matrix_id



    def _send_whatsapp_message_approval(self, template_id, approver, phone, url, submitter=False):
        for record in self:
            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.request_partner_id.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.partner_id.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", submitter)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            phone_num = phone
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "")
            param = {'body': string_test, 'phone': phone_num, 'previewBase64': '', 'title': ''}
            domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
            token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
            try:
                request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
            except ConnectionError:
                raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def _send_qiscus_whatsapp_approval(self, template_id, approver, phone, url, submitter=False):
        for record in self:
            broadcast_template_id = self.env['qiscus.wa.template.content'].search([
                ('language', '=', 'en'),
                ('template_id.name', '=', 'hm_sale_notification_1')
            ], limit=1)
            if not broadcast_template_id:
                raise ValidationError(_("Cannot find Whatsapp template with name = 'hm_sale_notification_1'!"))
            domain = self.env['ir.config_parameter'].get_param('qiscus.api.url')
            token = self.env['ir.config_parameter'].get_param('qiscus.api.secret_key')
            app_id = self.env['ir.config_parameter'].get_param('qiscus.api.appid')
            channel_id = self.env['ir.config_parameter'].get_param('qiscus.api.channel_id')

            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.request_partner_id.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.partner_id.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", submitter)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            # message = re.sub(r'\n+', ', ', string_test)
            messages = string_test.split(f'\n')
            message_obj = []
            for pesan in messages:
                message_obj.append({
                    'type': 'text',
                    'text': pesan
                })
            phone_num = phone
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "").replace(" ", "").replace("-", "")
            headers = {
                'content-type': 'application/json',
                'Qiscus-App-Id': app_id,
                'Qiscus-Secret-Key': token
            }
            url = f'{domain}{app_id}/{channel_id}/messages'
            params = {
                "to": phone_num,
                "type": "template",
                "template": {
                    "namespace": broadcast_template_id.template_id.namespace,
                    "name": broadcast_template_id.template_id.name,
                    "language": {
                        "policy": "deterministic",
                        "code": 'en'
                    },
                    "components": [{
                        "type": "body",
                        "parameters": message_obj
                    }]
                }
            }
            try:
                request_server = requests.post(url, json=params, headers=headers, verify=True)
                _logger.info("\nNotification Whatsapp --> Request for Approval:\n-->Header: %s \n-->Parameter: %s \n-->Result: %s" % (headers, params, request_server.json()))
                # if request_server.status_code != 200:
                #     data = request_server.json()
                #     raise ValidationError(f"""{data["error"]["error_data"]["details"]}""")
            except ConnectionError:
                raise ValidationError("Not connect to API Chat Server. Limit reached or not active!")

    def action_request_approval(self):
        if not self.approval_matrix_id:
            raise ValidationError(_("You don’t have approval matrix for this RFQ, please set Purchase Order Approval Matrix first"))
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_email_notification = IrConfigParam.get_param('equip3_purchase_operation.is_email_notification')
        is_whatsapp_notification = IrConfigParam.get_param('equip3_purchase_operation.is_whatsapp_notification')
        for record in self:
            approver = False
            # for line in record.order_line:
            #     if line.price_unit == 0.0:
            #         raise UserError(_('You cannot confirm the purchase order without price.'))
            # if is_email_notification or is_whatsapp_notification:
            data = []
            action_id = self.env.ref('purchase.purchase_form_action')
            template_id = self.env.ref('equip3_purchase_operation.email_template_purchase_order')
            wa_template_id = self.env.ref('equip3_purchase_operation.wa_purchase_order_template')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=purchase.order'
            record.request_partner_id = self.env.user.partner_id.id
            if record.approved_matrix_ids:
                if len(record.approved_matrix_ids[0].user_ids) > 1:
                    for approved_matrix_id in record.approved_matrix_ids[0].user_ids:
                        approver = approved_matrix_id
                        if is_email_notification:
                            ctx = {
                                'email_from' : self.env.user.company_id.email,
                                'email_to' : approver.partner_id.email,
                                'approver_name' : approver.name,
                                'requested_by' : self.env.user.name,
                                'product_lines' : data,
                                'url' : url,
                                'date': date.today(),
                            }

                            template_id.with_context(ctx).send_mail(record.id, True)
                        if is_whatsapp_notification:
                            phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                            # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                            record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
                else:
                    approver = record.approved_matrix_ids[0].user_ids[0]
                    if is_email_notification:
                        ctx = {
                            'email_from': self.env.user.company_id.email,
                            'email_to': approver.partner_id.email,
                            'approver_name': approver.name,
                            'requested_by': self.env.user.name,
                            'product_lines': data,
                            'url': url,
                            'date': date.today(),
                        }
                        template_id.with_context(ctx).send_mail(record.id, True)
                    if is_whatsapp_notification:
                        phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                        # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                        record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
            else:
                raise ValidationError("Please setup Approval Matrix:\nConfiguration > Approval Matrix Configuration > Purchase Order Approval Matrix")
            record.write({'state' : 'waiting_for_approve'})


    def action_approve(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_email_notification = IrConfigParam.get_param('equip3_purchase_operation.is_email_notification')
        is_whatsapp_notification = IrConfigParam.get_param('equip3_purchase_operation.is_whatsapp_notification')
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            data = []
            action_id = self.env.ref('purchase.purchase_form_action')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=purchase.order'
            template_id = self.env.ref('equip3_purchase_operation.email_template_purchase_order_approve')
            wa_template_id = self.env.ref('equip3_purchase_operation.email_template_reminder_for_purchase_order_approval_wa')
            wa_approved_template_id = self.env.ref('equip3_purchase_operation.email_template_purchase_order_approval_approved_wa')
            approved_template_id = self.env.ref('equip3_purchase_operation.email_template_purchase_order_approval_approved')
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                        user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    if name != '':
                        name += "\n • %s: Approved" % (self.env.user.name)
                    else:
                        name += "• %s: Approved" % (self.env.user.name)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True, 'approver_state': 'approved'})
                        next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        approver_name = ' and '.join(approval_matrix_line_id.mapped('user_ids.name'))
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                if is_email_notification:
                                    ctx = {
                                        'email_from': self.env.user.company_id.email,
                                        'email_to': approving_matrix_line_user.partner_id.email,
                                        'user_name': approving_matrix_line_user.name,
                                        'approver_name': ','.join(approval_matrix_line_id.user_ids.mapped('name')),
                                        'url': url,
                                        'submitter' : approver_name,
                                        'product_lines': data,
                                        'date': date.today(),
                                    }
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_whatsapp_notification:
                                    phone_num = str(approving_matrix_line_user.partner_id.mobile) or str(approving_matrix_line_user.partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, approving_matrix_line_user, phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id, approving_matrix_line_user,
                                                                          phone_num, url, submitter=approver_name)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                if is_email_notification:
                                    ctx = {
                                        'email_from': self.env.user.company_id.email,
                                        'email_to': next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                        'user_name': next_approval_matrix_line_id[0].user_ids[0].name,
                                        'approver_name': ','.join(approval_matrix_line_id.user_ids.mapped('name')),
                                        'url': url,
                                        'submitter' : approver_name,
                                        'product_lines': data,
                                        'date': date.today(),
                                    }
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_whatsapp_notification:
                                    phone_num = str(next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile) or str(next_approval_matrix_line_id[0].user_ids[0].partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id,
                                                                          next_approval_matrix_line_id[0].user_ids[0],
                                                                          phone_num, url, submitter=approver_name)
                    else:
                        approval_matrix_line_id.write({'approver_state': 'pending'})
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r:r.approved)):
                record.write({'state': 'rfq_approved'})
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.request_partner_id.email,
                    'date': date.today(),
                    'url' : url,
                }
                if is_email_notification:
                    approved_template_id.sudo().with_context(ctx).send_mail(record.id, True)
                if is_whatsapp_notification:
                    phone_num = str(record.request_partner_id.mobile) or str(record.request_partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_approved_template_id, record.request_partner_id, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_approved_template_id, record.request_partner_id,
                                                          phone_num, url)

    def action_reject(self):
        return {
                'type': 'ir.actions.act_window',
                'name': 'Rejected Reason',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'approval.reject',
                'target': 'new',
            }

    def _compute_hold_purchase_order(self):
        for record in self:
            if self.env.user.has_group('equip3_purchase_operation.group_purchase_order_partner_credit_limit'):
                record.is_hold_purchase_order = True
            else:
                record.is_hold_purchase_order = False

    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        res = super(PurchaseOrder, self).onchange_partner_id()
        self._compute_hold_purchase_order()
        return res

    def button_onhold_confirm(self):
        self.state = 'sent'
        self.with_context(order_confirm=True).button_confirm()

    def button_confirm(self):
        self.env.context = dict(self._context)
        if self.is_revision_po and not self.env.context.get('name'):
            self.env.context.update({'name': self.name})
        context = dict(self.env.context) or {}
        context.update({'active_id': self.id, 'active_ids': self.ids, 'active_model': 'purchase.order'})
        reference_formatting = self.env.ref('equip3_purchase_accessright_setting.purchase_setting_1').reference_formatting
        for record in self:
            if record.is_revision_po and record.origin.startswith('PO') and reference_formatting == 'revise':
                po_count = self.search_count([("int_revision_order_id", '=', self.int_revision_order_id), ('is_revision_po', '=', True)])
                split_name = self.origin.split('/')
                if split_name[-1].startswith('R'):
                    split_name[-1] = 'R%d' % (po_count)
                    name = '/'.join(split_name)
                else:
                    name = _('%s/R%d') % (self.origin, (po_count))
                record.name = name
            if self.env.user.has_group('equip3_purchase_operation.group_purchase_order_partner_credit_limit') and \
                record.amount_total > record.partner_id.vendor_available_purchase_limit and \
                not context.get('order_confirm') and \
                record.partner_id.is_set_vendor_purchase_limit:
                 return {
                    'name': 'Vendor Purchase Limit',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'purchase.order.partner.credit',
                    'view_id': self.env.ref('equip3_purchase_operation.purchase_order_partner_credit_limit_form').id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context' : context
                }
            else:
                record.state = 'draft'
                if self.env.user.has_group('equip3_purchase_operation.group_purchase_order_partner_credit_limit'):
                    record.partner_id.vendor_available_purchase_limit -=  record.amount_total


        res = super(PurchaseOrder, self).button_confirm()
        lines = []
        if self.have_product_service:
            lines = self.order_line.filtered(lambda p:p.product_id.type == 'service')
        if not self.is_product_service_operation_receiving:
            for line in lines:
                line.qty_received = line.product_qty
        is_service_work_order = bool(self.env['ir.config_parameter'].sudo().get_param('is_service_work_order'))
        # is_service_work_order = self.env.company.is_service_work_order
        if is_service_work_order:
            for rec in self:
                if rec.have_product_service:
                    for milestone in rec.milestone_purchase_ids:
                        vals = {
                            'partner_id':rec.partner_id.id,
                            'account_analytic_tag_ids':[(6,0,rec.analytic_account_group_ids.ids)],
                            'purchase_line_milestone_id':milestone.id,
                            'date_planned':rec.date_planned,
                            'deadline_date':rec.date_planned,
                            'origin':rec.name,
                            'branch_id':rec.branch_id and rec.branch_id.id or False,
                            'company_id':rec.company_id and rec.company_id.id or False,
                            'order_line':[],
                            'checklist_ids':[],
                            'purchase_order_id':rec.id,
                        }
                        checklist_ids = []
                        for milestone_checklist in milestone.checklist_template_id.checklist_template:
                            vals_checklist = {
                                'name':milestone_checklist.name,
                                'desc':milestone_checklist.description,
                            }
                            checklist_ids.append((0,0,vals_checklist))
                        if checklist_ids:
                            vals['checklist_ids'] = checklist_ids

                        order_line = []
                        if self.have_product_service:
                            for line in lines:
                                vals_line = {
                                    'sequence2':line.sequence2,
                                    'product_id':line.product_id and line.product_id.id or False,
                                    'account_analytic_tag_ids':[(6,0,line.analytic_tag_ids.ids)],
                                    'description':line.name,
                                    'initial_demand':line.product_qty,
                                    'remaining':line.product_qty,
                                    'order_line_id': line.id
                                }
                                order_line.append((0,0,vals_line))
                        if order_line:
                            vals['order_line'] = order_line

                        swo_id = self.env['service.work.order'].sudo().create(vals)
                        swo_id.button_confirm()
        return res

    @api.model
    def default_get(self, fields):
        res = super(PurchaseOrder, self).default_get(fields)
        res['sh_purchase_revision_config'] = self.env.ref('equip3_purchase_accessright_setting.purchase_setting_1').purchase_revision
        context = dict(self.env.context) or {}
        if 'is_goods_orders' in res or 'default_is_goods_orders' in context:
            if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':
            # if self.env.company.is_good_services_order:
                if 'is_goods_orders' in res or 'default_is_goods_orders' in context:
                    if res.get('is_goods_orders') or context.get('default_is_goods_orders'):
                        rfq_exp_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_goods') or 0
                        # rfq_exp_date = self.env.company.rfq_exp_date_goods or 0
                    else:
                        rfq_exp_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_services') or 0
                        # rfq_exp_date = self.env.company.rfq_exp_date_services or 0
            else:
                rfq_exp_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date') or 0
                # rfq_exp_date = self.env.company.rfq_exp_date or 0
            res.update({
                'date_order': datetime.now() + timedelta(days=int(rfq_exp_date))
            })
        analytic_priority_ids = self.env['analytic.priority'].search([], order="priority")
        for analytic_priority in analytic_priority_ids:
            if analytic_priority.object_id == 'user' and self.env.user.analytic_tag_ids:
                res.update({
                    'analytic_account_group_ids': [(6, 0, self.env.user.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)]
                })
                break
            elif analytic_priority.object_id == 'branch' and self.env.branch.analytic_tag_ids:
                res.update({
                    'analytic_account_group_ids': [(6, 0, self.env.branch.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)]
                })
                break
        # if 'branch_id' in res:
        #     if res['branch_id']:
        #         user = self.env['res.users'].browse(self.env.uid)
        #         if user.has_group('branch.group_multi_branch'):
        #             branch_id = self.env['res.branch'].search([('id', 'in', self.env.context['allowed_branch_ids'])])
        #         else:
        #             branch_id = self.env['res.branch'].search([
        #             ('id','=',res['branch_id']),
        #                 '|',
        #                 ('company_id','=',False),
        #                 ('company_id','=',self.env.company.id),
        #             ])
        #         # res['branch_id'] = branch_id and branch_id.id or False
        #         res['branch_id'] = self.env.branch.id if len(self.env.branches) == 1 else False
        return res

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            user_branch = user_id.sudo().branch_id
            if not user_id.has_group('branch.group_multi_branch'):
                if user_branch and user_branch.id != selected_brach.id:
                    raise Warning("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")
            return {'domain':{'partner_id':[('company_id','=',self.env.company.id),('vendor_sequence','!=',False),('state2', '=', 'approved'), ('supplier_rank', '>', 0), ('is_vendor', '=', True)]}}
        else:
            return {'domain':{'partner_id':[('company_id','=',self.env.company.id),('vendor_sequence','!=',False), ('supplier_rank', '>', 0), ('is_vendor', '=', True)]}}

    def auto_cancel_rfq(self):
        rfqs = self.env['purchase.order'].search([
            ('date_order','<',datetime.now()),
            ('state', 'in', ('draft','sent','to_approve'))
            ])
        # seharusnya write() tidak perlu looping
        # tapi karena di override dan tidak di handling error di line 1883 jika tidak dilooping
        # - Y -
        for rfq in rfqs:
            rfq.write({'state': 'cancel'})

    def auto_cancel_po(self):
        po = self.env['purchase.order'].search([
            ('state', 'in', ('purchase', 'done')),
            ('po', '=', True),
            ('po_expiry_date', '<', datetime.now()),
            ('invoice_ids', '=', False),
            ])

        # seharusnya write() tidak perlu looping
        # tapi karena di override dan tidak di handling error di line 1883 jika tidak dilooping
        # - Y -
        for purchase in po:
            if not purchase.is_services_orders:
                purchase.write({'state': 'cancel'})
            else:
                if purchase.swo_count < 1:
                    purchase.write({'state': 'cancel'})
                else:
                    swo = self.env['service.work.order'].search([('purchase_order_id','=',purchase.id),('state', '!=', 'cancel')])
                    if not swo:
                        purchase.write({'state': 'cancel'})
            # picking = self.env['stock.picking'].search([('purchase_id', '=', res.id),('state', '=', 'done')])


    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        # if not vals.get('is_revision_po') or (vals.get('is_revision_po') and vals.get('origin').startswith('PO')):
        if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':
        # if self.env.company.is_good_services_order:
            if context.get('goods_order'):
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rfq.goods')
            elif context.get('services_good'):
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rfq.services')
            elif context.get('goods_order') == None and context.get('services_good') == None and context.get('assets_orders') == None and 'origin' in vals:
                if  vals['origin'] == False:
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rfq')
                elif '/G/' in vals['origin']:
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rfq.goods')
                elif '/S/' in vals['origin']:
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rfq.services')
                elif '/A/' in vals['origin']:
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request.seqs.a')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rfq')
        # else:
        #     vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rfq')
        if 'partner_invoice_id' not in vals:
            if 'partner_id' in vals:
                default_partner_invoice_id = False
                partner_id = self.env['res.partner'].browse(vals['partner_id'])
                vendor = partner_id
                child_invoice_ids = vendor.child_ids.filtered(lambda p:p.type == 'invoice')
                if child_invoice_ids:
                    default_partner_invoice_id = child_invoice_ids[0]
                else:
                    default_partner_invoice_id = vendor
                vals['partner_invoice_id'] = default_partner_invoice_id.id
        res = super(PurchaseOrder, self).create(vals)
        if res.log_po and 'import_file' not in self.env.context:
            if res.partner_id.name:
                message_vendor_name = 'Vendor Name : ' + str(res.partner_id.name) + '<br/>'
            else:
                message_vendor_name = ''
            if res.partner_invoice_id.name:
                message_vendor_bill_address = 'Vendor Bill Address : ' + str(res.partner_invoice_id.name) + '<br/>'
            else:
                message_vendor_bill_address = ''
            if res.currency_id.name:
                message_currency = 'Currency : ' + str(res.currency_id.name) + '<br/>'
            else:
                message_currency = ''
            if res.journal_id:
                message_journal = 'Journal : ' + str(res.journal_id.name) + '<br/>'
            else:
                message_journal = ''
            if res.date_order:
                message_rfq_expiry_date = 'RFQ Expiry Date : ' + str(res.date_order) + '<br/>'
            else:
                message_rfq_expiry_date = ''
            if res.milestone_template_id:
                message_milestone = 'Milestone and Contract Terms : ' + str(res.milestone_template_id.name) + '<br/>'
            else:
                message_milestone = ''
            msg = message_vendor_name + message_vendor_bill_address + message_currency + message_journal + message_rfq_expiry_date + message_milestone
            if msg:
                res.message_post(body=msg)
        return res

    def write(self, vals):
        context = dict(self.env.context) or {}
        if 'state' in vals:
            if vals['state'] not in ('draft', 'sent', 'to_approve'):
                if vals['state'] == 'purchase':
                    reference_formatting = self.env.ref('equip3_purchase_accessright_setting.purchase_setting_1').reference_formatting
                    if not self.exp_po or (self.is_revision_po and self.origin.startswith('RFQ')):
                        if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':
                        # if self.env.company.is_good_services_order:
                            if self.is_goods_orders and not context.get('default_dp'):
                                vals['name2'] = context.get('name') or self.name
                                if reference_formatting == 'new' or not self.is_revision_po or self.origin.startswith('RFQ'):
                                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs.goods')
                            elif context.get('default_dp') and self.is_goods_orders:
                                vals['name'] = self.env['ir.sequence'].next_by_code('direct.purchase.sequence.dp.new.goods')
                            elif self.is_services_orders and not context.get('default_dp'):
                                vals['name2'] = context.get('name') or self.name
                                if reference_formatting == 'new' or not self.is_revision_po or self.origin.startswith('RFQ'):
                                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs.services')
                            elif self.is_services_orders and context.get('default_dp'):
                                vals['name'] = self.env['ir.sequence'].next_by_code('direct.purchase.sequence.dp.new.services')
                        else:
                            if context.get('default_dp'):
                                vals['name'] = self.env['ir.sequence'].next_by_code('direct.purchase.sequence.dp.new')
                            else:
                                if self.name and self.name.startswith('RFQ/'):
                                    vals['name2'] = context.get('name') or self.name
                                    if reference_formatting == 'new' or not self.is_revision_po or self.origin.startswith('RFQ'):
                                        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs')
                        vals['exp_po'] = True
                    if 'name' not in vals:
                        if self.name and self.name.startswith('RFQ/'):
                            vals['name2'] = context.get('name') or self.name
                        if reference_formatting == 'new' or not self.is_revision_po or self.origin.startswith('RFQ'):
                            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs')

                    if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':
                    # if self.env.company.is_good_services_order:
                        if self.is_goods_orders:
                            po_exp_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.po_exp_date_goods') or 0
                            # po_exp_date = self.env.company.po_exp_date_goods or 0
                        else:
                            po_exp_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.po_exp_date_services') or 0
                            # po_exp_date = self.env.company.po_exp_date_services or 0
                    else:
                        po_exp_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.po_exp_date') or 0
                        # po_exp_date = self.env.company.po_exp_date or 0
                    vals['po_expiry_date'] = datetime.now() + timedelta(days=int(po_exp_date))
                    vals['po'] = True
            else:
                if vals['state'] == 'draft':
                    vals['po'] = False
        self._reset_sequence()
        return super(PurchaseOrder, self).write(vals)

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in sorted(rec.order_line, key=lambda x: x.sequence):
                if line.product_template_id and line.product_uom:
                    line.sequence2 = current_sequence
                    current_sequence += 1

    @api.depends('currency_id','order_line','order_line.price_total','order_line.price_subtotal',\
        'order_line.product_qty','discount_amount',\
        'discount_method','discount_type' ,'order_line.discount_amount',\
        'order_line.discount_method', 'order_line.is_down_payment')
    def _amount_all(self):
        res = super(PurchaseOrder, self)._amount_all()
        tax_discount_policy = self.env.company.tax_discount_policy or False
        for record in self:
            gross_total = 0
            # try:
            #     self.env.cr.execute("""
            #             select sum(product_uom_qty * price_unit) as gross from purchase_order_line where order_id = %s
            #         """ % (record.id))
            #     value = self.env.cr.fetchall()
            #     gross_total = value[0][0] if value[0][0] is not None else 0
            # except:
            # for line_gross in record.order_line:
            #     gross_total += line_gross.product_uom_qty * line_gross.price_unit
            gross_total = sum(record.order_line.filtered(lambda x: not x.is_down_payment).mapped('gross_total'))
            res_price_subtotal = 0
            res_discounted_value = 0
            res_total_price = 0
            res_price_tax = 0
            res_price_total = 0
            for line in record.order_line:
                if not line.is_down_payment:
                    if record.discount_type == 'global':
                        discount_amount = 0
                        if record.discount_method == 'fix':
                            if gross_total > 0:
                                discount_amount = (record.discount_amount / gross_total) * (
                                        line.product_uom_qty * line.price_unit)
                        else:
                            discount_amount = record.discount_amount

                        if not line.is_reward_line:
                            line.update({
                                'discount_method': record.discount_method,
                                'discount_amount': discount_amount
                            })
                        else:
                            line.update({
                            'discount_method': record.discount_method,
                            'discount_amount': 0
                        })

                total_price = discounted_value = 0
                total_price = line.price_unit * line.product_qty

                # Calculate Discounted Value
                if not line.is_down_payment:
                    if tax_discount_policy == 'tax':
                        if record.discount_type == 'global':
                            if line.discount_method == 'fix':
                                discounted_value = line.discount_amount
                            else:
                                discounted_value = (total_price + line.price_tax) * (line.discount_amount / 100)
                        else:
                            if line.discount_method == 'fix':
                                discounted_value = line.discount_amount
                            else:
                                if line.multi_discount:
                                    discounted_value = total_price * (line.discount_amount / 100)
                                else:
                                    discounted_value = line.discount_amount
                    else:
                        if line.discount_method == 'fix':
                            discounted_value = line.discount_amount
                        else:
                            discounted_value = total_price * (line.discount_amount / 100)

                tax_per = 0
                total_tax = 0
                tax_pph = 0

                if line.taxes_id:
                    for tax in line.taxes_id:
                        if tax.amount_type == 'percent':
                            tax_per += tax.amount
                if tax_discount_policy == 'tax':
                    total_tax = (total_price * tax_per) / 100
                    price_subtotal = total_price
                    price_total = price_subtotal + total_tax - discounted_value
                else:
                    price_subtotal = total_price - discounted_value
                    taxes = []
                    taxes_pph = []
                    price_include = False
                    for i in line.taxes_id:
                        if i.price_include:
                            price_include = True
                        if i.amount > 0:
                            taxes.append(i.compute_all(price_subtotal, line.order_id.currency_id, 1, product=line.product_id, partner=line.order_id.partner_id)['taxes'])
                    for i in taxes:
                        total_tax += i[0]['amount']
                    value = line.set_price_include(price_subtotal, total_tax, price_include)
                    for i in line.taxes_id:
                        if i.amount < 0:
                            taxes_pph.append(i.compute_all(value['price_subtotal'], line.order_id.currency_id, 1, product=line.product_id, partner=line.order_id.partner_id)['taxes'])
                    if taxes_pph:
                        for i in taxes_pph:
                            tax_pph += i[0]['amount']
                    price_subtotal = value['price_subtotal']
                    price_total = value['price_total'] + tax_pph

                line.update({
                    'total_price': total_price,
                    'price_tax': total_tax + tax_pph,
                    'discounted_value': discounted_value,
                    'price_subtotal': price_subtotal,
                    'price_total': price_total
                })
                if not line.is_down_payment:
                    res_price_subtotal += line.price_subtotal
                    res_discounted_value += line.discounted_value
                    res_price_tax += line.price_tax
                    res_total_price += line.total_price
                    res_price_total += line.price_total

            # lines = record.order_line.filtered(lambda r: not r.is_down_payment)
            # record.amount_subtotal = record.currency_id.round(sum(lines.mapped('price_subtotal'))) + record.currency_id.round(sum(lines.mapped('discounted_value'))) if tax_discount_policy == 'untax' else record.currency_id.round(sum(lines.mapped('total_price')))
            # record.amount_untaxed = record.currency_id.round(sum(lines.mapped('price_subtotal')))
            # record.amount_tax = record.currency_id.round(sum(lines.mapped('price_tax')))
            # net_discount = record.currency_id.round(sum(lines.mapped('discounted_value')))

            record.amount_subtotal = record.currency_id.round(res_price_subtotal) + record.currency_id.round(res_discounted_value) if tax_discount_policy == 'untax' else record.currency_id.round(res_total_price)
            record.amount_untaxed = record.currency_id.round(res_price_subtotal)
            record.amount_tax = record.currency_id.round(res_price_tax)
            net_discount = record.currency_id.round(res_discounted_value)

            record.discount_amt = net_discount
            record.discount_amt_line = net_discount
            if tax_discount_policy == 'tax':
                record.amount_total = record.amount_untaxed + record.amount_tax - net_discount
            else:
                record.amount_total = record.amount_untaxed + record.amount_tax  if tax_discount_policy == 'untax' else record.currency_id.round(res_price_total)

            # tax_applies = self.env['ir.config_parameter'].sudo().get_param('tax_discount_policy')
            # if tax_applies:
            #     if tax_applies == 'tax':
            #         record.amount_tax = record.currency_id.round(sum(lines.mapped('price_tax')))
            # if record.discount_method == 'per':
            #     record.discount_amt = (record.amount_untaxed * record.discount_amount) / 100
            # record.amount_total = record.amount_untaxed + record.amount_tax - record.discount_amt - record.discount_amt_line

        return res

    @api.depends("order_line.qty_received","have_product_service")
    def _compute_shipment(self):
        if self:
            for po_rec in self:
                po_rec.sh_hidden_compute_field = False
                if po_rec.order_line and not po_rec.sh_hidden_compute_field:
                    if not po_rec.have_product_service:
                        # no_service_product_line = po_rec.order_line.filtered(
                        #     lambda line: (line.product_id) and (line.product_id.type != 'service'))
                        # if no_service_product_line:
                            po_rec.write({"sh_fully_ship": False})
                            po_rec.write({"sh_partially_ship": False})
                            product_qty = qty_received = 0
                            for line in po_rec.order_line:
                                qty_received += line.qty_received
                                product_qty += line.product_qty
                            if product_qty == qty_received:
                                po_rec.write({"sh_fully_ship": True})
                            elif product_qty > qty_received and qty_received != 0:
                                po_rec.write({"sh_partially_ship": True})

                if po_rec.invoice_ids and not po_rec.sh_hidden_compute_field:
                    sum_of_invoice_amount = 0.0
                    sum_of_due_amount = 0.0
                    po_rec.write({'sh_fully_paid': False})
                    po_rec.write({'sh_partially_paid': False})
                    # for invoice_id in po_rec.invoice_ids.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                    for invoice_id in po_rec.mapped('order_line.invoice_lines.move_id').filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                        sum_of_invoice_amount = sum_of_invoice_amount + invoice_id.amount_total
                        sum_of_due_amount = sum_of_due_amount + invoice_id.amount_residual
                        if invoice_id.amount_residual != 0 and invoice_id.amount_residual < invoice_id.amount_total:
                            po_rec.write({'sh_partially_paid': True})
                    if sum_of_due_amount == 0 and sum_of_invoice_amount < po_rec.amount_total:
                        po_rec.write({'sh_partially_paid': True})
                    if sum_of_due_amount == 0 and sum_of_invoice_amount >= po_rec.amount_total:
                        po_rec.write({'sh_fully_paid': True})
                        po_rec.write({'sh_partially_paid': False})

    def wizard_close_purchase_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Validation',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_purchase_operation.close_purchase_order_form_view').id,
            'res_model': 'close.purchase.order',
            'context': {
                'default_purchase_id': self.id,
            },
            'target': 'new'
        }

    def close_purchase_order(self):
        for rec in self:
            rec.state = 'closed'
            for picking in rec.picking_ids.filtered(lambda x: x.state != 'done'):
                cancel_picking_id = self.env['cancel.picking'].create({
                    'reason': "Purchase Order closed"
                })
                cancel_picking_id.with_context({'active_ids': picking.ids}).cancel_picking()

    # tidak dipakai dimanapun
    # @api.onchange('product_template_id')
    # def set_available_product_template_ids(self):
    #     domain = [('company_id', '=', self.env.company.id),('branch_id','=',self.branch_id.id)]
    #     context = dict(self.env.context) or {}
    #     if context.get('goods_order'):
    #         domain += [('order_type', '=', 'goods_order')]
    #     elif context.get('services_good'):
    #         domain += [('order_type', '=', 'services_order')]
    #     elif context.get('assets_orders'):
    #         domain += [('order_type', '=', 'assets_order')]
    #     elif context.get('rentals_orders'):
    #         domain += [('order_type', '=', 'rental_order')]
    #
    #     available_product_templates = self.env['purchase.product.template'].sudo().search(domain)
    #     if available_product_templates:
    #         return {'domain': {'product_template_id': [('id', 'in', available_product_templates.purchase_product_template_ids.ids)]}}

    @api.model
    def purchase_comparison(self, records):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return {"type": "ir.actions.act_url", 'name': "Purchase Comparison Chart",
                "url": base_url + "/purchase_comparison?purchase_comp_rpt_type=htm&rfq_ids={}".format(records.ids),
                }

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    branch_ids = fields.Many2many('res.branch', compute='compute_branch_ids', store=True)
    gross_total = fields.Float("Gross Total", compute='_compute_amount', store=True)
    price_unit_uom = fields.Float("Price Unit UoM", compute='_compute_amount', store=True)
    branch_id = fields.Many2one(related='order_id.branch_id', store=True)
    log_po_line = fields.Boolean(string="Log Purchase Order Line", related='order_id.log_po')

    @api.onchange('product_template_id')
    def change_product_id(self):
        # method untuk fixing issue perbedaan UoM, terjadi karna db salah ambil data product_id dari product template
        for rec in self:
            if rec.product_template_id:
                variant_id = rec.product_template_id.product_variant_id
                if variant_id:
                    if rec.product_id not in rec.product_template_id.product_variant_ids:
                        rec.product_id = variant_id.id
            else:
                rec.product_id = False

    @api.depends('product_id','product_qty', 'price_unit', 'taxes_id','discount_method','discount_amount','discount_type')
    def _compute_amount(self):
        res = super()._compute_amount()
        for rec in self:
            rec.gross_total = rec.product_uom_qty * rec.price_unit
            product_uom = rec.product_uom or rec.product_id.uom_po_id
            if product_uom:
                price_unit_uom = product_uom._compute_quantity(
                    rec.price_unit, product_uom
                )
            else:
                price_unit_uom = 0
            rec.price_unit_uom = price_unit_uom
        return res

    def set_price_include(self, price, taxes, price_include):
        if price_include:
            return {
                'price_total': price,
                'price_subtotal': price - taxes
            }
        else:
            return {
                'price_total': price + taxes,
                'price_subtotal': price
            }

    @api.depends('order_id','order_id.branch_ids')
    def compute_branch_ids(self):
        for rec in self:
            rec.branch_ids = rec.order_id.branch_ids

    def _compute_qty_received_method(self):
        super(PurchaseOrderLine, self)._compute_qty_received_method()
        if self[0].order_id.is_services_orders:
            lines = self.filtered(lambda l: not l.display_type)
            for line in lines:
                if line.product_id.type in ['service']:
                    line.qty_received_method = 'stock_moves'

    # OVERRIDE dari eq_po_multi_warehouse atau equip3_accounting_asset
    def _create_or_update_picking(self):
        for line in self:
            if not line.is_down_payment:
                if line.product_id and line.product_id.type in ('product', 'consu'):
                    # Prevent decreasing below received quantity
                    if float_compare(line.product_qty, line.qty_received, line.product_uom.rounding) < 0:
                        raise UserError(_('You cannot decrease the ordered quantity below the received quantity.\n'
                                        'Create a return first.'))

                    if float_compare(line.product_qty, line.qty_invoiced, line.product_uom.rounding) == -1:
                        # If the quantity is now below the invoiced quantity, create an activity on the vendor bill
                        # inviting the user to create a refund.
                        line.invoice_lines[0].move_id.activity_schedule(
                            'mail.mail_activity_data_warning',
                            note=_('The quantities on your purchase order indicate less than billed. You should ask for a refund.'))

                    # If the user increased quantity of existing line or created a new line
                    pickings = line.order_id.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel') and x.location_dest_id.usage in ('internal', 'transit', 'customer') and x.picking_type_id.id == line.picking_type_id.id)
                    picking = pickings and pickings[0] or False
                    if not picking:
                        res = line.order_id.with_context(line_picking_type_id=line.picking_type_id.id)._prepare_picking()
                        picking = self.env['stock.picking'].create(res)
                    moves = line._create_stock_moves(picking)
                    moves._action_confirm()._action_assign()

    available_product_ids = fields.Many2many(comodel_name='product.template', string='Available Products')

    @api.onchange('order_id','sequence')
    def set_available_product_ids_new(self):
        for rec in self:
            available_products = []
            vendor_categ = rec.order_id.partner_id.vendor_product_categ_ids
            if vendor_categ:
                for x in vendor_categ:
                    available_products.extend(x.ids)
                categs = self.env['product.category'].search([('id', 'in', available_products)])
                categ_type = categs.mapped('stock_type')
                return {'domain': {'product_template_id': [('type', 'in', categ_type)]}}
            else:
                if rec.order_id.list_available_products:
                    available_products = rec.order_id.list_available_products.split(',')
                    return {'domain': {'product_template_id': [('id', 'in', available_products)]}}

    @api.constrains('product_qty')
    def _check_min_qty(self):
        for record in self:
            if record.display_type == 'line_note' or record.display_type == 'line_section':
                continue
            else:
                if record.product_qty <= 0:
                    raise ValidationError("Minimal Qty should be greater then zero.")

    @api.onchange('price_unit')
    def _check_price_unit(self):
        for line in self:
            if line.price_unit < 0:
                raise ValidationError('Please input valid amount for unit price')

    @api.model
    def _default_domain(self):
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            return [('type', 'in', ('consu','product'))]
        elif context.get('services_good'):
            return [('type', '=', 'service')]

    @api.depends('company_id', 'destination_warehouse_id', 'product_id')
    def compute_destination(self):
        for res in self:
            if res.order_id.is_single_delivery_destination:
                res.destination_warehouse_id = res.order_id.destination_warehouse_id
            else:
                if not res.destination_warehouse_id:
                    res.destination_warehouse_id = False

    @api.depends('company_id', 'date_planned', 'product_id')
    def compute_receipt(self):
        for res in self:
            if res.order_id.is_delivery_receipt:
                if not res.display_type:
                    res.date_planned = res.order_id.date_planned
            else:
                if not res.date_planned:
                    res.date_planned = False

    last_purchased_price = fields.Float(string="Last Purchased Price",compute='_compute_calculate_last_price', store=True)
    last_customer_purchase_price = fields.Float(string="Last Purchase Price Of Vendor", compute='_compute_calculate_last_price_vendor', store=True)
    is_goods_orders = fields.Boolean(string="Goods Orders", related='order_id.is_goods_orders', store=True)
    is_services_orders = fields.Boolean(string="Services Orders", default=False, related="order_id.is_services_orders", store=True)
    destination_location_id = fields.Many2one('stock.location', string='Destination Location')
    filter_destination_warehouse = fields.Char(string="Filter Destination Warehouse",compute='_compute_filter_destination', store=False)
    destination_warehouse_id = fields.Many2one('stock.warehouse', string='Destination', compute="compute_destination", store=True, domain=lambda self: [('id', 'in', self.env.user.warehouse_ids.ids),('company_id','=',self.env.company.id)])
    date_planned = fields.Datetime(string='Delivery Date', index=True,
                                   help="Delivery date expected from vendor. This date respectively defaults to vendor pricelist lead time then today's date.", compute="compute_receipt", store=True)
    delivery_ref = fields.Char(string="Delivery Reference", compute="_compute_delivery_ref")
    vendor_bills_ref = fields.Char(string="Vendor Bills Reference", compute="_compute_vendor_bills_ref")
    request_line_id = fields.Many2one('purchase.request.line', string="Purchase Request Line")
    readonly_price = fields.Boolean("Readonly Price", related='order_id.readonly_price')
    sequence = fields.Integer(string='Sequence')
    sequence2 = fields.Integer(string='No')
    avg_price = fields.Float(string="Average Price", compute="")
    current_qty = fields.Float(string="Current Qty in Warehouse", compute="")
    incoming_stock = fields.Float(string="Incoming Stock", compute="")
    actual_progress = fields.Float(string='Actual Progress', compute="_compute_actual_progress", store=True) #dijadikan store true untuk optimasi, dari codenya dihitung kalau ada perubahan di swo, jd mending di store dari pada di cek tiap waktu, udah pake depends jg di functnya
    remaining_progress = fields.Float(string='Remaining Progress', compute="_compute_actual_progress", store=True)
    progress_paid = fields.Float(string='Progress Paid', compute="_compute_actual_progress", store=True)
    date_received = fields.Datetime(string='Received Date')
    reference_purchase_price = fields.Float(string='Reference Price', compute="_compute_cost_savings", store=True)
    purchase_line_cost_saving = fields.Float(string='Cost Savings', compute="_compute_cost_savings", store=True)
    total_cost_saving = fields.Float(string='Total Cost Savings', compute="_compute_cost_savings", store=True)
    cost_saving_percentage = fields.Float(string='Cost Savings (%)', compute="_compute_cost_savings", store=True)
    partner_id = fields.Many2one(related='order_id.partner_id', store=True)
    # price_subtotal = fields.Monetary(compute='_compute_amount', string='Untaxed Amount', store=True)
    # price_total = fields.Monetary(compute='_compute_amount', string='Total Amount', store=True)
    price_subtotal = fields.Monetary(compute='', string='Untaxed Amount', readonly=True, store=True)
    price_total = fields.Monetary(compute='', string='Total Amount', readonly=True, store=True)
    total_price = fields.Monetary(string='Total Price', readonly=True, store=True)
    discounted_value = fields.Float('Discounted Value', default=0, readonly=True, store=True)

    @api.depends('company_id','order_id.branch_id')
    def _compute_filter_destination(self):
        for rec in self:
            rec.filter_destination_warehouse = json.dumps([('branch_id', '=', rec.branch_id.id), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.warehouse_ids.ids)])


    @api.onchange('discount_method')
    def reset_disc(self):
        for res in self:
            res.discount_amount = 0
            res.multi_discount = '0'
            res.discounted_value = 0

    @api.depends('product_id','product_template_id','price_unit','product_qty')
    def _compute_cost_savings(self):
        for i in self:
            param = ""
            if i.product_template_id:
                domain = [
                    ('product_tmpl_id','=',i.product_template_id.id),
                    ('state','=','active'),
                    ('company_id', '=', i.company_id.id),
                ]
                reference_price_id = False
                reference_price_id = self.env['reference.purchase.price'].search(domain, order="id desc")
                if reference_price_id:
                    if len(reference_price_id) > 1:
                        for ref in reference_price_id:
                            if ref.date_start and ref.date_end:
                                if ref.date_start <= date.today() <= ref.date_end:
                                    reference_price_id = ref
                                    break
                            else:
                                reference_price_id = ref
                                break
                    else:
                        if reference_price_id.date_start and reference_price_id.date_end:
                            if not (reference_price_id.date_start <= date.today() <= reference_price_id.date_end):
                                reference_price_id = False

                reference_price = reference_price_id.reference_purchase_price if reference_price_id else 0
                purchase_line_cost_saving =  reference_price - i.price_unit
                i.reference_purchase_price = reference_price
                i.purchase_line_cost_saving = purchase_line_cost_saving
                i.total_cost_saving = purchase_line_cost_saving * i.product_qty
                if reference_price:
                    cost_saving_percentage = (purchase_line_cost_saving / reference_price) * 100
                    if cost_saving_percentage < 0:
                        i.cost_saving_percentage = 0
                    else:
                        i.cost_saving_percentage = cost_saving_percentage
                else:
                    i.cost_saving_percentage = 0

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty', 'order_id.state')
    def _compute_qty_invoiced(self):
        res = super()._compute_qty_invoiced()
        for line in self:
            if line.is_down_payment:
                line.qty_invoiced = line.product_qty
                if line.product_id.purchase_method == 'purchase':
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
        return res

    def _prepare_account_move_line(self, move=False):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line()
        if self.product_id.purchase_method == 'receive':
            if self.is_down_payment:
                res['quantity'] = self.product_qty
            else:
                res['quantity'] = self.qty_received-self.qty_invoiced
        elif self.product_id.purchase_method == 'purchase':
            res['quantity'] = self.product_qty-self.qty_invoiced
        if 'purchase_line_id' in res:
            po = self.env['purchase.order.line'].browse(res['purchase_line_id']).order_id
            if po.is_services_orders and po.down_payment_amount:
                dp = po.down_payment_amount * 100 / po.amount_total
                if 'purchase_line_id' in res:
                    if not self.env['purchase.order.line'].browse(res['purchase_line_id']).is_down_payment:
                        res['quantity'] = (self.env.context['total_swo'] + dp) * res['quantity'] / 100
            # if po.is_services_orders and self.env.context['down_payment_by'] == 'dont_deduct_down_payment':
            if po.is_services_orders and self.env.context.get('down_payment_by') == 'dont_deduct_down_payment':
                res['quantity'] = (self.env.context['total_swo']) * self.product_uom_qty / 100

        swo_ids = self.env.context.get('swo_ids', False)
        if not swo_ids:
            return res

        product_id = self.env['product.product'].browse(res.get('product_id', False))
        if product_id and product_id.type == 'service':
            categ_id = product_id.categ_id
            if categ_id.stock_type == 'service':
                if categ_id.property_valuation == 'real_time':
                    account_id = categ_id.property_stock_account_input_categ_id
                    if not account_id:
                        raise ValidationError(_('Please set service input account for product category %s' % categ_id.display_name))
                else:
                    account_id = categ_id.property_service_account_id
                    if not account_id:
                        raise ValidationError(_('Please set service account for product category %s' % categ_id.display_name))
                res['account_id'] = account_id.id
        return res

    @api.depends('product_id','order_id.swo_ids','order_id.swo_ids.state','order_id.invoice_ids')
    def _compute_actual_progress(self):
        for rec in self:
            amount_total = 0
            if rec.order_id.invoice_ids:
                inv_ids = rec.order_id.invoice_ids.filtered(lambda s:s.state == 'posted')
                remaining_total = rec.order_id.amount_total - rec.order_id.down_payment_amount
                for inv in inv_ids:
                    amount_total += inv.amount_total - inv.amount_residual
            actual_progress = 0
            progress_paid = 0.0
            if rec.order_id.swo_ids:
                swo_ids = []
                swo_line_by_product = []
                for swo in rec.order_id.swo_ids:
                    if swo.state == 'done' and swo.order_line:
                        swo_ids.append(swo.id)
                if swo_ids:
                    self.env.cr.execute("""
                        SELECT ms.contract_term
                        FROM service_work_order_line as l
                        INNER JOIN service_work_order as s
                        ON l.swo_id = s.id
                        INNER JOIN milestone_contract_template_purchase as ms
                        ON s.purchase_line_milestone_id = ms.id
                        WHERE l.swo_id in %s and l.state2 = 'Completed' and l.product_id = %s
                    """, (tuple(swo_ids), rec.product_id.id))
                    swo_line_by_product = self.env.cr.fetchall()
                for swo_line in swo_line_by_product:
                    actual_progress += swo_line[0]
            remaining_progress = 100.0 - actual_progress
            actual_progress_str = actual_progress
            if amount_total > rec.order_id.down_payment_amount:
                if remaining_total > 0:
                    progress_paid = (amount_total - rec.order_id.down_payment_amount) / remaining_total * 100
            rec.update({
                'actual_progress': actual_progress_str,
                'remaining_progress': remaining_progress,
                'progress_paid': progress_paid
            })


    @api.depends('product_id', 'destination_warehouse_id')
    def _compute_incoming_stock(self):
        for rec in self:
            incoming_stock = 0
            if rec.product_id and rec.destination_warehouse_id:
                location_ids = self.env['stock.location'].sudo().search([('warehouse_id','=',rec.destination_warehouse_id.id)])
                picking = self.env['stock.picking'].search(
                    [('state', 'not in', ['done', 'cancel', 'draft']), ('picking_type_id.code', '=', 'incoming'),
                     ('move_lines.product_id', '=', rec.product_id.id), ('location_dest_id', 'in', location_ids.ids)])
                if picking:
                    for stock in picking:
                        move_stock = stock.move_ids_without_package.filtered(
                            lambda x: x.product_id.id == rec.product_id.id)
                        if move_stock:
                            incoming_stock += sum(move_stock.mapped('remaining'))
            rec.incoming_stock = incoming_stock

    @api.depends('product_id', 'destination_warehouse_id')
    def _compute_current_qty(self):
        for record in self:
            location_ids = []
            record.current_qty = 0
            if record.product_id and record.destination_warehouse_id:
                location_obj = self.env['stock.location']
                store_location_id = record.destination_warehouse_id.view_location_id.id
                addtional_ids = location_obj.search(
                    [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_ids.append(location.id)
                child_location_ids = self.env['stock.location'].search(
                    [('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                final_location = child_location_ids + location_ids
                # stock_quant_ids = self.env['stock.quant'].search(
                #     [('location_id', 'in', final_location), ('product_id', '=', record.product_id.id)])
                self.env.cr.execute("""
                    SELECT SUM(quantity)
                    FROM stock_quant
                    WHERE location_id in %s AND product_id = %s
                """ % (str(final_location).replace('[','(').replace(']',')'), record.product_id.id))
                qty_available = self.env.cr.fetchall()
                record.current_qty = qty_available[0][0] or 0

    @api.depends('product_id')
    def _compute_avg_price(self):
        services = False
        qty = 0
        pr_order_average_price = self.env['ir.config_parameter'].sudo().get_param('equip3_purchase_operation.pr_order_average_price')
        for record in self:
            if not record.partner_id.id:
                raise ValidationError("Fill in the Vendor field first !")
            if record.product_id.type == 'service':
                services = True
            if pr_order_average_price == "day":
                # final_date = datetime.now().date() - timedelta(days=1)
                # order_lines = self.search([
                #     ('partner_id', '=', record.order_id.partner_id.id),
                #     ('product_id', '=', record.product_id.id)
                # ])
                # filter_order_lines = order_lines.filtered(lambda r: r.create_date.date() == final_date)
                # qty = (sum(filter_order_lines.mapped('price_subtotal')) / len(filter_order_lines)) if filter_order_lines else 0
                # record.avg_price = qty
                if record.product_id:
                    final_date = datetime.now().date() - timedelta(days=1)
                    self.env.cr.execute("""
                        SELECT SUM(price_subtotal), COUNT(id)
                          FROM purchase_order_line
                         WHERE partner_id = %s AND product_id = %s AND create_date = '%s'
                    """ % (record.partner_id.id, record.product_id.id, final_date))
                    filter_order_lines = self.env.cr.fetchall()
                    qty = filter_order_lines[0][0] / filter_order_lines[0][1] if filter_order_lines[0][0] is not None else 0
                record.avg_price = qty
            elif pr_order_average_price == "week":
                # final_date = datetime.now().date() - timedelta(days=8)
                # date_today = date.today() - timedelta(days=1)
                # order_lines = self.search([
                #     ('partner_id', '=', record.order_id.partner_id.id),
                #     ('product_id', '=', record.product_id.id)
                # ])
                # filter_order_lines = order_lines.filtered(lambda r: r.create_date.date() >= final_date and r.create_date.date() <= date_today)
                # qty = (sum(filter_order_lines.mapped('price_subtotal')) / len(filter_order_lines)) if filter_order_lines else 0
                if record.product_id:
                    final_date = datetime.now().date() - timedelta(days=8)
                    date_today = date.today() - timedelta(days=1)
                    self.env.cr.execute("""
                            SELECT SUM(price_subtotal),COUNT(id)
                              FROM purchase_order_line
                             WHERE partner_id = %s AND product_id = %s AND create_date BETWEEN '%s' AND '%s'
                        """ % (record.partner_id.id, record.product_id.id, final_date, date_today))
                    filter_order_lines = self.env.cr.fetchall()
                    qty = filter_order_lines[0][0] / filter_order_lines[0][1] if filter_order_lines[0][0] is not None else 0
                record.avg_price = qty
            elif pr_order_average_price == "month":
                if record.product_id:
                    final_date = datetime.now().date() - relativedelta(months=1)
                    date_today = date.today() - timedelta(days=1)
                    # order_lines = self.search([
                    #     ('partner_id', '=', record.order_id.partner_id.id),
                    #     ('product_id', '=', record.product_id.id)
                    # ])
                    # filter_order_lines = order_lines.filtered(lambda r: r.create_date.date() >= final_date and r.create_date.date() <= date_today)
                    # qty = (sum(filter_order_lines.mapped('price_subtotal')) / len(filter_order_lines)) if filter_order_lines else 0
                    # record.avg_price = qty
                    self.env.cr.execute("""
                            SELECT SUM(price_subtotal),COUNT(id)
                              FROM purchase_order_line
                             WHERE partner_id = %s AND product_id = %s AND create_date BETWEEN '%s' AND '%s'
                        """ % (record.partner_id.id, record.product_id.id, final_date, date_today))
                    filter_order_lines = self.env.cr.fetchall()
                    qty = filter_order_lines[0][0] / filter_order_lines[0][1] if filter_order_lines[0][0] is not None else 0
                record.avg_price = qty
            else:
                if record.product_id:
                    final_date = datetime.now().date() - relativedelta(years=1)
                    date_today = date.today() - timedelta(days=1)
                    # order_lines = self.search([
                    #     ('partner_id', '=', record.order_id.partner_id.id),
                    #     ('product_id', '=', record.product_id.id)
                    # ])
                    # filter_order_lines = order_lines.filtered(lambda r: r.create_date.date() >= final_date and r.create_date.date() <= date_today)
                    # qty = (sum(filter_order_lines.mapped('price_subtotal')) / len(filter_order_lines)) if filter_order_lines else 0
                    # record.avg_price = qty
                    self.env.cr.execute("""
                            SELECT SUM(price_subtotal),COUNT(id)
                              FROM purchase_order_line
                             WHERE partner_id = %s AND product_id = %s AND create_date BETWEEN '%s' AND '%s'
                        """ % (record.partner_id.id, record.product_id.id, final_date, date_today))
                    filter_order_lines = self.env.cr.fetchall()
                    qty = filter_order_lines[0][0] / filter_order_lines[0][1] if filter_order_lines[0][0] is not None else 0
                record.avg_price = qty
            if not record.order_id.is_services_orders:
                if services:
                    record.order_id.is_services_orders = services



    @api.model
    def default_get(self, fields):
        res = super(PurchaseOrderLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence2 = 1
            if 'order_line' in context_keys:
                for line in self._context.get('order_line'):
                    if line[2]:
                        next_sequence2 += 1
                    elif 'virtual' in str(line[1]):
                        if line[2]['product_template_id']:
                            next_sequence2 += 1
            res.update({'sequence': next_sequence2, 'sequence2': next_sequence2})
        return res

    def copy(self, default=None):
        res = super().copy(default)
        return res

    def unlink(self):
        approval = self.order_id
        res = super(PurchaseOrderLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.onchange('sequence')
    def set_sequence_line(self):
        for record in self:
            record.order_id._reset_sequence()

    @api.model
    def _get_date_planned(self, seller, po=False):
        # Do not change the date_planned for the PO line revision.
        if not self.env.context.get('is_revision_po'):
            return super()._get_date_planned(seller, po)
        else:
            return self.date_planned
    #

    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        if 'sh_pmps_adv_po_id' in context:
            order_id = self.env['purchase.order'].browse(vals['order_id'])
            vals['destination_warehouse_id'] = order_id.destination_warehouse_id.id
            vals['picking_type_id'] = order_id.destination_warehouse_id.in_type_id.id
            vals['analytic_tag_ids'] = order_id.analytic_account_group_ids.ids
        if 'is_down_payment' in vals:
            if vals['is_down_payment']:
                vals['qty_received'] = vals['product_qty']

        # bug fix ketika add note
        if vals.get('display_type', '') == 'Note':
            vals['display_type'] = 'line_note'

        res = super(PurchaseOrderLine, self).create(vals)
        # bug fix ketika add section / note
        if res.display_type:
            res.date_planned = False
            res.product_uom_qty = 0

        # res.order_id._reset_sequence()
        if res.log_po_line and 'import_file' not in self.env.context:
            if res.date_planned:
                message_expected_date = 'Expected Date : ' + str(res.date_planned) + '<br/>'
            else:
                message_expected_date = ''
            if res.destination_warehouse_id:
                message_destination = 'Destination : ' + str(res.destination_warehouse_id.name) + '<br/>'
            else:
                message_destination = ''
            if res.analytic_tag_ids:
                message_analytic = 'Analytic Group : ' + '<br/>'
                for rec in res.analytic_tag_ids:
                    message_analytic += rec.name + '<br/>'
            else:
                message_analytic = ''
            message_order_line = ''
            for tax_line in res.taxes_id:
                tax = res.price_subtotal * tax_line.amount / 100
                message_order_line += 'Product Added : ' + str(res.product_template_id.name) + '<br/>' + 'Discount : ' + str(res.discount_amount) + '<br/>' + 'Quantity : ' + str(res.product_qty) + '<br/>' + 'Price : ' + str(res.price_unit) + '<br/>' + 'Tax : ' + str(tax) + '<br/>' + message_analytic + message_expected_date + message_destination
            if message_order_line:
                res.order_id.message_post(body=message_order_line)
        if res.order_id.is_delivery_receipt:
            if not res.display_type:
                res.date_planned = res.order_id.date_planned
        return res

    def write(self, vals):
        msg = ''
        i = 0
        for rec in self:
            i += 1
            message_edit_product = ''
            message_edit_discount = ''
            message_edit_qty = ''
            message_edit_price = ''
            message_expected_date = ''
            message_destination = ''
            if rec.log_po_line and 'import_file' not in self.env.context:
                if vals.get('product_id') or vals.get('discount_amount') or vals.get('product_qty') or vals.get('price_unit') or vals.get('date_planned') or vals.get('destination_warehouse_id'):
                    if 'product_template_id' in vals:
                        if rec.product_template_id.id != vals['product_template_id']:
                            message_edit_product = 'Product : ' + str(rec.product_template_id.name) + ' --> ' + str(rec.env['product.template'].browse(vals['product_template_id']).name) + '<br/>'
                    if 'product_id' in vals:
                        if rec.product_id.id != vals['product_id']:
                            message_edit_product = 'Product : ' + str(rec.product_id.name) + ' --> ' + str(rec.env['product.product'].browse(vals['product_id']).name) + '<br/>'
                    if 'discount_amount' in vals:
                        if rec.discount_amount != vals['discount_amount']:
                            message_edit_discount = 'Discount : ' + str(rec.discount_amount) + ' --> ' + str(vals['discount_amount']) + '<br/>'
                    if 'product_qty' in vals:
                        if rec.product_qty != vals['product_qty']:
                            message_edit_qty = 'Quantity : ' + str(rec.product_qty) + ' --> ' + str(vals['product_qty']) + '<br/>'
                    if 'price_unit' in vals:
                        if rec.price_unit != vals['price_unit']:
                            message_edit_price = 'Price : ' + str(rec.price_unit) + ' --> ' + str(vals['price_unit']) + '<br/>'
                    if 'date_planned' in vals:
                        if rec.date_planned and rec.date_planned != vals['date_planned']:
                            message_expected_date = 'Expected Date : ' + str(rec.date_planned) + ' --> ' + str(vals['date_planned']) + '<br/>'
                    if 'destination_warehouse_id' in vals:
                        if rec.destination_warehouse_id.id != vals['destination_warehouse_id']:
                            message_destination = 'Destination : ' + str(rec.destination_warehouse_id.name) + ' --> ' + str(rec.env['stock.warehouse'].browse(vals['destination_warehouse_id']).name) + '<br/>'
                    msg += message_edit_product + message_edit_discount + message_edit_qty + message_edit_price + message_expected_date + message_destination
                    if len(self) != i:
                        msg+='<br/>'
        if msg:
            self[0].order_id.message_post(body=msg)
        return super(PurchaseOrderLine, self).write(vals)

    def _compute_vendor_bills_ref(self):
        for rec in self:
            rec.vendor_bills_ref = ''
            if rec.invoice_lines and rec.invoice_lines.filtered(lambda r:r.ref):
                name = ",".join(rec.invoice_lines.filtered(lambda r:r.ref).mapped('ref'))
                rec.vendor_bills_ref = name

    def _compute_delivery_ref(self):
        for rec in self:
            rec.delivery_ref = ""
            if rec.move_ids and rec.move_ids.filtered(lambda r:r.reference):
                name = ",".join(rec.move_ids.filtered(lambda r:r.reference).mapped('reference'))
                rec.delivery_ref = name

    # @api.depends('order_id', 'order_id.is_goods_orders')
    # def _compute_is_good_orders(self):
    #     for record in self:
    #         record.is_goods_orders = record.order_id.is_goods_orders

    @api.onchange('date_planned')
    def onchange_date_planned_line(self):
        if self.date_planned and not self.order_id.is_delivery_receipt:
            dates_list = self.order_id.order_line.filtered(lambda x: not x.display_type and x.date_planned).mapped('date_planned')
            if dates_list:
                self.order_id.date_planned = fields.Datetime.to_string(max(dates_list))
        elif self.date_planned and self.order_id.is_delivery_receipt:
            self.order_id.onchange_date_planned()

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        res = super(PurchaseOrderLine, self)._prepare_stock_move_vals(picking=picking, price_unit=price_unit, product_uom_qty=product_uom_qty, product_uom=product_uom)
        product = self.product_id.with_context(lang=self.order_id.dest_address_id.lang or self.env.user.lang)
        description_picking = product._get_description(picking.picking_type_id)
        price_unit = self.price_subtotal / self.product_uom_qty
        res.update({
            'picking_type_id': picking.picking_type_id.id,
            'warehouse_id': self.destination_warehouse_id.id,
            'price_unit': price_unit,
            'route_ids': picking.picking_type_id.warehouse_id and [(6, 0, [x.id for x in picking.picking_type_id.warehouse_id.route_ids])] or [],
            'location_dest_id': picking.picking_type_id.default_location_dest_id.id,
            'analytic_account_group_ids': [(6, 0, self.analytic_tag_ids.ids)]
        })
        self.picking_type_id = picking.picking_type_id.id
        return res

    @api.depends('product_id')
    def _compute_calculate_last_price(self):
        for record in self:
            purchase_order_line_id = False
            if isinstance(record.id, models.NewId):
                if record.product_id:
                    self.env.cr.execute("""
                        SELECT id, price_unit
                        FROM purchase_order_line
                        WHERE state in ('purchase','done') AND product_id = %s
                        GROUP BY id, price_unit
                    """ % (record.product_id.id))
                    purchase_order_line_id = self.env.cr.fetchall()
            else:
                if record.product_id:
                    self.env.cr.execute("""
                        SELECT id, price_unit
                        FROM purchase_order_line
                        WHERE state in ('purchase','done') AND product_id = %s AND id != %s
                        GROUP BY id, price_unit
                    """ % (record.product_id.id, record.id))
                    purchase_order_line_id = self.env.cr.fetchall()
            if purchase_order_line_id:
                record.last_purchased_price = purchase_order_line_id[-1][1]
            else:
                record.last_purchased_price = 0

    @api.depends('product_id', 'order_id', 'order_id.partner_id')
    def _compute_calculate_last_price_vendor(self):
        for record in self:
            if not record.partner_id.id:
                raise ValidationError("Fill in the Vendor field first !")
            purchase_order_line_id = False
            if isinstance(record.id, models.NewId):
                if record.product_id:
                    self.env.cr.execute("""
                        SELECT id, price_unit
                        FROM purchase_order_line
                        WHERE state in ('purchase','done') AND product_id = %s AND partner_id = %s
                        GROUP BY id, price_unit
                    """ % (record.product_id.id, record.partner_id.id))
                    purchase_order_line_id = self.env.cr.fetchall()
            else:
                if record.product_id:
                    self.env.cr.execute("""
                        SELECT id, price_unit
                        FROM purchase_order_line
                        WHERE state in ('purchase','done') AND product_id = %s AND partner_id = %s AND id != %s
                        GROUP BY id, price_unit
                    """ % (record.product_id.id, record.partner_id.id, record.id))
                    purchase_order_line_id = self.env.cr.fetchall()
            if purchase_order_line_id:
                record.last_purchased_price = purchase_order_line_id[-1][1]
            else:
                record.last_purchased_price = 0

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        ''' inventory catch this context to apply standard_price based warehouse '''
        self = self.with_context(price_for_warehouse=self.destination_warehouse_id)

        if self.product_id and not self.product_uom:
            self.product_uom = self.product_id.uom_po_id.id
        res = super(PurchaseOrderLine, self)._onchange_quantity()
        if self.product_id:
            params = {'order_id': self.order_id}
            seller = self.product_id._select_seller(
                partner_id=self.partner_id,
                quantity=self.product_qty,
                date=self.order_id.date_order and self.order_id.date_order.date(),
                uom_id=self.product_uom,
                params=params)
            if seller and self.is_vendor_pricelist_line and seller.state1 != 'approved':
                self.price_unit = 0
        if self.request_line_id:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            pr_qty_limit =  IrConfigParam.get_param('pr_qty_limit', "no_limit")
            # pr_qty_limit =  self.env.company.pr_qty_limit
            if pr_qty_limit == 'percent':
                max_percentage = IrConfigParam.get_param('max_percentage', 0)
                # max_percentage = self.env.company.max_percentage
                pr_line_qty = (self.request_line_id.product_qty * int(max_percentage)) / 100
                max_qty = pr_line_qty + self.request_line_id.product_qty
                if self.product_qty > max_qty:
                    warning_mess = {
                        'title': _('Quantity Warning!'),
                        'message' : _('Quantity Can Not Be Greater Then Purchase Request Quantity.'),
                    }
                    return {'warning': warning_mess, 'value': {'product_qty': self.request_line_id.product_qty}}
            elif pr_qty_limit == 'fix' and self.product_qty > self.request_line_id.product_qty:
                warning_mess = {
                    'title': _('Quantity Warning!'),
                    'message' : _('Quantity Can Not Be Greater Then Purchase Request Quantity.'),
                }
                return {'warning': warning_mess, 'value': {'product_qty': self.request_line_id.product_qty}}
        return res

    @api.onchange('destination_warehouse_id')
    def _onchange_destination_warehouse(self):
        self._onchange_quantity()

    def make_get_stock_move_price_unit(self):
        def _get_stock_move_price_unit(self):
            self.ensure_one()
            line = self[0]
            order = line.order_id
            price_unit = line.price_subtotal / line.product_qty # changed here (previous line.price_unit)
            price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
            if line.taxes_id:
                qty = line.product_qty or 1
                price_unit = line.taxes_id.with_context(round=False).compute_all(
                    price_unit, currency=line.order_id.currency_id, quantity=qty, product=line.product_id, partner=line.order_id.partner_id
                )['total_void']
                price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                price_unit = order.currency_id._convert(
                    price_unit, order.company_id.currency_id, self.company_id, self.date_order or fields.Date.today(), round=False)
            return price_unit
        return _get_stock_move_price_unit

    def _register_hook(self):
        BasicPurchaseOrderLine._patch_method('_get_stock_move_price_unit', self.make_get_stock_move_price_unit())
        return super(PurchaseOrderLine, self)._register_hook()

class PurchaseRequestLine(models.Model):
    _inherit ='purchase.request.line'

    branch_id = fields.Many2one(related='request_id.branch_id', store=True)
    sequence = fields.Integer(string='Sequence')
    sequence2 = fields.Integer(string='No')
    remaning_qty = fields.Float(compute="_compute_new_remaning_qty", string="Remaining Qty")
    purchase_req_budget = fields.Float(string='Purchase Request Budget', readonly=True)
    rem_budget = fields.Float(string='Remaining Budget', readonly=True)
    purchase_req_state = fields.Selection(related='request_id.purchase_req_state', store=True)
    assigned_to_partner_id = fields.Many2one(related='assigned_to.partner_id', store=True)
    set_order = fields.Char(compute='_compute_order_id', string='Set Order ID', store=True)
    purchase_req_budget_2 = fields.Float("Purchase Budget", compute='_get_purchase_req_budget', readonly=True)

    @api.depends('product_id','analytic_account_group_ids')
    def _get_purchase_req_budget(self):
        today = fields.Date.today()
        for rec in self:
            purchase_req_budget = 0
            realized_amount = 0
            if rec.confirm_budget_data:
                purchase_req_budget = rec.confirm_purchase_req_budget
                realized_amount = rec.confirm_realized_amount
                print("===TEST1",purchase_req_budget)
            elif rec.product_id:
                budget_purchase_line_filter = [('product_id','=',rec.product_id.id),('date_from','<=',today),('date_to','>=',today),('account_tag_ids','in',rec.analytic_account_group_ids.ids)]
                budget_purchase_lines = self.env['budget.purchase.lines'].search(budget_purchase_line_filter)
                print("===TEST2",budget_purchase_line_filter)
                print("===TEST3",budget_purchase_lines)
                print("===TEST4",budget_purchase_lines.purchase_budget_state)
                purchase_req_budget = budget_purchase_lines and sum([x.planned_amount for x in budget_purchase_lines if x.purchase_budget_state in ('done','validate')]) or 0
                realized_amount = budget_purchase_lines and sum([x.practical_amount for x in budget_purchase_lines if x.purchase_budget_id.state in ('done','validate')]) or 0
            print("===TEST",purchase_req_budget)
            rec.purchase_req_budget_2 = purchase_req_budget
            rec.realized_amount = realized_amount

    @api.depends('purchase_lines')
    def _compute_order_id(self):
        for rec in self:
            rec.set_order = "Ok"
            order_ids = []
            if rec.purchase_lines:
                for i in rec.purchase_lines:
                    if i.order_id.id not in order_ids:
                        if rec.requested_by.id not in i.order_id.user_request_ids.ids:
                            i.order_id.user_request_ids = [(4, rec.requested_by.id)]
                        order_ids.append(i.order_id.id)
            if order_ids:
                rec.request_id.purchase_ids = [(6, 0, order_ids)]

    @api.depends('product_qty','purchased_qty')
    def _compute_new_remaning_qty(self):
        for record in self:
            if record.product_qty == record.purchased_qty:
                record.remaning_qty = 0
            else:
                record.remaning_qty = record.product_qty - record.purchased_qty

    @api.model
    def default_get(self, fields):
        res = super(PurchaseRequestLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'line_ids' in context_keys:
                if len(self._context.get('line_ids')) > 0:
                    next_sequence = len(self._context.get('line_ids')) + 1
            res.update({'sequence': next_sequence, 'sequence2': next_sequence})
        return res

    def unlink(self):
        approval = self.request_id
        res = super(PurchaseRequestLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.onchange('sequence')
    def set_sequence_line(self):
        for record in self:
            record.request_id._reset_sequence()

    @api.model
    def create(self, vals):
        res = super(PurchaseRequestLine, self).create(vals)
        res.request_id._reset_sequence()
        return res

    # jalan
    @api.model
    def _default_domain(self):
        context = dict(self.env.context) or {}
        # setting = self.env['ir.config_parameter'].sudo().get_param('is_good_services_order')
        domain = [('company_id','=',self.env.company.id),('purchase_ok','=',True)]
        if context.get('goods_order'):
            return domain+[('type', 'in', ('consu','product'))]
        elif context.get('services_good'):
            return domain+[('type', '=', 'service')]
        return domain

    @api.depends('company_id', 'dest_loc_id', 'product_id')
    def compute_destination(self):
        for res in self:
            if res.request_id.is_single_delivery_destination:
                res.dest_loc_id = res.request_id.destination_warehouse
            else:
                if not res.dest_loc_id:
                    res.dest_loc_id = False

    @api.depends('company_id', 'date_required', 'product_id')
    def compute_receipt(self):
        for res in self:
            if res.request_id.is_single_request_date:
                res.date_required = res.request_id.request_date
            else:
                if not res.date_required:
                    res.date_required = False

    product_id = fields.Many2one(domain=_default_domain, required=True)
    is_goods_orders = fields.Boolean(string="Goods Orders", default=False, related='request_id.is_goods_orders', store=True)
    is_services_orders = fields.Boolean(string="Services Orders", default=False, related='request_id.is_services_orders', store=True)
    price_total = fields.Float(string="Total Estimated Cost", compute="_compute_price_total", store=True)
    dest_loc_id = fields.Many2one('stock.warehouse', string="Destination", store=False)
    picking_type_dest = fields.Many2one('stock.picking.type', string="Picking Type")
    current_qty = fields.Float(string="Current Qty in Warehouse", compute="_compute_current_qty", store=True)
    analytic_account_group_ids = fields.Many2many('account.analytic.tag', string="Analytic Account Group")
    purchase_order = fields.Char(string="Purchase Order", compute="_compute_purchase_order", store=False)
    date_required = fields.Date(
        string="Expected Date",
        required=True,
        track_visibility="onchange",
        default=fields.Date.context_today,
        compute="compute_receipt",
        store=True
    )
    product_uom_id = fields.Many2one(
        domain="[('category_id', '=', product_uom_category_id)]"
    )
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    incoming_stock = fields.Float(compute="_compute_incoming_stock", store=True, string="Incoming Stock")
    filter_destination_warehouse_line = fields.Char(string="Filter Destination Warehouse",compute='_compute_filter_destination', store=False)

    @api.depends('company_id')
    def _compute_filter_destination(self):
        for rec in self:
            allowed_warehouse = self.env.user.warehouse_ids
            rec.filter_destination_warehouse_line = json.dumps([('branch_id', '=', rec.branch_id.id), ('company_id', '=', rec.company_id.id), ('id', 'in', allowed_warehouse.ids)])

    def _compute_purchase_order(self):
        for record in self:
            name = ",".join(record.purchase_lines.mapped('order_id.name'))
            record.purchase_order = name

    @api.onchange('dest_loc_id')
    def _compute_picking_type(self):
        for res in self:
            if res.dest_loc_id:
                if res.dest_loc_id.pick_type_id:
                    res.picking_type_dest = res.dest_loc_id.pick_type_id
                else:
                    raise ValidationError("Picking type for destination location does not exist.")

    @api.depends('product_id', 'dest_loc_id')
    def _compute_current_qty(self):
        for record in self:
            location_ids = []
            record.current_qty = 0
            if record.product_id and record.dest_loc_id:
                location_obj = self.env['stock.location']
                store_location_id = record.dest_loc_id.view_location_id.id
                addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_ids.append(location.id)
                child_location_ids = self.env['stock.location'].search([('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                final_location = child_location_ids + location_ids
                # stock_quant_ids = self.env['stock.quant'].search([('location_id', 'in', final_location), ('product_id', '=', record.product_id.id)])
                self.env.cr.execute("""
                    SELECT SUM(quantity)
                      FROM stock_quant
                    WHERE location_id in %s AND product_id = %s
                """ % (str(final_location).replace('[','(').replace(']',')') if final_location else '(null)', record.product_id.id))
                qty = self.env.cr.fetchall()
                record.current_qty = qty[0][0] or 0

    @api.depends('product_qty', 'estimated_cost')
    def _compute_price_total(self):
        for record in self:
            amount = record.product_qty * record.estimated_cost
            record.price_total = amount

    @api.onchange("product_id")
    def onchange_product_id(self):
        res = super(PurchaseRequestLine,self).onchange_product_id()
        if self.product_id:
            self.product_uom_id = self.product_id.uom_po_id.id
        return res

    @api.model
    def _calc_new_qty(self, request_line, po_line=None, new_pr_line=False):
        context = dict(self.env.context) or {}
        if po_line is not None and po_line.purchase_request_lines:
            return request_line.product_qty
        else:
            return super(PurchaseRequestLine,self)._calc_new_qty(request_line=request_line, po_line=po_line, new_pr_line=new_pr_line)

    @api.depends('product_id', 'dest_loc_id')
    def _compute_incoming_stock(self):
        for rec in self:
            incoming_stock = 0
            if rec.product_id and rec.dest_loc_id:
                location_ids = self.env['stock.location'].sudo().search([('warehouse_id','=',rec.dest_loc_id.id)])
                picking = self.env['stock.picking'].search(
                    [('state', 'not in', ['done', 'cancel', 'draft']), ('picking_type_id.code', '=', 'incoming'),
                     ('move_lines.product_id', '=', rec.product_id.id), ('location_dest_id', 'in', location_ids.ids)])
                if picking:
                    for stock in picking:
                        move_stock = stock.move_ids_without_package.filtered(
                            lambda x: x.product_id.id == rec.product_id.id)
                        if move_stock:
                            incoming_stock += sum(move_stock.mapped('remaining'))
            rec.incoming_stock = incoming_stock

class PurchaseAgreement(models.Model):
    _inherit = "purchase.agreement"

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = dict(self.env.context) or {}
        domain.extend(['|',('branch_id', '=', False), ('branch_id', 'in', self.env.branches.ids)])
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit,orderby=orderby, lazy=lazy)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',('branch_id', '=', False), ('branch_id', 'in', self.env.branches.ids)])
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def action_new_quotation(self):
        res = super(PurchaseAgreement, self).action_new_quotation()
        res['context'].update({'default_origin': self.name})
        return res

    def action_view_documents(self):
        self.ensure_one()
        return {
            'name':'Tender Documents',
            'type':'ir.actions.act_window',
            'res_model':'ir.attachment',
            'view_mode':'kanban,tree,form',
            'context': {'default_res_model': 'purchase.agreement', 'default_res_id': self.id},
            'domain':[('res_model','=','purchase.agreement'),('res_id','=',self.id)],
            'target':'current',
        }

    def action_send_tender(self):
        self.ensure_one()
        res = super(PurchaseAgreement, self).action_send_tender()
        res.update({'name': 'Send Email'})
        return res

class SplitRFQWizard(models.TransientModel):
    _inherit = 'sh.split.rfq.wizard'

    @api.onchange('split_by')
    def onchange_split_by(self):
        context = dict(self.env.context) or {}
        active_model = context.get('active_model')
        if active_model == 'purchase.order':
            purchase_id = self.env[active_model].browse(context.get('active_ids'))
            return {'domain': {'purchase_order_id': [('id', '!=', purchase_id.id)]}}
class InheritPurchaseRequestLineMakePuchaseOrder(models.TransientModel):
    _inherit = 'purchase.request.line.make.purchase.order'

    pr_id = fields.Many2one('purchase.request', string='PR')


    def mod_make_purchase_order(self):
        res = []
        if self.supplier_ids:
            for supplier in self.supplier_ids:
                self.supplier_id = supplier
                purchase_obj = self.env["purchase.order"]
                po_line_obj = self.env["purchase.order.line"]
                pr_line_obj = self.env["purchase.request.line"]
                purchase = False
                context = dict(self.env.context) or {}
                # IrConfigParam = self.env['ir.config_parameter'].sudo()
                if context.get('active_model') == "purchase.request.line":
                    purchase_order_id = self.env[context.get('active_model')].browse(context.get('active_ids'))
                    is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
                    # is_good_services_order = self.env.company.is_good_services_order
                    if is_good_services_order:
                        if all(line.is_goods_orders for line in purchase_order_id):
                            context.update({'is_goods_orders': True, 'goods_order': True, 'default_is_goods_orders': True})
                        elif all(line.is_services_orders for line in purchase_order_id):
                            context.update({'is_services_orders': True, 'services_good': True, 'default_is_services_orders': True})
                        if purchase_order_id and 'is_assets_orders' in purchase_order_id[0]._fields and \
                            all(line.is_assets_orders for line in purchase_order_id):
                            context.update({'is_assets_orders': True, 'assets_orders': True, 'default_is_assets_orders': True})
                        if purchase_order_id and 'is_rental_orders' in purchase_order_id[0]._fields and \
                            all(line.is_rental_orders for line in purchase_order_id):
                            context.update({'is_rental_orders': True, 'rentals_orders': True, 'default_is_rental_orders': True})
                    for line in purchase_order_id:
                        if not line.assigned_to:
                            line.assigned_to = self.env.user.id
                pr_qty_limit = IrConfigParam.get_param('pr_qty_limit', "no_limit")
                max_percentage = int(IrConfigParam.get_param('max_percentage', 0))
                # pr_qty_limit = self.env.company.pr_qty_limit
                # max_percentage = self.env.company.max_percentage

                recs = {}
                for item in self.item_ids:
                    product_id = item.product_id.id
                    if product_id in recs:
                        recs[product_id]['product_qty'] += item.product_qty
                        recs[product_id]['rem_qty'] += item.rem_qty
                    else:
                        recs[product_id] = {}
                        recs[product_id]['product_qty'] = item.product_qty
                        recs[product_id]['rem_qty'] = item.rem_qty

                tmp_recs = {}
                for item in self.item_ids:
                    product_id = item.product_id.id
                    if product_id in tmp_recs:
                        continue
                    else:
                        tmp_recs[product_id] = True
                        item.product_qty = recs[product_id]['product_qty']
                        item.rem_qty = recs[product_id]['rem_qty']

                    filtered_product_ids = False
                    if item.product_qty <= 0:
                        continue
                    if pr_qty_limit == 'percent':
                        percentage_qty = item.line_id.product_qty + ((item.line_id.product_qty * max_percentage) / 100)
                        calculate_qty = percentage_qty - (item.line_id.purchased_qty + item.line_id.tender_qty)
                        if item.product_qty > calculate_qty:
                            raise UserError(_("Quantity to Purchase for %s cannot request greater than %d") % (item.product_id.display_name, calculate_qty))
                    elif pr_qty_limit == 'fix':
                        calculate_qty = item.line_id.product_qty - (item.line_id.purchased_qty + item.line_id.tender_qty)
                        if item.product_qty > calculate_qty:
                            raise UserError(_("Quantity to Purchase for %s cannot request greater than %d") % (item.product_id.display_name, calculate_qty))
                    line = item.line_id
                    if self.purchase_order_id:
                        purchase = self.purchase_order_id
                        purchase._onchange_partner_invoice_id()
                        filtered_product_ids = purchase.order_line.filtered(lambda m: m.product_id.id == item.product_id.id and m.destination_warehouse_id.id == item.line_id.dest_loc_id.id)
                        purchase.analytic_account_group_ids = [(4, analytic) for analytic in line.request_id.analytic_account_group_ids.ids]
                        for filter_product in filtered_product_ids:
                            filter_product.product_qty += item.product_qty
                    if not purchase:
                        po_data = self._prepare_purchase_order(
                            line.request_id.picking_type_id,
                            line.request_id.group_id,
                            line.company_id,
                            line.origin,
                        )
                        purchase = purchase_obj.with_context(context).create(po_data)
                        purchase._onchange_partner_invoice_id()

                    # Look for any other PO line in the selected PO with same
                    # product and UoM to sum quantities instead of creating a new
                    # po line
                    domain = self._get_order_line_search_domain(purchase, item)
                    available_po_lines = po_line_obj.search(domain)
                    new_pr_line = True
                    # If Unit of Measure is not set, update from wizard.
                    if not line.product_uom_id:
                        line.product_uom_id = item.product_uom_id
                    # Allocation UoM has to be the same as PR line UoM
                    alloc_uom = line.product_uom_id
                    wizard_uom = item.product_uom_id
                    if available_po_lines and not item.keep_description:
                        new_pr_line = False
                        po_line = available_po_lines[0]
                        po_line.purchase_request_lines = [(4, line.id)]
                        po_line.move_dest_ids |= line.move_dest_ids
                        if not filtered_product_ids:
                            po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                                po_line.product_uom_qty, alloc_uom
                            )
                            wizard_product_uom_qty = wizard_uom._compute_quantity(
                                item.product_qty, alloc_uom
                            )
                            all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                            self.create_allocation(po_line, line, all_qty, alloc_uom)
                        else:
                            all_qty = po_line.product_qty
                    else:
                        po_line_data = self._prepare_purchase_order_line(purchase, item)
                        if item.keep_description:
                            po_line_data["name"] = item.name
                        if not filtered_product_ids:
                            purchase_line = po_line_obj.create(po_line_data)
                        else:
                            purchase_line = po_line_obj
                        po_line = purchase_line

                        if not filtered_product_ids:
                            po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                                po_line.product_uom_qty, alloc_uom
                            )
                            wizard_product_uom_qty = wizard_uom._compute_quantity(
                                item.product_qty, alloc_uom
                            )
                            all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                            self.create_allocation(po_line, line, all_qty, alloc_uom)
                        else:
                            all_qty = po_line.product_qty
                    new_qty = pr_line_obj._calc_new_qty(
                        line, po_line=po_line, new_pr_line=new_pr_line
                    )
                    if not filtered_product_ids:
                        po_line.product_qty = all_qty
                        po_line._onchange_quantity()
                    # The onchange quantity is altering the scheduled date of the PO
                    # lines. We do not want that:
                    date_required = item.line_id.date_required
                    po_line.date_planned = datetime(
                        date_required.year, date_required.month, date_required.day
                    )
                    res.append(purchase.id)
                    computerem = item.rem_qty - item.product_qty

                if self.purchase_order_id:
                    for pur_req_line in self.purchase_order_id:
                        order_ids = []
                        if pur_req_line.purchase_lines:
                            for pur_line in pur_req_line.purchase_lines:
                                if pur_line.id not in order_ids:
                                    order_ids.append(pur_line.id)
                        if purchase:
                            for pur_line in purchase.order_line:
                                if pur_line.id not in order_ids:
                                    order_ids.append(pur_line.id)
                        if order_ids:
                            pur_req_line.purchase_lines = [(6, 0, order_ids)]
        else:
            raise UserError(_("Enter a supplier."))
        if not res:
            return False
        return {
            "domain": [("id", "in", res)],
            "name": _("RFQ"),
            "view_mode": "tree,form",
            "res_model": "purchase.order",
            "view_id": False,
            "context": context,
            "type": "ir.actions.act_window",
        }



class MilestoneContractPurchase(models.Model):
    _name = 'milestone.contract.template.purchase'
    _description = 'Milestone Contract Purchase'

    purchase_order_id = fields.Many2one(comodel_name='purchase.order', string='PO')

    name = fields.Char(string='Milestone Name', required=True)
    checklist_template_id = fields.Many2one(comodel_name='purchase.custom.checklist.template', string='Checklist Template', domain="[('order','=','milestone')]")
    contract_term = fields.Float(string='Contract Term (%)')
    progress_paid = fields.Float("Progress Paid (%)")

class DirectPurchase(models.Model):
    _inherit = 'purchase.order'

    dp = fields.Boolean("Direct Purchase")
    branch_ids = fields.Many2many('res.branch',string="Allowed Branch", compute='compute_branch_ids', store=True)
    list_available_products = fields.Char('Available Products')
    from_purchase_request = fields.Boolean("from purchase request")
    allowed_partner_ids = fields.Many2many('res.partner')
    filter_destination_warehouse = fields.Char(string="Filter Destination Warehouse",compute='_compute_filter_destination', store=False)

    @api.depends('company_id', 'branch_id')
    def _compute_filter_destination(self):
        for rec in self:
            rec.filter_destination_warehouse = json.dumps([('branch_id', '=', rec.branch_id.id), ('company_id', '=', rec.company_id.id), ('id', 'in', self.env.user.warehouse_ids.ids)])


    def _purchase_request_line_check(self):
        for rec in self:
            if rec.from_purchase_request:
                return super()._purchase_request_line_check()
            else:
                return True

    def _purchase_request_confirm_message(self):
        for rec in self:
            if rec.from_purchase_request:
                return super()._purchase_request_confirm_message()
            else:
                return True

    @api.depends('branch_id')
    def compute_branch_ids(self):
        for rec in self:
            branch = []
            if rec.branch_id:
                if len(rec.branch_ids) > 1:
                    branch.append(rec.branch_ids[0].ids[0])
                    branch.append(rec.branch_id.id)
                    rec.branch_ids = [(6, 0, branch)]
                else:
                    if rec.from_purchase_request:
                        rec.branch_ids = [(4, rec.branch_id.id)]
                    else:
                        rec.branch_ids = [(6, 0, rec.branch_id.ids)]
            else:
                rec.branch_ids = False

    def find_product_by_brands(self, brand_ids):
        where_params = ','.join({str(brand) for brand in brand_ids})
        query = """
SELECT *
FROM product_brand_product_template_rel
WHERE product_brand_id in ({})
        """
        self.env.cr.execute(query.format(where_params))
        query_result = self.env.cr.dictfetchall()
        return query_result

    @api.onchange('company_id','partner_id','product_brand_ids')
    def set_available_product_ids(self):
        for i in self:
            list_product_ids = self.env['product.template'].search(['|',('company_ids','=',False),('company_ids','in',self.env.company.ids)]).ids
            list_product_ids = tuple(list_product_ids)
            domain = [('id','in',list_product_ids)]
            product_ids = []
            product_brand_ids = []
            product_vendor_pricelist_ids = []
            new_domain = ''
            check = False
            context = dict(self.env.context) or {}
            if context.get('goods_order'):
                domain += [('type', 'in', ('consu','product'))]
            elif context.get('services_good'):
                domain += [('type', '=', 'service')]
            elif context.get('assets_orders'):
                domain+= [('type', '=', 'asset')]
            elif context.get('rentals_orders'):
                domain += [('is_rented', '=', True)]
            if i.dp:
                domain += [('tracking', 'is', 'Null'), ('can_be_direct','=',True)]
            is_product_brand_filter = bool(self.env['ir.config_parameter'].sudo().get_param('is_product_brand_filter'))
            is_product_vendor_pricelist_filter = bool(self.env['ir.config_parameter'].sudo().get_param('is_product_vendor_pricelist_filter'))
            is_vendor_pricelist_approval_matrix = bool(self.env['ir.config_parameter'].sudo().get_param('is_vendor_pricelist_approval_matrix'))
            # is_product_brand_filter = self.env.company.is_product_brand_filter
            # is_product_vendor_pricelist_filter = self.env.company.is_product_vendor_pricelist_filter
            # is_vendor_pricelist_approval_matrix = self.env.company.is_vendor_pricelist_approval_matrix
            if is_product_brand_filter:
                if i and i.product_brand_ids:
                    product_brand_product_templates = i.find_product_by_brands(i.product_brand_ids.ids)
                    product_brand_ids += [product['product_template_id'] for product in product_brand_product_templates]
            if is_product_vendor_pricelist_filter:
                if i and i.partner_id:
                    domain_v_pricelist = "name = %s" % i.partner_id.id
                    if is_vendor_pricelist_approval_matrix:
                        domain_v_pricelist += " AND state = 'approved'"
                    # vendor_pricelists = self.env['product.supplierinfo'].search(domain_v_pricelist)
                    query = """
                        SELECT product_tmpl_id
                        FROM product_supplierinfo
                        WHERE ({})
                    """
                    self.env.cr.execute(query.format(domain_v_pricelist))
                    query_result = self.env.cr.dictfetchall()
                    vendor_pricelists = ','.join(map(str,query_result)).replace("{'product_tmpl_id': ","").replace("}","")
                    product_vendor_pricelist_ids = vendor_pricelists.split(',') if vendor_pricelists != '' else []

            if is_product_brand_filter and is_product_vendor_pricelist_filter:
                set_product_brand_ids = set(product_brand_ids)
                set_product_vendor_pricelist_ids = set(product_vendor_pricelist_ids)
                if i and i.product_brand_ids:
                    product_ids = list(set_product_brand_ids.intersection(set_product_vendor_pricelist_ids))
                else:
                    product_ids = product_vendor_pricelist_ids
                new_domain = "id in (%s)" % ','.join(map(str,product_ids))
            elif is_product_brand_filter and not is_product_vendor_pricelist_filter:
                if i and i.product_brand_ids:
                    product_ids = product_brand_ids+product_vendor_pricelist_ids
                    new_domain = "id in (%s)" % ','.join(map(str,product_ids))
            elif not is_product_brand_filter and is_product_vendor_pricelist_filter:
                product_ids = product_brand_ids+product_vendor_pricelist_ids
                new_domain = "id in (%s)" % ','.join(map(str,product_ids))

            domain += [('purchase_ok', '=', True)]
            res_domain = ""
            j = 1
            for k in domain:
                if str(k[0]) == 'type' and not "(" in str(k[2]):
                    res_domain += str(k[0]) + " " + str(k[1]) + " " + "'" + str(k[2]) + "'"
                else:
                    res_domain += str(k[0]) + " " + str(k[1]) + " " + str(k[2])
                if j < len(domain):
                    res_domain += " AND "
                j+=1
            query = """
                SELECT id
                FROM product_template
                WHERE ({})
            """
            if new_domain != '':
                if product_ids:
                    res_domain += " AND %s" % new_domain
                    check = True
                else:
                    check = False
            else:
                check = True
            if check:
                self.env.cr.execute(query.format(res_domain))
                query_result = self.env.cr.dictfetchall()
                i.list_available_products = ','.join(map(str,query_result)).replace("{'id': ","").replace("}","")
            else:
                i.list_available_products = False

class PurchaseOrderHistoryInherit(models.Model):
    _inherit = 'purchase.order.history'

    # OVERIDE
    #Reorder Button
    def purchases_reorder(self):
        vals = {"price_unit": self.price_unit,
                "product_qty": self.product_qty,
                "price_subtotal": self.price_subtotal,
                "date_planned": fields.Datetime.now()}

        if self.product_id:
            vals.update({"name": self.product_id.display_name,
                         "product_id": self.product_id.id})

        if self.product_uom:
            vals.update({"product_uom": self.product_uom.id})

        if self.order_id:
            vals.update({"order_id": self.order_id.id,
                        "analytic_tag_ids": [(6,0,self.order_id.analytic_account_group_ids.ids)],
                        })

        self.order_id.write({"order_line": [(0, 0, vals)]})
        self._cr.commit()

        return {"type": "ir.actions.client", "tag": "reload"}

    purchase_state = fields.Selection(string='Purchase State', related="order_id.state", store=True)
