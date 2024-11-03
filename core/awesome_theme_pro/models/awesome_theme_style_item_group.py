# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
import logging, json

_logger = logging.getLogger(__name__)


class AwesomeStyleGroup(models.Model):
    '''
    user theme style group
    '''
    _name = 'awesome_theme_pro.style_item_group'
    _order = 'sequence asc'
    _description = "style item group"

    name = fields.Char(string="name", required=True)
    is_default = fields.Boolean(string="is default", default=False)
    theme_style = fields.Many2one(string="theme style",
                                  comodel_name="awesome_theme_pro.theme_style",
                                  ondelete="cascade")
    sub_groups = fields.One2many(
        string="sub groups",
        comodel_name="awesome_theme_pro.style_item_sub_group",
        inverse_name="group")
    sequence = fields.Integer(string="sequence", default=0)

    def check_sub_group(self, sub_groups):
        '''
        check group items, if not exsits create it else update it
        need fixed
        :return:0
        '''
        self.ensure_one()

        old_sub_group_cache = {
            sub_group.name: sub_group for sub_group in self.sub_groups}
        default_sub_group_cache = {
            default_group["name"]: default_group for default_group in sub_groups}

        for sub_group_index, sub_group in sub_groups:
            if sub_group["name"] not in old_sub_group_cache:
                self.env['awesome_theme_pro.style_item_sub_group']\
                    .create_from_default_data(self.id, sub_group, sub_group_index)
            else:
                # update the style item
                tmp_group = old_sub_group_cache[sub_group["name"]]
                tmp_group.write({
                    "name": sub_group["name"],
                    "is_default": True,
                    "sequence": sub_group_index,
                })
                # check group item data
                style_items = sub_group["style_items"]
                tmp_group.check_style_items(style_items)

        # delete the style item (just not default, user may add item)
        for sub_group_name in old_sub_group_cache:
            if sub_group_name not in default_sub_group_cache \
                    and not old_sub_group_cache[sub_group_name].is_default:
                old_sub_group_cache[sub_group_name].unlink()

    def create_group_from_default_data(self, theme_style, group, group_index):
        '''
        create group from default data
        :return:
        '''

        val = {
            "name": group["name"],
            "theme_style": theme_style,
            "sequence": group_index,
        }

        sub_group_array = []
        sub_groups = group["sub_groups"]
        for sub_group_index, sub_group in enumerate(sub_groups):

            style_item_vals = []
            items = sub_group["style_items"]
            for item_index, item in enumerate(items):
                selectors = json.dumps(item["selectors"])
                var_infos = item["vars"]

                var_vals = []
                for var_index, var_info in enumerate(var_infos):
                    var_vals.append((0, 0, {
                        "name": var_info["name"],
                        "type": var_info["type"],
                        "sequence": var_index,
                        "color": var_info.get('color', False),
                        "image": var_info.get('image', False),
                        "image_url": var_info.get('image_url', False),
                        "svg": var_info.get('svg', False),
                        "identity": var_info.get('identity', False)
                    }))

                style_item_vals.append((0, 0, {
                    "name": item["name"],
                    "sequence": item_index,
                    "sub_group": sub_group["name"],
                    "selectors": selectors,
                    "default_val": item["default_val"],
                    "vars": var_vals
                }))

            sub_group_array.append((0, 0, {
                "name": sub_group["name"],
                "sequence": sub_group_index,
                "style_items": style_item_vals,
                "is_default": True
            }))

        val["sub_groups"] = sub_group_array
        return self.create([val])

    @api.model
    def get_add_new_group_action(self, style_id):
        """
        get add new group action
        :param style_id:
        :return:
        """
        theme_style = self.env["awesome_theme_pro.theme_style"].browse(style_id)
        old_groups = theme_style.groups
        return {
            "type": "ir.actions.act_window",
            "res_model": "awesome_theme_pro.style_item_group",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_theme_style": style_id,
                "default_sequence": len(old_groups) + 1
            },
            "views": [[self.env.ref('awesome_theme_pro.style_item_group_form').id, "form"]]
        }

    def get_group_data(self):
        """
        get sub group data
        :return:
        """
        group_datas = []
        for record in self:
            group_datas.append({
                "id": record.id,
                "name": record.name,
                "is_default": record.is_default,
                "sequence": record.sequence,
                "sub_groups": record.sub_groups.get_sub_group_data()
            })
        return group_datas

    def get_add_sub_group_action(self):
        """
        get add sub group action
        :return:
        """
        return {
            "type": "ir.actions.act_window",
            "res_model": "awesome_theme_pro.style_item_sub_group",
            "view_mode": 'form',
            "target": "new",
            "context": {
                "default_group": self.id,
            },
            "views": [[self.env.ref('awesome_theme_pro.style_item_sub_group_form').id, "form"]]
        }

    def delete_item_group(self):
        """
        delete item group
        :return:
        """
        if len(self.sub_groups) > 0:
            raise exceptions.ValidationError(
                'there has some sub group left, please delete them first!')
        self.unlink()
