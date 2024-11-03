# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from datetime import datetime
from odoo.exceptions import UserError

class ContractExpiredReport(models.AbstractModel):
    _name = 'report.property_rental_mgt_app.template_report'
    _description = "Contract Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        get_to = data['form']['to_date']
        get_from = data['form']['from_date'] 
        docs = []
        
        to_date = datetime.strptime(get_to, '%Y-%m-%d').date()
        from_date = datetime.strptime(get_from, '%Y-%m-%d').date()
        contract_obj  = self.env['contract.details'].search([('to_date','>=',from_date),('to_date','<=',to_date),('to_date','<',fields.Date.today())])
        if not contract_obj:
            raise UserError(_("Expired Contract is not available in this Date Range."))

        for each in contract_obj:
            docs.append({
                'code':each.name,
                'name':each.contract_id.name,
                'from_date':each.from_date,
                'to_date':each.to_date,
                'property_id':each.property_id.name,
                'rent_price':each.rent_price,
                'renewal_date':each.renewal_date,
                'deposite':each.deposite,
                })
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'report_date':fields.Date.today(),
            'docs': docs,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: