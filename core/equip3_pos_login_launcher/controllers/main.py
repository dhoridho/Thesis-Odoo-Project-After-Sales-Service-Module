# -*- coding: utf-8 -*-

import odoo
from odoo import http, tools
from odoo.http import request
from odoo.addons.web.controllers.main import ensure_db
 
class PosLoginLauncher(http.Controller): 

    # TODO: Redirect to Point of Sale Dashboard
    @http.route('/pos/launcher', type='http', website=True, auth="user", sitemap=False)
    def pos_launcher(self, **kw):
        ensure_db()
        action_id = request.env.ref('point_of_sale.action_pos_config_kanban')
        redirect = f'/web#action={action_id.id}&model=pos.config&view_type=kanban'
        if request.session and request.session.uid:
            user_id = request.env['res.users'].browse(request.session.uid)
            redirect += f'&cids={user_id.company_id.id}&bids={user_id.branch_id.id}'
        menu_id = request.env.ref('point_of_sale.menu_pos_dashboard')
        if menu_id:
            redirect += f'&menu_id={menu_id.id}'

        return http.redirect_with_hash(redirect)