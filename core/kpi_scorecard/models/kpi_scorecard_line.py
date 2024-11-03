#coding: utf-8

from odoo import _, api, fields, models


class kpi_scorecard_line(models.Model):
    """
    KPI target
    """
    _name = "kpi.scorecard.line"
    _inherit = "kpi.help"
    _description = "KPI Target"
    _rec_name = "kpi_id"

    @api.depends("target_value", "actual_value", "computation_error", "kpi_id", "kpi_id.result_appearance", 
                 "kpi_id.result_preffix", "kpi_id.result_suffix", "kpi_id.result_type")
    def _compute_formatted_actual_value(self):
        """
        Compute method for formatted_actual_value, result, formatted_target_value

        Methods:
         * _return_formated_appearance of kpi.item
        """
        for line in self:
            kpi_id = line.kpi_id
            company_currency = line.period_id.company_id.currency_id
            if line.computation_error:
                line.formatted_actual_value = _("N/A")
                line.result = "error"
                line.formatted_target_value = kpi_id._return_formated_appearance(
                    line.target_value, novalue_change=True, currency=company_currency,
                )
            else:
                actual_value = line.actual_value
                line.formatted_actual_value = kpi_id._return_formated_appearance(
                    line.actual_value, novalue_change=False, currency=company_currency,
                )
                line.formatted_target_value = kpi_id._return_formated_appearance(
                    line.target_value, novalue_change=True, currency=company_currency,
                )
                result_type = kpi_id.result_type
                actual_value = line.kpi_id.result_appearance == "percentage" and (actual_value * 100) or actual_value
                bigger_result = actual_value >= line.target_value
                if result_type == "more":
                    line.result = bigger_result and "success" or "failure"
                elif result_type == "less":
                    line.result = bigger_result and "failure" or "success"

    @api.depends("period_id", "period_id.line_ids", "period_id.line_ids.kpi_id", "period_id.line_ids.kpi_id.sequence", 
                 "period_id.line_ids.kpi_id.all_parent_ids")
    def _compute_sequence(self):
        """
        The method to re-compute sequence, parent_id for lines
        """
        periods = self.mapped("period_id")
        for period in periods:
            res_hierarchy = period.line_ids.action_get_hierarchy() 
            cur_sequence = 0
            for line_dict in res_hierarchy:
                line = line_dict.get("line")
                line.sequence = cur_sequence
                parent = line_dict.get("parent")
                line.all_parents =  parent \
                                    and "{}{}".format(
                                        parent.id, 
                                        parent.all_parents and "{}".format("," + parent.all_parents) or ""
                                    ) \
                                    or False
                cur_sequence += 1

    @api.depends("kpi_id", "kpi_id.edit_access_user_ids")
    def _compute_edit_rights(self):
        """
        Compute method for edit_rights
        """
        active_user = self.env.user
        admin_rights = active_user.has_group("kpi_scorecard.group_kpi_admin")
        for line in self:
            line.edit_rights = admin_rights or active_user in line.kpi_id.edit_access_user_ids or False

    kpi_id = fields.Many2one(
        "kpi.item",
        string="KPI",
        required=True,
    )
    category_id = fields.Many2one(
        "kpi.category",
        related="kpi_id.category_id",
        store=True,
    )
    description = fields.Text(
        related="kpi_id.description",
        store=True,
    )
    period_id = fields.Many2one(
        "kpi.period",
        string="Period",
        ondelete="cascade",
    )
    target_value = fields.Float(string="Target Value")
    formatted_target_value = fields.Char(
        string="Target",
        compute=_compute_formatted_actual_value,
        compute_sudo=True,
        store=True,
    )
    actual_value = fields.Float(string="Actual Value")
    computation_error = fields.Char(string="Logs")
    formatted_actual_value = fields.Char(
        string="Actual",
        compute=_compute_formatted_actual_value,
        compute_sudo=True,
        store=True,
    )
    result = fields.Selection(
        [
            ("success", "Success"),
            ("failure", "Failure"),
            ("error", "Error"),
        ],
        compute=_compute_formatted_actual_value,
        compute_sudo=True,
        store=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        compute=_compute_sequence,
        compute_sudo=True,
        store=True,
    )
    all_parents = fields.Char(
        string="All Parents",
        compute=_compute_sequence,
        compute_sudo=True,
        store=True,
    )
    edit_rights = fields.Boolean(
        "Active User Editor",
        compute=_compute_edit_rights,
    )
    company_id = fields.Many2one(
        related="period_id.company_id",
        store=True,
        compute_sudo=True,
        related_sudo=True,
    )
    period_length = fields.Float(
        related="period_id.period_length",
        store=True,
        compute_sudo=True,
        related_sudo=True,
    )

    _order = "sequence, id"

    _sql_constraints = [
        (
            'period_kpi_uniq',
            'unique(period_id, kpi_id)',
            _('Target for this KPI is already set for this period'),
        )
    ]

    def name_get(self):
        """
        Overloading the method to make a name, since it doesn't have own
        """
        result = []
        for line in self:
            name = "{} ({})".format(line.kpi_id.name, line.period_id.name_get()[0][1])
            result.append((line.id, name))
        return result

    def action_get_hierarchy(self):
        """
        The method to get hirarchy of KPI targets
        
        Methods:
         * _get_levels_recursively
        
        Returns:
         * list of dict
        """
        kpi_ids = self.mapped("kpi_id")
        result = []
        if kpi_ids:
            kpi_ids = kpi_ids.sorted("sequence")
            kpi_lines_dict = {line.kpi_id.id: line for line in self} 
            parent_kpis = kpi_ids.filtered(lambda kpi: not kpi.parent_id or kpi.parent_id.id not in kpi_ids.ids)
            for parent_kpi in parent_kpis:
                line_id = kpi_lines_dict.get(parent_kpi.id)
                result += line_id._get_levels_recursively(parent_kpi, kpi_ids.ids, kpi_lines_dict, False)
        return result

    def action_get_history(self):
        """
        The method to find targets for the same KPI, same company and similar periods

        Returns:
         * dict :
          ** all_similar_targets - list of dicts to show in the table with formatted values
          ** similar_targets - list of dicts for graph

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        company_id = self.company_id
        all_similar_targets = self.search([
            ("kpi_id", "=", self.kpi_id.id),
            ("company_id", "=", company_id.id),
        ], order="period_id")
        all_similar_targets = all_similar_targets.mapped(lambda target: {
            "period_id": target.period_id.name_get()[0][1],
            "formatted_target_value": target.formatted_target_value,
            "formatted_actual_value": target.formatted_actual_value,
            "result": target.result,
        })
        lang = self._context.get("lang")
        lang_date_format = "%m/%d/%Y"
        if lang:
            record_lang = self.env['res.lang'].search([("code", "=", lang)], limit=1)
            lang_date_format = record_lang.date_format
        similar_targets = self.search([
            ("kpi_id", "=", self.kpi_id.id),
            ("company_id", "=", company_id.id),
            ("period_length", ">=", self.period_length - company_id.kpi_history_tolerance),
            ("period_length", "<=", self.period_length + company_id.kpi_history_tolerance),
        ], order="period_id DESC")
        similar_targets = similar_targets.mapped(lambda target: {
            "date": target.period_id.date_end.strftime(lang_date_format),
            "value": not target.computation_error and target.kpi_id._return_rounded_value(target.actual_value, False) \
                     or 0,
        })
        return {
            "all_similar_targets": all_similar_targets,
            "similar_targets": similar_targets,
            "kpi_name": self.kpi_id.name,
        }

    def _get_levels_recursively(self, parent_kpi, all_kpis, kpi_lines_dict, parent_line=False,):
        """
        The recursion method to get child kpi one by one
    
        Args:
         * parent_kpi - kpi.item record
         * all_kpis - list of ints
         * kpi_lines_dict - dict of relations kpi.scorecard.line (id - int) - kpi.item (id - int)
         * parent_line - id of parent

        Methods:
         * _get_value_dict

        Returns:
         * list of dicts

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        result = [self._get_value_dict(all_kpis, parent_line)]
        child_ids = self.kpi_id.child_ids
        for child_kpi in child_ids:
            child_kpi_id = child_kpi.id
            if child_kpi_id in all_kpis:
                line_id = kpi_lines_dict.get(child_kpi_id)
                result += line_id._get_levels_recursively(child_kpi, all_kpis, kpi_lines_dict, self)
        return result

    def _get_value_dict(self, all_kpis, parent_line=False):
        """
        The method to prepare values dict of js

        Args:
         * all_kpis - list of ints
         * parent_line - kpi.scorecard.line -parent

        Returns:
         * list of dict
           ** line - kpi.scorecard.line
           ** parent - int of parent if exist, False otherwise

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        return {
            "line": self,
            "parent": parent_line,
        }

    def _get_xls_table(self):
        """
        The method to prepare dict of values for xls row

        Args:
         * spaces - str - to add at the beginning of the name

        Methods:
         * _return_xls_formatting - of kpi.item
    
        Returns:
         * dict
        """
        result = {}
        row = 2
        previous_kpis = {}
        for line in self:
            parent_id = line.kpi_id.parent_id.id
            level = previous_kpis.get(parent_id) is not None and previous_kpis.get(parent_id) + 1 or 0
            previous_kpis.update({line.kpi_id.id: level})
            description = line.description or ""
            target_value = line.target_value
            actual_value = line.actual_value
            overall_style = { 
                "color": line.result == "success" and "black" or line.result == "failure" and "red" or "orange"
            }
            if line.computation_error:
                target_value = 0
                actual_value = 0
                description = "{} {}".format(line.computation_error, description)
                overall_style.update({"color": "orange"})
            target_value = line.kpi_id._return_xls_formatting(line.target_value, False)
            actual_value = line.kpi_id._return_xls_formatting(line.actual_value, True)
            num_style = overall_style.copy()
            num_style.update({
                "align": "center",
            })
            if line.kpi_id.result_appearance == "percentage":
                num_style.update({"num_format": 10}),
            overall_style.update({
                "valign": "vjustify",
            })
            result.update({
                "A{}".format(row): {"value": line.kpi_id.name, "style": overall_style, "level": level},
                "B{}".format(row): {"value": target_value, "style": num_style},
                "C{}".format(row): {"value": actual_value, "style": num_style},
                "D{}".format(row): {"value": description, "style": overall_style},
            })      
            row += 1
        return result