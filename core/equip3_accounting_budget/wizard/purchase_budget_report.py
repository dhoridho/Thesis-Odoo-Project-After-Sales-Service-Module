from odoo import fields, models, api, _
import json
import io
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class PurchaseBudgetReport(models.TransientModel):
    _inherit = "account.common.report"
    _name = 'purchase.budget.report'
    _description = 'Purchase Budget Report'

    company_ids = fields.Many2many('res.company', string='Company')
    branch_ids = fields.Many2many('res.branch', string='Branch')
    analytic_tag_ids = fields.Many2many("account.analytic.tag", string="Analytic Tags")

    @api.model
    def view_report(self, option):
        r = self.env['purchase.budget.report'].search([('id', '=', option[0])])
        data = {
            'model': self,
            'companies': r.company_ids,
            'branches': r.branch_ids,
            'analytic_tags': r.analytic_tag_ids,
        }

        if r.date_from:
            data.update({
                'date_from':r.date_from,
            })
        if r.date_to:
            data.update({
                'date_to':r.date_to,
            })

        filters = self.get_filter(option)
        records = self._get_report_values(data)
        currency = self._get_currency()
        currency_ids = self.env['res.currency'].search([('active', '=', True)])

        return {
            'name': "Purchase Budget Report",
            'type': 'ir.actions.client',
            'tag': 'p_b_r',
            'filters': filters,
            'report_lines': records['PurchaseBudgets'],
            'currency': currency,
            'currencies': [{
                'name': currency_id.name,
                'id': currency_id.id,
            } for currency_id in currency_ids],
        }

    def get_filter(self, option):
        data = self.get_filter_data(option)
        filters = {}

        if data.get('date_from'):
            filters['date_from'] = data.get('date_from')
        if data.get('date_to'):
            filters['date_to'] = data.get('date_to')
        if data.get('companies'):
            filters['companies'] = self.env['res.company'].browse(data.get('companies')).mapped('name')
        else:
            filters['companies'] = ['All']
        if data.get('branches'):
            filters['branches'] = self.env['res.branch'].browse(data.get('branches')).mapped('name')
        else:
            filters['branches'] = ['All']
        if data.get('analytic_tags'):
            filters['analytic_tags'] = self.env['account.analytic.tag'].browse(data.get('analytic_tags')).mapped('name')
        else:
            filters['analytic_tags'] = ['All']

        filters['company_id'] = ''
        filters['company_name'] = data.get('company_name')
        filters['companies_list'] = data.get('companies_list')
        filters['branches_list'] = data.get('branches_list')
        filters['analytic_tag_list'] = data.get('analytic_tag_list')

        return filters

    def get_filter_data(self, option):
        r = self.env['purchase.budget.report'].search([('id', '=', option[0])])
        default_filters = {}
        company_id = self.env.company
        company_domain = [('company_id', '=', company_id.id)]
        # analytic_tag_ids = self.analytic_tag_ids if self.analytic_tag_ids else self.env['account.analytic.tag'].sudo().search(['|', ('company_id', '=', company_id.id), ('company_id', '=', False)])
        analytic_tag_ids = self.analytic_tag_ids if self.analytic_tag_ids else self.env['account.analytic.tag'].sudo().search([])
        company = r.company_ids if r.company_ids else self.env['res.company'].search([])
        branch = r.branch_ids if r.branch_ids else self.env['res.branch'].search([])

        filter_dict = {
            'companies': r.company_ids.ids,
            'branches': r.branch_ids.ids,
            'analytic_tags': r.analytic_tag_ids.ids,
            'company_id': company_id.id,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'analytic_tag_list': [(anltag.id, anltag.name) for anltag in analytic_tag_ids],
            'companies_list': [(p.id, p.name) for p in company],
            'branches_list': [(p.id, p.name) for p in branch],
            'company_name': company_id and company_id.name,
        }

        filter_dict.update(default_filters)
        return filter_dict

    def _get_report_values(self, data):
        docs = data['model']

        domain = [('state','=','validate')]
        if data.get('date_from'):
            domain += [('date_from','>=',data['date_from'])]
        if data.get('date_to'):
            domain += [('date_to','<=',data['date_to'])]
        if data['companies']:
            domain += [('company_id','in',data['companies'].ids)]
        if data['branches']:
            domain += [('branch_id','in',data['branches'].ids)]
        if data['analytic_tags']:
            domain += [('account_tag_ids','in',data['analytic_tags'].ids)]

        purchase_budgets = self.env['budget.purchase'].search(domain)
        purchase_budget_res = self._get_purchase_budget(purchase_budgets, data)

        return {
            'doc_ids': self.ids,
            'docs': docs,
            'PurchaseBudgets': purchase_budget_res,
        }

    def _get_purchase_budget(self, purchase_budgets, data):
        cr = self.env.cr
        purchase_budget = self.search([], limit=1, order="id desc")
        report_currency_id = purchase_budget.report_currency_id
        currency_rate = 0

        if not report_currency_id:
            currency_id = self.env.company.currency_id
        else:
            currency_id = report_currency_id
            if data.get('date_from') and data.get('date_to'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name >= data.get('date_from') and r.name <= data.get('date_to')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            elif data.get('date_from'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name >= data.get('date_from')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            elif data.get('date_to'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name <= data.get('date_to')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            else:
                currency_rate = currency_id.rate

        partner_res = []
        for budget in purchase_budgets:
            company_id = self.env.company
            if not report_currency_id:
                currency = company_id.currency_id
            else:
                currency = report_currency_id

            res = {}
            res['id'] = budget.id
            res['name'] = budget.name
            res['date_from'] = budget.date_from
            res['date_to'] = budget.date_to
            res['planned_amount'] = budget.total_planned_amount
            res['avail_amount'] = budget.total_avail_amount
            res['reserve_amount'] = budget.total_reserve_amount
            res['practical_amount'] = budget.total_practical_amount
            res['remaining_amount'] = budget.total_remaining_amount
            res['parent_budget_id'] = budget.parent_budget_id.id
            res['state'] = dict(self.env['budget.purchase']._fields['state'].selection).get(budget.state)
            res['company_id'] = budget.company_id.name
            res['branch_id'] = budget.branch_id.name
            res['is_monthly'] = False

            tag_names = budget.account_tag_ids.mapped('name')
            res['analytic_tags'] = ', '.join(tag_names)

            if budget.child_budget_ids:
                res['child_lines'] = self._get_purchase_budget(budget.child_budget_ids, data)
                res['is_parent'] = True
            else:
                monthly_pb = self.env['monthly.purchase.budget'].search([('budget_purchase_id','=',budget.id)])
                if monthly_pb:
                    res['child_lines'] = self._get_monthly_purchase_budget(monthly_pb, data)
                    res['is_parent'] = True
                else:
                    res['child_lines'] = []
                    res['is_parent'] = False

            partner_res.append(res)

        return partner_res

    def _get_monthly_purchase_budget(self, monthly_pb, data):
        cr = self.env.cr
        purchase_budget = self.search([], limit=1, order="id desc")
        report_currency_id = purchase_budget.report_currency_id
        currency_rate = 0

        if not report_currency_id:
            currency_id = self.env.company.currency_id
        else:
            currency_id = report_currency_id
            if data.get('date_from') and data.get('date_to'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name >= data.get('date_from') and r.name <= data.get('date_to')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            elif data.get('date_from'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name >= data.get('date_from')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            elif data.get('date_to'):
                rate_ids = currency_id.rate_ids.filtered(lambda r: r.name <= data.get('date_to')).sorted(key=lambda r: r.name)
                if rate_ids:
                    currency_rate = rate_ids[-1].mr_rate
                else:
                    currency_rate = currency_id.rate
            else:
                currency_rate = currency_id.rate

        partner_res = []
        for monthly in monthly_pb:
            company_id = self.env.company
            if not report_currency_id:
                currency = company_id.currency_id
            else:
                currency = report_currency_id

            res = {}
            res['id'] = monthly.id
            res['name'] = monthly.name
            res['date_from'] = monthly.date_from
            res['date_to'] = monthly.date_to
            res['planned_amount'] = monthly.total_line_planned_amount
            res['avail_amount'] = monthly.total_line_avail_amount
            res['reserve_amount'] = monthly.total_line_reserve_amount
            res['practical_amount'] = monthly.total_line_practical_amount
            res['remaining_amount'] = monthly.total_line_remaining_amount
            # res['parent_budget_id'] = budget.parent_budget_id.id
            res['state'] = dict(self.env['monthly.purchase.budget']._fields['state'].selection).get(monthly.state)
            res['company_id'] = monthly.company_id.name
            res['branch_id'] = monthly.branch_id.name
            res['child_lines'] = []
            res['is_parent'] = False
            res['is_monthly'] = True

            tag_names = monthly.account_tag_ids.mapped('name')
            res['analytic_tags'] = ', '.join(tag_names)

            partner_res.append(res)

        return partner_res

    def write(self, vals):
        if vals.get('company_ids'):
            vals.update({'company_ids': [(6, 0, vals.get('company_ids'))]})
        if not vals.get('company_ids'):
            vals.update({'company_ids': [(5,)]})
        if vals.get('branch_ids'):
            vals.update({'branch_ids': [(6, 0, vals.get('branch_ids'))]})
        if not vals.get('branch_ids'):
            vals.update({'branch_ids': [(5,)]})
        if vals.get('analytic_tag_ids'):
            vals.update({'analytic_tag_ids': [(6, 0, vals.get('analytic_tag_ids'))]})
        if not vals.get('analytic_tag_ids'):
            vals.update({'analytic_tag_ids': [(5,)]})

        res = super(PurchaseBudgetReport, self).write(vals)
        return res

    @api.model
    def _get_currency(self):
        journal = self.env['account.journal'].browse(
            self.env.context.get('default_journal_id', False))
        if journal.currency_id:
            return journal.currency_id.id
        lang = self.env.user.lang
        if not lang:
            lang = 'en_US'
        lang = lang.replace("_", '-')
        currency_array = [self.env.company.currency_id.symbol,
                          self.env.company.currency_id.position, lang]
        return currency_array

    def get_dynamic_xlsx_report(self, data, response, report_data, dfr_data):
        report_data = json.loads(report_data)
        filters = json.loads(data)

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        cell_format = workbook.add_format({'bold': True,'border': 0})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'bold': True})
        txt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        sub_heading_sub = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black', 'num_format': '#,##0.00'})
        sheet.merge_range('A1:L2',
                          filters.get('company_name') + ':' + 'Purchase Budget Report',
                          head)
        date_head = workbook.add_format({'bold': True})

        sheet.merge_range('A3:B3', ' Company: ' + ', '.join(
            [lt or '' for lt in filters['companies']]), date_head)
        sheet.merge_range('C3:D3', ' Branch: ' + ', '.join(
            [lt or '' for lt in filters['branches']]), date_head)
        sheet.merge_range('E3:F3', ' Analytic Group: ' + ', '.join(
            [lt or '' for lt in filters['analytic_tags']]), date_head)

        if filters.get('date_from') and filters.get('date_to'):
            sheet.merge_range('E4:F4', 'From: ' + filters.get('date_from'), date_head)
            sheet.merge_range('G4:H4', 'To: ' + filters.get('date_to'), date_head)
        elif filters.get('date_from'):
            sheet.merge_range('E4:F4', 'From: ' + filters.get('date_from'), date_head)
        elif filters.get('date_to'):
            sheet.merge_range('E4:F4', 'To: ' + filters.get('date_to'), date_head)

        # sheet.merge_range('A5:E5', 'Partner', sub_heading_sub)
        sheet.write('A5', 'Purchase Budget', sub_heading_sub)
        sheet.write('B5', 'Company', sub_heading_sub)
        sheet.write('C5', 'Branch', sub_heading_sub)
        sheet.write('D5', 'Analytic Group', sub_heading_sub)
        sheet.write('E5', 'Start Date', sub_heading_sub)
        sheet.write('F5', 'End Date', sub_heading_sub)
        sheet.write('G5', 'Planned Amount', sub_heading_sub)
        sheet.write('H5', 'Available to Reserve', sub_heading_sub)
        sheet.write('I5', 'Reserved Amount', sub_heading_sub)
        sheet.write('J5', 'Used Amount', sub_heading_sub)
        sheet.write('K5', 'Remaining Amount', sub_heading_sub)
        # sheet.write('L5', 'Status', sub_heading_sub)

        row = 4
        col = 0

        sheet.set_column('A:A', 50, '')
        sheet.set_column('B:B', 20, '')
        sheet.set_column('C:C', 20, '')
        sheet.set_column('D:D', 25, '')
        sheet.set_column('E:E', 15, '')
        sheet.set_column('F:F', 15, '')
        sheet.set_column('G:G', 20, '')
        sheet.set_column('H:H', 20, '')
        sheet.set_column('I:I', 20, '')
        sheet.set_column('J:J', 20, '')
        sheet.set_column('K:K', 20, '')
        sheet.set_column('L:L', 15, '')

        for report in report_data:
            if report['parent_budget_id'] == False:
                row += 1
                sheet.write(row, col + 0, report['name'], txt)
                sheet.write(row, col + 1, report['company_id'], txt)
                sheet.write(row, col + 2, report['branch_id'], txt)
                sheet.write(row, col + 3, report['analytic_tags'], txt)
                sheet.write(row, col + 4, report['date_from'], txt)
                sheet.write(row, col + 5, report['date_to'], txt)
                sheet.write(row, col + 6, report['planned_amount'], txt)
                sheet.write(row, col + 7, report['avail_amount'], txt)
                sheet.write(row, col + 8, report['reserve_amount'], txt)
                sheet.write(row, col + 9, report['practical_amount'], txt)
                sheet.write(row, col + 10, report['remaining_amount'], txt)
                # sheet.write(row, col + 11, report['state'], txt)
                
                for r_rec in report['child_lines']:
                    row += 1
                    sheet.write(row, col + 0, '    ' + r_rec['name'], txt)
                    sheet.write(row, col + 1, r_rec['company_id'], txt)
                    sheet.write(row, col + 2, r_rec['branch_id'], txt)
                    sheet.write(row, col + 3, r_rec['analytic_tags'], txt)
                    sheet.write(row, col + 4, r_rec['date_from'], txt)
                    sheet.write(row, col + 5, r_rec['date_to'], txt)
                    sheet.write(row, col + 6, r_rec['planned_amount'], txt)
                    sheet.write(row, col + 7, r_rec['avail_amount'], txt)
                    sheet.write(row, col + 8, r_rec['reserve_amount'], txt)
                    sheet.write(row, col + 9, r_rec['practical_amount'], txt)
                    sheet.write(row, col + 10, r_rec['remaining_amount'], txt)
                    # sheet.write(row, col + 11, r_rec['state'], txt)

                    for line in r_rec['child_lines']:
                        row += 1
                        sheet.write(row, col + 0, '        ' + line['name'], txt)
                        sheet.write(row, col + 1, line['company_id'], txt)
                        sheet.write(row, col + 2, line['branch_id'], txt)
                        sheet.write(row, col + 3, line['analytic_tags'], txt)
                        sheet.write(row, col + 4, line['date_from'], txt)
                        sheet.write(row, col + 5, line['date_to'], txt)
                        sheet.write(row, col + 6, line['planned_amount'], txt)
                        sheet.write(row, col + 7, line['avail_amount'], txt)
                        sheet.write(row, col + 8, line['reserve_amount'], txt)
                        sheet.write(row, col + 9, line['practical_amount'], txt)
                        sheet.write(row, col + 10, line['remaining_amount'], txt)
                        # sheet.write(row, col + 11, line['state'], txt)
                row += 1

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()