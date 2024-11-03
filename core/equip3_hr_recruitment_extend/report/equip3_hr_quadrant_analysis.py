# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class Equip3HRQuadrantAnalysisReport(models.Model):
    _name = "equip3.hr.quadrant.analysis.report"
    _auto = False

    name = fields.Char('Name', readonly=True)
    job_id = fields.Many2one('hr.job', 'Jobs', readonly=True)
    quadrant_category = fields.Many2one("quadrant.category", string="Category", readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            qs.id as id,
            qs.applicant_name as name,
            qs.job_id as job_id,
            qc.id as quadrant_category
        """

        for field in fields.values():
            select_ += field

        from_ = """
                quadrant_score qs
                left join quadrant_category qc on qc.id=qs.category_id
                %s
        """ % from_clause

        groupby_ = """
            qc.id,
            qs.job_id,
            qs.id
            %s
        """ % (groupby)

        return '%s (SELECT %s FROM %s GROUP BY %s order by qs.id)' % (with_, select_, from_, groupby_)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))

