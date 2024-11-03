from odoo import api, fields, models, _
from odoo import tools


class ForecastHourMeterMaintenanceLine(models.Model):
    _name = 'forecast.hour.meter.maintenance.line'
    _description = "Forecast Hour Meter Maintenance"
    _auto = False
    
    # id_maintenance = fields.Char('Maintenance Id')
    forecast_id = fields.Many2one('forecast.hour.meter.maintenance', string="Forecast Id REF")
    equipment_id = fields.Many2one('maintenance.equipment', string="Maintenance Equipment")
    name = fields.Char('Hour Maintenance Plan')
    state = fields.Char(string='Status')
    last_date = fields.Date('Last Date')
    current_hour = fields.Float('Current Meter ( Hours )')
    next_treshold = fields.Float('Hour Meter  Threshold ( Hours )')
    cummulative_hour = fields.Float('Cumulative Hour Meter ( Hours )')
    unit = fields.Char('Hour Meter Type')
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
                subquer6.total_value as current_hour,
                subquery.threshold as next_treshold,
                subquer7.value as cummulative_hour,
                subquery.unit as unit,
                mp.end_date as monthly,
                subquery.threshold - subquer6.total_value as difference,
                me.id as forecast_id
        """

        for field in fields.values():
            select_ += field

        from_ = """
                (
                select maintenance_plan_id,threshold,unit from maintenance_threshold where
                threshold is not null and threshold >= 1 and unit = 'hours'
                ) as subquery
                LEFT JOIN
                    plan_task_check_list as ptcl on ptcl.maintenance_plan_id = subquery.maintenance_plan_id
                LEFT JOIN 
                    maintenance_equipment as me ON ptcl.equipment_id = me.id
                LEFT JOIN
                    maintenance_plan as mp ON subquery.maintenance_plan_id = mp.id
                LEFT JOIN
                    (SELECT DISTINCT ON (maintenance_asset)
                        id, maintenance_asset, create_date,date
                    FROM maintenance_hour_meter
                    ORDER BY maintenance_asset, id DESC
                    ) as subquer4 ON me.id = subquer4.maintenance_asset
                LEFT JOIN
                    (
                    SELECT DISTINCT ON (maintenance_asset)
                        maintenance_asset, total_value
                    FROM maintenance_hour_meter where value is not null
                    ORDER BY maintenance_asset asc, id desc
                    ) as subquer6 ON subquer6.maintenance_asset = me.id
                LEFT JOIN
                    (
                    SELECT DISTINCT ON (maintenance_asset)
                        maintenance_asset, sum(value) as value
                    FROM maintenance_hour_meter where value >= 1
                    GROUP BY maintenance_asset
                    ) as subquer7 ON subquer7.maintenance_asset = me.id
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
