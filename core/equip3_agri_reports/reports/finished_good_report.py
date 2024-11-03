from odoo import tools
from odoo import api, fields, models


class FinishedGoodReport(models.Model):
    _name = "agriculture.finished.good.report"
    _description = "Finished Goods Report"
    _auto = False
    _rec_name = 'create_date'
    _order = 'create_date desc'

    @api.model
    def _get_done_states(self):
        return ['sale', 'done', 'paid']

    name = fields.Char('Reference', readonly=True)
    availability = fields.Float('Forecasted', readonly=True)
    quantity_done = fields.Float('Consumed', readonly=True)
    difference = fields.Float('Difference', readonly=True)
    value = fields.Float('Value', readonly=True)
    daily_activity_id = fields.Many2one('agriculture.daily.activity', 'Plantation Plan', readonly=True)
    activity_line_id = fields.Many2one('agriculture.daily.activity.line', 'Plantation Lines', readonly=True)
    activity_record_id = fields.Many2one('agriculture.daily.activity.record', 'Plantation Record', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    branch_id = fields.Many2one('res.branch', 'Branch', readonly=True)
    create_date = fields.Datetime('Created On', readonly=True)
    create_uid = fields.Many2one('res.users', 'Created By', readonly=True)
    product_id = fields.Many2one('product.product', 'Finished Good', readonly=True)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed')
        ], string='Status', readonly=True)

    def _select_sale(self, fields=None):
        if not fields:
            fields = {}
        select_ = """
            coalesce(min(l.id), -mc.id) as id,
            l.product_id as product_id,
            l.product_uom as product_uom,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.stored_availability) ELSE 0 END as availability,
            CASE WHEN l.product_id IS NOT NULL AND l.state = 'done' THEN sum(l.quantity_done) ELSE 0 END as quantity_done,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.stored_availability) ELSE 0 END - CASE WHEN l.product_id IS NOT NULL AND l.state = 'done' THEN sum(l.quantity_done) ELSE 0 END as difference,
            count(*) as nbr,
            mc.name as name,
            mc.id as activity_record_id,
            mc.daily_activity_id as daily_activity_id,
            mc.activity_line_id as activity_line_id,
            mc.company_id as company_id,
            mc.branch_id as branch_id,
            mc.create_date as create_date,
            mc.state as state,
            mc.create_uid as create_uid
        """

        for field in fields.values():
            select_ += field
        return select_

    def _from_sale(self, from_clause=''):
        from_ = """
                stock_move l
                right outer join agriculture_daily_activity_record mc on (mc.id=l.activity_record_harvest_id)
                left join product_product p on (l.product_id=p.id)
                left join uom_uom u on (u.id=l.product_uom)
                %s
        """ % from_clause
        return from_

    def _group_by_sale(self, groupby=''):
        groupby_ = """
            mc.daily_activity_id,
            mc.activity_line_id,
            mc.company_id,
            mc.branch_id,
            mc.create_date,
            mc.create_uid,
            l.product_id,
            l.product_uom,
            mc.name,
            mc.id,
            l.state,
            mc.state %s
        """ % (groupby)
        return groupby_

    def _query(self, with_clause='', fields=None, groupby='', from_clause=''):
        if not fields:
            fields = {}
        with_ = ("WITH %s" % with_clause) if with_clause else ""
        return '%s (SELECT %s FROM %s WHERE l.activity_record_harvest_id=mc.id GROUP BY %s)' % \
               (with_, self._select_sale(fields), self._from_sale(from_clause), self._group_by_sale(groupby))

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))
