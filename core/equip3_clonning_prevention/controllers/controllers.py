# -*- coding: utf-8 -*-
from odoo.http import request
from odoo.addons.web.controllers.main import ensure_db, Home, Database
from odoo import http, _
import odoo
import requests
import ipaddress
from odoo.modules.module import get_module_path


class Equip3ClonningPreventionDatabase(Database):
    @http.route('/web/database/manager', type='http', auth="none")
    def manager(self, **kw):
        res = super(Equip3ClonningPreventionDatabase,self).manager(**kw)    
        ip_check = Equip3ClonningPreventionLogin().check_ip()
        if ip_check:
            return ip_check
        return res


    @http.route('/web/database/selector', type='http', auth="none")
    def selector(self, **kw):
        res = super(Equip3ClonningPreventionDatabase,self).selector(**kw)
        ip_check = Equip3ClonningPreventionLogin().check_ip()
        if ip_check:
            return ip_check
        return res
        
        
class Equip3ClonningPreventionLogin(Home):
    def get_public_ip(self):
        try:
            response = requests.get('https://httpbin.org/ip')
            public_ip = response.json()['origin']
            return public_ip
        except requests.RequestException:
            False

    def have_same_ip(self, list1, list2):
        ip_check = any(x in list2 for x in list1)
        return ip_check

    def check_ip(self):
        ip_list = [request.httprequest.remote_addr, self.get_public_ip()]
        module_path = get_module_path('equip3_clonning_prevention')
        fpath = module_path + '/data/'
        ip_text_rule = []
        with open(fpath+'ip.txt', 'r') as f:
            contents = f.read()
            if contents:
                ip_text_rule = eval(contents)
        
        ip_rules = request.env['ip.allowed.rules'].sudo().search(
            [('active_rules', '=', True)], limit=1)
        
        if not self.have_same_ip(ip_list,ip_text_rule):
            return request.render("equip3_clonning_prevention.not_allowed_page", {})
            
        if ip_rules:
            rules_ip = [data.name for data in ip_rules.rule_line_ids]
            if not self.have_same_ip(ip_list, rules_ip):
                return request.render("equip3_clonning_prevention.not_allowed_page", {})
            else:
                return False
        else:
            return False

    @http.route('/web/login', type='http', auth="none")
    def web_login(self, redirect=None, **kw):
        res = super(Equip3ClonningPreventionLogin,self).web_login(redirect=None, **kw)
        ip_check = self.check_ip()
        if ip_check:
            return ip_check
        
        return res
