# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _, registry
from odoo.exceptions import UserError, ValidationError

class PosSession(models.Model):
    _inherit = "pos.session" 
 

    # OVERRIDE
    def _prepare_invoice_for_pos_umum(self, cron=False):
        values = []
        domain = [
            ('state', 'in', ['paid','done']), 
            ('session_id', '=', self.id),
            ('return_order_id', '=', False) # If return of order is filled then skip the code below (to create account move)
        ]
        domain += ['|', '|', ('partner_id','=',False), ('partner_id.l10n_id_pkp','=',False), 
                    ('partner_id.vat','=',False)]
        orders = self.env['pos.order'].search(domain)
        if not orders:
            return []
            
        default_journal_id = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        default_partner_id = self.env['ir.config_parameter'].sudo().get_param('pkp_customer_id')
        if not default_partner_id:
            raise UserError('Please update default pkp customer in pos settings.')
        partner = self.env['res.partner'].browse(int(default_partner_id))

        invoice_line_ids = self._get_invoice_lines_values(orders)

        value = {
            'partner_id': partner.id,
            'date': fields.Date.context_today(self),
            'is_pkp_record': True,
            'invoice_date': fields.Date.context_today(self),
            'ref': self.name,
            'origin': self.name,
            'move_type': 'out_invoice',
            'pos_session_id': self.id,
            'currency_id': self.env.user.company_id.currency_id.id,
            'company_id': self.env.user.company_id.id,
            'journal_id': default_journal_id and default_journal_id.id,
            'invoice_line_ids': invoice_line_ids,
            'branch_id': self.pos_branch_id.id,
            'pos_branch_id': self.pos_branch_id.id,
            'is_from_pos_umum': True,
            # 'user_id': self.env.user.id,
        }
        if cron:
            value['date'] = self.stop_at
            value['invoice_date'] = self.stop_at
        return [value]

    # OVERRIDE
    def _prepare_invoice_for_pos_member(self, cron=False):
        self.ensure_one()
        session = self
        values = []
        query = '''
            SELECT po.partner_id, array_agg(po.id)
            FROM pos_order AS po
            INNER JOIN res_partner AS rp ON rp.id = po.partner_id
            LEFT JOIN pos_payment AS pp ON pp.pos_order_id = po.id
            LEFT JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
            WHERE rp.l10n_id_pkp = 't' 
                AND rp.vat IS NOT NULL 
                AND (rp.faktur_pajak_gabungan = 'f' OR rp.faktur_pajak_gabungan IS NULL)
                AND po.state IN ('paid','done')
                AND po.return_order_id IS NULL 
                AND po.session_id = {session_id}
            GROUP BY po.partner_id
        '''.format(session_id=session.id)
        self._cr.execute(query)
        results = dict(self._cr.fetchall())
        if not results:
            return []

        default_journal_id = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        default_partner_id = self.env['ir.config_parameter'].sudo().get_param('pkp_customer_id')
        if not default_partner_id:
            raise UserError('Please update default pkp customer in pos settings.')
        default_partner = self.env['res.partner'].browse(int(default_partner_id))

        for partner_id in results:
            partner = self.env['res.partner'].browse(int(partner_id))
            order_ids = results[partner_id]

            orders = self.env['pos.order'].search([('id','in',order_ids)])
            for pos_order in orders:
                invoice_line_ids = self._get_invoice_lines_values(pos_order)

                value = {
                    'partner_id': partner.id,
                    'date': fields.Date.context_today(self),
                    'is_pkp_record': True,
                    'invoice_date': fields.Date.context_today(self),
                    'ref': self.name,
                    'origin': self.name,
                    'move_type': 'out_invoice',
                    'pos_session_id': self.id,
                    'currency_id': self.env.user.company_id.currency_id.id,
                    'company_id': self.env.user.company_id.id,
                    'journal_id': default_journal_id and default_journal_id.id,
                    'invoice_line_ids': invoice_line_ids,
                    'branch_id': session.pos_branch_id.id,
                    'pos_branch_id': session.pos_branch_id.id,
                    'is_from_pos_member': True
                }
                if cron:
                    value['date'] = self.stop_at
                    value['invoice_date'] = self.stop_at

                values += [value]

        return values

    # OVERRIDE
    def _prepare_invoice_for_pos_member_gabungan(self, cron=False):
        self.ensure_one()
        session = self
        values = []
        query = '''
            SELECT po.partner_id, array_agg(po.id)
            FROM pos_order AS po
            INNER JOIN res_partner AS rp ON rp.id = po.partner_id
            LEFT JOIN pos_payment AS pp ON pp.pos_order_id = po.id
            LEFT JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
            WHERE rp.l10n_id_pkp = 't' AND rp.vat IS NOT NULL AND rp.faktur_pajak_gabungan = 't'
                AND po.state IN ('paid','done')
                AND po.return_order_id IS NULL 
                AND po.session_id = {session_id}
            GROUP BY po.partner_id
        '''.format(session_id=session.id)
        self._cr.execute(query)
        results = dict(self._cr.fetchall())
        if not results:
            return []

        default_journal_id = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        default_partner_id = self.env['ir.config_parameter'].sudo().get_param('pkp_customer_id')
        if not default_partner_id:
            raise UserError('Please update default pkp customer in pos settings.')
        default_partner = self.env['res.partner'].browse(int(default_partner_id))

        for partner_id in results:
            partner = self.env['res.partner'].browse(int(partner_id))
            order_ids = results[partner_id]
            orders = self.env['pos.order'].search([('id','in',order_ids)])

            invoice_line_ids = self._get_invoice_lines_values(orders)

            value = {
                'partner_id': partner.id,
                'date': fields.Date.context_today(self),
                'is_pkp_record': True,
                'invoice_date': fields.Date.context_today(self),
                'ref': self.name,
                'origin': self.name,
                'move_type': 'out_invoice',
                'pos_session_id': self.id,
                'currency_id': self.env.user.company_id.currency_id.id,
                'company_id': self.env.user.company_id.id,
                'journal_id': default_journal_id and default_journal_id.id,
                'invoice_line_ids': invoice_line_ids,
                'branch_id': session.pos_branch_id.id,
                'pos_branch_id': session.pos_branch_id.id,
                'is_from_pos_member_gabungan': True
            }
            if cron:
                value['date'] = self.stop_at
                value['invoice_date'] = self.stop_at
                
            values += [value]

        return values