from odoo.addons.web.controllers.main import Action, Home, ensure_db
from odoo.tools.translate import _
from odoo.http import request
from odoo.exceptions import UserError
from odoo import http

class Action(Action):
    
    @http.route('/web/action/load', type='json', auth="user")
    def load(self, action_id, additional_context=None):
        res = super(Action,self).load(action_id, additional_context=additional_context)
        cids = request.httprequest.cookies.get('cids') and request.httprequest.cookies.get('cids').split(',')[0] or request.env.company.id
        if res:
            for view_data in set(request.env['remove.action'].sudo().search([('view_data_ids','!=',False),('access_management_id.company_ids','in',int(cids)),('access_management_id','in',request.env.user.access_management_ids.ids),('model_id.model','=',res.get('res_model'))]).mapped('view_data_ids.techname')):
                for views_data_list in res.get('views'):
                    if view_data == views_data_list[1]:
                        res['views'].pop(res['views'].index(views_data_list))       
            if 'views' in res.keys() and not len(res.get('views')):
               raise UserError(_("You don't have the permission to access any views. Please contact to administrator."))
        return res
    

class Home(Home):

    @http.route('/web', type='http', auth="none")
    def web_client(self, s_action=None, **kw):
        ensure_db()
        user = request.env.user.browse(request.session.uid)
        if len(user.company_ids) > 1:
            request.env['ir.ui.menu'].clear_caches()
        if not kw.get('debug') or kw.get('debug') != "0":
            # cids = request.httprequest.cookies.get('cids') and request.httprequest.cookies.get('cids').split(',')[0] or request.env.company.id
            # old version
            # access_management = request.env['access.management'].sudo().search([('active','=',True),('company_ids','in',int(cids)),('disable_debug_mode','=',True),('user_ids','in',user.id)],limit=1)
            access_management = request.env['access.management'].sudo().search([('active','=',True),('disable_debug_mode','=',True),('user_ids','in',user.id)],limit=1)
            
            if access_management.id:
                return http.local_redirect('/web?debug=0')

        return super(Home, self).web_client(s_action=s_action, **kw)
