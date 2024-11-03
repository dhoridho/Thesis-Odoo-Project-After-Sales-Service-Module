# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2019. All rights reserved.

from odoo.addons.mail.controllers.main import MailController
from odoo import http




class Main(http.Controller):

    @http.route('/web/map_theme', type='json', auth='user')
    def map_theme(self):
        ICP = http.request.env['ir.config_parameter'].sudo()
        theme = ICP.get_param('google.maps_theme', default='default')
        res = {'theme': theme}
        return res
