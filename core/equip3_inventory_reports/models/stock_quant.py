
from odoo import fields, models, api
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class StockQuant(models.Model):
    _inherit = "stock.quant"

    @api.depends_context('inv_warehouse', 'inv_location')
    def _compute_inv_reports_warehouse_quantities(self):
        context = self.env.context
        warehouse = context.get('inv_warehouse', False)
        global_location = context.get('inv_location', False)
        context_data_dict_base = {}
        
        if global_location:
            context_data_dict_base.update({'location': global_location})
        elif warehouse:
            warehouse_record = self.env['stock.warehouse'].browse(warehouse)
            all_locations = self.env['stock.location'].search([
                ('warehouse_id', '=', warehouse_record.id),
                ('location_id', 'child_of', warehouse_record.lot_stock_id.id)
            ])
            location_ids = all_locations.ids
            context_data_dict_base.update({'location_ids': location_ids})
        
        for record in self:
            context_data_dict = context_data_dict_base.copy()
            if not global_location and warehouse:
                if record.location_id:
                    context_data_dict.update({'location': record.location_id.id})
                else:
                    context_data_dict.update({'location': warehouse_record.lot_stock_id.id})
            
            lot_id = record.lot_id.id if record.lot_id else None
            res = record.product_id.with_context(context_data_dict)._compute_quantities_dict(lot_id, None, None)
            product_id = record.product_id

            inv_report_qty_sec = 0
            inv_report_qty_ref = 0
            reference_uom_value = 0
            secondary_uom_value = 0
            qty_available = res[product_id.id]['qty_available']
            incoming_qty = res[product_id.id]['incoming_qty']
            outgoing_qty = res[product_id.id]['outgoing_qty']
            virtual_available = res[product_id.id]['virtual_available']
            free_qty = res[product_id.id]['free_qty']

            onhand_qty = qty_available + incoming_qty - outgoing_qty
            value = record.value
            if onhand_qty != 0 and value != 0:
                reference_uom_value = value / onhand_qty
            else:
                reference_uom_value = 0

            inv_report_ref = product_id.product_tmpl_id.uom_id.category_id.id
            inv_report_sec = product_id.product_tmpl_id.secondary_uom_id.id
            if product_id.product_tmpl_id.uom_id.uom_type == 'bigger':
                inv_report_qty_ref = qty_available * product_id.product_tmpl_id.uom_id.factor_inv
            if product_id.product_tmpl_id.uom_id.uom_type == 'reference':
                inv_report_qty_ref = qty_available
            if product_id.product_tmpl_id.uom_id.uom_type == 'smaller':
                inv_report_qty_ref = qty_available / product_id.product_tmpl_id.uom_id.factor
            if product_id.product_tmpl_id.secondary_uom_id.uom_type == 'bigger':
                inv_report_qty_sec = inv_report_qty_ref / \
                    product_id.product_tmpl_id.secondary_uom_id.factor_inv
                if onhand_qty == 0:
                    secondary_uom_value = 0
                else:
                    secondary_uom_value = (value / onhand_qty) * product_id.product_tmpl_id.secondary_uom_id.factor_inv
            if product_id.product_tmpl_id.secondary_uom_id.uom_type == 'reference':
                inv_report_qty_sec = inv_report_qty_ref
                if onhand_qty == 0:
                    secondary_uom_value = (value / onhand_qty)
                else:
                    secondary_uom_value = (value / onhand_qty)
            if product_id.product_tmpl_id.secondary_uom_id.uom_type == 'smaller':
                inv_report_qty_sec = inv_report_qty_ref * \
                    product_id.product_tmpl_id.secondary_uom_id.factor
                if onhand_qty == 0:
                    secondary_uom_value = 0
                else:
                    secondary_uom_value = (value / onhand_qty) / product_id.product_tmpl_id.secondary_uom_id.factor
            record.inv_report_qty_available = qty_available
            record.inv_report_incoming_qty = incoming_qty
            record.inv_report_outgoing_qty = outgoing_qty
            record.inv_report_virtual_available = virtual_available
            record.inv_report_free_qty = free_qty
            record.inv_report_qty_ref = inv_report_qty_ref
            record.inv_report_ref = inv_report_ref
            record.inv_report_qty_sec = inv_report_qty_sec
            record.inv_report_sec = inv_report_sec
            record.value_per_unit_of_measure = reference_uom_value
            record.value_per_secondary_uom = secondary_uom_value

    @api.depends_context('inv_warehouse', 'inv_sold_product')
    def _compute_inv_reports_sales(self):
        context = self.env.context
        warehouse = context.get('inv_warehouse', False)
        sold_product = context.get('inv_sold_product', False)

        self.inv_report_hide_sales = not sold_product
        if not warehouse or not sold_product:
            self.inv_report_sales = 0
            self.inv_report_stock_movement = ''
            return

        warehouse_ids = {warehouse} if warehouse else {}
        end_date = fields.Date.today()
        start_date = end_date - relativedelta(days=sold_product)

        query = """
            SELECT * FROM get_inventory_fsn_analysis_report('%s','%s','%s','%s','%s','%s', '%s')
        """ % ({self.env.company.id}, {}, {}, warehouse_ids, start_date, end_date, 'all')
        self._cr.execute(query)
        stock_data = self._cr.dictfetchall()

        res = {}
        for data in stock_data:
            res[data.get('product_id', False)] = {
                'sales': data.get('sales', 0.0),
                'stock_movement': data.get('stock_movement', ''),
            }

        for record in self:
            product_id = record.product_id
            record.inv_report_sales = res.get(product_id.id, {}).get('sales', 0.0)
            record.inv_report_stock_movement = res.get(product_id.id, {}).get('stock_movement', 0.0)

    inv_report_qty_available = fields.Float(
        compute=_compute_inv_reports_warehouse_quantities)
    inv_report_incoming_qty = fields.Float(
        compute=_compute_inv_reports_warehouse_quantities)
    inv_report_outgoing_qty = fields.Float(
        compute=_compute_inv_reports_warehouse_quantities)
    inv_report_virtual_available = fields.Float(
        compute=_compute_inv_reports_warehouse_quantities)
    inv_report_free_qty = fields.Float(
        compute=_compute_inv_reports_warehouse_quantities)
    inv_report_qty_ref = fields.Float(
        string="Quantity On Hand Reference UoM", compute=_compute_inv_reports_warehouse_quantities)
    inv_report_ref = fields.Many2one(
        'uom.category', string="Reference UoM", compute=_compute_inv_reports_warehouse_quantities)
    inv_report_qty_sec = fields.Float(
        string="Quantity On Hand Secondary UoM", compute=_compute_inv_reports_warehouse_quantities)
    inv_report_sec = fields.Many2one(
        'uom.uom', string="Secondary UoM", compute=_compute_inv_reports_warehouse_quantities)
    inv_report_sales = fields.Float(
        string="Sales", compute=_compute_inv_reports_sales)
    inv_report_stock_movement = fields.Char(
        string='Stock Movement', compute=_compute_inv_reports_sales)
    inv_report_default_code = fields.Char(
        related='product_id.default_code', string='Product Code')
    inv_report_hide_sales = fields.Boolean(compute=_compute_inv_reports_sales)

    product_category = fields.Many2one(
        "product.category", related="product_id.categ_id", store=True, string="Product category")
    expire_days = fields.Char(
        string="Expire in (days)", compute='_calculate_expire_day', store=False)
    expire_days_count = fields.Integer(
        string="Expire in (days) Count", compute='_calculate_expire_day', store=False)
    expire_date = fields.Datetime(
        'Expiration_date', readonly=True, compute='_compute_lots_expire_date', store=True)
    weight = fields.Float(related='product_id.weight')
    # is_update_value = fields.Boolean(compute='get_value_and_location')
    # purchase_value_in_lot = fields.Monetary(
    #     'Value', groups='stock.group_stock_manager', compute='get_value_and_location')
    cluster_area_id = fields.Many2one(
        comodel_name='cluster.area', string='Cluster Area', compute='get_cluster_area', store=True)
    value_per_unit_of_measure = fields.Float(string='Value per UoM', compute=_compute_inv_reports_warehouse_quantities)
    value_per_secondary_uom = fields.Float(string='Value per Secondary UoM', compute=_compute_inv_reports_warehouse_quantities)



        # for quant in self:
        #     quant.currency_id = quant.company_id.currency_id
        #     # If the user didn't enter a location yet while enconding a quant.
        #     if not quant.location_id:
        #         quant.value = 0
        #         return

        #     if not quant.location_id._should_be_valued() or\
        #             (quant.owner_id and quant.owner_id != quant.company_id.partner_id):
        #         quant.value = 0
        #         continue
        #     if quant.product_id.cost_method == 'fifo':
        #         quantity = quant.product_id.quantity_svl
        #         if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
        #             quant.value = 0.0
        #             continue
        #         average_cost = quant.product_id.with_company(quant.company_id).value_svl / quantity
        #         quant.value = quant.quantity * average_cost
        #     else:
        #         quant.value = quant.quantity * quant.product_id.with_company(quant.company_id).standard_price

    # def get_value_and_location(self):
            # for record in self:
            #     record.is_update_value = False
            #     record.purchase_value_in_lot = 0
            #     if record.product_category.property_cost_method == 'fifo' or record.product_category.property_cost_method == 'average':
            #         if record.lot_id.product_id.tracking == 'serial' or record.lot_id.product_id.tracking == 'lot':
            #             if record.lot_id.purchase_order_ids.order_line:
            #                 for line in record.lot_id.purchase_order_ids.order_line:
            #                     if line.product_id.id == record.lot_id.product_id.id:
            #                         # print('record......  atas',record.lot_id.name)
            #                         inventory_line = self.env['stock.inventory.line'].search([('prod_lot_id', '=', record.lot_id.id)])
            #                         price_unit_sum = sum(inventory_line.mapped('unit_price')) * sum(inventory_line.mapped('difference_qty'))
            #                         convert_price = line.order_id.currency_id._convert(
            #                             line.price_unit, self.env.company.currency_id, self.env.company, record.in_date, round=False) * record.quantity
            #                         if price_unit_sum:
            #                             record.sudo().write(
            #                                 {'purchase_value_in_lot': line.price_unit + price_unit_sum})
            #                         else:
            #                             record.sudo().write(
            #                                 {'purchase_value_in_lot': convert_price})
            #                         # record.sudo().write(
            #                         #     {'location_id': line.destination_warehouse_id.lot_stock_id.id})
            #                         # putaway_exists = self.env['stock.putaway.rule'].search(
            #                         #     [('location_in_id', '=', line.destination_warehouse_id.lot_stock_id.id)])
            #                         # for rule in putaway_exists:
            #                         #     if record.product_id.id in rule.product_ids.ids:
            #                         #         record.sudo().write(
            #                         #             {'location_id': rule.location_out_id.id})
            #             else:
            #                 inventory_line = self.env['stock.inventory.line'].search([('prod_lot_id', '=', record.lot_id.id)],order='id asc')
            #                 price_unit_sum = 0
            #                 harga_awal = 0
            #                 for line in inventory_line:
            #                     if line.product_id.id == record.lot_id.product_id.id:
            #                         if line.unit_price and line.difference_qty >= 1:
            #                             harga_awal = line.unit_price
            #                         if line.unit_price and line.difference_qty:
            #                             price_unit_sum = price_unit_sum + (line.unit_price * line.difference_qty)
            #                         else:
            #                             price_unit_sum = price_unit_sum + (harga_awal * line.difference_qty)
            #                         record.sudo().write(
            #                             {'purchase_value_in_lot': price_unit_sum})
            #                         # record.sudo().write(
            #                         #     {'location_id': line.location_id.id})
            #                         # putaway_exists = self.env['stock.putaway.rule'].search(
            #                         #     [('location_in_id', '=', line.location_id.id)])
            #                         # for rule in putaway_exists:
            #                         #     if record.product_id.id in rule.product_ids.ids:
            #                         #         record.sudo().write(
            #                         #             {'location_id': rule.location_out_id.id})
            #         else:
            #             svl = self.env['stock.valuation.layer'].search([('product_id', '=', record.product_id.id),
            #                                                             ('location_id', '=', record.location_id.id),
            #                                                             ('company_id','=', record.company_id.id)])
            #             record.purchase_value_in_lot = sum(svl.mapped('value'))
            #     # if procut category cost method = standard
            #     else:
            #         if record.lot_id.product_id.tracking == 'serial' or record.lot_id.product_id.tracking == 'lot':
            #             if record.lot_id.purchase_order_ids.order_line:
            #                 for line in record.lot_id.purchase_order_ids.order_line:
            #                     if line.product_id.id == record.lot_id.product_id.id:
            #                         inventory_line = self.env['stock.inventory.line'].search([('prod_lot_id', '=', record.lot_id.id)])
            #                         price_unit_sum = sum(inventory_line.mapped('unit_price')) * sum(inventory_line.mapped('difference_qty'))
            #                         convert_price = line.order_id.currency_id._convert(
            #                             line.price_unit, self.env.company.currency_id, self.env.company, record.in_date, round=False) * record.quantity
            #                         if price_unit_sum:
            #                             record.sudo().write(
            #                                 {'purchase_value_in_lot': line.price_unit + price_unit_sum})
            #                         else:
            #                             record.sudo().write(
            #                                 {'purchase_value_in_lot': convert_price})
            #             else:
            #                 inventory_line = self.env['stock.inventory.line'].search([('prod_lot_id', '=', record.lot_id.id)],order='id asc')
            #                 price_unit_sum = 0
            #                 harga_awal = 0
            #                 for line in inventory_line:
            #                     if line.product_id.id == record.lot_id.product_id.id:
            #                         if line.unit_price and line.difference_qty >= 1:
            #                             harga_awal = line.unit_price
            #                         if line.unit_price and line.difference_qty:
            #                             price_unit_sum = price_unit_sum + (line.unit_price * line.difference_qty)
            #                         else:
            #                             price_unit_sum = price_unit_sum + (harga_awal * line.difference_qty)
            #                         record.sudo().write(
            #                             {'purchase_value_in_lot': price_unit_sum})
            #         else:
            #             svl = self.env['stock.valuation.layer'].search([('product_id', '=', record.product_id.id),
            #                                                         ('location_id', '=', record.location_id.id),
            #                                                         ('company_id','=', record.company_id.id)])
            #             record.purchase_value_in_lot = sum(svl.mapped('value'))

    def _calculate_expire_day(self):
        today_date = datetime.now()
        for record in self:
            record.expire_days = ""
            record.expire_days_count = 0
            if record.expire_date:
                difference = record.expire_date - today_date
                record.expire_days_count = difference.days
                if difference.days > 0:
                    record.expire_days = str(difference.days) + " Days"
                elif difference.days == 0:
                    record.expire_days = "Today"
                else:
                    record.expire_days = str(
                        abs(difference.days)) + " Days Ago"

    @api.depends('lot_id.expiration_date', 'lot_id')
    def _compute_lots_expire_date(self):
        for record in self:
            if record.lot_id.id == False:
                record.expire_date = False
            else:
                record.expire_date = record.lot_id.expiration_date

    @api.depends('location_id')
    def get_cluster_area(self):
        for record in self:
            warehouse_id = record.location_id.get_warehouse().id
            cluster_warehouse_line = self.env['cluster.warehouse.line'].search(
                [('warehouse_id', '=', warehouse_id)], limit=1)
            if cluster_warehouse_line:
                record.cluster_area_id = cluster_warehouse_line.cluster_id.id


    @api.model
    def get_warehouse_values(self, values=None):
        if values is None:
            values = dict()

        warehouse = values.get('warehouse', False)
        if not warehouse:
            location = False
        else:
            location = values.get('location', False)

        if not location:
            brand = False
            product_category = False
            lot = False
            product_code = False
            product_name = False
            sold_product = False
            minus_stock = False
            fsn_color = False
        else:
            brand = values.get('brand', False)
            product_category = values.get('product_category', False)
            lot = values.get('lot', False)
            product_code = values.get('product_code', False)
            product_name = values.get('product_name', False)
            sold_product = values.get('sold_product', False)
            minus_stock = values.get('minus_stock', False)
            fsn_color = values.get('fsn_color', False)

        return {
            'warehouse': warehouse,
            'location': location,
            'brand': brand,
            'product_category': product_category,
            'lot': lot,
            'product_code': product_code,
            'product_name': product_name,
            'sold_product': sold_product,
            'minus_stock': minus_stock,
            'fsn_color': fsn_color
        }

    @api.model
    def get_warehouse_based_product(self, **kwargs):
        warehouse_id = kwargs.get('warehouse_id', False)
        location_ids = kwargs.get('location_ids', [])
        brands = kwargs.get('brand_names', [])
        product_category_ids = kwargs.get('product_category_ids', [])
        lot_ids = kwargs.get('lot_ids', [])
        product_codes = kwargs.get('product_codes', [])
        product_names = kwargs.get('product_names', [])
        minus_stock = kwargs.get('minus_stock', False)

        if not warehouse_id:
            return []

        domain = [('company_id', '=', self.env.company.id)]
        if location_ids:
            domain += [('location_id', 'in', location_ids)]
        else:
            domain += [('location_id', 'in', self.env['stock.location'].search(
                [('warehouse_id', '=', warehouse_id)]).ids)]

        if brands:
            for i in range(0, len(brands)-1):
                domain += ['|']
            for brand in brands:
                domain += [('product_id.product_brand_ids.brand_name', 'ilike', brand)]

        if product_category_ids:
            domain += [('product_id.categ_id', 'in', product_category_ids)]

        if lot_ids:
            domain += [('lot_id', 'in', lot_ids)]
        if product_codes:
            for i in range(0, len(product_codes)-1):
                domain += ['|']
            for code in product_codes:
                domain += [('product_id.default_code', 'ilike', code)]
        if product_names:
            for i in range(0, len(product_names)-1):
                domain += ['|']
            for name in product_names:
                domain += [('product_id.product_display_name', 'ilike', name)]

        quant_ids = self.search(domain)

        product_ids = quant_ids.mapped('product_id')
        if location_ids:
            product_ids = product_ids.with_context(location=location_ids)
        elif warehouse_id:
            product_ids = product_ids.with_context(warehouse=warehouse_id)

        res = product_ids._compute_quantities_dict(None, None, None)

        if minus_stock:
            allowed_product_ids = [product_id for product_id in res.keys(
            ) if res[product_id]['qty_available'] < 0 or res[product_id]['free_qty'] < 0]
        else:
            # allowed_product_ids = [product_id for product_id in res.keys() if res[product_id]['qty_available'] >= 0 and res[product_id]['free_qty'] >= 0]
            allowed_product_ids = [product_id for product_id in res.keys()]

        return quant_ids.filtered(lambda q: q.product_id.id in allowed_product_ids).ids

    # @api.model
    # def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
    #     """ This override is done in order for the grouped list view to display the total value of
    #     the quants inside a location. This doesn't work out of the box because `value` is a computed
    #     field.
    #     """
    #     if 'purchase_value_in_lot' not in fields:
    #         return super(StockQuant, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    #     res = super(StockQuant, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    #     for group in res:
    #         if group.get('__domain'):
    #             quants = self.search(group['__domain'])
    #             group['purchase_value_in_lot'] = sum(quant.purchase_value_in_lot for quant in quants)
    #     return res
