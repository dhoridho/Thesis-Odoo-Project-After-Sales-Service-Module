# -*- coding: utf-8 -*-

import logging
import copy
from collections import defaultdict
from passlib.context import CryptContext
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _, registry
from odoo.exceptions import UserError, ValidationError
from odoo import SUPERUSER_ID
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = "pos.session"

    scheduler_invoice_finish_date = fields.Datetime('Scheduler Invoice Finish Date', 
        help='''
        Scheduler finish date for Invoices:
        - POS Invoice Digunggung
        - POS Invoice Member
        - POS Partner Invoice 
        ''')

    def _get_invoice_lines_values(self, orders):
        product_obj = self.env['product.product']
        pos_line_obj = self.env['pos.order.line']
        lines = []
        lines_mapped = orders.mapped('lines')
        if lines_mapped:
            lines_ids = lines_mapped.ids
            tax_mapped = lines_mapped.mapped('tax_ids_after_fiscal_position')
            if tax_mapped:
                tax_ids = tax_mapped.ids
            query = '''
                SELECT pol.product_id, pol.product_uom_id,sum(pol.qty),pol.price_unit,sum(pol.discount_amount_percent),array_agg(pol.id)
                FROM pos_order_line AS pol
                WHERE pol.id IN %s and pol.product_id is not null
                GROUP BY pol.product_id, pol.product_uom_id, pol.price_unit
            ''' % (tuple(lines_ids) + tuple([0]),)
            self.env.cr.execute(query)        
            results = self.env.cr.fetchall()
            for r in results:
                tax_ids = False
                product = product_obj.browse(r[0])
                pos_line = pos_line_obj.search([('id','in',r[5])])
                tax_mapped = pos_line.mapped('tax_ids_after_fiscal_position')
                if tax_mapped:
                    tax_ids = tax_mapped.ids
                    tax_ids = [(6, 0, tax_ids)]
                account_id = product.categ_id.property_account_income_categ_id.id
                subtotal_without_tax = sum(pos_line.mapped('price_subtotal'))
                subtotal_with_tax = sum(pos_line.mapped('price_subtotal_incl'))

                lines.append((0,0,{
                    'product_id':r[0],
                    'name':product.name,
                    'quantity':r[2],
                    'product_uom_id':r[1],
                    'tax_ids':tax_ids,
                    'price_unit':r[3],
                    'discount_amount':r[4],
                    'price_subtotal':subtotal_without_tax,
                    'price_total':subtotal_with_tax,
                    'account_id':account_id,
                }))

        return lines

    def _prepare_invoice_for_pos_umum(self, cron=False):
        """
        TODO: Invoice for Non member and member without ID PKP & NPWP (pos_umum) 
            - Create and combine orders to only one invoice
            (module: equip3_pos_membership_l10n_id)
        """
        self.ensure_one()
        return []

    def _prepare_invoice_for_pos_member(self, cron=False):
        """
        TODO: Invoice for Member with ID PKP, NPWP & Faktur Pajak Gabungan = False (pos_member)
            - Every member has own invoice
            - If member have 5 orders then create 5 invoices to
                (module: equip3_pos_membership_l10n_id)
        """
        self.ensure_one()
        return []

    def _prepare_invoice_for_pos_member_gabungan(self, cron=False):
        """
        TODO: Invoice for Member with ID PKP, NPWP & Faktur Pajak Gabungan = True (pos_gabungan)
            - Every member has own invoice
            - If member have 5 orders then combine to one invoice
                (module: equip3_pos_membership_l10n_id)
        """
        self.ensure_one()
        return []

    # def action_pos_session_closing_control(self):
    #     """
    #     Create 3 type of invoice:
    #     1. Invoice for Non member and member without ID PKP & NPWP (pos_umum)
    #         - Create and combine orders to only one invoice
    #     2. Invoice for Member with ID PKP, NPWP & Faktur Pajak Gabungan = False (pos_member)
    #         - Every member has own invoice
    #         - If member have 5 orders then create 5 invoices to
    #     3. Invoice for Member with ID PKP, NPWP & Faktur Pajak Gabungan = True (pos_gabungan)
    #         - Every member has own invoice
    #         - If member have 5 orders then combine to one invoice
    #     """
    #     for session in self:
    #         values = []
    #         values += session._prepare_invoice_for_pos_umum()
    #         values += session._prepare_invoice_for_pos_member()
    #         values += session._prepare_invoice_for_pos_member_gabungan()
    #         for value in values:
    #             account_move = self.env['account.move'].sudo().create(value)
    #     return super(PosSession, self).action_pos_session_closing_control()

    def _get_session_ids_not_pos_invoices(self, limit=10):
        # Condition:
        # - Session with status Closes & Posted
        # - POS Invoice Digunggung not created
        # - POS Invoice Member not created
        # - POS Partner Invoice not created

        query = '''
            SELECT 
                t.id, t.state, t.scheduler_date, t.pos_umum, t.pos_member, t.pos_member_gabungan
            FROM (
                SELECT 
                    ps.id, 
                    ps.state, 
                    ps.scheduler_invoice_finish_date AS scheduler_date,
                    COALESCE(MIN(am_pu.id)) AS pos_umum,
                    COALESCE(MIN(am_pm.id)) AS pos_member,
                    COALESCE(MIN(am_pmg.id)) AS pos_member_gabungan
                FROM pos_session AS ps
                LEFT JOIN account_move AS am_pu ON am_pu.pos_session_id = ps.id AND am_pu.is_from_pos_umum = 't'
                LEFT JOIN account_move AS am_pm ON am_pm.pos_session_id = ps.id AND am_pm.is_from_pos_member = 't'
                LEFT JOIN account_move AS am_pmg ON am_pmg.pos_session_id = ps.id AND am_pmg.is_from_pos_member_gabungan = 't'
                WHERE ps.state = 'closed'
                    AND ps.scheduler_invoice_finish_date IS NULL 
                    AND ps.cash_real_transaction > 0 -- skip if no orders
                GROUP BY 
                    ps.id, 
                    ps.state, 
                    ps.scheduler_invoice_finish_date
            ) AS t
            WHERE t.pos_umum IS NULL
                AND t.pos_member IS NULL
                AND t.pos_member_gabungan IS NULL
            ORDER BY t.id DESC
            LIMIT {limit}
        '''.format(limit=limit)
        self.env.cr.execute(query)        
        results = self.env.cr.fetchall()
        return [x[0] for x in results]

    def create_pos_invoices_cron(self):
        """
        Create 3 type of invoice:
        1. Invoice for Non member and member without ID PKP & NPWP (pos_umum)
            - Create and combine orders to only one invoice
        2. Invoice for Member with ID PKP, NPWP & Faktur Pajak Gabungan = False (pos_member)
            - Every member has own invoice
            - If member have 5 orders then create 5 invoices to
        3. Invoice for Member with ID PKP, NPWP & Faktur Pajak Gabungan = True (pos_gabungan)
            - Every member has own invoice
            - If member have 5 orders then combine to one invoice
        """
        limit = 10

        # Check time in Jakarta Time (GMT+7)
        time_now = datetime.now() + relativedelta(hours=7) # From UTC to (GMT+7)
        start_time = datetime.strptime(time_now.strftime('%Y-%m-%d') + ' 19:00:00', '%Y-%m-%d %H:%M:%S') # 19:00 WIB (GMT+7)
        end_time   = datetime.strptime(time_now.strftime('%Y-%m-%d') + ' 06:00:00', '%Y-%m-%d %H:%M:%S') + relativedelta(days=1) # 06:00 WIB (GMT+7)
        is_allow_create_invoice = start_time <= time_now <= end_time

        if is_allow_create_invoice:
            session_ids = self._get_session_ids_not_pos_invoices(limit)
            sessions = self.env['pos.session'].sudo().search([('id','in', session_ids)], limit=limit)
            _logger.info('Start - Create POS Invoices: ' + str(session_ids))

            for session in sessions:
                if session.scheduler_invoice_finish_date:
                    _logger.info('Failed - Create POS Invoices session: ' + str(session.name) + ' already Done')
                    continue

                values = []
                values += session._prepare_invoice_for_pos_umum(cron=True)
                values += session._prepare_invoice_for_pos_member(cron=True)
                values += session._prepare_invoice_for_pos_member_gabungan(cron=True)
                for value in values:
                    account_move = self.env['account.move'].sudo().create(value)

                session.write({ 'scheduler_invoice_finish_date': fields.Datetime.now() })
            _logger.info('Done - Create POS Invoices: ' + str(session_ids))

    def _prepare_invoice_vals_from_payment(self, data, payment, pos_session):
        vals = super(PosSession, self)._prepare_invoice_vals_from_payment(data, payment, pos_session)
        if payment.is_bank and payment.generate_invoice:
            vals['is_from_pos_partner'] = True
        return vals