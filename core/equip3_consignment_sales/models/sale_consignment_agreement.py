from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.osv import expression
from odoo.exceptions import Warning


def _domain_analytic_group(self):
    user = self.env.user
    analytic_priority = self.env['analytic.priority'].sudo().search(
        [], limit=1, order='priority')
    active_company = self.env.company

    if analytic_priority.object_id == 'user':
        analytic_tag_ids = user.analytic_tag_ids.filtered(
            lambda p: p.company_id == active_company).ids
    elif analytic_priority.object_id == 'branch' and user.branch_id:
        analytic_tag_ids = user.branch_id.analytic_tag_ids.filtered(
            lambda p: p.company_id == active_company).ids
    elif analytic_priority.object_id == 'product_category':
        product_category = self.env['product.category'].sudo().search(
            [('analytic_tag_ids', '!=', False)], limit=1)
        analytic_tag_ids = product_category.analytic_tag_ids.ids
    else:
        analytic_tag_ids = []
    return [('id', 'in', analytic_tag_ids)]


class SaleConsignmentAgreement(models.Model):
    _name = 'sale.consignment.agreement'
    _inherit = ['mail.thread']
    _description = "Consignment Agreement"
    _rec_name = 'reference_number'
    _order = 'id desc'

    @api.model
    def _default_analytic_tag_ids(self):
        user = self.env.user
        analytic_priority = self.env['analytic.priority'].sudo().search(
            [], limit=1, order='priority')
        analytic_tag_ids = []
        active_company = self.env.company

        if analytic_priority.object_id == 'user' and user.analytic_tag_ids:
            analytic_tag_ids = user.analytic_tag_ids.filtered(
                lambda p: p.company_id == active_company).ids
        elif analytic_priority.object_id == 'branch' and user.branch_id and user.branch_id.analytic_tag_ids:
            analytic_tag_ids = user.branch_id.analytic_tag_ids.filtered(
                lambda p: p.company_id == active_company).ids
        elif analytic_priority.object_id == 'product_category':
            product_category = self.env['product.category'].sudo().search(
                [('analytic_tag_ids', '!=', False)], limit=1)
            analytic_tag_ids = product_category.analytic_tag_ids.ids
        return [(6, 0, analytic_tag_ids)]

    # @api.model
    # def _default_branch(self):
    #     default_branch_id = self.env.context.get('default_branch_id', False)
    #     if default_branch_id:
    #         return default_branch_id
    #     return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False

    # @api.model
    # def _domain_branch(self):
    #     return [('id', 'in', self.env.branches.ids), ('company_id', '=', self.env.company.id)]

    def _domain_partner_id(self):
        return expression.AND([
            [('is_a_consign', '=', True), ('company_id', '=', self.env.company.id)]
        ])

    # branch_id = fields.Many2one(
    #     'res.branch',
    #     check_company=True,
    #     domain=_domain_branch,
    #     default=_default_branch,
    #     readonly=False)
    reference_number = fields.Char("Reference Number", default="New")
    title = fields.Char("Agreement Name", required=True)
    customer_id = fields.Many2one(
        'res.partner', 'Customer', required=True, domain=_domain_partner_id)
    account_tag_ids = fields.Many2many('account.analytic.tag', domain=_domain_analytic_group,
                                       string="Analytic Group", default=_default_analytic_tag_ids)
    destination_warehouse_id = fields.Many2one(
        'stock.location', string='Destination', domain="[('company_id', '=', company_id)]", required=True)
    start_date = fields.Date(
        'Agreement Start Date', required=True, default=datetime.today())
    end_date = fields.Date('Agreement End Date', required=True)
    # branch_id = fields.Many2one('res.branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, default=lambda self: self.env.company)
    created_by = fields.Many2one(
        'res.users', string='Create By', default=lambda self: self.env.user, required=True)
    created_date = fields.Datetime(
        string='Create Date', readonly=True, default=datetime.today())
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', required=True)
    terms_and_conditions = fields.Html(
        string="Terms & Conditions", tracking=True)
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Closed'),
        ('close', 'Closed'),
        ('cancel', 'Canceled')
    ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    consignment_line_ids = fields.One2many(
        'sale.consignment.agreement.line', 'consignment_id', string="Consignment Line", copy=True)
    internal_transfer_count = fields.Integer(
        compute='_compute_internal_transfer_count')
    internal_transfer_back_count = fields.Integer(
        compute='_compute_internal_transfer_back_count')
    consignment_sale_count = fields.Integer(
        compute='_compute_consignment_sale_count')
    consignment_order_ids = fields.One2many(
        'sale.order', 'sale_consignment_id', string="Consignment Orders")
    is_group_analytic_tags = fields.Boolean("Is Analytic Group",
        compute="_compute_is_group_analytic_tags",
        default=lambda self: bool(self.env['ir.config_parameter'].sudo().get_param('group_analytic_tags', False)))

    def _compute_is_group_analytic_tags(self):
        for rec in self:
            rec.is_group_analytic_tags = bool(self.env['ir.config_parameter'].sudo().get_param('group_analytic_tags', False))

    @api.onchange('customer_id')
    def set_destination_warehouse_id(self):
        for rec in self:
            if rec.customer_id:
                rec.destination_warehouse_id = rec.customer_id.sale_consignment_location_id.id or False

    @api.model
    def create(self, vals):
        vals['reference_number'] = self.env['ir.sequence'].next_by_code(
            'sequence.sale.consignment.agreement')
        res = super().create(vals)
        return res

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.consignment_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def confirm_consignment(self):
        for rec in self:
            rec.state = 'confirmed'

    def close_consignment(self):
        for rec in self:
            total_current_qty = sum(line.current_qty for line in rec.consignment_line_ids)
            if total_current_qty > 0:
                raise Warning(_("Please transfer back all the products to continue this process"))
            rec.state = 'close'

    def cancel_consignment(self):
        for rec in self:
            rec.state = 'cancel'

    def button_transfer_request(self):
        now = datetime.now()
        location = self.customer_id.sale_consignment_location_id
        warehouse_id = location.warehouse_id

        ctx = {
            'default_sale_consignment_id': self.id,
            'default_scheduled_date': now,
            'default_destination_warehouse_id': warehouse_id.id,
            'default_destination_location_id': location.id,
            'default_product_line_ids': [(0, 0, {
                'product_consignment_id': self.env['product.product'].search([('product_tmpl_id', '=', line.product_id.id)], limit=1).id,
                'product_id': self.env['product.product'].search([('product_tmpl_id', '=', line.product_id.id)], limit=1).id,
                'description': line.product_description,
                'uom': line.product_uom_id.id,
                'qty': line.product_transferred_qty,
                'analytic_account_group_ids': [(6, 0, line.account_tag_ids.ids)],
            }) for line in self.consignment_line_ids]
        }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Transfer Request',
            'res_model': 'internal.transfer',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_consignment_sales.view_form_internal_transfer_consignment_sale').id,
            'target': 'current',
            'context': ctx
        }

    def button_create_orders(self):
        now = datetime.now()

        default_order_lines = []
        for line in self.consignment_line_ids.filtered(lambda line: line.current_qty > 0):
            product_id = self.env['product.product'].search(
                [('product_tmpl_id', '=', line.product_id.id)], limit=1).id
            order_line = (0, 0, {
                'product_id': product_id,
                'name': line.product_description,
                'product_uom': line.product_uom_id.id,
                'product_uom_qty': line.product_transferred_qty,
                'price_unit': line.product_unit_price,
                'location_id': self.customer_id.sale_consignment_location_id.id,
                'line_warehouse_id': self.destination_warehouse_id.warehouse_id.id,
                'line_warehouse_id_new': self.destination_warehouse_id.warehouse_id.id,
                'multiple_do_date_new': now,
                'multiple_do_date': now,
                'account_tag_ids': [(6, 0, line.account_tag_ids.ids)],
            })
            default_order_lines.append(order_line)

        ctx = {
            'sale_consignment_id': self.id,
            'partner_id': self.customer_id.id,
            'pricelist_id': self.pricelist_id.id,
            'pricelist_id': self.pricelist_id.id,
            'currency_id': self.pricelist_id.currency_id.id,
            'warehouse_id': self.destination_warehouse_id.warehouse_id.id,
            'warehouse_new_id': self.destination_warehouse_id.warehouse_id.id,
            'validity_date': now,
            'account_tag_ids': [(6, 0, self.account_tag_ids.ids)],
            'sale_consign': True,
            'order_line': default_order_lines,
        }
        sale_id = self.env['sale.order'].create(ctx)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Consignment Quotation',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': sale_id.id,
            'views': [(self.env.ref('equip3_consignment_sales.sale_order_consignment_form').id, 'form')],
        }

    def _compute_internal_transfer_count(self):
        self.internal_transfer_count = self.env['internal.transfer'].search_count(
            [('sale_consignment_id', '=', self.id), ('is_transfer_back_consignment', '=', False)])

    def _compute_internal_transfer_back_count(self):
        self.internal_transfer_back_count = self.env['internal.transfer'].search_count(
            [('sale_consignment_id', '=', self.id), ('is_transfer_back_consignment', '=', True)])

    def _compute_consignment_sale_count(self):
        self.consignment_sale_count = self.env['sale.order'].search_count(
            [('sale_consignment_id', '=', self.id)])

    def view_internal_transfer(self):
        internal_transfer_ids = self.env['internal.transfer'].search(
            [('sale_consignment_id', '=', self.id)])
        form_view = self.env.ref(
            'equip3_consignment_sales.view_form_internal_transfer_consignment_sale')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Internal Transfer',
            'res_model': 'internal.transfer',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'target': 'current',
            'views': [[False, 'list'], [form_view.id, 'form']],
            'domain': [('id', 'in', internal_transfer_ids.ids)]
        }

    def view_internal_transfer_back(self):
        internal_transfer_ids = self.env['internal.transfer'].search(
            [('sale_consignment_id', '=', self.id), ('is_transfer_back_consignment', '=', True)])
        form_view = self.env.ref(
            'equip3_consignment_sales.view_form_internal_transfer_consignment_sale')

        return {
            'type': 'ir.actions.act_window',
            'name': 'Internal Transfer',
            'res_model': 'internal.transfer',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'target': 'current',
            'views': [[False, 'list'], [form_view.id, 'form']],
            'domain': [('id', 'in', internal_transfer_ids.ids)]
        }

    def view_consignment_order(self):
        sale_order_ids = self.env['sale.order'].search(
            [('sale_consignment_id', '=', self.id)])
        form_view = self.env.ref(
            'equip3_consignment_sales.sale_order_consignment_form', raise_if_not_found=False)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Consignment Order',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [[False, 'list'], [form_view.id, 'form']],
            'domain': [('id', 'in', sale_order_ids.ids)],
        }

    def button_transfer_back(self):
        current_qty = sum(self.consignment_line_ids.mapped('current_qty'))
        if current_qty <= 0:
            raise Warning("There is no stock left on this agreement")
        else:
            now = datetime.now()
            location = self.destination_warehouse_id
            warehouse_id = location.warehouse_id

            ctx = {
                'default_sale_consignment_id': self.id,
                'default_scheduled_date': now,
                'default_source_warehouse_id': warehouse_id.id,
                'default_source_location_id': location.id,
                'default_is_transfer_back_consignment': 1,
                'default_product_line_ids': [(0, 0, {
                    'sequence': line.res_sequence,
                    'product_id': self.env['product.product'].search([('product_tmpl_id', '=', line.product_id.id)], limit=1).id,
                    'product_consignment_id': self.env['product.product'].search([('product_tmpl_id', '=', line.product_id.id)], limit=1).id,
                    'description': line.product_description,
                    'uom': line.product_uom_id.id,
                    'qty': line.current_qty,
                    'current_qty': line.current_qty,
                    'analytic_account_group_ids': [(6, 0, line.account_tag_ids.ids)],
                }) for line in self.consignment_line_ids if line.current_qty > 0]
            }

            return {
                'type': 'ir.actions.act_window',
                'name': 'Transfer Request',
                'res_model': 'internal.transfer',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('equip3_consignment_sales.view_form_internal_transfer_consignment_sale').id,
                'target': 'current',
                'context': ctx
            }


class SaleConsignmentAgreementLine(models.Model):
    _name = 'sale.consignment.agreement.line'

    consignment_id = fields.Many2one(
        'sale.consignment.agreement', string="Consignment")
    company_id = fields.Many2one(related='consignment_id.company_id')
    sequence = fields.Char(string='No')
    res_sequence = fields.Integer(string='No')
    product_id = fields.Many2one('product.template', string="Product")
    product_description = fields.Text(string='Description', tracking=True)
    product_uom_category_id = fields.Many2one(
        'uom.category', related='product_id.uom_id.category_id')
    product_uom_id = fields.Many2one(
        'uom.uom', string='UoM', domain="[('category_id', '=', product_uom_category_id)]")
    product_unit_price = fields.Float(string='Unit Price')
    product_transferred_qty = fields.Float("Transferred", copy=False)
    product_invoiced_qty = fields.Float("Invoiced", compute='_compute_amount')
    product_sold_qty = fields.Float("Sold", compute='_compute_amount')
    product_paid_qty = fields.Float("Paid", compute='_compute_amount')
    account_tag_ids = fields.Many2many(
        'account.analytic.tag', domain=_domain_analytic_group, string="Analytic Group")
    # current_qty = fields.Float(
    #     string="Current Quantity", readonly=True, compute='compute_current_qty')
    current_qty = fields.Float(
        string="Current Quantity", readonly=True, copy=False)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 0
            if 'consignment_line_ids' in context_keys:
                next_sequence = len(self._context.get(
                    'consignment_line_ids')) + 1
            res.update({'sequence': next_sequence,
                       'res_sequence': next_sequence})
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.consignment_id._reset_sequence()
        return res

    @api.onchange('sequence')
    def _default_analytic_tag_ids(self):
        for rec in self:
            if rec.consignment_id.account_tag_ids:
                rec.account_tag_ids = rec.consignment_id.account_tag_ids.ids
            else:
                rec.account_tag_ids = False

    @api.onchange('sequence')
    def set_sequence_line(self):
        for record in self:
            record.consignment_id._reset_sequence()

    def unlink(self):
        consignment_id = self.consignment_id
        res = super().unlink()
        consignment_id._reset_sequence()
        return res

    @api.onchange('product_id')
    def change_product_line(self):
        for rec in self:
            if rec.product_id:
                rec.product_uom_id = rec.product_id.uom_id.id
                rec.product_unit_price = rec.product_id.list_price
                rec.product_description = rec.product_id.name

    @api.depends('consignment_id.consignment_order_ids')
    def _compute_amount(self):
        for record in self:
            consignment_orders = record.consignment_id.consignment_order_ids
            invoices = consignment_orders.mapped('order_line.invoice_lines')

            product_sold_qty = sum(so_line.product_uom_qty for sale_order in consignment_orders if sale_order.state in (
                'sale', 'done') for so_line in sale_order.order_line if so_line.product_id.product_tmpl_id.id == record.product_id.id)
            product_invoiced_qty = sum(
                invoice_line.quantity for invoice_line in invoices if invoice_line.product_id.product_tmpl_id.id == record.product_id.id)
            paid_invoices = invoices.filtered(
                lambda r: r.move_id.payment_state == 'paid')
            product_paid_qty = sum(
                invoice_line.quantity for invoice_line in paid_invoices if invoice_line.product_id.product_tmpl_id.id == record.product_id.id)

            record.write({
                'product_sold_qty': product_sold_qty,
                'product_invoiced_qty': product_invoiced_qty,
                'product_paid_qty': product_paid_qty
            })

    # @api.depends('product_transferred_qty', 'product_sold_qty')
    # def compute_current_qty(self):
    #     for record in self:
    #         record.current_qty = record.product_transferred_qty - record.product_sold_qty if record.product_transferred_qty else 0
