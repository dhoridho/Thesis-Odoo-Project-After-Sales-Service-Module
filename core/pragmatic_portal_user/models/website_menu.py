# -*- coding: utf-8 -*-

from odoo import api, fields, models


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    def _compute_visible(self):
        res = super(WebsiteMenu, self)._compute_visible()
        not_urls_delivery_boy = ['/admin/delivery/routes', '/contactus', '/shop', '/', '/shop/cart']
        menu_delivery_boy = self.env['website.menu'].sudo().search([('url', 'in', not_urls_delivery_boy)])
        customer_menu = ['/page/job/list/driver', '/page/route/map', '/admin/delivery/routes', '/driver/broadcast/order',
         '/page/job/list/driver/paid', '/page/job/list/driver/reject']
        res_users = self.env['res.users'].sudo().search([('id', '=', self.env.user.id)])
        for menu in self:
            portal_user_visible = ['/shop', '/', '/contactus','/vendor_sign_up','/open_tender']
            if self.env.user == self.env.ref('base.public_user'):
                if menu.url in portal_user_visible:
                    menu.is_visible = True
                else:
                    menu.is_visible = False
            elif self.env.user.has_group('base.group_portal') and not res_users.partner_id.is_driver:
                if menu.url in customer_menu:
                    menu.is_visible = False

            else:
                if self.env.user.has_group('base.group_portal') and len(
                        menu_delivery_boy) != 0 and res_users.partner_id.is_driver:
                    for m_delivery in menu_delivery_boy:
                        m_delivery.is_visible = False
                menu.is_visible = menu.user_logged
