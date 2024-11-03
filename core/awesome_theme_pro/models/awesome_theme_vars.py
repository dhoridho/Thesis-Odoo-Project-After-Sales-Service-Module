# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AwesomeThemeVar(models.Model):
    '''
    user theme style setting
    '''
    _name = 'awesome_theme_pro.theme_var'
    _order = 'sequence asc'
    _description = "css selector"

    style_item = fields.Many2one(
        comodel_name="awesome_theme_pro.style_item",
        string="style_item",
        required=True,
        ondelete="cascade")
    sequence = fields.Integer(string="sequence", default=0)
    type = fields.Selection(
        selection=[('color', 'color'),
                   ('image', 'image'),
                   ('image_url', 'image_url'),
                   ('svg', 'svg')],
        string="type",
        default="color")

    name = fields.Char(string="Name", default="var1")
    color = fields.Char(string="Val")
    image = fields.Binary(string="image", attachment=True)
    image_file_url = fields.Char(string="Image File Url", compute="_compute_image_file_url")
    image_url = fields.Char(string="Image Url")
    svg = fields.Text(string="Svg")

    identity = fields.Char(string="identify")
    is_default = fields.Boolean(string="is_default", default=False)

    @api.depends('image')
    def _compute_image_file_url(self):
        """
        compute image file url
        :return:
        """
        for record in self:
            if record.type == 'image' and record.image:
                record.image_file_url = \
                    '/web/image/awesome_theme_pro.theme_var/{var_id}/image'.format(var_id=record.id)
            else:
                record.image_file_url = False

    def get_edit_var_action(self):
        """
        get edit action
        :return:
        """
        return {
            "type": "ir.actions.act_window",
            "res_model": "awesome_theme_pro.theme_var",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "views": [[self.env.ref('awesome_theme_pro.edit_theme_var_form').id, "form"]]
        }

    def get_var_data(self):
        """
        get var data
        :return:
        """
        return self.read(
            fields=["name", "identity", "type", "image_file_url", "image_url", "color", "svg"])
