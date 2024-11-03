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
    _name = "pos.generate.efaktur"
    _description = "Pos Generate E-Faktur"

    name = fields.Char(string="Number", required=True, default='New', copy=False)
    other_name = fields.Char('Name', copy=False)
    state = fields.Selection([('draft','Draft'), ('done', 'Done')], string='Status', default='draft')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    invoice_ids = fields.One2many('pos.generate.efaktur.invoice','gen_efaktur_id')
    digunggung_ids = fields.One2many('pos.generate.efaktur.digunggung','gen_efaktur_id')
    gabungan_ids = fields.One2many('pos.generate.efaktur.gabungan','gen_efaktur_id')
    other_ids = fields.One2many('pos.generate.efaktur.other','gen_efaktur_id')
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)

    def action_generate(self):
        self.ensure_one()
        return True

class PosGenerateEfakturInvoice(models.Model):
    _name = "pos.generate.efaktur.invoice"
    _description = "Pos Generate Efaktur Invoice"

    gen_efaktur_id = fields.Many2one('pos.generate.efaktur','Generate E-Faktur')
    partner_id = fields.Many2one('res.partner', 'Member')
    account_move_id = fields.Many2one('account.move', string='Invoice')


class PosGenerateEfakturDigunggung(models.Model):
    _name = "pos.generate.efaktur.digunggung"
    _description = "Pos Generate Efaktur Digunggung"

    gen_efaktur_id = fields.Many2one('pos.generate.efaktur','Generate E-Faktur')
    partner_id = fields.Many2one('res.partner', 'Member')
    account_move_id = fields.Many2one('account.move', string='Invoice')
    account_move_data = fields.Text(string='Invoice Data')
    no_of_invoice = fields.Integer('No of Invoice', compute='_compute_no_of_invoice')
    amount_total = fields.Float('Total Amount')

    def _compute_no_of_invoice(self):
        for rec in self:
            rec.no_of_invoice = rec.account_move_data and len(json.loads(rec.account_move_data)) or 0


class PosGenerateEfakturGabungan(models.Model):
    _name = "pos.generate.efaktur.gabungan" 
    _description = "Pos Generate Efaktur Gabungan"

    gen_efaktur_id = fields.Many2one('pos.generate.efaktur','Generate E-Faktur')
    partner_id = fields.Many2one('res.partner', 'Member')
    account_move_id = fields.Many2one('account.move', string='Invoice') 
    account_move_data = fields.Text(string='Invoice Data')
    no_of_invoice = fields.Integer('No of Invoice', compute='_compute_no_of_invoice')
    amount_total = fields.Float('Total Amount')

    def _compute_no_of_invoice(self):
        for rec in self:
            rec.no_of_invoice = rec.account_move_data and len(json.loads(rec.account_move_data)) or 0

class PosGenerateEfakturOther(models.Model):
    _name = "pos.generate.efaktur.other" 
    _description = "Pos Generate Efaktur Other"

    gen_efaktur_id = fields.Many2one('pos.generate.efaktur','Generate E-Faktur')
    partner_id = fields.Many2one('res.partner', 'Member')
    account_move_id = fields.Many2one('account.move', string='Invoice')