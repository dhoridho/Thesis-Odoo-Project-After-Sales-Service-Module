#coding: utf-8

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class kpi_category(models.Model):
    """
    The model to structure KPIs and targets
    """
    _name = "kpi.category"
    _inherit = "kpi.help"
    _description = "KPI Category"

    @api.depends("user_ids", "user_group_ids", "user_group_ids.users")
    def _compute_access_user_ids(self):
        """
        Compute method for access_user_ids
        """
        for category in self:
            users = category.user_group_ids.mapped("users") + category.user_ids
            category.access_user_ids = [(6, 0, users.ids)]
    
    @api.depends("edit_user_ids", "edit_user_group_ids", "edit_user_group_ids.users")
    def _compute_edit_access_user_ids(self):
        """
        Compute method for edit_access_user_ids
        """
        for category in self:
            users = category.edit_user_group_ids.mapped("users") + category.edit_user_ids
            category.edit_access_user_ids = [(6, 0, users.ids)]

    @api.constrains('parent_id')
    def _check_node_recursion(self):
        """
        Constraint for recursion
        """
        if not self._check_recursion():
            raise ValidationError(_('It is not allowed to make recursions!'))
        return True

    def _inverse_active(self):
        """
        Inverse method for active to deactivate all child categories
        """
        for category in self:
            if not category.active:
                for categ in category.child_ids:
                    categ.active = False

    name = fields.Char(
        string="Name",
        required=True,
        translate=True,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        inverse=_inverse_active,
    )
    parent_id = fields.Many2one(
        "kpi.category",
        string="Parent Category",
    )
    child_ids = fields.One2many(
        "kpi.category",
        "parent_id",
        string="Child Categories",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
    )
    description = fields.Text(
        string="Notes",
        translate=True,
    )
    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many(
        "res.users",
        "res_users_kpi_category_rel_table",
        "res_user_rel_id",
        "kpi_category_id",
        string="Read Rights Users",
    )
    user_group_ids = fields.Many2many(
        "res.groups",
        "res_groups_kkpi_category_rel_table",
        "res_groups_id",
        "kpi_category_id",
        string="Read Rights User Groups",
    )
    access_user_ids = fields.Many2many(
        "res.users",
        "res_users_kpi_category_all_rel_table",
        "res_user_all_rel_id",
        "kpi_category_all_id",
        string="Read Rights Access Users",
        compute=_compute_access_user_ids,
        compute_sudo=True,
        store=True,
    )
    edit_user_ids = fields.Many2many(
        "res.users",
        "res_users_kpi_category_edit_rel_table",
        "res_user_rel_id",
        "kpi_category_id",
        string="Edit Rights Allowed Users",
    )
    edit_user_group_ids = fields.Many2many(
        "res.groups",
        "res_groups_kpi_category_edit_rel_table",
        "res_groups_id",
        "kpi_category_id",
        string="Edit Rights User Groups",
    )
    edit_access_user_ids = fields.Many2many(
        "res.users",
        "res_users_kpi_category_edit_all_rel_table",
        "res_user_all_rel_id",
        "kpi_category_all_id",
        string="Edit Rights Access Users",
        compute=_compute_edit_access_user_ids,
        compute_sudo=True,
        store=True,
    )

    _order = "sequence, id"

    def name_get(self):
        """
        Overloading the method, to reflect parent's name recursively
        """
        result = []
        for node in self:
            name = u"{}{}".format(
                node.parent_id and node.parent_id.name_get()[0][1] + '/' or '',
                node.name,
            )
            result.append((node.id, name))
        return result

    @api.model
    def action_return_nodes(self):
        """
        The method to return nodes in jstree format

        Methods:
         * _return_nodes_recursive

        Returns:
         * list of folders dict with keys:
           ** id
           ** text - folder_name
           ** icon
           ** children - array with the same keys
        """
        self = self.with_context(lang=self.env.user.lang)
        nodes = self.search([("parent_id", "=", False)])
        res = []
        for node in nodes:
            res.append(node._return_nodes_recursive())
        return res

    def _return_nodes_recursive(self):
        """
        The method to go by all nodes recursively to prepare their list in js_tree format

        Extra info:
         * sorted needed to fix unclear bug of zero-sequence element placed to the end
         * Expected singleton
        """
        self.ensure_one()
        res = {
            "text": self.name,
            "id": self.id,
        }
        if self._context.get("show_tooltip") and hasattr(self, "description") and self.description not in EMPTYHTML:
            res.update({"a_attr": {"kn_tip": self.description},})
        child_res = []
        for child in self.child_ids.sorted(lambda ch: ch.sequence):
            child_res.append(child._return_nodes_recursive())
        res.update({"children": child_res})
        return res
