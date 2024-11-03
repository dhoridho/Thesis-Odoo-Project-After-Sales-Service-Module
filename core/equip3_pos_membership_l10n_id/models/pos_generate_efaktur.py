# -*- coding: utf-8 -*-

import copy
import json
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


def get_sum(lines, key, field):
    value = 0
    for l in lines:
        this_key = '%s' % (str(l['partner_id']))
        if this_key == key:
            value += l[field]
    return value

def get_invoices(lines, key, field):
    value = []
    for l in lines:
        this_key = '%s' % (str(l['partner_id']))
        if this_key == key:
            value += [l['account_move_id']]
    return value

class PosGenerateEfaktur(models.Model):
    _inherit = "pos.generate.efaktur"


    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].sudo().get('pos.generate.efaktur')
        GenDigunggung = self.env['pos.generate.efaktur.digunggung']
        GenGabungan = self.env['pos.generate.efaktur.gabungan']
        GenOther = self.env['pos.generate.efaktur.other']
        GenInvoice = self.env['pos.generate.efaktur.invoice']

        result = super(PosGenerateEfaktur, self).create(vals)

        invoices = {} 
        digunggung_ids, nomerge_values = GenDigunggung._create_values(vals, result)
        invoices['digunggung_ids'] = nomerge_values
        
        gabungan_ids, nomerge_values = GenGabungan._create_values(vals, result)
        invoices['gabungan_ids'] = nomerge_values

        other_ids = GenOther._create_values(vals, result)
        invoices['other_ids'] = other_ids

        GenInvoice._create_values(invoices, result)

        return result


    def _get_tax_numbers(self, limit=1,used_numbers=[]):
        query = """
            SELECT t.*
            FROM (

                SELECT 
                ae.id AS efaktur_id,
                ae.name AS nomor_seri, 
                COUNT(am.id) AS used_count
                FROM account_efaktur AS ae
                LEFT JOIN account_move AS am ON am.nomor_seri = ae.id 
                GROUP BY ae.id, ae.name
            ) AS t
            WHERE t.used_count = 0
        """
        if used_numbers:
            query += ' AND t.nomor_seri NOT IN (%s)' % str(used_numbers)[1:-1]

        query += ' ORDER BY t.nomor_seri ASC '
        query += f' LIMIT {limit} '
        self._cr.execute(query)
        results = self._cr.fetchall()

        if not results:
            return []
        return [ { 'id':r[0], 'number':r[1] } for r in results ]

    # OVERRIDE
    def action_generate(self):
        self.ensure_one()

        used_numbers = []
        digunggung_tax_numbers = {}
        gabungan_tax_numbers = {}
        other_tax_numbers = {}

        if self.digunggung_ids:
            numbers = self._get_tax_numbers(limit=1, used_numbers=used_numbers)
            if not numbers:
                raise ValidationError(_('Not enough "Nomor Seri Faktur Pajak")'))
            digunggung_tax_numbers = numbers[0]
            used_numbers += [numbers[0]['number']]

        if self.gabungan_ids:
            member_ids = [m.partner_id.id for m in self.gabungan_ids]

            limit = member_ids and len(member_ids) or 1
            numbers = self._get_tax_numbers(limit=limit, used_numbers=used_numbers)

            if len(numbers) < len(self.gabungan_ids):
                message = '\nMembers: ' + str(len(member_ids))
                message += '\nE-Faktur Number: ' + str(len(numbers))
                raise ValidationError(_('Not enough "Nomor Seri Faktur Pajak")\n' + message))

            used_numbers += [n['number'] for n in numbers]
            gabungan_tax_numbers = {k: v for k, v in zip(member_ids, [ [n['id'], n['number']] for n in numbers])}


        if self.other_ids:
            invoice_ids = [i.account_move_id.id for i in self.other_ids]

            limit = invoice_ids and len(invoice_ids) or 1
            numbers = self._get_tax_numbers(limit=limit, used_numbers=used_numbers)

            if len(numbers) < len(invoice_ids):
                message = '\nMembers: ' + str(len(invoice_ids))
                message += '\nE-Faktur Number: ' + str(len(numbers))
                raise ValidationError(_('Not enough "Nomor Seri Faktur Pajak")\n' + message))

            other_tax_numbers = {k: v for k, v in zip(invoice_ids, [ [n['id'], n['number']] for n in numbers])}

        #create
        if self.digunggung_ids:
            for rec in self.digunggung_ids:
                number = digunggung_tax_numbers
                l10n_id_tax_number = '010' + number['number']
                rec.write({ 'l10n_id_tax_number': l10n_id_tax_number, })

                account_moves = self.env['account.move'].search([('id','in', json.loads(rec.account_move_data))])
                account_moves.write({
                        'l10n_id_kode_transaksi': '01',
                        'status_code': '0',
                        'nomor_seri': number['id'],
                        'l10n_id_tax_number': l10n_id_tax_number,
                    })

        if self.gabungan_ids:
            for rec in self.gabungan_ids:
                number = gabungan_tax_numbers[rec.partner_id.id]
                l10n_id_tax_number = '010' + number[1]
                rec.write({ 'l10n_id_tax_number': l10n_id_tax_number, })

                account_moves = self.env['account.move'].search([('id','in', json.loads(rec.account_move_data))])
                account_moves.write({
                        'l10n_id_kode_transaksi': '01',
                        'status_code': '0',
                        'nomor_seri': number[0],
                        'l10n_id_tax_number': l10n_id_tax_number,
                    })

        if self.other_ids:
            for rec in self.other_ids:
                number = other_tax_numbers[rec.account_move_id.id]
                l10n_id_tax_number = '010' + number[1]
                rec.write({ 'l10n_id_tax_number': l10n_id_tax_number, })
                rec.account_move_id.write({
                    'l10n_id_kode_transaksi': '01',
                    'status_code': '0',
                    'nomor_seri': number[0],
                    'l10n_id_tax_number': l10n_id_tax_number,
                })
        self.write({ 'state': 'done' })
        return True


class PosGenerateEfakturInvoice(models.Model):
    _inherit = "pos.generate.efaktur.invoice"

    l10n_id_tax_number = fields.Char('Nomor Seri Faktur Pajak', compute='_compute_l10n_id_tax_number', store=False)

    def _compute_l10n_id_tax_number(self):
        for rec in self:
            rec.l10n_id_tax_number = rec.account_move_id.l10n_id_tax_number

    def _create_values(self, vals, gen_efaktur_id):

        values = []
        if vals.get('digunggung_ids'):
            for val in vals['digunggung_ids']:
                values += [{
                    'partner_id': val['partner_id'],
                    'account_move_id': val['account_move_id'],
                    'gen_efaktur_id': gen_efaktur_id.id
                }]
        
        if vals.get('gabungan_ids'):
            for val in vals['gabungan_ids']:
                values += [{
                    'partner_id': val['partner_id'],
                    'account_move_id': val['account_move_id'],
                    'gen_efaktur_id': gen_efaktur_id.id
                }]

        if vals.get('other_ids'):
            for val in vals['other_ids']:
                values += [{
                    'partner_id': val['partner_id'],
                    'account_move_id': val['account_move_id'],
                    'gen_efaktur_id': gen_efaktur_id.id
                }]

        for value in values:
            self.env[self._name].create(value)

        return values


class PosGenerateEfakturDigunggung(models.Model):
    _inherit = "pos.generate.efaktur.digunggung"

    l10n_id_tax_number = fields.Char('Nomor Seri Faktur Pajak')

    def _create_values(self, vals, gen_efaktur_id):
        domain = [
            ('l10n_id_tax_number', '=', False), 
            ('is_from_pos_umum', '=', True), 
            ('invoice_date', '>=', vals['start_date']), 
            ('invoice_date', '<=', vals['end_date']), 

        ]
        account_moves = self.env['account.move'].search(domain)
        values = []
        for move in account_moves:
            amount_total = sum([ x.price_total for x in move.line_ids if x.price_total > 0])
            values += [{
                'partner_id': move.partner_id.id,
                'account_move_id': move.id,
                'gen_efaktur_id': gen_efaktur_id.id,
                'amount_total': amount_total,
            }]

        # merge Invoice
        _values = defaultdict(dict)
        for value in values:
            l = copy.deepcopy(value)
            key = '%s' % (str(l['partner_id']))
            l['amount_total'] = get_sum(values, key, 'amount_total')
            l['account_move_data'] = json.dumps(get_invoices(values, key, 'account_move_id'))
            _values[key].update(l)
        nomerge_values = values
        values = list(_values.values())

        for value in values:
            self.env[self._name].create(value)

        return values, nomerge_values

class PosGenerateEfakturGabungan(models.Model):
    _inherit = "pos.generate.efaktur.gabungan" 

    l10n_id_tax_number = fields.Char('Nomor Seri Faktur Pajak')

    def _create_values(self, vals, gen_efaktur_id):
        domain = [
            ('l10n_id_tax_number', '=', False), 
            ('is_from_pos_member_gabungan', '=', True), 
            ('invoice_date', '>=', vals['start_date']), 
            ('invoice_date', '<=', vals['end_date']), 

        ]
        account_moves = self.env['account.move'].search(domain)
        values = []
        for move in account_moves:
            amount_total = sum([ x.price_total for x in move.line_ids if x.price_total > 0])
            values += [{
                'partner_id': move.partner_id.id,
                'account_move_id': move.id,
                'gen_efaktur_id': gen_efaktur_id.id,
                'amount_total': amount_total,
            }]


        # merge Invoice
        _values = defaultdict(dict)
        for value in values:
            l = copy.deepcopy(value)
            key = '%s' % (str(l['partner_id']))
            l['amount_total'] = get_sum(values, key, 'amount_total')
            l['account_move_data'] = json.dumps(get_invoices(values, key, 'account_move_id'))
            _values[key].update(l)
        nomerge_values = values
        values = list(_values.values())

        for value in values:
            self.env[self._name].create(value)

        return values, nomerge_values

class PosGenerateEfakturOther(models.Model):
    _inherit = "pos.generate.efaktur.other" 

    l10n_id_tax_number = fields.Char('Nomor Seri Faktur Pajak')
    
    def _create_values(self, vals, gen_efaktur_id):
        domain = [
            ('l10n_id_tax_number', '=', False), 
            ('is_from_pos_member', '=', True), 
            ('invoice_date', '>=', vals['start_date']), 
            ('invoice_date', '<=', vals['end_date']), 
        ]
        account_moves = self.env['account.move'].search(domain)
        values = []
        for move in account_moves:
            values += [{
                'partner_id': move.partner_id.id,
                'account_move_id': move.id,
                'gen_efaktur_id': gen_efaktur_id.id
            }]

        for value in values:
            self.env[self._name].create(value)

        return values