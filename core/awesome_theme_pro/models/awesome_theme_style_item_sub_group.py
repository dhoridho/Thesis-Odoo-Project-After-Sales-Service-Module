# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
import logging, json

_logger = logging.getLogger(__name__)


class AwesomeStyleSubGroup(models.Model):
    '''
    user theme style group
    '''
    _name = 'awesome_theme_pro.style_item_sub_group'
    _order = 'sequence asc'
    _description = "style item group"

    name = fields.Char(string="name", required=True)
    is_default = fields.Boolean(string="is default", default=False)
    group = fields.Many2one(string="group",
                            comodel_name="awesome_theme_pro.style_item_group",
                            ondelete="cascade")
    sequence = fields.Integer(string="sequence", default=0)
    style_items = fields.One2many(
        string="style items",
        comodel_name="awesome_theme_pro.style_item",
        inverse_name="sub_group")

    def check_style_items(self, style_items):
        '''
        check group items, if not exsits create it else update it
        need fixed
        :return:0
        '''
        self.ensure_one()

        old_style_item_cache = {
            style_item.name: style_item for style_item in self.style_items}
        new_style_item_cache = {
            style_item["name"]: style_item for style_item in style_items}

        for style_item_index, style_item in enumerate(style_items):
            if style_item["name"] not in old_style_item_cache:
                self.env["awesome_theme_pro.style_item"].create_from_default_data(
                    self.id, style_item, style_item_index)
            else:
                old_style_item = old_style_item_cache[style_item["name"]]
                old_style_item.write({
                    "name": style_item["name"],
                    "sequence": style_item["sequence"],
                })
                item_vars = style_item["vars"]
                old_style_item.check_vars(self.id, item_vars)

            # delete the style item (just not default, user may add item)
            for tmp_style_item in self.style_items:
                if tmp_style_item.name not in new_style_item_cache \
                        and not old_style_item_cache[tmp_style_item.name].is_default:
                    old_style_item[tmp_style_item.name].unlink()

    def create_from_default_data(self, group, sub_group, sub_group_index):
        '''
        create sub group from default data
        :return:
        '''
        val = {
            "name": sub_group["name"],
            "group": group,
            "sequence": sub_group_index,
            "is_default": True
        }

        style_item_vals = []
        style_items = sub_group["style_items"]
        for item_index, item in enumerate(style_items):
            try:
                selectors = json.dumps(item["selectors"])
            except Exception as error:
                _logger.info('parse selectors error:', error)
                continue

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
                "vars": var_vals
            }))

        val["style_items"] = style_item_vals

        return self.create([val])

    def get_sub_group_data(self):
        '''
        get group data
        :return:
        '''
        sub_groups = []
        for record in self:
            sub_groups.append({
                "id": record.id,
                "name": record.name,
                "style_items": record.style_items.get_style_item_data(),
                "sequence": record.sequence,
                "is_default": record.is_default
            })
        return sub_groups

    def delete_sub_group(self):
        """
        delete sub group
        :return:
        """
        self.ensure_one()
        if len(self.style_items) > 0:
            raise exceptions.ValidationError(
                'there has some style item left, please delete the style item first!')
        self.unlink()
