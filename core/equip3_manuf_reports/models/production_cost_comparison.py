from odoo import models, fields, api, tools, _


COST_TYPE_SEQ = {
    'finished': 1,
    'component': 2,
    'overhead': 3,
    'labor': 4,
    'subcontracting': 5,
    'byproduct': 6
}


class ProductionCostComparison(models.Model):
    _name = 'production.cost.comparison'
    _description = 'Production Cost Comparison'
    _auto = False

    company_id = fields.Many2one('res.company', string='Company')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    production_id = fields.Many2one('mrp.production', string='Production Order')
    production_create_date = fields.Datetime(string='Production Create Date')
    name = fields.Char()
    uom_name = fields.Char(string='UoM')
    type = fields.Selection(selection=[
        ('finished', 'Finished Goods'),
        ('byproduct', 'By-Product'),
        ('component', 'Material'),
        ('overhead', 'Overhead'),
        ('labor', 'Labor'),
        ('subcontracting', 'Subcontracting')
    ], string='Type')
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')
    cost = fields.Monetary(string='Cost')
    actual_quantity = fields.Float(string='Actual Quantity', digits='Product Unit of Measure')
    actual_cost = fields.Monetary(string='Actual Cost')
    
    def _query(self):
        return """
        SELECT
            ROW_NUMBER() OVER(
                ORDER BY 
                    mp.company_id,
                    mp.id DESC,
                    CASE
                        WHEN report.type = 'finished' THEN 0
                        WHEN report.type = 'component' THEN 1
                        WHEN report.type = 'overhead' THEN 2
                        WHEN report.type = 'labor' THEN 3
                        WHEN report.type = 'subcontracting' THEN 4
                        WHEN report.type = 'byproduct' THEN 5
                        ELSE 6
                    END
            ) AS id,
            mp.company_id,
            mp.id AS production_id,
            mp.create_date AS production_create_date,
            report.type,
            report.record,
            report.user_id,
            CASE
                WHEN COUNT(report.mec_name) > 0 THEN STRING_AGG(DISTINCT(report.mec_name), ',')
                ELSE STRING_AGG(DISTINCT(report.svl_name), ',')
            END AS name,
            STRING_AGG(DISTINCT(report.uom_name), ',') AS uom_name,
            SUM(report.quantity) AS quantity,
            SUM(report.cost) AS cost,
            SUM(report.actual_quantity) AS actual_quantity,
            SUM(report.actual_cost) AS actual_cost
        FROM
            -- mrp.estimated.cost
            (SELECT
                mec.production_id,
                mec.type,
                CASE
                    WHEN mec.type NOT IN ('labor', 'overhead') THEN 'product.product,' || mec.product_id::character varying
                    ELSE 'mrp.routing.workcenter,' || mec.operation_id::character varying
                END AS record,
                mec.user_id,
                mec.name AS mec_name,
                NULL AS svl_name,
                CASE
                    WHEN mec.type IN ('labor', 'overhead') THEN 'Minutes'
                    ELSE uom.name
                END AS uom_name,
                mec.product_qty AS quantity,
                mec.total_cost AS cost,
                0.0 AS actual_quantity,
                0.0 AS actual_cost
            FROM
                mrp_estimated_cost mec
                LEFT JOIN
                    product_product pp
                    ON (pp.id = mec.product_id)
                LEFT JOIN
                    product_template pt
                    ON (pt.id = pp.product_tmpl_id)
                LEFT JOIN
                    uom_uom uom
                    ON (uom.id = pt.uom_id)

            UNION ALL
            
            -- finished, component, & byproduct
            SELECT
                svl.mrp_production_id AS production_id,
                CASE
                    WHEN LEFT(svl.type, 4) != 'mca_' THEN svl.type
                    WHEN svl.product_id = mp.product_id THEN 'finished'
                    WHEN svl.value > 0.0 THEN 'byproduct'
                    WHEN svl.value < 0.0 THEN 'component'
                END AS type,
                CASE
                    WHEN LEFT(svl.type, 4) = 'mca_' AND svl.value < 0.0 THEN 'product.product,' || mec.product_id::character varying
                    ELSE 'product.product,' || svl.product_id::character varying
                END AS record,
                NULL AS user_id,
                NULL AS mec_name,
                svl.description AS svl_name,
                NULL AS uom_name,
                0.0 AS quantity,
                0.0 AS cost,
                ABS(CASE
                    WHEN LEFT(svl.type, 4) = 'mca_' AND svl.value < 0.0 THEN 
                        svl.quantity / (SELECT CASE WHEN COUNT(*) = 0 THEN 1 ELSE COUNT(*) END
                        FROM mrp_estimated_cost mec 
                        WHERE mec.type = 'component' AND mec.production_id = svl.mrp_production_id)
                    ELSE svl.quantity
                END) AS actual_quantity,
                ABS(CASE
                    WHEN LEFT(svl.type, 4) = 'mca_' AND svl.value < 0.0 THEN 
                        svl.value / (SELECT CASE WHEN COUNT(*) = 0 THEN 1 ELSE COUNT(*) END
                        FROM mrp_estimated_cost mec 
                        WHERE mec.type = 'component' AND mec.production_id = svl.mrp_production_id)
                    ELSE svl.value
                END) AS actual_cost
            FROM
                stock_valuation_layer svl
                LEFT JOIN
                    mrp_estimated_cost mec
                    ON (mec.type = 'component' AND mec.production_id = svl.mrp_production_id AND LEFT(svl.type, 4) = 'mca_' AND svl.value < 0.0)
                LEFT JOIN
                    mrp_production mp
                    ON (svl.mrp_production_id = mp.id)
            
            UNION ALL

            -- overhead, labor, & subcontracting
            SELECT
                svl_op.mrp_production_id AS production_id,
                REPLACE(svl_op.type, 'mca_', '') AS type,
                CASE
                    WHEN svl_op.type IN ('mca_overhead', 'mca_labor') THEN 'mrp.routing.workcenter,' || op_rel.operation_id::character varying
                    ELSE 'product.product,' || svl_op.product_id::character varying
                END AS record,
                CASE
                    WHEN svl_op.type = 'mca_labor' THEN labor_rel.user_id
                    ELSE NULL
                END AS user_id,
                NULL AS mec_name,
                CASE
                    WHEN svl_op.type IN ('mca_overhead', 'mca_labor') THEN NULL
                    ELSE '[' || pt_op.default_code || '] ' || pt_op.name
                END AS svl_name,
                CASE
                    WHEN svl_op.type IN ('mca_overhead', 'mca_labor') THEN NULL
                    ELSE uom_op.name
                END AS uom_name,
                0.0 AS quantity,
                0.0 AS cost,
                0.0 AS actual_quantity,
                ABS(CASE
                    WHEN svl_op.type = 'mca_labor' THEN 
                        svl_op.value / (SELECT CASE WHEN COUNT(*) = 0 THEN 1 ELSE COUNT(*) END
                        FROM svl_mca_labor_rel rel 
                        WHERE rel.svl_id = svl_op.id)
                    WHEN svl_op.type = 'mca_overhead' THEN 
                        svl_op.value / (SELECT CASE WHEN COUNT(*) = 0 THEN 1 ELSE COUNT(*) END
                        FROM svl_mca_operation_rel rel 
                        WHERE rel.svl_id = svl_op.id)
                    ELSE svl_op.value
                END) AS actual_cost
            FROM
                stock_valuation_layer svl_op
                LEFT JOIN
                    svl_mca_operation_rel op_rel
                    ON (op_rel.svl_id = svl_op.id AND svl_op.type IN ('mca_overhead', 'mca_labor'))
                LEFT JOIN
                    svl_mca_labor_rel labor_rel
                    ON (labor_rel.svl_id = svl_op.id AND svl_op.type = 'mca_labor')
                LEFT JOIN
                    product_product pp_op
                    ON (pp_op.id = svl_op.product_id)
                LEFT JOIN
                    product_template pt_op
                    ON (pt_op.id = pp_op.product_tmpl_id)
                LEFT JOIN
                    uom_uom uom_op
                    ON (uom_op.id = pt_op.uom_id)
            WHERE
                svl_op.type IN ('mca_overhead', 'mca_labor', 'mca_subcontracting') AND svl_op.value < 0.0
            ) report
            
            LEFT JOIN
                mrp_production mp
                ON (mp.id = report.production_id)

        WHERE
            mp.state = 'done'

        GROUP BY
            mp.company_id,
            mp.id,
            report.type,
            report.record,
            report.user_id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if self.env.context.get('production_cost_comparison_order', False):
            orderbys = []
            if 'production_create_date:month' in groupby:
                orderbys += ['production_create_date desc']
            if 'production_id' in groupby:
                orderbys += ['production_id desc']
            if orderbys:
                orderby = ','.join(orderbys)
        
        res = super(ProductionCostComparison, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        
        if self.env.context.get('production_cost_comparison_order', False):
            if groupby == ['type']:
                res.sort(key=lambda o: COST_TYPE_SEQ.get(o.get('type'), 7))
        return res
