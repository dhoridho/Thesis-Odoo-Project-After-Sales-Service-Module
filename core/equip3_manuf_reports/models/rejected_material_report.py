from odoo import fields, models, tools,_


class RejectedMaterialReport(models.Model):
    _name = "rejected.material.report"
    _description = "Rejected Material Report Report"
    _auto = False
    _rec_name = 'move_id'

    move_id = fields.Many2one('stock.move', string='Move')
    consumption_id = fields.Many2one('mrp.consumption', 'Production Record', readonly=True)
    workorder_id = fields.Many2one('mrp.workorder', 'Production Work Order', readonly=True)
    production_id = fields.Many2one('mrp.production', 'Production Order', readonly=True)
    plan_id = fields.Many2one('mrp.plan', 'Production Plan', readonly=True)

    to_consume = fields.Float('Quantity', readonly=True)
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

    location_id = fields.Many2one(comodel_name='stock.location', string='Location',  readonly=True)
    rejected_date = fields.Datetime(string='Rejected Date', readonly=True)

    reason = fields.Text(string='Reason', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
        SELECT sq.* FROM (
        SELECT	
                    sm.id AS id,
                    sm.id AS move_id,
                    sm.mrp_consumption_id AS consumption_id,
                    sm.mrp_workorder_component_id AS workorder_id,
                    sm.raw_material_production_id AS production_id,
                    sm.location_id as location_id,
                    me.write_date as rejected_date,
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
                    rj.name as reason,
                    ABS(svl.value) AS value
                FROM
                    mrp_consumption mpr 
                LEFT JOIN
                    stock_move sm ON (sm.mrp_consumption_id = mpr.id)
                LEFT JOIN
                    mrp_workorder wo ON (sm.mrp_workorder_component_id = wo.id)
                LEFT JOIN
                    mrp_production mo ON (sm.raw_material_production_id = mo.id)
                LEFT JOIN
                    mrp_plan mp ON (sm.mrp_plan_id = mp.id)
                LEFT JOIN
                    stock_valuation_layer svl ON (sm.id = svl.stock_move_id AND svl.type = 'component')
                LEFT JOIN
                    mrp_approval_matrix_reject ma ON (sm.mrp_consumption_id = ma.model_id AND ma.model_name = 'mrp.consumption')
                LEFT JOIN
                    mrp_approval_matrix_entry_reason rj ON (rj.id = ma.reason_id)
                LEFT JOIN 
                    mrp_approval_matrix_entry me ON (me.mo_id = sm.raw_material_production_id)
                WHERE
                    mp.state = 'reject' OR mo.state = 'reject' OR mpr.state = 'reject'
            ) sq
	    WHERE sq.rejected_date IS NOT null
        """
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, query))