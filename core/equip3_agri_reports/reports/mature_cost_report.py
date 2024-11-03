from odoo import models, fields, api, _
from odoo import tools


class MatureCostReport(models.Model):
    _inherit = 'agriculture.list.report'
    _name = 'agriculture.mature.cost.report'
    _description = 'Mature Cost Report'
    _auto = False

    print_all_records = True

    @api.model
    def _get_year_selection(self):
        record_ids = self.env['agriculture.daily.activity.record'].search([('crop_age', '=', 'TM')])
        record_dates = record_ids.mapped('date_scheduled')
        if not record_dates:
            return [('none', 'None')]
        min_date = min(record_dates)
        max_date = max(record_dates)
        selection = []
        for year in range(min_date.year, max_date.year + 1):
            selection += [(str(year), str(year))]
        return selection

    year = fields.Selection(selection=_get_year_selection, string='Year')
    month = fields.Selection(
        selection=[
            ('january', 'January'),
            ('february', 'February'),
            ('march', 'March'),
            ('april', 'April'),
            ('may', 'May'),
            ('june', 'June'),
            ('july', 'July'),
            ('august', 'August'),
            ('september', 'September'),
            ('october', 'October'),
            ('november', 'November'),
            ('december', 'December')
        ], string='Month'
    )
    norm_date = fields.Date(string='Date')
    group_id = fields.Many2one('crop.activity.group', string='Activity Group')
    activity_id = fields.Many2one('crop.activity', string='Activity')
    planned_cost = fields.Float(string='Planned')
    actual_cost = fields.Float(string='Actual')

    @api.model
    def _query(self):
        return """
        SELECT
            ROW_NUMBER() OVER (ORDER BY record.normalized_date) AS id,
            TRIM(TO_CHAR(record.normalized_date, 'YYYY')) AS year,
            TRIM(TO_CHAR(record.normalized_date, 'month')) AS month,
            record.normalized_date AS norm_date,
            act_group.id AS group_id,
            activity.id AS activity_id,
            record.planned_cost,
            ABS(SUM(svl.value)) AS actual_cost
        FROM
            (SELECT
                rec.normalized_date,
                rec.id,
                rec.activity_id,
                CASE
                    WHEN rec.month_seq = 1 THEN SUM(budget.val_jan)
                    WHEN rec.month_seq = 2 THEN SUM(budget.val_feb)
                    WHEN rec.month_seq = 3 THEN SUM(budget.val_mar)
                    WHEN rec.month_seq = 4 THEN SUM(budget.val_apr)
                    WHEN rec.month_seq = 5 THEN SUM(budget.val_may)
                    WHEN rec.month_seq = 6 THEN SUM(budget.val_jun)
                    WHEN rec.month_seq = 7 THEN SUM(budget.val_jul)
                    WHEN rec.month_seq = 8 THEN SUM(budget.val_aug)
                    WHEN rec.month_seq = 9 THEN SUM(budget.val_sep)
                    WHEN rec.month_seq = 10 THEN SUM(budget.val_oct)
                    WHEN rec.month_seq = 11 THEN SUM(budget.val_nov)
                    WHEN rec.month_seq = 12 THEN SUM(budget.val_dec)
                    ELSE 0.0
                END AS planned_cost
            FROM
                (SELECT
                    act_rec.id,
                    act_rec.activity_id,
                    EXTRACT(MONTH FROM act_rec.date_scheduled) AS month_seq,
                    CAST(DATE_TRUNC('month', act_rec.date_scheduled) AS date) AS normalized_date
                FROM 
                    agriculture_daily_activity_record act_rec
                WHERE
                    act_rec.crop_age = 'TM'
                ) rec
                LEFT JOIN agriculture_budget_planning plan ON (plan.year = TRIM(TO_CHAR(rec.normalized_date, 'YYYY')))
                LEFT JOIN agriculture_budget_planning_month budget ON (budget.activity_id = rec.activity_id AND budget.plan_id = plan.id)
            GROUP BY
                rec.month_seq, rec.normalized_date, rec.id, rec.activity_id
            ) record
            LEFT JOIN crop_activity activity ON (activity.id = record.activity_id)
            LEFT JOIN crop_activity_group act_group ON (act_group.id = activity.group_id)
            LEFT JOIN stock_valuation_layer svl ON (svl.activity_record_id = record.id)
        GROUP BY
            record.normalized_date, act_group.id, activity.id, record.planned_cost
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

    @api.model
    def _get_report_name(self):
        return _('Mature Cost Report')

    @api.model
    def _get_header_fields(self):
        return ['activity_id', 'planned_cost', 'actual_cost']

    @api.model
    def _get_aggregate_fields(self):
        return ['planned_cost', 'actual_cost']

    @api.model
    def _get_grouped_fields(self):
        return ['norm_date:month', 'group_id']


class ReportMatureCostReport(models.AbstractModel):
    _name = 'report.equip3_agri_reports.agriculture_mature_cost_report'
    _description = 'Report Mature Cost Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = dict()

        if 'report_data' not in data: 
            report_data = self.env['agriculture.mature.cost.report'].get_report_values()
        else:
            report_data = data['report_data']

        data['lines'] = report_data
        data['company'] = self.env.company
        return data
