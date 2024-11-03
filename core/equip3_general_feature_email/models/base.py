# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, exceptions, fields, models, _
import urllib.parse
from odoo.http import request


class Base(models.AbstractModel):
    """ The base model, which is implicitly inherited by all models. """
    _inherit = 'base'

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(Base, self).fields_view_get(view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if request.params.get('action_id'):
            request.session['history_action_'+self._name]= request.params['action_id']
        elif request.params.get('kwargs'):
            if request.params['kwargs'].get('options') and request.params['kwargs']['options'].get('action_id'):
                request.session['history_action_'+self._name] = request.params['kwargs']['options']['action_id']
                
       
            
        return res
