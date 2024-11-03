from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta


class AccountMove(models.Model):
    _inherit = 'account.move'

    property_maintenance_id = fields.Many2one(comodel_name='property.maintanance', string='Property Maintenance')

    @api.model
    def create(self, vals):
        res = super(AccountMove,self).create(vals)
        if vals.get("agreement_id"):
            agreement = self.env["agreement"].browse(vals.get("agreement_id"))
            res.property_id = agreement.property_id.id

            if agreement.property_id and agreement.property_id.property_book_for == 'rent':
                renter_history_obj = self.env["renter.history"].sudo()

                if agreement.recurring_invoice_id.recurring_type == 'daily':
                    duration = str(agreement.duration_daily) + ' Days'
                elif agreement.recurring_invoice_id.recurring_type == 'monthly':
                    duration = str(agreement.duration_monthly) + ' Months'
                elif agreement.recurring_invoice_id.recurring_type == 'yearly':
                    duration = str(agreement.duration_yearly) + ' Years'
                

                renter_history_obj.create({
                    'reference': agreement.name,
                    'property_id': agreement.property_id.id,
                    'date': vals.get("invoice_date"),
                    'from_date': vals.get("invoice_date"),
                    'to_date': vals.get("invoice_date_due") + relativedelta(days=1),
                    'rent_price': res.amount_total,
                    'contract_month': duration,
                    'deposite': res.amount_total,
                    'invoice_id': res.id,
                    'state': 'avl' if res.state == 'draft' else 'reserve',
                    'is_invoice': 1,

                    })
        return res

    def write(self, vals):
        res = super(AccountMove,self).write(vals)
        context = self._context
        if context.get("active_model") == "product.product":
            for rec in self.filtered(lambda x: x.agreement_id.property_id and x.agreement_id.property_id.property_book_for == 'rent'):
                history = self.env["renter.history"].search([('invoice_id','=',rec.id)],limit=1)
                if history and history.invoice_id.id == rec.id:
                    if rec.state == 'draft':
                        state = 'avl'
                    elif rec.state == 'posted':
                        state = 'reserve'
                    elif rec.state == 'cancel':
                        state = 'cancel'

                    history.write({
                        'reference': rec.agreement_id.name,
                        'from_date': rec.invoice_date,
                        'to_date': rec.invoice_date_due + relativedelta(days=1),
                        'rent_price': rec.amount_total,
                        'deposite': rec.amount_total,
                        'state': state,
                        })

        return res

# Global function for commission calculation
def commission_calculation(args_list):
	commi_data = {}
	for user_id,comm_amount in args_list:
		total_commission = commi_data.get(user_id,0) + comm_amount
		commi_data[user_id] = total_commission
	return list(commi_data.items())

class AccountPayment(models.Model):
    _inherit = 'account.payment'
    
    def action_post(self):

        active_id = self._context.get('active_id')
        invoice_id = self.env['account.move'].browse(active_id)
        agreement = self.env["agreement"].search([('id','=',invoice_id.agreement_id.id)])
        if agreement:
            for each in agreement:
                property_id = each.property_id.id
                if property_id:
                    property = self.env["product.product"].search([('id','=',property_id)])
                    if property.user_commission_ids:
                        for comm in property.user_commission_ids:
                            if comm.user_id.id == agreement.assigned_user_id.id:
                                values = {}
                                values.update({
                                    'pay_reference':invoice_id.payment_reference,
                                    'payment_origin':self.name,
                                    'user_id' :comm.user_id.id,
                                    'property_id':property_id,
                                    'percentage':comm.percentage,
                                    'commission':(invoice_id.amount_total * comm.percentage)/100,
                                    'inv_pay_source':invoice_id.name, 
                                    'invoice_id':invoice_id.id
                                    })
                                commission_id=self.env['commission.line'].create(values)
                                commission_id.write({'name':self.env['ir.sequence'].next_by_code('commission.line') or _('New')})
        res = super(AccountPayment, self).action_post()
        return res

    def generate_commission_worksheet(self):
        commission_obj = self.env['commission.line'].search([('is_created_worksheet','!=',True)])
        payment_obj = self.env['account.payment'].search([('state','=','posted')])
        for each in commission_obj:
            for payment in payment_obj:
                if each.inv_pay_source == payment.ref or each.pay_reference == payment.ref and each.invoice_id.invoice_origin == each.property_id.name:
                    values = {}
                    each.write({'is_created_worksheet':True})
                    values.update({'user_id':each.user_id.id,'percentage':each.percentage,'commission':each.commission, 'payment_origin':payment.name,'invoice_origin':each.inv_pay_source,'property_origin':each.property_id.name, 'property_id':each.property_id.id})
                    

                    self.env['merge.worksheet'].create(values)

            worksheet_obj=self.env['merge.worksheet'].search([])
            user_list = []
            same_user = []
            unique_list = []
            unique_user_list = []
            data_list2 = [] 
            for each in worksheet_obj:
                comm_dict ={}
                comm_dict = {'user_id':each.user_id.id,'percentage':each.percentage,'commission':each.commission, 'property_origin':each.property_origin, 'invoice_origin':each.invoice_origin,'payment_origin':each.payment_origin}
                data_list2.append(comm_dict)
                user_list.append([each.user_id.id,each.commission])
            same_user = commission_calculation(user_list)
            for val in same_user:
                unique_list.append(list(val))

            w_list = []
            for each in worksheet_obj:
                for val in unique_list:
                    if val[0] == each.user_id.id:
                        if each.user_id.id not in unique_user_list:
                            unique_user_list.append(each.user_id.id)
                            commission_values = {}
                            commission_values.update({'user_id':each.user_id.id, 'commission':val[1]})
                            worksheet_id = self.env['commission.worksheet'].create(commission_values)
                            worksheet_id.write({'name':self.env['ir.sequence'].next_by_code('commission.worksheet') or _('New')})
                            w_list.append(worksheet_id.id)
                each.unlink()
            for w in w_list:
                wk_id = self.env['commission.worksheet'].browse(w)
                comm_work_list = []
                for d in data_list2:
                    user_id = self.env['res.users'].browse(d['user_id'])
                    if wk_id.user_id.id == user_id.id:
                        comm_line_data = {'commission':d['commission'], 'percentage':d['percentage'], 'property_origin':d['property_origin'], 'invoice_origin':d['invoice_origin'], 'payment_origin':d['payment_origin']}
                        comm_work_list.append((0, 0,comm_line_data))
                wk_id.write({'comm_work_line_ids':comm_work_list})
        return True


class RenterHistoryInherit(models.Model):
    _inherit = 'renter.history'

    contract_month = fields.Char(string='Contract Duration')