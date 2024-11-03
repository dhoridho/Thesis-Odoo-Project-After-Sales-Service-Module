#coding: utf-8

import numbers
from datetime import date, datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

DEFAULT_PYTHON_CODE = """# Make sure the 'result' is defined and it contains the new current value.
# Result should be of type integer or float
# For example, result = env["crm.lead"].search_count([('create_date', '>=', period_start+timedelta(days=1))])
# Available variables:
#  - env: Odoo Environment on which the action is triggered
#  - period_start, period_end - period on which the KPI is calculated 
#  - period_company_id - res.company object for which KPI target is calculated
#  - date, datetime, timedelta: useful Python libraries
result = 10\n\n\n\n"""

EXISTING_INSTALLED = _("In order to activate the KPI, please install the module for {}")

class kpi_measure(models.Model):
    """
    The core model of the module to calculate KPI figure

    * The idea of having computed and inversed model, date_field_id is to have prepared classifier even the linked 
      apps are not installed
    """
    _name = "kpi.measure"
    _inherit = "kpi.help"
    _description = "KPI Measurement"

    @api.model
    def _return_model(self):
        """
        The method to return available models
        """
        self._cr.execute("SELECT model, name FROM ir_model ORDER BY name")
        return self._cr.fetchall()

    @api.depends("model_name")
    def _compute_model_id(self):
        """
        Compute method for model_id

        Methods:
         * _return_model
         * _get_id of ir.model
        """ 
        all_models = [model_n[0] for model_n in self._return_model()]
        for measure in self:
            model_id = False
            if measure.model_name and measure.model_name in all_models:
                model_id = self.env["ir.model"].sudo().search([("model", "=", measure.model_name)], limit=1)
            measure.model_id  = model_id

    @api.depends("date_field_name")
    def _compute_date_field_ids(self):
        """
        Compute method for date_field_name

        Methods:
         * _get of ir.model.fields
        """ 
        for measure in self:
            res_ids = []
            all_field_names = measure.date_field_name
            existing_model = not measure.existing_kpi
            if all_field_names:
                all_fields = all_field_names.split(",")
                for field_date in all_fields:
                    field_id = existing_model and self.env["ir.model.fields"]._get(measure.model_name, field_date) \
                               or False
                    if field_id:
                        res_ids.append(field_id.id)
            measure.date_field_ids = [(6, 0, res_ids)]

    @api.depends("measure_field_name")
    def _compute_measure_field_id(self):
        """
        Compute method for measure_field_id

        Methods:
         * _get of ir.model.fields
        """ 
        for measure in self:
            field_id = not measure.existing_kpi \
                       and self.env["ir.model.fields"]._get(measure.model_name, measure.measure_field_name) or False
            measure.measure_field_id = field_id or False

    @api.depends("company_field_name")
    def _compute_company_field_id(self):
        """
        Compute method for company_field_id

        Methods:
         * _get of ir.model.fields
        """ 
        for measure in self:
            field_id = not measure.existing_kpi \
                       and self.env["ir.model.fields"]._get(measure.model_name, measure.company_field_name) or False
            measure.company_field_id = field_id or False

    @api.depends("model_name")
    def _compute_existing_kpi(self):
        """
        Compute method for existing_kpi
        """
        for measure in self:
            res = False
            if measure.measure_type in ["sum", "average", "count"] and measure.model_name and not measure.model_id:
                res = EXISTING_INSTALLED.format(measure.model_name)
            measure.existing_kpi = res

    @api.depends("item_ids")
    def _compute_measures_len(self):
        """
        Compute method for measures_len
        """
        for measure in self:
            measure.measures_len = len(measure.item_ids)

    def _inverse_model_id(self):
        """
        Inverse method for model_id
        """
        for measure in self:
            measure.model_name = measure.model_id and measure.model_id.model or False

    def _inverse_date_field_ids(self):
        """
        Inverse method for date_field_ids
        """
        for measure in self:
            measure.date_field_name = measure.date_field_ids and ",".join(measure.date_field_ids.mapped("name")) or \
                                      False

    def _inverse_measure_field_id(self):
        """
        Inverse method for measure_field_id
        """
        for measure in self:
            measure.measure_field_name = measure.measure_field_id and measure.measure_field_id.name or False

    def _inverse_company_field_id(self):
        """
        Inverse method for company_field_id
        """
        for measure in self:
            measure.company_field_name = measure.company_field_id and measure.company_field_id.name or False

    @api.onchange("model_id")
    def _onchange_model_id(self):
        """
        Onchange method for model_id - to update fields and 
        """
        for measure in self:
            company_field_id = False
            if measure.model_id:
                measure.model_name = measure.model_id.model
                company_field = self.env["ir.model.fields"]._get(measure.model_id.model, "company_id")
                if company_field:
                    company_field_id = company_field
            measure.date_field_ids = False
            measure.measure_field_id = False
            measure.company_field_id = company_field_id

    @api.model
    def search_existing_kpi(self, operator, value):
        """
        Search method for existing_kpi
        """
        all_measures = self.search([])
        measure_ids = []
        for measure in all_measures:
            res = False
            if measure.measure_type in ["sum", "average", "count"] and measure.model_name and not measure.model_id:
                res = EXISTING_INSTALLED.format(measure.model_name)            
            if value == False:
                if operator == "!=" and not res:
                    measure_ids.append(measure.id)
                elif operator == "=" and res:
                    measure_ids.append(measure.id)
            elif res and res.find(value) != -1:
                measure_ids.append(measure.id)
        return [('id', 'in', measure_ids)]

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )
    measure_type = fields.Selection(
        [
            ("sum", "Sum of records field"),
            ("average", "Average of records field"),
            ("count", "Count of records"),
            ("py_code", "Execute Python code"),
        ],
        string="KPI Type",
        default="sum",
        required=True,
    )
    py_code = fields.Text(
        string="Python Code",
        default=DEFAULT_PYTHON_CODE,
        help="Make sure the 'result' is defined and it contains the new current value."
    )
    model_name = fields.Char("Model Name")
    model_id = fields.Many2one(
        'ir.model', 
        string='Model', 
        compute=_compute_model_id,
        inverse=_inverse_model_id,
        readonly=False,
    )      
    domain = fields.Text(
        string="Filters",
        default="[]",
        required=True,
    )
    date_field_name = fields.Char(string="Date Field Name",)
    date_field_ids = fields.Many2many(
        "ir.model.fields",
        "ir_model_fields_kpi_measure_rel_table",
        "ir_model_field_date_id",
        "kpi_measure_rel_id",
        string='Date Fields',
        compute=_compute_date_field_ids,
        inverse=_inverse_date_field_ids,
        readonly=False,
        help="""
            According to those dates Odoo will calculate whether a record is within a specified period.
            In case there are a few of date fields, all of related dates should be within a period. 
        """,
    )
    measure_field_name = fields.Char(
        string="Measure Field Name",
    )
    measure_field_id = fields.Many2one(
        'ir.model.fields',
        string='Measure Field',
        compute=_compute_measure_field_id,
        inverse=_inverse_measure_field_id,
        readonly=False,
    ) 
    company_field_name = fields.Char(
        string="Company Field Name",
    )
    company_field_id = fields.Many2one(
        'ir.model.fields',
        string='Company Field',
        compute=_compute_company_field_id,
        inverse=_inverse_company_field_id,
        readonly=False,
    )
    existing_kpi = fields.Char(
        string="Installed",
        compute=_compute_existing_kpi,
        search="search_existing_kpi",
    )
    item_ids = fields.One2many(
        "kpi.measure.item",
        "measure_id",
        string="Measurements"
    )
    measures_len = fields.Integer(
        string="Measurements Count",
        compute=_compute_measures_len,
        store=True,
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

    def _execute_py_code(self, date_start, date_end, period_company_id):
        """
        The method to executr Python code

        Args:
         * date_start - date
         * date_end - date
         * period_company_id - res.company object

        Returns:
         * float or integer - if success
         * char - if error

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        cxt = {
            'env': self.env,
            'period_start': date_start,
            'period_end': date_end,
            "period_company_id": period_company_id,
            'date': date,
            'datetime': datetime,
            'timedelta': timedelta,
        }
        code = self.py_code.strip()
        try:
            safe_eval(code, cxt, mode="exec", nocopy=True)
            result = cxt.get('result')
            if result is None:
                result = _("Computation Error: Python code is incorrect: it doesn't contain 'result' key word")
            elif not isinstance(result, (int, float)):
                result = _(
                    "Computation Error: Python code is incorrect: it returns not number but {}".format(type(result))
                )
        except Exception as e:
            result = _("Computation Error: {}".format(e))
        return result
