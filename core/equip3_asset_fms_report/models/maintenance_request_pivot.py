from odoo import models, fields, api, _
from odoo import tools


class MaintenanceRequestPivot(models.Model):
    _name = 'maintenance.request.pivot'
    _description = 'Maintenance Request Pivot'
    _auto = False

    name = fields.Char(string='Maintenance Request')
    work_order = fields.Char(string='Maintenance Work Order')
    repair_order = fields.Char(string='Maintenance Repair Order')
    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Equipment')
    state = fields.Char(string='State')
    date = fields.Date(string='Date')


    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
            SELECT 
                COALESCE(min(mr.id)) AS id,
                mr.name AS name,
                mwo.name AS work_order,
                mro.name AS repair_order,
                mr.equipment_id AS equipment_id,
                CASE
                    WHEN mr.extra_state = 'new' THEN 'New Request'
                    WHEN mr.extra_state = 'waiting' THEN 'Waiting for Approval'
                    WHEN mr.extra_state = 'approved' THEN 'Approved'
                    WHEN mr.extra_state = 'progress' THEN 'In Progress'
                    WHEN mr.extra_state = 'done' THEN 'Done'
                    WHEN mr.extra_state = 'reject' THEN 'Rejected'
                    WHEN mr.extra_state = 'cancel' THEN 'Cancelled'
                END AS state,
                mr.request_date as date
            FROM maintenance_request AS mr
            LEFT JOIN maintenance_work_order AS mwo ON mr.id = mwo.maintainence_request_id
            LEFT JOIN maintenance_repair_order AS mro ON mwo.id = mro.work_order_id
            GROUP BY 
                mr.name,
                mwo.name,
                mro.name,
                mr.equipment_id,
                mr.extra_state,
                mr.request_date
                    )""" % (self._table)
        )