#coding: utf-8

from odoo import api, fields, models


class kpi_copy_template(models.TransientModel):
    """
    The model to replace targets of this period with targets from another
    """
    _name = "kpi.copy.template"
    _inherit = "kpi.help"
    _description = "Template Targets Replace"

    period_id = fields.Many2one(
        "kpi.period",
        string="This Period",
        required=True,
    )
    template_id = fields.Many2one(
        "kpi.period",
        string="Substitute Targets With",        
        required=True,
    )

    def action_replace_targets(self):
        """
        The method to replace this period targets with template targets
        
        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        self = self.sudo()
        if self.period_id and self.period_id.state == "open" and self.template_id:
            self.period_id.write({
                "line_ids": False,
                "template_id": self.template_id.id,
            })
