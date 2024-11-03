from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class QualityAlertInherit(models.Model):
    _inherit = 'sh.quality.alert'

    @api.model
    def create(self, vals):
        active_id = self.env.context.get('active_id', False)
        picking = self.env['stock.picking'].search([('id', '=', active_id)], limit=1)
        if picking:
            seq = self.env['ir.sequence'].next_by_code('qc.alert.newseq')
            wh_code = picking.picking_type_id.warehouse_id.code
            wh_type = picking.picking_type_id.sequence_code
            name = 'QA/' + wh_code + '/' + wh_type + '/' + (seq)
            vals['name'] = name

        return super(QualityAlertInherit, self).create(vals)

    def create_qc_alert(self):
        active_id = self.env.context.get('active_id', False)
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
            action_id = self.env.ref('stock.action_picking_tree_all').id
            url = base_url + '/web#id=' + str(record.piking_id.id) + '&action=' + str(
                action_id) + '&view_type=form&model=stock.picking'
            template_id = self.env.ref(
                'equip3_inventory_qc.email_template_quality_alert')

            try:
                email_to = ', '.join(record.team_id.user_ids.mapped('email'))
                user_name = ', '.join(record.team_id.user_ids.mapped('name'))
                checked = record.piking_id.sh_quality_check_ids.mapped(
                    'checked_qty')
                checked_qty = checked if checked else record.product_id.sample_qc

            except Exception as e:
                users_email = record.team_id.user_ids.filtered(
                    lambda x: x.partner_id.email == False)
                if users_email:
                    raise ValidationError(_("Please set email for users: %s in %s. For more further please contact administrator") % (
                        ', '.join(users_email.partner_id.mapped('name')), record.team_id.name))

            ctx = {
                'email_from': self.env.user.company_id.email,
                'email_to': email_to,
                'user_name': user_name,
                'checked_qty': checked_qty,
                'url': url,
            }

            template_id.with_context(ctx).send_mail(record.id, True)
            template_id = self.env["ir.model.data"].xmlid_to_object(
                "equip3_inventory_qc.email_template_quality_alert"
            )
            body_html = self.env['mail.render.mixin'].with_context(ctx)._render_template(
                template_id.body_html, 'sh.quality.alert', record.ids, post_process=True)[record.id]

            notification_ids = []
            for user in record.team_id.user_ids:
                notification_ids.append([0, 0, {'res_partner_id': user.partner_id.id,
                                                'notification_type': 'inbox',
                                                "notification_status": "sent",
                                                }])

            vals = {
                "subject": "Quality Alert",
                "body": body_html,
                "model": "sh.quality.alert",
                "res_id": record.id,
                "message_type": "notification",
                "partner_ids": [(6, 0, record.team_id.user_ids.partner_id.ids,)],
                "notification_ids": notification_ids
            }
            self.env["mail.message"].sudo().create(vals)
