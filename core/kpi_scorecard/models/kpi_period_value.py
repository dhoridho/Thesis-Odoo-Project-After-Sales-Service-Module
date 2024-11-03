#coding: utf-8

from odoo import _, fields, models

class kpi_period_value(models.Model):
    """
    The model to distinguish KPIs constant values by periods
    """
    _name = "kpi.period.value"
    _description = "KPI Period Value"
    _rec_name = "period_id"

    period_id = fields.Many2one(
        "kpi.period",
        string="Period",
        required=True,
        ondelete="cascade",
    )
    constant_id = fields.Many2one(
        "kpi.constant",
        string="KPI Constant",
        ondelete="cascade",
    )
    target_value = fields.Float(
        string="Target Value",
    )

    _sql_constraints = [
        (
            'period_constant_id_uniq',
            'unique(period_id,constant_id)',
            _('Period should be unique per each constant!'),
        )
    ]
