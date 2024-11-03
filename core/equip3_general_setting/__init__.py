from . import models
from . import controllers

from odoo import api, _
from odoo.exceptions import AccessError
from odoo.tools import lazy_property
from odoo.http import request, OpenERPSession
from odoo.addons.branch.models.ir_http import Http
from .models.ir_http import Http as GeneralSettingHttp


class Environment(api.Environment):
    @lazy_property
    def branch(self):
        branch_ids = self.context.get('allowed_branch_ids', [])
        if branch_ids:
            if not self.su:
                user_branch_ids = self.user.branch_ids.ids
                if any(bid not in user_branch_ids for bid in branch_ids):
                    raise AccessError(_("Access to unauthorized or invalid branches."))
            return self['res.branch'].browse(branch_ids[0])
        return self.user.branch_id

    @lazy_property
    def branches(self):
        branch_ids = self.context.get('allowed_branch_ids', [])
        if branch_ids:
            if not self.su:
                user_branch_ids = self.user.branch_ids.ids
                if any(bid not in user_branch_ids for bid in branch_ids):
                    raise AccessError(_("Access to unauthorized or invalid branches."))
            return self['res.branch'].browse(branch_ids)
        return self.user.branch_ids

    @lazy_property
    def company_branches(self):
        return self.branches.filtered(lambda o: o.company_id == self.company)

def session_info(self):
    return super(Http, self).session_info()
    

def _monkey():
    api.Environment.branch = Environment.branch
    api.Environment.branches = Environment.branches
    api.Environment.company_branches = Environment.company_branches
    Http.session_info = session_info
