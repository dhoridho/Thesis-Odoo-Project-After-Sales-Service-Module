from odoo import models, api


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _get_mail_redirect_suggested_branch(self):
        if 'branch_id' in self:
            return self.branch_id
        return False
        

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _check_access_assignation(self):
        """ Check assigned user (user_id field) has access to the document. Purpose
        is to allow assigned user to handle their activities. For that purpose
        assigned user should be able to at least read the document. We therefore
        raise an UserError if the assigned user has no access to the document. """
        for activity in self:
            model = self.env[activity.res_model].with_user(activity.user_id).with_context(
                allowed_company_ids=activity.user_id.company_ids.ids,
                allowed_branch_ids=activity.user_id.branch_ids.ids,
            )
            try:
                model.check_access_rights('read')
            except exceptions.AccessError:
                raise exceptions.UserError(
                    _('Assigned user %s has no access to the document and is not able to handle this activity.') %
                    activity.user_id.display_name)
            else:
                try:
                    target_user = activity.user_id
                    target_record = self.env[activity.res_model].browse(activity.res_id)
                    if hasattr(target_record, 'company_id') and (
                        target_record.company_id != target_user.company_id and (
                            len(target_user.sudo().company_ids) > 1)):
                        return  # in that case we skip the check, assuming it would fail because of the company
                    model.browse(activity.res_id).check_access_rule('read')
                except exceptions.AccessError:
                    raise exceptions.UserError(
                        _('Assigned user %s has no access to the document and is not able to handle this activity.') %
                        activity.user_id.display_name)


class MailChannel(models.Model):
    _inherit = 'mail.channel'

    def _channel_channel_notifications(self, partner_ids):
        """ Generate the bus notifications of current channel for the given partner ids
            :param partner_ids : the partner to send the current channel header
            :returns list of bus notifications (tuple (bus_channe, message_content))
        """
        notifications = []
        for partner in self.env['res.partner'].browse(partner_ids):
            user_id = partner.user_ids and partner.user_ids[0] or False
            if user_id:
                user_channels = self.with_user(user_id).with_context(
                    allowed_company_ids=user_id.company_ids.ids,
                    allowed_branch_ids=user_id.branch_ids.ids,
                )
                for channel_info in user_channels.channel_info():
                    notifications.append([(self._cr.dbname, 'res.partner', partner.id), channel_info])
        return notifications
