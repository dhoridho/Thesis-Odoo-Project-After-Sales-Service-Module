import time
from operator import itemgetter
from odoo import netsvc
from odoo import fields, models
# from tools.misc import currency
from tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
# import dateTime
# from dateTime import RelativeDateTime, now, DateTime, localtime
from odoo.osv import osv
from odoo.tools import config
import string
from datetime import timedelta
import calendar




class agent_commission_invoice(models.Model):
    _name = "agent.commission.invoice"
    _description = "Agent Commision Invoice"
    
    def create(self, cr, uid, vals, context=None): 
        # function overwrites create method and auto generate request no. 
        res = super(agent_commission_invoice, self).create(cr, uid, vals, context=context)
        commission = self.create_commission(cr,uid,res)
        # print(res,"res",vals,"vals===============")
        if commission:
            req_no = self.pool.get('ir.sequence').get(cr,uid,'agent.commission.invoice'),
            # print(req_no,"req_no")
            vals['name'] = req_no[0]
            self.write(cr,uid,[res],{'name':req_no[0]})
        else:
            raise osv.except_osv(_("Warnning"),_("No Commission Line for this Agent !!!"))
    
        return res
    
    
    def check_obj (self,cr,uid,banquet_obj_id):
        # search for the book_id, if present already
        flag = 0
        quot_objj = self.pool.get('agent.commission.invoice.line').search(cr,uid,[('book_id', '=',banquet_obj_id)])
        # print("quot_objj********",quot_objj)
        for objj in quot_objj :
            try :
                objj_browse = self.pool.get('agent.commission.invoice.line').browse(cr,uid,objj)
                # print(objj_browse.commission_line_id.id, "objj_browse")
                
                obj_id = objj_browse.commission_line_id.id
                try :
                    if obj_id :
                        objj_state = self.pool.get('agent.commission.invoice').browse(cr,uid,obj_id)
                        # print(objj_state.state, "objj_state.state")
                        if objj_state.state == "draft" or objj_state.state == "confirm" :
                            flag = 1
                    else :
                        print("No record++++++")
                except :
                    print("an error")
                
            except :
                print("No commission_line_id")
                
        if flag == 1:
            return False
        else :
            return True

    
    def create_commission(self,cr,uid,my_id):
        result = {}
        obj = self.browse(cr,uid,my_id)
        # print("obj",obj)
        quot_obj = self.pool.get('banquet.quotation').search(cr,uid,[('via', '=','agent'),('agent_id', '=',obj.partner_id.id),('state', '=','done'),('invoiced', '=',False)])
        # print("quot_obj",quot_obj)
        
        banquet_list = []
        if quot_obj:
            for banq_id in quot_obj:
                banquet_obj = self.pool.get('hotel.reservation').search(cr,uid,[('banq_bool', '=',True),('banquet_id', '=',banq_id),('state', '=','done')])
                # print(banquet_obj,"banquet_obj")
                if banquet_obj:
                    banquet_obj_id = banquet_obj[0]
                    k = self.check_obj (cr, uid,banquet_obj_id)
                    if k :
                        # print(k, "K***")
                        banquet_list.append(banquet_obj[0])
                        # print()
                    else :
                        print("No K...")
                    #banquet_list.append(banquet_obj[0]) 
        # print(banquet_list,"banquet_list")
        line_data = False
        if banquet_list:
            for banq in banquet_list:
                banq_browse = self.pool.get('hotel.reservation').browse(cr,uid,banq)
                # print(banq_browse,"banq_browse")
                    
                com_amt = 0.0
                com_amt = (float(banq_browse.total_cost1) * obj.commission_percentage ) / 100
                # print("comm_amt",com_amt)
                dict = {
                    'name':banq_browse.name,
                    'book_id':banq_browse.id,
                    'partner_id':banq_browse.partner_id.id,
                    'tour_cost':banq_browse.total_cost1,
                    'commission_amt':com_amt,
                    #added
                    'commission_percentage':obj.commission_percentage,
                    'commission_line_id':my_id,
                    }
                # print("dict",dict)
                line_data = True
                self.pool.get('agent.commission.invoice.line').create(cr,uid,dict)
            if line_data:
                return True
            else:
                return False
        else:
            return False
    
    
    def _get_total_amt(self,cr,uid,ids,args1,args2,context=None):
        res = {}
        total = 0
        for obj in self.browse(cr, uid, ids):
            for i in range (0,len(obj.commission_line)):
                total = total + obj.commission_line[i].commission_amt
            res[obj.id] = total 
        return res
    
    
    _columns = {
                "name":fields.char("Agent Commission ID",readonly=True),
                "current_date":fields.date("Date",required=True,readonly=True, states={'draft':[('readonly',False)]}),
                "partner_id":fields.many2one("res.partner","Agent",required=True,readonly=True, states={'draft':[('readonly',False)]}),
                #'commission_line': fields.one2many('agent.commission.invoice.line', 'commission_line_id', 'Invoice Lines',readonly=True),
                'commission_line': fields.one2many('agent.commission.invoice.line', 'commission_line_id', 'Invoice Lines'),
                'agent_invoice_ids': fields.many2many('account.move','tour_agent_invoice_rel', 'tour_agent_id', 'invoice_id', 'Agent Invoices',readonly=True),
                'state':fields.selection([
                                            ('draft', 'Draft'),
                                            ('confirm','Confirmed'),
                                            ('invoiced', 'Invoiced'),
                                            ('done', 'Done'),
                                            ('cancel', 'Canceled'),
                                            ], 'Status',readonly=True),
                
                "commission_percentage":fields.float("Commission %",required=True,readonly=True,  states={'draft':[('readonly',False)]}),
                'total_amt':fields.function(_get_total_amt, method=True, type="float", string="Total", store=True),
                'recv_acc': fields.property('account.account', type='many2one',string="Expense Account", method=True,
                            required=True,readonly=True, states={'draft':[('readonly',False)]}),
                'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', required=True,readonly=True, states={'draft':[('readonly',False)]})
                } 
    
    
    _defaults = {
                 'state':lambda * a: 'draft',
                 'current_date' : lambda *args:datetime.now().strftime('%Y-%m-%d')
                 }
    
    def on_change_currency_id(self, cr, uid, ids, pricelist_id):
        if (pricelist_id) :
            # print("pricelist_id :", pricelist_id)
            p = self.pool.get('res.currency').browse(cr,uid,pricelist_id).name
            # print("p :", p)
            
            
        else:
            print("No Prielist Id.................")
    
    
    def on_change_partner_id(self,cr,uid,ids,partner_id):
        result = {}
        obj = self.pool.get('res.partner').browse(cr,uid,partner_id)
        # print("obj==========1111111111=======",obj,obj.commission)
        if obj.commission and partner_id:
            # print("fffffffffffff")
            result['commission_percentage'] = obj.commission
            result['pricelist_id'] = obj.property_product_pricelist.id
        if partner_id and not obj.commission:
            # print("eeeeeeeeeeeeeee")
            raise osv.except_osv(_("Warnning"),_("No Commission Percentage is defined for this Agent. Please Configure First !!!"))
        # print(result,"result")
        if ids:
            raise osv.except_osv(_("Warning"),_("Cannot change agent at this stage."))
        return {'value': result}
    
    
    
    def confirm_commission(self, cr, uid, ids, *args):
        for obj in self.browse(cr,uid,ids):
            if not obj.commission_line:
                raise osv.except_osv(_("Warning"),_("No Commission line for this Agent."))
            else :
                
                self.write(cr, uid, ids, {'state':'confirm'})
        return True
    
    
    def done(self, cr, uid, ids, *args):
        for obj in self.browse(cr,uid,ids):
            for invoice in obj.agent_invoice_ids:
                if invoice.invoice_payment_state != 'paid':
                    raise osv.except_osv(_("Warning"),_("Invoice is not Paid Yet."))
        self.write(cr, uid, ids, {'state':'done'})
        return True
    
    
    def make_commission_invoice(self, cr, uid, ids, *args):
#        for obj in self.browse(cr,uid,ids):
        for obj in self.browse(cr,uid,ids):
            
            acc_id = obj.partner_id.property_account_payable.id
                 
#            address_invoice_id = self.pool.get('res.partner.address').search(cr,uid,[('partner_id','=',obj.partner_id.id),('type','=','invoice')])
#            if not address_invoice_id:
#                address_invoice_id = self.pool.get('res.partner.address').search(cr,uid,[('partner_id','=',obj.partner_id.id)])
#            if not address_invoice_id:
#                raise osv.except_osv(_("Warnning"),_("Address is not found in  "))
            
            journal_obj = self.pool.get('account.journal')
            journal_ids = journal_obj.search(cr, uid, [('type', '=','purchase')], limit=1)
            type = 'in_invoice' 
            p_name = self.pool.get('res.currency').browse(cr,uid,obj.pricelist_id.id).name
            inv = {
                        'name': obj.name,
                        'origin': obj.name,
                        'type': type,
                        'reference': "Commission Invoice",
                        'account_id': acc_id,
                        'partner_id': obj.partner_id.id,
                        'currency_id': self.pool.get('res.currency').search(cr, uid, [('name', '=',p_name)])[0],#
                        'journal_id': len(journal_ids) and journal_ids[0] or False,
                        'amount_tax':0,
                        'amount_untaxed':obj.total_amt,
                        'amount_total':obj.total_amt,
                        }
            # print("inv",inv)
            inv_id = self.pool.get('account.move').create(cr, uid, inv)
            il = {
                    'name': obj.name,
                    'account_id': obj.recv_acc.id,
                    'price_unit':obj.total_amt, 
                    'quantity': 1.0,
                    'uos_id':  False,
                    'origin':obj.name,
                    'invoice_id':inv_id,
                    }
            # print("il",il)
            self.pool.get('account.move.line').create(cr, uid, il,)
            for banq in obj.commission_line:
                self.pool.get('banquet.quotation').write(cr, uid, banq.book_id.banquet_id.id,{'invoiced':True})
            cr.execute('insert into tour_agent_invoice_rel(tour_agent_id,invoice_id) values (%s,%s)', (obj.id, inv_id))
        self.write(cr, uid, ids, {'state':'invoiced'})
        return True
    


class agent_commission_invoice_line(osv.osv):
    _name = "agent.commission.invoice.line"
    _description = " Commision Invoice Line"
    _columns = {
                "name":fields.char("Name",required=True),
                "book_id":fields.many2one("hotel.reservation","Booking Ref.",required=True),
                "partner_id":fields.many2one("res.partner","Customer Name",required=True),
                'tour_cost':fields.float('Total Cost', required=True,),
                #added
                "commission_percentage" : fields.float('Commission %', required=True),
                "commission_amt":fields.float("Commission Amount",required=True),
                "commission_line_id":fields.many2one("agent.commission.invoice","Commission ID"),
                #"can_be_invoiced":fields.boolean("Invoice"),
                }  
    
    
    def create(self, cr, uid, vals, context=None):
        # print(vals,"valssssssssssssssss")
        if 'name' not in vals:
            raise osv.except_osv(_("Warning"),_("You cann't create commission line manually."))
        return super(agent_commission_invoice_line, self).create(cr, uid, vals, context=context)    

    
    def on_change_tour_book_id(self,cr,uid,ids,book_id):
        result = {}
        obj = self.pool.get('hotel.reservation').browse(cr,uid,book_id)
        result['name'] = obj.name
        return {'value': result}
    
    
    def on_change_commission_amt(self,cr,uid,ids,tour_cost, commission_percentage) :
        result={}
        com_amt = 0.0
        com_amt = (float(tour_cost) * commission_percentage ) / 100
        # print("comm_amt",com_amt)
        result['commission_amt'] = com_amt
        
        return {'value' : result}
