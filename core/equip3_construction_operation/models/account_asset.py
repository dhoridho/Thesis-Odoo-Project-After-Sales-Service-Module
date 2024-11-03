from odoo import models, fields, api
from datetime import datetime, time


class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    project_id = fields.Many2one('project.project', string="Project")
    year = fields.Char('Year', compute="_compute_year_dep")
    month = fields.Char('Month', compute="_compute_month_dep")

    def _compute_year_dep(self):
        for res in self:
            dep = datetime.strptime(str(res.depreciation_date), "%Y-%m-%d")
            year_d = dep.strftime("%Y")
            res.write({
                    'year': year_d
            })

    def _compute_month_dep(self):
        for res in self:
            dep = datetime.strptime(str(res.depreciation_date), "%Y-%m-%d")
            month_d = dep.strftime("%B")
            res.write({
                    'month': month_d
            })
