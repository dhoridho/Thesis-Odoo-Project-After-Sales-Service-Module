# -*- coding: utf-8 -*-
from odoo import models, api, fields
from dateutil.relativedelta import relativedelta


class StockQuant(models.Model):
    _inherit = "stock.quant"

    # @api.depends_context('inv_warehouse', 'inv_location')
    # def _compute_inv_reports_warehouse_quantities(self):
    #     context = self.env.context
    #     warehouse = context.get('inv_warehouse', False)
    #     location = context.get('inv_location', False)
    #     context_data_dict = {}
    #     if location:
    #         context_data_dict.update({'location': location})
    #     elif warehouse:
    #         context_data_dict.update({'warehouse': warehouse})

    #     for record in self:
    #         lot_id = record.lot_id and record.lot_id.id or None
    #         res = record.product_id.with_context(context_data_dict)._compute_quantities_dict(lot_id, None, None)
    #         product_id = record.product_id

    #         inv_report_qty_sec = 0
    #         inv_report_qty_ref = 0
    #         qty_available = res[product_id.id]['qty_available']
    #         incoming_qty = res[product_id.id]['incoming_qty']
    #         outgoing_qty = res[product_id.id]['outgoing_qty']
    #         virtual_available = res[product_id.id]['virtual_available']
    #         free_qty = res[product_id.id]['free_qty']

    #         inv_report_ref = product_id.product_tmpl_id.uom_id.category_id.id
    #         inv_report_sec = product_id.product_tmpl_id.secondary_uom_id.id
    #         if product_id.product_tmpl_id.uom_id.uom_type == 'bigger':
    #             inv_report_qty_ref = qty_available * product_id.product_tmpl_id.uom_id.factor_inv
    #         if product_id.product_tmpl_id.uom_id.uom_type == 'reference':
    #             inv_report_qty_ref = qty_available
    #         if product_id.product_tmpl_id.uom_id.uom_type == 'smaller':
    #             inv_report_qty_ref = qty_available / product_id.product_tmpl_id.uom_id.factor
    #         if product_id.product_tmpl_id.secondary_uom_id.uom_type == 'bigger':
    #             inv_report_qty_sec = inv_report_qty_ref / product_id.product_tmpl_id.secondary_uom_id.factor_inv
    #         if product_id.product_tmpl_id.secondary_uom_id.uom_type == 'reference':
    #             inv_report_qty_sec = inv_report_qty_ref
    #         if product_id.product_tmpl_id.secondary_uom_id.uom_type == 'smaller':
    #             inv_report_qty_sec = inv_report_qty_ref * product_id.product_tmpl_id.secondary_uom_id.factor
    #         record.inv_report_qty_available = qty_available
    #         record.inv_report_incoming_qty = incoming_qty
    #         record.inv_report_outgoing_qty = outgoing_qty
    #         record.inv_report_virtual_available = virtual_available
    #         record.inv_report_free_qty = free_qty
    #         record.inv_report_qty_ref = inv_report_qty_ref
    #         record.inv_report_ref = inv_report_ref
    #         record.inv_report_qty_sec = inv_report_qty_sec
    #         record.inv_report_sec = inv_report_sec

    # @api.depends_context('inv_warehouse', 'inv_sold_product')
    # def _compute_inv_reports_sales(self):
    #     context = self.env.context
    #     warehouse = context.get('inv_warehouse', False)
    #     sold_product = context.get('inv_sold_product', False)

    #     self.inv_report_hide_sales = not sold_product
    #     if not warehouse or not sold_product:
    #         self.inv_report_sales = 0
    #         self.inv_report_stock_movement = ''
    #         return

    #     warehouse_ids = {warehouse} if warehouse else {}
    #     end_date = fields.Date.today()
    #     start_date = end_date - relativedelta(days=sold_product)

    #     query = """
    #         SELECT * FROM get_inventory_fsn_analysis_report('%s','%s','%s','%s','%s','%s', '%s')
    #     """ % ({self.env.company.id}, {}, {}, warehouse_ids, start_date, end_date, 'all')
    #     self._cr.execute(query)
    #     stock_data = self._cr.dictfetchall()

    #     res = {}
    #     for data in stock_data:
    #         res[data.get('product_id', False)] = {
    #             'sales': data.get('sales', 0.0),
    #             'stock_movement': data.get('stock_movement', ''),
    #         }

    #     for record in self:
    #         product_id = record.product_id
    #         record.inv_report_sales = res.get(product_id.id, {}).get('sales', 0.0)
    #         record.inv_report_stock_movement = res.get(product_id.id, {}).get('stock_movement', 0.0)

    # inv_report_qty_available = fields.Float(compute=_compute_inv_reports_warehouse_quantities)
    # inv_report_incoming_qty = fields.Float(compute=_compute_inv_reports_warehouse_quantities)
    # inv_report_outgoing_qty = fields.Float(compute=_compute_inv_reports_warehouse_quantities)
    # inv_report_virtual_available = fields.Float(compute=_compute_inv_reports_warehouse_quantities)
    # inv_report_free_qty = fields.Float(compute=_compute_inv_reports_warehouse_quantities)
    # inv_report_qty_ref = fields.Float(string="Quantity On Hand Reference UoM", compute=_compute_inv_reports_warehouse_quantities)
    # inv_report_ref = fields.Many2one('uom.category', string= "Reference UoM", compute=_compute_inv_reports_warehouse_quantities)
    # inv_report_qty_sec = fields.Float(string="Quantity On Hand Secondary UoM", compute=_compute_inv_reports_warehouse_quantities)
    # inv_report_sec = fields.Many2one('uom.uom', string= "Secondary UoM", compute=_compute_inv_reports_warehouse_quantities)
    # inv_report_sales = fields.Float(string= "Sales", compute=_compute_inv_reports_sales)
    # inv_report_stock_movement = fields.Char(string='Stock Movement', compute=_compute_inv_reports_sales)
    # inv_report_default_code = fields.Char(related='product_id.default_code', string='Product Code')
    # inv_report_hide_sales = fields.Boolean(compute=_compute_inv_reports_sales)

    # @api.model
    # def get_warehouse_values(self, values=None):
    #     if values is None:
    #         values = dict()

    #     warehouse = values.get('warehouse', False)
    #     if not warehouse:
    #         location = False
    #     else:
    #         location = values.get('location', False)

    #     if not location:
    #         brand = False
    #         product_category = False
    #         lot = False
    #         product_code = False
    #         product_name = False
    #         sold_product = False
    #         minus_stock = False
    #         fsn_color = False
    #     else:
    #         brand = values.get('brand', False)
    #         product_category = values.get('product_category', False)
    #         lot = values.get('lot', False)
    #         product_code = values.get('product_code', False)
    #         product_name = values.get('product_name', False)
    #         sold_product = values.get('sold_product', False)
    #         minus_stock = values.get('minus_stock', False)
    #         fsn_color = values.get('fsn_color', False)

    #     return {
    #         'warehouse': warehouse,
    #         'location': location,
    #         'brand': brand,
    #         'product_category': product_category,
    #         'lot': lot,
    #         'product_code': product_code,
    #         'product_name': product_name,
    #         'sold_product': sold_product,
    #         'minus_stock': minus_stock,
    #         'fsn_color': fsn_color
    #     }

    # @api.model
    # def get_warehouse_based_product(self, **kwargs):
    #     warehouse_id = kwargs.get('warehouse_id', False)
    #     location_ids = kwargs.get('location_ids', [])
    #     brands = kwargs.get('brand_names', [])
    #     product_category_ids = kwargs.get('product_category_ids', [])
    #     lot_ids = kwargs.get('lot_ids', [])
    #     product_codes = kwargs.get('product_codes', [])
    #     product_names = kwargs.get('product_names', [])
    #     minus_stock = kwargs.get('minus_stock', False)

    #     if not warehouse_id:
    #         return []

    #     domain = [('company_id', '=', self.env.company.id)]
    #     if location_ids:
    #         domain += [('location_id', 'in', location_ids)]
    #     else:
    #         domain += [('location_id', 'in', self.env['stock.location'].search([('warehouse_id', '=', warehouse_id)]).ids)]

    #     if brands:
    #         for i in range(0, len(brands)-1):
    #             domain += ['|']
    #         for brand in brands:
    #             domain += [('product_id.product_template_attribute_value_ids.name', 'ilike', brand)]

    #     if product_category_ids:
    #         domain += [('product_id.categ_id','in', product_category_ids)]

    #     if lot_ids:
    #         domain += [('lot_id', 'in', lot_ids)]
    #     if product_codes:
    #         for i in range(0, len(product_codes)-1):
    #             domain += ['|']
    #         for code in product_codes:
    #             domain += [('product_id.default_code', 'ilike', code)]
    #     if product_names:
    #         for i in range(0, len(product_names)-1):
    #             domain += ['|']
    #         for name in product_names:
    #             domain += [('product_id.product_display_name', 'ilike', name)]

    #     quant_ids = self.search(domain)

    #     product_ids = quant_ids.mapped('product_id')
    #     if location_ids:
    #         product_ids = product_ids.with_context(location=location_ids)
    #     elif warehouse_id:
    #         product_ids = product_ids.with_context(warehouse=warehouse_id)

    #     res = product_ids._compute_quantities_dict(None, None, None)

    #     if minus_stock:
    #         allowed_product_ids = [product_id for product_id in res.keys() if res[product_id]['qty_available'] < 0 or res[product_id]['free_qty'] < 0]
    #     else:
    #         # allowed_product_ids = [product_id for product_id in res.keys() if res[product_id]['qty_available'] >= 0 and res[product_id]['free_qty'] >= 0]
    #         allowed_product_ids = [product_id for product_id in res.keys()]

    #     return quant_ids.filtered(lambda q: q.product_id.id in allowed_product_ids).ids
