
from odoo import SUPERUSER_ID, _, api, fields, models, registry
from collections import defaultdict
from odoo.exceptions import UserError , ValidationError
from datetime import datetime, date, timedelta
from odoo.tools import float_compare, frozendict, split_every
from dateutil import relativedelta
from itertools import groupby
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from json import dumps
from psycopg2 import OperationalError
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.osv import expression
from math import floor
# from dateutil.relativedelta import relativedelta
import calendar


# class PurchaseOrder(models.Model):
#     _inherit = "purchase.order"

#     name = fields.Char(required=True)

# class StockWarehouseOrderpoint(models.Model):
#     _inherit = "material.request"

#     @api.onchange('branch_id')
#     def _onchange_analytic_account_group_ids(self):
#         if self.branch_id:
#             self.analytic_account_group_ids = [(6, 0, self.branch_id.analytic_tag_ids.ids)]
#         else:
#             self.analytic_account_group_ids = [(6, 0, list())]


class StockWarehouseOrderpoint(models.Model):
    _name = "stock.warehouse.orderpoint"
    _inherit = ['portal.mixin', 'mail.thread', 'stock.warehouse.orderpoint', 'mail.activity.mixin', 'utm.mixin']
    
    def _domain_partner(self):
        return [('company_id','=',self.env.company.id),('is_vendor','=',True)]

    location_id = fields.Many2one(required=False)
    name = fields.Char(default='New')
    source_location_id = fields.Many2one('stock.location', string="Source Location", tracking=True)
    action_to_take = fields.Selection([
                    ('no_action', 'No Action'),
                    ('create_pr', 'Create Purchase Request'),
                    ('create_rfq', 'Create Request For Quotation'),
                    ('create_itr', 'Create Internal Transfer Request'),
                    ('create_mr', 'Create Material Request')
    ], default='no_action')
    trigger = fields.Selection(default='manual', tracking=True)
    start_date = fields.Selection([
                    ('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5'),('6', '6'),('7', '7'),('8', '8'),('9', '9'),('10', '10'),
                    ('11', '11'),('12', '12'),('13', '13'),('14', '14'),('15', '15'),('16', '16'),('17', '17'),('18', '18'),('19', '19'),('20', '20'),
                    ('21', '21'),('22', '22'),('23', '23'),('24', '24'),('25', '25'),('26', '26'),('27', '27'),('28', '28'),('29', '29'),('30', '30'),
                    ('31','31')],string='Start Date', tracking=True)
    start_month = fields.Selection([
                    ('1','January'),('2','February'),('3','March'),('4','April'),('5','May'),('6','June'),
                    ('7','July'),('8','August'),('9','September'),('10','October'),('11','November'),('12','December')],string='Start Month', tracking=True)
    end_date = fields.Selection([
                    ('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5'),('6', '6'),('7', '7'),('8', '8'),('9', '9'),('10', '10'),
                    ('11', '11'),('12', '12'),('13', '13'),('14', '14'),('15', '15'),('16', '16'),('17', '17'),('18', '18'),('19', '19'),('20', '20'),
                    ('21', '21'),('22', '22'),('23', '23'),('24', '24'),('25', '25'),('26', '26'),('27', '27'),('28', '28'),('29', '29'),('30', '30'),
                    ('31','31')],string='End Date', tracking=True)
    end_month = fields.Selection([
                    ('1','January'),('2','February'),('3','March'),('4','April'),('5','May'),('6','June'),
                    ('7','July'),('8','August'),('9','September'),('10','October'),('11','November'),('12','December')],string='End Month', tracking=True)

    is_replenish_document_created = fields.Boolean(string="Replenish Document Created?", tracking=True)
    purchase_request_id = fields.Many2one('purchase.request', string="Purchase Request Reference", tracking=True)
    purchase_order_id = fields.Many2one('purchase.order', string="Request for Quotation Reference", tracking=True)
    material_request_id = fields.Many2one('material.request', string="Material Request Reference", tracking=True)
    internal_transfer_id = fields.Many2one('internal.transfer', string="Internal Transfer Request Reference", tracking=True)
    replenish_document_status = fields.Char(string="Replenish Document Status", tracking=True)
    is_mo_created = fields.Boolean(string='Is MO Created')
    periods = fields.Char(string="Active On Period", tracking=True)
    run_rate_days = fields.Integer(string="Run Rate Days", tracking=True)
    safety_stock = fields.Float(string="Safety Stock", tracking=True)
    safety_stock_select = fields.Selection([('fix_qty', 'Fixed Quantity'), ('percentage', 'Percentage')], default="fix_qty", tracking=True, string="Safety Stock Type")
    stock_days = fields.Float(string="Stock Days", tracking=True)
    responsible_id = fields.Many2many('res.users', 'res_user_order_point_rel', 'user_id', 'order_point_id', string="Responsible", tracking=True)
    branch_id = fields.Many2one('res.branch', string="Branch", related="warehouse_id.branch_id", tracking=True)

    average_quantity_last_year = fields.Float(string="Average Quantity Last Year", compute='_compute_average_quantity_last_year', store=False)
    lead_days_last_year = fields.Float(string="Lead Days Last Year", compute='_compute_average_quantity_last_year', store=False)
    average_quantity_run_rate_days = fields.Float(string="Average Quantity Run Rate Days", compute="_compute_average_quantity_run_rate_days", store=False)
    lead_days_run_rate_days = fields.Float(string="Lead Days Run Rate Days", compute="_compute_average_quantity_run_rate_days", store=False)
    run_rate_type = fields.Selection([
                                    ('get_last_year', 'Last Year Period'),
                                    ('get_past_days_data', 'Current Period'),
                                    ], default='get_last_year')

    company_id = fields.Many2one(default=lambda self:self.env.company.id, readonly=True)
    warehouse_id = fields.Many2one(domain="[('company_id', '=', company_id)]")
    filter_warehouse_id = fields.Many2many('stock.location', compute="_compute_warehouse", string="Allowed Locations")

    is_minimum_quantity = fields.Boolean(string="Minimum Quantity Based On Past Stock Demand")
    is_safety_stock_quantity = fields.Boolean(string="Safety Stock Quantity For Replenishment")
    select_period = fields.Char(string='Choose Period', default='active')
    notification_user_ids = fields.Many2many('res.users', string="Notification send to")
    pr_status = fields.Selection(related="purchase_request_id.state", string="Purchase Request Status")
    rfq_status = fields.Selection(related="purchase_order_id.state", string="Request for Quotation Status")
    itr_status = fields.Selection(related="internal_transfer_id.state", string="Internal Transfer Request Status")
    mr_status = fields.Selection(related="material_request_id.status", string="Material Request Status")
    from_days_before = fields.Date(string="From Days Before")
    run_rate_qty = fields.Float(string="Run Rate Quantity")
    lead_days = fields.Float(string="Lead Days")

    period_date = fields.Selection([
                    ('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5'),('6', '6'),('7', '7'),('8', '8'),('9', '9'),('10', '10'),
                    ('11', '11'),('12', '12'),('13', '13'),('14', '14'),('15', '15'),('16', '16'),('17', '17'),('18', '18'),('19', '19'),('20', '20'),
                    ('21', '21'),('22', '22'),('23', '23'),('24', '24'),('25', '25'),('26', '26'),('27', '27'),('28', '28'),('29', '29'),('30', '30'),
                    ('31','31')],string='Period Date', tracking=True)
    period_month = fields.Selection([
                    ('1','January'),('2','February'),('3','March'),('4','April'),('5','May'),('6','June'),
                    ('7','July'),('8','August'),('9','September'),('10','October'),('11','November'),('12','December')],string='Period Month', tracking=True)
    run_rate_period_before = fields.Float(string="Run Rate Period Before", tracking=True)
    run_rate_period_after = fields.Float(string="Run Rate Period After", tracking=True)
    qty_check = fields.Boolean()
    is_low_stock = fields.Boolean(string="Is Low Stock")
    path = fields.Char(string="Path To A Document")
    quantity_restock = fields.Boolean(compute="_compute_qty_restock",inverse="_after_quantity_restock", string="Quantity Restock")
    is_quantity_restock = fields.Boolean(string="Is Quantity Restock",default=False, store=True)
    qty_restock = fields.Boolean(default=False)
    product_min_qty = fields.Float(
        'Min Quantity', digits="Product Unit Of Measure", required=True, default=0.0,
        help="When the virtual stock equals to or goes below the Min Quantity specified for this field, Hashmicro generates a procurement to bring the forecasted quantity to the Max Quantity."
    )
    product_max_qty = fields.Float(
        'Max Quantity', digits="Product Unit Of Measure", required=True, default=0.0,
        help="When the virtual stock equals to or goes below the Min Quantity specified for this field, Hashmicro generates a procurement to bring the forecasted quantity to the Max Quantity."
    )
    auto_trigger_replenishment = fields.Boolean(string='Auto Trigger Replenishment',tracking=True)
    select_days_trigger = fields.Selection([
                    ('1', '1 Days'),('3', '3 Days'),('7', '7 Days'),('30', '30 Days')],
                    string='Select Days passed to trigger the replenishment',
                    tracking=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', tracking=True, domain=_domain_partner)

    # def _domain_partner(self):
    #     return [('company_id','=',self.env.company.id),('is_vendor','=',True)]
    # supplier_id_new = fields.Many2one('res.partner', string='Vendor', domain=_domain_partner)


    @api.depends('qty_on_hand', 'product_min_qty')
    def _compute_qty_restock(self):
        for x in self:
            if x.qty_on_hand < x.product_min_qty:
                x.write({'is_quantity_restock': True})
            else:
                x.write({'is_quantity_restock': False})

    def _after_quantity_restock(self):
        pass

    def get_last_day_of_month(year, month):
        last_day = calendar.monthrange(year, month)
        return last_day

    def _get_message_for_html(self):
        # end_date = fields.Date.today()
        # start_date = end_date - timedelta(days=7)
        date_history = []
        product_id = ''
        qty_same_date = 0
        value_with_format = []


        product_id = '[' + self.product_id.product_tmpl_id.default_code + ']' + self.product_id.product_tmpl_id.name
        uom_name = self.product_id.product_tmpl_id.uom_id.name

        counter = 0
        for rec in range(0,6):
            if counter == 0:
                end_date = fields.Date.today()
                start_date = end_date.replace(day=1)
                month_name = calendar.month_name[end_date.month]
                # print('end_date',end_date)
                # print('start_date',start_date)
                date_history.append(f"""<td class="text-center" width="100px">
                                            <b>
                                                <span>{month_name}</span>
                                                <span>{end_date.year}</span>
                                            </b>
                                        </td>
                                    """)
            if counter >= 1:
                start_date = start_date - relativedelta.relativedelta(months=1)
                end_date = start_date + relativedelta.relativedelta(day=31)
                month_name = calendar.month_name[end_date.month]
                # print('end_date',end_date)
                # print('start_date',start_date)
                date_history.append(f"""<td class="text-center" width="100px">
                                            <b>
                                                <span>{month_name}</span>
                                                <span>{end_date.year}</span>
                                            </b>
                                        </td>
                                    """)

            purchase_order = self.env['purchase.order'].search([
                                                ('date_approve', '>=', start_date),
                                                ('date_approve', '<=', end_date),
                                                ('state', 'in', ('purchase','done'))
                                                ],order= 'date_approve asc')
            if purchase_order:
                purchase_order_line = self.env['purchase.order.line'].search([
                                                                ('product_id','=', self.product_id.id),
                                                                ('order_id', 'in', purchase_order.ids),
                                                                ('destination_warehouse_id', '=', self.warehouse_id.id)
                                                                ])
                if purchase_order_line:
                    qty_same_date = 0
                    for rec in purchase_order_line:
                        qty_same_date += rec.product_uom_qty
                    value_with_format.append(f"""<td class="text-center" width="100px"><b>{qty_same_date}</b></td>""")
                else:
                    value_with_format.append(f"""<td class="text-center" width="100px"><b>0</b></td>""")
            else:
                #  print('else')
                 value_with_format.append(f"""<td class="text-center" width="100px"><b>0</b></td>""")
            # print('counter')
            counter += 1
        date_history.reverse()
        date_string = ''
        date_string = ' '.join(date_history)
        value_with_format.reverse()
        value_string = ''
        value_string = ' '.join(value_with_format)
        final_history = f"""
                            <h3 style="padding-top: -100px;">Warehouse Name<h3>
                            <h1>{self.warehouse_id.name}</h1>
                            <br/>
                            <br/>
                            <table border=1 style="margin-left: 10px;">
                                <tr style="background-color: #D3D3D3;">
                                    <td width="100px"><b>Product</b></td>{date_string}
                                    <td class="text-center" width="100px"><b>UoM</b></td>
                                </tr>
                                <tr>
                                    <td width="100px"><b>{product_id}</b></td>{value_string}
                                    <td class="text-center" width="100px"><b>{uom_name}</b></td>
                                </tr>
                            </table>
                        """


        # print(final_history)
        return final_history

    def get_history(self):
        msg = self._get_message_for_html()
        ctx = {
            'default_html_field' : msg
        }

        return {
            'name': 'Product History',
            'type': 'ir.actions.act_window',
            'res_model': 'replenishment.history.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context' : ctx
        }

    #     return [('company_id','=',self.env.company.id),('is_vendor','=',True)]
    # supplier_id = fields.Many2one('res.partner', string='Vendor', domain=_domain_partner)

    # def _cron_stock_warehouse_orderpoint_qty(self):
    #     print('testing cron')
    #     stock_orderpoints = self.search([])
    #     for stock_orderpoint in stock_orderpoints:
    #         if stock_orderpoint.qty_on_hand < stock_orderpoint.product_min_qty:
    #             stock_orderpoint.write({'qty_restock': True})
    #         else:
    #             stock_orderpoint.write({'qty_restock': False})


    @api.onchange('product_min_qty', 'product_max_qty')
    def min_qty_validation(self):
        if self.product_max_qty == 0 and self.product_min_qty == 0:
            self.product_max_qty = 1
        if self.product_id:
            if self.product_max_qty <= self.product_min_qty:
                raise ValidationError('The Maximum Quantity cannot be below or equal to Minimum Quantity')

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        self.location_id = False

    def _get_orderpoint_action(self):
        """Create manual orderpoints for missing product in each warehouses. It also removes
        orderpoints that have been replenish. In order to do it:
        - It uses the report.stock.quantity to find missing quantity per product/warehouse
        - It checks if orderpoint already exist to refill this location.
        - It checks if it exists other sources (e.g RFQ) tha refill the warehouse.
        - It creates the orderpoints for missing quantity that were not refill by an upper option.

        return replenish report ir.actions.act_window
        """
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_orderpoint_replenish")
        action['context'] = self.env.context
        # Search also with archived ones to avoid to trigger product_location_check SQL constraints later
        # It means that when there will be a archived orderpoint on a location + product, the replenishment
        # report won't take in account this location + product and it won't create any manual orderpoint
        # In master: the active field should be remove
        # orderpoints = self.env['stock.warehouse.orderpoint'].with_context(active_test=False).search([])
        # Remove previous automatically created orderpoint that has been refilled.
        # to_remove = orderpoints.filtered(lambda o: o.create_uid.id == SUPERUSER_ID and o.qty_to_order <= 0.0 and o.trigger == 'manual')
        # to_remove.unlink()
        # orderpoints = orderpoints - to_remove
        # to_refill = defaultdict(float)
        # all_product_ids = []
        # all_warehouse_ids = []
        # qty_by_product_warehouse = self.env['report.stock.quantity.new'].read_group(
        #     [('date', '=', fields.date.today()), ('state', '=', 'forecast')],
        #     ['product_id', 'product_qty', 'warehouse_id'],
        #     ['product_id', 'warehouse_id'], lazy=False)
        # for group in qty_by_product_warehouse:
        #     warehouse_id = group.get('warehouse_id') and group['warehouse_id'][0]
        #     if group['product_qty'] >= 0.0 or not warehouse_id:
        #         continue
        #     all_product_ids.append(group['product_id'][0])
        #     all_warehouse_ids.append(warehouse_id)
        #     to_refill[(group['product_id'][0], warehouse_id)] = group['product_qty']
        # if not to_refill:
        #     return action

        # Recompute the forecasted quantity for missing product today but at this time
        # with their real lead days.
        # key_to_remove = []

        # group product by lead_days and warehouse in order to read virtual_available
        # in batch
        # pwh_per_day = defaultdict(list)
        # for (product, warehouse), quantity in to_refill.items():
        #     product = self.env['product.product'].browse(product).with_prefetch(all_product_ids)
        #     warehouse = self.env['stock.warehouse'].browse(warehouse).with_prefetch(all_warehouse_ids)
        #     rules = product._get_rules_from_location(warehouse.lot_stock_id)
        #     lead_days = rules.with_context(bypass_delay_description=True)._get_lead_days(product)[0]
        #     pwh_per_day[(lead_days, warehouse)].append(product.id)
        # for (days, warehouse), p_ids in pwh_per_day.items():
        #     products = self.env['product.product'].browse(p_ids)
        #     qties = products.with_context(
        #         warehouse=warehouse.id,
        #         to_date=fields.datetime.now() + relativedelta.relativedelta(days=days)
        #     ).read(['virtual_available'])
        #     for qty in qties:
        #         if float_compare(qty['virtual_available'], 0, precision_rounding=product.uom_id.rounding) >= 0:
        #             key_to_remove.append((qty['id'], warehouse.id))
        #         else:
        #             to_refill[(qty['id'], warehouse.id)] = qty['virtual_available']

        # for key in key_to_remove:
        #     del to_refill[key]
        # if not to_refill:
        #     return action

        # Remove incoming quantity from other origin than moves (e.g RFQ)
        # product_ids, warehouse_ids = zip(*to_refill)
        # dummy, qty_by_product_wh = self.env['product.product'].browse(product_ids)._get_quantity_in_progress(warehouse_ids=warehouse_ids)
        # rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        # Group orderpoint by product-warehouse
        # orderpoint_by_product_warehouse = self.env['stock.warehouse.orderpoint'].read_group(
        #     [('id', 'in', orderpoints.ids)],
        #     ['product_id', 'warehouse_id', 'qty_to_order:sum'],
        #     ['product_id', 'warehouse_id'], lazy=False)
        # orderpoint_by_product_warehouse = {
        #     (record.get('product_id')[0], record.get('warehouse_id')[0]): record.get('qty_to_order')
        #     for record in orderpoint_by_product_warehouse
        # }
        # for (product, warehouse), product_qty in to_refill.items():
        #     qty_in_progress = qty_by_product_wh.get((product, warehouse)) or 0.0
        #     qty_in_progress += orderpoint_by_product_warehouse.get((product, warehouse), 0.0)
            # Add qty to order for other orderpoint under this warehouse.
        #     if not qty_in_progress:
        #         continue
        #     to_refill[(product, warehouse)] = product_qty + qty_in_progress
        # to_refill = {k: v for k, v in to_refill.items() if float_compare(
        #     v, 0.0, precision_digits=rounding) < 0.0}

        # lot_stock_id_by_warehouse = self.env['stock.warehouse'].search_read([
        #     ('id', 'in', [g[1] for g in to_refill.keys()])
        # ], ['lot_stock_id'])
        # lot_stock_id_by_warehouse = {w['id']: w['lot_stock_id'][0] for w in lot_stock_id_by_warehouse}

        # With archived ones to avoid `product_location_check` SQL constraints
        # orderpoint_by_product_location = self.env['stock.warehouse.orderpoint'].with_context(active_test=False).read_group(
        #     [('id', 'in', orderpoints.ids)],
        #     ['product_id', 'location_id', 'ids:array_agg(id)'],
        #     ['product_id', 'location_id'], lazy=False)

        # orderpoint_by_product_location_dict = {}
        # for record in orderpoint_by_product_location:
        #     if record.get('location_id'):
        #         orderpoint_by_product_location_dict.update({
        #             (record.get('product_id')[0], record.get('location_id')[0]): record.get('ids')[0]
        #         })
        #     else:
        #         orderpoint_by_product_location_dict.update({
        #             (record.get('product_id')[0]): record.get('ids')[0]
        #         })
        # orderpoint_by_product_location = orderpoint_by_product_location_dict
        # orderpoint_values_list = []
        # for (product, warehouse), product_qty in to_refill.items():
        #     lot_stock_id = lot_stock_id_by_warehouse[warehouse]
        #     orderpoint_id = orderpoint_by_product_location.get((product, lot_stock_id))
        #     if orderpoint_id:
        #         self.env['stock.warehouse.orderpoint'].browse(orderpoint_id).qty_forecast += product_qty
        #     else:
        #         orderpoint_values = self.env['stock.warehouse.orderpoint']._get_orderpoint_values(product, lot_stock_id)
        #         orderpoint_values.update({
        #             'name': _('Replenishment Report'),
        #             'warehouse_id': warehouse,
        #             'company_id': self.env['stock.warehouse'].browse(warehouse).company_id.id,
        #         })
        #         orderpoint_values_list.append(orderpoint_values)

        # orderpoints = self.env['stock.warehouse.orderpoint'].with_user(SUPERUSER_ID).create(orderpoint_values_list)
        # for orderpoint in orderpoints:
        #     orderpoint.route_id = orderpoint.product_id.route_ids[:1]
        # orderpoints.filtered(lambda o: not o.route_id)._set_default_route_id()
        return action

    @api.onchange('product_id', 'location_id', 'run_rate_qty')
    def _onchange_days(self):
        if self.product_id and self.location_id and self.run_rate_qty > 0:
            stock_quant_ids = self.env['stock.quant'].search([('product_id', '=', self.product_id.id),
                                                              ('location_id', '=', self.location_id.id)
                                                              ])
            available_quantity = sum(stock_quant_ids.mapped('available_quantity'))
            qty = available_quantity / self.run_rate_qty
            self.stock_days = qty

    def set_active_period(self, vals):
        self.start_date = vals.get('start_date')
        self.start_month = vals.get('start_month')
        self.end_date = vals.get('end_date')
        self.end_month = vals.get('end_month')
        if self.start_date and self.start_month and self.end_date and self.end_month:
            start_month = dict(self.fields_get(
                    allfields=['start_month'])['start_month']['selection'])[self.start_month]
            end_month = dict(self.fields_get(
                    allfields=['end_month'])['end_month']['selection'])[self.end_month]
            self.periods = self.start_date + " " + start_month + " " +"-" + " " +self.end_date + " " + end_month
            return self.periods

    @api.onchange('start_date','start_month', 'end_date', 'end_month')
    def _onchange_date(self):
        if self.start_date and self.start_month and self.end_date and self.end_month:
            start_month = dict(self.fields_get(
                    allfields=['start_month'])['start_month']['selection'])[self.start_month]
            end_month = dict(self.fields_get(
                    allfields=['end_month'])['end_month']['selection'])[self.end_month]
            self.periods = self.start_date + " " + start_month + " " +"-" + " " +self.end_date + " " + end_month


    @api.depends('warehouse_id')
    def _compute_warehouse(self):
        for record in self:
            location_ids = []
            if record.warehouse_id:
                location_obj = record.env['stock.location']
                store_location_id = record.warehouse_id.view_location_id.id
                addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_ids.append(location.id)
                child_location_ids = record.env['stock.location'].search([('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                final_location = child_location_ids + location_ids
                record.filter_warehouse_id = [(6, 0, final_location)]
            else:
                record.filter_warehouse_id = [(6, 0, [])]

    @api.depends('product_id', 'warehouse_id', 'run_rate_type',
                'location_id', 'run_rate_period_after',
                'run_rate_period_before')
    def _compute_average_quantity_last_year(self):
        for record in self:
            record.average_quantity_last_year = 0
            record.lead_days_last_year = 0
            if record.run_rate_type == 'get_last_year':
                today_date = datetime.today()
                start_date = today_date.day
                start_month = today_date.month
                year = today_date.year - 1
                if record.location_id:
                    location_ids = record.location_id.ids
                else:
                    location_ids = record.filter_warehouse_id.ids

                try:
                    first_day = date(year, start_month, start_date)
                except ValueError:
                    first_day = date(year, start_month, calendar.monthrange(year, start_month)[1])
                first_day_before = first_day - timedelta(days=record.run_rate_period_before + 1)
                first_day_after = first_day + timedelta(days=record.run_rate_period_after)
                # print('FROM', first_day_before,'- TO', first_day_after)
                move_id = self.env['stock.move'].search([('product_id', '=', record.product_id.id),
                                                        ('date', '>=', first_day_before.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                                        ('date', '<=', first_day_after.strftime('%Y-%m-%d 23:59:59')),
                                                        ('state', '=', 'done'),
                                                        ('location_id', 'in', location_ids),
                                                        ('picking_type_code', 'not in', ('incoming','internal')),
                                                        ])
                # print('MOVE NAME', move_id.mapped('name'))
                lead_move_ids = self.env['stock.move'].search([('product_id', '=', record.product_id.id),
                                                        ('date', '>=', first_day_before.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                                        ('date', '<=', first_day_after.strftime('%Y-%m-%d 23:59:59')),
                                                        ('state', '=', 'done'),
                                                        ('location_dest_id', 'in', location_ids),
                                                        ('picking_type_code', '=', 'incoming')
                                                        ])
                process_time_days = sum(lead_move_ids.mapped('picking_id.transfer_log_activity_ids.process_days'))
                if len(lead_move_ids) > 0:
                    record.lead_days_last_year = process_time_days / len(lead_move_ids)
                qty = sum(move_id.mapped('quantity_done'))
                # print('Qty Stock Move', qty)

                # quantity = 0
                # if start_month >= 1 and start_month:
                #     day = (first_day_after - first_day_before).days
                #     if day > 0:
                #         quantity = qty / day
                # record.average_quantity_last_year = quantity
                if record.run_rate_period_after > 0 and record.run_rate_period_before > 0 and qty > 0:
                    if start_month >= 1 and start_month:
                        quantity = (qty / (record.run_rate_period_before + record.run_rate_period_after + 1))
                    record.average_quantity_last_year = quantity

    @api.depends('product_id', 'warehouse_id',
                'run_rate_type', 'run_rate_days',
                'run_rate_period_before',
                'location_id','run_rate_period_before','run_rate_period_after')
    def _compute_average_quantity_run_rate_days(self):
        for record in self:
            record.average_quantity_run_rate_days = 0
            record.lead_days_run_rate_days = 0
            if record.run_rate_type == 'get_past_days_data':
                today_date = datetime.today()
                start_date = today_date.day + 1
                if record.location_id:
                    location_ids = record.location_id.ids
                else:
                    location_ids = record.filter_warehouse_id.ids
                start_month = today_date.month

                try:
                    date1 = today_date.replace(day=start_date, month=start_month)
                except ValueError as e:
                    _, last_day_of_month = calendar.monthrange(today_date.year, start_month)    
                    date1 = today_date.replace(day=last_day_of_month)
                    
                date2 = date1 - timedelta(days=record.run_rate_period_before + 1)
                # date_from = fields.Date.today() + relativedelta.relativedelta(days=-record.run_rate_period_before)
                date_from = datetime.today() - timedelta(days=record.run_rate_period_before)
                date_to = datetime.today()
                # print('============= CURRENT PERIODE ============')
                # print('FROM', date_from.strftime('%Y-%m-%d 00:01:00'),'- TO', date_to.strftime('%Y-%m-%d 23:59:59'))
                # print('========================================')
                move_id = self.env['stock.move'].search([('product_id', '=', record.product_id.id),
                                                        # ('date', '>=', date2.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                                        # ('date', '<=', date1.strftime('%Y-%m-%d 23:59:59')),
                                                        ('date', '>=', date_from.strftime('%Y-%m-%d 00:01:00')),
                                                        ('date', '<=', date_to.strftime('%Y-%m-%d 23:59:59')),
                                                        ('location_id', 'in', location_ids),
                                                        ('picking_type_code', 'not in', ('incoming','internal')),
                                                        ('state', '=', 'done'),
                                                        ])
                date_obj = [date.strftime('%Y-%m-%d %H:%M:%S') for date in move_id.mapped('date')]
                # print('DATE', date_obj)
                lead_move_ids = self.env['stock.move'].search([('product_id', '=', record.product_id.id),
                                                        ('date', '>=', date2.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                                                        ('date', '<=', date1.strftime('%Y-%m-%d 23:59:59')),
                                                        ('state', '=', 'done'),
                                                        ('location_dest_id', 'in', location_ids),
                                                        ('picking_type_code', '=', 'incoming')
                                                        ])
                process_time_days = sum(lead_move_ids.mapped('picking_id.transfer_log_activity_ids.process_days'))
                if len(lead_move_ids) > 0:
                    record.lead_days_run_rate_days = process_time_days / len(lead_move_ids)
                qty = sum(move_id.mapped('quantity_done'))
                # print('QTY STOCK MOVE', qty)
                run_rate_days = (date1 - date2).days
                # quantity = 0
                # if run_rate_days >= 1:
                #     quantity = qty / run_rate_days
                # record.average_quantity_run_rate_days = quantity
                if record.run_rate_period_before > 0 and qty > 0:
                    quantity = (qty / (record.run_rate_period_before + 1))
                    record.average_quantity_run_rate_days = quantity
                    
    # @api.onchange('run_rate_type',
    #             'safety_stock',
    #             'safety_stock_select', 'is_minimum_quantity',
    #             'average_quantity_last_year', 'average_quantity_run_rate_days',
    #             'lead_days_last_year', 'lead_days_run_rate_days')
    # def _onchange_run_rate_type(self):
    #     if self.run_rate_type == 'get_last_year':
    #         self.run_rate_qty = self.average_quantity_last_year
    #         self.lead_days = self.lead_days_last_year
    #         if self.lead_days_last_year > 0:
    #             self.product_min_qty = self.run_rate_qty * self.lead_days_last_year
    #         else:
    #             self.product_min_qty = self.run_rate_qty * 1
    #     elif self.run_rate_type == 'get_past_days_data':
    #         self.run_rate_qty = self.average_quantity_run_rate_days
    #         self.lead_days = self.lead_days_run_rate_days
    #         if self.lead_days_run_rate_days > 0:
    #             self.product_min_qty = self.run_rate_qty * self.lead_days_run_rate_days
    #         else:
    #             self.product_min_qty = self.run_rate_qty * 1
    #     if self.safety_stock_select == 'fix_qty':
    #         self.run_rate_qty += self.safety_stock
    #     elif self.safety_stock_select == 'percentage' and self.run_rate_qty > 0:
    #         self.run_rate_qty += ((self.run_rate_qty * self.safety_stock) / 100)
                
    @api.onchange('is_minimum_quantity',
                  'run_rate_type','run_rate_period_before','run_rate_period_after',
                  'safety_stock_select', 'safety_stock', 'lead_days', 
                  'lead_days_last_year', 'lead_days_run_rate_days', 'average_quantity_last_year', 'average_quantity_run_rate_days')

    def _onchange_run_rate_type(self):
        if self.run_rate_type == 'get_last_year':
            if self.safety_stock_select == 'fix_qty':
                run_rate_qty = self.average_quantity_last_year
                if self.lead_days_last_year:
                    self.lead_days = self.lead_days + self.lead_days_last_year
                else:
                    self.lead_days = self.lead_days
                self.run_rate_qty = run_rate_qty
                self.product_min_qty = (run_rate_qty * (self.lead_days if self.lead_days else 1)) + (run_rate_qty if self.lead_days >= 1 else 0) + self.safety_stock
                
            if self.safety_stock_select == 'percentage' and self.run_rate_qty > 0:
                run_rate_qty = self.average_quantity_run_rate_days 
                if self.lead_days_last_year:
                    self.lead_days = self.lead_days + self.lead_days_last_year
                else:
                    self.lead_days = self.lead_days
                self.run_rate_qty = run_rate_qty
                self.product_min_qty = (run_rate_qty * (self.lead_days if self.lead_days else 1)) + (run_rate_qty if self.lead_days >= 1 else 0) + + (self.average_quantity_last_year * self.safety_stock) / 100
                
        elif self.run_rate_type == 'get_past_days_data':
            run_rate_qty = self.average_quantity_run_rate_days
            if self.safety_stock_select == 'fix_qty':
                if self.lead_days_run_rate_days:
                    self.lead_days = self.lead_days + self.lead_days_run_rate_days
                else:
                    self.lead_days = self.lead_days
                self.run_rate_qty = run_rate_qty
                self.product_min_qty = (run_rate_qty * (self.lead_days if self.lead_days else 1)) + (run_rate_qty if self.lead_days >= 1 else 0) + self.safety_stock
                
            if self.safety_stock_select == 'percentage' and self.run_rate_qty > 0:
                if self.lead_days_run_rate_days:
                    self.lead_days = self.lead_days + self.lead_days_run_rate_days
                else:
                    self.lead_days = self.lead_days
                self.run_rate_qty = run_rate_qty
                self.product_min_qty = (run_rate_qty * (self.lead_days if self.lead_days else 1)) + (run_rate_qty if self.lead_days >= 1 else 0) + ((self.average_quantity_run_rate_days * self.safety_stock) / 100)                    
    
    @api.model
    def _cron_stock_warehouse_orderpoint(self):
        stock_orderpoints = self.search([])
        orderpoint = []
        counter = 1
        partner_ids = []
        for stock_orderpoint in stock_orderpoints:
            if stock_orderpoint.start_date and stock_orderpoint.start_month:
                start_date = int(stock_orderpoint.start_date)
                start_month = int(stock_orderpoint.start_month)
            else:
                start_date = date.today().day
                start_month = date.today().month
            if stock_orderpoint.end_date and stock_orderpoint.end_month:
                end_date = int(stock_orderpoint.end_date)
                end_month = int(stock_orderpoint.end_month)
            else:
                end_date = date.today().day
                end_month = date.today().month
            today_date = datetime.today()
            for responsible_user in stock_orderpoint.notification_user_ids:
                partner_ids.append(responsible_user)
            date1 = today_date.replace(day=start_date, month=start_month)
            date2 = today_date.replace(day=end_date, month=end_month)
            if date1 <= today_date and date2 >= today_date and stock_orderpoint.start_month and stock_orderpoint.start_date and stock_orderpoint.end_date and stock_orderpoint.end_month:
                minimum_quantity = stock_orderpoint.product_min_qty
                if stock_orderpoint.location_id:
                    stock_quant_ids = self.env['stock.quant'].search([('product_id', '=', stock_orderpoint.product_id.id),
                                                                      ('location_id', '=', stock_orderpoint.location_id.id),
                                                                      ])
                else:
                    stock_quant_ids = self.env['stock.quant'].search([('product_id', '=', stock_orderpoint.product_id.id),
                                                                      ('location_id.warehouse_id', '=', stock_orderpoint.warehouse_id.id),
                                                                      ])
                available_quantity = sum(stock_quant_ids.mapped('available_quantity'))
                if available_quantity < minimum_quantity:
                    stock_orderpoint.write({'is_low_stock': True})
                    stock_quant_ids.write({'is_low_stock': True})
                    product_id = stock_quant_ids.mapped('product_id')
                    product_id.write({'is_low_stock': True})
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    action_lot = self.env.ref('stock.action_production_lot_form')
                    for quant in stock_quant_ids:
                        move_line_ids = self.env['stock.move.line'].search([('product_id', '=', quant.product_id.id), ('product_id.is_low_stock', '=', True), ('location_id', '=', quant.location_id.id)])
                        move_line_ids.write({'is_low_stock': True})
                        url = base_url + '/web#action='+ str(action_lot.id) + '&id=' + str(quant.lot_id.id) + '&view_type=form&model=stock.production.lot'
                        data = {
                            'counter' : counter,
                            'product_id' : quant.product_id.display_name,
                            'location_id' : quant.location_id.display_name,
                            'lot_id': quant.lot_id and quant.lot_id.name or '',
                            'quantity': quant.quantity,
                            'url':url
                        }
                        counter += 1
                        orderpoint.append(data)
                else:
                    stock_orderpoint.write({'is_low_stock': False})

        if orderpoint and stock_orderpoints:
            template_id = self.env.ref('equip3_inventory_control.email_template_stock_warehouse_orderpoint')
            datas = list(set(partner_ids))
            for user in datas:
                email = user.partner_id.email
                user_name = user.name
                ctx = {
                    'user_name': user_name,
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : email,
                    'data' : orderpoint
                    }
                if stock_orderpoints:
                    template_id.with_context(ctx).send_mail(stock_orderpoints[0].id, True)
                    body_html = self.env['mail.render.mixin'].with_context(ctx)._render_template(
                        template_id.body_html, 'stock.warehouse.orderpoint', stock_orderpoints[0].ids, post_process=True)[stock_orderpoints[0].id]
                    message_id = (
                        self.env["mail.message"]
                            .sudo()
                            .create(
                            {
                                "subject": 'Low Stock Alert 123',
                                "body": body_html,
                                "message_type": "notification",
                                "partner_ids": [
                                    (
                                        6,
                                        0,
                                        user.partner_id.ids,
                                    )
                                ],
                            }
                        )
                    )
                    notif_create_values = {
                        "mail_message_id": message_id.id,
                        "res_partner_id": user.partner_id.id,
                        "notification_type": "inbox",
                        "notification_status": "sent",
                    }
                    self.env["mail.notification"].sudo().create(notif_create_values)


    @api.model
    def create(self, vals):
        seq1 = self.env.ref('equip3_inventory_control.stock_warehouse_orderpoint_sequence').sudo()
        record_id = self.search([], limit=1, order='id desc')
        check_today = False
        if record_id and record_id.create_date.date() == date.today():
            check_today = True
        if check_today == True:
            seq = self.env['ir.sequence'].next_by_code('sequence.stock.warehouse.orderpoint')
            vals['name'] = seq
        else:
            seq1.sudo().write({'number_next_actual': 1})
            seq = self.env['ir.sequence'].next_by_code('sequence.stock.warehouse.orderpoint')
            vals['name'] = seq
        # if self.product_id:
        # if vals['product_max_qty'] == 0 and vals['product_min_qty'] == 0:
        #     vals['product_max_qty'] = 1
        # elif vals['product_min_qty'] > vals['product_max_qty']:
        #     vals['product_min_qty'] = 0
        # elif vals['product_max_qty'] <= vals['product_min_qty']:
        #     raise ValidationError('The Maximum Quantity cannot be below or equal to Minimum Quantity')
        return super(StockWarehouseOrderpoint, self).create(vals)


    # @api.constrains('product_min_qty','product_max_qty')
    # def min_qty_validation(self):
        # if self.product_max_qty == 0 and self.product_min_qty == 0:
        #     self.product_max_qty = 1
        # if self.product_id:
            # if self.product_max_qty <= self.product_min_qty:
            #     raise ValidationError('The Maximum Quantity cannot be below or equal to Minimum Quantity')

    # for cron replenish orderpoint
    @api.model
    def _cron_replenish_orderpoint(self):
        records = self.env['stock.warehouse.orderpoint'].search([
            ('auto_trigger_replenishment', '=', True),
            ('qty_to_order', '>', 0.0)
        ])

        if records:
            record = records[0]
            # Set env from existing record
            self = self.with_context(cron=True)
            self.env.user = record.create_uid
            self.env.companies = record.company_id
            self.env.branches = record.branch_id
            records._compute_qty()
            records._compute_qty_to_order()
            records = records.filtered(lambda r: r.qty_to_order > 0.0)

        if records:
            self.action_replenish_orderpoint(records.ids)


    def _create_mr(self, records, warehouse_ids, is_cron=False):
        material_request_ids = self.env['material.request']
        for warehouse in warehouse_ids:
            lines = records.filtered(lambda a: a.warehouse_id.id == warehouse.id)
            product_line_data = []
            temp_list = []
            line_list_vals = []
            name = ",".join(lines.mapped('name'))
            for line in lines:
                if line.product_id.id in temp_list:
                    filter_list = list(filter(lambda r: r.get('product') == line.product_id.id, line_list_vals))
                    if filter_list:
                        filter_list[0]['quantity'].append(line.qty_to_order)

                else:
                    temp_list.append(line.product_id.id)
                    line_list_vals.append({
                        'product' : line.product_id.id,
                        'description' : line.product_id.name,
                        'quantity' : [line.qty_to_order],
                        'product_unit_measure' : line.product_id.uom_id.id,
                        'request_date' : date.today(),
                        'destination_warehouse_id': warehouse.id,
                    }
                    )
            for product_line in line_list_vals:
                product_line['quantity'] = sum(product_line['quantity'])
                product_line_data.append((0, 0, product_line))
            vals={
                'requested_by' : self.env.user.id,
                'schedule_date' : date.today(),
                'source_document' : name,
                'product_line' : product_line_data,
                'destination_warehouse_id' : warehouse.id,
            }
            material_request = self.env['material.request'].create(vals)
            material_request._onchange_analytic_account_group_ids()
            material_request_ids += material_request

            if not is_cron:
                lines.write({
                    'trigger': 'manual',
                    'is_replenish_document_created': True,
                    'material_request_id' : material_request.id,
                    'replenish_document_status': 'Draft',
                    'snoozed_until': date.today() + timedelta(days=1),
                })
        
        return material_request_ids

    def _create_pr(self, records, warehouse_ids, is_cron=False):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
        product_line_data = []
        temp_list = []
        line_list_vals = []
        name = ",".join(records.mapped('name'))
        for warehouse in warehouse_ids:
            lines = records.filtered(lambda a: a.warehouse_id.id == warehouse.id)
            for line in lines:
                if {'product_id': line.product_id.id, 'dest_loc_id': line.warehouse_id.id} in temp_list:
                    filter_list = list(filter(lambda r: r.get('product_id') == line.product_id.id and r.get('dest_loc_id') == line.warehouse_id.id,  line_list_vals))
                    if filter_list:
                        filter_list[0]['product_qty'].append(line.qty_to_order)
                else:
                    temp_list.append({'product_id': line.product_id.id, 'dest_loc_id': line.warehouse_id.id})
                    line_list_vals.append({
                        'product_id' : line.product_id.id,
                        'name' : line.product_id.name,
                        'product_qty' : [line.qty_to_order],
                        'product_uom_id' : line.product_id.uom_id.id,
                        'dest_loc_id': line.warehouse_id.id,
                    })
        for final_line in line_list_vals:
            final_line['product_qty'] = sum(final_line['product_qty'])
            product_line_data.append((0, 0, final_line))
        vals = {
            'requested_by' : self.env.user.id,
            'origin' : name,
            'line_ids' : product_line_data,
        }
        if is_good_services_order:
            vals.update({
                'is_goods_orders': True,
            })
        purchase_request = self.env['purchase.request'].create(vals)
        if not is_cron:

            records.write({
                'trigger': 'manual',
                'is_replenish_document_created': True,
                'purchase_request_id' : purchase_request.id,
                'replenish_document_status': 'Draft',
                'snoozed_until': date.today() + timedelta(days=1),
            })
        return purchase_request

    def _create_rfq(self, records, is_cron=False):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
        is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))
        temp_list = []
        line_list_vals = []

        for record in records:
            key = {'warehouse_id': record.warehouse_id.id, 'vendor_id': record.partner_id.id}
            if key in temp_list:
                filter_line = next((r for r in line_list_vals if r['warehouse_id'] == record.warehouse_id.id and r['vendor_id'] == record.partner_id.id), None)
                if filter_line:
                    filter_line['lines'].append(record)
            else:
                temp_list.append(key)
                line_list_vals.append({
                    'warehouse_id': record.warehouse_id.id,
                    'vendor_id': record.partner_id.id,
                    'lines': [record]
                })
        
        purchase_orders = []
        for rfq_line in line_list_vals:
            final_lines = []
            for line in rfq_line.get('lines'):
                filter_list = next((r for r in final_lines if r['product_id'] == line.product_id.id), None)
                if filter_list:
                    filter_list['product_qty'] += line.qty_to_order
                else:
                    price_unit = line.product_id.standard_price
                    if is_cost_per_warehouse:
                        price_unit = self.env['product.warehouse.price'].sudo().search([
                            ('company_id', '=', self.env.company.id),
                            ('product_id', '=', line.product_id.id),
                            ('warehouse_id', '=', line.warehouse_id.id)
                        ], limit=1).standard_price

                    final_lines.append({
                        'product_id': line.product_id.id,
                        'name': line.product_id.name,
                        'price_unit': price_unit,
                        'display_type': False,
                        'date_planned': datetime.today(),
                        'product_qty': line.qty_to_order,
                        'product_uom': line.product_id.uom_id.id,
                        'destination_warehouse_id': line.warehouse_id.id,
                    })
            
            # Preparing data for purchase order creation
            product_line_data = [(0, 0, product_line) for product_line in final_lines]
            warehouse_id = self.env['stock.warehouse'].browse(rfq_line['warehouse_id'])
            
            vals = {
                'partner_id': rfq_line.get('vendor_id'),
                'date_order': datetime.today(),
                'date_planned': datetime.today(),
                'order_line': product_line_data,
                'picking_type_id': warehouse_id.int_type_id.id,
                'origin': ",".join([order_point.name for order_point in rfq_line['lines']]),
                'is_single_delivery_destination': True,
                'destination_warehouse_id': warehouse_id.id,
            }
            
            if is_good_services_order:
                po_name = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rfq.goods')
                vals.update({
                    'is_goods_orders': True,
                    'name': po_name
                })
            else:
                po_name = self.env['ir.sequence'].next_by_code('purchase.order.seqs.rfq')
                vals.update({
                    'name': po_name,
                })
            
            purchase_order = self.env['purchase.order'].create(vals)
            purchase_orders.append(purchase_order)
            
            if not is_cron:
                for line in rfq_line['lines']:
                    line.write({
                        'trigger': 'manual',
                        'is_replenish_document_created': True,
                        'purchase_order_id': purchase_order.id,
                        'replenish_document_status': 'Draft',
                        'snoozed_until': date.today() + timedelta(days=1),
                    })

        return purchase_orders


    def _create_itr(self, records, is_cron):
        temp_list = []
        line_list_vals = []
        internal_transfers = self.env['internal.transfer']
        for record in records:
            if {'destination_location_id': record.location_id.id, 'source_location_id': record.source_location_id.id} in temp_list:
                filter_line = list(filter(lambda r:r.get('destination_location_id') == record.location_id.id and r.get('source_location_id') == record.source_location_id.id, line_list_vals))
                if filter_line:
                    filter_line[0]['lines'].append(record)
            else:
                temp_list.append({'destination_location_id': record.location_id.id, 'source_location_id': record.source_location_id.id})
                line_list_vals.append({
                    'destination_location_id': record.location_id.id,
                    'source_location_id': record.source_location_id.id,
                    'lines': [record]
                })
        for itr_line in line_list_vals:
            product_line_data = []
            temp_lines = []
            counter = 1
            final_lines = []
            name = ",".join([order_point.name for order_point in itr_line.get('lines')])
            for line in itr_line.get('lines'):
                if line.product_id.id in temp_lines:
                    filter_list = list(filter(lambda r: r.get('product_id') == line.product_id.id, final_lines))
                    if filter_list:
                        filter_list[0]['qty'].append(line.qty_to_order)

                else:
                    temp_lines.append(line.product_id.id)
                    final_lines.append({
                        'sequence': counter,
                        'product_id' : line.product_id.id,
                        'description' : line.product_id.display_name,
                        'qty' : [line.qty_to_order],
                        'scheduled_date' : date.today(),
                        'uom' : line.product_id.uom_id.id,
                        'source_location_id': itr_line.get('source_location_id'),
                        'destination_location_id': itr_line.get('destination_location_id'),
                    })
            for product_line in final_lines:
                product_line['qty'] = sum(product_line['qty'])
                product_line_data.append((0, 0, product_line))
            vals={
                'source_location_id' : itr_line.get('source_location_id'),
                'destination_location_id' : itr_line.get('destination_location_id'),
                'scheduled_date' : date.today(),
                'source_document' : name,
                'product_line_ids' : product_line_data,
            }
            internal_transfer = self.env['internal.transfer'].create(vals)
            internal_transfer.write({'source_warehouse_id': record.source_location_id.warehouse_id.id, 'destination_warehouse_id': record.location_id.warehouse_id.id})
            if not is_cron:
                for line in itr_line.get('lines'):
                    line.write({
                        'trigger': 'manual',
                        'is_replenish_document_created': True,
                        'internal_transfer_id' : internal_transfer.id,
                        'replenish_document_status': 'Draft',
                        'snoozed_until': date.today() + timedelta(days=1),
                    })
            internal_transfer.onchange_source_loction_id()
            internal_transfer.onchange_dest_loction_id()
            internal_transfers += internal_transfer

        return internal_transfers

    def _send_email_to_responsible(self, records):
        mail_ids = []

        for rec in records:
            for user in rec.responsible_id:
                ctx = {}
                record_ref = ''                
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                orderpoint_ref = ''
                url = ''
                template_id = self.env.ref('equip3_inventory_control.email_template_stock_warehouse_orderpoint_for_all')

                if rec.action_to_take == 'create_mr':
                    record_ref = 'Material Request'
                    orderpoint_ref = rec.material_request_id.name
                    url = base_url + '/web#id='+ str(rec.material_request_id.id) + '&view_type=form&model=material.request'
                elif rec.action_to_take == 'create_pr':
                    record_ref = 'Purchase Request'
                    orderpoint_ref = rec.purchase_request_id.name
                    url = base_url + '/web#id='+ str(rec.purchase_request_id.id) + '&view_type=form&model=purchase.request'
                elif rec.action_to_take == 'create_rfq':
                    record_ref = 'Request for Quotation'
                    orderpoint_ref = rec.purchase_order_id.name
                    url = base_url + '/web#id='+ str(rec.purchase_order_id.id) + '&view_type=form&model=purchase.order'
                elif rec.action_to_take == 'create_itr':
                    record_ref = 'Internal Transfer Request'
                    orderpoint_ref = rec.internal_transfer_id.name
                    url = base_url + '/web#id='+ str(rec.internal_transfer_id.id) + '&view_type=form&model=internal.transfer'
                subject =  record_ref + ' To ' + rec.product_id.display_name
                ctx.update({
                    'email_from': self.env.user.company_id.email,
                    'email_to': user.partner_id.email,
                    'subject': subject,
                    'user_name': user.name,
                    'orderpoint_ref': orderpoint_ref,
                    'login_url': url,
                    'ref': record_ref,
                })
                mail_id = template_id.with_context(ctx).send_mail(rec.id, True)
                mail_ids.append(mail_id)

        return mail_ids

    @api.model
    def action_replenish_orderpoint(self, active_ids):
        records = self.browse(active_ids)
        action_to_take = list(set(records.mapped('action_to_take')))
        warehouse_ids = list(set(records.mapped('warehouse_id')))
        is_cron = self.env.context.get('cron')
        if len(action_to_take) > 1:
            raise ValidationError('Cannot merge more then one actions!')
        message = "The following record(s) already on progress of Replenishment:\n"
        is_replenish_document_created = False
        for rec in records:
            rec.is_replenish_document_created = False
            if rec.is_replenish_document_created and rec.trigger == 'auto':
                is_replenish_document_created = True
                message += ' - ' + rec.name + ' - ' + rec.product_id.display_name + ' - ' + rec.warehouse_id.name + '\n'
            if rec.is_replenish_document_created and rec.snoozed_until.date() > date.today():
                  is_replenish_document_created = True
                  message += ' This Product Has been Replenished for today , You can Replenish the product tomorrow'
        if is_replenish_document_created:
            raise ValidationError ('%s' % message)
        if action_to_take and action_to_take[0] == 'create_mr':
            self._create_mr(records, warehouse_ids, is_cron)
        elif action_to_take and action_to_take[0] == 'create_pr':
            self._create_pr(records, warehouse_ids, is_cron)
        elif action_to_take and action_to_take[0] == 'create_rfq':
            self._create_rfq(records, is_cron)
        elif action_to_take and action_to_take[0] == 'create_itr':
            self._create_itr(records, is_cron)

        self._send_email_to_responsible(records)
        return True

    @api.depends('rule_ids', 'product_id.seller_ids', 'product_id.seller_ids.delay')
    def _compute_json_popover(self):
        for orderpoint in self:
            if not orderpoint.product_id or not orderpoint.warehouse_id:
                orderpoint.json_lead_days_popover = False
                continue
            dummy, lead_days_description = orderpoint.rule_ids._get_lead_days(orderpoint.product_id)
            orderpoint.json_lead_days_popover = dumps({
                'title': _('Replenishment'),
                'icon': 'fa-area-chart',
                'popoverTemplate': 'stock.leadDaysPopOver',
                'lead_days_date': fields.Date.to_string(orderpoint.lead_days_date),
                'lead_days_description': lead_days_description,
                'today': fields.Date.to_string(fields.Date.today()),
                'trigger': orderpoint.trigger,
                'qty_forecast': orderpoint.qty_forecast,
                'qty_to_order': orderpoint.qty_to_order,
                'product_min_qty': orderpoint.product_min_qty,
                'product_max_qty': orderpoint.product_max_qty,
                'product_uom_name': orderpoint.product_uom_name,
                'virtual': orderpoint.trigger == 'manual' and orderpoint.create_uid.id == SUPERUSER_ID,
            })

    @api.depends('rule_ids', 'product_id.seller_ids', 'product_id.seller_ids.delay')
    def _compute_lead_days(self):
        for orderpoint in self:
            if not orderpoint.product_id or not orderpoint.warehouse_id:
                orderpoint.lead_days_date = False
                continue
            lead_days, dummy = orderpoint.rule_ids._get_lead_days(orderpoint.product_id)
            lead_days_date = fields.Date.today() + relativedelta.relativedelta(days=lead_days)
            orderpoint.lead_days_date = lead_days_date

    @api.depends('route_id', 'product_id', 'location_id', 'company_id', 'warehouse_id', 'product_id.route_ids')
    def _compute_rules(self):
        for orderpoint in self:
            if not orderpoint.product_id or not orderpoint.warehouse_id:
                orderpoint.rule_ids = False
                continue
            final_location = False
            if not orderpoint.location_id:
                location_obj = self.env['stock.location']
                store_location_id = orderpoint.warehouse_id.view_location_id.id
                addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')], order='id')
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_obj += location
                child_location_ids = self.env['stock.location'].search([('id', 'child_of', location_obj.ids), ('id', 'not in', location_obj.ids)])
                final_location = child_location_ids + location_obj
            else:
                final_location = orderpoint.location_id
            orderpoint_rule_ids = []
            for location in final_location:
                rule_ids = orderpoint.product_id._get_rules_from_location(location, route_ids=orderpoint.route_id)
                orderpoint_rule_ids.extend(rule_ids.ids)
            orderpoint.rule_ids = [(6, 0, orderpoint_rule_ids)]

    @api.depends('product_id', 'location_id', 'product_id.stock_move_ids', 'product_id.stock_move_ids.state', 'product_id.stock_move_ids.product_uom_qty')
    def _compute_qty(self):
        orderpoints_contexts = defaultdict(lambda: self.env['stock.warehouse.orderpoint'])
        for orderpoint in self:
            if not orderpoint.product_id or not orderpoint.warehouse_id:
                orderpoint.qty_on_hand = False
                orderpoint.qty_forecast = False
                continue
            orderpoint_context = orderpoint._get_product_context()
            if not orderpoint.location_id and orderpoint.warehouse_id:
                orderpoint_context['warehouse'] =  orderpoint.warehouse_id.id
            product_context = frozendict({**self.env.context, **orderpoint_context})
            orderpoints_contexts[product_context] |= orderpoint
        for orderpoint_context, orderpoints_by_context in orderpoints_contexts.items():
            products_qty = orderpoints_by_context.product_id.with_context(orderpoint_context)._product_available()
            products_qty_in_progress = orderpoints_by_context._quantity_in_progress()
            for orderpoint in orderpoints_by_context:
                orderpoint.qty_on_hand = products_qty[orderpoint.product_id.id]['qty_available']
                orderpoint.qty_forecast = products_qty[orderpoint.product_id.id]['virtual_available'] + products_qty_in_progress[orderpoint.id]

    @api.depends('qty_multiple', 'qty_forecast', 'product_min_qty', 'product_max_qty')
    def _compute_qty_to_order(self):
        for orderpoint in self:
            if not orderpoint.product_id or not orderpoint.warehouse_id:
                orderpoint.qty_to_order = False
                continue
            qty_to_order = 0.0
            rounding = orderpoint.product_uom.rounding
            if float_compare(orderpoint.qty_forecast, orderpoint.product_min_qty, precision_rounding=rounding) < 0:
                qty_to_order = max(orderpoint.product_min_qty, orderpoint.product_max_qty) - orderpoint.qty_forecast
                # remainder = orderpoint.qty_multiple > 0 and qty_to_order % orderpoint.qty_multiple or 0.0
                # if float_compare(remainder, 0.0, precision_rounding=rounding) > 0:
                #     qty_to_order += orderpoint.qty_multiple - remainder
                if orderpoint.qty_multiple:
                    qty_to_order = floor(qty_to_order / orderpoint.qty_multiple) * orderpoint.qty_multiple
            orderpoint.qty_to_order = qty_to_order

    @api.model
    def default_get(self, fields):
        res = super(StockWarehouseOrderpoint, self).default_get(fields)
        context = dict(self.env.context) or {}
        res['responsible_id'] = [(6, 0, self.env.user.ids)]
        if context.get('search_default_trigger'):
            res['trigger'] = 'auto'
        return res
