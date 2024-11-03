from odoo import api, fields, models, tools

class MachineryPerformanceReliability(models.Model):
    _name = 'machinery.performance.reliability'
    _description = 'Machinery Performance Reliability'
    _auto = False

    asset = fields.Char(string="Asset")
    mtbf = fields.Float(string='Mean Time Between Failures (Hours) ')
    mttr = fields.Float(string='Mean Time To Repair (Hours) ')
    mttf = fields.Float(string='Mean Time To Failure (Hours) ')
    pa = fields.Float(string='Physical Availability (%) ')
    ua = fields.Float(string='Utilization Availability (%) ')
    ma = fields.Float(string='Maintainability Availability (%)')
    eu = fields.Float(string='Efficiency Utilization (%)')
    create_date = fields.Datetime(string='Date')

    @property
    def _table_query(self):
        query =  '%s' % (self.query())
        return query

    
    def query(self):
        select_str = """
        SELECT
            coalesce(min(me.id), 0) as id,
            concat(me.name, ' [', me.serial_no, ']') as asset,
            case
                when count(xx.breakdown) FILTER (WHERE xx.breakdown >= 1) > 0 then (sum(operative + standby) - sum(breakdown + maintenance + idle)) / count(xx.breakdown) FILTER (WHERE xx.breakdown >= 1)
                else 0
            end as mtbf,
            case
                when count(xx.maintenance) FILTER (WHERE xx.maintenance >= 1) > 0 then sum(maintenance) / count(xx.maintenance) FILTER (WHERE xx.maintenance >= 1)
                else 0
            end as mttr,
            case
                when count(DISTINCT equipment_id) > 0 then sum(operative) / (select count(distinct equipment_id) from asset_usage_line where activity_type = 'operative')
                else 0
            end as mttf,
            case
                when (sum(operative) + sum(standby) + sum(breakdown)) > 0 then ((sum(operative) + sum(standby)) / (sum(operative) + sum(standby) + sum(breakdown))) * 100
                else 0
            end as pa,
            case
                when (sum(operative) + sum(standby)) > 0 then (sum(operative) / (sum(operative) + sum(standby))) * 100
                else 0
            end as ua,
            case
                when (sum(operative) + sum(breakdown)) > 0 then (sum(operative) / (sum(operative) + sum(breakdown))) * 100
                else 0
            end as ma,
            case
                when (sum(operative) + sum(standby) + sum(breakdown)) > 0 then (sum(operative) / (sum(operative) + sum(standby) + sum(breakdown))) * 100
                else 0
            end as eu,
			xx.create_date
        FROM
            (
                SELECT  
					aul.create_date as create_date,
                    aul.equipment_id,
                    EXTRACT(EPOCH FROM (aul.end_time - aul.start_time) / 3600) AS operative,
                    0 AS standby,
                    0 AS idle,
                    0 AS maintenance,
                    0 AS breakdown,
                    0 AS breakdown_count
                FROM
                    asset_usage_line AS aul
                WHERE
                    aul.activity_type = 'operative'
                GROUP BY
					aul.create_date,
                    aul.equipment_id,
                    aul.end_time,
                    aul.start_time

                UNION ALL

                SELECT
					aul.create_date as create_date,
                    aul.equipment_id,
                    0 AS operative,
                    EXTRACT(EPOCH FROM (aul.end_time - aul.start_time) / 3600) AS standby,
                    0 AS idle,
                    0 AS maintenance,
                    0 AS breakdown,
                    0 AS breakdown_count
                FROM
                    asset_usage_line AS aul
                WHERE
                    aul.activity_type = 'standby'
                GROUP BY
					aul.create_date,
                    aul.equipment_id,
                    aul.end_time,
                    aul.start_time

                UNION ALL

                SELECT
					aul.create_date as create_date,
                    aul.equipment_id,
                    0 AS operative,
                    0 AS standby,
                    0 AS idle,
                    0 AS maintenance,
                    0 AS breakdown,
                    0 AS breakdown_count
                FROM
                    asset_usage_line AS aul
                WHERE
                    aul.activity_type = 'maintenance'
                GROUP BY
					aul.create_date,
                    aul.equipment_id

                UNION ALL

                SELECT
					aul.create_date as create_date,
                    aul.equipment_id,
                    0 AS operative,
                    0 AS standby,
                    0 AS idle,
                    EXTRACT(EPOCH FROM (aul.end_time - aul.start_time) / 3600) AS maintenance,
                    0 AS breakdown,
                    0 AS breakdown_count
                FROM
                    asset_usage_line AS aul
                WHERE
                    aul.activity_type = 'maintenance'
                GROUP BY
					aul.create_date,
                    aul.equipment_id,
                    aul.end_time,
                    aul.start_time

                UNION ALL

                SELECT
					aul.create_date as create_date,
                    aul.equipment_id,
                    0 AS operative,
                    0 AS standby,
                    EXTRACT(EPOCH FROM (aul.end_time - aul.start_time) / 3600) AS idle,
                    0 AS maintenance,
                    0 AS breakdown,
                    0 AS breakdown_count
                FROM
                    asset_usage_line AS aul
                WHERE
                    aul.activity_type = 'idle'
                GROUP BY
					aul.create_date,
                    aul.equipment_id,
                    aul.end_time,
                    aul.start_time

                UNION ALL

                SELECT
					aul.create_date as create_date,
                    aul.equipment_id,
                    0 AS operative,
                    0 AS standby,
                    0 AS idle,
                    0 AS maintenance,
                    0 AS breakdown,
                    0 AS breakdown_count
                FROM
                    asset_usage_line AS aul
                WHERE
                    aul.activity_type = 'breakdown'
                GROUP BY
					aul.create_date,
                    aul.equipment_id

                UNION ALL

                SELECT
					aul.create_date as create_date,
                    aul.equipment_id,
                    0 AS operative,
                    0 AS standby,
                    0 AS idle,
                    0 AS maintenance,
                    EXTRACT(EPOCH FROM (aul.end_time - aul.start_time) / 3600) AS breakdown,
                    0 AS breakdown_count
                FROM
                    asset_usage_line AS aul
                WHERE
                    aul.activity_type = 'breakdown'
                GROUP BY
					aul.create_date,
                    aul.equipment_id,
                    aul.end_time,
                    aul.start_time
            ) AS xx
            LEFT JOIN maintenance_equipment AS me ON me.id = xx.equipment_id
        GROUP BY
            me.id,
			xx.create_date

        """ 
        return select_str