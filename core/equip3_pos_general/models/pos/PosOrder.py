# -*- coding: utf-8 -*-

import base64
import pytz
import logging
import psycopg2

from datetime import datetime, timedelta
from lxml import etree

from odoo import api, fields, models, tools, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError, Warning

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'out_receipt': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'in_receipt': 'supplier',
}

_logger = logging.getLogger(__name__)


class PosOrderLog(models.Model):
    _inherit = "pos.order.log"


    branch_id = fields.Many2one('res.branch', string='Branch', related="session_id.pos_branch_id")
    company_id = fields.Many2one('res.company', string='Company', related="session_id.company_id")

class PosBackUpOrders(models.Model):
    _inherit = "pos.backup.orders"
    
    branch_id = fields.Many2one('res.branch', string='Branch', related="config_id.pos_branch_id")
    company_id = fields.Many2one('res.company', string='Company', related="config_id.company_id")

class POSOrder(models.Model):
    _inherit = 'pos.order'

    is_past_date = fields.Boolean(compute='_compute_is_past_date', store=True)

    def _compute_is_past_date(self):
        for order in self:
            today = fields.Date.today()
            order_date = fields.Date.from_string(order.date_order)
            return_period = timedelta(days=order.config_id.pos_order_period_return_days)
            period_end = today + return_period
            order.is_past_date = (order_date - today) > return_period

    self_order_id = fields.Many2one('pos.order','Self Order',compute='_compute_self_order_id')
    take_away_order = fields.Boolean('Take Away Order')
    delivery_date = fields.Datetime('Delivery Date of Bill')
    delivered_date = fields.Datetime('Delivered Date of Bill')
    delivery_address = fields.Char('Delivery Address of Bill')
    delivery_phone = fields.Char('Delivery Phone', help='Phone of Customer for Shipping')
    shipping_id = fields.Many2one('res.partner', 'Partner Shipping')
    statement_ids = fields.One2many(
        'account.bank.statement.line',
        'pos_statement_id',
        string='Bank Payments',
        states={'draft': [('readonly', False)]},
        readonly=True)
    expire_date = fields.Datetime('Expire Date')
    is_return = fields.Boolean('Is Return')
    is_returned = fields.Boolean('Is Returned')
    email = fields.Char('Email')
    email_invoice = fields.Boolean('Email Invoice')
    signature = fields.Binary('Signature', readonly=1)
    parent_id = fields.Many2one('pos.order', 'Parent Order', readonly=1)
    sale_id = fields.Many2one('sale.order', 'Sale Order', readonly=1)
    margin = fields.Float(
        'Margin',
        compute='_compute_margin',
        store=True
    )
    partial_payment = fields.Boolean('Partial Payment')
    booking_id = fields.Many2one(
        'sale.order',
        'Covert from Sale Order',
        help='This order covert from Quotation Sale order',
        readonly=1)
    so_pickup_id = fields.Many2one(
        'sale.order',
        'SO Pickup',)
    payment_journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        readonly=0,
        related=None, )
    location_id = fields.Many2one(
        'stock.location',
        string="Source Location",
        related=None,
        readonly=1)
    pos_branch_id = fields.Many2one('res.branch', string='Branch', readonly=1, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    is_paid_full = fields.Boolean('Is Paid Full', compute='_checking_payment_full')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=1, related=False)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        'Analytic Account'
    )
    state = fields.Selection(selection_add=[
        ('quotation', 'Quotation')
    ], ondelete={
        'quotation': 'set default',
    })
    removed_user_id = fields.Many2one(
        'res.users',
        'Removed by User',
        readonly=1)
    is_quotation = fields.Boolean('Is Quotation Order')
    paid_date = fields.Datetime('Paid Date')
    picking_type_id = fields.Many2one(
        'stock.picking.type', related=False,
        string="Operation Type",
        readonly=False)
    receipt_count = fields.Integer(compute='_get_receipt_count', string='Receipt Count')
    employeemeal_employee_id = fields.Many2one('hr.employee', string="Employee Meal", copy=False)
    # variant_ids = fields.Many2many(
    #     'product.variant',
    #     'pos_order_line_variant_rel',
    #     'line_id', 'variant_id',
    #     string='Variant Items', readonly=1)

    cashier_id = fields.Many2one('res.users', string="Cashier")
    void_order_id = fields.Many2one('pos.order', string="Void Order")
    void_state = fields.Char(string='Void Status', default='')
    rounding_multiplier = fields.Float(string='Rounding Multiplier', digits=0, copy=False)
    # rounding_payment = fields.Float(string='Rounding Payment', digits=0, copy=False)


    is_return_order = fields.Boolean(string='Return Order',copy=False)
    return_order_id = fields.Many2one('pos.order','Return Order Of',readonly=True,copy=False)
    return_status = fields.Selection([('-','Not Returned'),('Fully-Returned','Fully-Returned'),('Partially-Returned','Partially-Returned'),('Non-Returnable','Non-Returnable')],default='-',copy=False,string='Return Status')
    return_order_state = fields.Selection([
        ('-','Not Returned'),
        ('Fully-Returned','Fully-Returned'),
        ('Partially-Returned','Partially-Returned'),
        ('Non-Returnable','Non-Returnable')
    ], string='Return Order Status', compute='_compute_return_order_state')

    cron_picking = fields.Boolean('Create picking via CRON', default=False)
    ean13 = fields.Char('Ean13', readonly=1)

    is_multiple_warehouse = fields.Boolean(string='Multiple Warehouse')

    is_show_pos_payment = fields.Boolean('Is Show Pos Payment', compute='_compute_is_show_pos_payment')

    # OVERRIDE
    @api.depends('picking_ids', 'picking_ids.state')
    def _compute_picking_count(self):
        picking_by_order_id = {}
        if self: # skip branch rules
            query = '''
                SELECT sp.pos_order_id, COUNT(sp.id)
                FROM stock_picking AS sp
                WHERE sp.pos_order_id IN (%s)
                GROUP BY sp.pos_order_id
            ''' % (str(self.ids)[1:-1])
            self.env.cr.execute(query)
            picking_by_order_id = dict(self.env.cr.fetchall())

        for order in self:
            order.picking_count = picking_by_order_id.get(order.id,)
            order.failed_pickings = bool(order.picking_ids.filtered(lambda p: p.state != 'done'))

    # OVERRIDE
    def action_stock_picking(self):
        self.ensure_one()
        if self.picking_count != len(self.picking_ids.ids):
            branch_name = self.pos_branch_id and self.pos_branch_id.name or 'False'
            raise Warning(_(f"Cannot open pickings, please select branch '{branch_name}' first"))

        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_ready')
        action['context'] = {}
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action

    def _compute_self_order_id(self):
        for data in self:
            data.self_order_id = data.id

    def _compute_return_order_state(self):
        result = {}
        if self:
            query = '''
                SELECT po.id, SUM(po_r.amount_total)
                FROM pos_order AS po_r
                LEFT JOIN pos_order AS po ON po.id = po_r.return_order_id
                WHERE po.id IN (%s)
                    AND po_r.return_order_id IS NOT NULL
                GROUP BY po.id
            ''' % (str(self.ids)[1:-1])
            self._cr.execute(query)
            result = dict(self._cr.fetchall())
            
        for rec in self:
            state = '-'
            if result.get(rec.id, False) is not False:
                amount_return = abs(result.get(rec.id, 0))
                if amount_return < rec.amount_total:
                    state = 'Partially-Returned'
                if amount_return >= rec.amount_total:
                    state = 'Fully-Returned'
            rec.return_order_state = state

    def _prepare_refund_values(self, current_session):
        res = super(POSOrder, self)._prepare_refund_values(current_session=current_session)
        res.update({
            'is_return_order': True,
            'return_order_id': self.id,
        })

        return_status = 'Partially-Returned'
        if abs(res['amount_total']) >= self.amount_total:
            return_status = 'Fully-Returned'
        self.write({ 'return_status': return_status })

        return res

    def _validate_order_for_refund(self):
        if self.return_order_state == 'Fully-Returned':
            raise UserError(_('Order already Fully-Returned'))
        return super(POSOrder, self)._validate_order_for_refund()

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(POSOrder, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        user_pos_not_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_cashier') or self.env.user.has_group('equip3_pos_masterdata.group_pos_waiter') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cooker')
        user_pos_have_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_staff') or self.env.user.has_group('equip3_pos_masterdata.group_pos_supervisor') or self.env.user.has_group('equip3_pos_masterdata.group_pos_manager')
        if user_pos_not_create_edit and not user_pos_have_create_edit:
            root = etree.fromstring(res['arch'])
            root.set('edit', 'false')
            res['arch'] = etree.tostring(root)
            
        return res

    def _get_order_not_picking(self):
        query = '''
            SELECT t.pos_order_id, t.picking_count
            FROM (
                SELECT 
                    po.id AS pos_order_id, 
                    COUNT(sp.id) as picking_count
                FROM pos_order AS po
                LEFT JOIN stock_picking AS sp ON sp.pos_order_id = po.id
                WHERE po.cron_picking = 't'
                    AND po.state NOT IN ('draft', 'cancel', 'quotation')
                GROUP BY po.id
            ) AS t
            WHERE t.picking_count = 0
            ORDER BY t.pos_order_id DESC
            LIMIT 75
        '''
        self._cr.execute(query)
        result = self._cr.fetchall()
        return [r[0] for r in result]

    def create_order_picking_cron(self):
        order_ids = self._get_order_not_picking()
        if order_ids:
            stock_picking_sequences = []
            orders = self.env['pos.order'].search([('id', 'in', order_ids)], limit=75)
            for order in orders:
                with_context = {
                    'create_picking_from_cron': True, 
                    'pos_order':order,
                    'stock_picking_sequences': stock_picking_sequences
                }
                sequence = order.with_context(with_context)._create_order_picking()
                if sequence:
                    stock_picking_sequences += sequence
                order.cron_picking = False
        return True

    
    def _create_order_picking(self):
        # OVERRIDE
        self.ensure_one()
        if not self._context.get('pos_order'):
            self.with_context(pos_order=self)
        if not self.cron_picking:
            self.cron_picking = True
        if not self.env.context.get('create_picking_from_cron'):
            return True
        
        if not self.session_id.update_stock_at_closing or (self.company_id.anglo_saxon_accounting and self.to_invoice):
            pos_branch_id = False
            if self.config_id and self.config_id.pos_branch_id:
                pos_branch_id = self.config_id.pos_branch_id.id
            if not pos_branch_id:
                pos_branch_id = self.env['res.branch'].sudo().get_default_branch()
            with_context = { **{'pos_branch_id': pos_branch_id}, **self._context }

            default_picking_type = self.config_id.picking_type_id
            default_destination_id = False
            if self.partner_id.property_stock_customer:
                default_destination_id = self.partner_id.property_stock_customer.id
            elif not default_picking_type or not default_picking_type.default_location_dest_id:
                default_destination_id = self.env['stock.warehouse']._get_partner_locations()[0].id
            else:
                default_destination_id = default_picking_type.default_location_dest_id.id

            if self.config_id.multi_stock_operation_type:
                picking_type_ids = list(set([ l.picking_type_id.id for l in self.lines]))
                pickings = []
                for picking_type_id in picking_type_ids:
                    if picking_type_id:
                        lines = self.lines.filtered(lambda x: x.picking_type_id.id == picking_type_id)
                        picking_type = self.env['stock.picking.type'].search([('id','=',picking_type_id)], limit=1)
                        destination_id = picking_type.default_location_dest_id.id
                    if not picking_type_id:
                        lines = self.lines.filtered(lambda x: not x.picking_type_id)
                        picking_type = default_picking_type
                        destination_id = default_destination_id

                    if not destination_id:
                        raise UserError(_(f'Operations Types -> Default Destination Location is not set.') + f' [{str(picking_type)}]')

                    picking = self.env['stock.picking'].with_context(with_context)._create_picking_from_pos_order_lines(destination_id, lines, picking_type, self.partner_id)
                    picking.write({'pos_session_id': self.session_id.id, 'pos_order_id': self.id, 'origin': self.name})
                    pickings.append(picking)

                return [p.name for p in pickings]

            else:
                picking_type = default_picking_type
                destination_id = default_destination_id
                pickings = self.env['stock.picking'].with_context(with_context)._create_picking_from_pos_order_lines(destination_id, self.lines, picking_type, self.partner_id)
                pickings.write({'pos_session_id': self.session_id.id, 'pos_order_id': self.id, 'origin': self.name})
                return [p.name for p in pickings]

    @api.depends('picking_ids')
    def compute_location(self):
        for rec in self:
            rec.location_id = False
            if rec.is_multiple_warehouse == False:
                for pck in rec.picking_ids:
                    rec.location_id = pck.location_id

    def _get_receipt_count(self):
        for record in self:
            record.receipt_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'pos.order'),
                ('res_id', '=', record.id)
            ])


    def action_download_receipt(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        action['context'] = {}
        action['domain'] = [('res_model', '=', 'pos.order'), ('res_id', '=', self.id)]
        return action

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        context = self._context.copy()
        if context.get('pos_config_id', None):
            config = self.env['pos.config'].browse(context.get('pos_config_id'))
            domain = [('config_id', '=', config.id)]
            if config.pos_orders_load_orders_another_pos:
                domain = []
            today = datetime.today()
            if context.get('partner_id', None):
                domain = [('partner_id', '=', context.get('partner_id', None))]
            if context.get('reference', None):
                domain = ['|', '|',
                    ('name', '=', context.get('reference', None)),
                    ('pos_reference', '=', context.get('reference', None)),
                    ('ean13', '=', context.get('reference', None)),
                ]
            # SQL Based data fetching for faster loading
            sql_where = ""
            sql_limit = limit and str(limit) or 'NULL'
            # Update / Remove fields to comply with SQL syntax
            sql_fields = ['id'] + list(set(fields))
            if 'picking_ids' in sql_fields:
                sql_fields.remove('picking_ids')
            sql_fields = ['po.' + f for f in sql_fields]
            sql_fields = ",\n".join(sql_fields)
            if 'po.partner_id' in sql_fields:
                sql_fields = sql_fields.replace("po.partner_id", "COALESCE('[' || rp.id || ', ''' || rp.name || ''']') AS partner_id")
            if 'po.config_id' in sql_fields:
                sql_fields = sql_fields.replace("po.config_id", "ps.config_id")
            if 'po.is_paid_full' in sql_fields:
                sql_fields = sql_fields.replace("po.is_paid_full", "(CASE WHEN (po.amount_paid - po.amount_return) = po.amount_total THEN true ELSE false END) AS is_paid_full")
            # Convert domain to SQL Where clause
            for item in domain:
                if len(item) != 3:
                    continue
                if sql_where:
                    sql_where += ' AND '
                sql_where += item[0] + item[1]
                if type(item[2]) in (int, float):
                    sql_where += str(item[2])
                else:
                    sql_where += "'%s'" % item[2]
            # Process query and get the result

            if sql_where:
                sql_query = 'SELECT \n%s \nFROM pos_order AS po \nLEFT JOIN pos_session AS ps ON (po.session_id = ps.id) \nLEFT JOIN res_partner AS rp ON (po.partner_id = rp.id) \nWHERE \n%s\nLIMIT %s' % (sql_fields, sql_where, sql_limit)
            else:
                sql_query = 'SELECT \n%s \nFROM pos_order AS po \nLEFT JOIN pos_session AS ps ON (po.session_id = ps.id) \nLEFT JOIN res_partner AS rp ON (po.partner_id = rp.id) \nLIMIT %s' % (sql_fields, sql_limit)
            sql_query = sql_query.replace("po.payment_ids", "po.parent_id")
            sql_query = sql_query.replace(",\npo.lines", "")
            self.env.cr.execute(sql_query)
            data = self.env.cr.dictfetchall()
            # Result data update
            for count in range(len(data)):
                data[count]['partner_id'] = data[count]['partner_id'] and eval(data[count]['partner_id']) or False
            return data
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def create_pos_order_from_so(self, sale_id):
        pos_line_obj = self.env['pos.order.line']
        sale = self.env['sale.order'].sudo().browse(sale_id)
        if self.env.context.get('delivered'):
            sale.action_force_validate_picking()
            

        session = self.env['pos.session'].sudo().browse(self.env.context.get('session_id'))
        vals = {}
        vals['user_id'] = sale.user_id.id
        vals['session_id'] = session.id
        vals['name'] = sale.name
        vals['so_pickup_id'] = sale.id
        vals['pos_reference'] = sale.name
        vals['partner_id'] = sale.partner_id.id
        vals['date_order'] = sale.date_order
        vals['fiscal_position_id'] = sale.fiscal_position_id and sale.fiscal_position_id.id or False
        vals['pricelist_id'] = sale.pricelist_id and sale.pricelist_id.id or False
        vals['amount_total'] = sale.amount_total
        vals['amount_paid'] = sale.amount_total
        vals['amount_tax'] = sale.amount_tax
        vals['amount_return'] = 0.0
        vals['company_id'] = sale.company_id.id
        vals['location_id'] = session.config_id.stock_location_id and session.config_id.stock_location_id.id or False
        vals['to_invoice'] = False
        vals['is_tipped'] = False
        vals['tip_amount'] = 0.0
        line_data = []
        for line in sale.order_line:
            if line.product_id:
                if sale.ean13:
                    pos_lines = pos_line_obj.sudo().search([('order_id.ean13','=',sale.ean13),('product_id','=', line.product_id.id)])
                    if pos_lines:
                        pos_lines.write({'is_done_self_pickup':True})
                line_vals = {}
                line_vals['full_product_name'] = line.name
                line_vals['product_id'] = line.product_id and line.product_id.id or False
                line_vals['product_uom_id'] = line.product_uom.id
                line_vals['price_unit'] = line.price_unit
                line_vals['qty'] = line.product_uom_qty
                line_vals['price_subtotal'] = line.price_unit * line.product_uom_qty
                line_vals['price_subtotal_incl'] = line.price_unit * line.product_uom_qty
                line_vals['tax_ids_after_fiscal_position'] = [(6,0,line.tax_id.ids)]
                line_vals['user_id'] = sale.user_id.id
                line_data.append((0,0,line_vals))
        vals['lines'] = line_data
        # Create POS Order
        pos_order_id = self.create(vals)
        if not line_data:
            return True
        # Create payment lines
        if sale.payment_partial_method_id:
            payment_method = sale.payment_partial_method_id
        else:
            payment_method = pos_order_id.config_id.payment_method_ids.filtered(lambda l: l.name.lower() == 'cash')
            if not payment_method:
                payment_method = pos_order_id.config_id.payment_method_ids[0]
            else:
                payment_method = payment_method[0]
        if payment_method:
            payment_vals = {}
            payment_vals['amount'] = sale.amount_total
            payment_vals['payment_date'] = datetime.now()
            payment_vals['payment_method_id'] = payment_method.id
            payment_vals['card_type'] = ''
            payment_vals['cardholder_name'] = ''
            payment_vals['transaction_id'] = ''
            payment_vals['payment_status'] = ''
            payment_vals['ticket'] = ''
            payment_vals['pos_order_id'] = pos_order_id.id
            payment_vals['pos_branch_id'] = pos_order_id.pos_branch_id and pos_order_id.pos_branch_id.id or False
            payment_vals['payment_card_id'] = False
            pos_order_id.add_payment(payment_vals)
            # Process POS Order - Done
            pos_order_id.action_pos_order_paid()
            # Create Picking
            pos_order_id._create_order_picking()
        sale.pos_order_id = pos_order_id.id
        return True

    def getTopSellingProduct(self, totalRows):
        sql = """
            select 
                pol.product_id, sum(pol.qty)
            from 
                pos_order_line as pol
            group by pol.product_id
            Order by sum(pol.qty) desc
            limit %s
        """ % totalRows
        self.env.cr.execute(sql)
        topSellingProducts = self.env.cr.fetchall()
        return topSellingProducts

    def print_report(self):
        for order in self:
            return order.print_html_report(order.id, 'equip3_pos_masterdata.pos_order_template')

    def print_html_report(self, docids, reportname, data=None):
        report = self.env['ir.actions.report'].sudo()._get_report_from_name(reportname)
        html = report.render_qweb_html(docids, data=data)[0]
        return html

    def _prepare_invoice_vals(self):
        vals = super(POSOrder, self)._prepare_invoice_vals()
        vals['journal_id'] = self.payment_journal_id.id
        return vals
    
    def action_pos_order_invoice(self):
        """
        TODO: add move_id return back to pos screen
        """
        result = super(POSOrder, self).action_pos_order_invoice()
        move_id = result.get('res_id', None)
        if move_id:
            result.update({'move_id': move_id})
            if self._context.get('return_data') is True :
                result.update(self._get_data_account_move_for_pos_frontend(move_id, self._context))
        return result

    def _get_data_account_move_for_pos_frontend(self, move_id, context):
        values = {}
        move = self.env['account.move'].search_read([('id','=', move_id)], ['id','name'], limit=1)
        move = move and move[0] or []
        for k in move:
            values[k] = move[k]
        return {'data': values}

    def made_invoice(self):
        for order in self:
            order.action_pos_order_invoice()
            order.account_move.sudo().with_context(force_company=self.env.user.company_id.id).post()
        return True

    # todo: when cancel order we set all quantity of lines and payment method amount to 0
    # todo: because when pos session closing, odoo core get all total amount of line and pos payment compare before posting
    def action_pos_order_cancel(self):
        for order in self:
            if order.picking_ids or order.account_move:
                raise UserError(_(
                    'Error, Order have Delivery Order or Account move, it not possible cancel, please return products'))
            order.lines.write({
                'price_unit': 0,
                'price_subtotal': 0,
                'price_subtotal_incl': 0,
            })
            order.write({'amount_total': 0})
            order.payment_ids.write({'amount': 0})
        return super(POSOrder, self).action_pos_order_cancel()

    def _is_pos_order_paid(self):
        if not self.currency_id and self.env.user.company_id.currency_id:
            self.currency_id = self.env.user.company_id.currency_id.id
        return super(POSOrder, self)._is_pos_order_paid()

    def _checking_payment_full(self):
        for order in self:
            order.is_paid_full = False
            if (order.amount_paid - order.amount_return) == order.amount_total:
                order.is_paid_full = True

    @api.depends('lines.margin')
    def _compute_margin(self):
        for order in self:
            order.margin = sum(order.mapped('lines.margin'))

    def unlink(self):
        for order in self:
            if order._is_pos_order_paid():
                raise UserError(_(
                    'Not allow remove Order have payment information. Please set to Cancel, Order Ref %s' % order.name))
            if order.state == 'cancel' and order.removed_user_id and not self.env.user.has_group(
                    'point_of_sale.group_pos_manager'):
                raise UserError(_(
                    "You can not remove this order, only POS Manager can do it"))
        return super(POSOrder, self).unlink()

    def write(self, vals):
        """
        TODO: required link pos_branch_id to:
            - account bank statement and lines
            - account move and lines (x)
            - stock picking and moves, and stock moves line (x)
            - pos payment (x)
        """
        if vals.get('state', None) in ['paid', 'invoice']:
            vals.update({'paid_date': fields.Datetime.now()})
        res = super(POSOrder, self).write(vals)
        for order in self:
            pos_branch = order.pos_branch_id
            if order.picking_ids:
                picking_ids = [p.id for p in order.picking_ids]
                picking_ids.append(0)
                if not order.location_id:
                    if not pos_branch:
                        self.env.cr.execute(
                            "UPDATE stock_picking SET pos_order_id=%s where id in %s", (order.id, tuple(picking_ids),))
                    else:
                        self.env.cr.execute(
                            "UPDATE stock_picking SET pos_branch_id=%s, pos_order_id=%s where id in %s", (
                                pos_branch.id, order.id, tuple(picking_ids),))
                else:
                    if not pos_branch:
                        self.env.cr.execute(
                            "UPDATE stock_picking SET pos_order_id=%s,location_id=%s  where id in %s", (
                                order.id, order.location_id.id, tuple(picking_ids),))
                    else:
                        self.env.cr.execute(
                            "UPDATE stock_picking SET pos_branch_id=%s, pos_order_id=%s,location_id=%s  where id in %s",
                            (
                                pos_branch.id, order.id, order.location_id.id, tuple(picking_ids),))
                if pos_branch:
                    self.env.cr.execute(
                        "UPDATE stock_move SET pos_branch_id=%s WHERE picking_id in %s",
                        (pos_branch.id, tuple(picking_ids),))
                    self.env.cr.execute(
                        "UPDATE stock_move_line SET pos_branch_id=%s WHERE picking_id in %s" % (
                            pos_branch.id, tuple(picking_ids),))
            if vals.get('state', False) in ['paid', 'invoiced']:
                for line in order.lines:
                    self.env.cr.execute(
                        "UPDATE pos_voucher SET state='active' WHERE pos_order_line_id=%s" % (
                            line.id))  # TODO: active vouchers for customers can use, required paid done
                order.auto_closing_backup_session()
            if order.pos_branch_id:
                if order.account_move:
                    self.env.cr.execute("UPDATE account_move SET pos_branch_id=%s WHERE id=%s" % (
                        order.pos_branch_id.id, order.account_move.id))
                    self.env.cr.execute("UPDATE account_move_line SET pos_branch_id=%s WHERE move_id=%s" % (
                        order.pos_branch_id.id, order.account_move.id))

        return res

    def action_pos_order_paid(self):
        self.ensure_one()
        if self.config_id.rounding and (
                (self.amount_total - self.amount_paid) > 0 and (self.amount_total - self.amount_paid) < 1):
            rounding_payment_method_id = None
            for payment in self.payment_ids:
                if payment.amount > 0:
                    rounding_payment_method_id = payment.payment_method_id.id
                    break
            if rounding_payment_method_id:
                payment_difference = self.amount_total - self.amount_paid
                _logger.info('Rounding cash %s' % payment_difference)
                rounding_payment_vals = {
                    'name': _('rounding cash'),
                    'pos_order_id': self.id,
                    'amount': payment_difference,
                    'payment_date': fields.Datetime.now(),
                    'payment_method_id': rounding_payment_method_id,
                    'is_change': True,
                }
                self.add_payment(rounding_payment_vals)
        return super(POSOrder, self).action_pos_order_paid()

    @api.model
    def auto_closing_backup_session(self):
        if self.session_id and self.session_id.backup_session:
            orders_not_paid = self.search([
                ('state', 'not in', ['paid', 'invoiced']),
                ('id', '!=', self.id),
                ('session_id', '=', self.session_id.id)
            ])
            if not orders_not_paid:
                self.session_id.force_action_pos_session_close()
        return True

    @api.model
    def create(self, vals):

        session = self.env['pos.session'].sudo().browse(vals.get('session_id'))
        if session and session.config_id.pos_branch_id:
            vals.update({'pos_branch_id': session.config_id.pos_branch_id.id})

        if not vals.get('pos_branch_id'):
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
        if not vals.get('location_id', None):
            vals.update({
                'location_id': session.config_id.stock_location_id.id if session.config_id.stock_location_id else None
            })
        if not vals.get('payment_journal_id', None):
            vals.update({'payment_journal_id': session.config_id.journal_id.id})
        if not vals.get('currency_id', None) and session.config_id.currency_id:
            vals.update({'currency_id': session.config_id.currency_id.id})

        if session.config_id.zone_id:
            vals.update({'zone_id': session.config_id.zone_id.id})

        bundle_pack_combo_items = {}
        dynamic_combo_items = {}
        addonItems = None
        if vals and vals.get('lines', []):
            for line in vals.get('lines', []):
                line = line[2]
                # TODO: combo bundle pack items
                combo_item_ids = line.get('combo_item_ids', None)
                if combo_item_ids:
                    for combo_item in combo_item_ids:
                        if float(combo_item['quantity']) <= 0:
                            continue
                        comboRecord = self.env['pos.combo.item'].sudo().browse(combo_item['id'])
                        productOfCombo = comboRecord.product_id
                        if not bundle_pack_combo_items.get(combo_item['id']):
                            bundle_pack_combo_items[combo_item['id']] = {
                                'product_id': productOfCombo.id,
                                'qty': float(combo_item['quantity']) * line['qty'],
                                'name': '%s [Combo Item of] %s' % (
                                    productOfCombo.name, line.get('full_product_name', ''))
                            }
                        else:
                            bundle_pack_combo_items[combo_item['id']]['qty'] += combo_item['quantity'] * line['qty']
                    del line['combo_item_ids']
                # TODO: combo dynamic items
                selected_combo_items = line.get('selected_combo_items', None)
                if selected_combo_items:
                    for product_id, quantity in selected_combo_items.items():
                        if not dynamic_combo_items.get(product_id, False):
                            dynamic_combo_items[int(product_id)] = quantity
                        else:
                            dynamic_combo_items[int(product_id)] += quantity
                    del line['selected_combo_items']
                    
        # updated_pos_ref = vals['pos_reference']
        # after_rep1 = updated_pos_ref.replace("false", self.env.user.cashier_code)
        # after_rep2 = after_rep1.replace("-", ".")
        # vals['pos_reference'] = after_rep2
        
        order = super(POSOrder, self).create(vals)
        if bundle_pack_combo_items:
            for combo_item_id, item in bundle_pack_combo_items.items():
                self.env['pos.order.line'].create({
                    'name': item['name'],
                    'full_product_name': item['name'],
                    'product_id': item['product_id'],
                    'qty': item['qty'],
                    'price_unit': 0,
                    'order_id': order.id,
                    'price_subtotal': 0,
                    'price_subtotal_incl': 0,
                })
        if dynamic_combo_items:
            order.create_picking_dynamic_combo_items(dynamic_combo_items)
        if order.return_order_id:
            order.return_order_id.write({'is_returned': True})
        # if order.company_id.rounding_multiplier and order.company_id.is_order_rounding:
        #     total_origin = 0
        #     for l in order.lines:
        #         total_origin+=l.price_subtotal_incl
        #     order.write({'rounding_multiplier':order.amount_total - total_origin - order.total_mdr_amount_customer})

        for line in order.lines:
            if line.promotion_id:
                if line.promotion_id.no_of_usage > 0 and line.promotion_id.no_of_usage <= line.promotion_id.no_of_used:
                    line.promotion_id.write({'active':False})
        return order

    def action_pos_order_send(self):
        if not self.partner_id:
            raise UserError(_('Customer not found on this Point of Sale Orders.'))
        self.ensure_one()
        template = self.env.ref('equip3_pos_masterdata.email_template_edi_pos_orders', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='pos.order',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def add_payment(self, data):
        if self.pos_branch_id:
            data.update({'pos_branch_id': self.pos_branch_id.id})
        if data.get('name', None) == 'return':
            order = self.browse(data.get('pos_order_id'))
            if order.currency_id and self.env.user.company_id.currency_id and order.currency_id.id != self.env.user.company_id.currency_id.id:
                customer_payment = self.env['pos.payment'].search([('pos_order_id', '=', order.id)], limit=1)
                if customer_payment:
                    data.update({
                        'payment_method_id': customer_payment.payment_method_id.id
                    })
        res = super(POSOrder, self).add_payment(data)

        #TODO: Don't calculate with payment method receivable (is_receivables=True)
        self.amount_paid = sum(self.payment_ids.filtered(lambda p: p.payment_method_id.is_receivables==False).mapped('amount'))

        return res

    # def made_purchase_order(self):
    #     # TODO: create 1 purchase get products return from customer
    #     customer_return = self.env['res.partner'].search([('name', '=', 'Customer return')])
    #     po = self.env['purchase.order'].create({
    #         'partner_id': self.partner_id.id if self.partner_id else customer_return[0].id,
    #         'name': 'Return/' + self.name,
    #     })
    #     for line in self.lines:
    #         if line.qty < 0:
    #             self.env['purchase.order.line'].create({
    #                 'order_id': po.id,
    #                 'name': 'Return/' + line.product_id.name,
    #                 'product_id': line.product_id.id,
    #                 'product_qty': - line.qty,
    #                 'product_uom': line.product_id.uom_po_id.id,
    #                 'price_unit': line.price_unit,
    #                 'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
    #             })
    #     po.button_confirm()
    #     for picking in po.picking_ids:
    #         picking.action_assign()
    #         picking.force_assign()
    #         wrong_lots = self.set_pack_operation_lot(picking)
    #         if not wrong_lots:
    #             picking.button_validate()
    #     return True

    def set_done(self):
        return self.write({'state': 'done'})

    @api.model
    def action_send_email_with_receipt_to_customer(self, name, client, ticket, email, body):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            return False
        orders = self.sudo().search([('pos_reference', '=', name)])
        if not orders:
            return False
        order = orders[0]
        client_name = client.get('name', None) if client else 'Guy'
        message = _("<p>Dear %s,<br/>Here is your electronic ticket for the %s. </p>") % (client_name, name)
        message += _('<p>Note Order : <strong>%s</strong>. </p>' % body)
        message += _('<p>Regards</p>')
        message += _('<p>%s</p>' % self.env.company.name)
        filename = 'Receipt-' + name + '.jpg'
        receipt = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': ticket,
            'res_model': 'pos.order',
            'res_id': order.id,
            'store_fname': filename,
            'mimetype': 'image/jpeg',
        })
        template_data = {
            'subject': _('Receipt %s') % name,
            'body_html': message,
            'author_id': self.env.user.partner_id.id,
            'email_from': self.env.company.email or self.env.user.email_formatted,
            'email_to': email,
            'attachment_ids': [(4, receipt.id)],
        }

        if orders.mapped('account_move'):
            report = self.env.ref('point_of_sale.pos_invoice_report').render_qweb_pdf(orders.ids[0])
            filename = name + '.pdf'
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(report[0]),
                'store_fname': filename,
                'res_model': 'pos.order',
                'res_id': orders[:1].id,
                'mimetype': 'application/x-pdf'
            })
            template_data['attachment_ids'] += [(4, attachment.id)]

        mail = self.env['mail.mail'].create(template_data)
        mail.send()
        _logger.info('{POS} %s sending email success' % order.name)
        return True

    def saveReceipt(self, order_id=None, imageBase64=None):
        order = self.browse(order_id)
        if not order:
            return True
        fileName = order.pos_reference + '.jpg'
        receipt = self.env['ir.attachment'].create({
            'name': fileName,
            'type': 'binary',
            'datas': imageBase64,
            'res_model': 'pos.order',
            'res_id': order_id,
            'store_fname': fileName,
            'mimetype': 'image/jpeg',
        })
        _logger.info('new receipt saved: %s' % receipt.id)
        return receipt

    @api.model
    def action_send_email(self, subject, ticket, email, body):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            return False
        message = _("<p>Dear,<br/>Have new message for you.</p>")
        message += _('<p>Description : <strong>%s</strong>. </p>' % body)
        message += _('<p>Regards</p>')
        message += _('<p>%s</p>' % self.env.company.name)
        filename = subject + '.jpg'
        receipt = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': ticket,
            'res_model': 'res.users',
            'res_id': self.env.user.id,
            'store_fname': filename,
            'mimetype': 'image/jpeg',
        })
        template_data = {
            'subject': _('%s') % subject,
            'body_html': message,
            'author_id': self.env.user.partner_id.id,
            'email_from': self.env.company.email or self.env.user.email_formatted,
            'email_to': email,
            'attachment_ids': [(4, receipt.id)],
        }
        mail = self.env['mail.mail'].create(template_data)
        mail.send()
        return True

    @api.model
    def _order_fields(self, ui_order):
        user_tz = self.env.user.tz or pytz.utc
        local_tz = pytz.timezone(user_tz)
        order_fields = super(POSOrder, self)._order_fields(ui_order)
        update_name = True
        if ui_order.get('is_multiple_warehouse'):
            order_fields['is_multiple_warehouse'] = ui_order.get('is_multiple_warehouse', False)
        else:
            order_fields['is_multiple_warehouse'] = False

        if ui_order.get('is_return_order', None):
            order_fields.update({ 'is_return_order': ui_order['is_return_order'] })

        if ui_order.get('return_order_id', None):
            order_fields.update({ 'return_order_id': ui_order['return_order_id'] })
            order_return = self.browse(ui_order['return_order_id'])
            if not ui_order.get('is_exchange_order'):
                order_fields.update({ 'name': 'RETURN/'+ order_return.name})
                update_name = False
            if ui_order.get('exchange_amount') and ui_order.get('is_exchange_order'):
                order_fields.update({ 'name': 'EXCHANGE/'+ order_return.name})
                update_name = False

        if ui_order.get('return_status', None):
            order_fields.update({ 'return_status': ui_order['return_status'] })

        if ui_order.get('rounding_payment', None):
            order_fields.update({ 'rounding_payment': ui_order['rounding_payment'] })

        if ui_order.get('picking_type_id', None):
            order_fields.update({ 'picking_type_id': ui_order['picking_type_id'] })
        else:
            order_fields.update({ 'picking_type_id': self.env['pos.session'].browse( ui_order.get('pos_session_id')).config_id.picking_type_id.id })

        if ui_order.get('sale_id', False):
            order_fields.update({ 'sale_id': ui_order['sale_id'] })

        if ui_order.get('delivery_date', False):
            order_fields.update({ 'delivery_date': ui_order['delivery_date'] })

        if ui_order.get('delivery_address', False):
            order_fields.update({ 'delivery_address': ui_order['delivery_address'] })

        if ui_order.get('delivery_phone', False):
            order_fields.update({ 'delivery_phone': ui_order['delivery_phone'] })

        if ui_order.get('shipping_id'):
            order_fields.update({ 'shipping_id': ui_order['shipping_id'] })

        if ui_order.get('parent_id', False):
            order_fields.update({ 'parent_id': ui_order['parent_id'] })

        if ui_order.get('payment_journal_id', False):
            order_fields['payment_journal_id'] = ui_order.get('payment_journal_id')

        if ui_order.get('ean13', False):
            order_fields.update({ 'ean13': ui_order['ean13'] })

        if ui_order.get('expire_date', False):
            order_fields.update({ 'expire_date': ui_order['expire_date'] })

        if ui_order.get('is_return', False):
            order_fields.update({ 'is_return': ui_order['is_return'] })

        if ui_order.get('email', False):
            order_fields.update({ 'email': ui_order.get('email') })

        if ui_order.get('email_invoice', False):
            order_fields.update({ 'email_invoice': ui_order.get('email_invoice') })

        if ui_order.get('note', None):
            order_fields.update({ 'note': ui_order['note'] })

        if ui_order.get('return_order_id', False):
            order_fields.update({ 'return_order_id': ui_order['return_order_id'] })

        if ui_order.get('location_id', False):
            order_fields.update({ 'location_id': ui_order['location_id'] })

        if ui_order.get('booking_id', False):
            order_fields.update({ 'booking_id': ui_order['booking_id'] })

        if ui_order.get('currency_id', False):
            order_fields.update({ 'currency_id': ui_order['currency_id'] })

        if ui_order.get('analytic_account_id', False):
            order_fields.update({ 'analytic_account_id': ui_order['analytic_account_id'] })

        if ui_order.get('combo_item_ids', False):
            order_fields.update({ 'combo_item_ids': ui_order['combo_item_ids'] })

        if ui_order.get('take_away_order', False):
            order_fields.update({ 'take_away_order': ui_order['take_away_order'] })

        if ui_order.get('employeemeal_employee_id', False):
            order_fields.update({ 'employeemeal_employee_id': ui_order['employeemeal_employee_id'] })

        if ui_order.get('state', False):
            order_fields.update({ 'state': ui_order['state'] })

        if ui_order.get('removed_user_id', False):
            order_fields.update({ 'removed_user_id': ui_order['removed_user_id'] })

        if (ui_order.get('state', False) == 'cancel' and ui_order.get('removed_user_id', False)) and update_name :
            order_fields.update({ 'name': self.env['pos.session'].browse(ui_order['pos_session_id']).config_id.sequence_id._next(), })

        if ui_order.get('save_draft', None) and not ui_order.get('backend_id', None)  and update_name:
            order_fields.update({ 'name': self.env['pos.session'].browse(ui_order['pos_session_id']).config_id.sequence_id._next(), })

        if ui_order.get('is_self_picking', False):
            order_fields.update({ 'is_self_picking': ui_order['is_self_picking'] })

        if ui_order.get('is_home_delivery', False):
            order_fields.update({ 'is_home_delivery': ui_order['is_home_delivery'] })
        if ui_order.get('is_pre_order', False):
            order_fields.update({ 'is_pre_order': ui_order['is_pre_order'] })
        if ui_order.get('estimated_order_pre_order', False):
            order_fields.update({ 'estimated_order_pre_order': ui_order['estimated_order_pre_order'] })

        order_fields['total_mdr_amount_customer'] = ui_order.get('total_mdr_amount_customer')
        order_fields['total_mdr_amount_company'] = ui_order.get('total_mdr_amount_company')

        if ui_order.get('cashier_id'):
            user_cashier_id = self.env['res.users'].sudo().search([('id','=',ui_order['cashier_id'])], limit=1)
            if user_cashier_id:
                order_fields['cashier_id'] = user_cashier_id.id

        order_fields['void_order_id'] = ui_order.get('void_order_id')
        order_fields['void_state'] = ui_order.get('void_state') or ''
        return order_fields

    @api.model
    def _process_order(self, order, draft, existing_order):
        if order.get('data').get('state', None) == 'cancel':
            draft = True

        if order.get('id'):
            self.env['pos.sync.session.order'].update_sync_state(order['id'])

        order_id = super(POSOrder,self)._process_order(order, draft, existing_order) 
        if order_id:
            pos_order = self.browse(order_id)
            if pos_order:

                #TODO: If payment method selected is_receivables=True then order state is draft
                is_receivables = False
                for payment in pos_order.payment_ids:
                    if payment.payment_method_id.is_receivables:
                        is_receivables = True
                        break
                if is_receivables:
                    #TODO: Don't calculate with payment method receivable (is_receivables=True)
                    amount_paid = sum(pos_order.payment_ids.filtered(lambda p: p.payment_method_id.is_receivables==False).mapped('amount'))

                    pos_order.write({ 
                        'is_payment_method_with_receivable': True,
                        'state': 'invoiced',
                        'amount_paid': amount_paid,
                    })

        return order_id

    @api.model
    def get_code(self, code):
        return self.env['barcode.nomenclature'].sudo().sanitize_ean(code)

    def get_debit(self, order_id):
        order = self.browse(order_id)
        return order.amount_total - order.amount_paid

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        """
            - Reason we force this method bellow:
            1) If pos session use another pricelist have currency difference with pos config company currency
            2) have one statement rounding example: 0.11 VND inside statement_ids
            3) when order push to backend and currency VND have prec_acc = order.pricelist_id.currency_id.decimal_places is 1.0 (*)
            4) and method float_is_zero check 0.11 is 0 and if not float_is_zero(payments[2]['amount'], precision_digits=prec_acc) with be true
            5) if (4) true, _process_payment_lines not add statement rounding amount 0.11
            6) and when pos session action closing session and post entries, post entries will compare debit and credit and missed 0.11 VND
            7) And session could not close
            - So solution now is:
            1) if have order (pricelist >> currency) difference with company currency
            2) we not call parent method
            3) we only check statement line have amount not zero and allow create rounding statement
            ---- END ----
        """
        company_currency = pos_session.config_id.company_id.currency_id
        company_currency_id = None
        if company_currency:
            company_currency_id = company_currency.id
        pricelist_currency_id = order.pricelist_id.currency_id.id
        pricelist_currency_difference_company_currency = False
        if company_currency_id and company_currency_id != pricelist_currency_id:
            pricelist_currency_difference_company_currency = True
        if not pricelist_currency_difference_company_currency:
            return super(POSOrder, self)._process_payment_lines(pos_order, order, pos_session, draft)
        else:
            order_bank_statement_lines = self.env['pos.payment'].search([('pos_order_id', '=', order.id)])
            order_bank_statement_lines.unlink()
            for payments in pos_order['statement_ids']:
                if payments[2]['amount'] != 0:
                    order.add_payment(self._payment_fields(order, payments[2]))
            order.amount_paid = sum(order.payment_ids.mapped('amount'))
            if (not draft and pos_order['amount_return'] != 0):
                cash_payment_method = pos_session.payment_method_ids.filtered('is_cash_count')[:1]
                if not cash_payment_method:
                    raise UserError(_("No cash statement found for this session. Unable to record returned cash."))
                return_payment_vals = {
                    'name': _('return'),
                    'pos_order_id': order.id,
                    'amount': -pos_order['amount_return'],
                    'payment_date': fields.Date.context_today(self),
                    'payment_method_id': cash_payment_method.id,
                }
                order.add_payment(return_payment_vals)


    def remove_fields_not_existing_order_line(self, orders):
        for o in orders:
            data = o['data']
            if not data.get('partner_id'):
                o['to_invoice'] = False
                o['data']['to_invoice'] = False
            lines = data.get('lines')
            for line_val in lines:
                line = line_val[2]
                new_line = {}
                for key, value in line.items():
                    if key not in self._get_fields_exception():
                        new_line[key] = value
                try:
                    line_val[2] = new_line
                except:
                    _logger.error('remove existing fields for order line fail')
        return orders

    def validate_order_data(self, orders):
        for order in orders:
            order_data = order['data']

            # TODO: double check if return order not negative values
            if order_data.get('is_return_order') == True and order_data.get('return_order_id') and not order_data.get('is_exchange_order'):
                # pos.order
                data_fields = ['amount_paid', 'amount_total', 'amount_tax']
                for data_field in data_fields:
                    if data_field in order_data and order_data[data_field] > 0:
                        order_data[data_field] = -1 * order_data[data_field]

                # pos.order.line
                for line in order['data']['lines']:
                    line = line[2]
                    line_fields = ['qty', 'price_subtotal', 'price_subtotal_incl','discount']
                    for line_field in line_fields:
                        if line_field in line and line[line_field] > 0:
                            line[line_field] = -1 * line[line_field]

                # pos.payment
                for statement in order['data']['statement_ids']:
                    statement = statement[2]
                    statement_fields = ['amount']
                    for statement_field in statement_fields:
                        if statement_field in statement and statement[statement_field] > 0:
                            statement[statement_field] = -1 * statement[statement_field]

            # TODO: Create new Rescue Coupon data if already deleted
            if order_data.get('pos_coupon_id') and order_data.get('is_use_pos_coupon'):
                pos_coupon_id = order_data['pos_coupon_id']
                pos_coupon = self.env['pos.coupon'].with_context(active_test=False).search_read([('id','=',pos_coupon_id)], ['id','name'], limit=1)
                if not pos_coupon:
                    coupon_vals = {
                        'name': f'Rescue Coupon (Previous data(ID:{pos_coupon_id}) already deleted)',
                        'sequence_generate_method': 'Manual Input',
                        'reward_type': 'Discount',
                        'type_apply': 'Specific Product',
                        'state': 'expired',
                    }
                    pos_coupon = self.env['pos.coupon'].sudo().create(coupon_vals)
                    pos_coupon_id = pos_coupon.id
                    order_data['pos_coupon_id'] = pos_coupon_id
                    for line in order['data']['lines']:
                        line = line[2]
                        if line.get('pos_coupon_id'):
                            line['pos_coupon_id'] = pos_coupon_id

        return orders

    # OVERRIDE
    @api.model
    def create_from_ui(self, orders, draft=False):
        """ Create and update Orders from the frontend PoS application.

        Create new orders and update orders that are in draft status. If an order already exists with a status
        diferent from 'draft'it will be discareded, otherwise it will be saved to the database. If saved with
        'draft' status the order can be overwritten later by this function.

        :param orders: dictionary with the orders to be created.
        :type orders: dict.
        :param draft: Indicate if the orders are ment to be finalised or temporarily saved.
        :type draft: bool.
        :Returns: list -- list of db-ids for the created and updated orders.
        """

        orders = self.validate_order_data(orders)

        self.remove_fields_not_existing_order_line(orders)

        order_ids = []
        for order in orders:
            existing_order = False
            if 'server_id' in order['data']:
                amount_total = float(order['data']['amount_total'])
                domain_existing_order = ['|', ('id', '=', order['data']['server_id']), ('pos_reference', '=', order['data']['name'])]
                domain_existing_order += [('amount_total','=', amount_total)]
                existing_order = self.env['pos.order'].search(domain_existing_order, limit=1)
            if (existing_order and existing_order.state == 'draft') or not existing_order:
                order_ids.append(self._process_order(order, draft, existing_order))

        ordersSaved = self.env['pos.order'].search_read(domain = [('id', 'in', order_ids)], fields = ['id', 'pos_reference'])
        for order_id in ordersSaved:
            order_list = []
            order_line_list = []
            payment_list = []
            if(order_id.get('id')):
                order = self.browse([order_id.get('id')])
                vals = {}
                vals['lines'] = []
                if hasattr(order[0], 'return_status'):
                    if not order.is_return_order:
                        vals['return_status'] = order.return_status
                        vals['existing'] = False
                        vals['id'] = order.id
                    else:
                        order.return_order_id.return_status = order.return_status
                        vals['existing'] = True
                        vals['id'] = order.id
                        vals['original_order_id'] = order.return_order_id.id
                        vals['return_status'] = order.return_order_id.return_status
                        for line in order.lines:
                            line_vals = {}
                            if line.original_line_id:
                                line_vals['id'] = line.original_line_id.id
                                line_vals['line_qty_returned'] = line.original_line_id.line_qty_returned
                                line_vals['existing'] = True
                            order_line_list.append(line_vals)
                vals['statment_ids'] = [obj.payment_method_id for obj in order.payment_ids]
                vals['name'] = order.name
                vals['amount_total'] = order.amount_total
                vals['amount_return'] = order.amount_return
                vals['amount_paid'] = order.amount_paid
                vals['amount_tax'] = order.amount_tax
                vals['pos_reference'] = order.pos_reference
                vals['state'] = order.state
                vals['session_id'] = order.session_id.id
                vals['date_order'] = order.date_order
                vals['ean13'] = order.ean13
                if order.account_move:
                    vals['invoice_id'] = order.account_move.id
                else:
                    vals['invoice_id'] = False
                if order.partner_id:
                    vals['partner_id'] = [order.partner_id.id, order.partner_id.name]
                else:
                    vals['partner_id'] = False
                if (not hasattr(order[0], 'return_status') or (hasattr(order[0], 'return_status') and not order.is_return_order)):
                    vals['id'] = order.id
                    for line in order.lines:
                        vals['lines'].append(line.id)
                        line_vals = {}
                        # LINE DATAA
                        line_vals['create_date'] = line.create_date
                        line_vals['discount'] = line.discount
                        line_vals['display_name'] = line.display_name
                        line_vals['id'] = line.id
                        line_vals['order_id'] = [line.order_id.id, line.order_id.name]
                        line_vals['price_subtotal'] = line.price_subtotal
                        line_vals['price_subtotal_incl'] = line.price_subtotal_incl
                        line_vals['price_unit'] = line.price_unit
                        line_vals['product_id'] = [line.product_id.id, line.product_id.name]
                        line_vals['qty'] = line.qty
                        line_vals['write_date'] = line.write_date
                        if hasattr(line, 'line_qty_returned'):
                            line_vals['line_qty_returned'] = line.line_qty_returned
                        # LINE DATAA
                        order_line_list.append(line_vals)
                    for payment_id in order.payment_ids:
                        payment_vals = {}
                        # STATEMENT DATAA
                        payment_vals['amount'] = payment_id.amount
                        payment_vals['id'] = payment_id.id
                        if payment_id.payment_method_id:
                            currency = payment_id.payment_method_id.company_id.currency_id
                            payment_vals['journal_id'] = [payment_id.payment_method_id.id, payment_id.payment_method_id.name + " (" +currency.name+")"]
                        else:
                            payment_vals['journal_id'] = False
                        payment_list.append(payment_vals)
                order_list.append(vals)
            order_id['orders'] = order_list
            order_id['orderlines'] = order_line_list
            order_id['payments'] = payment_list

        ordersSavedData = self.rebuid_orders_response_back_to_pos(ordersSaved)
        _logger.info('%s [create_from_ui] %s' % (self.env.user.login, ordersSavedData))
        return ordersSavedData

    def rebuid_orders_response_back_to_pos(self, orders):
        for order_value in orders:
            order_value['order_fields_extend'] = {}
            order_value['included_order_fields_extend'] = False
            order_value['delivery_fields_extend'] = {}
            order_value['included_delivery_fields_extend'] = False
            order_value['invoice_fields_extend'] = {}
            order_value['included_invoice_fields_extend'] = False
        return orders 

    def create_picking_dynamic_combo_items(self, combo_item_dict):
        if combo_item_dict:
            wareHouseObject = self.env['stock.warehouse']
            stockMoveObject = self.env['stock.move']
            moves = stockMoveObject
            stockPickingObject = self.env['stock.picking']
            picking_type = self.picking_type_id
            location_id = self.location_id.id
            if self.partner_id:
                destination_id = self.partner_id.property_stock_customer.id
            else:
                if (not picking_type) or (not picking_type.default_location_dest_id):
                    customerloc, supplierloc = wareHouseObject._get_partner_locations()
                    destination_id = customerloc.id
                else:
                    destination_id = picking_type.default_location_dest_id.id
            is_return = self.is_return
            picking_vals = {
                'is_picking_combo': True,
                'user_id': False,
                'origin': self.pos_reference,
                'partner_id': self.partner_id.id if self.partner_id else None,
                'date_done': self.date_order,
                'picking_type_id': picking_type.id,
                'company_id': self.company_id.id,
                'move_type': 'direct',
                'note': self.note or "",
                'location_id': location_id if not is_return else destination_id,
                'location_dest_id': destination_id if not is_return else location_id,
                'pos_order_id': self.id,
            }
            picking_combo = stockPickingObject.create(picking_vals)
            for product_id, quantity in combo_item_dict.items():
                product = self.env['product.product'].browse(product_id)
                vals = {
                    'name': self.name,
                    'product_uom': product.uom_id.id,
                    'picking_id': picking_combo.id,
                    'picking_type_id': picking_type.id,
                    'product_id': product_id,
                    'product_uom_qty': quantity,
                    'state': 'draft',
                    'location_id': location_id if not is_return else destination_id,
                    'location_dest_id': destination_id if not is_return else location_id,
                }
                move = stockMoveObject.create(vals)
                moves |= move
            picking_combo.action_assign()
            for move in picking_combo.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
            picking_combo.button_validate()
        return True

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        payment_fields = super(POSOrder, self)._payment_fields(order, ui_paymentline)
        if ui_paymentline.get('voucher_id', None):
            payment_fields['voucher_id'] = ui_paymentline.get('voucher_id')
        if ui_paymentline.get('ref', None):
            payment_fields['ref'] = ui_paymentline.get('ref')
        if ui_paymentline.get('cheque_owner', None):
            payment_fields['cheque_owner'] = ui_paymentline.get('cheque_owner')
        if ui_paymentline.get('cheque_bank_account', None):
            payment_fields['cheque_bank_account'] = ui_paymentline.get('cheque_bank_account')
        if ui_paymentline.get('cheque_bank_id', None):
            payment_fields['cheque_bank_id'] = ui_paymentline.get('cheque_bank_id')
        if ui_paymentline.get('cheque_check_number', None):
            payment_fields['cheque_check_number'] = ui_paymentline.get('cheque_check_number')
        if ui_paymentline.get('cheque_card_name', None):
            payment_fields['cheque_card_name'] = ui_paymentline.get('cheque_card_name')
        if ui_paymentline.get('cheque_card_number', None):
            payment_fields['cheque_card_number'] = ui_paymentline.get('cheque_card_number')
        if ui_paymentline.get('cheque_card_type', None):
            payment_fields['cheque_card_type'] = ui_paymentline.get('cheque_card_type')
        if ui_paymentline.get('mdr_payment_card_id', None):
            payment_fields['payment_card_id'] = ui_paymentline.get('mdr_payment_card_id')
        if ui_paymentline.get('payment_mdr_id', None):
            payment_fields['payment_mdr_id'] = ui_paymentline.get('payment_mdr_id')
        if ui_paymentline.get('card_payment_number', None):
            payment_fields['card_payment_number'] = ui_paymentline.get('card_payment_number')
        if ui_paymentline.get('mdr_amount', None):
            payment_fields['mdr_amount'] = ui_paymentline.get('mdr_amount')
        if ui_paymentline.get('mdr_paid_by', None):
            payment_fields['mdr_paid_by'] = ui_paymentline.get('mdr_paid_by')
        return payment_fields





    @api.model
    def product_summary_report(self, vals):
        result = {
            'product_summary': {},
            'category_summary': {},
            'payment_summary': {},
            'location_summary': {},
        }
        if not vals:
            return result
        else:
            product_summary_dict = {}
            category_summary_dict = {}
            payment_summary_dict = {}
            location_summary_dict = {}
            product_qty = 0
            location_qty = 0
            category_qty = 0
            payment = 0
            if vals.get('session_id'):
                orders = self.sudo().search([('session_id', '=', vals.get('session_id'))])
            else:
                orders = self.sudo().search([
                    ('date_order', '>=', vals.get('from_date')),
                    ('date_order', '<=', vals.get('to_date')),
                    ('company_id', '=', self.env.user.company_id.id)
                ])
            location_list = []
            for each_order in orders:
                if 'location_summary' in vals.get('summary', []) or len(vals.get('summary')) == 0:
                    for picking in each_order.picking_ids:
                        if not location_summary_dict.get(picking.location_id.name, None):
                            location_summary_dict[picking.location_id.name] = {}
                for each_order_line in each_order.lines:
                    if 'product_summary' in vals.get('summary', []) or len(vals.get('summary')) == 0:
                        if not product_summary_dict.get(each_order_line.product_id.id, None):
                            product_summary_dict[each_order_line.product_id.id] = {
                                'name': each_order_line.product_id.name,
                                'quantity':0
                            }
                        product_summary_dict[each_order_line.product_id.id]['quantity'] += each_order_line.qty
                    if 'category_summary' in vals.get('summary', []) or len(vals.get('summary')) == 0:
                        if each_order_line.product_id.pos_categ_id.name in category_summary_dict:
                            category_qty = category_summary_dict[each_order_line.product_id.pos_categ_id.name]
                            category_qty += each_order_line.qty
                        else:
                            category_qty = each_order_line.qty
                        category_summary_dict[each_order_line.product_id.pos_categ_id.name] = category_qty;
                    if 'payment_summary' in vals.get('summary', []) or len(vals.get('summary')) == 0:
                        for payment in each_order.payment_ids:
                            if not payment_summary_dict.get(payment.payment_method_id.name, None):
                                payment_summary_dict[payment.payment_method_id.name] = 0
                            payment_summary_dict[payment.payment_method_id.name] += payment.amount
            if 'location_summary' in vals.get('summary', []) or len(vals.get('summary')) == 0:
                for each_order in orders:
                    for picking in each_order.picking_ids:
                        for each_order_line in each_order.lines:
                            if each_order_line.product_id.name in location_summary_dict[
                                picking.location_id.name]:
                                location_qty = location_summary_dict[picking.location_id.name][
                                    each_order_line.product_id.name]
                                location_qty += each_order_line.qty
                            else:
                                location_qty = each_order_line.qty
                            location_summary_dict[picking.location_id.name][
                                each_order_line.product_id.name] = location_qty
                location_list.append(location_summary_dict)

            return {
                'product_summary': product_summary_dict,
                'category_summary': category_summary_dict,
                'payment_summary': payment_summary_dict,
                'location_summary': location_summary_dict,
            }

    @api.model
    def payment_summary_report(self, vals={}):
        if not vals.get('summary', None):
            vals['summary'] = 'sales_person'
        journals_detail = {}
        salesmen_detail = {}
        summary_data = {}
        if vals.get('session_id'):
            order_detail = self.sudo().search([('session_id', '=', vals.get('session_id'))])
        else:
            order_detail = self.sudo().search([
                ('date_order', '>=', vals.get('from_date')),
                ('date_order', '<=', vals.get('to_date')),
                ('company_id', '=', self.env.user.company_id.id)
            ])
        if vals.get('summary', None) == 'journals':
            if (order_detail):
                for each_order in order_detail:
                    order_date = each_order.date_order
                    date1 = order_date
                    date1 = date1.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    month_year = datetime.strptime(date1, DEFAULT_SERVER_DATETIME_FORMAT).strftime("%B-%Y")
                    if not month_year in journals_detail:
                        journals_detail[month_year] = {}
                    for payment in each_order.payment_ids:
                        if not journals_detail[month_year].get(payment.payment_method_id.name, None):
                            journals_detail[month_year][payment.payment_method_id.name] = payment.amount
                        else:
                            journals_detail[month_year][payment.payment_method_id.name] += payment.amount
                for journal in journals_detail.values():
                    for i in journal:
                        if i in summary_data:
                            total = journal[i] + summary_data[i]
                        else:
                            total = journal[i]
                        summary_data[i] = float(format(total, '2f'));

        if vals.get('summary', None) == 'sales_person':
            if (order_detail):
                for each_order in order_detail:
                    order_date = each_order.date_order
                    date1 = order_date
                    date1 = date1.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    month_year = datetime.strptime(date1, DEFAULT_SERVER_DATETIME_FORMAT).strftime("%B-%Y")
                    if not salesmen_detail.get(each_order.user_id.name, {}):
                        salesmen_detail[each_order.user_id.name] = {}
                    if not salesmen_detail[each_order.user_id.name].get(month_year, {}):
                        salesmen_detail[each_order.user_id.name][month_year] = {}
                    for payment in each_order.payment_ids:
                        if not salesmen_detail[each_order.user_id.name][month_year].get(payment.payment_method_id.name,
                                                                                        None):
                            salesmen_detail[each_order.user_id.name][month_year][payment.payment_method_id.name] = 0
                        salesmen_detail[each_order.user_id.name][month_year][
                            payment.payment_method_id.name] += payment.amount

        return {
            'journal_details': journals_detail,
            'salesmen_details': salesmen_detail,
            'summary_data': summary_data
        }

    @api.model
    def order_summary_report(self, vals):
        _logger.info(vals)
        order_list = {}
        category_list = {}
        payment_list = {}
        if vals:
            orders = []
            if vals.get('session_id'):
                orders = self.sudo().search([
                    ('session_id', '=', vals.get('session_id'))
                ])
            else:
                orders = self.sudo().search([
                    ('date_order', '>=', vals.get('from_date')),
                    ('date_order', '<=', vals.get('to_date')),
                    ('company_id', '=', self.env.user.company_id.id)
                ])

            if ('order_summary_report' in vals['summary'] or len(vals['summary']) == 0):
                for each_order in orders:
                    order_list[each_order.state] = []
                for each_order in orders:
                    if each_order.state in order_list:
                        order_list[each_order.state].append({
                            'order_ref': each_order.name,
                            'order_date': each_order.date_order,
                            'total': float(format(each_order.amount_total, '.2f'))
                        })
                    else:
                        order_list.update({
                            each_order.state.append({
                                'order_ref': each_order.name,
                                'order_date': each_order.date_order,
                                'total': float(format(each_order.amount_total, '.2f'))
                            })
                        })
            if ('category_summary_report' in vals['summary'] or len(vals['summary']) == 0):
                count = 0.00
                amount = 0.00
                for each_order in orders:
                    category_list[each_order.state] = {}
                for each_order in orders:
                    for order_line in each_order.lines:
                        if each_order.state == 'paid':
                            if order_line.product_id.pos_categ_id.name in category_list[each_order.state]:
                                count = category_list[each_order.state][order_line.product_id.pos_categ_id.name][0]
                                amount = category_list[each_order.state][order_line.product_id.pos_categ_id.name][1]
                                count += order_line.qty
                                amount += order_line.price_subtotal_incl
                            else:
                                count = order_line.qty
                                amount = order_line.price_subtotal_incl
                        if each_order.state == 'done':
                            if order_line.product_id.pos_categ_id.name in category_list[each_order.state]:
                                count = category_list[each_order.state][order_line.product_id.pos_categ_id.name][0]
                                amount = category_list[each_order.state][order_line.product_id.pos_categ_id.name][1]
                                count += order_line.qty
                                amount += order_line.price_subtotal_incl
                            else:
                                count = order_line.qty
                                amount = order_line.price_subtotal_incl
                        if each_order.state == 'invoiced':
                            if order_line.product_id.pos_categ_id.name in category_list[each_order.state]:
                                count = category_list[each_order.state][order_line.product_id.pos_categ_id.name][0]
                                amount = category_list[each_order.state][order_line.product_id.pos_categ_id.name][1]
                                count += order_line.qty
                                amount += order_line.price_subtotal_incl
                            else:
                                count = order_line.qty
                                amount = order_line.price_subtotal_incl
                        category_list[each_order.state].update(
                            {order_line.product_id.pos_categ_id.name: [count, amount]})
                    if (False in category_list[each_order.state]):
                        category_list[each_order.state]['others'] = category_list[each_order.state].pop(False)

            if ('payment_summary_report' in vals['summary'] or len(vals['summary']) == 0):
                for each_order in orders:
                    if not payment_list.get(each_order.state, None):
                        payment_list[each_order.state] = {}
                    for payment in each_order.payment_ids:
                        if not payment_list[each_order.state].get(payment.payment_method_id.name, None):
                            payment_list[each_order.state][payment.payment_method_id.name] = 0
                        payment_list[each_order.state][payment.payment_method_id.name] += payment.amount
            return {
                'order_report': order_list,
                'category_report': category_list,
                'payment_report': payment_list,
                'state': vals['state']
            }

    def _compute_is_show_pos_payment(self):
        for rec in self:
            is_show = False
            if rec.amount_paid < rec.amount_total:
                is_show = True
            rec.is_show_pos_payment = is_show

    def action_open_invoice_register_payment(self):
        self.ensure_one()
        domain = [('state','=', 'posted'), ('pos_order_id','=', self.id)]
        move = self.env['account.move'].sudo().search(domain)
        if len(move) != 1:
            return self.action_view_receivable_invoices()
        
        context = {
            'active_model': 'account.move',
            'active_ids': [move.id],
            'active_id': move.id,
            'ctx_pos_payment': True,
        }
        for payment in self.payment_ids:
            if payment.payment_method_id.is_receivables:
                journal_id = payment.payment_method_id.account_journal_id
                if journal_id:
                    context['default_journal_id'] = journal_id.id
                break

        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': context,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }


    def _prepare_void_order_payment_vals(self, order, payment):
        values = {
            'amount': -1 * payment.amount, 
            'payment_date': payment.payment_date, 
            'payment_method_id': payment.payment_method_id.id, 
            'card_type': payment.card_type, 
            'cardholder_name': payment.cardholder_name, 
            'transaction_id': payment.transaction_id, # field type char
            'payment_status': payment.payment_status, 
            'pos_order_id': order.id, 
            'payment_card_id': payment.payment_card_id and payment.payment_card_id.id or False, 
            'customer_deposit_id': payment.payment_card_id and payment.payment_card_id.id or False, 
            'pos_branch_id': payment.payment_card_id and payment.payment_card_id.id or False
        }
        return values

    def _prepare_void_order_line_vals(self, order, line):
        values = {
            'is_return': True, 
            'returned_order_line_id': line.id, 
            'qty': -1 * line.qty, 
            'price_unit': line.price_unit, 
            'price_subtotal': -1 * line.price_subtotal, 
            'price_subtotal_incl': -1 * line.price_subtotal_incl, 
            'discount': -1 * line.discount, 
            'discount_amount_percent': -1 * line.discount_amount_percent, 
            'product_id': line.product_id and line.product_id.id or False, 
            'tax_ids': [ [6, False, [x]] for x in line.tax_ids.ids ], 
            'full_product_name': line.product_id and line.product_id.display_name or '', 
            'price_extra': -1 * line.price_extra, 
            'note': line.note,
        }
        return values

    def _prepare_void_order_vals(self, order, vals):
        self.ensure_one()
        values = {
            'is_return': True,
            'name': '/',
            'ean13': vals['ean13'], 
            'pos_reference': 'VOID/' + order.name,
            'return_order_id': order.id,
            'void_order_id': order.id,
            'void_state': 'Void',

            'cron_picking': True, # Create picking via cron
            'location_id': False, # Location will auto change when picking created

            'crm_team_id': order.crm_team_id and order.crm_team_id.id or False, 
            'cashier_id': order.cashier_id and order.cashier_id.id or False, 
            'user_id': order.user_id and order.user_id.id or False, 
            'picking_type_id': order.picking_type_id and order.picking_type_id.id or False, 
            'payment_journal_id': order.payment_journal_id and order.payment_journal_id.id or False, 
            'fiscal_position_id': order.fiscal_position_id and order.fiscal_position_id.id or False,
            'session_id': order.session_id and order.session_id.id or False, 
            'partner_id': order.partner_id and order.partner_id.id or False, 
            'employee_id': order.employee_id and order.employee_id.id or False, 
            'company_id': order.company_id and order.company_id.id or False, 
            'pos_branch_id': order.pos_branch_id and order.pos_branch_id.id or False, 
            'sequence_number': order.sequence_number, 
            'date_order': fields.Datetime.now(), 

            'currency_id': order.currency_id and order.currency_id.id or False, 
            'pricelist_id': order.pricelist_id and order.pricelist_id.id or False, 
            'amount_paid': -1 * order.amount_paid, 
            'amount_total': -1 * order.amount_total, 
            'amount_tax': -1 * order.amount_tax, 
            'amount_return': order.amount_return, 
            'rounding_payment': -1 * order.rounding_payment,

            'to_invoice': order.to_invoice, 
            'is_tipped': order.is_tipped, 
            'tip_amount': order.tip_amount, 
            'is_exchange_order': order.is_exchange_order, 
            'exchange_amount': order.exchange_amount, 
            'total_mdr_amount_customer': order.total_mdr_amount_customer, 
            'total_mdr_amount_company': order.total_mdr_amount_company, 

            'table_id': order.table_id and order.table_id.id or False, 
            'customer_count': order.customer_count, 
            'multiprint_resume': order.multiprint_resume, 
            'is_multiple_warehouse': order.is_multiple_warehouse,
        }

        lines = []
        for line in order.lines:
            lines += [[0, 0, self._prepare_void_order_line_vals(order, line)]]
        values['lines'] = lines

        payments = []
        for payment in order.payment_ids:
            payments += [[0, 0, self._prepare_void_order_payment_vals(order, payment)]]
        values['payment_ids'] = payments

        return values

    def void_order_create_line_details(self):
        # Self (pos.order)
        self.ensure_one()
        return self

    def create_void_order(self, vals):
        self.ensure_one()

        existing = self.env['pos.order'].search([('void_order_id','=', self.id)], limit=1)
        if existing:
            return {
                'status': 'failed',
                'error_message': 'This order is already void!'
            }

        values = self._prepare_void_order_vals(self, vals)
        void_order = self.env['pos.order'].create(values)
        void_order.void_order_create_line_details()

        if void_order.return_order_id:
            void_order.return_order_id.write({'is_returned': True})

        try:
            void_order.action_pos_order_paid()
        except psycopg2.DatabaseError:
            # do not hide transactional errors, the order(s) won't be saved!
            raise
        except Exception as e:
            _logger.error('Could not fully process the POS Order: %s', tools.ustr(e))

        return {
            'status': 'success',
            'void_order_id': void_order.id,
        }


class POSOrderLine(models.Model):
    _inherit = "pos.order.line"

    picking_type_id = fields.Many2one('stock.picking.type', string='Operation Type')
    partner_id = fields.Many2one(
        'res.partner',
        related='order_id.partner_id',
        string='Partner',
        readonly=1)
    is_return = fields.Boolean('Is Return')
    order_uid = fields.Text('order_uid', readonly=1)
    user_id = fields.Many2one('res.users', 'Sale Person')
    session_info = fields.Text('session_info', readonly=1)
    uid = fields.Text('uid', readonly=1)
    # variant_ids = fields.Many2many(
    #     'product.variant',
    #     'order_line_variant_rel',
    #     'line_id', 'variant_id',
    #     string='Variant Items', readonly=1)
    tag_ids = fields.Many2many(
        'pos.tag',
        'pos_order_line_tag_rel',
        'line_id',
        'tag_id',
        string='Tags / Reasons Return')
    note = fields.Text('Note')
    discount_reason = fields.Char('Discount Reason')
    margin = fields.Float(
        'Margin',
        compute='_compute_multi_margin',
        store=True
    )
    margin_percent = fields.Float(
        'Margin %',
        compute='_compute_multi_margin',
        store=True
    )
    purchase_price = fields.Float(
        'Cost Price',
        compute='_compute_multi_margin',
        store=True
    )
    config_id = fields.Many2one(
        'pos.config',
        related='order_id.session_id.config_id',
        string="Point of Sale")
    pos_branch_id = fields.Many2one(
        'res.branch',
        related='order_id.pos_branch_id',
        string='Branch',
        readonly=1,
        index=True,
        store=True)
    manager_user_id = fields.Many2one('res.users', 'Manager Approved')
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        related='order_id.analytic_account_id',
        store=True,
        readonly=1,
        string='Analytic Account'
    )
    returned_qty = fields.Float('Returned Qty')
    returned_order_line_id = fields.Many2one('pos.order.line', 'Returned from Line')
    uom_id = fields.Many2one('uom.uom', 'Sale Uom', readonly=1)
    product_uom_id = fields.Many2one('uom.uom', string='Product UoM', related=None)
    is_shipping_cost = fields.Boolean('Shipping Cost')
    order_time = fields.Char('Order Time')
    price_extra = fields.Float('Discount Value')
    not_returnable = fields.Boolean('Not Returnable', related="product_id.not_returnable", store=True)
    returnable_by_categories = fields.Boolean('Not Returnable', compute="_compute_allowed_categories", store=True, default=True)

    line_qty_returned = fields.Integer('Line Returned', default=0)
    original_line_id = fields.Many2one('pos.order.line', "Original line")
    last_supplier_id = fields.Many2one("res.partner", string="Vendor",related='product_id.last_supplier_id',store=True)
    is_done_self_pickup = fields.Boolean('Done Self Pickup',copy=False)


    @api.depends('config_id.pos_allowed_return_category_ids')
    def _compute_allowed_categories(self):
        for line in self:
            if line.config_id.pos_allowed_return_category_ids:
                if line.product_id.pos_categ_id not in line.config_id.pos_allowed_return_category_ids:
                    line.returnable_by_categories = False
                else:
                    line.returnable_by_categories = True
            else:
                line.returnable_by_categories = True

    item_state = fields.Selection(
        [('ordered', 'Ordered'),('cancelled', 'Cancelled')],
        string='Item State',
        required=1,
        default='ordered'
    )
    is_complementary = fields.Boolean(string="Complementary")
    
    note = fields.Char('Note')
    mp_skip = fields.Boolean('Skip line when sending ticket to kitchen printers.')


    def _export_for_ui(self, orderline):
        res = super(POSOrderLine, self)._export_for_ui()
        res.update({
            'cashier_id': orderline.cashier_id.id,
            'void_order_id': orderline.void_order_id.id,
            'void_state': orderline.void_state,
            'is_complementary': orderline.is_complementary,
        }) 

    def getProductRecommendations(self, product_id=None, product_recommendation_number=10):
        OrderLines = self.search([('product_id', '=', product_id)], limit=product_recommendation_number,order='create_date DESC')
        OrderIds = []
        ProductIds = []
        for line in OrderLines:
            if line.id not in OrderIds:
                OrderIds.append(line.order_id.id)
        OrderLines = self.search([('product_id', '!=', product_id), ('order_id', 'in', OrderIds)], limit=product_recommendation_number, order='create_date DESC')
        for line in OrderLines:
            if line.product_id.id not in ProductIds:
                ProductIds.append(line.product_id.id)
            if len(ProductIds) >= product_recommendation_number:
                break
        return ProductIds

    @api.depends('product_id', 'qty', 'price_subtotal', 'order_id.note')
    def _compute_multi_margin(self):
        for line in self:
            if line.qty <= 0:
                continue
            if line.price_subtotal <= 0:
                line.purchase_price = 0
                line.margin = 0
                line.margin_percent = 0
                continue
            if not line.product_id:
                line.purchase_price = 0
                line.margin = 0
                line.margin_percent = 0
            else:
                line.purchase_price = line.product_id.standard_price
                line.margin = line.price_subtotal - (
                        line.product_id.standard_price * line.qty)
                if line.product_id.standard_price <= 0:
                    line.margin_percent = 100
                else:
                    line.margin_percent = (line.price_subtotal / line.qty - line.product_id.standard_price) / line.product_id.standard_price * 100

    def _order_line_fields(self, line, session_id=None):
        values = super(POSOrderLine, self)._order_line_fields(line, session_id)
        
        if line[2].get('combo_item_ids', []):
            values[2].update({'combo_item_ids': line[2].get('combo_item_ids', [])})
        if line[2].get('selected_combo_items', []):
            values[2].update({'selected_combo_items': line[2].get('selected_combo_items', [])})
        if line[2].get('voucher', None):
            values[2].update({'voucher': line[2].get('voucher', [])})
        if line[2].get('is_shipping_cost', False):
            values[2].update({'is_shipping_cost': line[2].get('is_shipping_cost', False)})
        if line[2].get('price_extra', None):
            values[2].update({'price_extra': line[2].get('price_extra', 0)})
        if line[2].get('line_qty_returned'):
            values[2].update({'line_qty_returned': line[2].get('line_qty_returned', 0)})
        if line[2].get('original_line_id'):
            values[2].update({'original_line_id': int(line[2]['original_line_id']) })
        if line[2].get('picking_type_id', []):
            values[2].update({'picking_type_id': line[2].get('picking_type_id', False)})

        return values

    # TODO: cashier add voucher variable to each line, backend automatic create voucher
    def _add_voucher(self, order, voucher_vals=[]):
        today = datetime.today()
        if voucher_vals.get('period_days', None):
            end_date = today + timedelta(days=int(voucher_vals['period_days']))
        else:
            end_date = today + timedelta(days=order.config_id.expired_days_voucher)
        self.env['pos.voucher'].sudo().create({
            'number': voucher_vals.get('number', None) if voucher_vals.get('number', None) else '',
            'customer_id': voucher_vals.get('customer_id', None) if voucher_vals.get('customer_id', None) else None,
            'start_date': fields.Datetime.now(),
            'end_date': end_date,
            'state': 'active',
            'value': voucher_vals['value'],
            'apply_type': voucher_vals.get('apply_type', None) if voucher_vals.get('apply_type', None) else 'fixed_amount',
            'method': voucher_vals.get('method', None) if voucher_vals.get('method', None) else 'general',
            'source': order.name,
            'pos_order_id': order.id,
            'pos_order_line_id': self.id,
            'user_id': self.env.user.id
        })

    @api.model
    def create(self, vals):
        voucher_vals = {}
        if vals.get('voucher', {}):
            voucher_vals = vals.get('voucher')
            del vals['voucher']
        if vals.get('mp_skip', {}):
            del vals['mp_skip']
        if 'voucher' in vals:
            del vals['voucher']
        order = self.env['pos.order'].browse(vals['order_id'])
        if order.booking_id and order.booking_id.state != 'booked':
            order.booking_id.write({
                'pos_order_id': order.id,
                'payment_partial_amount': 0,
                'state': 'booked'
            })
        if order.pos_branch_id:
            vals.update({'pos_branch_id': order.pos_branch_id.id})
        else:
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
        if vals.get('uom_id', None):
            vals.update({'product_uom_id': vals.get('uom_id')})
        else:
            product = self.env['product.product'].browse(vals.get('product_id'))
            vals.update({
                'product_uom_id': product.uom_id.id,
                'uom_id': product.uom_id.id,
            })

        if order.session_id and order.session_id.config_id.zone_id:
            vals.update({'zone_id': order.session_id.config_id.zone_id.id})

        po_line = super(POSOrderLine, self).create(vals)
        if voucher_vals:
            po_line._add_voucher(order, voucher_vals)
        if po_line.returned_order_line_id:
            po_line.returned_order_line_id.write({'returned_qty': po_line.qty})
        return po_line

    def get_purchased_lines_histories_by_partner_id(self, partner_id):
        orders = self.env['pos.order'].sudo().search([('partner_id', '=', partner_id)], order='create_date DESC')
        fields_sale_load = self.env['pos.cache.database'].sudo().get_fields_by_model('pos.order.line')
        vals = []
        if orders:
            order_ids = [order.id for order in orders]
            lines = self.sudo().search([('order_id', 'in', order_ids)])
            return lines.read(fields_sale_load)
        else:
            return vals

    def unlink(self):
        for line in self:
            if line.order_id and line.order_id.state == 'cancel' and line.order_id.removed_user_id and not self.env.user.has_group(
                    'point_of_sale.group_pos_manager'):
                raise UserError(_(
                    "You can not remove this order, only POS Manager can do it"))
        return super(POSOrderLine, self).unlink()
