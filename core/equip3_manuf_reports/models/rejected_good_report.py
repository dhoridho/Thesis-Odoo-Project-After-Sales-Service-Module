from odoo import fields, models, tools,_


class RejectedGoodReport(models.Model):
    _name = "rejected.good.report"
    _inherit = "finished.good.report"
    _description = "Rejected Goods Report"

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
            sm.state != 'draft' AND sm.production_id IS NOT NULL AND sm.byproduct_id IS NULL AND sm.is_mpr_rejected IS True
        """
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, query))
