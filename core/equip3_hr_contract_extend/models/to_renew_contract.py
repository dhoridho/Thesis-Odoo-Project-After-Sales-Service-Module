from datetime import timedelta, datetime

from odoo import models, fields, api



class HashMicroToRenewContract(models.TransientModel):
    _name = 'to.renew.contract'
    name = fields.Char()


    def get_list(self):
        contract_list = []
        global_setting = self.env['expiry.contract.notification'].search([])
        now = datetime.strptime(str(datetime.now()), "%Y-%m-%d %H:%M:%S.%f")
        month_days = global_setting.month * 30 if global_setting.month > 0 else 0
        total_days = global_setting.days + month_days
        to_renew_contract = self.env['hr.contract'].search([('date_end', '=', now.date() + timedelta(days=total_days))])
        if to_renew_contract:
            list = [data.id for data in to_renew_contract]
            contract_list.extend(list)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Contract To Renew',
            'res_model': 'hr.contract',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', contract_list)]
        }