from odoo import fields, models, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class ShFiscalYear(models.Model):
    _inherit = 'sh.fiscal.year'

    hide_button = fields.Boolean(default=False, compute='_onchange_period_ids')
    move_id = fields.Many2one('account.move', string="Closing Year Entry", readonly=True, states={'draft': [('readonly', False)]})
    summary_move_id = fields.Many2one('account.move', string="Profit and Loss Summary Entry", readonly=True, states={'draft': [('readonly', False)]})
    
    @api.onchange('state', 'period_ids')  
    def _onchange_period_ids(self):
        if len(self.period_ids) == 0:
            self.hide_button = False
            if self.state == 'draft':
                self.hide_button = False
            else:
                self.hide_button = True
        else:
            self.hide_button = True

    def create_period(self, interval=1):
        period_obj = self.env['sh.account.period']
        company_id = self.env['res.company']._company_default_get('sh.fiscal.year')
        if not company_id:
            raise UserError(_('Please define a company for the fiscal year.'))
        

        for rec in self:
            ds = rec.date_start
            period_obj.create({
                'name':  "%s %s" % (_('Opening Period'), ds.strftime('%Y')),
                'code': ds.strftime('00/%Y'),
                'date_start': ds,
                'date_end': ds,
                'special': True,
                'fiscal_year_id': rec.id,
                'company_id': company_id.id,
                'branch_id': rec.branch_id.id,
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
                    'company_id': company_id.id,
                    'branch_id': rec.branch_id.id,

                })
                ds = ds + relativedelta(months=interval)
            rec.hide_button = True
        # print('period_obj', period_obj)
        return True