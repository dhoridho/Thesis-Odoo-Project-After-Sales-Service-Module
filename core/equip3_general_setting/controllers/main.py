import werkzeug.utils
from werkzeug.urls import url_encode
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.addons.mail.controllers.main import MailController


class MailControllerOverrided(MailController):
    @classmethod
    def _redirect_to_record(cls, model, res_id, access_token=None, **kwargs):
        # access_token and kwargs are used in the portal controller override for the Send by email or Share Link
        # to give access to the record to a recipient that has normally no access.
        uid = request.session.uid
        user = request.env['res.users'].sudo().browse(uid)
        cids = False
        bids = False

        # no model / res_id, meaning no possible record -> redirect to login
        if not model or not res_id or model not in request.env:
            return cls._redirect_to_messaging()

        # find the access action using sudo to have the details about the access link
        RecordModel = request.env[model]
        record_sudo = RecordModel.sudo().browse(res_id).exists()
        if not record_sudo:
            # record does not seem to exist -> redirect to login
            return cls._redirect_to_messaging()

        # the record has a window redirection: check access rights
        if uid is not None:
            if not RecordModel.with_user(uid).check_access_rights('read', raise_exception=False):
                return cls._redirect_to_messaging()
            try:
                # We need here to extend the "allowed_company_ids" to allow a redirection
                # to any record that the user can access, regardless of currently visible
                # records based on the "currently allowed companies".
                cids = request.httprequest.cookies.get('cids', str(user.company_id.id))
                cids = [int(cid) for cid in cids.split(',')]
                bids = request.httprequest.cookies.get('bids', str(user.branch_id.id))
                bids = [int(bid) for bid in bids.split(',')]
                try:
                    record_sudo.with_user(uid).with_context(allowed_company_ids=cids, allowed_branch_ids=bids).check_access_rule('read')
                except AccessError:
                    # In case the allowed_company_ids from the cookies (i.e. the last user configuration
                    # on his browser) is not sufficient to avoid an ir.rule access error, try to following
                    # heuristic:
                    # - Guess the supposed necessary company to access the record via the method
                    #   _get_mail_redirect_suggested_company
                    #   - If no company, then redirect to the messaging
                    #   - Merge the suggested company with the companies on the cookie
                    # - Make a new access test if it succeeds, redirect to the record. Otherwise, 
                    #   redirect to the messaging.
                    suggested_company = record_sudo._get_mail_redirect_suggested_company()
                    suggested_branch = record_sudo._get_mail_redirect_suggested_branch()
                    if not suggested_company or not suggested_branch:
                        raise AccessError('')
                    cids = cids + [suggested_company.id]
                    bids = bids + [suggested_branch.id]
                    record_sudo.with_user(uid).with_context(allowed_company_ids=cids, allowed_branch_ids=bids).check_access_rule('read')
            except AccessError:
                return cls._redirect_to_messaging()
            else:
                record_action = record_sudo.get_access_action(access_uid=uid)
        else:
            record_action = record_sudo.get_access_action()
            if record_action['type'] == 'ir.actions.act_url' and record_action.get('target_type') != 'public':
                return cls._redirect_to_messaging()

        record_action.pop('target_type', None)
        # the record has an URL redirection: use it directly
        if record_action['type'] == 'ir.actions.act_url':
            return werkzeug.utils.redirect(record_action['url'])
        # other choice: act_window (no support of anything else currently)
        elif not record_action['type'] == 'ir.actions.act_window':
            return cls._redirect_to_messaging()

        url_params = {
            'model': model,
            'id': res_id,
            'active_id': res_id,
            'action': record_action.get('id'),
        }
        view_id = record_sudo.get_formview_id()
        if view_id:
            url_params['view_id'] = view_id

        if cids:
            url_params['cids'] = ','.join([str(cid) for cid in cids])
        if bids:
            url_params['bids'] = ','.join([str(bid) for bid in bids])
        url = '/web?#%s' % url_encode(url_params)
        return werkzeug.utils.redirect(url)