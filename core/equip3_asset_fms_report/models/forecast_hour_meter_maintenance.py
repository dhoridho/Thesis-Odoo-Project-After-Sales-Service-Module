from odoo import api, fields, models, _
from odoo import tools


class ForecastHourMeterMaintenance(models.Model):
    _name = 'forecast.hour.meter.maintenance'
    _description = "Forecast Hour Meter Maintenance"
    _auto = False
    
    # id_maintenance = fields.Char('Maintenance Id')
    name = fields.Char('Equipment Name')
    serial_no = fields.Char('Serial Number')
    equipment_id = fields.Many2one('maintenance.equipment')
    brand = fields.Char('Brand')
    state = fields.Char(string='Status')
    last_date = fields.Date('Last Date')
    current_hour = fields.Float('Current Hour Meter ( Hours )')
    next_treshold = fields.Float('Hour Meter Threshold ( Hours )')
    cummulative_hour = fields.Float('Cumulative Hour Meter ( Hours )')
    unit = fields.Char('Hour Meter Type')
    monthly = fields.Char('End Date')
    difference = fields.Float('Diff')
    forecast_line_ids = fields.One2many('forecast.hour.meter.maintenance.line', 'forecast_id', string="Forecast lines")

    def print_excel(self):
        fhmm = self.env['forecast.hour.meter.maintenance'].search([],limit=1)
        return {
            'type': 'ir.actions.act_url',
            'url': '/sale/forecast_excel_report/?id=%s' % (fhmm.id),
            'target': 'new',
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            %s
            %s
            )""" % (self._table, self._select(), self._from(), self._where()))

    def _select(self):
        select_str = """
            SELECT
                DISTINCT ON (me.id)
                me.id as id,
                me.name as name,
                me.serial_no as serial_no,
                me.id as equipment_id,
                me.model as brand,
                me.state as state,
                subquer4.date as last_date,
                subquer5.value as current_hour,
                subquery.threshold as next_treshold,
                subquer6.value as cummulative_hour,
                subquery.unit as unit,
                mp.end_date as monthly,
                subquery.threshold - subquer5.value as difference,
                me.id as forecast_line_ids
        """ 
        return select_str

    def _from(self):
        from_str = """
            FROM
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
					select maintenance_asset,sum(value) as value
						from maintenance_hour_meter where value is not null 
					group by maintenance_asset
					) as subquer5 ON subquer5.maintenance_asset = me.id
                LEFT JOIN
                    (
                    SELECT DISTINCT ON (maintenance_asset)
                        maintenance_asset, sum(value) as value
                    FROM maintenance_hour_meter where value >= 1
					GROUP BY maintenance_asset
                    ) as subquer6 ON subquer6.maintenance_asset = me.id
        """
        return from_str
    
    def _where(self):
        where_str = """
        WHERE 
            subquery.threshold > subquer5.value and mp.state = 'active'

        ORDER BY me.id, subquery.threshold
        """
        return where_str
