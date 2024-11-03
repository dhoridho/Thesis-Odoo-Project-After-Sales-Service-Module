from odoo import models, api, fields


class SetuInventoryOutOfStockReport(models.TransientModel):

    _inherit = 'setu.inventory.outofstock.report'

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    company_ids = fields.Many2many(
        default=lambda self: self.env.user.company_id.ids)

    def download_report_in_listview(self):
        rec = super(SetuInventoryOutOfStockReport,
                    self).download_report_in_listview()
        rec.update({'name': ("Inventory Demand Forecast Analysis")})
        return rec

    def get_file_name(self):
        filename = "inventory_demand_forecast_analysis.xlsx"
        return filename


class SetuInventoryOverstockReport(models.TransientModel):
    _inherit = 'setu.inventory.overstock.report'

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    company_ids = fields.Many2many(
        default=lambda self: self.env.user.company_id.ids)


class SetuInventoryTurnoverReport(models.TransientModel):

    _inherit = 'setu.inventory.turnover.analysis.report'

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    company_ids = fields.Many2many(
        default=lambda self: self.env.user.company_id.ids)


class SetuInventoryFSNReport(models.TransientModel):

    _inherit = 'setu.inventory.fsn.analysis.report'

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    company_ids = fields.Many2many(
        default=lambda self: self.env.user.company_id.ids)


class SetuInventoryXYZReport(models.TransientModel):

    _inherit = 'setu.inventory.xyz.analysis.report'

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    company_ids = fields.Many2many(
        default=lambda self: self.env.user.company_id.ids)


class SetuInventoryFSNXYZReport(models.TransientModel):

    _inherit = 'setu.inventory.fsn.xyz.analysis.report'

    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env.company)
    company_ids = fields.Many2many(
        default=lambda self: self.env.user.company_id.ids)


class SetuInventoryAgeReport(models.TransientModel):
    _inherit = "setu.inventory.age.report"

    warehouse_ids = fields.Many2many("stock.warehouse", string="Warehouses")

    def get_inventory_age_report_data(self):
        """
        :return:
        """
        category_ids = company_ids = {}
        warehouse_ids = {}
        if self.product_category_ids:
            categories = self.env['product.category'].search(
                [('id', 'child_of', self.product_category_ids.ids)])
            category_ids = set(categories.ids) or {}
        products = self.product_ids and set(self.product_ids.ids) or {}

        if self.warehouse_ids:
            warehouse_ids = self.warehouse_ids and set(
                self.warehouse_ids.ids) or {}

        if self.company_ids:
            companies = self.env['res.company'].search(
                [('id', 'child_of', self.company_ids.ids)])
            company_ids = set(companies.ids) or {}
        else:
            company_ids = set(self.env.context.get(
                'allowed_company_ids', False) or self.env.user.company_ids.ids) or {}
        query = """
                Select * from inventory_stock_age_report_inv('%s','%s','%s','%s')
            """ % (company_ids, products, category_ids, warehouse_ids)
        self._cr.execute(query)
        stock_data = self._cr.dictfetchall()
        return stock_data
