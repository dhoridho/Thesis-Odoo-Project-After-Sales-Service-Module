# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2021. All rights reserved.

from odoo import fields, models, api, SUPERUSER_ID


class Website(models.Model):
    _inherit = 'website'

    def get_home_banner(self):
        home_banner = self.env['home.banner'].sudo().search([])
        return home_banner

    def get_category(self):
        category = self.env['fresh.foods.product.category'].sudo().search([])
        return category

    def get_our_product(self):
        our_product = self.env['our.products'].sudo().search([])
        return our_product

    def get_popular_product(self):
        popular_product = self.env['popular.products'].sudo().search([])
        return popular_product

    def get_half_banner(self):
        half_banner = self.env['half.banner'].sudo().search([])
        return half_banner

    def get_product_menu(self):
        product_menu = self.env['product.menu'].sudo().search([])
        return product_menu


class HomeBanner(models.Model):
    _name = "home.banner"
    _description = "Fresh Foods Home Banner"

    name = fields.Char(string="Name")
    heading = fields.Char(string="Add Heading")
    description = fields.Char(string="Add Description")


class ProductCategory(models.Model):
    _name = "fresh.foods.product.category"
    _rec_name = 'category_id'
    _description = "Product Category"

    category_id = fields.Many2one('product.public.category', string="Category")


class OurProducts(models.Model):
    _name = "our.products"
    _description = "Our Product"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.template', string="Product")


class PopularProducts(models.Model):
    _name = "popular.products"
    _description = "Popular Product"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.template', string="Product")


class HalfBanner(models.Model):
    _name = "half.banner"
    _description = "Half Banner"

    name = fields.Char(string="Name")
    # image = fields.Binary(string="Upload Image")
    heading = fields.Char(string="Add Heading")
    description = fields.Char(string="Add Description")


class ProductMenu(models.Model):
    _name = "product.menu"
    _description = "Product Menu"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.template', string="Product")

# class IrModuleModule(models.Model):
#     _name = "ir.module.module"
#     _description = 'Module'
#     _inherit = _name
#
#     @api.model
#     def _theme_remove(self, website):
#         if website.theme_id.name == "tis_jewellery_theme":
#             header = self.env['ir.ui.view'].sudo().search([('name', '=', 'Website Jewellery Header')])
#             header.unlink()
#             footer = self.env['ir.ui.view'].sudo().search([('name', '=', 'Jewellery Footer')])
#             footer.unlink()
#             footer_cpy = self.env['ir.ui.view'].sudo().search([('name', '=', 'Jewellery Copyright')])
#             footer_cpy.unlink()
#             home = self.env['ir.ui.view'].sudo().search([('name', '=', 'Home Jewellery')])
#             home.unlink()
#             env = api.Environment(self.env.cr, SUPERUSER_ID, {})
#             default_website = env.ref('website.default_website', raise_if_not_found=False)
#             default_homepage = env.ref('website.homepage_page', raise_if_not_found=False)
#             default_website.homepage_id = default_homepage.id
#         return super(IrModuleModule, self)._theme_remove(website)
