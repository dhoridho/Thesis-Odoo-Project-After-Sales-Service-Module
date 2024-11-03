from odoo import api, fields, models, _
from odoo import tools


class ForecastOdoMeterMaintenanceLine(models.Model):
    _name = 'forecast.odo.meter.maintenance.line'
    _description = "Forecast Odo Meter Maintenance"
    _auto = False
    
    # id_maintenance = fields.Char('Maintenance Id')
    forecast_odo_id = fields.Many2one('forecast.odo.meter.maintenance', string="Forecast Id REF")
    equipment_id = fields.Many2one('maintenance.equipment', string="Maintenance Equipment")
    name = fields.Char('Odometer Maintenance Plan')
    state = fields.Char(string='Status')
    last_date = fields.Date('Last Date')
    current_odo = fields.Float('Current Odometer ( Km )')
    next_treshold = fields.Float('Odometer  Threshold ( Km )')
    cummulative_odo = fields.Float('Cumulative Odometer ( Km )')
    unit = fields.Char('Odometer Type')
    monthly = fields.Char('End Date')
    difference = fields.Float('Diff')


    def _query(self, with_clause='', fields={} ,where='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            DISTINCT ON (subquery.maintenance_plan_id)
                subquery.maintenance_plan_id as id,
                me.id as equipment_id,
                mp.name as name,
                mp.state as state,
                subquer4.date as last_date,
                subquer6.total_value as current_odo,
                subquery.threshold as next_treshold,
                subquer7.value as cummulative_odo,
                subquery.unit as unit,
                mp.end_date as monthly,
                subquery.threshold - subquer6.total_value as difference,
                me.id as forecast_odo_id
        """

        for field in fields.values():
            select_ += field

        from_ = """
                (
                select maintenance_plan_id,threshold,unit from maintenance_threshold where
                threshold is not null and threshold >= 1 and unit = 'km'
                ) as subquery
                LEFT JOIN
                    plan_task_check_list as ptcl on ptcl.maintenance_plan_id = subquery.maintenance_plan_id
                LEFT JOIN 
                    maintenance_equipment as me ON ptcl.equipment_id = me.id
                LEFT JOIN
                    maintenance_plan as mp ON subquery.maintenance_plan_id = mp.id
                LEFT JOIN
                    (SELECT DISTINCT ON (maintenance_vehicle)
                        id, maintenance_vehicle, create_date,date
                    FROM maintenance_vehicle
                    ORDER BY maintenance_vehicle, id DESC
                    ) as subquer4 ON me.id = subquer4.maintenance_vehicle
                LEFT JOIN
                    (
                    SELECT DISTINCT ON (maintenance_vehicle)
                        maintenance_vehicle, total_value
                    FROM maintenance_vehicle where value is not null
                    ORDER BY maintenance_vehicle asc, id desc
                    ) as subquer6 ON subquer6.maintenance_vehicle = me.id
                LEFT JOIN
                    (
                    SELECT DISTINCT ON (maintenance_vehicle)
                        maintenance_vehicle, sum(value) as value
                    FROM maintenance_vehicle where value >= 1
                    GROUP BY maintenance_vehicle
                    ) as subquer7 ON subquer7.maintenance_vehicle = me.id
        """

        where_ = """
                subquery.threshold > subquer6.total_value

        ORDER BY subquery.maintenance_plan_id, subquery.threshold
        """


        return '%s (SELECT %s FROM %s WHERE %s)' % (with_, select_, from_, where_,)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
