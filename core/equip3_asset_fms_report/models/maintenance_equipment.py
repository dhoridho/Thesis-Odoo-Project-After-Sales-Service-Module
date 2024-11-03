from odoo import api, fields, models, _
from odoo import tools



class ForecastPreventiveMaintenance(models.Model):
    _name = 'forecast.preventive.maintenance'
    _description = "Forecast Preventive Maintenance"
    _auto = False

    equip_id = fields.Many2one('maintenance.equipment', string="Maintenance Equipment")
    name = fields.Char('Preventive Maintenance Plan')
    team_id = fields.Many2one('maintenance.teams', string="Team")
    start_date = fields.Date('Start Date')
    next_maintenance_date = fields.Date('Next Maintenance')
    last_date = fields.Date('Last Date')
    frequency = fields.Integer('Frequency ( Days )')


    def _query(self, with_clause='', fields={} ,where='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            distinct on (mp.name)
                mp.id,
                me.id as equip_id,
                mp.name as name,
                mp.maintenance_team_id as team_id,
                mp.start_date as start_date,
                subquery.start_date as next_maintenance_date,
                mp.end_date as last_date,
                mp.frequency_interval_number as frequency
        """

        for field in fields.values():
            select_ += field

        from_ = """
                maintenance_plan as mp
                left join 
                    plan_task_check_list as ptcl on ptcl.maintenance_plan_id = mp.id
                LEFT JOIN 
                    maintenance_equipment as me ON ptcl.equipment_id = me.id
                LEFT JOIN
                (
                select start_date,parent_id from maintenance_plan as mp where
                mp.is_preventive_m_plan = True
                and parent_id is not null
                and start_date > current_date
                and state = 'active'
                ) as subquery on subquery.parent_id = mp.id
        """

        where_ = """
                 
                mp.is_preventive_m_plan = True
                    and mp.parent_id is null
                    and mp.state = 'active'
                    and mp.end_date > current_date
                order by mp.name, subquery.start_date asc
        """


        return '%s (SELECT %s FROM %s WHERE %s)' % (with_, select_, from_, where_,)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    hour_meter_line_ids = fields.One2many('forecast.hour.meter.maintenance.line', 'equipment_id', string="Forecast Hourmeter")
    odo_meter_line_ids = fields.One2many('forecast.odo.meter.maintenance.line', 'equipment_id', string="Forecast Odometer")
    forecast_preventive_ids = fields.One2many('forecast.preventive.maintenance', 'equip_id', string="Forecast Preventive")

