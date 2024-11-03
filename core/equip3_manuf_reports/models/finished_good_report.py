from odoo import tools
from odoo import api, fields, models


class FinishedGoodsReport(models.Model):
    _name = "finished.good.report"
    _description = "Finished Goods Report"
    _auto = False

    consumption_id = fields.Many2one('mrp.consumption', 'Production Record', readonly=True)
    workorder_id = fields.Many2one('mrp.workorder', 'Production Work Order', readonly=True)
    production_id = fields.Many2one('mrp.production', 'Production Order', readonly=True)
    plan_id = fields.Many2one('mrp.plan', 'Production Plan', readonly=True)

    to_produce = fields.Float('To Produce', readonly=True)
    produced = fields.Float('Produced', readonly=True)
    difference = fields.Float('Difference', readonly=True)
    value = fields.Float('Value', readonly=True)
    
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    branch_id = fields.Many2one('res.branch', 'Branch', readonly=True)
    product_id = fields.Many2one('product.product', 'Finished Good', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    create_date = fields.Datetime(string='Create On', readonly=True)
    create_uid = fields.Many2one('res.users', string='Create By', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
        SELECT
            sm.id AS id,
            sm.mrp_consumption_finished_id AS consumption_id,
            sm.workorder_id AS workorder_id,
            sm.production_id AS production_id,
            sm.mrp_plan_id AS plan_id,
            sm.company_id AS company_id,
            sm.branch_id AS branch_id,
            sm.product_id AS product_id,
            sm.product_uom AS product_uom,
            sm.warehouse_id AS warehouse_id,
            sm.create_date AS create_date,
            sm.create_uid AS create_uid,
            mp.product_qty AS to_produce,
            sm.quantity_done AS produced,
            mp.product_qty - sm.quantity_done AS difference,
            svl.value AS value
        FROM
            stock_move sm
        LEFT JOIN
            mrp_production mp ON (mp.id = sm.production_id)
        LEFT JOIN
            stock_valuation_layer svl ON (sm.id = svl.stock_move_id AND svl.type = 'finished')
        WHERE
            sm.state != 'draft' AND sm.production_id IS NOT NULL AND sm.byproduct_id IS NULL AND sm.is_mpr_rejected IS NOT True
        """
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, query))
