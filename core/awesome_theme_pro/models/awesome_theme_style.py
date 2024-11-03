# -*- coding: utf-8 -*-

from odoo import models, fields, api
import json
import logging
import base64

_logger = logging.getLogger(__name__)


class AwesomeThemeStyle(models.Model):
    '''
    user theme style setting
    '''
    _name = 'awesome_theme_pro.theme_style'
    _description = 'awesome theme style'
    _order = 'sequence'

    name = fields.Char(string="style name",
                       required=True)
    theme_mode = fields.Many2one(comodel_name="awesome_theme_pro.theme_mode",
                                 string="theme mode",
                                 ondelete="cascade")

    is_default = fields.Boolean(string="is default", default=False)

    owner = fields.Reference(
        string="owner",
        selection=[('res.company', 'res.company'),
                   ('res.users', 'res.users')],
        default=False,
        help="owner which this theme is create by")

    sequence = fields.Integer(string="style sequence")

    groups = fields.One2many(
        string="groups",
        comodel_name="awesome_theme_pro.style_item_group",
        inverse_name="theme_style")

    def get_style(self):
        '''
        get simple style data
        :return:
        '''
        self.ensure_one()
        result = self.read(['id', 'name', 'is_default'])[0]
        result["groups"] = self.groups.get_group_data()
        identities = dict()
        groups = result["groups"]
        # collect identity
        for group in groups:
            sub_groups = group["sub_groups"]
            for sub_group in sub_groups:
                style_items = sub_group["style_items"]
                for item in style_items:
                    if not item["vars"]:
                        continue
                    var_infos = item["vars"]
                    for var in var_infos:
                        if var.get('identity', False):
                            identities[var['identity']] = var['color']
        result["identities"] = identities
        return result

    def get_styles(self):
        '''i
        get mode datas
        :return:
        '''
        results = []
        for record in self:
            results.append(record.get_style())
        return results

    def _get_style_data(self):
        '''
        get mode datas
        :return:
        '''
        self.ensure_one()
        results = []
        result = self.read(['name', 'is_default', 'sequence'])[0]
        result["groups"] = self.groups.get_group_data()
        results.append(result)
        return results

    def get_styles_txt(self):
        '''
        get style txt
        :return:
        '''
        self.ensure_one()

        mode_prefix = 'body.' + self.theme_mode.name + ' '
        result = []
        groups = self.groups
        for group in groups:
            for sub_group in group.sub_groups:
                style_items = sub_group.style_items
                for style_item in style_items:
                    val = style_item.val
                    if val == "":
                        continue
                    if not style_item.selectors:
                        continue
                    try:
                        selector = mode_prefix + ','.join(json.loads(style_item["selectors"]))
                        tmp_txt = selector + " {" + val + "}"
                        result.append(tmp_txt)
                    except Exception as error:
                        _logger.info(error)

        return result

    def post_deal_preview_data(self, web_style_info, font_info):
        '''
        get mode datas
        :return:
        '''
        self.ensure_one()

        mode_prefix = 'body.' + self.theme_mode.name + ' '
        result = [font_info]
        groups = self.groups
        for group in groups:
            for sub_group in group.sub_groups:
                style_items = sub_group.style_items
                for style_item in style_items:
                    if str(style_item.id) not in web_style_info:
                        val = style_item.val
                        if val == "":
                            continue
                        if not style_item.selectors:
                            continue
                        try:
                            selector = mode_prefix + ','.join(json.loads(style_item["selectors"]))
                            tmp_txt = selector + " {" + val + "}"
                            result.append(tmp_txt)
                        except Exception as error:
                            _logger.info(error)
                    else:
                        result.append(web_style_info[str(style_item.id)])

        return "\n".join(result)

    @api.model
    def delete_style(self, style_id):
        '''
        delete styel of user
        :return:
        '''
        record = self.search([('id', '=', style_id)])
        record.unlink()

    def check_groups(self, groups):
        '''
        check the style group
        :param groups:
        :return:
        '''
        self.ensure_one()

        new_group_cache = {group["name"]: group for group in groups}
        old_group_cache = {group.name: group for group in self.groups}

        for group_index, default_group in enumerate(new_group_cache):
            if default_group["name"] not in old_group_cache:
                self.env['awesome_theme_pro.style_item_group']\
                    .create_group_from_default_data(self.id, default_group, group_index)
            else:
                # update the style item
                tmp_group = old_group_cache[default_group["name"]]
                tmp_group.write({
                    "name": default_group["name"],
                    "is_default": True,
                    "sequence": group_index,
                })
                # check group item data
                sub_group_items = default_group["sub_groups"]
                tmp_group.check_sub_group(sub_group_items)

        # delete the style item
        for tmp_group_name in old_group_cache:
            if tmp_group_name not in new_group_cache \
                    and old_group_cache[tmp_group_name].is_default:
                old_group_cache[tmp_group_name].unlink()

    def create_style_from_default_data(
            self, model_id, default_style_info, owner=False, is_default=True):
        '''
        create theme style from default info
        :return:
        '''
        default_groups = default_style_info['groups']

        group_datas = []
        for group_index, group in enumerate(default_groups):
            sub_groups = group["sub_groups"]
            sub_group_array = []
            for sub_group_index, sub_group in enumerate(sub_groups):

                style_items = sub_group["style_items"]
                style_item_datas = []
                for style_item_index, style_item in enumerate(style_items):
                    selectors = json.dumps(style_item['selectors'])
                    var_vals = []
                    var_infos = style_item['vars']
                    for var_info in var_infos:
                        var_vals.append((0, 0, {
                            "name": var_info["name"],
                            "is_default": is_default,
                            "type": var_info["type"],
                            "color": var_info.get('color', False),
                            "image": var_info.get('image', False),
                            "image_url": var_info.get('image_url', False),
                            "svg": var_info.get('svg', False),
                            "identity": var_info.get('identity', False)
                        }))

                    tmp_style_item = dict()
                    tmp_style_item['selectors'] = selectors
                    tmp_style_item['sequence'] = style_item_index
                    tmp_style_item['name'] = style_item["name"]
                    tmp_style_item["is_default"] = is_default
                    tmp_style_item["val_template"] = style_item["val_template"]
                    tmp_style_item["vars"] = var_vals

                    style_item_datas.append((0, 0, tmp_style_item))

                sub_group_array.append((0, 0, {
                    "name": sub_group["name"],
                    "sequence": sub_group_index,
                    "style_items": style_item_datas,
                    "is_default": True
                }))

            group_datas.append((0, 0, {
                "name": group["name"],
                "sequence": group_index,
                "sub_groups": sub_group_array,
                "is_default": True
            }))

        return self.env['awesome_theme_pro.theme_style'].create({
            "name": default_style_info["name"],
            "theme_mode": model_id,
            "is_default": is_default,
            "groups": group_datas,
            "owner": owner
        })

    @api.model
    def add_new_style(
            self, mode_id, style_data, owner=False, is_default=False):
        '''
        add new style, get the first style as the default, call from the front web
        :return:
        '''
        if not owner:
            theme_setting_mode = \
                self.env["res.config.settings"].sudo().get_theme_setting_mode()
            if theme_setting_mode == 'user':
                owner = 'res.users, {user_id}'.format(user_id=self.env.user.id)

        theme_style = self.create_style_from_default_data(
            mode_id, style_data, owner, is_default)
        # return the new style data
        style_data = theme_style.get_styles()[0]
        return style_data

    def clone_style(self, owner=False):
        '''
        clone style
        :return:
        '''
        if not owner:
            theme_setting_mode = \
                self.env["res.config.settings"].sudo().get_theme_setting_mode()
            if theme_setting_mode == 'user':
                owner = 'res.users, {user_id}'.format(user_id=self.env.user.id)

        style_data = self.get_styles()[0]
        return self.add_new_style(self.theme_mode.id, style_data, owner)

    @api.model
    def import_new_style(self, mode_id, wizard_id):
        """
        import new style
        :param mode_id:
        :param wizard_id:
        :return:
        """
        wizard = self.env["awesome_theme_pro.import_theme_style"].browse(wizard_id)
        style_data = json.loads(base64.decodebytes(wizard.file).decode('utf-8'))
        return self.add_new_style(mode_id, style_data)
