# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class PosPaymentReport(models.AbstractModel):
    _name = "report.equip3_pos_report.report_pos_payment"
    _description = "POS Payment Report"
    
    def _get_report_values(self, docids, data=None,sessions=False):
        """ Serialise the orders of the day information

        params: pos_payment_rec.start_dt, pos_payment_rec.end_dt string representing the datetime of order
        """
        config_obj = self.env['pos.config']
        domain_config = []

        Report = self.env['ir.actions.report']
        top_selling_report = Report._get_report_from_name('equip3_pos_report.report_profit_loss')       
        top_selling_rec = self.env['pos.payment.wizard'].browse(docids) 
        branch_data = top_selling_rec.branch_id or False
        company_data = top_selling_rec.company_id or False

        if branch_data:
            domain_config+= [('pos_branch_id','=',branch_data.id)]
            name_branch = branch_data.name
        if company_data:
            domain_config+= [('company_id','=',company_data.id)]

        pos_configs = config_obj.search(domain_config)  

        orders = self.env['pos.order'].search([
                ('date_order', '>=', top_selling_rec.start_dt),
                ('config_id','in', pos_configs.ids),
                ('date_order', '<=', top_selling_rec.end_dt),
                ('state', 'in', ['paid','invoiced','done']),
            ])
        st_line_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
        if st_line_ids:
            self.env.cr.execute("""
                SELECT ppm.name, sum(amount) total
                FROM pos_payment AS pp,
                    pos_payment_method AS ppm
                WHERE  pp.payment_method_id = ppm.id 
                    AND pp.id IN %s 
                GROUP BY ppm.name
            """, (tuple(st_line_ids),))
            payments = self.env.cr.dictfetchall()
        else:
            payments = []   
                
        prod_data ={}
        top_list={}
        for odr in orders:      
            for line in odr.lines:                  
                product = line.product_id.id
                disc = 0
                if line.discount > 0 :
                    disc =(line.price_unit * line.qty * line.discount)/100

                if product in prod_data:
                    old_qty = prod_data[product]['qty']
                    old_price = prod_data[product]['price_subtotal']
                    old_discount = prod_data[product]['discount']
                
                    prod_data[product].update({
                        'qty' :  float(old_qty+line.qty),
                        'price_subtotal' :  float(old_price+line.price_subtotal_incl),
                        'discount': float(old_discount + disc),
                    })
                else:   
                    prod_data.update({ product : {
                        'product_id':line.product_id.id,
                        'product_name':line.product_id.name,
                        'uom_name':line.product_id.uom_id.name,
                        'price_unit':line.price_unit,                       
                        'price_subtotal':line.price_subtotal_incl,                      
                        'qty' : float(line.qty),
                        'discount':float(disc),                 
                    }})
        top_list=(sorted(prod_data.values(), key=lambda kv: kv['qty'], reverse=True))
                
        return {
            'currency_precision': 2,
            'doc_ids': docids,
            'doc_model': 'pos.top.selling.wizard',
            'start_dt' : top_selling_rec.start_dt,
            'end_dt' : top_selling_rec.end_dt,
            'prod_data':top_list,
            'payments': payments,
        }
    

    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
