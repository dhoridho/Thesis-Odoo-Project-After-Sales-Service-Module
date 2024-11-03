# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models,fields,api
from odoo.http import request


class sh_wqm_quick_menu(models.Model):
    _name = "sh.wqm.quick.menu"
    _description = "quick / Shortcut menu model"
    _order = "id desc"
    
    menu_id = fields.Many2one(comodel_name = "ir.ui.menu",
                              string = "Menu",
                              required = True,
                              ondelete='cascade')
    user_id = fields.Many2one(comodel_name = "res.users",
                              string = "User",
                              required = True,
                              ondelete='cascade')
    
    parent_menu_id = fields.Integer(string = "Parent Menu ID")
    
    

    def set_quick_menu(self, action_id,parent_menu_id):
        if action_id:
            menu = self.env['ir.ui.menu'].sudo().search([('action', 'like', '%,' + str(action_id))], limit=1)
            if not menu:
                action = self.env['ir.actions.actions'].sudo().browse(int(action_id))
                if action:
                    menu = self.env['ir.ui.menu'].sudo().search([('name', '=', action.name), ('action', '!=', '')], limit=1)

            
            if menu:
                rec = self.sudo().search(
                    [('menu_id', '=', menu.id),
                     ('user_id', '=', self.env.user.id)])
                if (rec):
                    if (rec.sudo().unlink()):
                        return {
                            'is_set_quick_menu': False
                        }
                else:
                    if (menu and menu.action):
                        if (self.sudo().create({
                            'menu_id': menu.id,
                            'user_id': self.env.user.id,
                            'parent_menu_id' : int(parent_menu_id),
                        })):
                            return {
                                'is_set_quick_menu': True
                            }
        return {}
    
    def is_quick_menu_avail(self, action_id):
        if action_id:
            menu = self.env['ir.ui.menu'].sudo().search([('action', 'like', '%,' + str(action_id))], limit=1)
#             menu = False
            if not menu:
                action = self.env['ir.actions.actions'].sudo().browse(int(action_id))
                if action:
                    menu = self.env['ir.ui.menu'].sudo().search([('name', '=', action.name), ('action', '!=', '')], limit=1)
            
            if menu:
                result = self.is_already_have_in_quick_menu(menu.id)
                return result       
                    
    def is_already_have_in_quick_menu(self, menu_id):
        menu = self.env['ir.ui.menu'].sudo().browse(int(menu_id))
        if (menu and menu.action):
            rec = self.sudo().search(
                [('menu_id', '=', menu_id),
                 ('user_id', '=', self.env.user.id)])
            if (rec):
                return True
        return False

    def get_quick_menu_data(self, fields=[]): 
        search_quick_menu = self.sudo().search([
            ('user_id', '=', self.env.user.id),
            ])
        final_quick_menu_list = []
        if search_quick_menu:
            for rec in search_quick_menu:
                vals = {
                    'id'             : rec.menu_id.id,
                    'name'           : rec.menu_id.name,
                    'action_id'      : rec.menu_id.action.id,
                    'parent_menu_id' : rec.parent_menu_id
                    }
                final_quick_menu_list.append(vals)
                
        return final_quick_menu_list

    def remove_quick_menu_data(self, menu_id):
        if menu_id:
            rec = self.sudo().search(
                [('menu_id', '=', menu_id),
                 ('user_id', '=', self.env.user.id)])
            if rec:
                json = {
                    'id': rec.id,
                    'action_id': rec.menu_id.action.id,
                    'menu_id': rec.menu_id.id,
                }
                rec.sudo().unlink()
                return json
        return False    
    
class res_users(models.Model):
    _inherit = "res.users"
    
    sh_wqm_web_quick_menu_line = fields.One2many(comodel_name="sh.wqm.quick.menu",
                                                inverse_name="user_id",
                                                string = "Quick Menu",
                                                )
    
    sh_enable_one_click = fields.Boolean('Enable One Click Form Edit')

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights on livechat_username
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(res_users, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        # type(self).SELF_WRITEABLE_FIELDS = list(self.SELF_WRITEABLE_FIELDS)
        # type(self).SELF_WRITEABLE_FIELDS.extend(['sh_enable_one_click'])
        # duplicate list to avoid modifying the original reference
        # type(self).SELF_READABLE_FIELDS = list(self.SELF_READABLE_FIELDS)
        # type(self).SELF_READABLE_FIELDS.extend(['sh_enable_one_click'])
        return init_res


class Http(models.AbstractModel):
    _inherit = 'ir.http'
    
    def session_info(self):
        info = super().session_info()
        # user = request.env.user
        # info["sh_enable_one_click"] = user.sh_enable_one_click
        return info
    

    