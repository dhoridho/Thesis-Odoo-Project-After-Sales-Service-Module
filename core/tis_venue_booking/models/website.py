# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2021. All rights reserved.

from odoo import fields, models, SUPERUSER_ID, api


class website(models.Model):
    _inherit = 'website'

    def get_banner(self):
        banner = self.env['banner.banner'].sudo().search([])
        return banner

    def get_inner_banner(self):
        banner = self.env['inner.banner'].sudo().search([])
        return banner

class Banner(models.Model):
    _name = "banner.banner"
    _description = "Banner Section"
    _rec_name = 'name'

    name = fields.Char(string='Name')
    header = fields.Char(string='Header')
    description = fields.Text(string='Description')
    image = fields.Binary(string="Image")


class InnerBanner(models.Model):
    _name = "inner.banner"
    _description = "Banner Section in inner pages"
    _rec_name = 'name'

    name = fields.Char(string='Name')
    header = fields.Char(string='Header')
    description = fields.Text(string='Description')
    image = fields.Binary(string="Image")

