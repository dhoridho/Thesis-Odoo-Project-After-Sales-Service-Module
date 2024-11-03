# -*- coding: utf-8 -*-
from odoo import api, models, _


class InsReportJournalEntry(models.AbstractModel):
    _name = 'report.equip3_accounting_reports.journal_entry_report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.context.get('js_report'):
            if data.get('report_data'):
                data.update({
                    'Filters': data.get('report_data')['filters'],
                    'report_lines': data.get('report_data')['je_lines'],
                    'report_name': data.get('report_name'),
                    'title': data.get('report_data')['name'],
                })
        return data

class JournalEntryReport(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_journal_entries'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        record = []
        for lines in docs:
            rec = {}
            rec['name'] = lines.name
            rec['journal'] = lines.journal_id.name
            rec['date'] = lines.date
            rec['partner'] = lines.partner_id.display_name
            rec['reference'] = lines.ref
            rec['currency_id'] = lines.currency_id
            rec['line_ids'] = []
            cek = lines.line_ids.sorted(key=lambda y: y.debit, reverse=True)
            for line in cek:
                rec_line = {}
                rec_line['account'] = line.account_id.name
                rec_line['date'] = line.date
                rec_line['partner'] = line.partner_id.display_name
                rec_line['label'] = line.name
                rec_line['analytic_account'] = line.analytic_account_id.display_name
                rec_line['debit'] = line.debit
                rec_line['credit'] = line.credit
                rec_line['currency_id'] = line.currency_id
                rec['line_ids'].append(rec_line)
            
            record.append(rec)            
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
            'move': record,
        }