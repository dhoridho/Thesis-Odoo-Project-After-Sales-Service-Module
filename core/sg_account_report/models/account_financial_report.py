# See LICENSE file for full copyright and licensing details.

import time

from odoo import _, api, fields, models


class AccountFinancialReport(models.Model):

    _name = "afr"
    _description = "Account Financial Report"

    name = fields.Char('Name',
                       help="""This will be the title that will be displayed \
                       in the header of the report. E.g. - "Balance Sheet" or \
                       "Income Statement".""", required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True)
    currency_id = fields.Many2one('res.currency', 'Currency',
                                  help="This will be the currency in which \
                                  the report will be stated in. If no \
                                  currency is selected, the default currency \
                                  of the \
                                  company will be selected.")
    columns = fields.Selection([('one', 'End. Balance'),
                                ('two', 'Debit | Credit'),
                                ('four', 'Balance | Debit | Credit'),
                                ('five', 'Balance | Debit | Credit | YTD'),
                                ('qtr', "4 QTR's | YTD"),
                                ('thirteen', '12 Months | YTD')],
                               'Columns', required=True, default='five')
    start_date = fields.Datetime('Start Date', required=True,
                                 default=time.strftime('%Y-01-01'))
    end_date = fields.Datetime('End Date', required=True,
                               default=time.strftime('%Y-12-31'))
    target_move = fields.Selection([('posted', 'All Posted Entries'),
                                    ('all', 'All Entries')], default='posted',
                                   string='Target Moves', required=True)

    def copy(self, defaults):
        """Copy Method.

        This method override to add 'Copy' string in the name field.
        """
        res_afr = super(AccountFinancialReport, self).copy(defaults)
        for afr_rec in self:
            new_name = _('Copy of %s') % afr_rec.name
            afr_recs = self.search([('name', 'like', new_name)])
            if afr_recs.ids:
                new_name = '%s (%s)' % (new_name, len(afr_recs.ids) + 1)
            afr_rec.name = new_name
        return res_afr

    @api.onchange('company_id')
    def onchange_company_id(self):
        """Company Onchange.

        This onchange method is used to set currency_id according to selection
        of company. Set currency_id which define in company.
        """
        context = self.env.context
        company_id = self and self.company_id and self.company_id.id or False
        if context is None:
            context = {}
        ctx = context.copy()
        ctx = dict(ctx)
        ctx['company_id'] = company_id
        if company_id:
            company_obj = self.env['res.company']
            company_rec = company_obj.with_context(context=ctx).browse(
                company_id)
            self.currency_id = company_rec and company_rec.currency_id and \
                company_rec.currency_id.id or False
