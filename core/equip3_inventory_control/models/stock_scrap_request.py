from odoo import _, api, fields, models
from odoo.exceptions import UserError,ValidationError
from datetime import datetime, timedelta, date
import pytz
from pytz import timezone, UTC
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.equip3_inventory_operation.models.qiscus_connector import qiscus_request
import json


class StockScrapRequest(models.Model):
    _name = 'stock.scrap.request'
    _description = 'Stock Scrap Request'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    @api.model
    def default_pu_bm_is_cont_scan(self):
        return self.env.company.pu_bm_is_cont_scan

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

    pu_barcode_mobile = fields.Char(string="Mobile Barcode")
    pu_bm_is_cont_scan = fields.Char(
        string='Continuously Scan?', default=default_pu_bm_is_cont_scan, readonly=True)
    pu_barcode_mobile_type = fields.Selection([
        ('int_ref', 'Internal Reference'),
        ('barcode', 'Barcode'),
        ('sh_qr_code', 'QR code'),
        ('all', 'All')
    ], default='barcode', string='Product Scan Options In Mobile (Product Usage)', compute='_compute_barcode_scan')
    pu_bm_is_cont_scan = fields.Boolean(
        string='Continuously Scan? (Product Usage)', compute='_compute_barcode_scan')
    pu_bm_is_notify_on_success = fields.Boolean(
        string='Notification On Product Succeed? (Product Usage)', compute='_compute_barcode_scan')
    pu_bm_is_notify_on_fail = fields.Boolean(
        string='Notification On Product Failed? (Product Usage)', compute='_compute_barcode_scan')
    pu_bm_is_sound_on_success = fields.Boolean(
        string='Play Sound On Product Succeed? (Product Usage)', compute='_compute_barcode_scan')
    pu_bm_is_sound_on_fail = fields.Boolean(
        string='Play Sound On Product Failed? (Product Usage)', compute='_compute_barcode_scan')
    pu_bm_is_add_product = fields.Boolean(
        string="Is add new product in Product Usage? (Product Usage)", compute='_compute_barcode_scan')
    is_mbs_on_product_usage = fields.Boolean(
        string="Is Product Usage", compute='_compute_barcode_scan')

    def _compute_barcode_scan(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        for record in self:
            record.pu_barcode_mobile_type = IrConfigParam.get_param('pu_barcode_mobile_type', 'barcode')
            record.pu_bm_is_cont_scan = IrConfigParam.get_param('pu_bm_is_cont_scan', False)
            record.pu_bm_is_notify_on_success = IrConfigParam.get_param('pu_bm_is_notify_on_success', False)
            record.pu_bm_is_notify_on_fail = IrConfigParam.get_param('pu_bm_is_notify_on_fail', False)
            record.pu_bm_is_sound_on_success = IrConfigParam.get_param('pu_bm_is_sound_on_success', False)
            record.pu_bm_is_sound_on_fail = IrConfigParam.get_param('pu_bm_is_sound_on_fail', False)
            record.pu_bm_is_add_product = IrConfigParam.get_param('pu_bm_is_add_product', False)
            record.is_mbs_on_product_usage = IrConfigParam.get_param('is_mbs_on_product_usage', False)

    company_id = fields.Many2one('res.company', string='Company',tracking=True, readonly=True, default=lambda self: self.env.user.company_id)
    branch_id = fields.Many2one('res.branch',
                                string='Branch',
                                tracking=True,
                                default = _default_branch,
                                domain=_domain_branch,
                                related="warehouse_id.branch_id")
    accounting = fields.Boolean(string="Acccounting", related='company_id.accounting', readonly=False)
    name = fields.Char(string="Reference", readonly=True, tracking=True, default='New', copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', tracking=True, required=True, domain=_domain_branch_warehouse)
    state = fields.Selection([('draft', 'Draft'),
                                    ('confirmed', 'Confirmed'),
                                    ('to_approve', 'Waiting for Approval'),
                                    ('approved', 'Approved'),
                                    ('rejected', 'Rejected'),
                                    ('validating', 'Validating'),
                                    ('validated', 'Validated'),
                                    ('cancel', 'Cancelled')
                                    ], string='Status', tracking=True, default='draft')
    scrap_ids = fields.One2many('stock.scrap', 'scrap_id', tracking=True, required=True)
    scrap_request_name = fields.Char(string='Name', required=True, tracking=True)
    expire_date = fields.Datetime(string="Expiry Date")
    date_done = fields.Datetime('Date of Transfer', copy=False, tracking=True, readonly=True,
                                help="Date at which the transfer has been processed or cancelled.")
    scrap_type = fields.Many2one('usage.type', string="Scrap Type", required=True)
    is_product_usage = fields.Boolean(string="Product Usage")
    payment_method_id = fields.Many2one('account.journal', string="Payment Method", tracking=True)
    is_payment_method = fields.Boolean(string="Payment Usage", compute="_compute_payement_method")
    schedule_date = fields.Datetime(string='Scheduled Date', tracking=True)
    responsible_id = fields.Many2one('res.users', string="Responsible", tracking=True)
    analytic_tag_ids = fields.Many2many("account.analytic.tag",
                                        "scrap_request_analytic_tag_rel",
                                        "stock_scrap_request",
                                        "account_analytic_tag_id",
                                        "Analytic Groups",
                                        default=lambda self: self.env.user.analytic_tag_ids.filtered(lambda a: a.company_id == self.env.company).ids)
    is_group_analytic_tags = fields.Boolean("Is Analytic Group",
                                            compute="_compute_is_group_analytic_tags",
                                            default=lambda self: bool(self.env['ir.config_parameter'].sudo().get_param('group_analytic_tags', False)))
    scrap_state = fields.Selection(related='state', tracking=False, string='Status 0')
    scrap_state_1 = fields.Selection(related='state', tracking=False, string='Status 1')
    is_product_usage_approval = fields.Boolean(string="Product Usage Approval", store=True)
    approval_matrix_id = fields.Many2one('stock.scrap.approval.matrix', string="Approval Matrix", compute='_get_approval_matrix', store=True)
    approved_matrix_ids = fields.One2many('stock.scrap.approval.matrix.line', 'scap_request_id', compute="_compute_approving_matrix_lines_scrap", store=True, string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('stock.scrap.approval.matrix.line', string='Material Approval Matrix Line', compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    account_move_count = fields.Integer(compute='_compute_account_move', string='Account Move count', default=0)
    domain_warehouse_id = fields.Char('Warehouse Domain', compute="_compute_location")

    @api.constrains('scrap_ids','scrap_ids.scrap_qty')
    def validation_for_quantity(self):
        for record in self.scrap_ids:
            if record.available_quantity < record.scrap_qty:
                raise ValidationError(_("Quantity cannot be greater than the available quantity"))

    @api.model
    def default_get(self, fields):
        res = super(StockScrapRequest, self).default_get(fields)
        self._get_usage_approve_button_from_config(res)
        return res

    @api.depends('branch_id')
    def _compute_location(self):
        if self.env.branches.ids:
            warehouse_ids = self.env['stock.warehouse'].search([('branch_id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)])
            if warehouse_ids:
                self.domain_warehouse_id = json.dumps([('id', 'in', warehouse_ids.ids)])
            else:
                self.domain_warehouse_id = json.dumps([])
        else:
            self.domain_warehouse_id = json.dumps([])

    def _compute_account_move(self):
        for record in self:
            record.account_move_count = 0
            account_id = self.env['account.move'].search([
                ('stock_scrap_id', '=', record.id)
            ])
            record.account_move_count = len(account_id)

    def action_journal_items(self):
        account_id = self.env['account.move'].search([('stock_scrap_id', '=', self.id)], limit=1)
        view_mode = "form" if self.account_move_count == 1 else "tree,form"
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'view_mode': view_mode,
            'res_model': 'account.move',
            'domain': [('stock_scrap_id', '=', self.id)],
            "target": "current",
            "res_id": account_id.id if self.account_move_count == 1 else False,
        }

    @api.onchange('warehouse_id')
    def _onchange_warehouse(self):
        # print('chk----')
        for line in self.scrap_ids:
            if self.warehouse_id.id != line.location_id.warehouse_id.id:
                # print('cht')
                if self.state != 'validated':
                    self.write({'scrap_ids': [(3, line.id)]})


    @api.onchange('pu_barcode_mobile')
    def _onchange_pu_barcode_mobile(self):

        if self.pu_barcode_mobile in ['', "", False, None]:
            return

        CODE_SOUND_SUCCESS = ""
        CODE_SOUND_FAIL = ""
        if self.pu_bm_is_sound_on_success:
            CODE_SOUND_SUCCESS = "SH_BARCODE_MOBILE_SUCCESS_"

        if self.pu_bm_is_sound_on_fail:
            CODE_SOUND_FAIL = "SH_BARCODE_MOBILE_FAIL_"

        if self and self.state != 'draft':
            selections = self.fields_get()['state']['selection']
            value = next((v[1] for v in selections if v[0]
                          == self.state), self.state)
            if self.pu_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL +
                            'You can not scan item in %s state.') % (value)
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
            return
        elif self:
            search_pul = False
            domain = []

            if self.pu_barcode_mobile_type == 'barcode':
                search_pul = self.scrap_ids.filtered(
                    lambda ml: ml.product_id.barcode == self.pu_barcode_mobile)
                domain = [("barcode", "=", self.pu_barcode_mobile)]

            elif self.pu_barcode_mobile_type == 'int_ref':
                search_pul = self.scrap_ids.filtered(
                    lambda ml: ml.product_id.default_code == self.pu_barcode_mobile)
                domain = [("default_code", "=", self.pu_barcode_mobile)]

            elif self.pu_barcode_mobile_type == 'sh_qr_code':
                search_pul = self.scrap_ids.filtered(
                    lambda ml: ml.product_id.sh_qr_code == self.pu_barcode_mobile)
                domain = [("sh_qr_code", "=", self.pu_barcode_mobile)]

            elif self.pu_barcode_mobile_type == 'all':
                search_pul = self.scrap_ids.filtered(
                    lambda ml: ml.product_id.barcode == self.pu_barcode_mobile or ml.product_id.default_code == self.pu_barcode_mobile)
                domain = ["|", "|",
                          ("default_code", "=", self.pu_barcode_mobile),
                          ("barcode", "=", self.pu_barcode_mobile),
                          ("sh_qr_code", "=", self.pu_barcode_mobile),
                          ]

            if search_pul:
                for line in search_pul:
                    line.write({'scrap_qty': line.scrap_qty + 1})
                    if self.pu_bm_is_notify_on_success:
                        message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                            line.product_id.name, line.scrap_qty)
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                             self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
            elif self.state == 'draft':
                if self.pu_bm_is_add_product:

                    search_product = self.env["product.product"].search(
                        domain, limit=1)
                    addtional_ids = False
                    if self.warehouse_id:
                        location_ids = []
                        location_obj = self.env['stock.location']
                        store_location_id = self.warehouse_id.view_location_id.id
                        addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')], order='id')
                    if search_product:
                        product_vals = {
                                        "name": search_product.name,
                                        "product_id": search_product.id,
                                        "product_uom_id": search_product.uom_id.id,
                                        "scrap_qty": 1,
                                        "location_id": addtional_ids and addtional_ids[0].id or False,
                                    }
                        self.scrap_ids = [(0, 0, product_vals)]
                        if self.pu_bm_is_notify_on_success:
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                search_product.name, 1)
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                 self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                        return

                    else:
                        if self.pu_bm_is_notify_on_fail:
                            message = _(
                                CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                 self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

                        return

                else:
                    if self.pu_bm_is_notify_on_fail:
                        message = _(
                            CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                             self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

                    return

            else:
                if self.pu_bm_is_notify_on_fail:
                    message = _(
                        CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                    self.env['bus.bus'].sendone(
                        (self._cr.dbname, 'res.partner',
                         self.env.user.partner_id.id),
                        {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

                return
        else:
            # failed message here
            if self.pu_bm_is_notify_on_fail:
                message = _(
                    CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

            return

    def _get_usage_approve_button_from_config(self, res):
        is_product_usage_approval_config = self.env[
            'ir.config_parameter'].sudo().get_param(
                'is_product_usage_approval', False)
        res.update(
            {'is_product_usage_approval': is_product_usage_approval_config})

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

    @api.depends('warehouse_id', 'is_product_usage_approval')
    def _get_approval_matrix(self):
        for record in self:
            if record.is_product_usage_approval:
                matrix_id = self.env['stock.scrap.approval.matrix'].search([('warehouse_id', '=', record.warehouse_id.id)], limit=1)
                record.approval_matrix_id = matrix_id.id

    @api.depends('approval_matrix_id')
    def _compute_approving_matrix_lines_scrap(self):
        data = [(5, 0, 0)]
        for record in self:
            counter = 1
            record.approved_matrix_ids = []
            for line in record.approval_matrix_id.sc_approval_matrix_line_ids:
                data.append((0, 0, {
                    'sequence' : counter,
                    'user_ids' : [(6, 0, line.user_ids.ids)],
                    'minimum_approver' : line.minimum_approver,
                }))
                counter += 1
            record.approved_matrix_ids = data

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id_boolean(self):
        self._compute_barcode_scan()

    def scrap_request_for_approving(self):
        for record in self:
            values = {
                'sender': self.env.user,
                'name': 'Product Usage',
                'no': record.name,
                'datetime': fields.Datetime.now(),
                'action_xmlid': 'equip3_inventory_control.action_stock_product_usage',
                'menu_xmlid': 'equip3_inventory_control.menuitem_stock_product_usage'
            }

            for approver in record.approved_matrix_ids.mapped('user_ids'):
                values.update({'receiver': approver})
                qiscus_request(record, values)
            record.write({'state': 'to_approve'})

    def scrap_approving(self):
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
                    local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (self.env.user.name, local_datetime)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True})
                        # next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        # if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].approver) > 1:
                        #     pass
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r:r.approved)):
                record.write({'state': 'approved'})

    def scrap_reject(self):
        for record in self:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Reject Product Usage Matrix',
                    'res_model': 'stock.scrap.request.matrix.reject',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }

    def set_to_draft_scp(self):
        for record in self:
            record.write({'state': 'draft'})

    @api.depends('scrap_type.usage_type',
                'scrap_type.income_account_id',
                'scrap_type', 'state',
                'scrap_ids', 'scrap_ids.cost_price')
    def _compute_payement_method(self):
        for record in self:
            if record.scrap_type.usage_type == 'scrap' and \
               record.scrap_type.income_account_id and \
               record.scrap_ids and \
               record.accounting and \
               all(line.cost_price > 0 for line in record.scrap_ids):
                record.is_payment_method = True
            else:
                record.is_payment_method = False

    def action_request_confirm(self):
        for record in self:
            record.write({'state': 'confirmed'})
            # for line in record.scrap_ids:
            #     line.action_validate()
            #     line.move_id.reference = record.name
            #     for move_line_id in line.move_id.move_line_ids:
            #         move_line_id.write({
            #             'reference': record.name,
            #             'scrap_sale_price': line.sale_price,
            #         })

    # def action_request_validated(self):
    #     for record in self:
    #         import datetime
    #         today = datetime.date.today()
    #         if record.expire_date and record.expire_date.date() < today:
    #             raise UserError(_('Product usage is expired'))
    #         context = dict(self.env.context) or {}

    #         analytic_tag_ids = bool(self.env['ir.config_parameter'].sudo().get_param('group_analytic_tags', False)) and \
    #                            [(6, 0, record.analytic_tag_ids.ids)] or \
    #                            [(6, 0, [])]

    #         for scrap_id in record.scrap_ids:
    #             picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id', '=', record.warehouse_id.id)], limit=1)
    #             label_name = record.name + " - " + scrap_id.product_id.name
    #             scrap_id.action_validate()
    #             scrap_id.move_id.reference = record.name
    #             scrap_id.move_id.picking_type_id = picking_type_id.id
    #             for move_line_id in scrap_id.move_id.move_line_ids:
    #                 move_line_id.write({
    #                     'reference': record.name,
    #                     'scrap_sale_price': scrap_id.sale_price,
    #                 })
    #             for move_line in scrap_id.move_id.move_line_ids:
    #                 # move_line.write({
    #                 #     'reference': record.name,
    #                 #     'scrap_sale_price': scrap_id.sale_price,
    #                 # })
    #                 # value = sum(scrap_id.move_id.stock_valuation_layer_ids.mapped('unit_cost')) * move_line.qty_done
    #                 value = scrap_id.product_id.standard_price * move_line.qty_done
    #                 scrap_journal_id = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', record.company_id.id), '|', ('name', 'ilike', 'Miscellaneous'), ('name', 'ilike', 'Inventory Valuation')], limit=1, order="id desc")
    #                 if not record.accounting and value > 0:
    #                     credit_vals = {
    #                         'name' : label_name,
    #                         'debit' : 0,
    #                         'credit' : value,
    #                         'date' : fields.datetime.now(),
    #                         'account_id' : scrap_id.product_id.categ_id.property_stock_valuation_account_id.id,
    #                         # self.env.ref('equip3_inventory_masterdata.data_account_account_other_inventory').id,
    #                         'analytic_tag_ids': analytic_tag_ids
    #                     }
    #                     debit_vals = {
    #                         'name' : label_name,
    #                         'credit' : 0,
    #                         'debit' : value,
    #                         'date' : fields.datetime.now(),
    #                         'account_id' : scrap_id.product_id.categ_id.stock_scrap_account.id,
    #                         'analytic_tag_ids': analytic_tag_ids
    #                     }
    #                     vals = {
    #                         'ref' : move_line.reference,
    #                         'date' : fields.datetime.now(),
    #                         'journal_id' : scrap_journal_id.id,
    #                         'move_type': 'entry',
    #                         'branch_id' : record.branch_id.id,
    #                         'line_ids' : [(0, 0, credit_vals), (0, 0, debit_vals)],
    #                         'stock_scrap_id': record.id
    #                     }
    #                     # print(">>>>>>>>>>>>>>>>>>>>vals",vals)

    #                     move_id = self.env['account.move'].create(vals)
    #                     move_id.action_post()
    #                 # kalau harga == 0 kena fungsi ini dan type scrap / usage
    #                 elif record.accounting and value > 0:
    #                     if move_line.location_dest_id.usage != 'internal':
    #                         journal_id = record.payment_method_id
    #                         if record.scrap_type.usage_type == "usage" or (record.scrap_type.usage_type == "scrap" and scrap_id.sale_price == 0):
    #                             credit_vals = {
    #                                 'name' : label_name,
    #                                 'debit' : 0,
    #                                 'credit' : value,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : scrap_id.product_id.categ_id.property_stock_valuation_account_id.id,
    #                                 # self.env.ref('equip3_inventory_masterdata.data_account_account_other_inventory').id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             debit_vals = {
    #                                 'name' : label_name,
    #                                 'credit' : 0,
    #                                 'debit' : value,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : record.scrap_type.account_id.id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             vals = {
    #                                 'ref' : move_line.reference,
    #                                 'date' : fields.datetime.now(),
    #                                 'stock_scrap_id': record.id,
    #                                 'journal_id' : scrap_journal_id.id,
    #                                 'move_type': 'entry',
    #                                 'branch_id' : record.branch_id.id,
    #                                 'line_ids' : [(0, 0, credit_vals), (0, 0, debit_vals)]
    #                             }
    #                             # print(">>>>>>>>>>>>>>>>>>>>vals",vals)

    #                             move_id = self.env['account.move'].create(vals)
    #                             move_id.action_post()

    #                         # if sale price > product.standard_price and scrap type == scrap
    #                         if record.scrap_type.usage_type == "scrap" and \
    #                             scrap_id.sale_price > scrap_id.product_id.standard_price \
    #                             and record.payment_method_id:
    #                             credit_vals = {
    #                                 'name' : label_name,
    #                                 'debit' : 0,
    #                                 'credit' : scrap_id.product_id.standard_price * scrap_id.scrap_qty,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : scrap_id.product_id.categ_id.property_stock_valuation_account_id.id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             debit_vals = {
    #                                 'name' : label_name,
    #                                 'credit' : 0,
    #                                 'debit' : scrap_id.product_id.standard_price * scrap_id.scrap_qty,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : record.payment_method_id.payment_debit_account_id.id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             vals = {
    #                                 'ref' : move_line.reference,
    #                                 'date' : fields.datetime.now(),
    #                                 'stock_scrap_id': record.id,
    #                                 'journal_id' : scrap_journal_id.id,
    #                                 'move_type': 'entry',
    #                                 'branch_id' : record.branch_id.id,
    #                                 'line_ids' : [(0, 0, credit_vals), (0, 0, debit_vals)]
    #                             }
    #                             # print(">>>>>>>>>>>>>>>>>>>>vals",vals)

    #                             move_id = self.env['account.move'].create(vals)
    #                             move_id.action_post()
    #                             credit_vals = {
    #                                 'name' : label_name,
    #                                 'debit' : 0,
    #                                 'credit' : (scrap_id.sale_price - scrap_id.product_id.standard_price) * scrap_id.scrap_qty,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : record.scrap_type.income_account_id.id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             debit_vals = {
    #                                 'name' : label_name,
    #                                 'credit' : 0,
    #                                 'debit' : (scrap_id.sale_price - scrap_id.product_id.standard_price) * scrap_id.scrap_qty,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : record.payment_method_id.payment_debit_account_id.id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             vals = {
    #                                 'ref' : move_line.reference,
    #                                 'date' : fields.datetime.now(),
    #                                 'stock_scrap_id': record.id,
    #                                 'journal_id' : journal_id.id,
    #                                 'move_type': 'entry',
    #                                 'branch_id' : record.branch_id.id,
    #                                 'line_ids' : [(0, 0, credit_vals), (0, 0, debit_vals)]
    #                             }
    #                             # print(">>>>>>>>>>>>>>>>>>>>vals",vals)
    #                             move_id = self.env['account.move'].create(vals)
    #                             move_id.action_post()

    #                         # if sale price < product.standard_price and scrap type == scrap
    #                         if record.scrap_type.usage_type == "scrap" and \
    #                             scrap_id.sale_price < scrap_id.product_id.standard_price \
    #                             and record.payment_method_id:
    #                             credit_vals = {
    #                                 'name' : label_name,
    #                                 'debit' : 0,
    #                                 'credit' : (scrap_id.product_id.standard_price - scrap_id.sale_price) * scrap_id.scrap_qty,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : scrap_id.product_id.categ_id.property_stock_valuation_account_id.id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             debit_vals = {
    #                                 'name' : label_name,
    #                                 'credit' : 0,
    #                                 'debit' : (scrap_id.product_id.standard_price - scrap_id.sale_price) * scrap_id.scrap_qty,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : record.scrap_type.account_id.id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             vals = {
    #                                 'ref' : move_line.reference,
    #                                 'date' : fields.datetime.now(),
    #                                 'stock_scrap_id': record.id,
    #                                 'journal_id' : scrap_journal_id.id,
    #                                 'move_type': 'entry',
    #                                 'branch_id' : record.branch_id.id,
    #                                 'line_ids' : [(0, 0, credit_vals), (0, 0, debit_vals)]
    #                             }
    #                             # print(">>>>>>>>>>>>>>>>>>>>vals",vals)

    #                             move_id = self.env['account.move'].create(vals)
    #                             move_id.action_post()
    #                             credit_vals = {
    #                                 'name' : label_name,
    #                                 'debit' : 0,
    #                                 'credit' : scrap_id.sale_price * scrap_id.scrap_qty,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : scrap_id.product_id.categ_id.property_stock_valuation_account_id.id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             debit_vals = {
    #                                 'name' : label_name,
    #                                 'credit' : 0,
    #                                 'debit' : scrap_id.sale_price * scrap_id.scrap_qty,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : record.payment_method_id.payment_debit_account_id.id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             vals = {
    #                                 'ref' : move_line.reference,
    #                                 'date' : fields.datetime.now(),
    #                                 'stock_scrap_id': record.id,
    #                                 'journal_id' : journal_id.id,
    #                                 'move_type': 'entry',
    #                                 'branch_id' : record.branch_id.id,
    #                                 'line_ids' : [(0, 0, credit_vals), (0, 0, debit_vals)]
    #                             }
    #                             # print(">>>>>>>>>>>>>>>>>>>>vals",vals)
    #                             move_id = self.env['account.move'].create(vals)
    #                             move_id.action_post()

    #                         # if sale price == product.standard_price and scrap type == scrap
    #                         if record.scrap_type.usage_type == "scrap" and \
    #                             scrap_id.sale_price == scrap_id.product_id.standard_price \
    #                             and record.payment_method_id:
    #                             credit_vals = {
    #                                 'name' : label_name,
    #                                 'debit' : 0,
    #                                 'credit' : scrap_id.sale_price * scrap_id.scrap_qty,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : scrap_id.product_id.categ_id.property_stock_valuation_account_id.id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             debit_vals = {
    #                                 'name' : label_name,
    #                                 'credit' : 0,
    #                                 'debit' : scrap_id.sale_price * scrap_id.scrap_qty,
    #                                 'date' : fields.datetime.now(),
    #                                 'account_id' : record.payment_method_id.payment_debit_account_id.id,
    #                                 'analytic_tag_ids': analytic_tag_ids
    #                             }
    #                             vals = {
    #                                 'ref' : move_line.reference,
    #                                 'date' : fields.datetime.now(),
    #                                 'stock_scrap_id': record.id,
    #                                 'journal_id' : scrap_journal_id.id,
    #                                 'move_type': 'entry',
    #                                 'branch_id' : record.branch_id.id,
    #                                 'line_ids' : [(0, 0, credit_vals), (0, 0, debit_vals)]
    #                             }
    #                             # print(">>>>>>>>>>>>>>>>>>>>vals",vals)
    #                             move_id = self.env['account.move'].create(vals)
    #                             move_id.action_post()

    #         return self.write({'state': 'validated', 'date_done': fields.datetime.now()})

    def action_request_validated(self):
        freezed_locations = self.env['stock.move']._get_freezed_locations()
        for scrap in self.scrap_ids:
            if scrap.location_id.id in freezed_locations:
                freeze_source = freezed_locations[scrap.location_id.id]
                raise ValidationError(_("Can't move from/to location %s, because the location is in freeze status from %s. Stock move can be process after operation is done." % (scrap.location_id.display_name, freeze_source)))

        use_scheduler = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_control.stock_scrap_validation_scheduler', 'False'))

        if use_scheduler:
            for request in self:
                self.env['stock.scrap.request.log'].create({'scrap_request_id': request.id})
                self.write({'state': 'validating'})
            return

        self.scrap_ids._request()
        self._done_request()

    def _done_request(self):
        self.write({'state': 'validated', 'date_done': fields.Datetime.now()})

    def action_cancel(self):
        for record in self:
            if record.state == 'validated':
                scrap_name = record.scrap_ids.mapped('name')
                journal_entries_ids = self.env['account.move.line'].search([("name", 'in', scrap_name)]).mapped('move_id')
                journal_entries_ids.button_draft()
                journal_entries_ids.button_cancel()
                for scrap_id in record.scrap_ids:
                    new_move_id = scrap_id.move_id.copy({
                        'location_id': scrap_id.move_id.location_dest_id.id,
                        'location_dest_id': scrap_id.move_id.location_id.id,
                        'product_uom_qty': scrap_id.move_id.product_uom_qty,
                        'state': 'done'})
                    for move_line_id in scrap_id.move_id.move_line_ids:
                        new_move_line_id = move_line_id.copy({
                            'move_id': new_move_id.id,
                            'state': 'done',
                            'qty_done': move_line_id.qty_done,
                            'location_id': move_line_id.location_dest_id.id,
                            'location_dest_id': move_line_id.location_id.id
                        })
            record.write({'state': 'cancel'})

    @api.model
    def _cron_auto_cancel_product_usage(self):
        today = datetime.now()
        product_usage_ids = self.search([('state', '=', 'confirmed'), ('expire_date', '<', today)])
        for record in product_usage_ids:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id='+ str(record.id) + '&view_type=form&model=stock.scrap.request'
            template_id = self.env.ref('equip3_inventory_control.email_template_product_usage_scrap_auto_cancel')
            ctx = {
                    'email_from': self.env.user.company_id.email,
                    'url': url,
                    'is_lot': record.scrap_ids.filtered(lambda r:r.lot_id),
                    'is_package': record.scrap_ids.filtered(lambda r:r.package_id),
                    'is_owner': record.scrap_ids.filtered(lambda r:r.owner_id),
                }
            template_id.with_context(ctx).send_mail(record.id, True)
            template_id = self.env["ir.model.data"].xmlid_to_object(
                "equip3_inventory_control.email_template_product_usage_scrap_auto_cancel"
            )

            body_html = self.env['mail.render.mixin'].with_context(ctx)._render_template(
                        template_id.body_html, 'stock.scrap.request', record.ids, post_process=True)[record.id]
            message_id = (
                self.env["mail.message"]
                .sudo()
                .create(
                    {
                        "subject": "Product Usage Expire",
                        "body": body_html,
                        "model": "stock.scrap.request",
                        "res_id": record.id,
                        "message_type": "notification",
                        "partner_ids": [
                            (
                                6,
                                0,
                                record.responsible_id.partner_id.ids,
                            )
                        ],
                    }
                )
            )
            notif_create_values = {
                "mail_message_id": message_id.id,
                "res_partner_id": record.responsible_id.partner_id.id,
                "notification_type": "inbox",
                "notification_status": "sent",
            }
            self.env["mail.notification"].sudo().create(notif_create_values)
            record.write({'state': 'cancel'})

    @api.onchange('schedule_date')
    def onchange_schedule_date(self):
        if self.schedule_date:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            expiry_days_select = IrConfigParam.get_param('expiry_days_select', 'before')
            product_expiry = IrConfigParam.get_param('product_expiry', 0)
            if expiry_days_select == 'before':
                self.expire_date = self.schedule_date - timedelta(days=int(product_expiry))
            else:
                self.expire_date = self.schedule_date + timedelta(days=int(product_expiry))

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == _('New'):
            if vals.get('is_product_usage'):
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.product.usage')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.scrap.request')
            if not vals.get('scrap_type'):
                raise ValidationError(_('Please Fill the Usage Type'))
            if not vals.get('scrap_ids'):
                raise ValidationError(_('Please Fill the Scrap'))

        res = super(StockScrapRequest, self).create(vals)
        return res


    def _compute_is_group_analytic_tags(self):
        for rec in self:
            rec.is_group_analytic_tags = bool(self.env['ir.config_parameter'].sudo().get_param('group_analytic_tags', False))


    def get_selection_label(self, field_name, field_value):
        field = self._fields.get(field_name)
        if field and field.type == 'selection':
            selection_dict = dict(self._fields[field_name].selection)
            label = selection_dict.get(field_value)
        return label

    def unlink(self):
        for record in self:
            if record.state in ('confirmed', 'validated'):
                state_label = record.get_selection_label('state', record.state)
                if state_label:
                    raise ValidationError(f'You can not delete product usage in {state_label.lower()} status')
        return super(StockScrapRequest, self).unlink()


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    product_uom_id = fields.Many2one(domain="[]")
    scrap_id = fields.Many2one('stock.scrap.request', string="Scrap")
    filter_location_ids = fields.Many2many('stock.location', compute='_get_stock_locations', store=False)
    filter_product_ids = fields.Many2many('product.product', compute='_get_product_by_locations', store=False)
    location_id = fields.Many2one('stock.location', default=False)
    cost_price = fields.Float(string="Cost Price", readonly=True, help="By default, the value is automatically filled from the 'Cost' price (standard_price) of the product.")
    product_usage_state = fields.Selection(related="scrap_id.state", string='Scrap Status')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Groups', related="scrap_id.analytic_tag_ids")
    filter_lot_ids = fields.Many2many('stock.production.lot', compute='_get_lot_serial', store=False)
    filter_package_ids = fields.Many2many('stock.quant.package', compute='_get_lot_serial', store=False)
    filter_owner_ids = fields.Many2many('res.partner', compute='_get_lot_serial', store=False)
    scrap_qty = fields.Float(default=0)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', tracking=True, related="scrap_id.warehouse_id")
    available_quantity = fields.Float('Available Quantity')

    # technical field
    is_validated = fields.Boolean()

    @api.onchange('location_id', 'product_id', 'lot_id')
    def _onchange_location_and_product_id(self):
        for record in self.filtered('scrap_id'):
            if not record.location_id or not record.product_id:
                continue

            tracking = record.product_id.tracking
            lot_id = record.lot_id if tracking != 'none' else None
            available_qty = self.env['stock.quant']._get_available_quantity(
                record.product_id,
                record.location_id,
                lot_id,
                strict=True
            )
            record.available_quantity = available_qty

    @api.onchange('location_id')
    def _onchange_location(self):
        if self.scrap_id:
            company_id = self.env.context.get('default_company_id') or self.env.company.id
            list_scrap = self.env['stock.location'].search([('scrap_location', '=', True), ('company_id', 'in', [company_id, False])])
            virtual_scrap = list_scrap.filtered(lambda r: r.usage == 'inventory' and r.scrap_location).sorted(key=lambda r: r.company_id.id)
            self.scrap_location_id = virtual_scrap[-1].id
        else:
            return {'domain': {'location_id': [('warehouse_id', '=', self.scrap_id.warehouse_id.id)]}}

    def _get_product_warehouse_price(self, product_id, warehouse_id):
        is_cost_per_warehouse = self.env['ir.config_parameter'].sudo().get_param(
            'equip3_inventory_base.is_cost_per_warehouse', False)
        if is_cost_per_warehouse:
            product_price = self.env['product.warehouse.price'].sudo().search(
                [('product_id', '=', product_id), ('warehouse_id', '=', warehouse_id)], limit=1).standard_price or 0
        else:
            product_price = self.env['product.product'].browse(
                product_id).standard_price
        return product_price or self.env['product.product'].browse(product_id).standard_price

    @api.onchange('product_id', 'product_uom_id', 'scrap_qty')
    def onchange_product_id(self):
        if self.product_id:
            
            price = self._get_product_warehouse_price(self.product_id.id, self.scrap_id.warehouse_id.id)
            if self.product_uom_id:
                price = self.product_id.uom_id._compute_price(self.scrap_qty, self.product_uom_id) * price
            self.cost_price = price
        self._get_stock_locations()
        self._get_product_by_locations()

    @api.onchange('company_id')
    def _onchange_company_id(self):
        res = super(StockScrap, self)._onchange_company_id()
        if self.scrap_id.warehouse_id:
            location_ids = []
            location_obj = self.env['stock.location']
            store_location_id = self.scrap_id.warehouse_id.view_location_id.id
            addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')], order='id')
            if addtional_ids:
                self.location_id = addtional_ids[0].id
        return res

    def _get_stock_locations(self):
        for record in self:
            location_ids = []
            location_obj = self.env['stock.location']
            store_location_id = record.scrap_id.warehouse_id.view_location_id.id
            addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')], order='id')
            for location in addtional_ids:
                if location.location_id.id not in addtional_ids.ids:
                    location_ids.append(location.id)
            record.filter_location_ids = [(6, 0, location_ids)]
            # if not self.scrap_id.warehouse_id:
            #     record.location_id = False
            if not self.product_id:
                record.location_id = False
            # if self.location_id.id not in location_ids:
            #     record.location_id = False

    @api.depends('location_id', 'product_id')
    def _get_lot_serial(self):
        for record in self:
            record.filter_package_ids = []
            record.filter_owner_ids = []
            record.filter_lot_ids = []

            if record.location_id and record.product_id:
                quant_ids = self.env['stock.quant']._get_available_lots(location_id=record.location_id.id, product_id=record.product_id.id)
                record.filter_lot_ids = [(6, 0, quant_ids.mapped('lot_id').ids)]
                record.filter_package_ids = [(6, 0, quant_ids.mapped('package_id').ids)]
                record.filter_owner_ids = [(6, 0, quant_ids.mapped('owner_id').ids)]
            

    @api.depends('location_id')
    def _get_product_by_locations(self):
        for record in self:
            product_ids = self.env['stock.quant'].search([('location_id', '=', record.location_id.id)]).mapped('product_id')
            record.filter_product_ids = [(6, 0, product_ids.ids)]

    def _request(self, log_line=None):
        if not self:
            return

        if log_line:
            log_line.state = 'running'

        StockPickingType = self.env['stock.picking.type']
        AccountMove = self.env['account.move']
        config_param_obj = self.env['ir.config_parameter'].sudo()
        use_analytic_tags = bool(config_param_obj.get_param('group_analytic_tags', False))

        record = self[0].scrap_id

        picking_type = StockPickingType.search([
            ('code', '=', 'outgoing'),
            ('warehouse_id', '=', record.warehouse_id.id)
        ], limit=1)

        if not picking_type:
            raise ValidationError(_('Outgoing picking type not found for warehouse %s') % record.warehouse_id.name)

        usage_type = record.scrap_type.usage_type

        analytic_tag_ids = [(6, 0, record.analytic_tag_ids.ids)] if use_analytic_tags else [(6, 0, [])]

        move_lines = []
        current_date = fields.Datetime.now()

        for scrap in self:
            label_name = f"{record.name} - {scrap.product_id.name}"
            result = scrap.action_validate()
            if result is not True:
                raise ValidationError(result.get('name', scrap.product_id.display_name + _(': Insufficient Quantity To Scrap')))

            scrap.move_id.reference = record.name
            scrap.move_id.picking_type_id = picking_type.id

            if scrap.cost_price > 0:
                category = scrap.product_id.categ_id
                stock_account_output_id = category.property_stock_account_output_categ_id.id
                stock_valuation_account_id = category.property_stock_valuation_account_id.id
                journal_id = category.property_stock_journal.id

                if not stock_account_output_id:
                    raise ValidationError(_('Stock Output Account is not set for category %s') % category.name)
                if not stock_valuation_account_id:
                    raise ValidationError(_('Stock Valuation Account is not set for category %s') % category.name)
                if not journal_id:
                    raise ValidationError(_('Stock Journal is not set for category %s') % category.name)

                amount = scrap.cost_price * scrap.scrap_qty

                for move_line in scrap.move_id.move_line_ids:
                    debit_vals = {
                        'name': label_name,
                        'debit': amount,
                        'credit': 0,
                        'date': current_date,
                        'account_id': record.scrap_type.account_id.id if usage_type != "scrap" else record.scrap_type.account_id.id,
                        'analytic_tag_ids': analytic_tag_ids,
                    }

                    credit_vals = {
                        'name': label_name,
                        'debit': 0,
                        'credit': amount,
                        'date': current_date,
                        'account_id': stock_valuation_account_id if usage_type != "scrap" else record.scrap_type.income_account_id.id,
                        'analytic_tag_ids': analytic_tag_ids,
                    }

                    move_vals = {
                        'name': '/',
                        'ref': move_line.reference,
                        'date': current_date,
                        'stock_scrap_id': record.id,
                        'journal_id': journal_id,
                        'move_type': 'entry',
                        'branch_id': record.branch_id.id,
                        'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)],
                    }
                    move_lines.append(move_vals)
        
        if move_lines:
            moves = AccountMove.create(move_lines)
            moves._post()
        
        self.is_validated = True

    def _prepare_move_values(self):
        res = super(StockScrap, self)._prepare_move_values()
        res['scrap_ids'] = [(4, self.id)]
        return res

    # @api.onchange('product_id', 'location_id', 'lot_id', 'scrap_qty')
    # def _onchange_available_quantity(self):
    #     disallowed_negative = self.env['ir.config_parameter'].sudo().get_param('qty_can_minus', False)
    #     if not disallowed_negative:
    #         return

    #     for record in self.filtered(lambda r: r.scrap_id and r.location_id and r.product_id and r.scrap_qty):

    #         product = record.product_id
    #         location = record.location_id
    #         scrap_qty = record.scrap_qty
    #         lot_serial = record.lot_id

    #         is_lot_serial = product.tracking != 'none'

    #         available_qty = self.env['stock.quant']._get_available_quantity(
    #             product,
    #             location,
    #             lot_id=lot_serial if lot_serial else None,
    #             strict=True,
    #         )

    #         quantity = available_qty - scrap_qty

    #         if is_lot_serial:
    #             if record.lot_id:
    #                 if scrap_qty > available_qty:
    #                     msg_add = f" lot '{lot_serial.name_get()[0][1]}'" if lot_serial and is_lot_serial else ''
    #                     raise ValidationError(
    #                         f"You cannot validate this stock operation because the stock level of the product '{product.display_name}'{msg_add} would become "
    #                         f"negative ({quantity}) on the stock location '{location.complete_name}' and negative stock is not allowed."
    #                     )
    #         else:
    #             if scrap_qty > available_qty:
    #                 raise ValidationError(
    #                     f"You cannot validate this stock operation because the stock level of the product '{product.display_name}' would become "
    #                     f"negative ({quantity}) on the stock location '{location.complete_name}' and negative stock is not allowed."
    #                 )

class StockScrapApprovalMatrixLine(models.Model):
    _inherit = "stock.scrap.approval.matrix.line"

    scap_request_id = fields.Many2one('stock.scrap.request', string="Product Usage")
