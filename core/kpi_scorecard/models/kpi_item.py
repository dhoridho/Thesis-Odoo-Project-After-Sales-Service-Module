#coding: utf-8

import random
import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


OPERANDS = ["-", "+", "*", "/", "(", ")", "**"]
ERRORFORM = _("<ERROR!!!FORMULA PART DOES NOT EXIST>")

def cut_name_part(part):
    """
    The method to cut part name
    """
    if part and len(part) > 40:
        part = part[:38] + ".."
    return part

class kpi_item(models.Model):
    """
    The key model for KPI calulation
    """
    _name = "kpi.item"
    _inherit = "kpi.help"
    _description = "KPI"

    @api.depends("formula")
    def _compute_measures_ids(self):
        """
        Compute method for measures_ids, constant_ids, kpi_ids, formula_warning

        Methods:
         * action_render_formula
         * _check_formula_with_testing_data
        """
        self = self.sudo()
        for kpi in self:
            formula_parts = kpi.action_render_formula(kpi.formula)
            measures_ids = []
            constant_ids = []
            kpi_ids = []
            for part in formula_parts:
                if part.get("type") == "MEASURE":
                    measures_ids.append(part.get("res_id"))
                elif part.get("type") == "CONST":
                    constant_ids.append(part.get("res_id"))
                elif part.get("type") == "KPI":
                    kpi_ids.append(part.get("res_id"))
            measures_ids = self.env["kpi.measure.item"].browse(measures_ids).exists().ids
            kpi.measures_ids = [(6, 0, measures_ids)]
            constant_ids = self.env["kpi.constant"].browse(constant_ids).exists().ids
            kpi.constant_ids = [(6, 0, constant_ids)]
            kpi_ids = self.env["kpi.item"].browse(kpi_ids).exists().ids
            kpi.kpi_ids = [(6, 0, kpi_ids)]
            kpi.formula_warning = kpi._check_formula_with_testing_data()

    @api.depends("parent_id", "parent_id.all_parent_ids")
    def _compute_all_parent_ids(self):
        """
        Compute method for all_parent_ids. The idea is have full hierarchy for dependance
        """
        for kpi in self:
            kpi.all_parent_ids = [(6, 0, (kpi.parent_id + kpi.parent_id.all_parent_ids).ids)]

    @api.depends("user_ids", "user_group_ids", "user_group_ids.users", "category_id", "category_id.access_user_ids")
    def _compute_access_user_ids(self):
        """
        Compute method for access_user_ids
        """
        for line in self:
            own_users = line.user_group_ids.mapped("users") + line.user_ids
            category_users = line.category_id.access_user_ids
            users = own_users + category_users
            line.access_user_ids = [(6, 0, users.ids)]

    @api.depends("edit_user_ids", "edit_user_group_ids", "edit_user_group_ids.users", "category_id", 
                 "category_id.edit_access_user_ids")
    def _compute_edit_access_user_ids(self):
        """
        Compute method for edit_access_user_ids
        """
        for line in self:
            own_users = line.edit_user_group_ids.mapped("users") + line.edit_user_ids
            category_users = line.category_id.edit_access_user_ids
            users = own_users + category_users
            line.edit_access_user_ids = [(6, 0, users.ids)]

    @api.constrains('parent_id')
    def _check_hierarhcical_recursion(self):
        """
        Check hierarchical recursion

        Methods:
         * _check_recursion of models.py
        """
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive KPIs.'))
        return True

    @api.constrains('formula')
    def _check_formula_recursion(self):
        """
        Check formula recursion not to have other KPIs calculation leads to this calculation

        Methods:
         * _check_recursion of models.py
        """
        for kpi in self:
            parent_kpis = kpi.kpi_ids
            while parent_kpis:
                if kpi.id in parent_kpis.ids:
                    raise ValidationError(_(
                        'Other KPIs used in formula depends on this KPI. Calculation is impossible'
                    ))
                parent_kpis = parent_kpis.mapped("kpi_ids")
        return True

    @api.onchange("result_appearance")
    def _onchange_result_appearance(self):
        """
        Onchange method for result_appearance
        """
        for kpi in self:
            if kpi.result_appearance == "percentage":
                kpi.result_suffix = "%"

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )
    category_id = fields.Many2one(
        "kpi.category",
        string="Category",
        required=True,
    )
    formula = fields.Char(
        string="Formula",
    )
    formula_warning = fields.Char(
        string="Alert",
        compute=_compute_measures_ids,
        store=False,
    )
    line_ids = fields.One2many(
        "kpi.scorecard.line",
        "period_id",
        string="Targets"
    )
    result_type = fields.Selection(
        [
            ("more", "The more the better"),
            ("less", "The less the better"),
        ],
        string="Success Criteria",
        default="more",
        required=True,
    )
    result_appearance = fields.Selection(
        [
            ("number", "Number"),
            ("percentage", "Percentage"),
            ("monetory", "Monetary"),
        ],
        string="Result Type",
        default="number",
        required=True,
    )
    result_suffix = fields.Char(
        string="Result Suffix",
        help="would be shown after the result value",
    )
    result_preffix = fields.Char(
        string="Result Prefix",
        help="would be shown before the result value",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.user.company_id.currency_id,
    )
    result_rounding = fields.Selection(
        [
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
            ("4", "4"),
        ],
        string="Rounding Decimals",
        default="2",
    )
    parent_id = fields.Many2one(
        "kpi.item",
        string="Parent KPI",
    )
    all_parent_ids = fields.Many2many(
        "kpi.item",
        "kpi_item_kpi_item_all_parents_rel_table",
        "kpi_item_all_id",
        "kpi_item_all_back_id",
        string="All Parents",
        compute=_compute_all_parent_ids,
        compute_sudo=True,
        store=True,
    )
    child_ids = fields.One2many(
        "kpi.item",
        "parent_id",
        string="Child KPIs",
    )
    measures_ids = fields.Many2many(
        "kpi.measure.item",
        "kpi_item_kpi_measure_rel_table"
        "kpi_item_measure_rel_id",
        "kpi_measure_item_rel_id",
        string="Measurements",
        compute=_compute_measures_ids,
        context={'active_test':False},
    )
    constant_ids = fields.Many2many(
        "kpi.constant",
        "kpi_item_kpi_constant_rel_table",
        "kpi_item_id",
        "kpi_constant_id",
        string="Constants",
        compute=_compute_measures_ids,
        context={'active_test':False},
    )
    kpi_ids = fields.Many2many(
        "kpi.item",
        "kpi_item_kpi_item_rel_table",
        "kpi_item_this_id",
        "kpi_item_back_id",
        string="Other KPIs",
        compute=_compute_measures_ids,
        context={'active_test': False},
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
    user_ids = fields.Many2many(
        "res.users",
        "res_users_kpi_item_rel_table",
        "res_user_rel_id",
        "kpi_item_id",
        string="Allowed Users",
    )
    user_group_ids = fields.Many2many(
        "res.groups",
        "res_groups_kpi_item_rel_table",
        "res_groups_id",
        "kpi_item_id",
        string="Allowed User Groups",
    )
    access_user_ids = fields.Many2many(
        "res.users",
        "res_users_kpi_item_all_rel_table",
        "res_user_all_rel_id",
        "kpi_item_all_id",
        string="Access Users",
        compute=_compute_access_user_ids,
        compute_sudo=True,
        store=True,
    )
    edit_user_ids = fields.Many2many(
        "res.users",
        "res_users_kpi_item_edit_rel_table",
        "res_user_rel_id",
        "kpi_item_id",
        string="Edit Rights Allowed Users",
    )
    edit_user_group_ids = fields.Many2many(
        "res.groups",
        "res_groups_kpi_item_edit_rel_table",
        "res_groups_id",
        "kpi_item_id",
        string="Edit Rights User Groups",
    )
    edit_access_user_ids = fields.Many2many(
        "res.users",
        "res_users_kpi_item_edit_all_rel_table",
        "res_user_all_rel_id",
        "kpi_item_all_id",
        string="Edit Rights Access Users",
        compute=_compute_edit_access_user_ids,
        compute_sudo=True,
        store=True,
    )

    _order = "sequence, id"

    def unlink(self):
        """
        The method to block unlink if used in any KPI
        """
        for kpi in self:
            kpi_key = "KPI({})".format(kpi.id)
            domain = [
                ("formula", "like", kpi_key),
                "|",
                    ("active", "=", False),
                    ("active", "=", True),
            ]
            kpi_id = self.env["kpi.item"].sudo().search(domain, limit=1)
            if kpi_id:
                raise ValidationError(
                    _("There are KPIs which depend on this KPI: {}. Delete them before".format(kpi_id))
                )
        super(kpi_item, self).unlink()

    def action_return_measures(self, formula):
        """
        The method to return available measurements, constants

        Methods:
         * action_render_formula

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        measure_ids = self.env["kpi.measure.item"].search([('existing_kpi', '!=', False)]).mapped(lambda mes: {
            "id": mes.id,
            "name": mes.name,
            "description": mes.description or mes.name,
        })
        constant_ids = self.env["kpi.constant"].search([]).mapped(lambda const: {
            "id": const.id,
            "name": const.name,
            "description": const.description or const.name,
        })
        kpi_ids = self.env["kpi.item"].search([("id", "!=", self.id)]).mapped(lambda kpi: {
            "id": kpi.id,
            "name": kpi.name,
            "description": kpi.description or kpi.name,
        })
        formulaparts = self.action_render_formula(formula)
        return {
            "measures": measure_ids,
            "constants": constant_ids,
            "kpis": kpi_ids,
            "operands": OPERANDS,
            "formulaparts": formulaparts,
        }

    @api.model
    def action_render_formula(self, formula):
        """
        The method to split formula on parts
        
        Methods:
         * _get_id_from_string

        Returns:
         * list of dicts
          ** id
          ** name

        Extra info:
         * expected singleton
        """
        formula_parts = []
        if formula:
            formula_parts_str = formula.split(";")
            for part in formula_parts_str:
                if part.startswith("MEASURE"):
                    part_id = self._get_id_from_string(part)
                    if part_id:
                        measure_id = self.env["kpi.measure.item"].browse(part_id)
                        formula_parts.append({
                            "type": "MEASURE",
                            "res_id": part_id,
                            "id": part,
                            "name": measure_id.exists() and cut_name_part(measure_id.name) or ERRORFORM,
                            "extra_class": "kpi-measure-highlight",
                        })
                elif part.startswith("CONST"):
                    part_id = self._get_id_from_string(part)
                    if part_id:
                        const_id = self.env["kpi.constant"].browse(part_id)
                        formula_parts.append({
                            "type": "CONST",
                            "res_id": part_id,
                            "id": part,
                            "name": const_id.exists() and cut_name_part(const_id.name) or ERRORFORM,
                            "extra_class": "kpi-const-highlight",
                        })
                elif part.startswith("KPI"):
                    part_id = self._get_id_from_string(part)
                    if part_id:
                        kpi_id = self.env["kpi.item"].browse(part_id)
                        formula_parts.append({
                            "type": "KPI",
                            "res_id": part_id,
                            "id": part,
                            "name": kpi_id.exists() and cut_name_part(kpi_id.name) or ERRORFORM,
                            "extra_class": "kpi-kpi-highlight",
                        })
                elif part.startswith("PERIOD"):
                    if part == "PERIOD_len":
                        formula_parts.append({
                            "type": "PERIOD",
                            "res_id": False,
                            "id": part,
                            "name": _("Period Days"),
                            "extra_class": "kpi-measure-highlight",
                        })
                    elif part == "PERIOD_passed":
                        formula_parts.append({
                            "type": "PERIOD_passed",
                            "res_id": False,
                            "id": part,
                            "name": _("Days Passed"),
                            "extra_class": "kpi-measure-highlight",
                        })
                else:
                    formula_parts.append({
                        "type": "OPERATOR",
                        "res_id": False,
                        "id": part,
                        "name": part,
                        "extra_class": "kpi-element-operator kpi-operator-highlight",
                    })
        return formula_parts

    @api.model
    def action_open_formula_part(self, formula_part_id):
        """
        The method to open formula part (measure, cosntant, another kpi)

        Args: 
         * formula_part_id - char 

        Methods:
         * _get_id_from_string

        Returns:
         * action dict (or False if not connected)
        """
        res_id = False
        if formula_part_id:
            action = {
                "name": _("Details"),
                "view_mode": "form",
                "type": "ir.actions.act_window",
                "views": [(False, 'form')],
                "target": "new",
            }
            if formula_part_id.startswith("MEASURE"):
                res_id = self._get_id_from_string(formula_part_id)
                action.update({
                    "res_id": res_id,
                    "res_model": "kpi.measure.item",
                })
            elif formula_part_id.startswith("CONST"):
                res_id = self._get_id_from_string(formula_part_id)
                action.update({
                    "res_id": res_id,
                    "res_model": "kpi.constant",
                })
            elif formula_part_id.startswith("KPI"):
                res_id = self._get_id_from_string(formula_part_id)
                action.update({
                    "res_id": res_id,
                    "res_model": "kpi.item",
                })        
        return res_id and action or False

    def _calculate_by_measure(self, all_variables_dict):
        """
        The method to consturct formula with numeric values and calculate the result
        
        Returns:
         * float

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        try:
            if self.formula:
                numeric_formula = self.formula.replace(";", " ")
                for key, value in all_variables_dict.items():
                    if numeric_formula.find(key) != -1:
                        if isinstance(value, (int, float)):
                            numeric_formula = numeric_formula.replace(key, str(value))
                        else:
                            res = value
                            break
                else:
                    res = safe_eval(numeric_formula)
            else:
                res = _("Computation Error: the formula is empty")
        except Exception as e:
            res = _("Computation Error: {}".format(e))
        return res

    def _get_measures(self):
        """
        The method to recursively return included measures and constants
        
        Returns:
         * kpi.measure.item recordset
         * kpi.constant recordset
        """
        all_measures = self.mapped("measures_ids")
        all_constants = self.mapped("constant_ids")
        all_other_kpis = self.mapped("kpi_ids")
        if all_other_kpis:
            child_measures, child_constants, child_other_kpis = all_other_kpis._get_measures()
            all_measures += child_measures 
            all_constants += child_constants
            all_other_kpis += child_other_kpis
        return all_measures, all_constants, all_other_kpis

    def _check_formula_with_testing_data(self):
        """
        The method to check the formula with random tesing data
        
        Methods:
         * _calculate_by_measure

        Returns:
         * False if everything is fine
         * char - error messages otherwise

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        res = False
        if self.formula:
            all_variables_dict = {}
            for measure in self.measures_ids:
                if measure.existing_kpi != False:
                    res = _("The formula uses obsolete measurement: {}".format(measure.name))
                    break
                all_variables_dict.update({"MEASURE({})".format(measure.id): random.randint(5, 10000)})
            else:
                for constant in self.constant_ids:
                    all_variables_dict.update({"CONST({})".format(constant.id): random.randint(5, 10000)})        
                else:
                    all_variables_dict.update({
                        "PERIOD_len": 90,
                        "PERIOD_passed": 80,
                    })
                    for kpi in self.kpi_ids:
                        child_check = kpi._check_formula_with_testing_data()
                        if child_check:
                            res = _("The formula might rely upon incorrect KPI: {}.>> {}".format(kpi.name, child_check))
                            break                        
                        all_variables_dict.update({"KPI({})".format(kpi.id): random.randint(5, 10000)}) 
                    else:
                        value = self._calculate_by_measure(all_variables_dict)
                        if not isinstance(value, (int, float)):
                            res = _("The formula might be incorrect: {}".format(value))
        else:
            res = _("The formula is empty")
        return res

    @api.model
    def _get_id_from_string(self, str_id):
        """
        The method to retrieve int from string
        
        Args:
         * str_id - char
        
        Returns:
         * int
        """
        all_numbers = re.findall('\d+', str_id)
        return all_numbers and int(all_numbers[0]) or False

    def _return_formated_appearance(self, value, novalue_change=False, currency=False):
        """
        The method to format value accroding to KPI setting

        Args:
         * value - float
         * novalue_change - whether value should not be recalculated (e.g for % of target value)
         * currency - res.currency object

        Methods:
         * _return_rounded_value

        Returns:
         * str

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        formatted_value = self._return_rounded_value(value, novalue_change)
        formatted_value = isinstance(formatted_value, (int, float)) and "{:,}".format(formatted_value) \
                          or formatted_value
        currency = self.currency_id or currency
        if self.result_appearance in ["monetory"] and currency:
            currency_symbol = currency.symbol
            formatted_value = currency.position == "before" and "{}{}".format(currency_symbol, formatted_value) \
                              or "{}{}".format(formatted_value, currency_symbol)
        else:
            formatted_value = "{}{}{}".format(
                self.result_preffix or "", formatted_value, self.result_suffix or "",
            )
        return formatted_value

    def _return_rounded_value(self, value, novalue_change):
        """
        The method to return rounded value

        Args:
         * value - float
         * novalue_change - whether value should not be recalculated (e.g for % of target value)

        Returns:
         * int. float, or str
        """
        self.ensure_one()   
        result_appearance = self.result_appearance
        formatted_value = value 
        if result_appearance in ["number", "percentage", "monetory"]:    
            rounding = self.result_rounding and int(self.result_rounding) or 0
            formatted_value = result_appearance in ["number", "monetory"] and formatted_value \
                              or result_appearance in ["percentage"] and novalue_change and formatted_value \
                              or formatted_value * 100 \
                              or formatted_value
            formatted_value = round(formatted_value, rounding)
            if rounding == 0:
                formatted_value = int(formatted_value)
        return formatted_value

    def _return_xls_formatting(self, value, novalue_change=False):
        """
        The method to format value accroding to KPI setting for table cell

        Args:
         * value - float
         * novalue_change - whether value should not be recalculated (e.g for % of target value)

        Returns:
         * int or float
        """
        self.ensure_one()
        result_appearance = self.result_appearance
        rounding = self.result_rounding and int(self.result_rounding) or 0
        formatted_value = value
        if result_appearance in ["number", "percentage", "monetory"]:
            formatted_value = result_appearance in ["number", "monetory"] and formatted_value \
                              or result_appearance in ["percentage"] and novalue_change and formatted_value \
                              or formatted_value / 100 \
                              or formatted_value
            formatted_value = round(formatted_value, rounding)
            if rounding == 0:
                formatted_value = int(formatted_value)
        return formatted_value

