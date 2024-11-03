# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
import logging
import json
import base64

_logger = logging.getLogger(__name__)


class AwesomeThemeStyleItem(models.Model):
    '''
    user theme style setting
    '''
    _name = 'awesome_theme_pro.style_item'
    _order = 'sequence asc'
    _description = "style item"

    sub_group = fields.Many2one(
        comodel_name="awesome_theme_pro.style_item_sub_group", string="sub group")
    sequence = fields.Integer(string="sequence", default=0)
    name = fields.Char(string="name", required=True, default="var1")
    val = fields.Char(string="val", compute="_compute_val")
    val_template = fields.Char(
        string="val template",
        required=True,
        default="background: {var1}", help="save the last val")
    vars = fields.One2many(
        string="vars",
        comodel_name="awesome_theme_pro.theme_var",
        inverse_name="style_item")
    selectors = fields.Char(string="selectors", required=True)
    is_default = fields.Boolean(string="is default", default=False)
    type = fields.Selection(
        string="type",
        selection=[('normal', 'normal'),
                   ('login', 'login')],
        default='normal')
    login_style = fields.Selection(
        string="login style",
        selection=[('login_style1', 'login_style1'),
                   ('login_style2', 'login_style2'),
                   ('login_style3', 'login_style3'),
                   ('login_style4', 'login_style4')],
        default="login_style1")

    def check_vars(self, sub_group, default_vars):
        '''
        check vars
        :return:
        '''
        # check vars
        self.ensure_one()

        # get current var cache
        old_var_cache = {var.name: var for var in self.vars}
        default_var_cache = \
            {default_var["name"]: default_var for default_var in default_vars}

        tmp_vals = []
        for default_var in default_vars:
            # item exits must keep
            if default_var["name"] not in old_var_cache:
                tmp_vals.append({
                    "sub_group": sub_group,
                    "name": default_var["name"],
                    "style_item": self.id,
                    "type": default_var["type"],
                    "color": default_var.get('color', False),
                    "image": default_var.get('image', False),
                    "image_url": default_var.get('image_url', False),
                    "svg": default_var.get('svg', False),
                    "is_default": default_var.get('is_default', True),
                    "identity": default_var.get('identity', False)
                })
            else:
                # keep the val, maybe user will
                tmp_var = old_var_cache[default_var["name"]]
                tmp_var.write({
                    "type": default_var["type"],
                    "is_default": default_var.get('is_default', True),
                    "identity": default_var.get('identity', False),
                    "color": default_var.get('color', False),
                    "image": default_var.get('image', False),
                    "image_url": default_var.get('image_url', False),
                    "svg": default_var.get('svg', False),
                })

        # create the missing vars
        self.env["awesome_theme_pro.theme_var"].create(tmp_vals)

        # unlink the old var
        for name in old_var_cache:
            if name not in default_var_cache:
                tmp_var = old_var_cache[name]
                tmp_var.unlink()

    @api.depends('selectors', 'val_template', "vars")
    def _compute_val(self):
        '''
        compute the val
        :return:
        '''
        for record in self:
            vars_cache = dict()
            for var in record.vars:
                if var.type == 'color':
                    vars_cache[var.name] = var.color
                elif var.type == 'image':
                    vars_cache[var.name] = var.image_file_url
                elif var.type == 'image_url':
                    vars_cache[var.name] = var.image_url
                else:
                    vars_cache[var.name] = var.svg

            if not record.vars:
                record.val = ''
            else:
                try:
                    record.val = str(record.val_template).format(**vars_cache)
                except Exception as error:
                    record.val = ""
                    _logger.info('parse var value error, item name {item_name}->{error}'.format(
                        item_name=record['name'], error=error))

    def get_style_item_data(self):
        '''
        get the style item data
        :return:
        '''
        export_style = self.env.context.get('export_style', False)
        style_items = []
        for record in self:
            style_item = record.read(
                fields=["id", "name", "is_default", "val_template", "val", "selectors"])[0]

            try:
                style_item['selectors'] = json.loads(style_item['selectors'])
            except Exception as error:
                _logger.info('try to decode selectors error!', error)

            if not export_style:
                # maybe the image is very large, so do not read the image
                style_item["vars"] = \
                    record.vars.read(
                        ["name", "identity", "type", "image_file_url", "image_url", "color", "svg"])
            else:
                style_item["vars"] = \
                    record.vars.read(
                        ["name", "identity", "type", "image", "image_url", "color", "svg"])
                for tmp_var in style_item["vars"]:
                    if tmp_var["image"]:
                        tmp_var["image"] = str(tmp_var["image"])

            style_items.append(style_item)
        return style_items

    def write(self, vals):
        """
        rewrite to check if the selectors are right
        :param vals:
        :return:
        """
        super(AwesomeThemeStyleItem, self).write(vals)

        vars_cache = dict()
        for var in self.vars:
            if var.type == 'color':
                vars_cache[var.name] = var.color
            elif var.type == 'image':
                vars_cache[var.name] = var.image_file_url
            elif var.type == 'image_url':
                vars_cache[var.name] = var.image_url
            else:
                vars_cache[var.name] = var.svg

        try:
            str(self.val_template).format(**vars_cache)
        except Exception as error:
            raise exceptions.ValidationError(
                'format val template error, is the vars compatible')

    def get_login_style_data(
            self, theme_style_id, login_style):
        """
        get login style data
        :return:
        """
        result = []
        theme_style = self.env["awesome_theme_pro.theme_style"].browse(theme_style_id)
        sub_group_ids = theme_style.mapped('groups.sub_groups.id')
        style_items = self.search(
            [('type', '=', 'login'),
             ('login_style', '=', login_style),
             ('sub_group', 'in', sub_group_ids)])
        for style_item in style_items:
            val = style_item.val
            if val == "":
                continue
            if not style_item.selectors:
                continue
            try:
                selector = ','.join(json.loads(style_item["selectors"]))
                tmp_txt = selector + " {" + val + "}"
                result.append(tmp_txt)
            except Exception as error:
                _logger.info(error)
        return ";".join(result)

    def delete_style_item(self):
        '''
        delete style item
        :return:
        '''
        self.ensure_one()
        self.unlink()

