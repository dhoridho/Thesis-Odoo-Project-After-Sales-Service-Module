# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo import api, fields, models


class ApplicantRefusalReporting(models.Model):
    _name = "applicant.refusal.reporting"
    _auto = False

    applicant_id = fields.Many2one("hr.applicant", string="Applicant Id", readonly=True)
    job_id = fields.Many2one("hr.job", string="Applied Job", readonly=True)
    refuse_reason_id = fields.Many2one('hr.applicant.refuse.reason', string='Refuse Reason', readonly=True)
    partner_name = fields.Char("Applicant's Name", readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(ApplicantRefusalReporting, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(ApplicantRefusalReporting, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)


    def _select(self):
        select_str = """
            min(ha.id) as id,
            ha.id as applicant_id,
            ha.partner_name as partner_name,
            ha.refuse_reason_id as refuse_reason_id,
            ha.job_id,
            ha.category_id,
            ha.company_id"""
        return select_str

    def _from(self):
        from_str = """
            hr_applicant ha
             """
        return from_str

    def _where(self):
        where_str = """ 
            WHERE ha.active = False
        """
        return where_str

    def _group_by(self):
        group_by_str = """group by ha.id,ha.applicant_id,ha.partner_name,ha.refuse_reason_id,ha.job_id,ha.company_id"""

        return group_by_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as ( SELECT
                   %s
                   FROM %s
                   %s
                   %s
                   )""" % (self._table, self._select(), self._from(), self._where(), self._group_by()))

