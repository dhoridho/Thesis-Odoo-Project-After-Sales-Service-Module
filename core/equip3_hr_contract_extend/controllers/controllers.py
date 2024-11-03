from odoo import http
# from odoo.addons.equip3_hr_recruitment_extend.model.applicant_question import HrApplicant
from odoo.http import request


class ContractExtend(http.Controller):

    @http.route(["/get-expired-contract"], type='http', auth="public", website=True, csrf=False)
    def get_expired_contract(self, **kw):
        action_id = request.env.ref('equip3_hr_contract_extend.contract_expire_action')
        return request.redirect('/web?&#min=1&limit=80&view_type=list&model=hr.contract&action=%s' % (action_id.id))

    @http.route(["/get-renew-contract"], type='http', auth="public", website=True, csrf=False)
    def get_renew_contract(self, **kw):
        action_id = request.env.ref('equip3_hr_contract_extend.contract_renew_action')
        data_id = request.env.ref('equip3_hr_contract_extend.renew_contract_notification')
        return request.redirect('/web?&#view_type=form&model=to.renew.contract&action=%s&id=%s' % (action_id.id,data_id.id))


