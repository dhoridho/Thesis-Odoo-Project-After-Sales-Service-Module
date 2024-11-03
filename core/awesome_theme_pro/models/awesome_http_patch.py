# -*- coding: utf-8 -*-

import logging
from odoo import models
from odoo.http import request

from odoo.http import ALLOWED_DEBUG_MODES
from odoo.tools.misc import str2bool

_logger = logging.getLogger(__name__)


class IrHttpExtend(models.AbstractModel):
    '''
    disable debug mode
    '''
    _inherit = 'ir.http'

    def session_info(self):
        """
        extend session info
        :return:
        """
        res = super(IrHttpExtend, self).session_info()
        group_infos = self.env["res.users"].get_group_infos()
        res["group_infos"] = group_infos
        res["user_context"]["group_ids"] = group_infos["group_ids"]
        return res

    @classmethod
    def _handle_debug(cls):
        # Store URL debug mode (might be empty) into session
        if 'debug' in request.httprequest.args:
            debug_mode = []
            for debug in request.httprequest.args['debug'].split(','):
                if debug not in ALLOWED_DEBUG_MODES:
                    debug = '1' if str2bool(debug, debug) else ''
                debug_mode.append(debug)

            debug_mode = ','.join(debug_mode)

            # force debug mode to empty
            # allow_debug = request.env["res.config.settings"].sudo().is_allow_debug()
            # if not allow_debug:
            # debug_mode = ''

            # Write on session only when needed
            if debug_mode != request.session.debug:
                request.session.debug = debug_mode
