from odoo import models, fields, api, _

class MaintenanceWorkorderInsight(models.Model):
    _name = 'maintenance.workorder.insight'
    _description = 'Maintenance Workorder Insight'
    _auto = False

    name = fields.Char(string='Maintenance Work Order')
    time_in_progress = fields.Float(string='Time In Progress (Minutes)')
    time_post = fields.Float(string='Time Pause (Minutes)')
    cost = fields.Float(string='Cost')
    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Equipment')
    part_equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Part')
    product_id = fields.Many2one(comodel_name='product.product', string='Material')
    total_time = fields.Float(string='Total Time (Minutes)')
    mwo_count = fields.Integer(string='Count')

    
    @property
    def _table_query(self):
        query =  '%s' % (self.query())
        return query

    def query(self):
        select_str = """
        SELECT
            COALESCE(min(id) FILTER (WHERE row_num = 1), 0) AS id,
            name,
            parent_equipment_id AS equipment_id,
            maintenance_wo_id,
            part_equipment_id,
            product_id,
            CASE
                WHEN row_num = 1 THEN time_in_progress
                ELSE 0
            END AS time_in_progress,
            CASE
                WHEN row_num = 1 THEN time_post
                ELSE 0
            END AS time_post,
            CASE
				WHEN row_num = 1 THEN time_in_progress + time_post
				ELSE 0
		    END AS total_time,
            cost,
			CASE
                WHEN row_num = 1 THEN 1
                ELSE null
            END AS mwo_count
        FROM (
            SELECT
                mwo.id,
                mwo.name,
                mwo.time_in_progress,
                mwo.time_post,
                mml.parent_equipment_id,
                ptcl.maintenance_wo_id,
                mml.price_subtotal + mml.price_tax AS cost,
                mml.part_equipment_id,
                mml.product_id,
				ROW_NUMBER() OVER (PARTITION BY mwo.id, mml.parent_equipment_id ORDER BY mwo.id) AS row_num
            FROM
                maintenance_work_order AS mwo
                LEFT JOIN maintenance_materials_list AS mml ON mwo.id = mml.maintenance_wo_id
                LEFT JOIN plan_task_check_list ptcl ON mwo.id = ptcl.maintenance_wo_id
        ) AS subquery
        GROUP BY
            subquery.name,
            subquery.time_in_progress,
            subquery.time_post,
            subquery.parent_equipment_id,
            subquery.maintenance_wo_id,
            subquery.cost,
            subquery.part_equipment_id,
            subquery.product_id,
            subquery.row_num
        ORDER BY 
			subquery.name,
			subquery.parent_equipment_id

        """
        return select_str
