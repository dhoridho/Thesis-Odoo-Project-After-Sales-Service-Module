from datetime import datetime

from odoo import fields, models, api, _

class SetuInventoryLedger(models.TransientModel):
    _name = 'setu.inventory.ledger.report'
    _description = "Inventory Ledger Report"

    stock_file_data = fields.Binary('Stock Movement File')
    start_date = fields.Date(string="Start Date", default=datetime.today().replace(day=1))
    end_date = fields.Date(string="End Date", default=datetime.today())
    product_category_ids = fields.Many2many("product.category", string  ="Product Categories")
    product_ids = fields.Many2many("product.product", string="Products")
    warehouse_ids = fields.Many2many("stock.warehouse", string="Warehouses")
    # stock_location = fields.Many2many("stock.location", string="Stock Location")
    company_ids = fields.Many2many("res.company", string="Companies")
    report_by = fields.Selection([('company_wise', 'Company'),
                                    ('warehouse_wise', 'Warehouse')], "Report by", default="warehouse_wise")

    @api.onchange('company_ids')
    def onchange_company_id(self):
        if self.company_ids:
            return {'domain': {'warehouse_ids': [('partner_id', 'child_of', self.company_ids.mapped('partner_id').ids)]}}

    @api.onchange('product_category_ids')
    def onchange_product_category_id(self):
        if self.product_category_ids:
            return {'domain': {'product_ids': [('categ_id', 'child_of', self.product_category_ids.ids)]}}

    def download_report_in_listview(self):
        stock_data = self.get_products_movements_for_inventory_ledger()
        print(stock_data)
        for ledger_data_value in stock_data:
            ledger_data_value['wizard_id'] = self.id
            self.create_data(ledger_data_value)

        # graph_view_id = self.env.ref('setu_inventory_ledger_report.setu_inventory_fsn_analysis_bi_report_graph').id
        tree_view_id = self.env.ref('setu_inventory_ledger_report.setu_inventory_ledger_bi_report_tree').id
        tree_view_id_cmpwise = self.env.ref('setu_inventory_ledger_report.setu_inventory_ledger_bi_report_tree_cmpwise').id
        form_view_id = self.env.ref('setu_inventory_ledger_report.setu_inventory_ledger_bi_report_form').id
        # is_graph_first = self.env.context.get('graph_report', False)
        report_display_views = []
        viewmode = ''
        tree_id = tree_view_id
        if self.report_by == 'company_wise':
            tree_id = tree_view_id_cmpwise

        report_display_views.append((tree_id, 'tree'))
        report_display_views.append((form_view_id, 'form'))
        viewmode = "tree,form"
        return {
            'name': _('Invetory Ledger Report - %s to %s' % (self.start_date, self.end_date)),
            'domain': [('wizard_id', '=', self.id)],
            'res_model': 'setu.inventory.ledger.bi.report',
            'view_mode': viewmode,
            'type': 'ir.actions.act_window',
            'views': report_display_views,
            'context': {'search_default_product_groupby':1},
            'help' : """
                <p class="o_view_nocontent_smiling_face">
                    No data found.
                </p>
            """
        }

    def create_data(self, data):
        del data['product_name']
        del data['company_name']
        if self.report_by == 'warehouse_wise':
            del data['warehouse_name']
        del data['row_id']
        del data['category_name']
        # domain1 = []
        # from_date = data.get('inventory_date').strftime('%Y-%m-%d') + " 00:00:00"
        # to_date = data.get('inventory_date').strftime('%Y-%m-%d') + " 23:59:59"
        # domain = [('state', '=', 'done'), ('product_id', '=', data.get('product_id')), ('date', '>=', from_date),
        #           ('date', '<=', to_date)]
        # if self.report_by == "company_wise":
        #     domain.append(('company_id', '=', data.get('company_id')))
        # else:
        #     warehouse = self.env['stock.warehouse'].browse(data.get('warehouse_id'))
        #     location_ids = self.env['stock.location'].search(
        #         [('id', 'child_of', warehouse.view_location_id.id)]).ids
        #     domain1 = ['|', ('location_id', 'in', location_ids), ('location_dest_id', 'in', location_ids)]
        #
        # move_ids = self.env['stock.move'].search(domain + domain1).ids
        # if move_ids:
        #     data.update({'ledger_detail_ids': [(6, 0, move_ids)]})
        return self.env['setu.inventory.ledger.bi.report'].create(data)

    def get_products_movements_for_inventory_ledger(self):
        """
        :return:
        """
        start_date = self.start_date
        end_date = self.end_date
        category_ids = company_ids = {}
        if self.product_category_ids:
            categories = self.env['product.category'].search([('id','child_of',self.product_category_ids.ids)])
            category_ids = set(categories.ids) or {}
        products = self.product_ids and set(self.product_ids.ids) or {}

        if self.company_ids:
            companies = self.env['res.company'].search([('id','child_of',self.company_ids.ids)])
            company_ids = set(companies.ids) or {}
        else:
            company_ids = set(self.env.context.get('allowed_company_ids',False) or self.env.user.company_ids.ids) or {}

        warehouses = self.warehouse_ids and set(self.warehouse_ids.ids) or {}

        if self.report_by == 'warehouse_wise':
            # get_products_movements_for_inventory_ledger(integer[], integer[], integer[], integer[], date, date)
            query = """
                    Select * from get_products_movements_for_inventory_ledger('%s','%s','%s','%s','%s','%s')
                """%(company_ids, products, category_ids, warehouses, start_date, end_date)
        else:
            # get_products_movements_for_inventory_ledger_cmpwise(integer[], integer[], integer[], date, date)
            query = """
                    Select * from get_products_movements_for_inventory_ledger_cmpwise('%s','%s','%s','%s','%s')
                """ % (company_ids, products, category_ids, start_date, end_date)
        print(query)
        self._cr.execute(query)
        stock_data = self._cr.dictfetchall()
        return  stock_data

    def prepare_data_to_write(self, stock_data={}):
        """
        :param stock_data:
        :return:
        """
        warehouse_wise_data = {}
        for data in stock_data:
            key = (data.get('warehouse_id'), data.get('warehouse_name'))
            if not warehouse_wise_data.get(key,False):
                warehouse_wise_data[key] = {data.get('product_id') : data}
            else:
                warehouse_wise_data.get(key).update({data.get('product_id') : data})
        return warehouse_wise_data

class SetuInventoryLedgerBIReport(models.TransientModel):
    _name = 'setu.inventory.ledger.bi.report'

    inventory_date = fields.Date("Inventory Date")
    company_id = fields.Many2one("res.company", "Company")
    warehouse_id = fields.Many2one("stock.warehouse", "Warehouse")
    # stock_location = fields.Many2one("stock.location", "Stock Location")
    product_id = fields.Many2one("product.product", "Product")
    product_category_id = fields.Many2one("product.category", "Category")
    opening_stock = fields.Float("Opening Stock")
    wizard_id = fields.Many2one("setu.inventory.ledger.report")
    purchase = fields.Float("Purchase")
    sales = fields.Float("Sales")
    purchase_return = fields.Float("Purchase Return")
    sales_return = fields.Float("Sales Return")
    internal_in = fields.Float("Internal In")
    internal_out = fields.Float("Internal Out")
    adjustment_in = fields.Float("Adjustment In")
    adjustment_out = fields.Float("Adjustment Out")
    production_in = fields.Float("Production In")
    production_out = fields.Float("Production Out")
    transit_in = fields.Float("Transit In")
    transit_out = fields.Float("Transit Out")
    closing = fields.Float("Closing")
    ledger_detail_ids = fields.Many2many("stock.move", string="Product movements", compute='_calculate_ledger_details')
    total_in = fields.Float(string='Total in', store=False, readonly=True, compute='_amount_all')
    total_out = fields.Float(string='Total out', store=False, readonly=True, compute='_amount_all')
    product_movements = fields.Selection([('all',"All"),('purchase',"Purchase"),('purchase_return',"Purchase Return"),
                                          ('sales', "Sales"), ('sales_return', "Sales Return"),
                                          ('internal_in', "Internal in"),('internal_out', "Internal out"),
                                          ('adjustment_in', "Adjustment in"), ('adjustment_out', "Adjustment out"),
                                          ('transit_in', "Transit in"), ('transit_out', "Transit out"),
                                          ('production_in', "Production in"), ('production_out', "Production out"),
                                          ], "Choose movement", default="all")

    @api.depends('product_movements')
    def _calculate_ledger_details(self):
        domain1 = []
        self.ledger_detail_ids = []
        from_date = self.inventory_date.strftime('%Y-%m-%d') + " 00:00:00"
        to_date = self.inventory_date.strftime('%Y-%m-%d') + " 23:59:59"
        domain = [('state', '=', 'done'), ('product_id', '=', self.product_id.id), ('date', '>=', from_date),
                  ('date', '<=', to_date)]
        if self.wizard_id.report_by == "company_wise":
            domain.append(('company_id', '=', self.company_id.id))
        else:
            warehouse = self.env['stock.warehouse'].browse(self.warehouse_id.id)
            location_ids = self.env['stock.location'].search(
                [('id', 'child_of', warehouse.view_location_id.id)]).ids
            domain1 = ['|', ('location_id', 'in', location_ids), ('location_dest_id', 'in', location_ids)]

        if self.product_movements == "purchase":
            domain.append(('location_id.usage','=','supplier'))
            domain.append(('location_dest_id.usage','=','internal'))
        elif self.product_movements == "purchase_return":
            domain.append(('location_id.usage', '=', 'internal'))
            domain.append(('location_dest_id.usage', '=', 'supplier'))
        elif self.product_movements == "sales":
            domain.append(('location_id.usage', '=', 'internal'))
            domain.append(('location_dest_id.usage', '=', 'customer'))
        elif self.product_movements == "sales_return":
            domain.append(('location_id.usage', '=', 'customer'))
            domain.append(('location_dest_id.usage', '=', 'insternal'))
        elif self.product_movements == "internal_in" or self.product_movements == "internal_out":
            domain.append(('location_id.usage', '=', 'internal'))
            domain.append(('location_dest_id.usage', '=', 'internal'))
        elif self.product_movements == "adjustment_in":
            domain.append(('location_id.usage', '=', 'inventory'))
            domain.append(('location_dest_id.usage', '=', 'internal'))
        elif self.product_movements == "adjustment_out":
            domain.append(('location_id.usage', '=', 'internal'))
            domain.append(('location_dest_id.usage', '=', 'inventory'))
        elif self.product_movements == "transit_in":
            domain.append(('location_id.usage', '=', 'transit'))
            domain.append(('location_dest_id.usage', '=', 'internal'))
        elif self.product_movements == "transit_out":
            domain.append(('location_id.usage', '=', 'internal'))
            domain.append(('location_dest_id.usage', '=', 'transit'))
        elif self.product_movements == "production_in":
            domain.append(('location_id.usage', '=', 'production'))
            domain.append(('location_dest_id.usage', '=', 'internal'))
        elif self.product_movements == "production_out":
            domain.append(('location_id.usage', '=', 'internal'))
            domain.append(('location_dest_id.usage', '=', 'production'))

        move_ids = self.env['stock.move'].search(domain + domain1).ids
        if move_ids:
            self.write({'ledger_detail_ids': [(6, 0, move_ids)]})

    def _amount_all(self):
        for movement in self:
            movement.total_in = movement.purchase + movement.sales_return + movement.internal_in + movement.adjustment_in + movement.production_in + movement.transit_in
            movement.total_out = movement.purchase_return + movement.sales + movement.internal_out + movement.adjustment_out + movement.production_out + movement.transit_out