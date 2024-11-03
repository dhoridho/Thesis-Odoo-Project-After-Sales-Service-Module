# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo.addons.web.controllers.main import Home as Home
from odoo import http
from odoo.http import request


class Home(Home):
    
    @http.route(website=True, auth="public", sitemap=False)
    def web_login(self, redirect=None, *args, **kw):
        response = super(Home, self).web_login(redirect=redirect, *args, **kw)
        if not redirect and request.params['login_success']:
            
            if request.env['res.users'].browse(request.uid).has_group('base.group_user'):
                if request.uid:
                    res_users_obj = request.env['res.users']
                    search_user = res_users_obj.search([('id','=',request.uid)],limit=1)            
                    if search_user and search_user.sh_direct_redirect:
                        action_id = request.env.ref('sh_price_checker_kiosk.checker_action_kiosk_mode')
                        menu_id = request.env.ref('sh_price_checker_kiosk.price_checker_sub_menu')
                        redirect = '/web#action='+str(action_id.id)+'&menu_id='+str(menu_id.id)
                    else:
                        redirect =  '/web'   
            else:
                redirect = '/my'
            return http.redirect_with_hash(redirect)
        return response
    
    """
        import home controllers and override login method...
    """
    
    def _login_redirect(self, uid, redirect=None):

        res_users_obj = request.env['res.users']
        if uid:
            search_user = res_users_obj.search([('id','=',uid)],limit=1)            
            if search_user and search_user.sh_direct_redirect: 
                action_id = request.env.ref('sh_price_checker_kiosk.checker_action_kiosk_mode')
                menu_id = request.env.ref('sh_price_checker_kiosk.price_checker_sub_menu')
                return redirect if redirect else '/web#action='+str(action_id.id)+'&menu_id='+str(menu_id.id)
            else:
                return redirect if redirect else '/web'                
        
        return redirect if redirect else '/web'