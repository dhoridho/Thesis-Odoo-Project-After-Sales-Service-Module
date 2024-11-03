from odoo import tools
from odoo import models, fields, api, _


class HarvestingReport(models.Model):
    _inherit = 'agriculture.list.report'
    _name = 'agriculture.harvest.report'
    _description = 'Harvesting Report'
    _auto = False

    print_all_records = True

    @api.model
    def _get_state_selection(self):
        stock_move = self.env['stock.move']
        return [(k, v) for k, v in stock_move.fields_get(allfields=['state'])['state']['selection']]

    estate_id = fields.Many2one('crop.estate', string='Estate')
    division_id = fields.Many2one('agriculture.division', string='Division')
    block_id = fields.Many2one('crop.block', string='Block')
    date = fields.Date(string='Date')
    activity_record_id = fields.Many2one('agriculture.daily.activity.record', string='Reference')
    product_id = fields.Many2one('product.product', string='Harvest')
    qty = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    bunch = fields.Integer(string='Bunch')
    state = fields.Selection(selection=_get_state_selection, string='Status')

    @api.model
    def _query(self):
        return """
        SELECT
            mv.id AS id,
            estate.id AS estate_id,
            div.id AS division_id,
            record.block_id AS block_id,
            record.id AS activity_record_id,
            mv.date AS date,
            mv.product_id AS product_id,
            mv.product_uom_qty AS qty,
            mv.product_uom AS uom_id,
            mv.bunch AS bunch,
            mv.state AS state
        FROM
            stock_move mv
            LEFT JOIN agriculture_daily_activity_record record ON (record.id = mv.activity_record_harvest_id)
            LEFT JOIN crop_block block ON (record.block_id = block.id) 
            LEFT JOIN crop_estate estate ON (block.estate_id = estate.id)
            LEFT JOIN agriculture_division div ON (block.division_id = div.id)
        WHERE 
            record.harvest = True
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

    @api.model
    def _get_report_name(self):
        return _('Harvesting Report')

    @api.model
    def _get_header_fields(self):
        return ['date', 'activity_record_id', 'product_id', 'qty', 'uom_id', 'bunch']

    @api.model
    def _get_aggregate_fields(self):
        return ['qty', 'bunch']

    @api.model
    def _get_grouped_fields(self):
        return ['estate_id', 'division_id', 'block_id']


class ReportHarvestReport(models.AbstractModel):
    _name = 'report.equip3_agri_reports.agriculture_harvest_report'
    _description = 'Report Harvest Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = dict()

        if 'report_data' not in data: 
            report_data = self.env['agriculture.harvest.report'].get_report_values()
        else:
            report_data = data['report_data']

        data['lines'] = report_data
        data['company'] = self.env.company
        return data
