from odoo import _, api, fields, models
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    @api.constrains('name', 'product_id', 'company_id')
    def _check_unique_lot(self):
        domain = [('product_id', 'in', self.product_id.ids),
                  ('company_id', 'in', self.company_id.ids),
                  ('name', 'in', self.mapped('name'))]
        fields = ['company_id', 'product_id', 'name']
        groupby = ['company_id', 'product_id', 'name']
        records = self.read_group(domain, fields, groupby, lazy=False)
        error_message_lines = []
        for rec in records:
            if rec['__count'] != 1:
                product_name = self.env['product.product'].browse(
                    rec['product_id'][0]).display_name
                error_message_lines.append(
                    _(" - Product: %s, Serial Number: %s", product_name, rec['name']))

        context = dict(self.env.context or {})
        do_return = False
        # fix lot/sn contrains for return DO picking
        if context.get('button_validate_picking_ids'):
            pickings = self.env['stock.picking'].browse(
                context.get('button_validate_picking_ids'))
            if pickings:                
                for picking in pickings:
                    if picking.picking_type_code == 'incoming' and picking.origin and 'Return' in picking.origin:
                        do_return = True
        production_lot_ids = self.search(domain)
        move_line_ids = self.env['stock.move.line'].search(
            [('lot_name', 'in', production_lot_ids.mapped('name'))])
        packages_data = {}
        for move_line in move_line_ids:
            if move_line.result_package_id and move_line.lot_name and move_line.lot_name in packages_data.keys():
                packages_data[move_line.lot_name] += 1
            elif move_line.result_package_id and move_line.lot_name and move_line.lot_name not in packages_data.keys():
                packages_data[move_line.lot_name] = 1
        if packages_data and any(line > 1 for line in packages_data.values()):
            pass
        else:
            if error_message_lines and not do_return:
                raise ValidationError(
                    _('The combination of serial number and product must be unique across a company.\nFollowing combination contains duplicates:\n') + '\n'.join(error_message_lines))

    @api.model
    def _alert_date_exceeded(self):
        """overriding and disabling the original function"""

    @api.model
    def _expire_date_cron(self):
        lot_ids = self.search([("expiration_date", ">", datetime.now().replace(
            hour=0, minute=0, second=0)), ("expiration_date", "<=", datetime.now().replace(hour=23, minute=59, second=59))])
        expire_lot_quant_ids = lot_ids.quant_ids.filtered(
            lambda l: l.location_id.usage == "internal" and l.location_id.get_warehouse().responsible_users)
        warehouse_wise_expired_quant = {}
        for quant in expire_lot_quant_ids:
            quant_warehouse = quant.location_id.get_warehouse()
            if quant_warehouse not in warehouse_wise_expired_quant:
                warehouse_wise_expired_quant[quant_warehouse] = quant
            else:
                warehouse_wise_expired_quant[quant_warehouse] = warehouse_wise_expired_quant[quant_warehouse] | quant

        mail_template_name = "equip3_inventory_tracking.email_template_expired_stock_production_lot"
        mail_subject = "Expired Products Today"
        for rec in warehouse_wise_expired_quant:
            self.send_email_notification(
                rec.responsible_users, rec, warehouse_wise_expired_quant[rec], mail_template_name, mail_subject)

    @api.model
    def _expire_alert_date_cron(self):
        lot_ids = self.search([("alert_date", ">", datetime.now().replace(
            hour=0, minute=0, second=0)), ("alert_date", "<=", datetime.now().replace(hour=23, minute=59, second=59))])
        expire_lot_quant_ids = lot_ids.quant_ids.filtered(
            lambda l: l.location_id.usage == "internal" and l.location_id.get_warehouse().responsible_users)
        warehouse_wise_expire_quant = {}
        for quant in expire_lot_quant_ids:
            quant_warehouse = quant.location_id.get_warehouse()
            if quant_warehouse not in warehouse_wise_expire_quant:
                warehouse_wise_expire_quant[quant_warehouse] = quant
            else:
                warehouse_wise_expire_quant[quant_warehouse] = warehouse_wise_expire_quant[quant_warehouse] | quant

        mail_template_name = "equip3_inventory_tracking.email_template_expired_alert_stock_production_lot"
        mail_subject = "Alert On Products That Are Going To Be Expire Soon"
        for rec in warehouse_wise_expire_quant:
            self.send_email_notification(
                rec.responsible_users, rec, warehouse_wise_expire_quant[rec], mail_template_name, mail_subject)

    def send_email_notification(self, responsible_users, warehouse, quant, mail_template_name, mail_subject):
        ctx = {
            "email_from": self.env.user.company_id.email,
            "quant": quant
        }
        template_id = self.env.ref(mail_template_name)

        for user in responsible_users:
            ctx.update({
                "email_to": user.email,
                "responsible_users": user.name,
            })

            template_id.with_context(ctx).send_mail(warehouse.id, True)
            body_html = self.env['mail.render.mixin'].with_context(ctx)._render_template(
                template_id.body_html, 'stock.production.lot', warehouse.ids, post_process=True)[warehouse.id]
            message_id = (
                self.env["mail.message"]
                    .sudo()
                    .create(
                    {
                        "subject": mail_subject,
                        "body": body_html,
                        "message_type": "notification",
                        "partner_ids": [
                            (
                                6,
                                0,
                                user.partner_id.ids,
                            )
                        ],
                    }
                )
            )
            notif_create_values = {
                "mail_message_id": message_id.id,
                "res_partner_id": user.partner_id.id,
                "notification_type": "inbox",
                "notification_status": "sent",
            }
            self.env["mail.notification"].sudo().create(notif_create_values)

    def get_lot_url(self):
        base_url = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        action_id = self.env.ref('stock.action_production_lot_form')
        return base_url + '/web#id=' + str(self.id) + '&action=' + str(action_id.id) + '&view_type=form&model=stock.production.lot'

    def _get_dates(self, product_id=None):
        res = super(StockProductionLot, self)._get_dates(product_id=product_id)

        if res['expiration_date']:
            product_tmpl_id = self.env['product.product'].browse(
                product_id).product_tmpl_id
            now = fields.datetime.now()
            if product_tmpl_id.expiration_time > 0:
                res['expiration_date'] = fields.datetime.now(
                ) + timedelta(product_tmpl_id.expiration_time)
            else:
                res['expiration_date'] = now
            if product_tmpl_id.alert_time > 0:
                res['alert_date'] = fields.datetime.now(
                ) + timedelta(product_tmpl_id.alert_time)
            else:
                res['alert_date'] = now

            if product_tmpl_id.removal_time > 0:
                res['removal_date'] = res['expiration_date'] + \
                    timedelta(product_tmpl_id.removal_time)
            else:
                res['removal_date'] = now

            if product_tmpl_id.use_time > 0:
                res['use_date'] = res['expiration_date'] - \
                    timedelta(product_tmpl_id.use_time)
            else:
                res['use_date'] = now
        return res
