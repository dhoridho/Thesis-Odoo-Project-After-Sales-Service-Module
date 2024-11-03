from odoo import models, fields, _

class WebsiteMenuInherit(models.Model):
    _inherit = "website.menu"

    user_logged = fields.Boolean(
        string="User Logged",
        default=True,
        help=_("If checked, "
               "the menu will be displayed when the user is logged "
               "and give access.")
    )

    user_not_logged = fields.Boolean(
        string="User Not Logged",
        default=True,
        help=_("If checked, "
               "the menu will be displayed when the user is not logged "
               "and give access.")
    )

    def _compute_visible(self):
        """Display the menu item whether the user is logged or not."""
        res =super(WebsiteMenuInherit,self)._compute_visible()
        for menu in self:
            if not menu.is_visible:
                return
        # not_urls = [ '/page/job/list']
        not_urls_driver = ['/admin/delivery/routes']
        not_urls_admin = ['/page/job/list/driver', '/page/route/map']
        not_urls_cust = ['/admin/delivery/routes', '/page/job/list/driver', '/page/route/map']



        # menus = self.env['website.menu'].sudo().search([('url','in',not_urls)])
        menus_driver = self.env['website.menu'].sudo().search([('url','in',not_urls_driver)])
        menus_admin = self.env['website.menu'].sudo().search([('url','in',not_urls_admin)])
        menus_cust = self.env['website.menu'].sudo().search([('url','in',not_urls_cust)])
        for menu in self:
            portal_user_visible = ['/shop', '/', '/contactus','/vendor_sign_up','/open_tender']
            if self.env.user == self.env.ref('base.public_user'):
                if menu.url in portal_user_visible:
                    menu.is_visible = True
                else:
                    menu.is_visible = False

            else:
                res_users = self.env['res.users'].sudo().search([('id', '=', self.env.user.id)])
                res_partner = self.env['res.partner'].sudo().sudo().search([('id', '=', res_users.partner_id.id)])
                # if self.env.user.has_group('base.group_portal') and len(menus) != 0:
                #     for m in menus:
                #         m.is_visible = False
                if self.env.user.has_group('pragmatic_odoo_delivery_boy.group_pragtech_driver') and not self.env.user.has_group(
                        'pragmatic_delivery_control_app.group_delivery_control_app_manager') and len(menus_driver) != 0:
                    for m_driver in menus_driver:
                        m_driver.is_visible = False
                if not self.env.user.has_group('pragmatic_odoo_delivery_boy.group_pragtech_driver') and self.env.user.has_group(
                        'pragmatic_delivery_control_app.group_delivery_control_app_manager') and len(menus_admin) != 0:
                    for m_admin in menus_admin:
                        m_admin.is_visible = False
                if self.env.user.has_group('base.group_portal') and len(menus_cust) != 0:
                    for m_cust in menus_cust:
                        m_cust.is_visible = False
                menu.is_visible = menu.user_logged
            