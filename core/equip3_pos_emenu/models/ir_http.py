# -*- coding: utf-8 -*-

from odoo import api, models

class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _get_error_html(cls, env, code, values):
        if code in ('page_404', 'protected_403'):
            
            #TODO: return hml to emenu_page_404 if url first path is /emenu
            path = values.get('path')
            if path and path[:5] == 'emenu':
                return code.split('_')[1], env['ir.ui.view']._render_template('equip3_pos_emenu.emenu_page_404', values)

            return code.split('_')[1], env['ir.ui.view']._render_template('website.%s' % code, values)
        return super(Http, cls)._get_error_html(env, code, values)
