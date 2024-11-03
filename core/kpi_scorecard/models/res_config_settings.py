# -*- coding: utf-8 -*-

from odoo import _, fields, models


class res_config_settings(models.TransientModel):
    """
    The model to keep settings of business appointments on website
    """
    _inherit = "res.config.settings"

    kpi_company_id = fields.Many2one(
        "res.company",
        string="Company for KPI settings",
        default=lambda self: self.env.user.company_id,
    )
    kpi_history_tolerance = fields.Integer(
        related="kpi_company_id.kpi_history_tolerance",
        readonly=False,
    )
    show_kpi_help = fields.Boolean(
        related="kpi_company_id.show_kpi_help",
        readonly=False,
    )

    def action_open_kpi_cron(self):
        """
        The method to open ir.cron of kpi update

        Returns:
         * action dict

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        cron_id = self.sudo().env.ref("kpi_scorecard.cron_recalculate_kpi_periods", False)
        if cron_id:
            return {
                "res_id": cron_id.id,
                "name": _("Job: Calculate KPIs"),
                "type": "ir.actions.act_window",
                "res_model": "ir.cron",
                "view_mode": "form",
                "target": "new",
            }       


