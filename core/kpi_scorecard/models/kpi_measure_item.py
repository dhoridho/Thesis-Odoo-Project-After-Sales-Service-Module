#coding: utf-8

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class kpi_measure_item(models.Model):
    """
    The key model for KPI calulation
    """
    _name = "kpi.measure.item"
    _inherit = "kpi.help"
    _description = "KPI Measurement (Variable)"

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )
    measure_id = fields.Many2one(
        "kpi.measure",
        string="Measurement",
        required=True,
        domain=[("existing_kpi", "!=", False)],
    )
    domain = fields.Text(
        string="Extra Filters",
        default="[]",
        required=True,
    )
    model_id = fields.Many2one(
        related="measure_id.model_id",
        store=True,
        compute_sudo=True,
        related_sudo=True,
    )
    model_name = fields.Char(
        related="measure_id.model_name",
        store=True,
        compute_sudo=True,
        related_sudo=True,
    )
    measure_type = fields.Selection(
        related="measure_id.measure_type",
        store=True,
        compute_sudo=True,
        related_sudo=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company"
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
    existing_kpi = fields.Char(related="measure_id.existing_kpi",)

    _order = "sequence, id"

    def unlink(self):
        """
        The method to block unlink if used in any KPI
        """
        for kpi in self:
            measure_item_key = "MEASURE({})".format(kpi.id)
            domain = [
                ("formula", "like", measure_item_key),
                "|",
                    ("active", "=", False),
                    ("active", "=", True),
            ]
            kpi_id = self.env["kpi.item"].sudo().search(domain, limit=1)
            if kpi_id:
                raise ValidationError(
                    _("There are KPIs which depend on this MEASUREMENT: {}. Delete them before".format(kpi_id))
                )
        super(kpi_measure_item, self).unlink()

    def _calculate_for_period(self, period_id):
        """
        The method to calculate KPI for period

        Args:
         * period_id - kpi.period

        Returns:
         * float

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        self = self.sudo()
        measure = self.measure_id
        res = _("""Computation Error: KPI is not correctly defined. Perhaps, the related module was uninstalled or 
                field was removed. Please check basic measurements involved in formula""")
        date_start = period_id.date_start
        date_end = period_id.date_end
        company_id = period_id.company_id
        if measure.measure_type == "py_code":
            res = measure._execute_py_code(date_start, date_end, company_id)
        elif measure.model_id:
            considered_model = self.env[measure.model_name]
            try:
                domain = safe_eval(self.domain)+safe_eval(measure.domain)
                for date_field in measure.date_field_ids:
                    domain += [
                        (date_field.name, ">=", date_start),
                        (date_field.name, "<=", date_end),
                    ]
                if measure.company_field_id:
                    company_f = measure.company_field_name
                    domain += ["|", (company_f, "=", False), (company_f, "=", company_id.id)]
                if measure.measure_type == "count":
                    res = considered_model.search_count(domain)
                elif measure.measure_field_name:
                    if measure.measure_type == "sum":
                        res = sum(considered_model.search(domain).mapped(measure.measure_field_name))
                    elif measure.measure_type == "average":
                        all_records = considered_model.search(domain)
                        res = sum(all_records.mapped(measure.measure_field_name)) / len(all_records)
            except Exception as e:
                res = """{}
                {}""".format(res, e)
        return res