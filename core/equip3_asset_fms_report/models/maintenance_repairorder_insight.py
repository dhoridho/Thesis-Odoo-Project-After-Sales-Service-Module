from odoo import models, fields, api, _

class MaintenanceRepairorderInsight(models.Model):
    _name = 'maintenance.repairorder.insight'
    _description = 'Maintenance Repairorder Insight'
    _auto = False

    name = fields.Char(string='Maintenance Repair Order')
    time_in_progress = fields.Float(string='Time In Progress (Minutes)')
    time_post = fields.Float(string='Time Pause (Minutes)')
    cost = fields.Float(string='Cost')
    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Equipment')
    part_equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Part')
    product_id = fields.Many2one(comodel_name='product.product', string='Material')
    total_time = fields.Float(string='Total Time (Minutes)')
    mro_count = fields.Integer(string='Count')
    types = fields.Char(string='Type')

    
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
            maintenance_ro_id,
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
            CASE
                WHEN types = 'add' THEN price_subtotal + price_tax
                ELSE null
            END AS cost,
            CASE
                WHEN row_num = 1 THEN 1
                ELSE 0
            END AS mro_count,
            types
        FROM (
            SELECT
                mro.id,
                mro.name,
                mro.time_in_progress,
                mro.time_post,
                mml.parent_equipment_id,
                ptcl.maintenance_ro_id,
                mml.part_equipment_id,
                mml.product_id,
                mml.price_subtotal,
                mml.price_tax,
                mml.types,
                ROW_NUMBER() OVER (PARTITION BY mro.id, mml.parent_equipment_id ORDER BY mro.id) AS row_num
            FROM
                maintenance_repair_order AS mro
                LEFT JOIN maintenance_materials_list AS mml ON mro.id = mml.maintenance_ro_id
                LEFT JOIN plan_task_check_list ptcl ON mro.id = ptcl.maintenance_ro_id
        ) AS subquery
        GROUP BY
            subquery.id,
            subquery.name,
            subquery.parent_equipment_id,
            subquery.maintenance_ro_id,
            subquery.part_equipment_id,
            subquery.product_id,
            subquery.time_in_progress,
            subquery.time_post,
            subquery.types,
            subquery.price_subtotal,
            subquery.price_tax,
            subquery.row_num
        ORDER BY
            subquery.name,
            subquery.parent_equipment_id
        """
        return select_str