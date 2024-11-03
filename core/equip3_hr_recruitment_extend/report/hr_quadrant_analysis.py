# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class HRQuadrantAnalysisReport(models.Model):
    _name = "hr.quadrant.analysis.report"
    _auto = False

    applicant_id = fields.Char("Applicant's ID", readonly=True)
    applicant_name = fields.Many2one("hr.applicant", string="Applicant's Name", readonly=True)
    applicant_email = fields.Char("Email", readonly=True)
    job_id = fields.Many2one("hr.job", string="Applied Job", readonly=True)
    category_id = fields.Many2one("quadrant.category", string="Category", readonly=True)

    def _select(self):
        select_str = """
            min(ha.id) as id,
            ha.applicant_id,
            ha.id as applicant_name,
            ha.email_from as applicant_email,
            ha.job_id,
            ha.category_id"""
        return select_str

    def _from(self):
        from_str = """
                hr_applicant ha
             """
        return from_str

    def _group_by(self):
        group_by_str = """group by ha.id,ha.applicant_id,ha.email_from,ha.job_id,ha.category_id"""
        return group_by_str
        
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as ( SELECT
                   %s
                   FROM %s
                   %s
                   )""" % (self._table, self._select(), self._from(), self._group_by()))

