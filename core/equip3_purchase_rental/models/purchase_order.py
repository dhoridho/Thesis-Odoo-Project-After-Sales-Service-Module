
from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    is_rent_duration = fields.Boolean(string='Rent Duration', default=True)
    rent_duration = fields.Integer(string='Rent Duration')
    rent_duration_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
    ],string="Single Rent Duration")
    expected_return_date = fields.Date(string="Expected Return Date", compute="_compute_expected_return_date", store=True)
    is_rental_orders = fields.Boolean(string="Rental Orders", default=False)
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_delivery')
    subcon_picking_ids = fields.Many2many('stock.picking', relation='purchase_picking_subcon_ids', string='Subcontracting Delivery Orders')
    procurement_group = fields.Many2one('procurement.group', string="Procurement Group",copy=False)
    is_extend_id = fields.Many2one('purchase.order', 'Purchase Extend')
    history_extend_ids = fields.One2many('history.extend.rental', 'po_id', string="Extend History")

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for i in self:
            if i.state1 in ['purchase']:
                if i.is_rental_orders:
                    i.name = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rental') or _('New')
            if i.is_extend_id:
                po_id = self.env['purchase.order'].search([('name','=',i.origin)])
                if po_id:
                    do_ids = self.env['stock.picking'].search([('purchase_order_id', '=', po_id.id)]).filtered(lambda r: r.state not in ('done', 'cancel'))
                    if do_ids:
                        for do in do_ids:
                            do.scheduled_date = i.expected_return_date
        return res

    def wizard_extend_rental(self):
        context = dict(self.env.context) or {}
        val_ids = []
        for line in self.order_line:
            rental_line_id = self.env['extend.rental.line'].create({
                'product_id':line.product_template_id.id,
                'description':line.name,
                'rented_qty': line.product_qty,
                'extend_qty': 1,
                'unit_price': line.price_unit
            })
            val_ids.append(rental_line_id.id)
        context.update({
            'default_po_id': self.id,
            'default_old_date_planned': self.expected_return_date,
            'default_old_rent_duration': self.rent_duration,
            'default_old_rent_duration_unit': self.rent_duration_unit,
            'default_date_planned': self.expected_return_date + relativedelta(days=1),
            'default_rent_duration': 1,
            'default_rent_duration_unit': 'days',
            'default_line_ids': [(6,0,val_ids)]
        })
        return {
            'name': 'Rental Extension',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'extend.rental',
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
        }

    def write(self, vals):
        context = dict(self.env.context) or {}
        if 'state' in vals and vals['state'] == 'purchase':
            reference_formatting = self.env['ir.config_parameter'].sudo().get_param('reference_formatting')
            if not self.exp_po or (self.is_revision_po and self.origin.startswith('RFQ')):
                if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':
                    if self.is_rental_orders and not context.get('default_dp'):
                        vals['name2'] = context.get('name') or self.name
                        if reference_formatting == 'new' or not self.is_revision_po or self.origin.startswith('RFQ'):
                            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rental')
                    elif self.is_rental_orders and context.get('default_dp'):
                        vals['name'] = self.env['ir.sequence'].next_by_code('direct.purchase.seqs.r')
        return super(PurchaseOrder, self).write(vals)

    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        res = super(PurchaseOrder , self).create(vals)
        if context.get('rentals_orders') or res.is_rental_orders:
            name = self.env['ir.sequence'].next_by_code('purchase.order.seqs.r')
            res.write({
                'name': name,
                'is_rental_orders': True,
                'name2': name
            })
        if res.is_rental_orders and res.dp:
            name = self.env['ir.sequence'].next_by_code('direct.purchase.seqs.r')
            res.name = name
            res.name_dp = name
        return res

    @api.depends('rent_duration', 'rent_duration_unit', 'date_planned')
    def _compute_expected_return_date(self):
        for record in self:
            expected_date = record.date_planned
            rent_duration = record.rent_duration
            main_date = expected_date
            if record.rent_duration_unit == 'days' and expected_date:
                main_date = expected_date + timedelta(days=rent_duration)
            elif record.rent_duration_unit == 'weeks' and expected_date:
                total_days = rent_duration * 7
                main_date = expected_date + timedelta(days=total_days)
            elif record.rent_duration_unit == 'months' and expected_date:
                main_date = expected_date + relativedelta(months=rent_duration)
            elif record.rent_duration_unit == 'years' and expected_date:
                main_date = expected_date + relativedelta(years=rent_duration)
            record.expected_return_date = main_date

    @api.onchange('is_rent_duration', 'rent_duration', 'rent_duration_unit')
    def onchange_rent_duration(self):
        if self.is_rent_duration:
            self.order_line.rent_duration = self.rent_duration
            self.order_line.rent_duration_unit = self.rent_duration_unit
            self.order_line.expected_return_date = self.expected_return_date

    def action_delivery_order(self):
        return {
			'name': 'Picking',
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_model': 'stock.picking',
            'domain': [('purchase_order_id', '=', self.id)],
            'target': 'current'
		}

    def action_view_picking(self):
        res = super(PurchaseOrder, self).action_view_picking()
        receipts = self.picking_ids.filtered(lambda r: r.picking_type_code == 'incoming')
        res['domain'] = [('id', 'in', receipts.ids)]
        return res

    def _compute_picking(self):
        res = super(PurchaseOrder, self)._compute_picking()
        for record in self:
            record.picking_count = len(record.picking_ids.filtered(lambda r: r.picking_type_code == "incoming"))
        return res

    def _compute_delivery(self):
        for record in self:
            record.delivery_count = self.env['stock.picking'].search_count([('purchase_order_id', '=', record.id)])

    @api.depends('amount_untaxed', 'branch_id', 'currency_id')
    def _compute_approval_matrix_id(self):
        res = super(PurchaseOrder, self)._compute_approval_matrix_id()
        for record in self:
            if record.is_rental_orders and record.is_approval_matrix and record.company_id and record.branch_id and record.amount_untaxed:
                approval_matrix_id = self.env['approval.matrix.purchase.order'].search([
                            ('minimum_amt', '<=', record.amount_untaxed),
                            ('maximum_amt', '>=', record.amount_untaxed),
                            ('branch_id', '=', record.branch_id.id),
                            ('company_id', '=', record.company_id.id),
                            ('currency_id', '=', record.currency_id.id),
                            ('order_type', '=', "rental_order")], limit=1)
                if not approval_matrix_id:
                    raise ValidationError(_("You don’t have approval matrix for this RFQ, please set Purchase Order Approval Matrix first"))
                record.approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
        return res

    @api.depends('amount_untaxed','approval_matrix_id')
    def _compute_approval_matrix_direct(self):
        res = super(PurchaseOrder, self)._compute_approval_matrix_direct()
        for record in self:
            if record.is_approval_matrix_direct and record.dp and record.is_rental_orders:
                approval_matrix_id = self.env['approval.matrix.direct.purchase'].search([
                    ('minimum_amt', '<=', record.amount_untaxed),
                    ('maximum_amt', '>=', record.amount_untaxed),
                    ('company_id', '=', record.company_id.id),
                    ('branch_id', '=', record.branch_id.id),
                    ('order_type', '=', "rental_order")
                    ], limit=1)
                record.direct_approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
        return res

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _default_domain(self):
        res = super(PurchaseOrderLine, self)._default_domain()
        context = dict(self.env.context) or {}
        if context.get('rentals_orders'):
            return [('is_rented', '=', True)]
        return res

    rent_duration = fields.Integer(string='Rent Duration')
    rent_duration_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
    ],string="Single Rent Duration")
    expected_return_date = fields.Date(string="Expected Return Date", compute="_compute_expected_return_date", store=True)
    is_rental_orders = fields.Boolean(string="Rental Orders", default=False, related="order_id.is_rental_orders", store=True)
    is_rent_duration = fields.Boolean(string='Rent Duration', related="order_id.is_rent_duration")

    @api.depends('rent_duration', 'rent_duration_unit', 'date_planned')
    def _compute_expected_return_date(self):
        for record in self:
            expected_date = record.date_planned
            rent_duration = record.rent_duration
            main_date = expected_date
            if record.rent_duration_unit == 'days' and expected_date:
                main_date = expected_date + timedelta(days=rent_duration)
            elif record.rent_duration_unit == 'weeks' and expected_date:
                total_days = rent_duration * 7
                main_date = expected_date + timedelta(days=total_days)
            elif record.rent_duration_unit == 'months' and expected_date:
                main_date = expected_date + relativedelta(months=rent_duration)
            elif record.rent_duration_unit == 'years' and expected_date:
                main_date = expected_date + relativedelta(years=rent_duration)
            record.expected_return_date = main_date

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if self.order_id.is_rent_duration:
            self.rent_duration = self.order_id.rent_duration
            self.rent_duration_unit = self.order_id.rent_duration_unit
            self.expected_return_date = self.order_id.expected_return_date
        return res

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        if not 'from_extend_rental' in self.env.context:
            return super()._onchange_quantity()
        else:
            return False

class AccountMove(models.Model):
    _inherit = 'account.move'

    # func agar journal item dari receipt tidak terbuat bagi rental order, tp harus fixing di accounting_stockoperation funct _action_done
    # @api.model
    # def create(self, vals):
    #     if 'from_picking' not in self.env.context:
    #         res = super(AccountMove, self).create(vals)
    #         return res
    #     else:
    #         return False

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model
    def create(self, vals):
        if 'product_id' in vals:
            product_id = self.env['product.product'].browse(vals['product_id'])
            product_name = product_id.name
            if product_name != 'Down Payment' and 'rentals_orders' in self.env.context:
                vals['account_id'] = product_id.categ_id.rental_account.id
        res = super(AccountMoveLine, self).create(vals)
        return res

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order")

