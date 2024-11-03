from odoo import tools
from odoo import api, fields, models, _


class NurseryReport(models.Model):
    _inherit = 'agriculture.list.report'
    _name = 'agriculture.nursery.report'
    _description = 'Nursery Report'
    _auto = False
    _rec_name = 'activity_record_id'

    print_all_records = True

    @api.model
    def _get_state_selection(self):
        activity_record = self.env['agriculture.daily.activity.record']
        return [(k, v) for k, v in activity_record.fields_get(allfields=['state'])['state']['selection']]

    estate_id = fields.Many2one('crop.estate', string='Estate')
    division_id = fields.Many2one('agriculture.division', string='Division')
    block_id = fields.Many2one('crop.block', string='Block')
    date = fields.Date(string='Date')
    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Reference')
    product_id = fields.Many2one('product.product', string='Crop')
    qty = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', string='Product UoM')
    planted_year = fields.Datetime(string='Planted Year')
    planted_area = fields.Float(string='Planted Area')
    area_uom_id = fields.Many2one('uom.uom', string='Area UoM')
    state = fields.Selection(selection=_get_state_selection, string='Status')

    @api.model
    def _query(self):
        return """
        SELECT
            nursery.id AS id,
            estate.id AS estate_id,
            div.id AS division_id,
            block.id AS block_id,
            record.id AS activity_record_id,
            nursery.date AS date,
            nursery.product_id AS product_id,
            nursery.count AS qty,
            nursery.uom_id AS uom_id,
            nursery.create_date AS planted_year,
            block.size AS planted_area,
            block.uom_id AS area_uom_id,
            record.state AS state
        FROM agriculture_daily_activity_nursery nursery
            LEFT JOIN agriculture_daily_activity_record record ON (record.id = nursery.activity_record_id)
            LEFT JOIN crop_block block ON (nursery.block_id = block.id) 
            LEFT JOIN crop_estate estate ON (block.estate_id = estate.id)
            LEFT JOIN agriculture_division div ON (block.division_id = div.id)
        WHERE
            record.state = 'confirm'
        ORDER BY
            nursery.id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

    @api.model
    def _get_report_name(self):
        return _('Nursery Report')

    @api.model
    def _get_header_fields(self):
        return ['date', 'activity_record_id', 'product_id', 'qty', 'uom_id', 'planted_year', 'planted_area', 'area_uom_id']

    @api.model
    def _get_aggregate_fields(self):
        return ['qty', 'planted_area']

    @api.model
    def _get_grouped_fields(self):
        return ['estate_id', 'division_id', 'block_id']

    @api.model
    def get_report_values(self, state):
        lines = super(NurseryReport, self).get_report_values(state)
        for line in lines:
            line['planted_year'] = line['planted_year'].split('-')[0]
        return lines


class ReportNurseryReport(models.AbstractModel):
    _name = 'report.equip3_agri_operations.agriculture_nursery_report'
    _description = 'Report Nursery Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = dict()

        if 'report_data' not in data: 
            report_data = self.env['agriculture.nursery.report'].get_report_values()
        else:
            report_data = data['report_data']

        data['lines'] = report_data
        data['company'] = self.env.company
        return data
