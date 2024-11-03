from odoo import models, fields, api, _


class POSSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def create(self, vals):
        if vals.get('base_sync', False):
            for field_name, value in vals.items():
                field = self._fields[field_name]
                if field.type == 'many2one':
                    if not self.env[field.comodel_name].browse(value).exists():
                        vals[field_name] = False
        return super(POSSession, self).create(vals)

    base_sync = fields.Boolean()
    base_sync_origin_id = fields.Integer()

    def generate_sequence(self):
        if not self.env.user.has_group('base_synchro.group_pos_double_bookkeeper'):
            return

        Session = self.env['pos.session']
        sessions = Session.search([('id', 'in', self.ids)], order=Session._order)[::-1]
        configs = sessions.mapped('config_id')

        for config in configs:
            sequences = self.env['ir.sequence'].search([('code', '=', 'pos.session'), ('company_id', 'in', [config.company_id.id, False])], order='company_id')
            
            for sequence in sequences:
                domain = [
                    ('id', 'not in', sessions.ids),
                    ('config_id', '=', config.id),
                    ('base_sync', '=', False)
                ]
                if sequence.company_id:
                    domain += [('company_id', '=', sequence.company_id.id)]

                prefix = sequence.prefix
                suffix = sequence.suffix
                
                session_numbers = []
                for session in Session.sudo().search(domain):
                    number = session.name
                    if prefix and number.startswith(prefix):
                        number = number[len(prefix):]
                    if suffix and number.endswith(suffix):
                        number = number[:-len(suffix)]
                    try:
                        number = int(number)
                    except Exception as err:
                        continue
                    session_numbers += [number]
                
                if not session_numbers:
                    continue
                
                next_number = max(session_numbers) + 1
                sequence.write({'number_next_actual': next_number})

        sessions.write({'name': '/'})
        for session in sessions:
            pos_config = session.config_id
            ctx = dict(self.env.context, company_id=pos_config.company_id.id)
            session.write({'name': self.env['ir.sequence'].with_context(ctx).next_by_code('pos.session')})

    def sync_unlink(self):
        if not self.env.user.has_group('base_synchro.group_pos_double_bookkeeper'):
            return
        sessions = self

        orders = sessions.mapped('order_ids')
        statements = sessions.mapped('statement_ids')
        
        if orders:
            orders.sync_unlink()

        if statements:
            statements.pos_session_id = False
        
        sessions.unlink()
        
        statements.unlink()
