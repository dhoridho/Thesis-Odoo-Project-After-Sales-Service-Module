from odoo import tools
from odoo import api, fields, models


class MaterialUsageReport(models.Model):
    _name = "material.usage.report"
    _description = "Material Usage Report"
    _auto = False

    consumption_id = fields.Many2one('mrp.consumption', 'Production Record', readonly=True)
    workorder_id = fields.Many2one('mrp.workorder', 'Production Work Order', readonly=True)
    production_id = fields.Many2one('mrp.production', 'Production Order', readonly=True)
    plan_id = fields.Many2one('mrp.plan', 'Production Plan', readonly=True)

    to_consume = fields.Float('To Consume', readonly=True)
    consumed = fields.Float('Consumed', readonly=True)
    difference = fields.Float('Difference', readonly=True)
    value = fields.Float('Value', readonly=True)
    
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    branch_id = fields.Many2one('res.branch', 'Branch', readonly=True)
    product_id = fields.Many2one('product.product', 'Material', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    create_date = fields.Datetime(string='Create On', readonly=True)
    create_uid = fields.Many2one('res.users', string='Create By', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
        SELECT
            sm.id AS id,
            sm.mrp_consumption_id AS consumption_id,
            sm.mrp_workorder_component_id AS workorder_id,
            sm.raw_material_production_id AS production_id,
            sm.mrp_plan_id AS plan_id,
            sm.company_id AS company_id,
            sm.branch_id AS branch_id,
            sm.product_id AS product_id,
            sm.product_uom AS product_uom,
            sm.warehouse_id AS warehouse_id,
            sm.create_date AS create_date,
            sm.create_uid AS create_uid,
            sm.product_uom_qty AS to_consume,
            sm.quantity_done AS consumed,
            sm.product_uom_qty - sm.quantity_done AS difference,
            ABS(svl.value) AS value
        FROM
            stock_move sm
        LEFT JOIN
            stock_valuation_layer svl ON (sm.id = svl.stock_move_id AND svl.type = 'component')
        WHERE
            sm.state != 'draft' AND sm.raw_material_production_id IS NOT NULL
        """
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, query))
