
from odoo import api, fields, models, _
from datetime import datetime
from tabulate import tabulate


class AccountMove(models.Model):
    _inherit = "account.move"


    def ph_format_currency_amount(self, amount):
        pre = post = u''
        currency_id = self.currency_id
        if currency_id.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency_id.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency_id.symbol or '')

        amount = '{:,.0f}'.format(amount)
        format_amount = '{pre}{amount}{post}'.format(amount=amount, pre=pre, post=post)
        format_amount = str(format_amount)
        format_amount = ' '.join(format_amount.split())
        return format_amount


    def set_content_for_download_txt(self):
        self.ensure_one()
        res = '\n\n'
        if self.pos_session_id:
            res += '                                                                   '+self.pos_session_id.config_id.company_id.name+' '+self.pos_session_id.config_id.pos_branch_id.name+'\n'
            if self.pos_session_id.config_id.pos_branch_id.street:
                res += '                                                                   '+self.pos_session_id.config_id.pos_branch_id.street+'\n'
            else:
                if self.pos_session_id.config_id.company_id.street:
                    res += '                                                                   '+self.pos_session_id.config_id.company_id.street+'\n'
            if self.pos_session_id.config_id.pos_branch_id.street_2:
                res += '                                                                   '+self.pos_session_id.config_id.pos_branch_id.street_2+'\n'
            else:
                if self.pos_session_id.config_id.company_id.street2:
                    res += '                                                                   '+self.pos_session_id.config_id.company_id.street2+'\n'

            if self.company_id.company_npwp:
                res += '                                                                   VAT REG TIN  : '+self.company_id.company_npwp+'\n'

            if self.pos_session_id.config_id.pos_branch_id.telephone:
                res += '                                                                   Phone : '+self.pos_session_id.config_id.pos_branch_id.telephone+'\n'
            else:
                if self.pos_session_id.config_id.company_id.phone:
                    res += '                                                                   Phone : '+self.pos_session_id.config_id.company_id.phone+'\n'


        else:
            res += '                                                                   '+self.company_id.name+'\n'
            if self.company_id.street:
                res += '                                                                   '+self.company_id.street+'\n'
            if self.company_id.company_npwp:
                res += '                                                                   VAT REG TIN  : '+self.company_id.company_npwp+'\n'
            if self.company_id.phone:
                res += '                                                                   Phone : '+self.company_id.phone+'\n'


        res += '\n\n'

        data = []
        move_date = self.date or ''
        if move_date:
            move_date = move_date.strftime("%d/%m/%Y")
        data.append(['Number : ' + (self.name or '/'),''])
        data.append(['Journal : ' + (self.journal_id.name or '/'),'Date : '+ move_date])
        data.append(['Partner : ' + (self.partner_id.name or ''),'Reference : '+ ((self.pos_session_id.name or '') or self.origin)])
        tabulate_header  = tabulate(data,  tablefmt="grid")
        res+=tabulate_header
        res+='\n'
        res+='\n'
        data = []
        headers = ["ACCOUNT", "DATE", "PARTNER", "LABEL", "ANALYTIC", "DEBIT", "CREDIT"]
        total_debit = 0
        total_credit = 0
        for line in self.line_ids:
            total_debit+=line.debit
            total_credit+=line.credit
            data.append([
                line.account_id.name,
                move_date,
                self.partner_id.name or '',
                line.name,
                line.analytic_tag_ids.mapped('name') or '',
                self.ph_format_currency_amount(line.debit),
                self.ph_format_currency_amount(line.credit),
                ])
        data.append([
            '',
            '',
            '',
            '',
            '',
            self.ph_format_currency_amount(total_debit),
            self.ph_format_currency_amount(total_credit),
            ])

        tabulate_body  = tabulate(data,headers=headers,  tablefmt="grid")
        res+=tabulate_body
        res+='\n'
        return res

        

    def act_url_download_account_move_txt(self):
        return {
                'type': 'ir.actions.act_url',
                'url': '/download_journal_entry_txt?id='+str(self.id),
                'target': 'new',
            }
