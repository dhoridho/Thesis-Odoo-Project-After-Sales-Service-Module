import pytz
from odoo import api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
from odoo import tools
from odoo.addons.equip3_inventory_operation.models.qiscus_connector import qiscus_request
import json


class InternalTransfer(models.Model):
    _name = "internal.transfer"
    _description = "Internal Transfer"
    _inherit = ['portal.mixin', 'mail.thread',
                'mail.activity.mixin', 'utm.mixin']


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    name = fields.Char(string="Reference", readonly=True,
                       default='New', tracking=True)
    source_location_id = fields.Many2one(
        'stock.location', string="Source Location", tracking=True)
    destination_location_id = fields.Many2one(
        'stock.location', string="Destination Location", tracking=True)
    scheduled_date = fields.Datetime(
        string="Scheduled Date", required=True, tracking=True)
    description = fields.Text(string="Description", tracking=True)
    source_document = fields.Char(
        string="Source Document", readonly=True, tracking=True)
    state = fields.Selection(string='Status', selection=[
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], default='draft')
    state1 = fields.Selection(related='state', string='Status 1')
    state2 = fields.Selection(related='state', string='Status 2')
    state3 = fields.Selection(related='state', string='Status 3')
    product_line_ids = fields.One2many(
        'internal.transfer.line', 'product_line', string="Product Line")
    operation_type_in_id = fields.Many2one(
        'stock.picking.type', string="Operation Type IN", readonly='1', tracking=True)
    operation_type_out_id = fields.Many2one(
        'stock.picking.type', string="Operation Type Out", readonly='1', tracking=True)
    is_transit = fields.Boolean(string='Transit Operation')
    operation_count = fields.Integer(
        string='Operation Count', compute='_compute_operation_count')
    expiry_date = fields.Datetime(
        string="Expiry Date", help="Expiry Date is autofill based on the Expiry Period after this request document is created")
    is_source_loc = fields.Boolean(string="Is Source Location")
    is_destination_loc = fields.Boolean(string="Is Destination Location")
    internal_transfer_line_total = fields.Integer(
        string="Internal Transfer", store=True, compute='calculate_lines_total', tracking=True)
    operations = fields.Text()

    itr_approval_matrix_id = fields.Many2one(
        'itr.approval.matrix', string="Approval Matrix", compute='_get_approval_matrix')
    is_itr_approval_matrix = fields.Boolean(
        string="ITR Request", store=True)
    approved_matrix_ids = fields.One2many('itr.approval.matrix.line', 'transfer_id',
                                        store=True, string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one(
        'itr.approval.matrix.line', string='Internal Approval Matrix Line', compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(
        string='Is Approve Button', compute='_get_approve_button', store=False)
    is_reset_to_draft = fields.Boolean(
        string='Is Reset to Draft', compute='_get_is_show_draft', store=False)
    is_product_lines = fields.Boolean(
        string='Is Product Lines', compute='_get_is_product_lines', store=False)

    source_warehouse_id = fields.Many2one(
        'stock.warehouse', string="Source Warehouse")
    destination_warehouse_id = fields.Many2one(
        'stock.warehouse', string="Destination Warehouse")
    company_id = fields.Many2one(
        'res.company', string="Company", readonly=True, tracking=True, default=lambda self: self.env.company)
    filter_source_warehouse_id = fields.Many2many(
        'stock.location', compute="_compute_source_warehouse", string="Allowed Source Warehouses")
    filter_destination_warehouse_id = fields.Many2many(
        'stock.location', compute="_compute_destination_warehouse", string="Allowed Destination Warehouses")
    analytic_account_group_ids = fields.Many2many('account.analytic.tag', 'it_analytic_rel', 'tag_id', 'it_id', string="Analytic Groups")
    requested_by = fields.Many2one(
        'res.users', 'Requested By', required='1', tracking=True, default=lambda self: self.env.user.id)
    get_warehouse = fields.Boolean(
        compute="_get_warehouses", string='Get Warehouse')
    is_mbs_on_transfer_operations = fields.Boolean(string="Transfer Operations",
                                                   compute="_compute_is_mbs_on_transfer_operations", store=False)
    is_mbs_on_itr_location = fields.Boolean(string="Interwarehouse Location Mbs",
                                                   compute="_compute_is_mbs_on_itr_location")
    branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
        domain=_domain_branch,
        default = _default_branch,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True)


    domain_warehouse_source_id = fields.Char(
        'Warehouse Source Domain', compute="_compute_location")
    domain_warehouse_destination_id = fields.Char(
        'Warehouse Destination Domain', compute="_compute_location")
    domain_analytic_account_group_ids = fields.Char(
        'Analytic Account Group Domain', compute="_compute_analytic_domain")
    is_single_source_location = fields.Boolean(string="Is Single Source Location", default=True)
    is_single_destination_location = fields.Boolean(string="Is Single Destination Location", default=True)
    mr_id = fields.Many2many('material.request', 'ir_id',
                             'mr_id', 'ir_mr_id', string='Mr')
    source_location_barcode = fields.Char(string='Source Location Barcode')
    destination_location_barcode = fields.Char(string='Destination Location Barcode')

    @api.onchange('source_location_barcode', 'destination_location_barcode')
    def onchange_barcode(self):
        StockLocation = self.env['stock.location']
        for record in self:
            barcodes = {
                'source_location_barcode': {
                    'location_field': 'source_location_id',
                    'warehouse_field': 'source_warehouse_id',
                },
                'destination_location_barcode': {
                    'location_field': 'destination_location_id',
                    'warehouse_field': 'destination_warehouse_id',
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


    @api.depends('source_warehouse_id', 'destination_warehouse_id')
    def _compute_analytic_domain(self):
        for record in self:
            if record.source_warehouse_id and record.destination_warehouse_id:
                analytic_source = record.source_warehouse_id.branch_id.mapped('analytic_tag_ids')
                analytic_destination = record.destination_warehouse_id.branch_id.mapped('analytic_tag_ids')
                if analytic_source and analytic_destination:
                    merge_analytic = analytic_source + analytic_destination
                    record.domain_analytic_account_group_ids = json.dumps(
                        [('id', 'in', list(set(merge_analytic.ids)))])
                else:
                    record.domain_analytic_account_group_ids = json.dumps(
                        [('id', 'in', [])])
            else:
                record.domain_analytic_account_group_ids = json.dumps(
                    [('id', 'in', [])])

    @api.onchange('analytic_account_group_ids')
    def set_analytic_account_group_ids(self):
        for res in self:
            for line in res.product_line_ids:
                line.analytic_account_group_ids = res.analytic_account_group_ids

    @api.depends('branch_id')
    def _compute_location(self):
        for record in self:
            company_id = record.company_id.id or self.env.company.id
            warehouse_ids_destination = self.env['stock.warehouse'].search([('company_id','=',company_id), ('branch_id', 'in', self.env.branches.ids)])
            record.domain_warehouse_destination_id = json.dumps(
                        [('id', 'in', warehouse_ids_destination.ids)])

            if record.branch_id.id:
                warehouse_ids_source = self.env['stock.warehouse'].search(
                    [('branch_id', '=', record.branch_id.id),('company_id','=',company_id)])
                if warehouse_ids_source:
                    record.domain_warehouse_source_id = json.dumps(
                        [('id', 'in', warehouse_ids_source.ids)])
                else:
                    record.domain_warehouse_source_id = json.dumps([('id', '=', 0)])

                if record.source_warehouse_id.branch_id != record.branch_id:
                    record.source_warehouse_id = False
            else:
                record.domain_warehouse_source_id = json.dumps([('id', '=', 0)])


    @api.onchange('destination_warehouse_id', 'source_warehouse_id')
    def onchange_destination_warehouse_id(self):
        if self.destination_warehouse_id and self.source_warehouse_id and self.destination_warehouse_id == self.source_warehouse_id:
            raise ValidationError('Source Warehouse ({}) Cannot be the same as Destination Warehouse ({})'.format(
                self.source_warehouse_id.name, self.destination_warehouse_id.name))

    @api.model
    def default_sh_it_bm_is_cont_scan(self):
        return self.env.company.sh_it_bm_is_cont_scan

    sh_it_barcode_mobile = fields.Char(string="Mobile Barcode")

    sh_it_bm_is_cont_scan = fields.Char(
        string='Continuously Scan?', default=default_sh_it_bm_is_cont_scan, readonly=True)

    @api.onchange('sh_it_barcode_mobile')
    def _onchange_sh_it_barcode_mobile(self):
        if self.sh_it_barcode_mobile in ['', "", False, None]:
            return

        CODE_SOUND_SUCCESS = ""
        CODE_SOUND_FAIL = ""
        if self.env.user.company_id.sudo().sh_it_bm_is_sound_on_success:
            CODE_SOUND_SUCCESS = "SH_BARCODE_MOBILE_SUCCESS_"

        if self.env.user.company_id.sudo().sh_it_bm_is_sound_on_fail:
            CODE_SOUND_FAIL = "SH_BARCODE_MOBILE_FAIL_"

        # if not self.operation_type_in_id or not self.operation_type_out_id:
        #     if self.env.user.company_id.sudo().sh_it_bm_is_notify_on_fail:
        #         message = _(CODE_SOUND_FAIL +
        #                     'You must first select a Operation Type.')
        #         self.env['bus.bus'].sendone(
        #             (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
        #             {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
        #     return

        if self and self.state not in ['to_approve', 'draft', 'approved', 'confirm']:
            selections = self.fields_get()['state']['selection']
            value = next((v[1] for v in selections if v[0]
                          == self.state), self.state)
            if self.env.user.company_id.sudo().sh_it_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL +
                            'You can not scan item in %s state.') % (value)
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
            return
        elif self:
            search_itls = False
            domain = []

            if self.env.user.company_id.sudo().sh_it_barcode_mobile_type == 'barcode':
                search_itls = self.product_line_ids.filtered(
                    lambda ml: ml.product_id.barcode == self.sh_it_barcode_mobile)
                domain = [("barcode", "=", self.sh_it_barcode_mobile)]

                sh_it_mobile_barcode_type = self.env['ir.config_parameter'].sudo().get_param('equip3_inventory_scanning.sh_it_mobile_barcode_type', 'sku')
                if sh_it_mobile_barcode_type == 'lot_serial':
                    stock_production_lot = self.env['stock.production.lot'].search([('name', '=', self.sh_it_barcode_mobile)], limit=1)
                    domain = [('id', '=', stock_production_lot.product_id.id)]
                    search_itls = self.product_line_ids.filtered(
                        lambda ml: ml.product_id.id == stock_production_lot.product_id.id)
            elif self.env.user.company_id.sudo().sh_it_barcode_mobile_type == 'int_ref':
                search_itls = self.product_line_ids.filtered(
                    lambda ml: ml.product_id.default_code == self.sh_it_barcode_mobile)
                domain = [("default_code", "=", self.sh_it_barcode_mobile)]

            elif self.env.user.company_id.sudo().sh_it_barcode_mobile_type == 'sh_qr_code':
                search_itls = self.product_line_ids.filtered(
                    lambda ml: ml.product_id.sh_qr_code == self.sh_it_barcode_mobile)
                domain = [("sh_qr_code", "=", self.sh_it_barcode_mobile)]

            elif self.env.user.company_id.sudo().sh_it_barcode_mobile_type == 'all':
                search_itls = self.product_line_ids.filtered(
                    lambda ml: ml.product_id.barcode == self.sh_it_barcode_mobile or ml.product_id.default_code == self.sh_it_barcode_mobile)
                domain = ["|", "|",
                          ("default_code", "=", self.sh_it_barcode_mobile),
                          ("barcode", "=", self.sh_it_barcode_mobile),
                          ("sh_qr_code", "=", self.sh_it_barcode_mobile),
                          ]
            if search_itls:
                for line in search_itls:
                    qty_done = line.qty + 1
                    line.qty = qty_done
                    if self.env.user.company_id.sudo().sh_it_bm_is_notify_on_success:
                        self.sh_it_barcode_mobile = ''
                        message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                            line.product_id.name, line.qty)
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                             self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
            elif self.state in ['to_approve', 'draft', 'approved', 'confirm']:
                if self.env.user.company_id.sudo().sh_it_bm_is_add_product:
                    search_product = self.env["product.product"].search(
                        domain, limit=1)
                    if search_product:
                        itl_vals = {
                            "description": search_product.name,
                            "product_id": search_product.id,
                            "qty": 1,
                            "analytic_account_group_ids": [(6, 0, self.analytic_account_group_ids.ids)],
                            "scheduled_date": self.scheduled_date,
                            "source_location_id": self.source_location_id.id,
                            "destination_location_id": self.destination_location_id.id,
                        }
                        if search_product.uom_id:
                            itl_vals.update({
                                "uom": search_product.uom_id.id,
                            })

                        self.product_line_ids = [(0, 0, itl_vals)]
                        if self.env.user.company_id.sudo().sh_it_bm_is_notify_on_success:
                            self.sh_it_barcode_mobile = ''
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                search_product.name, 1)
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                 self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                        return

                    else:
                        if self.env.user.company_id.sudo().sh_it_bm_is_notify_on_fail:
                            message = _(
                                CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                 self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

                        return

                else:
                    if self.env.user.company_id.sudo().sh_it_bm_is_notify_on_fail:
                        message = _(
                            CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                             self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

                    return

            else:
                if self.env.user.company_id.sudo().sh_it_bm_is_notify_on_fail:
                    message = _(
                        CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                    self.env['bus.bus'].sendone(
                        (self._cr.dbname, 'res.partner',
                         self.env.user.partner_id.id),
                        {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

                return
        else:
            # failed message here
            if self.env.user.company_id.sudo().sh_it_bm_is_notify_on_fail:
                message = _(
                    CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

            return

    def _compute_is_mbs_on_transfer_operations(self):
        is_mbs_on_transfer_operations = self.env['ir.config_parameter'].sudo().get_param(
            'is_mbs_on_transfer_operations', False)
        for record in self:
            record.is_mbs_on_transfer_operations = is_mbs_on_transfer_operations
            
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

    @api.onchange('requested_by')
    def _onchange_requested_by(self):
        self._compute_is_mbs_on_transfer_operations()

    def _get_warehouses(self):
        self.get_warehouse = True

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
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
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.onchange('scheduled_date')
    def compute_expiry_date(self):
        for record in self:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            itr_expiry_days = IrConfigParam.get_param(
                'itr_expiry_days', 'before')
            itr_ex_period = IrConfigParam.get_param('ex_period', 0)
            if record.scheduled_date:
                if itr_expiry_days == 'before':
                    record.expiry_date = record.scheduled_date - \
                        timedelta(days=int(itr_ex_period))
                else:
                    record.expiry_date = record.scheduled_date + \
                        timedelta(days=int(itr_ex_period))

                if record.scheduled_date.date() < datetime.now().date():
                    raise ValidationError('Scheduled date must be greater than current date')

    @api.depends('source_warehouse_id')
    def _compute_source_warehouse(self):
        for record in self:
            location_ids = []
            if record.source_warehouse_id:
                location_obj = record.env['stock.location']
                store_location_id = record.source_warehouse_id.view_location_id.id
                addtional_ids = location_obj.search(
                    [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_ids.append(location.id)
                child_location_ids = record.env['stock.location'].search(
                    [('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                final_location = child_location_ids + location_ids
                record.filter_source_warehouse_id = [(6, 0, final_location)]
            else:
                record.filter_source_warehouse_id = [(6, 0, [])]

    @api.depends('destination_warehouse_id')
    def _compute_destination_warehouse(self):
        for record in self:
            location_ids = []
            if record.destination_warehouse_id:
                location_obj = record.env['stock.location']
                store_location_id = record.destination_warehouse_id.view_location_id.id
                addtional_ids = location_obj.search(
                    [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_ids.append(location.id)
                child_location_ids = record.env['stock.location'].search(
                    [('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                final_location = child_location_ids + location_ids
                record.filter_destination_warehouse_id = [
                    (6, 0, final_location)]
            else:
                record.filter_destination_warehouse_id = [(6, 0, [])]

    @api.depends('product_line_ids')
    def _get_is_product_lines(self):
        for record in self:
            record.is_product_lines = False
            if record.product_line_ids:
                record.is_product_lines = True

    def _get_is_show_draft(self):
        for record in self:
            not_approved_lines = record.approved_matrix_ids.filtered(
                lambda r: not r.approved_users)
            if record.is_itr_approval_matrix and \
                    record.state == 'to_approve' and \
                    len(not_approved_lines) == len(record.approved_matrix_ids):
                record.is_reset_to_draft = True
            else:
                record.is_reset_to_draft = False

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(
                lambda r: not r.approved), key=lambda r: r.sequence)
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

    def _get_approving_matrix_lines_itr(self):
        self.approved_matrix_ids = [(5, 0, 0)]

        data = [
            (0, 0, {
                'sequence': idx + 1,
                'user_ids': [(6, 0, line.user_ids.ids)],
                'minimum_approver': line.minimum_approver,
            })
            for idx, line in enumerate(self.itr_approval_matrix_id.itr_approval_matrix_line_ids)
        ]
        self.approved_matrix_ids = data

    def _get_approve_button_from_config(self, res):
        is_internal_transfer_approval_matrix = self.env['ir.config_parameter'].sudo(
        ).get_param('is_internal_transfer_approval_matrix', False)
        res.update({
            'is_itr_approval_matrix': is_internal_transfer_approval_matrix
        })

    @api.depends('source_warehouse_id', 'is_itr_approval_matrix')
    def _get_approval_matrix(self):
        for record in self:
            record.itr_approval_matrix_id = self.env['itr.approval.matrix'].search(
                [('warehouse_id', '=', record.source_warehouse_id.id)], limit=1) if record.is_itr_approval_matrix else False

    def itr_request_for_approving(self):
        for record in self:
            if record.is_itr_approval_matrix and not record.itr_approval_matrix_id:
                raise ValidationError(_('Please set approval matrix for Internal Transfer first!\nContact Administrator for more details.'))
            record._get_approving_matrix_lines_itr()

            values = {
                'sender': self.env.user,
                'name': 'Internal Transfers',
                'no': record.name,
                'datetime': fields.Datetime.now(),
                'action_xmlid': 'equip3_inventory_operation.action_internal_transfer_request',
                'menu_xmlid': 'equip3_inventory_operation.menu_operation_internal_transfer_request'
            }

            for approver in record.approved_matrix_ids.mapped('user_ids'):
                values.update({'receiver': approver})
                qiscus_request(record, values)
            record.write({'state': 'to_approve'})

    def itr_approving(self):
        for record in self:
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                        user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
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
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write(
                            {'time_stamp': datetime.now(), 'approved': True})

            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                record.write({'state': 'approved'})

    def itr_reject(self):
        for record in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Reject Internal Transfer Request',
                'res_model': 'itr.matrix.reject',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }

    def itr_reset_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})
            record.approved_matrix_ids.write({
                'state_char': False,
                'approved_users': [(6, 0, [])],
                'approved': False,
                "feedback": False,
                'time_stamp': False,
                'last_approved': False,
                'approved': False
            })

    @api.onchange('source_location_id')
    def _compute_source_loc(self):
        self._get_is_product_lines()
        for record in self:
            for line in record.product_line_ids:
                if record.source_location_id:
                    line.source_location_id = record.source_location_id

    @api.onchange('source_warehouse_id', 'destination_warehouse_id', 'is_single_source_location', 'is_single_destination_location')
    def _onchange_warehouse_id_for_location(self):
        for record in self:
            record.source_location_id = self._get_location_id(record.source_warehouse_id, record.is_single_source_location)
            record.destination_location_id = self._get_location_id(record.destination_warehouse_id, record.is_single_destination_location)

    def _get_location_id(self, warehouse_id, is_single_location):
        if is_single_location and warehouse_id:
            location = self.env['stock.location'].search([
                ('warehouse_id', '=', warehouse_id.id),
                ('usage', '=', 'internal')
            ], limit=1, order='id')
            return location.id if location else False
        return False

    @api.depends('product_line_ids')
    def calculate_lines_total(self):
        for record in self:
            record.internal_transfer_line_total = len(record.product_line_ids)

    @api.onchange('destination_location_id')
    def _compute_destination_loc(self):
        for record in self:
            for line in record.product_line_ids:
                if record.destination_location_id:
                    line.destination_location_id = record.destination_location_id

    def upd_source(self):
        for record in self:
            for product_line_id in record.product_line_ids:
                product_line_id.write(
                    {'source_location_id': record.source_location_id.id})
            record.is_source_loc = False

    def upd_dest(self):
        for record in self:
            for product_line_id in record.product_line_ids:
                product_line_id.write(
                    {'destination_location_id': record.destination_location_id.id})
            record.is_destination_loc = False

    def _compute_operation_count(self):
        for record in self:
            record.operation_count = self.env['stock.picking'].search_count(
                [('transfer_id', '=', record.id)])

    def check_qc(self, product, picking_type, move_id):
        quality_point_id = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [product]),
                                                                  ('operation_ids', 'in', [
                                                                   picking_type]), '|',
                                                                  ('team.user_ids.id', 'in', [
                                                                   self.env.context.get('uid')]),
                                                                  ('team', '=', False)], limit=1, order='create_date desc')

        quality_point_id_not_in_team = self.env['sh.qc.point'].sudo().search([('product_ids', 'in', [product]),
                                                                              ('is_mandatory',
                                                                               '=', True),
                                                                              ('operation_ids', 'in', [
                                                                               picking_type]), '|',
                                                                              ('team.user_ids.id', 'in', [
                                                                               self.env.context.get('uid')]),
                                                                              ('team', '!=', False)], limit=1, order='create_date desc')

        if quality_point_id or quality_point_id_not_in_team:
            move_id.update(
                {'sh_quality_point': True, 'sh_quality_point_id': quality_point_id.id or quality_point_id_not_in_team.id})

    def _prepare_transfer_out_vals(self, scheduled_date, source_location_id,operation_type_out_id):
        self.ensure_one()
        transit_location = self.env.ref('equip3_inventory_masterdata.location_transit')
        vals = self._prepare_transfer_vals(
            source_location_id,
            transit_location,
            scheduled_date,
            operation_type_out_id,
            self.source_warehouse_id.branch_id)

        analytic_tag_ids = self.source_location_id.warehouse_id.branch_id.analytic_tag_ids.ids
        vals.update({
            'origin_dest_location': self.destination_location_id.display_name,
            'is_transfer_out': True,
            'analytic_account_group_ids': [(6, 0, analytic_tag_ids)]
        })
        return vals

    def _prepare_transfer_in_vals(self, scheduled_date, destination_location_id, operation_type_in_id):
        self.ensure_one()
        transit_location = self.env.ref('equip3_inventory_masterdata.location_transit')
        vals = self._prepare_transfer_vals(
            transit_location,
            destination_location_id,
            scheduled_date,
            operation_type_in_id,
            self.destination_warehouse_id.branch_id)

        analytic_tag_ids = self.destination_location_id.warehouse_id.branch_id.analytic_tag_ids.ids
        vals.update({
            'origin_src_location': self.source_location_id.display_name,
            'is_transfer_in': True,
            'branch_id': self.destination_warehouse_id.branch_id.id,
            'analytic_account_group_ids': [(6, 0, analytic_tag_ids)]
        })
        return vals

    def _prepare_transfer_vals(self, location_id, location_dest_id, scheduled_date, picking_type_id, branch_id):
        self.ensure_one()
        return {
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'move_type': 'direct',
            'partner_id': self.create_uid.partner_id.id,
            'scheduled_date': scheduled_date,
            'picking_type_id': picking_type_id.id,
            'analytic_account_group_ids': [(6, 0, self.analytic_account_group_ids.ids)],
            'origin': self.name,
            'transfer_id': self.id,
            'company_id': self.company_id.id,
            'branch_id': branch_id.id
        }

    def _get_lines_based_scheduled_date(self):
        self.ensure_one()
        temp_list = []
        line_vals_list = []
        for line in self.product_line_ids:
            if line.scheduled_date.date() in temp_list:
                filter_line = list(filter(lambda r: r.get('date') == line.scheduled_date.date(), line_vals_list))
                if filter_line:
                    filter_line[0]['lines'].append(line)
            else:
                temp_list.append(line.scheduled_date.date())
                line_vals_list.append({
                    'date': line.scheduled_date.date(),
                    'lines': [line]
                })
        return line_vals_list

    def action_confirm(self):
        StockMove = self.env['stock.move']
        Picking = self.env['stock.picking']

        for transfer in self:
            if not transfer.product_line_ids:
                raise ValidationError(_('Please add product lines'))

            picking_dict = {}
            for line_vals in transfer._get_lines_based_scheduled_date():
                date = line_vals.get('date')
                lines = line_vals.get('lines', [])

                if transfer.is_transit:
                    for sequence, line in enumerate(lines):
                        transit_location_id = self.env.ref('equip3_inventory_masterdata.location_transit')

                        # Create picking out
                        out_key = (line.source_location_id.id, transit_location_id.id)
                        if out_key not in picking_dict:
                            domain_out = [
                                ('default_location_src_id', '=', line.source_location_id.id),
                                ('default_location_dest_id', '=', transit_location_id.id)
                            ]
                            operation_type_out_id = self.env['stock.picking.type'].search(domain_out, limit=1)
                            picking_out = Picking.create(transfer._prepare_transfer_out_vals(
                                scheduled_date=date,
                                source_location_id=line.source_location_id,
                                operation_type_out_id=operation_type_out_id))
                            picking_dict[out_key] = picking_out
                        else:
                            picking_out = picking_dict[out_key]

                        move_out = StockMove.create(line._prepare_transfer_out_line_vals(picking_out, date, sequence + 1))
                        self.check_qc(product=line.product_id.id, picking_type=picking_out.picking_type_id.id, move_id=move_out)

                        # Create picking in
                        in_key = (transit_location_id.id, line.destination_location_id.id)
                        if in_key not in picking_dict:
                            domain_in = [
                                ('default_location_src_id', '=', transit_location_id.id),
                                ('default_location_dest_id', '=', line.destination_location_id.id)
                            ]
                            operation_type_in_id = self.env['stock.picking.type'].search(domain_in, limit=1)
                            picking_in = Picking.create(transfer._prepare_transfer_in_vals(
                                scheduled_date=date,
                                destination_location_id=line.destination_location_id,
                                operation_type_in_id=operation_type_in_id))
                            picking_dict[in_key] = picking_in
                        else:
                            picking_in = picking_dict[in_key]

                        move_in = StockMove.create(line._prepare_transfer_in_line_vals(picking_in, move_out, date, sequence + 1))
                        self.check_qc(product=line.product_id.id, picking_type=picking_in.picking_type_id.id, move_id=move_in)

                else:
                    for line in lines:
                        domain = [
                            ('default_location_src_id', '=', line.source_location_id.id),
                            ('default_location_dest_id', '=', line.source_location_id.id)
                        ]
                        operation_type_out_id = self.env['stock.picking.type'].search(domain, limit=1)
                        picking_key = (line.source_location_id.id, line.destination_location_id.id)
                        if picking_key not in picking_dict:
                            picking = Picking.create(transfer._prepare_transfer_vals(
                                line.source_location_id,
                                line.destination_location_id,
                                date,
                                operation_type_out_id,
                                transfer.branch_id
                            ))
                            picking_dict[picking_key] = picking
                        else:
                            picking = picking_dict[picking_key]

                        StockMove.create(line._prepare_transfer_line_vals(
                            line.source_location_id,
                            line.destination_location_id,
                            picking, date, len(picking.move_lines) + 1))

                transfer.write({'state': 'confirm'})

        return True

    def action_done(self):
        self.ensure_one()

        if self.mr_id:
            mr_rec = self.env['material.request'].search(
                [('id', '=', self.mr_id.ids)])
            for ir_line in self.product_line_ids:
                for mr_line in mr_rec.product_line:
                    if ir_line.product_id.id == mr_line.product.id:
                        mr_line.itr_done_qty += ir_line.transfer_qty
                        mr_line.itr_returned_qty += ir_line.return_qty

        self.write({'state': 'done'})

    def print_report(self):
        for record in self:
            all_transfer_op = record.env['stock.picking'].search(
                [('transfer_id', '=', record.id), ('state', '!=', 'cancel')])
            operations = ''
            for picking in all_transfer_op:
                operations = operations + '• ' + str(picking.name) + '\n'
            self.operations = operations
            return self.env.ref('equip3_inventory_operation.report_internal_transfer').report_action(self)

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})
            all_transfer_op = record.env['stock.picking'].search(
                [('transfer_id', '=', record.id), ('state', '!=', 'cancel')])
            for picking in all_transfer_op:
                picking.action_cancel()

        return True

    def button_notes(self):
        self.ensure_one()

        view_id = self.env.ref(
            'equip3_inventory_operation.view_tree_stock_picking')
        action = self.env.ref(
            'equip3_inventory_operation.action_from_interwarehouse_request').read()[0]
        action['domain'] = [('transfer_id', '=', self.id)]
        return action

    @api.model
    def default_get(self, fields):
        res = super(InternalTransfer, self).default_get(fields)
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        internal_type = IrConfigParam.get_param('internal_type', False)
        if internal_type == 'with_transit':
            res['is_transit'] = True
        self._get_approve_button_from_config(res)
        return res

    @api.model
    def _expire_date_cron(self):
        today_date = datetime.now()
        expire_records = self.search([
            ('state', 'in', ('draft', 'to_approve')),
            ('expiry_date', '<', today_date)
        ])
        template_id = self.env.ref(
            'equip3_inventory_operation.email_template_expired_internal_transfer_request')
        for record in expire_records:
            record.write({'state': 'cancel'})
            record.send_email_notification(
                template_id, 'equip3_inventory_operation.email_template_expired_internal_transfer_request', record.create_uid)

    @api.model
    def _expire_date_reminder_cron(self):
        today_date = date.today() + timedelta(days=1)
        expire_records = self.search([
            ('state', 'in', ('draft', 'to_approve'))
        ])
        user_reminder_template = self.env.ref(
            'equip3_inventory_operation.email_template_expired_internal_transfer_reminder_user')
        approver_user_template = self.env.ref(
            'equip3_inventory_operation.email_template_expired_internal_transfer_reminder_approved_user')
        for record in expire_records:
            if record.expiry_date and record.expiry_date.date() == today_date:
                record.send_email_notification(
                    user_reminder_template, 'equip3_inventory_operation.email_template_expired_internal_transfer_reminder_user', record.create_uid)
                matrix_line = sorted(record.approved_matrix_ids.filtered(
                    lambda r: not r.approved), key=lambda r: r.sequence)
                if record.is_itr_approval_matrix and matrix_line:
                    matrix_line = matrix_line[0]
                    approver_user = False
                    for user in matrix_line.user_ids:
                        if user.id in matrix_line.user_ids.ids and \
                                user.id not in matrix_line.approved_users.ids:
                            approver_user = user
                            break
                    record.send_email_notification(
                        approver_user_template, 'equip3_inventory_operation.email_template_expired_internal_transfer_reminder_approved_user', approver_user)

    def send_email_notification(self, template_id, template_name, user_id):
        record = self
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        action_id = self.env.ref(
            'equip3_inventory_operation.action_internal_transfer_request').id
        url = base_url + '/web#id=' + \
            str(record.id) + '&action=' + str(action_id) + \
            '&view_type=form&model=internal.transfer'
        ctx = {
            'email_from': self.env.user.company_id.email,
            'email_to': user_id.partner_id.email,
            'user_name': user_id.name,
            'url': url,
        }
        template_id.with_context(ctx).send_mail(record.id, True)
        template_id = self.env["ir.model.data"].xmlid_to_object(template_name)

        body_html = self.env['mail.render.mixin'].with_context(ctx)._render_template(
            template_id.body_html, 'internal.transfer', record.ids, post_process=True)[record.id]
        message_id = (
            self.env["mail.message"]
            .sudo()
            .create(
                {
                    "subject": "Internal Transfer Expiry",
                    "body": body_html,
                    "model": "internal.transfer",
                    "res_id": record.id,
                    "message_type": "notification",
                    "partner_ids": [
                        (
                            6,
                            0,
                            user_id.partner_id.ids,
                        )
                    ],
                }
            )
        )
        notif_create_values = {
            "mail_message_id": message_id.id,
            "res_partner_id": user_id.partner_id.id,
            "notification_type": "inbox",
            "notification_status": "sent",
        }
        self.env["mail.notification"].sudo().create(notif_create_values)

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('internal.transfer')
        return super(InternalTransfer, self).create(vals)


    @api.onchange('source_location_id', 'is_transit')
    def onchange_source_loction_id(self):
        for record in self:
            transit_location_id = self.env.ref(
                'equip3_inventory_masterdata.location_transit')
            if record.source_location_id and not record.is_transit:
                condition = [
                    ('default_location_src_id', '=', record.source_location_id.id),
                    ('default_location_dest_id', '=',
                     record.source_location_id.id),
                ]
                picking_type_id = self.env['stock.picking.type'].search(
                    condition, limit=1)
                record.operation_type_out_id = picking_type_id and picking_type_id.id or False
            elif record.source_location_id and record.is_transit:
                condition = [
                    ('code', '=', 'internal'),
                    ('is_transit', '=', True),
                    ('default_location_dest_id', '=', transit_location_id.id),
                    ('default_location_src_id', '=', record.source_location_id.id)
                ]
                picking_type_id = self.env['stock.picking.type'].search(
                    condition, limit=1)
                record.operation_type_out_id = picking_type_id and picking_type_id.id or False

    @api.onchange('destination_location_id', 'is_transit')
    def onchange_dest_loction_id(self):
        for record in self:
            transit_location_id = self.env.ref(
                'equip3_inventory_masterdata.location_transit')
            if record.destination_location_id and not record.is_transit:
                condition = [
                    ('default_location_src_id', '=',
                     record.destination_location_id.id),
                    ('default_location_dest_id', '=',
                     record.destination_location_id.id),
                ]
                picking_type_id = self.env['stock.picking.type'].search(
                    condition, limit=1)
                record.operation_type_in_id = picking_type_id and picking_type_id.id or False
            elif record.destination_location_id and record.is_transit:
                condition = [
                    ('code', '=', 'internal'),
                    ('is_transit', '=', record.is_transit),
                    ('default_location_dest_id', '=',
                     record.destination_location_id.id),
                    ('default_location_src_id', '=', transit_location_id.id)
                ]
                picking_type_id = self.env['stock.picking.type'].search(
                    condition, limit=1)
                record.operation_type_in_id = picking_type_id and picking_type_id.id or False

    def calculate_transfer_qty(self, stock_picking):
        for record in self:
            if stock_picking:
                internal_type = record.env['ir.config_parameter'].sudo(
                ).get_param('internal_type') or False
                transit_location = record.env.ref(
                    'equip3_inventory_masterdata.location_transit')
                if internal_type == 'with_transit':
                    for picking in stock_picking:
                        if picking.location_id.id == transit_location.id and \
                                picking.location_dest_id.id == record.destination_location_id.id:
                            for line in picking.move_ids_without_package:
                                product_lines = record.product_line_ids.filtered(
                                    lambda r: r.product_id.id == line.product_id.id)
                                total_qty = line.quantity_done
                                for itr_line in product_lines:
                                    if itr_line.transfer_qty != itr_line.qty:
                                        if itr_line.qty <= total_qty:
                                            itr_line.transfer_qty = itr_line.qty
                                            total_qty -= itr_line.transfer_qty
                                        elif itr_line.qty > total_qty:
                                            diff = itr_line.qty - total_qty
                                            itr_line.transfer_qty += itr_line.qty - diff
                                            total_qty -= itr_line.transfer_qty
                                        else:
                                            itr_line.transfer_qty = 0
                else:
                    for picking in stock_picking:
                        if picking.location_id.id == record.source_location_id.id and \
                                picking.location_dest_id.id == record.destination_location_id.id:
                            for line in picking.move_ids_without_package:
                                product_lines = record.product_line_ids.filtered(
                                    lambda r: r.product_id.id == line.product_id.id)
                                total_qty = line.quantity_done
                                for itr_line in product_lines:
                                    if itr_line.transfer_qty != itr_line.qty:
                                        if itr_line.qty <= total_qty:
                                            itr_line.transfer_qty = itr_line.qty
                                            total_qty -= itr_line.transfer_qty
                                        elif itr_line.qty > total_qty:
                                            diff = itr_line.qty - total_qty
                                            itr_line.transfer_qty += itr_line.qty - diff
                                            total_qty -= itr_line.transfer_qty
                                        else:
                                            itr_line.transfer_qty = 0

        return True


    @api.model
    def _adjust_approval_all_in_one(self):
        self._adjust_approval('internal.transfer', 'itr.approval.matrix', 'source_warehouse_id', 'is_itr_approval_matrix', 'state', 'to_approve', 'ITR')
        self._adjust_approval('material.request', 'mr.approval.matrix', 'destination_warehouse_id', 'is_material_request_approval_matrix', 'status', 'to_approve', 'MR')
        self._adjust_approval('stock.picking', 'rn.approval.matrix', 'location_dest_id', 'is_rn_request_approval_matrix', 'state', 'waiting_for_approval', 'RN')
        self._adjust_approval('stock.picking', 'do.approval.matrix', 'location_id', 'is_do_request_approval_matrix', 'state', 'waiting_for_approval', 'DO')
        self._adjust_approval('stock.scrap.request', 'stock.scrap.approval.matrix', 'warehouse_id', 'is_product_usage_approval', 'state', 'to_approve', 'PU')
        return True

    def _adjust_approval(self, model, approval_model, warehouse_field,is_approval_field, state_key, state_value, name_prefix):
        model_records = self.env[model].search([(state_key, '=', state_value), (is_approval_field, '=', False)])
        for record in model_records:
            warehouse_id = self._get_warehouse_id(record, warehouse_field, model)
            approval = self.env[approval_model].search([('warehouse_id', '=', warehouse_id)], limit=1)
            if approval:
                setattr(record, is_approval_field, True)
                print(f"SUCCESSFULLY MAKE IT TRUE ➡ {name_prefix}", record.name)

    def _get_warehouse_id(self, record, warehouse_field, model):
        if model == 'stock.picking':
            if record.picking_type_id.code == 'incoming':
                return record.location_dest_id.warehouse_id.id
            elif record.picking_type_id.code == 'outgoing':
                return record.location_id.warehouse_id.id
        else:
            return getattr(record, warehouse_field).id



class InternalTransferLine(models.Model):
    _name = 'internal.transfer.line'
    _description = "Internal Transfer Line"

    qty_cancel = fields.Float(string="Quantity Cancel")
    product_line = fields.Many2one(
        'internal.transfer', string="Internal Transfer")
    product_id = fields.Many2one(
        'product.product', string="Product", required=True)
    qty = fields.Float(string="Quantity", default=1)
    uom = fields.Many2one('uom.uom', string="Unit of Measure",
                          required=True)
    source_location_id = fields.Many2one(
        'stock.location', string="Source Location", required=True)
    destination_location_id = fields.Many2one(
        'stock.location', string="Destination Location", required=True)
    transfer_qty = fields.Float(
        string="Transferred Quantity", readonly=True)
    return_qty = fields.Float(string="Return Quantity", readonly=True,
                              compute='compute_return_quantity')
    total_trf = fields.Float(string="Total Transferred Quantity", readonly=True,
                             compute='calculate_total_trf_qty', store=True)
    scheduled_date = fields.Datetime(string="Scheduled Date")
    filter_source_loc = fields.Char(compute='_compute_filter_loc', string="Filter Source location", store=False)
    filter_dest_loc = fields.Char(compute='_compute_filter_loc',  string="Filter Destination Location", store=False)
    current_qty = fields.Float(string="Current Quantity", readonly=True,
                               store=True, compute='calculate_current_qty')
    filter_available_product_ids = fields.Many2many('product.product', 'product_id', 'avl_product_rel',
                                                    'product_avl_product_id', string="Available Quantity", compute='avl_qty_calculation', store=False)
    analytic_account_group_ids = fields.Many2many(
        'account.analytic.tag', string="Analytic Groups")

    status = fields.Selection(related="product_line.state", readonly='1', string='Request State')
    description = fields.Text('Description', required='1')
    mr_line_id = fields.Many2one('material.request.line')
    source_document = fields.Char('Source Document')
    requested_by = fields.Many2one('res.partner', 'Requested By')
    company_id = fields.Many2one('res.company', 'Company')
    picking_id = fields.One2many('stock.picking', 'internal_transfer_line_id')
    itr_in_progress_qty = fields.Float(
        'In Progress Quantity', compute='_compute_itr_in_progress_qty')
    itr_remaining_qty = fields.Float(
        string="Remaining Quantity", compute="_compute_remaining_qty_itr")
    is_single_source_location = fields.Boolean(string="Is Single Source Location", related="product_line.is_single_source_location")
    is_single_destination_location = fields.Boolean(string="Is Single Destination Location", related="product_line.is_single_destination_location")
    product_uom_category_id = fields.Many2one(comodel_name='uom.category', related='product_id.uom_id.category_id')

    @api.onchange('product_id')
    def get_description(self):
        for record in self:
            if record.product_id.description_picking:
                record.description = record.product_id.description_picking
            else:
                record.description = record.product_id.display_name

    @api.model
    def default_get(self, fields):
        res = super(InternalTransferLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'product_line_ids' in context_keys:
                if len(self._context.get('product_line_ids')) > 0:
                    next_sequence = len(
                        self._context.get('product_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Char(string="No.")

    def _compute_remaining_qty_itr(self):
        for record in self:
            record.itr_remaining_qty = record.qty - \
                (record.transfer_qty + record.itr_in_progress_qty)

    def _compute_itr_in_progress_qty(self):
        for record in self:
            record.itr_in_progress_qty = 0
            transit_location = self.env.ref(
                'equip3_inventory_masterdata.location_transit')
            stock_picking = record.env['stock.picking'].search(
                [('transfer_id', '=', record.product_line.id), ('state', 'not in', ('draft', 'done', 'cancel'))])
            for picking in stock_picking:
                if ((picking.location_id.id == transit_location.id and picking.origin == record.product_line.name and picking.location_dest_id == record.product_line.destination_location_id) or
                        (picking.location_id.id == record.product_line.source_location_id.id and picking.location_dest_id.id == transit_location.id)):
                    for move in picking.move_ids_without_package:
                        product_lines = record.product_line.product_line_ids.filtered(
                            lambda r: r.product_id.id == move.product_id.id)
                        total_qty = move.reserved_availability
                        line_data = []
                        for itr_line in product_lines:
                            if total_qty != 0:
                                if total_qty <= itr_line.qty:
                                    line_data.append(
                                        {'line': itr_line, 'qty': total_qty})
                                    total_qty = 0
                                elif total_qty > itr_line.qty:
                                    diff = total_qty - itr_line.qty
                                    qty = total_qty - diff
                                    line_data.append(
                                        {'line': itr_line, 'qty': qty})
                                    total_qty -= qty
                        if line_data:
                            filter_line = list(filter(lambda r: r.get(
                                'line').id == record.id, line_data))
                            if filter_line:
                                record.itr_in_progress_qty = filter_line[0].get(
                                    'qty')
                if picking.location_id.id == record.product_line.source_location_id.id and picking.origin == record.product_line.name and picking.location_dest_id.id == record.product_line.destination_location_id.id:
                    for move in picking.move_ids_without_package:
                        if move.state == 'done':
                            record.itr_in_progress_qty += abs(
                                record.qty - move.quantity_done)

    def compute_return_quantity(self):
        for record in self:
            stock_picking = record.env['stock.picking'].search(
                [('transfer_id', '=', record.product_line.id), ('state', '=', 'done')])
            if stock_picking:
                internal_type = record.env['ir.config_parameter'].sudo(
                ).get_param('internal_type') or False
                transit_location = record.env.ref(
                    'equip3_inventory_masterdata.location_transit')
                if internal_type == 'with_transit':
                    for picking in stock_picking:
                        for product_line in self.product_line:
                            if picking.origin != product_line.name:
                                if picking.location_id == transit_location and picking.location_dest_id == record.source_location_id:
                                    for line in picking.move_line_ids_without_package:
                                        if line.product_id == record.product_id:
                                            record.return_qty += line.qty_done
                            else:
                                record.return_qty += 0
                else:
                    for picking in stock_picking:
                        if picking.origin and 'Return' in picking.origin:
                            if picking.location_id == record.destination_location_id and picking.location_dest_id == record.source_location_id:
                                for line in picking.move_line_ids_without_package:
                                    if line.product_id == record.product_id:
                                        record.return_qty += line.qty_done
                        else:
                            record.return_qty += 0
            else:
                record.return_qty = 0
            record.return_qty += 0

    @api.depends('source_location_id')
    def avl_qty_calculation(self):
        for record in self:
            product_ids = []
            stock_quant_ids = self.env['stock.quant'].search(
                [('location_id', '=', record.source_location_id.id), ('available_quantity', '>', 0), ('product_id.type', '=', 'product')])
            for quant in stock_quant_ids:
                if quant.available_quantity > 0:
                    product_ids.append(quant.product_id.id)
            record.filter_available_product_ids = [(6, 0, product_ids)]

    @api.depends('product_line.source_warehouse_id', 'product_line.destination_warehouse_id')
    def _compute_filter_loc(self):
        stock_location_model = self.env['stock.location']

        source_warehouse_ids = self.mapped(
            'product_line.source_warehouse_id.id')
        destination_warehouse_ids = self.mapped(
            'product_line.destination_warehouse_id.id')
        warehouse_ids = list(source_warehouse_ids + destination_warehouse_ids)

        all_locations = stock_location_model.search([
            ('warehouse_id', 'in', warehouse_ids),
            ('usage', '=', 'internal'),
            ('active', '=', True)
        ])

        locations_by_warehouse = {
            warehouse_id: [
                location.id for location in all_locations
                if location.warehouse_id.id == warehouse_id
            ]
            for warehouse_id in warehouse_ids
        }

        for record in self:
            source_warehouse_id = record.product_line.source_warehouse_id.id
            dest_warehouse_id = record.product_line.destination_warehouse_id.id

            filter_source_location_ids = locations_by_warehouse.get(
                source_warehouse_id, [])
            filter_dest_location_ids = locations_by_warehouse.get(
                dest_warehouse_id, [])

            record.filter_source_loc = json.dumps(
                [('id', 'in', filter_source_location_ids)]) if filter_source_location_ids else json.dumps([('id', 'in', [])])
            record.filter_dest_loc = json.dumps(
                [('id', 'in', filter_dest_location_ids)]) if filter_dest_location_ids else json.dumps([('id', 'in', [])])



    @api.onchange('product_id')
    def onchange_product_id(self):
        self.uom = False
        if self.product_id:
            self.uom = self.product_id.uom_id.id

    @api.depends('transfer_qty', 'return_qty', 'qty_cancel')
    def calculate_total_trf_qty(self):
        for record in self:
            record.total_trf = record.transfer_qty - record.return_qty - record.qty_cancel

    @api.depends('product_id', 'source_location_id')
    def calculate_current_qty(self):
        is_consignment = self.env['ir.model.fields']._get('stock.quant', 'is_consignment')
        for record in self:
            if record.product_id.type == 'product':
                domain = ([('location_id', '=', record.source_location_id.id), ('product_id', '=', record.product_id.id)])
                if is_consignment:
                    domain += [('is_consignment', '=', False)]
                stock_quant_id = self.env['stock.quant'].search(domain)
                avl_qty = sum(stock_quant_id.mapped('available_quantity'))
                record.current_qty = avl_qty

    def _prepare_transfer_out_line_vals(self, picking, date, sequence):
        self.ensure_one()
        transit_location = self.env.ref('equip3_inventory_masterdata.location_transit')
        vals = self._prepare_transfer_line_vals(self.source_location_id, transit_location, picking, date, sequence)
        vals.update({
            'origin_dest_location': self.destination_location_id.display_name,
        })
        return vals

    def _prepare_transfer_in_line_vals(self, picking, transfer_out, date, sequence):
        self.ensure_one()
        transit_location = self.env.ref('equip3_inventory_masterdata.location_transit')
        vals = self._prepare_transfer_line_vals(transit_location, self.destination_location_id, picking, date, sequence)
        vals.update({
            'origin_src_location': self.source_location_id.display_name,
            'transfer_out_id': transfer_out.id
        })
        return vals

    def _prepare_transfer_line_vals(self, location_id, location_dest_id, picking, date, sequence):
        self.ensure_one()
        return {
            'move_line_sequence': sequence,
            'picking_id': picking.id,
            'name': self.product_id.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.qty,
            'remaining_checked_qty': self.qty,
            'product_uom': self.uom.id,
            'analytic_account_group_ids': [(6, 0, picking.analytic_account_group_ids.ids)],
            'location_id': location_id.id,
            'location_dest_id': location_dest_id.id,
            'date': date,
            'is_transit': True,
            'origin': self.product_line.name
        }
