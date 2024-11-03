import json
from odoo import models, fields, api, _


class POSOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def create(self, vals):
        if vals.get('base_sync', False):
            for field_name, value in vals.items():
                field = self._fields[field_name]
                if field.type == 'many2one':
                    if not self.env[field.comodel_name].browse(value).exists():
                        vals[field_name] = False
        return super(POSOrder, self).create(vals)

    base_sync = fields.Boolean()
    base_sync_origin_id = fields.Integer()
    base_sync_payment_data = fields.Text()

    def generate_sequence(self):
        if not self.env.user.has_group('base_synchro.group_pos_double_bookkeeper'):
            return

        Order = self.env['pos.order']
        orders = Order.search([('id', 'in', self.ids)], order=Order._order)[::-1]
        configs = orders.mapped('config_id')

        for config in configs:
            sequence = config.sequence_id

            domain = [
                ('id', 'not in', orders.ids),
                ('config_id', '=', config.id),
                ('base_sync', '=', False)
            ]
            if sequence.company_id:
                domain += [('company_id', '=', sequence.company_id.id)]

            prefix = sequence.prefix
            suffix = sequence.suffix
            
            order_numbers = []
            for order in Order.sudo().search(domain):
                number = order.name
                if prefix and number.startswith(prefix):
                    number = number[len(prefix):]
                if suffix and number.endswith(suffix):
                    number = number[:-len(suffix)]
                try:
                    number = int(number)
                except Exception as err:
                    continue
                order_numbers += [number]
            
            if not order_numbers:
                continue
            
            next_number = max(order_numbers) + 1
            sequence.write({'number_next_actual': next_number})

        orders.write({'name': '/'})
        for order in orders:
            order.write({'name': order.config_id.sequence_id._next()})

    def sync_unlink(self):
        if not self.env.user.has_group('base_synchro.group_pos_double_bookkeeper'):
            return
        orders = self

        for order in orders:
            if order._is_pos_order_paid():
                order.action_pos_order_cancel()
            if order.payment_ids:
                order.payment_ids.unlink()
        
        orders.unlink()

    def sync_confirm(self):
        if not self.env.user.has_group('base_synchro.group_pos_double_bookkeeper'):
            return
        orders = self.filtered(lambda o: o.base_sync)
        for order in orders:
            payment_data = json.loads(order.base_sync_payment_data)
            for payment in payment_data:
                order.add_payment({
                    'pos_order_id': order.id,
                    'amount': order._get_rounded_amount(payment['amount']),
                    'name': payment['name'],
                    'payment_method_id': payment['payment_method_id'],
                })

            if order._is_pos_order_paid():
                order.action_pos_order_paid()
                order._create_order_picking()


class POSOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.model
    def create(self, vals):
        if vals.get('base_sync', False):
            for field_name, value in vals.items():
                field = self._fields[field_name]
                if field.type == 'many2one':
                    if not self.env[field.comodel_name].browse(value).exists():
                        vals[field_name] = False
        return super(POSOrderLine, self).create(vals)

    base_sync = fields.Boolean()
    base_sync_origin_id = fields.Integer()
