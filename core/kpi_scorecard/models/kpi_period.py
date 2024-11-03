#coding: utf-8

import base64
import logging
import tempfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.warning("Cannot import xlsxwriter")
    xlsxwriter = False


class kpi_period(models.Model):
    """
    The model to distinguish KPIs objects by periods
    """
    _name = "kpi.period"
    _inherit = "kpi.help"
    _description = "KPI Period"

    @api.depends("date_start", "date_end")
    def _compute_period_length(self):
        """
        Compute method for period_length
        """
        for period in self:
            period_length = 0
            if period.date_end and period.date_start:
                period_length = (period.date_end - period.date_start).days + 1
            period.period_length = period_length

    @api.depends("date_start", "date_end")
    def _compute_period_passed(self):
        """
        Compute method for period_passed
        """
        today = fields.Date.today()
        for period in self:
            period_passed = 1
            if period.date_end and period.date_start:
                if period.date_end <= today:
                    period_passed = period.period_length
                elif period.date_start < today:
                    period_passed = (today - period.date_start).days + 1
            period.period_passed = period_passed

    def _compute_parent_id(self):
        """
        Compute method for parent_id (e.g. for montly it would be quartely if exists or annually)
        """
        for period in self:
            parent_period = False
            if period.date_end and period.date_start:
                parent_period = self.search([
                    ("date_start", "!=", False),
                    ("date_end", "!=", False),
                    ("id", "!=", period.id),
                    ("date_start", "<=", period.date_start),
                    ("date_end", ">=", period.date_end),
                ], limit=1, order="period_length ASC, id")
            period.parent_id = parent_period

    def _inverse_template_id(self):
        """
        Inverse method for template_id
        """
        for period in self:
            if period.template_id:
                line_vals = []
                for line in period.template_id.line_ids:
                    if line.kpi_id.active:
                        line_vals.append((0, 0, {
                            "kpi_id": line.kpi_id.id,
                            "target_value": line.target_value,
                        }))
                if line_vals:
                    period.line_ids = line_vals
                period.template_id = False

    name = fields.Char(
        string="Reference",
        required=True,
        translate=True,
    )
    date_start = fields.Date(
        "Period Start",
        required=True,
        default=lambda self: fields.Date.today().strftime('%Y-01-01'),
    )
    date_end = fields.Date(
        "Period End",
        required=True,
        default=lambda self: fields.Date.today().strftime('%Y-12-31'),
    )
    line_ids = fields.One2many(
        "kpi.scorecard.line",
        "period_id",
        string="KPI Targets",
        copy=True,
    )
    period_length = fields.Float(
        string="Period Days",
        compute=_compute_period_length,
        store=True,
    )
    period_passed = fields.Float(
        string="Days Passed",
        compute=_compute_period_passed,
        store=False,
    )
    parent_id = fields.Many2one(
        "kpi.period",
        string="Parent Period",
        compute=_compute_parent_id,
    )
    state = fields.Selection(
        [
            ("open", "Opened"),
            ("closed", "Closed"),
        ],
        string="State",
        default="open",
    )
    template_id = fields.Many2one(
        "kpi.period",
        string="Copy targets from",
        inverse=_inverse_template_id,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.user.company_id,
    )
    last_recalculation_date = fields.Datetime(
        string="Last KPI Calculation",
        default=lambda self: fields.Datetime.now(),
    )

    _order = "date_start DESC, period_length, id"

    _sql_constraints = [
        (
            'dates_check',
            'check (date_end>=date_start)',
            _('Period end should be after period start')
        ),
    ]

    def name_get(self):
        """
        Overloading the method to include period start and end ino the names
        """
        result = []
        lang = self._context.get("lang")
        lang_date_format = "%m/%d/%Y"
        if lang:
            record_lang = self.env['res.lang'].search([("code", "=", lang)], limit=1)
            lang_date_format = record_lang.date_format
        for period in self:
            date_start = period.date_start.strftime(lang_date_format)
            date_end = period.date_end.strftime(lang_date_format)
            name = "{} ({} - {})".format(period.name, date_start, date_end)
            result.append((period.id, name))
        return result

    @api.model
    def action_return_periods(self):
        """
        The method to return available periods
        
        Returns:
         * dict
          ** all_periods - list of tuples 
          ** this_period - int - id
        """
        all_periods = self.search([])
        today = fields.Date.today()
        this_period = False
        if all_periods:
            this_periods = all_periods.filtered(lambda period: period.date_start <= today and period.date_end >= today)
            this_periods = this_periods.sorted("period_length", reverse=False)
            this_period = this_periods and this_periods[0].id or all_periods[0].id  
        return {
            "all_periods": all_periods and all_periods.mapped(lambda per: [per.id, per.name_get()[0][1], per.state]) \
                           or False,
            "this_period": this_period,
            "kpi_adming_rights": self.env.user.has_group("kpi_scorecard.group_kpi_admin"),
        }

    def action_calculate_kpis(self):
        """
        The method to update KPI values

        Methods:
         * _calculate_kpis
        """
        for period in self:
            period._calculate_kpis()

    @api.model
    def action_cron_calculate_kpi(self):
        """
        The method to find all periods for re-calculations
        """
        open_periods = self.search([("state", "=", "open")], order="last_recalculation_date ASC, id")
        open_periods.action_calculate_kpis()

    def action_export_scorecard(self):
        """
        The method to prepare the xls table

        Methods:
         * _get_xls_table of kpi.scorecard.line

        Returns:
         * action of downloading the xlsx table

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        if not xlsxwriter:
            raise UserError(_("The Python library xlsxwriter is installed. Contact your system administrator"))
        file_name = u"{}.xlsx".format(self.name_get()[0][1])
        file_path = tempfile.mktemp(suffix='.xlsx')
        workbook = xlsxwriter.Workbook(file_path)
        main_header_style =  workbook.add_format({
            'bold': True,
            'font_size': 11,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': 'silver',
            'border_color': 'gray',
        })
        main_cell_style_dict = {
            'font_size': 11,
            'border': 1,
            'border_color': 'gray',
        }
        worksheet = workbook.add_worksheet(file_name)
        column_keys = [
            {"key": "A", "label": _("KPI"), "width": 60},
            {"key": "B", "label": _("Target"), "width": 14},
            {"key": "C", "label": _("Actual"), "width": 14},
            {"key": "D", "label": _("Notes"), "width": 80},
        ]
        total_row_number = len(self.line_ids)
        cell_values = self.line_ids._get_xls_table()
        for ccolumn in column_keys:
            ckey = ccolumn.get("key")
            # set columns
            worksheet.set_column('{c}:{c}'.format(c=ckey), ccolumn.get("width"))
            # set header row
            worksheet.write("{}1".format(ckey), ccolumn.get("label"), main_header_style)
            # set column values
            for row_number in range(2, total_row_number+2):
                cell_number = "{}{}".format(ckey, row_number)
                cell_value_dict = cell_values.get(cell_number)
                cell_value = ""
                cell_level = 0
                cell_style = main_cell_style_dict.copy()
                if cell_value_dict:
                    cell_value = cell_value_dict.get("value")
                    cell_style.update(cell_value_dict.get("style")) 
                    cell_level = cell_value_dict.get("level") or 0
                cell_style = workbook.add_format(cell_style)
                if ckey == "A":
                    cell_style.set_indent(cell_level)
                worksheet.write(
                    cell_number, 
                    cell_value, 
                    cell_style,
                )  
        worksheet.set_row(0, 24)
        workbook.close()
        with open(file_path, 'rb') as r:
            xls_file = base64.b64encode(r.read())
        att_vals = {
            'name':  file_name,
            'type': 'binary',
            'datas': xls_file,
        }
        attachment_id = self.env['ir.attachment'].create(att_vals)
        self.env.cr.commit()
        action = {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment_id.id,),
            'target': 'self',
        }
        return action

    def action_close(self):
        """
        The method to close periods
        """
        for period in self:
            if period.state != "closed":
                period.state = "closed"
    
    def action_reopen(self):
        """
        The method to close periods
        """
        for period in self:
            if period.state != "open":
                period.state = "open"

    def _calculate_kpis(self):
        """
        The method to calculate KPIs for this period
         1. Firstly calculate all variables to avoid duplicated calculations
         2. Calculate all involved kpi.items
         3. Get actual value from calculated dict and save it to line

        Methods:
         * _get_measures of kpi.item
         * _calculate_for_period of kpi.measure.item
         * _get_value_by_period of kpi.constant
         * _calculate_by_measure of kpi.item

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        self = self.sudo()
        if self.state == "open":
            if self.line_ids:
                # 1
                all_variables_dict = {}
                all_kpis = self.line_ids.mapped("kpi_id")
                all_measures, all_constants, all_other_kpis = all_kpis._get_measures()
                all_kpis += all_other_kpis
                for measure in all_measures:
                    value = measure._calculate_for_period(self)
                    all_variables_dict.update({"MEASURE({})".format(measure.id): value})
                for cosntant in all_constants:
                    value = cosntant._get_value_by_period(self)
                    all_variables_dict.update({"CONST({})".format(cosntant.id): value})                       
                all_variables_dict.update({
                    "PERIOD_len": self.period_length,
                    "PERIOD_passed": self.period_passed,
                })
                # 2
                lines_iterator = 0
                while all_kpis:
                    this_kpi = all_kpis[lines_iterator]
                    kpi_id_reference = "KPI({})".format(this_kpi.id)
                    if not all_variables_dict.get(kpi_id_reference):
                        other_kpis = this_kpi.kpi_ids
                        for other_kpi in other_kpis:
                            other_value = all_variables_dict.get("KPI({})".format(other_kpi.id))
                            if other_value is None:
                                break
                        else:
                            # we have all data to process formula
                            all_kpis -= this_kpi
                            actual_value = this_kpi._calculate_by_measure(all_variables_dict)                        
                            all_variables_dict.update({kpi_id_reference: actual_value})             
                    else:
                        # seems excess to be here; but left for sudden cases
                        all_kpis -= this_kpi
                        all_variables_dict.update({kpi_id_reference: all_variables_dict.get(kpi_id_reference)})
                    lines_iterator += 1
                    if lines_iterator >= len(all_kpis):
                        # start from missed factors
                        lines_iterator = 0
                # 3
                for line in self.line_ids:
                    kpi_id_reference = "KPI({})".format(line.kpi_id.id)
                    actual_value = all_variables_dict.get(kpi_id_reference)
                    if isinstance(actual_value, str):
                        # it is the error
                        line.write({
                            "computation_error": actual_value,
                            "actual_value": 0,
                        })
                    else:
                        line.write({
                            "computation_error": False,
                            "actual_value": actual_value,
                        })
            self.last_recalculation_date = fields.Datetime.now()
            self._cr.commit()
