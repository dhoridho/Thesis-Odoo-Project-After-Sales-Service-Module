import pytz
from odoo import tools
from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.equip3_inventory_operation.models.qiscus_connector import qiscus_request


class MaterialRequest(models.Model):
    _name = 'material.request'
    _description = "Material Request"
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Reference", required=True,
                           default="New", tracking=True, index=True)
    create_date = fields.Datetime('Create On', tracking=True, readonly='1')
    create_uid = fields.Many2one(
        'res.users', 'Created by', tracking=True, readonly='1')
    requested_by = fields.Many2one(
        'res.users', 'Requested By', required='1', tracking=True, default=lambda self: self.env.user.id)
    destination_location_id = fields.Many2one(
        'stock.location', 'Destination Location', tracking=True)
    destination_warehouse_id = fields.Many2one(
        'stock.warehouse', 'Destination Warehouse', tracking=True)
    company_id = fields.Many2one('res.company', 'Company', readonly='1',
                                 related='destination_warehouse_id.company_id', tracking=True, index=True)
    branch_id = fields.Many2one(
        'res.branch', 'Branch', related='destination_warehouse_id.branch_id', tracking=True, readonly=True, index=True)
    schedule_date = fields.Date('Scheduled Date', tracking=True, required='1')
    expiry_date = fields.Date('Expiry Date', tracking=True)
    description = fields.Text('Description', tracking=True)
    source_document = fields.Char('Source Document', tracking=True)
    status = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
        ('done', 'Done')
    ],
        default="draft", tracking=True, copy=False, index=True)
    status_1 = fields.Selection(related='status', index=True, string='Status 1')
    status_2 = fields.Selection(related='status', index=True, string='Status 2')
    status_3 = fields.Selection(related='status', index=True, string='Status 3')
    product_line = fields.One2many(
        'material.request.line', 'material_request_id', 'Products', tracking=True)
    purchase_request = fields.Integer(string='Purchase Request', tracking=True)
    internal_transfer = fields.Integer(
        'Internal Transfer Request', tracking=True)
    check_product = fields.Boolean(
        default=False, compute='_compute_check_product')
    mr_approval_matrix_id = fields.Many2one(
        'mr.approval.matrix', string="Approval Matrix", compute='_get_approval_matrix', store=True)
    is_material_request_approval_matrix = fields.Boolean(
        string="Material Request", store=True)
    approved_matrix_ids = fields.One2many('mr.approval.matrix.line', 'mr_matrix_id',
                                          compute="_compute_approving_matrix_lines_mr", store=True, string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one(
        'mr.approval.matrix.line', string='Material Approval Matrix Line', compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(
        string='Is Approve Button', compute='_get_approve_button', store=False)
    is_reset_to_draft = fields.Boolean(
        string='Is Reset to Draft', compute='_get_is_show_draft', store=False)
    analytic_account_group_ids = fields.Many2many('account.analytic.tag', 'mr_analytic_rel', 'tag_id', 'mr_id', string="Analytic Groups",
                                                  required=True, default=lambda self: self.env.user.analytic_tag_ids.filtered(lambda a: a.company_id == self.env.company).ids)
    cancel_reason = fields.Text("Cancel Reason")
    internal_note = fields.Text("Internal Note")
    pr_count = fields.Integer(default=0, compute="_compute_pr_count")
    ir_count = fields.Integer(default=0, compute="_compute_ir_count")
    itr_war_count = fields.Integer(default=0, compute="_compute_itr_war_count")


    @api.model
    def default_get(self, fields):
        res = super(MaterialRequest, self).default_get(fields)
        is_material_request_approval_config = self.env['ir.config_parameter'].sudo().get_param('is_material_request_approval_matrix', False)
        res.update({
            'is_material_request_approval_matrix':is_material_request_approval_config
        })
        return res


    @api.depends('destination_warehouse_id','is_material_request_approval_matrix')
    def _get_approval_matrix(self):
        for record in self:
            if record.is_material_request_approval_matrix:
                matrix_id = self.env['mr.approval.matrix'].search(
                    [('warehouse_id', '=', record.destination_warehouse_id.id)], limit=1)
                record.mr_approval_matrix_id = matrix_id

    def _get_street(self, partner):
        self.ensure_one()
        address = ''
        if partner.street:
            address = "%s" % partner.street
        if partner.street2:
            address += ", %s" % partner.street2
        # reload(sys)
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
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.model
    def _expire_date_cron(self):
        today_date = datetime.today()
        expire_records = self.search([
            ('status', 'in', ('draft', 'to_approve')),
            ('expiry_date', '<', today_date)
        ])
        template_id = self.env.ref(
            'equip3_inventory_operation.email_template_expired_material_request')
        for record in expire_records:
            record.write({'status': 'cancel'})
            record.send_email_notification(
                template_id, 'equip3_inventory_operation.email_template_expired_material_request', record.create_uid)

    @api.model
    def _expire_date_reminder_cron(self):
        today_date = date.today() + timedelta(days=1)
        expire_records = self.search([
            ('status', 'in', ('draft', 'to_approve'))
        ])
        user_reminder_template = self.env.ref(
            'equip3_inventory_operation.email_template_expired_material_request_reminder_user')
        approver_user_template = self.env.ref(
            'equip3_inventory_operation.email_template_expired_material_request_reminder_approved_user')
        for record in expire_records:
            if record.expiry_date == today_date:
                record.send_email_notification(
                    user_reminder_template, 'equip3_inventory_operation.email_template_expired_material_request_reminder_user', record.create_uid)
                matrix_line = sorted(record.approved_matrix_ids.filtered(
                    lambda r: not r.approved), key=lambda r: r.sequence)
                if record.is_material_request_approval_matrix and matrix_line:
                    matrix_line = matrix_line[0]
                    approver_user = False
                    for user in matrix_line.user_ids:
                        if user.id in matrix_line.user_ids.ids and \
                                user.id not in matrix_line.approved_users.ids:
                            approver_user = user
                            break
                    record.send_email_notification(
                        approver_user_template, 'equip3_inventory_operation.email_template_expired_material_request_reminder_approved_user', approver_user)

    def send_email_notification(self, template_id, template_name, user_id):
        self.ensure_one()

        record = self
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        url = base_url + '/web#id=' + \
            str(record.id) + '&view_type=form&model=material.request'
        ctx = {
            'email_from': self.env.user.company_id.email,
            'email_to': user_id.partner_id.email,
            'user_name': user_id.name,
            'url': url,
        }
        template_id.with_context(ctx).send_mail(record.id, True)
        template_id = self.env["ir.model.data"].xmlid_to_object(template_name)

        body_html = self.env['mail.render.mixin'].with_context(ctx)._render_template(
            template_id.body_html, 'material.request', record.ids, post_process=True)[record.id]
        message_id = self.env["mail.message"].sudo().create({
            "subject": "Material Request Expiry",
            "body": body_html,
            "model": "material.request",
            "res_id": record.id,
            "message_type": "notification",
            "partner_ids": [(6, 0, user_id.partner_id.ids)],
        })
        notif_create_values = {
            "mail_message_id": message_id.id,
            "res_partner_id": user_id.partner_id.id,
            "notification_type": "inbox",
            "notification_status": "sent",
        }
        return self.env["mail.notification"].sudo().create(notif_create_values)

    def _get_is_show_draft(self):
        for record in self:
            not_approved_lines = record.approved_matrix_ids.filtered(
                lambda r: not r.approved_users)
            if record.is_material_request_approval_matrix and \
                    record.status == 'to_approve' and \
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

    @api.depends('mr_approval_matrix_id')
    def _compute_approving_matrix_lines_mr(self):
        data = [(5, 0, 0)]
        for record in self:
            counter = 1
            record.approved_matrix_ids = []
            for line in record.mr_approval_matrix_id.mr_approval_matrix_line_ids:
                data.append((0, 0, {
                    'sequence': counter,
                    'user_ids': [(6, 0, line.user_ids.ids)],
                    'minimum_approver': line.minimum_approver,
                }))
                counter += 1
            record.approved_matrix_ids = data

    def mr_request_for_approving(self):
        for record in self:
            values = {
                'sender': self.env.user,
                'name': 'Material Requests',
                'no': record.name,
                'datetime': fields.Datetime.now(),
                'action_xmlid': 'equip3_inventory_operation.material_request_action',
                'menu_xmlid': 'equip3_inventory_operation.material_request_menu'
            }

            for approver in record.approved_matrix_ids.mapped('user_ids'):
                values.update({'receiver': approver})
                qiscus_request(record, values)
            record.write({'status': 'to_approve'})
        return True

    def mr_approving(self):
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
                record.write({'status': 'approved'})
        return True

    def mr_reject(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'material.request.matrix.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def mr_reset_to_draft(self):
        for record in self:
            record.write({'status': 'draft'})
            record.approved_matrix_ids.write({
                'state_char': False,
                'approved_users': [(6, 0, [])],
                'approved': False,
                "feedback": False,
                'time_stamp': False,
                'last_approved': False,
            })
        return True

    def mr_cancel(self):
        self.ensure_one()

        purchase_request_ids = self.env['purchase.request'].search(
            [('mr_id', '=', self.id)])
        internal_transfer_ids = self.env['internal.transfer'].search(
            [('mr_id', '=', self.id)])

        for records in purchase_request_ids, internal_transfer_ids:
            not_in_draft = records.filtered(
                lambda x: x.state not in ['draft', 'cancel'])
            if not not_in_draft:
                self.write({'status': 'cancel'})
                records.filtered(lambda x: x.state == 'draft').unlink()
            else:
                raise ValidationError(
                    f"The operation cannot be cancelled because the following document already processed.")
        return True

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('material.request')
        return super(MaterialRequest, self).create(vals)

    @api.depends('product_line')
    def _compute_check_product(self):
        for record in self:
            if record.product_line:
                record.check_product = True
            else:
                record.check_product = False

    @api.onchange('schedule_date')
    def compute_expiry_date(self):
        for record in self:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            mr_expiry_days = IrConfigParam.get_param(
                'mr_expiry_days', 'before')
            material_request = IrConfigParam.get_param('material_request', 0)
            if record.schedule_date:
                if mr_expiry_days == 'before':
                    record.expiry_date = record.schedule_date - \
                        timedelta(days=int(material_request))
                else:
                    record.expiry_date = record.schedule_date + \
                        timedelta(days=int(material_request))

    def _compute_pr_count(self):
        for obj in self:
            count = self.env['purchase.request'].search_count(
                [('mr_id', 'in', obj.ids)])
            obj.update({
                'pr_count': count,
                'purchase_request': count
            })

    def _compute_ir_count(self):
        for obj in self:
            count = self.env['internal.transfer'].search_count(
                [('mr_id', '=', obj.id)])
            obj.update({
                'ir_count': count,
                'internal_transfer': count
            })

    def _compute_itr_war_count(self):
        for record in self:
            record.itr_war_count = self.env['stock.picking'].search_count(
                [('mr_id', '=', record.id)])

    def button_confirm(self):
        for record in self:
            for line in record.product_line:
                if line.quantity <= 0:
                    raise ValidationError(
                        "You Can Not Confirm Without Product Quantity Or Zero Quantity Of Product")
            record.write({'status': 'confirm'})
        return True


    def create_purchase_request(self):
        self.ensure_one()

        context = self.env.context.copy()
        pr_line = []
        count = 1
        for line in self.product_line:
            qty = line.quantity - line.done_qty
            if qty < 0:
                qty = 0
            vals = {
                'no': count,
                'mr_id': self.id,
                'mr_line_id': line.id,
                'product_id': line.product.id,
                'description': line.product.product_display_name,
                'uom_id': line.product_unit_measure.id,
                'qty_purchase': qty,
                'request_date': line.request_date,
            }
            pr_line.append((0, 0, vals))
            count += count
        context.update({'default_pr_wizard_line': pr_line})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Purchase Request',
            'res_model': 'purchase.request.wizard',
            'view_id': self.env.ref('equip3_inventory_operation.purchase_request_wizard_form_view').id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def create_intrawarehouse_transfer(self):
        self.ensure_one()

        context = dict(self.env.context) or {}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Intrawarehouse Transfer',
            'res_model': 'intrawarehouse.transfer',
            'view_id': self.env.ref('equip3_inventory_operation.intrawarehouse_transfer_from_view').id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def create_internal_transfer(self):
        self.ensure_one()

        context = self.env.context.copy()
        ir_line = []
        count = 1
        for line in self.product_line:
            qty = line.quantity - line.done_qty
            if qty < 0:
                qty = 0
            vals = {
                'no': count,
                'mr_id': self.id,
                'mr_line_id': line.id,
                'product_id': line.product.id,
                'description': line.product.description,
                'uom_id': line.product.uom_id.id,
                'qty_transfer': qty,
            }
            ir_line.append((0, 0, vals))
            count = count+1
        context.update({
            'default_ir_wizard_line': ir_line,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Interwarehouse Transfer',
            'res_model': 'mr.internal_transfer',
            'view_id': self.env.ref('equip3_inventory_operation.internal_transfer_wizard_form_view').id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def material_request_done(self):
        self.ensure_one()

        show_popup = False
        for line in self.product_line:
            if line.quantity > line.done_qty:
                show_popup = True
        if show_popup:
            return {
                'name': 'Warning',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'show.material.done.popup',
                'view_type': 'form',
                'target': 'new'
            }
        else:
            self.write({'status': 'done'})

        return True

    def get_purchase_request_line(self):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id(
            "purchase_request.purchase_request_form_action")
        action['views'] = [
            (self.env.ref('purchase_request.view_purchase_request_tree').id, 'tree'),
            (self.env.ref('purchase_request.view_purchase_request_form').id, 'form')
        ]
        action['context'] = self.env.context

        pr_list = self.env['purchase.request'].search(
            [('mr_id', '=', self.id)]).ids
        action['domain'] = [('id', 'in', pr_list)]
        return action

    def get_internal_transfer(self):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id(
            "equip3_inventory_operation.action_internal_transfer_request")
        action['views'] = [
            (self.env.ref('equip3_inventory_operation.view_tree_internal_transfer').id, 'tree'),
            (self.env.ref('equip3_inventory_operation.view_form_internal_transfer').id, 'form')
        ]
        action['context'] = self.env.context

        ir_lines = self.env['internal.transfer'].search(
            [('mr_id', '=', self.ids)]).ids
        action['domain'] = [('id', 'in', ir_lines)]
        return action

    def get_intra_warehouse_transfer(self):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id(
            "equip3_inventory_operation.action_interwarehouse_transfer")
        action['views'] = [
            (self.env.ref(
                'equip3_inventory_operation.view_tree_stock_picking_internal_warehouse').id, 'tree'),
            (self.env.ref(
                'equip3_inventory_operation.view_form_stock_picking_internal_warehouse').id, 'form')
        ]
        action['context'] = self.env.context

        action['domain'] = [('mr_id', '=', self.id)]
        return action

    @api.constrains('product_line')
    def _check_product_dup(self):
        for record in self:
            products = []
            for product in record.product_line:
                if product.product.id not in products:
                    products.append(product.product.id)
                else:
                    raise ValidationError(
                        "Product %s already exist" % product.product.name)


    def get_selection_label(self, field_name, field_value):
        field = self._fields.get(field_name)
        if field and field.type == 'selection':
            selection_dict = dict(self._fields[field_name].selection)
            label = selection_dict.get(field_value)
        return label

    def unlink(self):
        for record in self:
            if record.status in ('confirm', 'done'):
                state_label = record.get_selection_label('status', record.status)
                if state_label:
                    raise ValidationError(f'You can not delete material request in {state_label.lower()} status')
        return super(MaterialRequest, self).unlink()

    def _check_processed_record(self, material_request_id, origin_id=None):
        """
        Check if any related documents to a material request are already processed.
        Args:
            material_request_id (int): The ID of the material request being checked.
            origin_id (int, optional): The ID of the record considered as the origin.
            Defaults to None.
            the origin_id can only be from the following models and not from Transient models:
                - Purchase Request (purchase.request)
                - Internal Transfer (internal.transfer)
                - Inter-Location Transfer (stock.picking)
        """
        record_models = [
            ('purchase.request', 'Purchase Request', ['state', 'purchase_req_state']),
            ('internal.transfer', 'Interwarehouse Transfer Request', ['state']),
            ('stock.picking', 'Inter-Location Transfer', ['state']),
        ]

        for model, model_name, fields in record_models:
            domain = [('mr_id', '=', material_request_id)]
            if origin_id:
                domain.append(('id', '!=', origin_id))
            records = self.env[model].search(domain)
            if any(all(getattr(record, field) not in ['draft', 'cancel', 'done'] for field in fields) for record in records):
                raise ValidationError(f"You cannot continue, another document is already processed.")

        return True


class MaterialRequestLine(models.Model):
    _name = 'material.request.line'
    _description = "Material Request Line"
    _rec_name = 'product'
    _order = 'sequence'

    @api.model
    def default_get(self, fields):
        res = super(MaterialRequestLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'product_line' in context_keys:
                if len(self._context.get('product_line')) > 0:
                    next_sequence = len(self._context.get('product_line')) + 1
            res.update({'no': next_sequence})
        return res

    material_request_id = fields.Many2one('material.request')
    sequence = fields.Integer(string="Sequence")
    no = fields.Integer('No')
    product = fields.Many2one('product.product', 'Product', required='1')
    description = fields.Text('Description')
    quantity = fields.Float('Quantity', default="1")
    product_unit_measure = fields.Many2one(
        'uom.uom', 'Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(
        related='product.uom_id.category_id')
    destination_location_id = fields.Many2one(
        'stock.location', 'Destination Location')
    destination_warehouse_id = fields.Many2one(
        'stock.warehouse', 'Destination Warehouse')
    status = fields.Selection(related="material_request_id.status", readonly='1')
    request_date = fields.Date(
        'Request Date', required='1', related='material_request_id.schedule_date')
    done_qty_dup = fields.Float("Done Quantity Duplicate", compute='_compute_done_qty')
    done_qty = fields.Float("Done Quantity")
    requested_qty = fields.Float("Requested Quantity")
    remaining_qty = fields.Float("Remaining Quantity to Process")
    source_document = fields.Char('Source Document', readonly='1')
    requested_by = fields.Many2one(
        'res.users', 'Requested By', related="material_request_id.requested_by", readonly='1')
    company_id = fields.Many2one(
        'res.company', related="material_request_id.company_id", string='Company', readonly='1')
    branch_id = fields.Many2one('res.branch', 'Branch', readonly='1')
    create_date = fields.Datetime('Created On', readonly='1')
    pr_requested_qty = fields.Float(
        'PR Requested Quantity', compute='_compute_pr_requested_qty')
    pr_pending_qty_to_receive = fields.Float(
        'PR Pending Quantity to Receive ', compute='_compute_pr_pending_qty_to_receive')
    pr_in_progress_qty = fields.Float(
        'PR In Progress Quantity', compute='_compute_pr_in_progress_qty')
    pr_done_qty = fields.Float('PR Done Quantity', compute='_compute_pr_done_qty')
    pr_cancelled_qty = fields.Float(
        'PR Cancelled Quantity', compute='_compute_pr_cancelled_qty')
    itr_requested_qty = fields.Float(
        'ITR Requested Quantity', compute='_compute_itr_requested_qty')
    itr_in_progress_qty = fields.Float(
        'ITR In Progress Quantity', compute='_compute_itr_in_progress_qty')
    itr_done_qty = fields.Float(
        'ITR Done Quantity', compute='_compute_itr_done_qty')
    itr_returned_qty = fields.Float(
        'ITR Returned Quantity', compute='_compute_itr_returned_qty')
    pr_lines_ids = fields.One2many('purchase.request.line', 'mr_line_id')
    ir_lines_ids = fields.One2many('internal.transfer.line', 'mr_line_id')
    itr_war_lines_ids = fields.One2many('stock.move', 'mr_line_id')
    analytic_account_group_ids = fields.Many2many(
        related='material_request_id.analytic_account_group_ids', string="Analytic Groups")
    progress_quantity = fields.Float(
        string="In Progress Quantity", compute="_compute_progress_quantity")
    pr_remaining_qty = fields.Float(
        string="PR Remaining Quantity", compute="_compute_remaining_qty_pr")
    itr_remaining_qty = fields.Float(
        string="ITR Remaining Quantity", compute="_compute_remaining_qty_itr")
    itw_requested_qty = fields.Float(
        'ITW Requested Quantity', compute='_compute_itw_requested_qty')
    itw_in_progress_qty = fields.Float(
        'ITW In Progress Quantity', compute='_compute_itw_in_progress_qty')
    itw_remaining_qty = fields.Float(
        string="ITW Remaining Quantity", compute="_compute_remaining_qty_itw")
    itw_done_qty = fields.Float(
        'ITW Done Quantity', compute='_compute_itw_done_qty')

    def action_show_stock(self):
        self.ensure_one()

        context = dict(self.env.context) or {}
        product_obj = self.env["product.product"].browse(self.product.id)
        product_line_data = []
        product_stock_location = self.env["stock.quant"].search([("product_id", "=", self.product.id),
                                                                 ("location_id.usage", "=", "internal")]).mapped("location_id")
        for location in product_stock_location:
            res = product_obj.with_context(location=location.id)._compute_quantities_dict(
                False,  # lot_id
                False,  # owner_id
                False,  # package_id
            )
            product_line = {
                "product_id": product_obj.id,
                "location_id": location.id,
                "warehouse_id": location.get_warehouse().id,
                "quantity": res[product_obj.id]['qty_available'],
                "available_quantity": res[product_obj.id]['free_qty'],
                "forecast_incoming": res[product_obj.id]['incoming_qty'],
                "forecast_outcoming": res[product_obj.id]['outgoing_qty'],
                "forecast_qty": res[product_obj.id]['virtual_available'],
            }
            product_line_data.append((0, 0, product_line))

        context.update({
            'default_stock_quant_line_ids': product_line_data
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Availability',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_inventory_operation.view_tree_stock_quant_show_stock').id,
            'res_model': 'material.request.show.stock',
            'target': 'new',
            'context': context
        }

    def _compute_remaining_qty_pr(self):
        for record in self:
            record.pr_remaining_qty = abs(
                record.pr_requested_qty - record.pr_in_progress_qty - record.pr_done_qty)

    def _compute_remaining_qty_itr(self):
        for record in self:
            record.itr_remaining_qty = abs(
                record.itr_requested_qty - record.itr_in_progress_qty - record.itr_done_qty)

    def _compute_remaining_qty_itw(self):
        for record in self:
            record.itw_remaining_qty = abs(
                record.quantity - record.itw_requested_qty)

    @api.depends('pr_in_progress_qty', 'itr_in_progress_qty')
    def _compute_progress_quantity(self):
        for record in self:
            record.progress_quantity = record.pr_in_progress_qty + \
                record.itr_in_progress_qty + record.itw_in_progress_qty

    def _compute_itr_requested_qty(self):
        for record in self:
            if record.ir_lines_ids:
                for line in record.ir_lines_ids:
                    if line.status != 'cancel':
                        record.itr_requested_qty += line.qty
                    else:
                        record.itr_requested_qty += 0
            else:
                record.itr_requested_qty = 0

    def _compute_itw_requested_qty(self):
        for record in self:
            if record.itr_war_lines_ids:
                for line in record.itr_war_lines_ids:
                    if line.state != 'cancel':
                        record.itw_requested_qty += line.product_uom_qty
                    else:
                        record.itw_requested_qty += 0
            else:
                record.itw_requested_qty = 0

    # def _compute_itr_in_progress_qty(self):
    #     for record in self:
    #         transit_location = self.env.ref(
    #             'equip3_inventory_masterdata.location_transit')
    #         if record.ir_lines_ids:
    #             for line in record.ir_lines_ids:
    #                 if line.status != 'cancel':
    #                     for product_line in line.product_line:
    #                         stock_picking = record.env['stock.picking'].search(
    #                             [('transfer_id', '=', product_line.id)])
    #                         for picking in stock_picking:
    #                             if picking.location_id.id == transit_location.id and picking.origin == product_line.name and picking.location_dest_id == product_line.destination_location_id:
    #                                 for move in picking.move_ids_without_package:
    #                                     if move.state == 'done':
    #                                         record.itr_in_progress_qty += abs(
    #                                             line.qty - move.quantity_done)
    #                             if picking.location_id.id == product_line.source_location_id.id and picking.origin == product_line.name and picking.location_dest_id.id == product_line.destination_location_id.id:
    #                                 for move in picking.move_ids_without_package:
    #                                     if move.state == 'done':
    #                                         record.itr_in_progress_qty += abs(
    #                                             line.qty - move.quantity_done)
    #                 else:
    #                     record.itr_in_progress_qty += 0

    #         record.itr_in_progress_qty += 0
    
    # def _compute_itr_in_progress_qty(self):
    #     for record in self:
    #         record.itr_in_progress_qty = 0
    #         if record.ir_lines_ids:
    #             for itr in record.ir_lines_ids:
    #                 record.itr_in_progress_qty += itr.itr_in_progress_qty
    
    def _compute_itr_in_progress_qty(self):
        for record in self:
            record.itr_in_progress_qty = sum(itr.itr_in_progress_qty for itr in record.ir_lines_ids)

    def _compute_itw_in_progress_qty(self):
        for record in self:
            record.itw_in_progress_qty = 0
            if record.itr_war_lines_ids:
                for line in record.itr_war_lines_ids:
                    record.itw_in_progress_qty += line.reserved_availability

    def _compute_itr_done_qty(self):
        for record in self:
            if record.ir_lines_ids:
                for line in record.ir_lines_ids:
                    record.itr_done_qty += line.transfer_qty
            else:
                record.itr_done_qty += 0

    def _compute_itw_done_qty(self):
        for record in self:
            if record.itr_war_lines_ids:
                for line in record.itr_war_lines_ids:
                    record.itw_done_qty += line.quantity_done
            else:
                record.itw_done_qty += 0

    def _compute_itr_returned_qty(self):
        for record in self:
            transit_location = self.env.ref(
                'equip3_inventory_masterdata.location_transit')
            if record.ir_lines_ids:
                for line in record.ir_lines_ids:
                    if line.status != 'cancel':
                        for product_line in line.product_line:
                            stock_picking = record.env['stock.picking'].search(
                                [('transfer_id', '=', product_line.id)])
                            for picking in stock_picking:
                                if picking.location_id.id == transit_location.id and 'Return' in picking.origin and picking.location_dest_id == product_line.source_location_id:
                                    for move in picking.move_ids_without_package:
                                        if move.state == 'done':
                                            record.itr_returned_qty += move.quantity_done
                                if picking.location_id.id == product_line.destination_location_id.id and 'Return' in picking.origin and picking.location_dest_id.id == product_line.source_location_id.id:
                                    for move in picking.move_ids_without_package:
                                        if move.state == 'done':
                                            record.itr_returned_qty += move.quantity_done
                    else:
                        record.itr_returned_qty += 0

            record.itr_returned_qty += 0

    def _compute_pr_requested_qty(self):
        for record in self:
            if record.pr_lines_ids:
                for line in record.pr_lines_ids:
                    record.pr_requested_qty += line.product_qty
            else:
                record.pr_requested_qty += 0

    def _compute_pr_pending_qty_to_receive(self):
        for record in self:
            if record.pr_lines_ids:
                for line in record.pr_lines_ids:
                    record.pr_pending_qty_to_receive += line.pending_qty_to_receive
            else:
                record.pr_pending_qty_to_receive += 0

    def _compute_pr_in_progress_qty(self):
        for record in self:
            if record.pr_lines_ids:
                for line in record.pr_lines_ids:
                    record.pr_in_progress_qty += line.qty_in_progress
            else:
                record.pr_in_progress_qty += 0

    def _compute_pr_done_qty(self):
        for record in self:
            if record.pr_lines_ids:
                for line in record.pr_lines_ids:
                    record.pr_done_qty += line.qty_done
            else:
                record.pr_done_qty += 0

    def _compute_pr_cancelled_qty(self):
        for record in self:
            if record.pr_lines_ids:
                for line in record.pr_lines_ids:
                    record.pr_cancelled_qty += line.qty_cancelled
            else:
                record.pr_cancelled_qty += 0

    def _compute_done_qty(self):
        for record in self:
            pr_done_qty = 0
            itr_done_qty = 0
            itw_done_qty = 0
            if record.pr_lines_ids:
                for line in record.pr_lines_ids:
                    pr_done_qty += line.qty_done
            if record.ir_lines_ids:
                for line in record.ir_lines_ids:
                    itr_done_qty += line.transfer_qty
            if record.itr_war_lines_ids:
                for line in record.itr_war_lines_ids:
                    itw_done_qty += line.quantity_done
            record.done_qty = pr_done_qty + itr_done_qty + itw_done_qty
            record.done_qty_dup = pr_done_qty + itr_done_qty
            record.done_qty_dup = 0
            record.requested_qty = record.quantity
            record.remaining_qty = abs(
                record.pr_remaining_qty + record.itr_remaining_qty + record.itw_remaining_qty)

    @api.onchange('product')
    def _get_uom(self):
        self.product_unit_measure = self.product.uom_id.id
        self.description = self.product.name

    @api.constrains('product')
    def _check_product_type(self):
        for record in self:
            if record.product.type == 'service':
                raise ValidationError(
                    'user can’t add a product which type is service in material requests')
