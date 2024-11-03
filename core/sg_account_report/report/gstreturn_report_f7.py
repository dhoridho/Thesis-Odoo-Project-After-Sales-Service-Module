
import time

from odoo import models
from odoo.tools.misc import formatLang


class ReportGstReturnf7(models.AbstractModel):

    _name = 'report.sg_account_report.gst_return_report_f7'
    _description = "Gst F7 Report"

    def get_info(self, form):
        """Get Information."""
        tax_list = []
        account_tax = self.env['account.tax']
        box1 = box2 = box3 = box4 = box5 = box6 = box7 = box8 = \
            box9 = box10 = box11 = box12 = box13 = \
            net_gst_prevs = 0.00
        box1_tot = box2_tot = box3_tot = box5_tot = box6_tot = \
            box7_tot = box9_tot = 0.0
        box10 = form.get('box10') or 0.00
        box11 = form.get('box11') or 0.00
        box12 = form.get('box12') or 0.00
        net_gst_prevs = form.get('net_gst_prevs') or 0.00
        date_start = form.get('date_from', False) or False
        date_end = form.get('date_to', False) or False
        notes = form.get('notes') or ''
        company_id = self.env.user.company_id
        company_name = company_id.name
        tax_no = company_id.vat or False
        gst_no = company_id.gst_no or False
        domain = [('date', '>=', date_start), ('date', '<=', date_end)]
        if form.get('target_move', False):
            if form['target_move'] == 'posted':
                domain += [('move_id.state', '=', 'posted')]
        move_line_obj = self.env['account.move.line']

        #  fetch account move line for  customer Invoices
        #  search invoice line which has sales tax 7% SR or DS
        tax_ids_box1 = account_tax.search([('name', 'in',
                                            ['Sales Tax 7% SR',
                                             'Sales Tax 7% DS'])])
        move_lines = move_line_obj.search(domain + [('tax_ids', 'in',
                                                     tax_ids_box1.ids)])
        if move_lines and move_lines.ids:
            box1_tot = sum([move.credit for move in move_lines])

        #  search move lines which has sales tax OS or ZR taxes
        tax_ids_box2 = account_tax.search([('name', 'in',
                                            ['Sales Tax 0% OS',
                                             'Sales Tax 0% ZR'])])
        move_lines2 = move_line_obj.search(domain + [('tax_ids', 'in',
                                                      tax_ids_box2.ids)])
        if move_lines2 and move_lines2.ids:
            box2_tot = sum([move2.credit for move2 in move_lines2])

        #  search move lines which has sales tax ES33 or ESN33
        tax_ids_box3 = account_tax.search([('name', 'in',
                                            ['Sales Tax 0% ES33',
                                             'Sales Tax 0% ESN33'])])
        move_lines3 = move_line_obj.search(domain + [('tax_ids', 'in',
                                                      tax_ids_box3.ids)])
        if move_lines3 and move_lines3.ids:
            box3_tot = sum([move3.credit for move3 in move_lines3])

        #  fetch the move lines which has the purchase taxes
        tax_ids_box5 = account_tax.search([('name', 'in',
                                            ['Purchase Tax 0% EP',
                                             'Purchase Tax 0% ME',
                                             'Purchase Tax 0% NR',
                                             'Purchase Tax 0% OP',
                                             'Purchase Tax 0% ZP',
                                             'Purchase Tax 7% BL',
                                             'Purchase Tax 7% IM',
                                             'Purchase Tax 7% TX7',
                                             'Purchase Tax 7% TX-E33',
                                             'Purchase Tax 7% TX-N33',
                                             'Purchase Tax 7% TX-RE'])])
        move_lines5 = move_line_obj.search(domain + [('tax_ids', 'in',
                                                      tax_ids_box5.ids)])
        if move_lines5 and move_lines5.ids:
            box5_tot = sum([move5.debit for move5 in move_lines5])

        #  fetch the move line which has the taxes
        move_lines6 = move_line_obj.search(domain + [('tax_line_id', 'in',
                                                      tax_ids_box1.ids)])
        if move_lines6 and move_lines6.ids:
            for move6 in move_lines6:
                box6_tot += move6.credit
                box6_tot -= move6.debit

        move_lines7 = move_line_obj.search(domain + [('tax_line_id', 'in',
                                                      tax_ids_box5.ids)])
        if move_lines7 and move_lines7.ids:
            for move7 in move_lines7:
                box7_tot += move7.debit
                box7_tot -= move7.credit

        tax_ids_box9 = account_tax.search([('name', 'in',
                                            ['Purchase Tax MES'])])
        move_lines9 = move_line_obj.search(domain + [('tax_ids', 'in',
                                                      tax_ids_box9.ids)])
        if move_lines9 and move_lines9.ids:
            box9_tot = sum([move9.debit for move9 in move_lines9])

        box1 = box1_tot
        box2 = box2_tot
        box3 = box3_tot
        box4 = box1_tot + box2_tot + box3_tot
        box5 = box5_tot
        box6 = box6_tot
        box7 = box7_tot
        box8 = box7_tot + box6_tot
        box9 = box9_tot
        box13 = box5_tot - box4

        tax_list.append({'name': company_name or '',
                         'tax_no': tax_no or 0.0,
                         'gst_no': gst_no or 0.0,
                         'date_start': date_start or False,
                         'date_end': date_end or False,
                         'notes': notes or '',
                         'box1': formatLang(self.env, abs(box1 or 0.0)),
                         'box2': formatLang(self.env, abs(box2 or 0.0)),
                         'box3': formatLang(self.env, abs(box3 or 0.0)),
                         'box4': formatLang(self.env, abs(box4 or 0.0)),
                         'box5': formatLang(self.env, abs(box5 or 0.0)),
                         'box6': formatLang(self.env, abs(box6 or 0.0)),
                         'box7': formatLang(self.env, abs(box7 or 0.0)),
                         'box8': formatLang(self.env, (box8 or 0.0)),
                         'box9': formatLang(self.env, abs(box9 or 0.0)),
                         'box10': formatLang(self.env, abs(box10 or 0.00)),
                         'box11': formatLang(self.env, abs(box11 or 0.00)),
                         'box12': formatLang(self.env, abs(box12 or 0.00)),
                         'box13': formatLang(self.env, (box13 or 0.0)),
                         'net_gst_prevs': formatLang(
                             self.env, float(net_gst_prevs)),
                         'net_gst_prevs_total':
                         formatLang(self.env, (box8 - net_gst_prevs))})
        return tax_list

    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        datas = docs.read([])[0]
        report_lines = self.get_info(datas)
        return {'doc_ids': self.ids,
                'doc_model': model,
                'data': data,
                'docs': docs,
                'time': time,
                'get_info': report_lines}
