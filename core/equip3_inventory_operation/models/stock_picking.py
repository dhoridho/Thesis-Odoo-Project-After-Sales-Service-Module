# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from re import findall as regex_findall
from re import split as regex_split

# import packaging
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import Warning
import pytz
from lxml import etree
from odoo.tools.float_utils import float_is_zero
from odoo.tools import float_repr

import pytz
from datetime import datetime, date, time, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import json
from odoo.addons.equip3_inventory_operation.models.qiscus_connector import qiscus_request
from odoo.http import request


class Picking(models.Model):
    _inherit = "stock.picking"


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False




    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    @api.model
    def _domain_branch_warehouse(self):
        return [('branch_id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]



    branch_id = fields.Many2one(
                    'res.branch',
                    string='Branch',
                    domain=_domain_branch,
                    default = _default_branch,
                    readonly=True,
                    states={'draft': [('readonly', False)]},
                    tracking=True,
                    required=True)

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", domain=_domain_branch_warehouse)
    is_interwarehouse_transfer = fields.Boolean(
        string="Interwarehouse Transfer")

    is_transfer_in = fields.Boolean(string="Transit In", readonly=True)
    is_transfer_out = fields.Boolean(string="Transit Out", readonly=True)
    transfer_id = fields.Many2one(
        'internal.transfer', string='Internal Transfer')
    partner_id = fields.Many2one(
        'res.partner', 'Contact',
        check_company=False, tracking=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    location_id = fields.Many2one(
        'stock.location', "Source Location",
        default=lambda self: self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id')).default_location_src_id,
        check_company=True, readonly=True, required=True, tracking=True,
        states={'draft': [('readonly', False)]})
    date_done = fields.Datetime('Date of Transfer', copy=False, tracking=True, readonly=True,
                                help="Date at which the transfer has been processed or cancelled.")
    origin = fields.Char(
        'Source Document', index=True, tracking=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Reference of the document")
    company_id = fields.Many2one(
        'res.company', string='Company', tracking=True,
        readonly=True, store=True, index=True, default=lambda self: self.env.company)
    is_show_location = fields.Boolean(
        string='Is Show Location', compute='_compute_show_location')
    # branch_id = fields.Many2one('res.branch', string="Branch", tracking=True)

    # unused field
    filter_branch_ids = fields.Many2many(
        'res.branch', string="Branches", compute='_compute_branch_ids', store=False)
    filter_source_location_ids = fields.Many2many(
        'stock.location', compute='_compute_location')
    filter_dest_location_ids = fields.Many2many(
        'stock.location', compute='_compute_location')
    filter_operation_picking_type_ids = fields.Many2many(
        'stock.picking.type', compute='_compute_picking_type')

    journal_cancel = fields.Boolean(
        string="Journal Cancel", compute='_compute_journal_entry', store=True)
    cancel_reason = fields.Text(string="Cancel Reason")
    merge_info = fields.Html(string="Merge Info", readonly=True)
    is_return_orders = fields.Boolean(
        string="Return Order", compute="_compute_is_return_order", store=False)
    internal_transfer_line_id = fields.Many2one('internal.transfer.line')
    return_date_limit = fields.Datetime(
        "Return before", copy=False, readonly=True)
    domain_analytic_account_group_ids = fields.Char('Domain Analytic Account Group', compute='_compute_domain_analytic')
    analytic_account_group_ids = fields.Many2many('account.analytic.tag', 'stock_analytic_rel', 'tag_id', 'picking_id',
                                                  copy=True, string="Analytic Groups")
    origin_src_location = fields.Char('Origin Source Location', readonly='1')
    origin_dest_location = fields.Char(
        'Origin Destination Location', readonly='1')
    process_time = fields.Char(compute="_compute_process_time", string='Processed Time String', store=True,
                               help="The time it takes to complete a transfer from Draft until Done state.")
    process_time_hours = fields.Float(compute="_compute_process_time", string='Processed Time', store=True,
                                      help="The time it takes to complete a transfer from Draft until Done state.")
    transfer_log_activity_ids = fields.One2many('transfer.log.activity', 'reference',
                                                string='Transfer Log Activity Ids')
    delivery_package_level_ids = fields.One2many(
        'stock.package_level', 'picking_id')
    show_entire_packs = fields.Boolean(
        related='picking_type_id.show_entire_packs', string='Show Entire Packs')
    mr_id = fields.Many2one('material.request', string="Material Request")
    is_mbs_on_transfer_operations = fields.Boolean(string="Transfer Operations",
                                                   compute="_compute_is_mbs_on_transfer_operations", store=False)
    is_source_package = fields.Boolean(
        string="Source Package", compute="_compute_source_package", store=False)
    rn_approval_matrix = fields.Many2one('rn.approval.matrix', string='Receiving Notes Approval Matrix', readonly='1',
                                         compute="_get_approval_matrix_rn")
    is_rn_request_approval_matrix = fields.Boolean(string="Is RN Request Approval Matrix",
        default='False', store=True, copy=False)
    state = fields.Selection(selection_add=[
        ('waiting_for_approval', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('waiting',),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")
    status_1 = fields.Selection(related='state', string='Status 1', tracking=False)
    status_2 = fields.Selection(related='state', string='Status 2', tracking=False)
    status_3 = fields.Selection(related='state', string='Status 3', tracking=False)
    status_4 = fields.Selection(related='state', string='Status 4', tracking=False)
    approved_matrix_ids = fields.One2many('rn.approval_matrix_line', 'picking_id', store=True, string="Approved Matrix",)
    approval_matrix_line_id = fields.Many2one('rn.approval_matrix_line', string='Receiving Notes Approval Matrix Line',
                                              compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(
        string='Is Approve Button', compute='_get_approve_button', store=False)
    is_reset_to_draft = fields.Boolean(
        string='Is Reset to Draft', compute='_get_is_show_draft', store=False)
    check_product = fields.Boolean(
        default=False, compute='_compute_check_product')
    active = fields.Boolean(default=True, string="Active")
    is_picking_itr = fields.Boolean(string="Is Picking ITR")
    is_adjustable_picking = fields.Boolean(
        string="Adjustable Picking", compute="_is_adjustable_picking")
    do_approval_matrix = fields.Many2one('do.approval.matrix', string='Delivery Order Approval Matrix', readonly='1',
                                         compute="_get_approval_matrix_do")
    is_do_request_approval_matrix = fields.Boolean(string="Is DO Request Approval Matrix",
        default='False', store=True, copy=False)
    do_approved_matrix_ids = fields.One2many('do.approval_matrix_line', 'picking_id', store=True,
                                             string="Delivery Order Approved Matrix",)
    do_approval_matrix_line_id = fields.Many2one('do.approval_matrix_line',
                                                 string='Delivery Order Approval Matrix Line',
                                                 compute='_get_approve_button_do', store=False)
    is_approve_button_do = fields.Boolean(
        string='Is Approve Button Delivery Order', compute='_get_approve_button_do', store=False)
    is_reset_to_draft_do = fields.Boolean(
        string='Is Reset to Draft Delivery Order', compute='_get_is_show_draft_do', store=False)
    force_validate_button = fields.Boolean(
        string='Force Validate Button', compute='_get_force_validate_button', store=False)
    current_user = fields.Boolean('is current user ?', compute='_get_current_user', default=False)
    partner_id_domain = fields.Char('Partner Id Domain', compute='_get_partner_id_domain', store=False)
    owner_id_domain = fields.Char('Owner Id Domain', compute='_get_partner_id_domain', store=False)
    journal_button = fields.Boolean('Journal', compute='_get_journal', default=False)
    picking_batch_id = fields.Many2one('stock.picking.batch', 'Picking Batch Id')
    qty_can_minus_boolean = fields.Boolean('qty', compute='_qty_can_minus_boolean', default=False)
    is_readonly_location = fields.Boolean('readonly', default=False)
    sent = fields.Boolean('Sent', default=False)
    is_invisible_button_serialize = fields.Boolean(compute='_compute_visisibility_button_serialize')
    filter_dest_location = fields.Char(compute='_compute_filter_location')
    filter_source_location = fields.Char(compute='_compute_filter_location')
    filter_operation_picking_type = fields.Char(compute='_compute_filter_picking_type')
    source_location_barcode = fields.Char('Source Location Barcode')
    destination_location_barcode = fields.Char('Destination Location Barcode')
    is_mbs_on_itr_location = fields.Boolean(string="Inter-Location mbs",
                                                   compute="_compute_is_mbs_on_itr_location")
    sales_person_id = fields.Many2one('res.users', string='Sales Person')
    is_complete_return = fields.Boolean(string="Is Complete Return", copy=False)
    account_move_id = fields.Many2one('account.move', string='Journal Entry') # 1 picking 1 account.move
    
    
    @api.onchange('source_location_barcode', 'destination_location_barcode')
    def onchange_barcode(self):
        StockLocation = self.env['stock.location']
        for record in self:
            barcodes = {
                'source_location_barcode': {
                    'location_field': 'location_id',
                    'warehouse_field': 'warehouse_id',
                },
                'destination_location_barcode': {
                    'location_field': 'location_dest_id',
                    'warehouse_field': 'warehouse_id',
                },
            }

            for field, mapping in barcodes.items():
                barcode_value = record[field]
                if barcode_value:
                    scanned_location = StockLocation.search([('barcode', '=', barcode_value)], limit=1)
                    if not scanned_location:
                        record[field] = ''
                        raise ValidationError(_('Please scan a valid location barcode. Barcode/Location not found.'))
                    setattr(record, mapping['location_field'], scanned_location.id)
                    setattr(record, mapping['warehouse_field'], scanned_location.warehouse_id.id)

            

    @api.depends('location_id', 'location_dest_id')
    def _compute_filter_picking_type(self):
        self.filter_operation_picking_type = json.dumps([])
        for record in self:
            domain = []
            if self.env.context.get('picking_type_code') == "outgoing":
                domain = [('code', '=', 'outgoing')]
            elif self.env.context.get('picking_type_code') == "incoming":
                domain = [('code', '=', 'incoming')]
            else:
                domain = []
            picking_types = self.env['stock.picking.type'].search(domain)
            record.filter_operation_picking_type = json.dumps([('id', 'in', picking_types.ids)])


    @api.depends('transfer_id', 'company_id')
    def _compute_domain_analytic(self):
        internal_type = self.env['ir.config_parameter'].sudo().get_param('internal_type')
        for record in self:
            domain = []
            if record.transfer_id:
                if internal_type == 'direct_transit':
                    domain = [('id', 'in', record.transfer_id.analytic_account_group_ids.ids)]
                elif internal_type == 'with_transit':
                    if record.is_transfer_out:
                        domain = [('id', 'in', record.transfer_id.destination_warehouse_id.branch_id.analytic_tag_ids.ids)]
                    elif record.is_transfer_in:
                        domain = [('id', 'in', record.transfer_id.source_warehouse_id.branch_id.analytic_tag_ids.ids)]
            if not domain:
                analytics = self.env['account.analytic.tag'].search([('company_id', '=', self.env.company.id)])
                domain = [('id', 'in', analytics.ids)]
            record.domain_analytic_account_group_ids = json.dumps(domain)


    @api.depends('location_id', 'location_dest_id', 'branch_id')
    def _compute_filter_location(self):
        context = self.env.context or {}
        user = self.env.user

        def search_locations(domain):
            return self.env['stock.location'].search(domain).ids

        def json_filter(location_ids):
            return json.dumps([('id', 'in', location_ids)])

        for record in self:
            if record.is_interwarehouse_transfer and record.warehouse_id:
                store_location_id = record.warehouse_id.view_location_id.id
                location_ids = search_locations([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                child_location_ids = search_locations([('id', 'child_of', location_ids), ('id', 'not in', location_ids)])
                final_location_ids = location_ids + child_location_ids
                filter_locations = json_filter(final_location_ids)
                record.filter_source_location = filter_locations
                record.filter_dest_location = filter_locations
            else:
                if user.branch_ids or user.branch_id:
                    warehouse_ids = self.env['stock.warehouse'].search([('branch_id', '=', record.branch_id.id)]).ids
                    domain = [('warehouse_id', 'in', warehouse_ids), ('usage', '=', 'internal')]
                    if user.warehouse_ids:
                        domain.append(('warehouse_id', 'in', user.warehouse_ids.ids))
                    location_ids = search_locations(domain)
                elif user.warehouse_ids:
                    location_ids = search_locations([('warehouse_id', 'in', user.warehouse_ids.ids), ('usage', '=', 'internal')])
                else:
                    location_ids = search_locations([('usage', '=', 'internal')])

                filter_locations = json_filter(location_ids)
                record.filter_source_location = filter_locations
                record.filter_dest_location = filter_locations

            if context.get('pick'):
                pick_types = self.env['stock.picking.type'].search([('sequence_code', '=', 'PICK')])
                source_ids = search_locations([('id', 'in', pick_types.default_location_src_id.ids), ('branch_id', '=', record.branch_id.id)])
                dest_ids = search_locations([('id', 'in', pick_types.default_location_dest_id.ids), ('branch_id', '=', record.branch_id.id)])
                record.filter_source_location = json_filter(source_ids)
                record.filter_dest_location = json_filter(dest_ids)
                if record.location_id:
                    operation_ids_dest = self.env['stock.picking.type'].search([('sequence_code', '=', 'PICK'), ('default_location_src_id', '=', record.location_id.id)])
                    record.location_dest_id = operation_ids_dest.default_location_dest_id.id

            if context.get('pack'):
                pack_types = self.env['stock.picking.type'].search([('sequence_code', '=', 'PACK')])
                source_ids = search_locations([('id', 'in', pack_types.default_location_src_id.ids), ('branch_id', '=', record.branch_id.id)])
                dest_ids = search_locations([('id', 'in', pack_types.default_location_dest_id.ids), ('branch_id', '=', record.branch_id.id)])
                record.filter_source_location = json_filter(source_ids)
                record.filter_dest_location = json_filter(dest_ids)
                if record.location_id:
                    operation_ids_dest = self.env['stock.picking.type'].search([('sequence_code', '=', 'PACK'), ('default_location_src_id', '=', record.location_id.id)])
                    record.location_dest_id = operation_ids_dest.default_location_dest_id.id

            if context.get('output'):
                output_types = self.env['stock.picking.type'].search([('sequence_code', '=', 'OUT')])
                source_ids = search_locations([('id', 'in', output_types.default_location_src_id.ids), ('branch_id', '=', record.branch_id.id), ('name', 'ilike', 'OUTPUT')])
                record.filter_source_location = json_filter(source_ids)
                record.location_dest_id = search_locations([('usage', '=', 'customer')])

            if not record.filter_source_location:
                record.filter_source_location = json.dumps([])
            if not record.filter_dest_location:
                record.filter_dest_location = json.dumps([])



    @api.depends('state', 'picking_type_code', 'move_lines', 'move_lines.product_id', 'move_lines.fulfillment')
    def _compute_visisibility_button_serialize(self):
        for record in self:
            record.is_invisible_button_serialize = record._is_invisible_button_serialize()

    def _is_invisible_button_serialize(self):
        self.ensure_one()
        all_lot_created = all([move.fulfillment == 100 for move in self.move_lines.filtered(lambda o: o.product_id._is_auto())])
        return self.state != 'assigned' or self.picking_type_code != 'incoming' or all_lot_created

    def _qty_can_minus_boolean(self):
        qty_can_minus = self.env['ir.config_parameter'].sudo().get_param(
            'qty_can_minus', False)
        for record in self:
            if qty_can_minus:
                record.qty_can_minus_boolean = qty_can_minus
            else:
                record.qty_can_minus_boolean = False
                
    @api.depends('state')
    def _compute_is_mbs_on_itr_location(self):
        for record in self:
            record.is_mbs_on_itr_location = False
            if record.state != 'draft':
                continue
            is_mbs_on_itr_location = eval(self.env['ir.config_parameter'].sudo().get_param(
                'equip3_inventory_accessright_setting.is_mbs_on_itr_location', 'False'))
            if is_mbs_on_itr_location:
                for record in self:
                    record.is_mbs_on_itr_location = is_mbs_on_itr_location

    @api.onchange('move_ids_without_package')
    def _onchange_new(self):
        for rec in self:
            if rec.qty_can_minus_boolean and rec.picking_type_code == 'outgoing':
                for move in rec.move_ids_without_package:
                    if move.reserved_availability:
                        if move.quantity_done > move.reserved_availability:
                            raise ValidationError('Cannot Force Transaction , the product is less than 0')
                    else:
                        stock_quant = self.env['stock.quant'].search([('product_id','=',move.product_id.id),
                                                                    ('location_id','=', move.location_id.id)])
                        total_available_quantity = sum(stock_quant.mapped('available_quantity'))
                        product_qty = move.product_uom._compute_quantity(move.product_uom_qty, move.product_id.uom_id) if move.quantity_done < 1 else move.quantity_done
                        if total_available_quantity < product_qty:
                        # if stock_quant.available_quantity < move.quantity_done:
                            raise ValidationError('Done qty is greater than the available stock')


    @api.depends('picking_type_id')
    def _get_partner_id_domain(self):
        context = dict(self.env.context)
        for rec in self:
            rec.partner_id_domain = json.dumps([])
            rec.owner_id_domain = json.dumps([])
            # if rec.picking_type_code == 'incoming':
            #     rec.partner_id_domain = json.dumps([('is_vendor', '=', True)])
            #     rec.owner_id_domain = json.dumps([('company_id', 'in', [rec.company_id.id, False])])

            # if rec.picking_type_code == 'outgoing':
            #     rec.partner_id_domain = json.dumps([('customer_rank', '>', 0)])
            #     rec.owner_id_domain = json.dumps([('company_id', 'in', [rec.company_id.id, False])])

            #  and rec.is_consignment == True
            if rec.picking_type_code == 'incoming':
                rec.partner_id_domain = json.dumps([])
                rec.owner_id_domain = json.dumps([('company_id', 'in', [rec.company_id.id, False]),('is_vendor', '=', True)])

            #  and rec.is_consignment == True
            if rec.picking_type_code == 'outgoing':
                rec.partner_id_domain = json.dumps([])
                rec.owner_id_domain = json.dumps([('company_id', 'in', [rec.company_id.id, False],('is_customer', '=', True))])


    def write(self, vals):
        res = super(Picking, self).write(vals)
        for rec in self:
            count = 0
            for move in rec.move_ids_without_package:
                if move.state in (
                        'waiting', 'confirmed', 'assigned') and not move.initial_demand and move.product_uom_qty > 0:
                    move.initial_demand = move.product_uom_qty
                count += 1
                move.move_line_sequence = count
        return res

    def _get_journal(self):
        for rec in self:
            account_move = self.env['account.move'].search([('ref', 'ilike', rec.name)])
            if account_move:
                rec.journal_button = True
            else:
                rec.journal_button = False


    def action_view_journal_in_itr(self):
        return {
           'name': ('Journal Items'), #This is form name, which you can edit according to you
           'res_model': 'account.move', #Here we will provide model name for the form view
           'type': 'ir.actions.act_window', #This is action which is predefined
           'views': [[self.env.ref('account.view_move_tree').id, 'list'], [self.env.ref('account.view_move_form').id, 'form']],
           'domain': [('ref','ilike',self.name)] #Here we are call required field, with the help of "self" which invokes a record rule
        }


    def _get_current_user(self):
        self.current_user = False
        for e in self:
            if e.purchase_id or e.sale_id:
                e.current_user = True
                break
            else:
                if e.env.user.id == e.user_id.id:
                    e.current_user = True
                    break
                else:
                    e.current_user = False

    @api.onchange('sh_stock_barcode_mobile')
    def _onchange_sh_stock_barcode_mobile(self):
        if self.sh_stock_barcode_mobile in ['', "", False, None]:
            return

        CODE_SOUND_SUCCESS = "NOTIFY_ONCE_"
        CODE_SOUND_FAIL = "NOTIFY_ONCE_"
        if self.env.company.sudo().sh_stock_bm_is_sound_on_success:
            CODE_SOUND_SUCCESS += "SH_BARCODE_MOBILE_SUCCESS_"

        if self.env.company.sudo().sh_stock_bm_is_sound_on_fail:
            CODE_SOUND_FAIL += "SH_BARCODE_MOBILE_FAIL_"

        if not self.picking_type_id:
            if self.env.company.sudo().sh_stock_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL +
                            'You must first select a Operation Type.')
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
            return

        if self and self.state not in ['assigned', 'draft', 'confirmed']:
            selections = self.fields_get()['state']['selection']
            value = next((v[1] for v in selections if v[0]
                          == self.state), self.state)
            if self.env.company.sudo().sh_stock_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL +
                            'You can not scan item in %s state.') % (value)
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
            return
        elif self:
            search_mls = False
            domain = []
            barcode_config = self.env['barcode.configuration'].search([], limit=1).barcode_type

            if self.env.company.sudo().sh_stock_barcode_mobile_type == 'barcode':
                search_mls = self.move_ids_without_package.filtered(
                    lambda ml: (ml.product_id.barcode == self.sh_stock_barcode_mobile) or
                    (ml.product_id.multi_barcode and self.sh_stock_barcode_mobile in ml.product_id.barcode_line_ids.mapped('name')))
                domain = ['|', ("barcode", "=", self.sh_stock_barcode_mobile), '&', ('multi_barcode', '=', True), ('barcode_line_ids.name', '=', self.sh_stock_barcode_mobile)]
                
                sh_it_mobile_barcode_type = self.env['ir.config_parameter'].sudo().get_param('equip3_inventory_scanning.sh_it_mobile_barcode_type', 'sku')
                if self.is_interwarehouse_transfer and sh_it_mobile_barcode_type == 'lot_serial':
                    stock_production_lot = self.env['stock.production.lot'].search([('name', '=', self.sh_stock_barcode_mobile)], limit=1)
                    domain = [('id', '=', stock_production_lot.product_id.id)]
                    search_mls = self.move_ids_without_package.filtered(
                        lambda ml: ml.product_id.id == stock_production_lot.product_id.id)
                    
            elif self.env.company.sudo().sh_stock_barcode_mobile_type == 'int_ref':
                search_mls = self.move_ids_without_package.filtered(
                    lambda ml: ml.product_id.default_code == self.sh_stock_barcode_mobile)
                domain = [("default_code", "=", self.sh_stock_barcode_mobile)]

            elif self.env.company.sudo().sh_stock_barcode_mobile_type == 'sh_qr_code':
                search_mls = self.move_ids_without_package.filtered(
                    lambda ml: ml.product_id.sh_qr_code == self.sh_stock_barcode_mobile)
                domain = [("sh_qr_code", "=", self.sh_stock_barcode_mobile)]

            elif self.env.company.sudo().sh_stock_barcode_mobile_type == 'all':
                search_mls = self.move_ids_without_package.filtered(
                    lambda ml: ml.product_id.barcode == self.sh_stock_barcode_mobile or ml.product_id.default_code == self.sh_stock_barcode_mobile or (ml.product_id.multi_barcode and self.sh_stock_barcode_mobile in ml.product_id.barcode_line_ids.mapped('name')))
                if barcode_config == 'EAN13':
                    domain = ["|", "|", "|",
                            ("default_code", "=", self.sh_stock_barcode_mobile),
                            ("barcode_ean13_value", "=", self.sh_stock_barcode_mobile),
                            ("sh_qr_code", "=", self.sh_stock_barcode_mobile),
                            '&',
                            ('multi_barcode', '=', True), ('barcode_line_ids.name', '=', self.sh_stock_barcode_mobile)
                            ]
                else:
                    domain = ["|", "|", "|",
                            ("default_code", "=", self.sh_stock_barcode_mobile),
                            ("barcode", "=", self.sh_stock_barcode_mobile),
                            ("sh_qr_code", "=", self.sh_stock_barcode_mobile),
                            '&',
                            ('multi_barcode', '=', True), ('barcode_line_ids.name', '=', self.sh_stock_barcode_mobile)
                            ]
            search_product = self.env["product.product"].search(
                        domain, limit=1)
            if search_mls and not search_product.multi_barcode:
                # internal transfer
                if self.transfer_id:
                    field_name = 'product_uom_qty'
                    for move_line in search_mls:
                        qty_done = move_line.quantity_done + 1
                        product_uom_qty = move_line.product_uom_qty
                        if field_name == 'quantity_done' and qty_done > product_uom_qty:
                            if self.env.company.sudo().sh_stock_bm_is_notify_on_fail:
                                message = _(CODE_SOUND_FAIL + 'Cannot set quantity done more than demand!.')
                                self.env['bus.bus'].sendone(
                                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
                        else:
                            move_line['quantity_done'] = qty_done
                            move_line['product_uom_qty'] = product_uom_qty + 1
                            if self.env.company.sudo().sh_stock_bm_is_notify_on_success:
                                self.sh_stock_barcode_mobile = ''
                                message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                    move_line.product_id.name, move_line[field_name])
                                self.env['bus.bus'].sendone(
                                    (self._cr.dbname, 'res.partner',
                                    self.env.user.partner_id.id),
                                    {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                else:
                    field_name = 'product_uom_qty' if self.state == 'draft' else 'quantity_done'
                    for move_line in search_mls:
                        qty_done = move_line[field_name] + 1
                        if field_name == 'quantity_done' and qty_done > move_line.product_uom_qty:
                            if self.env.company.sudo().sh_stock_bm_is_notify_on_fail:
                                message = _(CODE_SOUND_FAIL + 'Cannot set quantity done more than demand!.')
                                self.env['bus.bus'].sendone(
                                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
                        else:
                            move_line[field_name] = qty_done
                            if self.env.company.sudo().sh_stock_bm_is_notify_on_success:
                                self.sh_stock_barcode_mobile = ''
                                message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                    move_line.product_id.name, move_line[field_name])
                                self.env['bus.bus'].sendone(
                                    (self._cr.dbname, 'res.partner',
                                    self.env.user.partner_id.id),
                                    {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})

            elif search_mls and search_product.multi_barcode:
                # internal transfer
                if self.transfer_id:
                    field_name = 'product_uom_qty'
                    barcode_line = search_product.barcode_line_ids.filtered(lambda r: r.name == self.sh_stock_barcode_mobile)
                    move_line = search_mls.filtered(lambda r: r.product_id.id == search_product.id and r.product_uom.id == barcode_line[0].uom_id.id)
                    if move_line:
                        qty_done = move_line.quantity_done + 1
                        product_uom_qty = move_line.product_uom_qty
                        if field_name == 'quantity_done' and qty_done > move_line.product_uom_qty:
                            if self.env.company.sudo().sh_stock_bm_is_notify_on_fail:
                                message = _(CODE_SOUND_FAIL + 'Cannot set quantity done more than demand!.')
                                self.env['bus.bus'].sendone(
                                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
                        else:
                            move_line['quantity_done'] = qty_done
                            move_line['product_uom_qty'] = product_uom_qty + 1
                            if self.env.company.sudo().sh_stock_bm_is_notify_on_success:
                                self.sh_stock_barcode_mobile = ''
                                message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                    move_line.product_id.name, move_line[field_name])
                                self.env['bus.bus'].sendone(
                                    (self._cr.dbname, 'res.partner',
                                    self.env.user.partner_id.id),
                                    {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                    else:
                        if self.env.company.sudo().sh_stock_bm_is_add_product and search_product:
                            stock_move_vals = {
                                "name": search_product.name,
                                "product_id": search_product.id,
                                "price_unit": search_product.lst_price,
                                "location_id": self.location_id.id,
                                "location_dest_id": self.location_dest_id.id,
                                "product_uom": barcode_line[0].uom_id.id,
                                "product_uom_qty" : 1,
                                "quantity_done": 1,
                                "picking_type_id": self.picking_type_id.id
                            }
                            self.move_ids_without_package = [(0, 0, stock_move_vals)]
                            if self.env.company.sudo().sh_stock_bm_is_notify_on_success:
                                self.sh_stock_barcode_mobile = ''
                                message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                    search_product.name, 1)
                                self.env['bus.bus'].sendone(
                                    (self._cr.dbname, 'res.partner',
                                    self.env.user.partner_id.id),
                                    {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                            return
                else:
                    field_name = 'product_uom_qty' if self.state == 'draft' else 'quantity_done'
                    barcode_line = search_product.barcode_line_ids.filtered(lambda r: r.name == self.sh_stock_barcode_mobile)
                    move_line = search_mls.filtered(lambda r: r.product_id.id == search_product.id and r.product_uom.id == barcode_line[0].uom_id.id)
                    if move_line:
                        qty_done = move_line[field_name] + 1
                        if field_name == 'quantity_done' and qty_done > move_line.product_uom_qty:
                            if self.env.company.sudo().sh_stock_bm_is_notify_on_fail:
                                message = _(CODE_SOUND_FAIL + 'Cannot set quantity done more than demand!.')
                                self.env['bus.bus'].sendone(
                                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
                        else:
                            move_line[field_name] = qty_done
                            if self.env.company.sudo().sh_stock_bm_is_notify_on_success:
                                self.sh_stock_barcode_mobile = ''
                                message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                    move_line.product_id.name, move_line[field_name])
                                self.env['bus.bus'].sendone(
                                    (self._cr.dbname, 'res.partner',
                                    self.env.user.partner_id.id),
                                    {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                    else:
                        if self.env.company.sudo().sh_stock_bm_is_add_product and search_product:
                            stock_move_vals = {
                                "name": search_product.name,
                                "product_id": search_product.id,
                                "price_unit": search_product.lst_price,
                                "location_id": self.location_id.id,
                                "location_dest_id": self.location_dest_id.id,
                                "product_uom": barcode_line[0].uom_id.id,
                                field_name: 1,
                                "picking_type_id": self.picking_type_id.id
                            }
                            self.move_ids_without_package = [(0, 0, stock_move_vals)]
                            if self.env.company.sudo().sh_stock_bm_is_notify_on_success:
                                self.sh_stock_barcode_mobile = ''
                                message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                    search_product.name, 1)
                                self.env['bus.bus'].sendone(
                                    (self._cr.dbname, 'res.partner',
                                    self.env.user.partner_id.id),
                                    {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                            return

            elif self.state in ['assigned', 'draft', 'confirmed']:
                # inteernal transfer
                if self.transfer_id:
                    if self.env.company.sudo().sh_stock_bm_is_add_product and search_product:
                        stock_move_vals = {
                            "name": search_product.name,
                            "product_id": search_product.id,
                            "price_unit": search_product.lst_price,
                            "location_id": self.location_id.id,
                            "location_dest_id": self.location_dest_id.id,
                            "product_uom_qty" : 1,
                            "quantity_done": 1,
                            "picking_type_id": self.picking_type_id.id
                        }
                        if search_product.uom_id and not search_product.multi_barcode:
                            stock_move_vals.update({
                                "product_uom": search_product.uom_id.id,
                            })
                        elif search_product.multi_barcode:
                            barcode_line = search_product.barcode_line_ids.filtered(lambda r: r.name == self.sh_stock_barcode_mobile)
                            if barcode_line:
                                stock_move_vals.update({
                                    "product_uom": barcode_line[0].uom_id.id,
                                })

                        self.move_ids_without_package = [(0, 0, stock_move_vals)]
                        if self.env.company.sudo().sh_stock_bm_is_notify_on_success:
                            self.sh_stock_barcode_mobile = ''
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                search_product.name, 1)
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                        return
                    else:
                        if self.env.company.sudo().sh_stock_bm_is_notify_on_fail:
                            message = _(
                                CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
                        return
                else:
                    if self.env.company.sudo().sh_stock_bm_is_add_product and search_product:
                        field_name = "product_uom_qty" if self.state == "draft" else "quantity_done"
                        stock_move_vals = {
                            "name": search_product.name,
                            "product_id": search_product.id,
                            "price_unit": search_product.lst_price,
                            "location_id": self.location_id.id,
                            "location_dest_id": self.location_dest_id.id,
                            field_name : 1,
                            "picking_type_id": self.picking_type_id.id
                        }
                        if search_product.uom_id and not search_product.multi_barcode:
                            stock_move_vals.update({
                                "product_uom": search_product.uom_id.id,
                            })
                        elif search_product.multi_barcode:
                            barcode_line = search_product.barcode_line_ids.filtered(lambda r: r.name == self.sh_stock_barcode_mobile)
                            if barcode_line:
                                stock_move_vals.update({
                                    "product_uom": barcode_line[0].uom_id.id,
                                })

                        self.move_ids_without_package = [(0, 0, stock_move_vals)]
                        if self.env.company.sudo().sh_stock_bm_is_notify_on_success:
                            self.sh_stock_barcode_mobile = ''
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                search_product.name, 1)
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                        return
                    else:
                        if self.env.company.sudo().sh_stock_bm_is_notify_on_fail:
                            message = _(
                                CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
                        return
            else:
                if self.env.company.sudo().sh_stock_bm_is_notify_on_fail:
                    message = _(
                        CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                    self.env['bus.bus'].sendone(
                        (self._cr.dbname, 'res.partner',
                         self.env.user.partner_id.id),
                        {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

                return
        else:
            # failed message here
            if self.env.company.sudo().sh_stock_bm_is_notify_on_fail:
                message = _(
                    CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

            return


    def _get_force_validate_button(self):
        for record in self:
            record.force_validate_button = False
            for line in record.move_ids_without_package:
                if line.is_pack == True:
                    record.force_validate_button = True
                else:
                    record.force_validate_button = False
        return True

    def force_validate(self):
        self.ensure_one()
        for x in self.move_ids_without_package:
            x.quantity_done = x.product_uom_qty
        self.button_validate()
        return True


    def force_validate_is_pack(self):
        qty_per_bundle_needed = 0
        id_product_bundle = ''
        result = []
        product_in_box_first = 0
        for x in self.move_ids_without_package:
            qty_per_bundle_needed = x.qty_bundle
            id_product_bundle = self.env['product.template'].search([('id', '=' ,x.id_bundle)])

        for x in self.move_ids_without_package:
            id_product_bundle = self.env['product.template'].search([('id', '=' ,x.id_bundle)],limit=1)
            stock_quant = self.env['stock.quant'].search([('product_id', '=' ,x.product_id.id),
                                                    ('location_id' ,'=', x.location_id.id)]
                                                    ,limit=1, order = 'id desc')
            if stock_quant.available_quantity >= x.product_uom_qty:
                product_in_box_first = x.product_uom_qty
                if product_in_box_first >= 1:
                    for qty_product in id_product_bundle.bi_pack_ids:
                        if stock_quant.product_id.id == qty_product.product_id.id:
                            result.append(int(product_in_box_first / qty_product.qty_uom))


            elif stock_quant.available_quantity < x.product_uom_qty:
                product_in_box_first = stock_quant.available_quantity
                for qty_product in id_product_bundle.bi_pack_ids:
                    if stock_quant.product_id.id == qty_product.product_id.id:
                        result.append(int(product_in_box_first / qty_product.qty_uom))

        result = min(result)
        if result >= 1:
            for qty_product in id_product_bundle.bi_pack_ids:
                for x in self.move_ids_without_package:
                    if x.product_id.id == qty_product.product_id.id:
                        x.quantity_done = result * qty_product.qty_uom
        if result < 1:
            # x.quantity_done = 0
            raise ValidationError(_('%s ' 'is a product bundle, require all product need to be available', id_product_bundle.name))
            # ( nama produk bundle nya ) is a product bundle , require all product need to be available
            # raise ValidationError(_('You cannot have a receivable/payable account that is not reconcilable. (account code: %s)', account.code))
        return True


    def _is_adjustable_picking(self):
        ICP = self.env['ir.config_parameter'].sudo()
        for record in self:
            record.is_adjustable_picking = ICP.get_param(
                'is_adj_picking', False)

    @api.depends('location_dest_id','is_rn_request_approval_matrix')
    def _get_approval_matrix_rn(self):
        for record in self:
            if record.is_rn_request_approval_matrix and record.picking_type_code == 'incoming':
                rn_approval_matrix = self.env['rn.approval.matrix'].search(
                    [('warehouse_id', '=', record.location_dest_id.warehouse_id.id)], limit=1)
                record.rn_approval_matrix = rn_approval_matrix
            else:
                record.rn_approval_matrix = False

    @api.depends('location_id', 'is_do_request_approval_matrix')
    def _get_approval_matrix_do(self):
        for record in self:
            if record.is_do_request_approval_matrix and record.picking_type_code == 'outgoing':
                do_approval_matrix = self.env['do.approval.matrix'].search(
                    [('warehouse_id', '=', record.location_id.warehouse_id.id)], limit=1)
                record.do_approval_matrix = do_approval_matrix
            else:
                record.do_approval_matrix = False

    def _get_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            counter = 1
            record.approved_matrix_ids = []
            for line in sorted(record.rn_approval_matrix.rn_approval_matrix_line_ids.filtered(lambda r: not r.approved),
                                 key=lambda r: r.sequence):
                data.append((0, 0, {
                    'sequence': counter,
                    'approver': [(6, 0, line.approver.ids)],
                    'minimal_approver': line.minimal_approver,
                }))
                counter += 1
            record.approved_matrix_ids = data

    def _get_do_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            counter = 1
            record.do_approved_matrix_ids = []
            for line in record.do_approval_matrix.do_approval_matrix_line_ids:
                data.append((0, 0, {
                    'sequence': counter,
                    'approver': [(6, 0, line.approver.ids)],
                    'minimal_approver': line.minimal_approver,
                }))
                counter += 1
            record.do_approved_matrix_ids = data


    @api.onchange('location_id', 'location_dest_id')
    def show_rn_approval_matrix(self):
        # to moke approval matrix visible on create
        # is_rn_request_approval_matrix = self.env['ir.config_parameter'].sudo().get_param(
        #     'is_receiving_notes_approval_matrix', False)
        # if self.location_dest_id and self.location_dest_id.get_warehouse():
        #     search_approval_matrix = self.env['rn.approval.matrix'].sudo().search(
        #         [('warehouse_id', '=', self.location_dest_id.get_warehouse().id)], limit=1)
        #     if not search_approval_matrix:
        #         is_rn_request_approval_matrix = False

        # if not self.rn_approval_matrix:
        #     is_rn_request_approval_matrix = False

        # self.is_rn_request_approval_matrix = is_rn_request_approval_matrix

        # is_do_request_approval_matrix = self.env['ir.config_parameter'].sudo().get_param(
        #     'is_delivery_order_approval_matrix', False)

        # if self.location_dest_id and self.location_dest_id.get_warehouse():
        #     search_do_approval_matrix = self.env['do.approval.matrix'].sudo().search(
        #         [('warehouse_id', '=', self.location_dest_id.get_warehouse().id)], limit=1)
        #     if not search_do_approval_matrix:
        #         is_do_request_approval_matrix = False

        # if not self.do_approval_matrix:
        #     is_do_request_approval_matrix = False
        # self.is_do_request_approval_matrix = is_do_request_approval_matrix

        context = dict(self.env.context)
        if context.get('picking_type_code') == 'incoming':
            self.picking_type_code = 'incoming'
        else:
            self.picking_type_code = 'outgoing'

    # def _get_approve_button_from_config(self, res):
    #     is_rn_request_approval_matrix = self.env['ir.config_parameter'].sudo().get_param(
    #         'is_receiving_notes_approval_matrix', False)
    #     is_do_request_approval_matrix = self.env['ir.config_parameter'].sudo().get_param(
    #         'is_delivery_order_approval_matrix', False)
    #     for record in self:
    #         do_approval_matrix = self.env['do.approval.matrix'].search([('warehouse_id', '=', record.location_id.warehouse_id.id), ('company_id', '=', record.company_id.id)], limit=1)
    #         record.is_rn_request_approval_matrix = is_rn_request_approval_matrix
    #         record.is_do_request_approval_matrix = is_do_request_approval_matrix

    #         # FIX DO APPROVAL MATRIX
    #         if do_approval_matrix:
    #             record.is_do_request_approval_matrix = is_do_request_approval_matrix
    #         else:
    #             record.is_do_request_approval_matrix = False

    def _get_is_show_draft(self):
        for record in self:
            not_approved_lines = record.approved_matrix_ids.filtered(
                lambda r: not r.approved_users)
            if record.is_rn_request_approval_matrix and \
                    record.state == 'to_approve' and \
                    len(not_approved_lines) == len(record.approved_matrix_ids):
                record.is_reset_to_draft = True
            else:
                record.is_reset_to_draft = False

    def _get_is_show_draft_do(self):
        for record in self:
            not_approved_lines = record.do_approved_matrix_ids.filtered(
                lambda r: not r.approved_users)
            if record.is_do_request_approval_matrix and \
                    record.state == 'to_approve' and \
                    len(not_approved_lines) == len(record.do_approved_matrix_ids):
                record.is_reset_to_draft_do = True
            else:
                record.is_reset_to_draft_do = False

    @api.depends('move_ids_without_package')
    def _compute_check_product(self):
        for record in self:
            if record.move_ids_without_package:
                record.check_product = True
            else:
                record.check_product = False

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
            # for x in matrix_line:
            if len(matrix_line) == 0:
                record.is_approve_button = False
                record.approval_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.approver.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button = True
                    record.approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button = False
                    record.approval_matrix_line_id = False
            else:
                record.is_approve_button = False
                record.approval_matrix_line_id = False

    def _get_approve_button_do(self):
        for record in self:
            matrix_line = sorted(record.do_approved_matrix_ids.filtered(lambda r: not r.approved),
                                 key=lambda r: r.sequence)
            if len(matrix_line) == 0:
                record.is_approve_button_do = False
                record.do_approval_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.approver.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button_do = True
                    record.do_approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button_do = False
                    record.do_approval_matrix_line_id = False
            else:
                record.is_approve_button_do = False
                record.do_approval_matrix_line_id = False


    def _compute_source_package(self):
        for record in self:
            record.is_source_package = False
            if all(move_line.package_id for move_line in record.move_line_ids_without_package):
                record.is_source_package = True
            else:
                if all(move_id.packaging_ids for move_id in record.move_ids_without_package):
                    record.is_source_package = True

    def _check_approval_master(self):
        for record in self:
            if record.picking_type_code == 'incoming' and record.is_rn_request_approval_matrix and not record.rn_approval_matrix:
                raise ValidationError(_('Please set approval matrix for Receiving Notes first!\nContact Administrator for more details.'))

            if record.picking_type_code == 'outgoing' and record.is_do_request_approval_matrix and not record.do_approval_matrix:
                raise ValidationError(_('Please set approval matrix for Delivery Orders first!\nContact Administrator for more details.'))

    def action_request_for_approval(self):
        self.ensure_one()
        self._check_approval_master()
        if self.picking_type_code == 'incoming':
            name = 'Receiving Notes'
            action_xmlid = 'equip3_inventory_operation.stock_picking_receiving_note'
            menu_xmlid = 'equip3_inventory_operation.stock_picking_receiving_note_menu'
            lines = self.approved_matrix_ids
            self._get_approving_matrix_lines()
        else:
            name = 'Delivery Orders'
            action_xmlid = 'equip3_inventory_operation.action_delivery_order'
            menu_xmlid = 'equip3_inventory_operation.menu_delivery_order'
            lines = self.do_approved_matrix_ids
            self._get_do_approving_matrix_lines()

        values = {
            'sender': self.env.user,
            'name': name,
            'no': self.name,
            'datetime': fields.Datetime.now(),
            'action_xmlid': action_xmlid,
            'menu_xmlid': menu_xmlid
        }

        for approver in lines.mapped('approver'):
            values.update({'receiver': approver})
            qiscus_request(self, values)
        self.write({'state': 'waiting_for_approval'})

        return True

    def action_request_for_approval_do(self):
        self.ensure_one()
        self._check_approval_master()
        self.write({'state': 'waiting_for_approval'})
        self._get_do_approving_matrix_lines()
        return True

    def action_set_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            record.approved_matrix_ids.write({
                'approval_status': False,
                'approved_users': [(6, 0, [])],
                'approved': False,
                "feedback": False,
                'time_stamp': False,
                'last_approved': False,
                # 'approved': False
            })
            if record.sudo().mapped('move_ids_without_package'):
                record.sudo().mapped('move_ids_without_package').sudo().write(
                    {'state': 'draft'})
                record.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
        return True

    def action_set_to_draft_do(self):
        for record in self:
            record.write({'state': 'draft'})
            record.do_approved_matrix_ids.write({
                'approval_status': False,
                'approved_users': [(6, 0, [])],
                'approved': False,
                "feedback": False,
                'time_stamp': False,
                'last_approved': False,
                # 'approved': False
            })
            if record.sudo().mapped('move_ids_without_package'):
                record.sudo().mapped('move_ids_without_package').sudo().write(
                    {'state': 'draft'})
                record.sudo().mapped('move_ids_without_package').mapped(
                    'move_line_ids').sudo().write({'state': 'draft'})
        return True


    def action_approve(self):
        for record in self:
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.approver.ids and \
                        user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.approval_status or ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(
                        local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (
                            self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (
                            self.env.user.name, local_datetime)
                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'approval_status': name,
                        'approved_users': [(4, user.id)]})

                    if approval_matrix_line_id.minimal_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write(
                            {'time_stamp': datetime.now(), 'approved': True})

            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                record.write({'state': 'approved'})
        return True

    def action_approve_do(self):
        for record in self:
            user = self.env.user
            if record.is_approve_button_do and record.do_approval_matrix_line_id:
                do_approval_matrix_line_id = record.do_approval_matrix_line_id
                if user.id in do_approval_matrix_line_id.approver.ids and \
                        user.id not in do_approval_matrix_line_id.approved_users.ids:
                    name = do_approval_matrix_line_id.approval_status or ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(
                        local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (
                            self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (
                            self.env.user.name, local_datetime)
                    do_approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'approval_status': name,
                        'approved_users': [(4, user.id)]})

                    if do_approval_matrix_line_id.minimal_approver == len(
                            do_approval_matrix_line_id.approved_users.ids):
                        do_approval_matrix_line_id.write(
                            {'time_stamp': datetime.now(), 'approved': True})

            if len(record.do_approved_matrix_ids) == len(record.do_approved_matrix_ids.filtered(lambda r: r.approved)):
                record.write({'state': 'approved'})
        return True

    def action_reject(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'rn.matrix.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_reject_do(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'do.matrix.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.depends('transfer_log_activity_ids')
    def _compute_process_time(self):
        for res in self:
            total_seconds = 0
            for log_line in res.transfer_log_activity_ids:
                time = str(log_line.process_time).split(':')
                if len(time) == 3:
                    total_seconds += (float(time[0]) * 60 * 60) + \
                        (float(time[1]) * 60) + (float(time[2]))
            seconds = total_seconds
            seconds_in_day = 60 * 60 * 24
            seconds_in_hour = 60 * 60
            seconds_in_minute = 60
            days = seconds // seconds_in_day
            hours = (seconds - (days * seconds_in_day)) // seconds_in_hour
            minutes = (seconds - (days * seconds_in_day) -
                       (hours * seconds_in_hour)) // seconds_in_minute
            res.process_time = str(int(
                days)) + ' Days ' + str(int(hours)) + ' Hours ' + str(int(minutes)) + ' Minutes'
            res.process_time_hours = sum(
                res.transfer_log_activity_ids.mapped('process_time_hours'))

    def _get_process_time(self):
        time = fields.datetime.now() - \
            self.transfer_log_activity_ids[-1].timestamp
        days, seconds = time.days, time.seconds
        hours = days * 24 + seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        second = str('0' + str(seconds)) if seconds < 10 else str(seconds)
        minute = str('0' + str(minutes)) if minutes < 10 else str(minutes)
        hour = str('0' + str(hours)) if hours < 10 else str(hours)
        return hour + ':' + minute + ':' + second

    @api.model
    def action_internal_transfer_menu(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        internal_type = IrConfigParam.get_param(
            'internal_type', "with_transit")
        if internal_type == 'with_transit':
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_in').active = True
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_out').active = True
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_notes').active = False
        else:
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_in').active = False
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_out').active = False
            self.env.ref(
                'equip3_inventory_operation.menu_internal_transfer_notes').active = True

    def _get_processed_hours(self):
        time = fields.datetime.now() - \
            self.transfer_log_activity_ids[-1].timestamp
        hours = time.total_seconds() / 3600
        return hours

    def _get_processed_days(self, process_time):
        time = str(process_time).split(':')
        total_seconds = 0
        if len(time) == 3:
            total_seconds += (float(time[0]) * 60 * 60) + \
                (float(time[1]) * 60) + (float(time[2]))
        return round(total_seconds / 86400.00, 2)

    def _compute_branch_ids(self):
        # user = self.env.user
        # for record in self:
        #     if user.branch_ids and record.branch_id:
        #         branch_ids = user.branch_ids.ids + user.branch_id.ids
        #         record.filter_branch_ids = [(6, 0, branch_ids)]
        #     elif user.warehouse_ids and record.branch_id:
        #         warehouse_ids = self.env['stock.warehouse'].search([('id', 'in', user.warehouse_ids.ids)])
        #         branch_id = []
        #         for x in warehouse_ids:
        #             if x.branch_id.id == False:
        #                 x = str(0)
        #             branch_id.append(str(x.branch_id.id))
        #         record.filter_branch_ids = [(6, 0, (branch_id))]
        #     else:
        #         branch_ids = self.env['res.branch'].search([])
        #         record.filter_branch_ids = [(6, 0, (branch_ids).ids)]
        self.filter_branch_ids = [(5, 0, 0)]

    def transfer_log_action_assign(self):
        line_vals = []
        for rec in self:
            line_vals.append((0, 0, {'state': rec.state,
                                     'action': "Record Created",
                                     'timestamp': fields.datetime.now(),
                                     'reference': rec.id,
                                     'process_days': 00,
                                     'process_time_hours': 0,
                                     'process_time': '00:00:00',
                                     'user_id': self.env.user.id,
                                     }))
            rec.transfer_log_activity_ids = line_vals

    def transfer_log_action(self):
        line_vals = []
        for rec in self:
            if rec.transfer_log_activity_ids:
                last_record_transfer_activity = rec.transfer_log_activity_ids[-1]

                before_state_value = dict(rec.fields_get(
                    allfields=['state'])['state']['selection'])[last_record_transfer_activity.state]
                after_state_value = dict(rec.fields_get(
                    allfields=['state'])['state']['selection'])[rec.state]
                action = before_state_value + ' To ' + after_state_value
                process_time = self._get_process_time()
                process_days = self._get_processed_days(process_time)
                line_vals.append((0, 0, {
                    'state': rec.state,
                    'action': action,
                    'timestamp': fields.datetime.now(),
                    'reference': rec.id,
                    'process_time': process_time,
                    'process_time_hours': rec._get_processed_hours(),
                    'process_days': process_days,
                    'user_id': self.env.user.id, }))
                rec.transfer_log_activity_ids = line_vals
                if rec.state in ('waiting', 'confirmed', 'assigned'):
                    for move in rec.move_ids_without_package:
                        move.scheduled_date = move.date
                else:
                    pass

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.warehouse_id and self.is_interwarehouse_transfer:
            self.picking_type_id = self.warehouse_id.int_type_id.id
            self.company_id = self.warehouse_id.company_id.id
            self.branch_id = self.warehouse_id.branch_id.id

    @api.onchange('picking_type_id', 'partner_id')
    def onchange_picking_type(self):
        location_dest_id = self.location_dest_id.id
        result = super(Picking, self).onchange_picking_type()
        self._compute_branch_ids()
        self._is_adjustable_picking()
        if self.picking_type_id and self.is_interwarehouse_transfer and self.warehouse_id:
            self.location_id = False
            self.location_dest_id = False
            self._compute_location()
        else:
            self.location_dest_id = location_dest_id
        if not self.warehouse_id:
            self.company_id = self.picking_type_id.company_id.id
        return result

    def _process_internal_transfer(self):
        self.ensure_one()
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

        """ Automatically reserve the quantity in the 2nd stock.picking operation (Virtual Location/Transit → Destination Location) """
        transfer_in = self.env['stock.picking'].search([
            ('transfer_id', '=', self.transfer_id.id),
            ('is_transfer_in', '=', True)])

        if not transfer_in:
            return

        transfer_out_moves = self.move_ids_without_package

        for picking in transfer_in:

            picking.action_confirm()
            for in_move in picking.move_ids_without_package:
                out_moves = transfer_out_moves.filtered(lambda o: o.product_id == in_move.product_id)
                product_uom = in_move.product_id.uom_id
                move_uom = in_move.product_uom
                
                product = in_move.product_id
                if is_cost_per_warehouse:
                    product = product.with_context(price_for_warehouse=in_move.location_dest_id.get_warehouse().id)

                cost_method = in_move.product_id.with_company(in_move.company_id).cost_method
                standard_price_unit = 0.0
                if cost_method == 'standard':
                    standard_price_unit = product.standard_price

                move_line_vals_list = []
                total_qty_done = 0.0
                total_value = 0.0
                for svl_line in out_moves.stock_valuation_layer_ids.line_ids:
                    if cost_method == 'standard':
                        price_unit = standard_price_unit
                    else:
                        price_unit = svl_line.unit_cost
                    qty_done = product_uom._compute_quantity(abs(svl_line.quantity), move_uom)
                    move_line_vals = in_move._prepare_move_line_vals()
                    move_line_vals.update({
                        'svl_source_line_id': svl_line._source().id,
                        'qty_done': qty_done,
                        'price_unit': price_unit,
                        'lot_id': svl_line.lot_id.id
                    })
                    move_line_vals_list += [(0, 0, move_line_vals)]
                    total_qty_done += qty_done
                    total_value += qty_done * svl_line.unit_cost

                if cost_method == 'standard':
                    move_price_unit = standard_price_unit
                else:
                    move_price_unit = in_move.price_unit
                    if not float_is_zero(total_qty_done, precision_rounding=product_uom.rounding):
                        move_price_unit = total_value / total_qty_done

                in_move.write({
                    'price_unit': move_price_unit,
                    'move_line_ids': move_line_vals_list
                })
            picking.action_assign()

    def _action_done(self):
        result = super(Picking, self)._action_done()

        for picking in self:
            if picking.rma_id and picking.picking_type_code in ('outgoing', 'incoming'):
                picking._update_return_qty()
            
            if picking.is_transfer_out:
                picking._process_internal_transfer()

            if picking.picking_type_code == 'incoming':
                for move in picking.move_ids_without_package:
                    if move.location_dest_id.on_max_capacity:
                        product_qty = move.quantity_done
                        if move.location_dest_id.capacity_unit < move.location_dest_id.occupied_unit:
                            self.create_interwarehouse_transfer(move.location_dest_id, move.location_dest_id.putaway_destination, move.id, "draft", self.id)
            picking.create_no_backorder_transit()
        return result
    
    def _update_return_qty(self):
        self.ensure_one() 
        
        if not self.rma_id:
            return

        rma_picking_moves = self.rma_id.picking_id.move_ids_without_package

        origin_move_dict = {move.product_id.id: move for move in rma_picking_moves}

        for move in self.move_ids_without_package:
            move.return_qty = move.quantity_done
            move_product_id = move.product_id.id

            # Fetch corresponding move_origin from dictionary
            move_origin = origin_move_dict.get(move_product_id)

            if move_origin:
                move_origin.return_qty += move.quantity_done

                if move_origin.return_qty == move_origin.quantity_done:
                    move_origin.picking_id.is_complete_return = True
        

    def create_interwarehouse_transfer(self, location_in_id, location_out_id, stock_move, state, picking_id):
        warehouse = location_in_id.get_warehouse()
        picking = self.env['stock.picking'].browse(picking_id)
        if picking:
            move_vals = []
            move_line_vals = []
            for rec in picking:
                location_space = rec.location_dest_id.capacity_unit - rec.location_dest_id.occupied_unit
                if rec.location_dest_id.occupied_unit > rec.location_dest_id.capacity_unit:
                    diff_unit = rec.location_dest_id.occupied_unit - rec.location_dest_id.capacity_unit
                else:
                    diff_unit = rec.quantity_done
                vals_picking = {
                    'is_interwarehouse_transfer': True,
                    'warehouse_id': warehouse.id,
                    'branch_id' : self.env.branch.id,
                    'location_id': rec.location_dest_id.id,
                    'location_dest_id': rec.location_dest_id.putaway_destination.id,
                    'picking_type_id': warehouse.int_type_id.id,
                }
                for move in picking.move_ids_without_package.sorted(reverse=True):
                    # if move.location_dest_id.occupied_unit > move.location_dest_id.capacity_unit:
                    #     diff_unit = move.location_dest_id.occupied_unit - move.location_dest_id.capacity_unit
                    # else:
                    #     diff_unit = move.quantity_done
                    # location_space = location_space - 0 if move.product_id.product_tmpl_id.tracking in ('serial','lot') else abs(diff_unit)
                    # if location_space >= move.location_dest_id.capacity_unit:
                    move_vals.append([0, 0, {
                        'name': move.product_id.name,
                        'product_id': move.product_id.id,
                        'product_uom': move.product_uom.id,
                        'product_uom_qty':  abs(diff_unit),
                        'quantity_done': 0 if move.product_id.product_tmpl_id.tracking in ('serial','lot') else abs(diff_unit),
                        'location_id': move.location_dest_id.id,
                        'location_dest_id': move.location_dest_id.putaway_destination.id
                        }])

                for move_line in picking.move_line_ids_without_package.sorted(reverse=True):
                    if move_line.product_id.product_tmpl_id.tracking in('serial', 'lot'):
                        if diff_unit > 0 and move_line.lot_id.id:
                            move_line_vals.append([0,0,{
                                    'product_id': move_line.product_id.id,
                                    'product_uom_id': move_line.product_uom_id.id,
                                    'qty_done': move_line.qty_done if move_line.qty_done < diff_unit else diff_unit,
                                    'lot_id' : move_line.lot_id.id,
                                    'location_id': move_line.location_dest_id.id,
                                    'location_dest_id': move_line.location_dest_id.putaway_destination.id}])
                            diff_unit -= move_line.qty_done

            picking_id = self.env["stock.picking"].with_context(not_create_interwarehouse_transfer=True).create(vals_picking)
            picking_id.action_confirm()
            if move_vals:
                picking_id.write({'move_ids_without_package': move_vals})
            if move_line_vals:
                picking_id.write({'move_line_ids_without_package': move_line_vals})
            picking_id.button_validate()
        return True

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.move_ids_without_package:
                line.sequence = current_sequence
                current_sequence += 1
            current_sequence = 1
            for line in rec.move_line_ids_without_package:
                line.move_line_sequence = current_sequence
                current_sequence += 1

    @api.model
    def default_get(self, fields):
        context = dict(self.env.context)
        res = super(Picking, self).default_get(fields)
        if context.get('picking_type_code') == 'outgoing':
            res['location_dest_id'] = self.env.ref(
                'stock.stock_location_customers').id
        elif context.get('picking_type_code') == 'incoming':
            res['location_id'] = self.env.ref(
                'stock.stock_location_suppliers').id
        self._get_approve_button_from_config(res, context.get('picking_type_code'))
        return res

    def _get_approve_button_from_config(self, res, picking_type_code):
        rn_approval_matrix_config = self.env['ir.config_parameter'].sudo().get_param('is_receiving_notes_approval_matrix', False)
        do_approval_matrix_config = self.env['ir.config_parameter'].sudo().get_param('is_delivery_order_approval_matrix', False)
        res['is_rn_request_approval_matrix'] = rn_approval_matrix_config if picking_type_code == 'incoming' else False
        res['is_do_request_approval_matrix'] = do_approval_matrix_config if picking_type_code == 'outgoing' else False


    @api.model
    def create(self, vals):
        # picking_type_id = vals.get('picking_type_id')
        # picking_type = self.env['stock.picking.type'].browse([picking_type_id])
        # record_id = self.search([], limit=1, order='id desc')
        # check_today = False
        # if record_id and record_id.create_date.date().year == date.today().year:
        #     check_today = True
        # if not check_today:
        #     picking_type.sequence_id.number_next_actual = 1
        res = super(Picking, self).create(vals)
        # if res.picking_type_id.code == 'internal':
        #     if res.location_id.warehouse_id.id != res.location_dest_id.warehouse_id.id and \
        #             vals.get('move_ids_without_package'):
        #         move_line_vals = [(0, 0,
        #                            {
        #                                'product_id': move_line[2].get('product_id'),
        #                                'description': move_line[2].get('name'),
        #                                'qty': move_line[2].get('product_uom_qty'),
        #                                'scheduled_date': date.today(),
        #                                'uom': move_line[2].get('product_uom'),
        #                            }) for move_line in vals.get('move_ids_without_package')]
        #         itr_vals = {
        #             'requested_by': self.env.user.id,
        #             'source_warehouse_id': res.location_id.warehouse_id.id,
        #             'destination_warehouse_id': res.location_dest_id.warehouse_id.id,
        #             'source_location_id': res.location_id.id,
        #             'destination_location_id': res.location_dest_id.id,
        #             'scheduled_date': date.today(),
        #             'product_line_ids': move_line_vals,
        #         }
        #         itr_id = self.env['internal.transfer'].create(itr_vals)
        #         itr_id.onchange_source_loction_id()
        #         itr_id.onchange_dest_loction_id()
        #         itr_id.upd_source()
        #         itr_id.upd_dest()
        #         res.write({
        #             'active': False,
        #             'is_picking_itr': True,
        #         })
        #     elif res.location_id.warehouse_id.id == res.location_dest_id.warehouse_id.id:
        #         res.write({
        #             'is_interwarehouse_transfer': True,
        #             'warehouse_id': res.location_id.warehouse_id.id,
        #         })
        # if res.picking_type_id.code == 'incoming' and not res.rn_approval_matrix:
        #     res.is_rn_request_approval_matrix = False

        # self._next_by_code_for_same_warehouse(picking_type_id)

        res.transfer_log_action_assign()
        return res

    # def _next_by_code_for_same_warehouse(self, picking_type_id):
    #     type_id = self.env['stock.picking.type'].browse(picking_type_id)
    #     all_picking_type = self.env['stock.picking.type'].search(['&',
    #                                                             ('warehouse_id', '=', type_id.warehouse_id.id),
    #                                                             ('code', '=', type_id.code)])
    #     for rec in all_picking_type:
    #         rec.sequence_id.number_next_actual = type_id.sequence_id.number_next_actual


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(Picking, self).onchange_partner_id()
        self._compute_is_return_order()
        self._compute_is_mbs_on_transfer_operations()
        return res

    def _compute_is_mbs_on_transfer_operations(self):
        is_mbs_on_transfer_operations = self.env['ir.config_parameter'].sudo().get_param(
            'is_mbs_on_transfer_operations', False)
        for record in self:
            record.is_mbs_on_transfer_operations = is_mbs_on_transfer_operations

    def _compute_is_return_order(self):
        return_type = self.env['ir.config_parameter'].sudo(
        ).get_param('return_type')
        for record in self:
            if record.picking_type_code in ('incoming', 'outgoing') and return_type in ('direct_return', 'both'):
                record.is_return_orders = False
            else:
                record.is_return_orders = True

    def action_confirm(self):
        rn_approval_matrix_config = self.env['ir.config_parameter'].sudo().get_param('is_receiving_notes_approval_matrix', False)
        do_approval_matrix_config = self.env['ir.config_parameter'].sudo().get_param('is_delivery_order_approval_matrix', False)

        for rec in self:
            if rec.backorder_id:
                if rec.picking_type_code == 'incoming' and rn_approval_matrix_config:
                    rec.state = 'assigned'
                elif rec.picking_type_code == 'outgoing' and do_approval_matrix_config:
                    rec.state = 'waiting'
                else:
                    return super(Picking, self).action_confirm()
            else:
                return super(Picking, self).action_confirm()

        res = super(Picking, self).action_confirm()

        self.check_validate_order_itr()
        for record in self:
            record.transfer_log_action()
            # for move_line in record.move_ids_without_package:
            #     move_line.initial_demand = move_line.product_uom_qty
            # if record.transfer_id and record.is_transfer_in:
            #     picking_id = self.env['stock.picking'].search(
            #         [('transfer_id', '=', record.transfer_id.id), ('is_transfer_out', '=', True),
            #          ('state', '=', 'done')])
            #     if not picking_id:
            #         raise Warning(
            #             "You can only validate Operation IN if the Operation OUT is validated")
            # transit_location = self.env.ref(
            #     'equip3_inventory_masterdata.location_transit')
            # if record.location_id.id == transit_location.id:
            #     operation_out = self.env['stock.picking'].search(
            #         [('id', '=', record.id - 1)])
            #     if operation_out.state != 'done':
            #         raise Warning(
            #             "You can only validate Operation Return IN if the Operation Return OUT is validated")
            if record.is_interwarehouse_transfer:
                record.is_readonly_location = True
        return res

    def check_validate_order_itr(self):
        if self.transfer_id:
            picking_from_itr = self.env['stock.picking'].search([('transfer_id', '=', self.transfer_id.id), ('is_transfer_out', '=', True), ('state', '=', 'done')])
            if self.is_transfer_in and not picking_from_itr:
                raise Warning("You can only validate Operation IN if the Operation OUT is validated")

    def action_serialize(self):
        self.ensure_one()
        if self.env.context.get('skip_serializer', False):
            for move in self.move_lines.filtered(lambda o: o.product_id._is_auto() and o.fulfillment < 100):
                move._generate_lot_serial_numbers()
            return True

        lot_auto_moves = self.move_lines.filtered(lambda o: o.product_id._is_lot_auto() and o.fulfillment < 100)
        if lot_auto_moves:
            context = dict(self._context or {})
            context.update({
                'default_picking_id': self.id,
            })
            return {
                'name': 'Lot Serializer',
                'view_mode': 'form',
                'res_model': 'stock.lot.serialize',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'context': context,
                'target': 'new',
            }
        return self.with_context(skip_serializer=True).action_serialize()

    def action_assign(self):
        self.ensure_one()

        res = super(Picking, self).action_assign()
        if self.transfer_id and self.is_transfer_in:
            picking_id = self.env['stock.picking'].search(
                [('transfer_id', '=', self.transfer_id.id), ('is_transfer_out', '=', True), ('state', '=', 'done')])
            if not picking_id:
                raise Warning(
                    "You can only validate Operation IN if the Operation OUT is validated")
        return res


    @api.onchange('location_id', 'location_dest_id')
    def onchange_location_id(self):
        context = dict(self.env.context) or {}
        if self.is_picking_itr:
            raise ValidationError(
                'Cannot Change Location once Internal Transfer Request Created!')
        if self.is_interwarehouse_transfer:
            self.move_ids_without_package = [(5,0,0)]
        if not self.is_interwarehouse_transfer:
            self._compute_picking_type()
            self._compute_location()
            self._compute_show_location()
            picking_type_id = False
            if self.location_id and self.location_dest_id.usage == 'customer':
                picking_type_id = self.env['stock.picking.type'].search(
                    [('default_location_src_id', '=', self.location_id.id), ('code', '=', 'outgoing'),
                     ('default_location_dest_id', '=', False), ('warehouse_id',
                                                                '=', self.location_id.warehouse_id.id)
                     ], limit=1
                )
            elif self.location_dest_id and self.location_id.usage == 'supplier':
                picking_type_id = self.env['stock.picking.type'].search(
                    [('default_location_src_id', '=', False), ('code', '=', 'incoming'),
                     ('default_location_dest_id', '=', self.location_dest_id.id),
                     ('warehouse_id', '=', self.location_dest_id.warehouse_id.id)
                     ], limit=1
                )
            elif self.location_id.warehouse_id.id == self.location_dest_id.warehouse_id.id:
                picking_type_id = self.location_id.warehouse_id.int_type_id.id
            elif self.location_id and self.location_dest_id and self.location_id.warehouse_id.id != self.location_dest_id.warehouse_id.id:
                picking_type_id = self.location_id.warehouse_id.int_type_id.id
            if context.get('pick') and self.location_id and self.location_dest_id:
                operation_ids = self.env['stock.picking.type'].search([('default_location_src_id', '=', self.location_id.id),
                                                               ('sequence_code','=', 'PICK')],limit=1)
                picking_type_id = operation_ids.id
            if context.get('pack') and self.location_id and self.location_dest_id:
                operation_ids = self.env['stock.picking.type'].search([('default_location_src_id', '=', self.location_id.id),
                                                                    ('sequence_code','=', 'PACK')],limit=1)
                picking_type_id = operation_ids.id
            if context.get('output') and self.location_id and self.location_dest_id:
                operation_ids = self.env['stock.picking.type'].search([('default_location_src_id', '=', self.location_id.id),
                                                                    ('sequence_code','=', 'OUT')],limit=1)
                picking_type_id = operation_ids.id
            self.picking_type_id = picking_type_id

    def _compute_show_location(self):
        context = dict(self.env.context) or {}
        for record in self:
            record.is_show_location = False

    @api.depends('move_ids_without_package', 'move_ids_without_package.account_move_ids',
                 'move_ids_without_package.account_move_ids.state')
    def _compute_journal_entry(self):
        for record in self:
            account_move_ids = record.move_ids_without_package.mapped(
                'account_move_ids')
            if account_move_ids and all(move.state == 'cancel' for move in account_move_ids):
                record.journal_cancel = True
            else:
                record.journal_cancel = False

    def _compute_picking_type(self):
        # for record in self:
        #     domain = []
        #     if self.env.context.get('picking_type_code') == "outgoing":
        #         domain = [('code', '=', 'outgoing')]
        #     elif self.env.context.get('picking_type_code') == "incoming":
        #         domain = [('code', '=', 'incoming')]
        #     else:
        #         domain = []

        #     picking_types = self.env['stock.picking.type'].search(domain)
        #     record.filter_operation_picking_type_ids = [(6, 0, picking_types.ids)]
        self.filter_operation_picking_type_ids = [(5, 0, 0)]

    @api.onchange('branch_id', 'location_id', 'location_dest_id')
    def _onchange_branch_id_picking_operation(self):
        context = dict(self.env.context) or {}
        for record in self:
            if context.get('picking_type_code') == "outgoing":
                if record.branch_id.id != record.location_id.branch_id.id:
                    record.location_id = False
            elif context.get('picking_type_code') == "incoming":
                if record.branch_id.id != record.location_dest_id.branch_id.id:
                    record.location_dest_id = False
            else:
                if record.branch_id.id != record.location_dest_id.branch_id.id:
                    record.location_dest_id = False
                if record.branch_id.id != record.location_id.branch_id.id:
                    record.location_id = False


    @api.depends('branch_id')
    def _compute_location(self):
        context = dict(self.env.context) or {}
        self.filter_source_location_ids = [(5, 0, 0)]
        self.filter_dest_location_ids = [(5, 0, 0)]
        # stock_locations_ids = self.env['stock.location'].search([])
        # for record in self:
            # if record.is_interwarehouse_transfer:
            #     location_ids = []
            #     if record.warehouse_id:
            #         location_obj = record.env['stock.location']
            #         store_location_id = record.warehouse_id.view_location_id.id
            #         addtional_ids = location_obj.search(
            #             [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
            #         for location in addtional_ids:
            #             if location.location_id.id not in addtional_ids.ids:
            #                 location_ids.append(location.id)
            #         child_location_ids = record.env['stock.location'].search(
            #             [('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
            #         final_location = child_location_ids + location_ids
            #         record.filter_source_location_ids = [
            #             (6, 0, final_location)]
            #         record.filter_dest_location_ids = [(6, 0, final_location)]
                # else:

            # else:
            #     user = self.env.user
            #     if self.branch_id:
            #         warehouse_ids = self.env['stock.warehouse'].search([('branch_id', '=', self.branch_id.id)])
            #         if user.warehouse_ids:
            #             location_ids = self.env['stock.location'].search(['&','&', ('warehouse_id', 'in', warehouse_ids.ids),('warehouse_id', 'in', user.warehouse_ids.ids), ('usage', '=', 'internal')])
            #         else:
            #             location_ids = self.env['stock.location'].search(['&', ('warehouse_id', 'in', warehouse_ids.ids), ('usage', '=', 'internal')])
            #         if context.get('picking_type_code') == "outgoing":
                        # record.filter_dest_location_ids = [(6, 0, stock_locations_ids.filtered(
                        #     lambda r: r.usage != 'internal' and r.branch_id.id in branch_ids).ids)]
                        # record.filter_source_location_ids = [(6, 0, stock_locations_ids.filtered(
                        #     lambda r: r.usage == 'internal' and r.branch_id.id in branch_ids).ids)]
                        # warehouse_filtered_by_branch = self.env['stock.warehouse'].search([('branch_id', '=', branch_ids.id)])
                    #     record.filter_dest_location_ids = [(6, 0, (location_ids).ids)]
                    #     record.filter_source_location_ids = [(6, 0, (location_ids).ids)]

                    # elif context.get('picking_type_code') == "incoming":
                        # location_filtered_by_branch = self.env['stock.warehouse'].search([('branch_id', '=', branch_ids.id)])
            #             record.filter_dest_location_ids = [(6, 0, (location_ids).ids)]
            #             record.filter_source_location_ids = [(6, 0, (location_ids).ids)]
            #         else:
            #             record.filter_dest_location_ids = [
            #                 (6, 0, (location_ids).ids)]
            #             record.filter_source_location_ids = [
            #                 (6, 0, (location_ids).ids)]
            #     else:
            #         if user.branch_ids.ids or user.branch_id.id:
            #             warehouse_ids = self.env['stock.warehouse'].search(['|', '|',('branch_id', '=', user.branch_id.id), ('branch_id', '=', user.branch_ids.ids),('branch_id', '=', None)])
            #             if user.warehouse_ids:
            #                 location_ids = self.env['stock.location'].search(['&', ('warehouse_id', 'in', user.warehouse_ids.ids), ('usage', '=', 'internal')])
            #             else:
            #                 location_ids = self.env['stock.location'].search(['&', ('warehouse_id', 'in', warehouse_ids.ids), ('usage', '=', 'internal')])
            #             if context.get('picking_type_code') == "outgoing":
            #                 record.filter_dest_location_ids = [(6, 0, (location_ids).ids)]
            #                 record.filter_source_location_ids = [(6, 0, (location_ids).ids)]
            #             elif context.get('picking_type_code') == "incoming":
            #                 record.filter_dest_location_ids = [(6, 0, (location_ids).ids)]
            #                 record.filter_source_location_ids = [(6, 0, (location_ids).ids)]
            #             else:
            #                 record.filter_dest_location_ids = [
            #                     (6, 0, (location_ids).ids)]
            #                 record.filter_source_location_ids = [
            #                     (6, 0, (location_ids).ids)]
            #         elif user.warehouse_ids.ids:
            #             location_ids = self.env['stock.location'].search(['&', ('warehouse_id', 'in', user.warehouse_ids.ids), ('usage', '=', 'internal')])
            #             if context.get('picking_type_code') == "outgoing":
            #                 record.filter_dest_location_ids = [(6, 0, (location_ids).ids)]
            #                 record.filter_source_location_ids = [(6, 0, (location_ids).ids)]
            #             elif context.get('picking_type_code') == "incoming":
            #                 record.filter_dest_location_ids = [(6, 0, (location_ids).ids)]
            #                 record.filter_source_location_ids = [(6, 0, (location_ids).ids)]
            #             else:
            #                 record.filter_dest_location_ids = [
            #                     (6, 0, (location_ids).ids)]
            #                 record.filter_source_location_ids = [
            #                     (6, 0, (location_ids).ids)]
            #         else:
            #             location_ids = self.env['stock.location'].search([('usage', '=', 'internal')])
            #             if context.get('picking_type_code') == "outgoing":
            #                 record.filter_dest_location_ids = [(6, 0, (location_ids).ids)]
            #                 record.filter_source_location_ids = [(6, 0, (location_ids).ids)]
            #             elif context.get('picking_type_code') == "incoming":
            #                 record.filter_dest_location_ids = [(6, 0, (location_ids).ids)]
            #                 record.filter_source_location_ids = [(6, 0, (location_ids).ids)]
            #             else:
            #                 record.filter_dest_location_ids = [
            #                     (6, 0, (location_ids).ids)]
            #                 record.filter_source_location_ids = [
            #                     (6, 0, (location_ids).ids)]

            # if context.get('pick'):
            #     operation_ids = self.env['stock.picking.type'].search([('sequence_code', '=', 'PICK')])
            #     source_location_ids = self.env['stock.location'].search([('id', 'in', operation_ids.default_location_src_id.ids),
            #                                                              ('branch_id', '=', self.branch_id.id)])
            #     record.filter_source_location_ids = [(6, 0, (source_location_ids).ids)]
            #     dest_location_ids = self.env['stock.location'].search([('id', 'in', operation_ids.default_location_dest_id.ids),
            #                                                            ('branch_id', '=', self.branch_id.id)])
            #     record.filter_dest_location_ids = [(6, 0, (dest_location_ids).ids)]
            #     if self.location_id:
            #         operation_ids_dest = self.env['stock.picking.type'].search([('sequence_code', '=', 'PICK'),
            #                                                                     ('default_location_src_id','=', self.location_id.id)])
            #         self.location_dest_id = operation_ids_dest.default_location_dest_id.id

            # if context.get('pack'):
            #     operation_ids = self.env['stock.picking.type'].search([('sequence_code', '=', 'PACK')])
            #     source_location_ids = self.env['stock.location'].search([('id', 'in', operation_ids.default_location_src_id.ids),
            #                                                              ('branch_id', '=', self.branch_id.id)])
            #     record.filter_source_location_ids = [(6, 0, (source_location_ids).ids)]
            #     dest_location_ids = self.env['stock.location'].search([('id', 'in', operation_ids.default_location_dest_id.ids),
            #                                                            ('branch_id', '=', self.branch_id.id)])
            #     record.filter_dest_location_ids = [(6, 0, (dest_location_ids).ids)]
            #     if self.location_id:
            #         operation_ids_dest = self.env['stock.picking.type'].search([('sequence_code', '=', 'PACK'),
            #                                                                     ('default_location_src_id','=', self.location_id.id)])
            #         self.location_dest_id = operation_ids_dest.default_location_dest_id.id
            # if context.get('output'):
            #     operation_ids = self.env['stock.picking.type'].search([('sequence_code', '=', 'OUT')])
            #     source_location_ids = self.env['stock.location'].search([('id', 'in', operation_ids.default_location_src_id.ids),
            #                                                              ('branch_id', '=', self.branch_id.id),
            #                                                              ('name', 'ilike', 'OUTPUT')])
            #     record.filter_source_location_ids = [(6, 0, (source_location_ids).ids)]
            #     self.location_dest_id = self.env['stock.location'].search([('usage', '=', 'customer')])
            # if context.get('picking_type_code') == 'incoming' and record.location_dest_id.branch_id != False:
            #     if record.location_dest_id.branch_id != record.branch_id:
            #         self.location_dest_id = False

    def _check_limits(self, picking_type_code, limit_type_attr, min_qty_attr, max_qty_attr, action_verb):
        error_list = []

        pickings = self.filtered(lambda p: p.picking_type_code == picking_type_code)

        for picking in pickings:
            for line in picking.move_ids_without_package:
                product = line.product_id
                qty_done = line.quantity_done
                qty_demand = line.product_uom_qty
                
                if line.initial_unit_of_measure and line.initial_unit_of_measure != line.product_uom:
                    qty_done = line.product_uom._compute_quantity(qty_done, line.initial_unit_of_measure)

                # Get limit settings from product category
                limit_type = getattr(product.categ_id, limit_type_attr)
                min_qty = getattr(product.categ_id, min_qty_attr)
                max_qty = getattr(product.categ_id, max_qty_attr)

                # Override with product-specific limits if set and not 'no_limit'
                if getattr(product, limit_type_attr) and getattr(product, limit_type_attr) != 'no_limit':
                    limit_type = getattr(product, limit_type_attr)
                    min_qty = getattr(product, min_qty_attr)
                    max_qty = getattr(product, max_qty_attr)

                if limit_type == 'no_limit':
                    continue

                if limit_type == 'str_rule' and qty_demand != qty_done:
                    error_list.append(f'{product.name} must be {action_verb} exactly at {qty_demand}')
                elif limit_type == 'limit_per':
                    percentage_done = (qty_done / qty_demand) * 100
                    if not (min_qty <= percentage_done <= max_qty):
                        error_list.append(f'{product.name} must be {action_verb} between {min_qty}% and {max_qty}%')
                elif limit_type == 'limit_amount':
                    if not (min_qty <= qty_done <= max_qty):
                        error_list.append(f'{product.name} must be {action_verb} between {min_qty} and {max_qty}')

        if error_list:
            raise ValidationError('\n'.join(error_list))

    def _check_product_limit(self):
        self._check_limits(
            picking_type_code='incoming',
            limit_type_attr='product_limit',
            min_qty_attr='min_val',
            max_qty_attr='max_val',
            action_verb='received'
        )

    def _check_delivery_limit(self):
        self._check_limits(
            picking_type_code='outgoing',
            limit_type_attr='delivery_limit',
            min_qty_attr='delivery_limit_min_val',
            max_qty_attr='delivery_limit_max_val',
            action_verb='delivered'  
        )

    def _check_missing_account_itr(self):
        for rec in self:
            if rec.transfer_id:
                for line in rec.move_ids_without_package:
                    if not line.product_id.categ_id.stock_transfer_transit_account_id:
                        raise Warning(_(f'Please set up stock transfer transit account in product category for category {line.product_id.categ_id.display_name}'))

    def button_validate(self):
        self._check_product_limit()
        self._check_delivery_limit()
        self._check_missing_account_itr()
        pickings_without_quantities = self.browse()
        for record in self:
            # picking.message_subscribe([self.env.user.partner_id.id])
            # picking_type = picking.picking_type_id
            precision_digits = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            no_quantities_done = all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in record.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
            no_reserved_quantities = all(float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in record.move_line_ids)
            if no_reserved_quantities and no_quantities_done:
                pickings_without_quantities |= record
            if not self._should_show_transfers():
                if pickings_without_quantities:
                    for rec in record.move_ids_without_package:
                        if rec.is_pack == True:
                            self.force_validate_is_pack()
                        else:
                            raise UserError(self._get_without_quantities_error_message())
        res = super(Picking, self).button_validate()
        for record in self:
            if record.transfer_id and record.is_transfer_in:
                picking_id = self.env['stock.picking'].search(
                    [('transfer_id', '=', record.transfer_id.id), ('is_transfer_out', '=', True),
                     ('state', '=', 'done')])
                if not picking_id:
                    raise Warning(
                        "You can only validate Operation IN if the Operation OUT is validated")
            if record.state == 'done' and record.transfer_id:
                record.transfer_id.calculate_transfer_qty(record)
                if record.is_transfer_out or record.is_transfer_in:
                    for move in record.move_ids_without_package:
                        analytic_tag_ids = move.analytic_account_group_ids.mapped(
                            'analytic_distribution_ids')
                        for analytic_distribution_id in analytic_tag_ids:
                            vals = {
                                'name': move.product_id.name,
                                'account_id': analytic_distribution_id.account_id.id,
                                'tag_ids': [(6, 0, analytic_distribution_id.tag_id.ids)],
                                'partner_id': move.picking_id.partner_id.id,
                                'company_id': move.picking_id.company_id.id,
                                'amount': sum(move.stock_valuation_layer_ids.mapped('value')),
                                'unit_amount': move.quantity_done,
                                'product_id': move.product_id.id,
                                'product_uom_id': move.product_uom.id,
                                'general_account_id': move.product_id.categ_id.property_stock_valuation_account_id.id,
                            }
                            analytic_entry_id = self.env['account.analytic.line'].create(
                                vals)
            # if record.transfer_id and record.transfer_id.is_transit and record.is_transfer_in and not record.backorder_id:
            #     for line in record.move_line_ids_without_package:
            #         transist_line = record.transfer_id.product_line_ids.filtered(lambda r: r.product_id.id == line.product_id.id)
            #         transist_line.write({'transfer_qty': line.qty_done})
            # if record.transfer_id and not record.transfer_id.is_transit and record.backorder_id:
            #     for line in record.move_line_ids_without_package:
            #         transist_line = record.transfer_id.product_line_ids.filtered(lambda r: r.product_id.id == line.product_id.id)
            #         for trns_line in transist_line:
            #             trns_line.transfer_qty += line.qty_done
            if record.transfer_id and 'Return' in record.origin:
                for line in record.move_line_ids_without_package:
                    transist_line = record.transfer_id.product_line_ids.filtered(
                        lambda r: r.product_id.id == line.product_id.id)
                    transist_line.write({'return_qty': line.qty_done})

            return_date = fields.Datetime.now() + timedelta(
                days=int(self.env["ir.config_parameter"].sudo().get_param("return_policy_days")))
            record.write({"return_date_limit": return_date})

            if record.transfer_id and record.is_transfer_out:
                picking_id = self.env['stock.picking'].search(
                    [('transfer_id', '=', record.transfer_id.id), ('is_transfer_in', '=', True)], limit=1)
                for move in picking_id.move_ids_without_package:
                    move.is_transfer_out = True
            for move in record.move_ids_without_package:
                for lot in move.lot_ids:
                    if lot.alert_date and lot.expiration_date:
                        lot.alert_date = lot.expiration_date - \
                            timedelta(days=lot.product_id.alert_time)
            ml_sequence = 1
            for line in record.move_line_ids_without_package:
                line.move_line_sequence = ml_sequence
                ml_sequence += 1

            # for move_ids_without_package in self.move_ids_without_package:
            #     move_ids_without_package.lot_ids.expiration_date = move_ids_without_package.exp_date

            if record.state == 'done' and record.move_ids_without_package:
                no = 0
                for x in record.move_ids_without_package:
                    if x.picking_code == 'incoming':
                        pass
                for x1 in record.move_line_nosuggest_ids:
                    for i in x1.result_package_id:
                        for quant in i.quant_ids:
                            if quant.product_id.product_tmpl_id.tracking != 'none':
                                quant[0].sudo().unlink()
                            else:
                                pass
            if record.picking_batch_id:
                for batch in record.picking_batch_id.stock_picking_batch_ids:
                    if batch.transfer_id.id == record.id:
                        batch.done_qty = batch.reserved_qty
                        batch.reserved_qty = 0
        return res

    # def create_interwarehouse_transfer(self, location_in_id, location_out_id, stock_move, state, picking_id):
    #     warehouse = location_in_id.get_warehouse()
    #     stock_move = self.env['stock.move'].browse(stock_move)
    #     picking = self.env['stock.picking'].browse(picking_id)
    #     if stock_move:
    #         for rec in stock_move:
    #             location_space = rec.location_dest_id.capacity_unit - rec.location_dest_id.occupied_unit
    #             if rec.location_dest_id.occupied_unit > rec.location_dest_id.capacity_unit:
    #                 diff_unit = rec.location_dest_id.occupied_unit - rec.location_dest_id.capacity_unit
    #             else:
    #                 diff_unit = rec.quantity_done
    #             vals = {
    #                 'is_interwarehouse_transfer': True,
    #                 'warehouse_id': warehouse.id,
    #                 'branch_id' : self.env.branch.id,
    #                 'location_id': stock_move.location_dest_id.id,
    #                 'location_dest_id': stock_move.location_dest_id.putaway_destination.id,
    #                 'picking_type_id': warehouse.int_type_id.id,
    #                 'branch_id': warehouse.int_type_id.branch_id.id,
    #                 'move_ids_without_package': [(0, 0, {
    #                     'name': stock_move.product_id.name,
    #                     'product_id': stock_move.product_id.id,
    #                     'product_uom': stock_move.product_uom.id,
    #                     'product_uom_qty': abs(diff_unit),
    #                     'quantity_done': 0 if stock_move.product_id.product_tmpl_id.tracking in ('serial','lot') else abs(diff_unit),
    #                     'location_id': stock_move.location_dest_id.id,
    #                     'location_dest_id': stock_move.location_dest_id.putaway_destination.id
    #                 })],
    #             }
    #         lot_vals = []
    #         for sml in picking.move_line_ids_without_package:
    #             if sml.product_id.product_tmpl_id.tracking in('serial', 'lot'):
    #                 if diff_unit > 0 and sml.lot_id.id:
    #                     lot_vals.append([0,0,{
    #                             'product_id': sml.product_id.id,
    #                             'product_uom_id': sml.product_uom_id.id,
    #                             'qty_done': sml.qty_done if sml.qty_done < diff_unit else diff_unit,
    #                             'lot_id' : sml.lot_id.id,
    #                             'location_id': sml.location_dest_id.id,
    #                             'location_dest_id': sml.location_dest_id.putaway_destination.id}])
    #                     diff_unit -= sml.qty_done
    #         picking_id = self.env["stock.picking"].with_context(not_create_interwarehouse_transfer=True).create(vals)
    #         picking_id.write({'branch_id' : self.env.branch.id})
    #         picking_id.action_confirm()
    #         if lot_vals:
    #             picking_id.write({'move_line_ids_without_package': lot_vals})
    #         picking_id.button_validate()
    #     return True

    def _get_next_sequence_and_serial(self, moves):
        self.ensure_one()

        if self.picking_type_code not in ('incoming', 'outgoing'):
            return

        for product in moves.mapped('product_id'):
            product_moves = moves.filtered(lambda o: o.product_id == product)
            product._update_current_sequence(product_moves)

    def _check_entire_pack(self):
        """ This function check if entire packs are moved in the picking"""
        if any(picking.picking_type_code == 'outgoing' for picking in self):
            for picking in self:
                origin_packages = picking.move_line_ids.mapped("package_id")
                for pack in origin_packages:
                    package_level_ids = picking.package_level_ids.filtered(
                        lambda pl: pl.package_id == pack)
                    move_lines_to_pack = picking.move_line_ids.filtered(
                        lambda ml: ml.package_id == pack and not ml.result_package_id)
                    if package_level_ids:
                        package_level_ids.unlink()
                    for move_line in move_lines_to_pack:
                        package_qty = sum(
                            pack.quant_ids.filtered(lambda r: r.product_id.id == move_line.product_id.id).mapped(
                                'quantity'))
                        occupancy = ""
                        if move_line.product_uom_qty == package_qty:
                            occupancy = "full"
                        elif move_line.product_uom_qty < package_qty:
                            occupancy = "partial"
                        package_level_id = self.env['stock.package_level'].create({
                            'picking_id': picking.id,
                            'package_id': pack.id,
                            'location_id': pack.location_id.id,
                            'product_id': move_line.product_id.id,
                            'occupancy': occupancy,
                            'location_dest_id': self._get_entire_pack_location_dest(
                                move_line) or picking.location_dest_id.id,
                            'move_line_ids': [(6, 0, move_line.ids)] if picking.picking_type_code != 'outgoing' else [],
                            'company_id': picking.company_id.id,
                        })
        else:
            return super(Picking, self)._check_entire_pack()

    def do_unreserve(self):
        self.ensure_one()
        self.move_lines._do_unreserve()
        return True

    def button_action_cancel(self):
        context = dict(self.env.context) or {}
        context.update({'active_ids': self.ids})
        return {
            'name': 'Cancel Picking',
            'view_mode': 'form',
            'res_model': 'cancel.picking',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(Picking, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        if view_type == 'form' and self.env.context.get("date_done_string"):
            doc = etree.XML(result['arch'])
            date_done_reference = doc.xpath("//field[@name='date_done']")
            date_done_reference[0].set(
                "string", self.env.context.get("date_done_string"))
            result['arch'] = etree.tostring(doc, encoding='unicode')
        return result


    def validate_picking_transfer(self):
        records_to_process = self.filtered(lambda o: o.state != 'done' and o.transfer_id)

        for record in records_to_process.filtered(lambda o: not o.transfer_id.is_transit and o.state != 'done'):
            for move in record.move_ids_without_package:
                move.quantity_done = move.product_uom_qty
            record.action_confirm()
            record.action_assign()
            record.button_validate()

        for record in records_to_process.filtered(lambda o: o.transfer_id.is_transit and o.is_transfer_out and o.state != 'done'):
            for move in record.move_ids_without_package:
                move.quantity_done = move.product_uom_qty
            record.action_confirm()
            record.action_assign()
            record.button_validate()

        for record in records_to_process.filtered(lambda o: o.transfer_id.is_transit and o.is_transfer_in):
            record.button_validate()

    def _create_backorder(self):
        backorders = super(Picking, self)._create_backorder()
        is_approval_rn = self.env['ir.config_parameter'].sudo().get_param('is_receiving_notes_approval_matrix')
        is_approval_do = self.env['ir.config_parameter'].sudo().get_param('is_delivery_order_approval_matrix')
        if is_approval_rn and backorders.picking_type_id.code == 'incoming':
            backorders.write({'state': 'draft'})
        if is_approval_do and backorders.picking_type_id.code == 'outgoing':
            backorders.write({'state': 'draft'})
        return backorders

    def create_no_backorder_transit(self):
        """Creates a transit picking no backorder."""
        context = self.env.context
        if context.get('active_model') != 'internal.transfer' or not context.get('picking_ids_not_to_backorder'):
            return

        picking_out = self._get_transit_picking_out(self.transfer_id)
        if self.transfer_id and self.transfer_id.is_transit and self._has_pending_backorder():
            self._prepare_create_backorder_move(self, picking_out)

    def _get_transit_picking_out(self, transfer_id):
        return self.env['stock.picking'].search(
            [('transfer_id', '=', transfer_id.id), ('is_transfer_out', '=', True)],
            limit=1, order='id asc'
        )

    def _has_pending_backorder(self):
        """Checks if there are pending "no backorders"."""
        return any(move.quantity_done < move.product_uom_qty for move in self.move_ids_without_package)

    def _prepare_create_backorder_move(self, current_picking, picking_out):
        transit_location_id = self.env.ref('equip3_inventory_masterdata.location_transit')
        
        operation_type_id = self.env['stock.picking.type'].search([
            ('default_location_src_id', '=', transit_location_id.id),
            ('default_location_dest_id', '=', picking_out.location_id.id)
        ], limit=1)

        move_ids = self._get_backorder_move_lines(current_picking)
        if not move_ids:
            return
        
        picking_vals = {
            'transfer_id': current_picking.transfer_id.id,
            'picking_type_id': operation_type_id.id,
            'partner_id': current_picking.partner_id.id,
            'branch_id': current_picking.branch_id.id,
            'location_id': current_picking.location_id.id,
            'location_dest_id': picking_out.location_id.id,
            'date': fields.datetime.now(),
            'company_id': current_picking.company_id.id,
            'origin': current_picking.origin,
            'move_ids_without_package': move_ids,
        }
        return self.env['stock.picking'].create(picking_vals)

    def _get_backorder_move_lines(self, picking):
        return [
            (0, 0, {
                'product_id': move.product_id.id,
                'product_uom_qty': move.product_uom_qty - move.quantity_done,
                'quantity_done': move.product_uom_qty - move.quantity_done,
                'product_uom': move.product_id.uom_id.id,
                'name': move.product_id.name,
            })
            for move in picking.move_ids_without_package
            if move.quantity_done < move.product_uom_qty
        ]
