#coding: utf-8

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class kpi_constant(models.Model):
    """
    The model to use static figures for calculations
    """
    _name = "kpi.constant"
    _inherit = "kpi.help"
    _description = "KPI Constant"

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )
    target_value = fields.Float(
        "Global Value",
        help="Value used in case this constant is not applied for a target period",
    )
    periods_ids = fields.One2many(
        "kpi.period.value",
        "constant_id",
        string="Set for periods",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    description = fields.Text(
        string="Notes",
        translate=True,
    )
    sequence = fields.Integer(string="Sequence")

    _order = "sequence, id"

    def unlink(self):
        """
        The method to block unlink if used in any KPI
        """
        for constant in self:
            const_key = "CONST({})".format(constant.id)
            domain = [
                ("formula", "like", const_key),
                "|",
                    ("active", "=", False),
                    ("active", "=", True),
            ]
            kpi_id = self.env["kpi.item"].sudo().search(domain, limit=1)
            if kpi_id:
                raise ValidationError(
                    _("There are KPIs which depend on this constant: {}. Delete them before".format(kpi_id))
                )
        super(kpi_constant, self).unlink()

    def _get_value_by_period(self, period_id):
        """
        The method to find target value by date
        We search the most preceis constant definition: if it monthly period > but there is no constant for this month,
        we also check quarterly and yearly intervals
        
        Args:
         * period_id - kpi.period 

        Returns:
         * float

        Extra info
         * the method is hierarchicallyr recursive to check parents
         * Expected singleton
        """
        self.ensure_one()
        target_value = self.target_value
        for constant_period in self.periods_ids:
            if period_id == constant_period.period_id:
                target_value = constant_period.target_value
                break
        else:
            if period_id.parent_id:
                target_value = self._get_value_by_period(period_id.parent_id) 
            else:
                target_value = self.target_value
        return target_value
