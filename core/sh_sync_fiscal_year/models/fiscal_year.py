# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)
from dateutil.relativedelta import relativedelta


class ResCompany(models.Model):
    _inherit = 'res.company'

    sh_enable_approval = fields.Boolean("Enable Approval work Flow")
    sh_restrict_for_close_period = fields.Boolean(
        "Restrict record creation for Closed Fiscal Period or Closed Fiscal Year")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sh_enable_approval = fields.Boolean(
        string="Enable Approval work Flow", related='company_id.sh_enable_approval', readonly=False)
    sh_restrict_for_close_period = fields.Boolean(
        string="Restrict record creation for Closed Fiscal Period or Closed Fiscal Year", related='company_id.sh_restrict_for_close_period', readonly=False)

    def update_old_records(self):
        for rec in self.env['account.move'].sudo().search(['|', ('period_id', '=', False), ('fiscal_year', '=', False)]):
            if rec.date:
                period = self.env['sh.account.period'].sudo().search(
                    [('date_start', '<=', rec.date), ('date_end', '>=', rec.date)], limit=1)
                if period:
                    rec.period_id = period.id


class Journal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection(selection_add=[(
        'opening', 'Opening/Closing Situation')], ondelete={'opening': 'cascade'})


class MoveLine(models.Model):
    _inherit = 'account.move.line'

    period_id = fields.Many2one(
        'sh.account.period', string="Period", related="move_id.period_id", store=True)
    fiscal_year = fields.Many2one(
        'sh.fiscal.year', string="Fiscal Year", related="period_id.fiscal_year_id", store=True)


class Move(models.Model):
    _inherit = 'account.move'

    period_id = fields.Many2one(
        'sh.account.period', string="Period", compute='_compute_get_period', store=True)
    fiscal_year = fields.Many2one(
        'sh.fiscal.year', string="Fiscal Year", related="period_id.fiscal_year_id", store=True)

    @api.depends('date')
    def _compute_get_period(self):
        if self:
            for rec in self:
                rec.period_id = False
                if rec.date:
                    period = self.env['sh.account.period'].sudo().search([('date_start', '<=', rec.date), ('date_end', '>=', rec.date)], limit=1)
                    if period:
                        rec.period_id = period.id

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        res = super(Move, self).create(vals_list)
        for vals in vals_list:
            if 'date' in vals:
                period = self.env['sh.account.period'].sudo().search(
                    [('date_start', '<=', vals['date']), ('date_end', '>=', vals['date'])], limit=1)

                if self.env.company.sh_restrict_for_close_period and period.state == 'done':
                    raise UserError(_(
                        "You can not Select Date from Closed Fiscal Period / Closed Fiscal Year."))
        return res

    def write(self, vals):
        rslt = super(Move, self).write(vals)
        if self:
            for rec in self:
                if rec.company_id.sh_restrict_for_close_period and rec.period_id.state == 'done':
                    raise UserError(_(
                        "You can not Select Date from Closed Fiscal Period / Closed Fiscal Year."))
        return rslt


class ShFiscalYear(models.Model):
    _name = 'sh.fiscal.year'
    _description = "Fiscal Year"

    name = fields.Char("Fiscal Year", required="1", copy=False, readonly=True, states={'draft': [('readonly', False)]})
    code = fields.Char("Code", required="1", copy=False, readonly=True, states={'draft': [('readonly', False)]})
    date_start = fields.Date("Start Date", required=True, readonly=True, states={'draft': [('readonly', False)]})
    date_end = fields.Date("End Date", required=True, readonly=True, states={'draft': [('readonly', False)]})
    period_ids = fields.One2many('sh.account.period', 'fiscal_year_id', string="Periods", readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Open'), 
                              ('waiting', 'Waiting for Approval'), 
                              ('done', 'Closed'),
                              ('reopen', 'Waiting for Re-Open Approval')], 
                              string="State", default="draft")
    move_id = fields.Many2one('account.move', string="End of Year Entries Journal", readonly=True, states={'draft': [('readonly', False)]})

    _sql_constraints = [
        ('code_company_uniq', 'unique (code,company_id)', 'The code of the fiscal years must be unique per company !'),
        ('name_company_uniq', 'unique (name,company_id)', 'The name of the fiscal years must be unique per company !')
    ]

    def check_date_fs(self, data):
        if data.get('date_start') and data.get('date_end'):
            # sql = ('''SELECT sfy.name, sfy.code, sfy.company_id, sfy.date_start, sfy.date_end
            #           FROM sh_fiscal_year sfy 
            #           WHERE company_id = %s and 
            #           (sfy.date_start >= %s and sfy.date_start <= %s) or (sfy.date_end >= %s and sfy.date_end <= %s)'''
            #       )
            # params = [str(data.get('company_id')), data.get('date_start'), data.get('date_end'), data.get('date_start'), data.get('date_end')]

            sql = ('''SELECT sfy.name, sfy.code, sfy.company_id, sfy.date_start, sfy.date_end
                      FROM sh_fiscal_year sfy 
                      WHERE company_id = %s and 
                      (sfy.date_start = %s and sfy.date_end = %s)'''
                  )
            params = [str(data.get('company_id')), data.get('date_start'), data.get('date_end')]
            self.env.cr.execute(sql, params)
            value_fetch = self.env.cr.dictfetchall()           
            return value_fetch
        return False

    @api.model
    def create(self, vals):
        if vals.get('date_start') and vals.get('date_end'):
            check_date = self.check_date_fs(vals)
            if check_date:
                raise UserError(_("Can't create Fiscal Years\nFiscal Years date has ben created before"))
        result = super(ShFiscalYear, self).create(vals)
        return result

    def create_period3(self):
        return self.create_period(3)

    def create_period(self, interval=1):
        period_obj = self.env['sh.account.period']
        for rec in self:
            ds = rec.date_start
            period_obj.create({
                'name':  "%s %s" % (_('Opening Period'), ds.strftime('%Y')),
                'code': ds.strftime('00/%Y'),
                'date_start': ds,
                'date_end': ds,
                'special': True,
                'fiscal_year_id': rec.id,
                'company_id': rec.company_id.id,
            })
            while ds < rec.date_end:
                de = ds + relativedelta(months=interval, days=-1)

                if de > rec.date_end:
                    de = rec.date_end

                period_obj.create({
                    'name': ds.strftime('%m/%Y'),
                    'code': ds.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_end': de.strftime('%Y-%m-%d'),
                    'fiscal_year_id': rec.id,
                    'company_id': rec.company_id.id,
                })
                ds = ds + relativedelta(months=interval)
        return True

    def close_fiscal_year(self):
        for rec in self:
            if rec.env.user.company_id.sh_enable_approval:
                rec.write({'state': 'waiting'})
                rec.period_ids.write({'state': 'waiting'})
            else:
                rec.write({'state': 'done'})
                rec.period_ids.write({'state': 'done'})

    def close_fiscal_year_approve(self):
        # if self.move_id.state != 'posted':
        #     raise UserError(_(
        #         'In order to close a fiscalyear, you must first post related journal entries.'))

        if self.state == 'waiting':

            self._cr.execute('UPDATE sh_account_period SET state = %s '
                            'WHERE fiscal_year_id = %s', ('done', self.id))
            self._cr.execute('UPDATE sh_fiscal_year '
                            'SET state = %s WHERE id = %s', ('done', self.id))

        # return {'type': 'ir.actions.act_window_close'}

    def re_open_fiscal_year_approve(self):

        if self.state == 'reopen':

            self._cr.execute('UPDATE sh_fiscal_year '
                             'SET state = %s WHERE id = %s', ('draft', self.id))
            self._cr.execute('UPDATE sh_account_period SET state = %s '
                             'WHERE fiscal_year_id = %s', ('draft', self.id))

    def re_open_fiscal_year(self):
        for rec in self:
            if rec.env.user.company_id.sh_enable_approval:
                rec.write({'state': 'reopen'})
                rec.period_ids.write({'state': 'reopen'})
            else:
                rec.write({'state': 'draft'})
                self.period_ids.write({'state': 'draft'})


class ShAccountPeriod(models.Model):
    _name = 'sh.account.period'
    _description = "Fiscal Period"

    name = fields.Char("Period Name", required="1", copy=False,
                       readonly=True, states={'draft': [('readonly', False)]})
    code = fields.Char("Code", copy=False, readonly=True,
                       states={'draft': [('readonly', False)]})
    date_start = fields.Date("Start of Period", required=True, copy=False,
                             readonly=True, states={'draft': [('readonly', False)]})
    date_end = fields.Date("End of Period", required=True, copy=False,
                           readonly=True, states={'draft': [('readonly', False)]})
    fiscal_year_id = fields.Many2one('sh.fiscal.year', string="Fiscal Year", readonly=True, states={
                                     'draft': [('readonly', False)]})
    special = fields.Boolean(
        "Opening/Closing Period", readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(
        [('draft', 'Open'), ('waiting', 'Waiting for Approval'), ('done', 'Closed'),
         ('reopen', 'Waiting for Re-Open Approval')], string="State", default="draft")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        # _logger.info("allowed_company_ids: %s", self.env.context.get('allowed_company_ids'))
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', context.get('allowed_company_ids'))]
            # _logger.info("domain: %s", domain)

        result = super(ShAccountPeriod, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

        return result

    def close_period(self):
        for rec in self:
            if rec.env.user.company_id.sh_enable_approval:
                rec.write({'state': 'waiting'})
            else:
                rec.write({'state': 'done'})

    def reopen_period(self):
        if self.env.user.company_id.sh_enable_approval:
            self.write({'state': 'reopen'})
        else:
            self.write({'state': 'draft'})

    def close_period_approve(self):
        for rec in self:

            rec.write({'state': 'done'})

    def reopen_period_approve(self):

        self.write({'state': 'draft'})
