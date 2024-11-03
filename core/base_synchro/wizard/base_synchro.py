# See LICENSE file for full copyright and licensing details.

import logging
import threading
import time
import json
from xmlrpc.client import ServerProxy
from odoo import api, fields, models, SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from odoo.tools import format_datetime
import pytz, logging, requests, json, sys, traceback
from datetime import datetime, date

_logger = logging.getLogger(__name__)


class RPCProxyOne(object):
    def __init__(self, server, ressource):
        """Class to store one RPC proxy server."""
        self.server = server
        if server.server_url_server:
            local_url = "%s/xmlrpc/common" % (server.server_url_server)
            rpc = ServerProxy(local_url)
            self.uid = rpc.login(server.server_db, server.login, server.password)
            local_url = "%s/xmlrpc/object" % (server.server_url_server)
            self.rpc = ServerProxy(local_url)
            self.ressource = ressource
        else:
            local_url = "http://%s:%d/xmlrpc/common" % (
                server.server_url,
                server.server_port,
            )
            rpc = ServerProxy(local_url)
            self.uid = rpc.login(server.server_db, server.login, server.password)
            local_url = "http://%s:%d/xmlrpc/object" % (
                server.server_url,
                server.server_port,
            )
            self.rpc = ServerProxy(local_url)
            self.ressource = ressource
        # raise ValidationError("jasdhasgdjas")

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.rpc.execute(
            self.server.server_db,
            self.uid,
            self.server.password,
            self.ressource,
            name,
            *args
        )

class RPCProxy(object):
    """Class to store RPC proxy server."""

    def __init__(self, server):
        self.server = server

    def get(self, ressource):
        return RPCProxyOne(self.server, ressource)


class BaseSynchro(models.TransientModel):
    """Base Synchronization."""

    _name = "base.synchro"
    _description = "Base Synchronization"

    @api.depends("server_url")
    def _compute_report_vals(self):
        self.report_total = 0
        self.report_create = 0
        self.report_write = 0

    server_url = fields.Many2one(
        "base.synchro.server", "Server URL", required=True
    )
    user_id = fields.Many2one(
        "res.users", "Send Result To", default=lambda self: self.env.user
    )
    report_total = fields.Integer(compute="_compute_report_vals")
    report_create = fields.Integer(compute="_compute_report_vals")
    report_write = fields.Integer(compute="_compute_report_vals")

    @api.model
    def create_in_query(self,json_value,model):
        json_value = json_value.replace('|', '/')
        value = json.loads(json_value)

        for key, val in value.items():
            value[key] = None if val is False else val

        # Ensure consistent ordering of columns and their corresponding values
        sorted_columns = sorted(value.keys())
        sorted_values = [value[col] for col in sorted_columns]

        columns = ', '.join(sorted_columns)
        placeholders = ', '.join(['%s'] * len(value))
        query = f"INSERT INTO {model.replace('.','_')} ({columns}) VALUES ({placeholders})"
        self.env.cr.execute(query, tuple(sorted_values))

        query = f"select id from {model.replace('.','_')} order by id desc limit 1"
        self.env.cr.execute(query)
        new_id = self.env.cr.fetchone()[0]
        self.run_hr_onchange_compute_method(model, new_id)
        self.env.cr.commit()

        return new_id
    
    def run_hr_onchange_compute_method(self, model, id):
        new_record = self.env[model].browse([id])
        if model == "hr.payslip":
            new_record.base_sync = True
            new_record.onchange_employee()
            new_record.confirm_compute_sheet()
            new_record.compute_sheet()

            # set sequence number to draft
            new_record.write({'number' : 'New'})
            sequence = self.env['ir.sequence'].search([('code', '=', 'salary.slip')])
            if not sequence.use_date_range:
                new_seq_num = self.env['ir.sequence'].browse([sequence.id]).write({'number_next_actual' : sequence.number_next_actual - 1})
            else:
                date_range = sequence.date_range_ids.sorted('create_date', reverse=True)[0]
                new_seq_num = self.env['ir.sequence.date_range'].browse([date_range.id]).write({'number_next_actual' : date_range.number_next_actual - 1})

        elif model == "hr.expense.sheet":
            new_record.onchange_approver_user()
        elif model == "vendor.deposit" and new_record.is_cash_advance:
            new_record.onchange_approver_user()
    
    def update_state_to_draft(self, value):
        if "state" in value:
            value["state"] = "draft"
        
        return value

    def update_name_number_doc(self,value,model):
        models_to_rename_new = [
            "sale.order",
            "material.request",
            "internal.transfer",
            "invoice.recurring",
            "account.voucher",
            "customer.deposit",
            "vendor.payment.request",
            "account.multipayment",
            "receipt.voucher",
            "vendor.deposit",
            "account.internal.transfer",
            "account.pettycash",
            "account.pettycash.voucher.wizard",
            "stock.scrap.request",
            "stock.warehouse.orderpoint",
        ]

        models_to_rename_slash = [
            "purchase.order",
            "purchase.request",
            "purchase.requisition",
            "purchase.agreement",
            "stock.picking",
            "stock.inventory",
            "dev.rma.rma",
        ]

        if model in models_to_rename_new:
            value['name'] = 'New'

        if model in models_to_rename_slash:
            value['name'] = '/'
        
        if model == 'hr.expense.sheet':
            value['seq_name'] = 'New'
        
        if model == 'hr.payslip':
            value["number"] = 'New'

        return value

    def remove_exceptional_fields(self, value, model):
        list_model_remove_move_id = ["vendor.deposit", "hr.payslip.run", "hr.payslip"]
        if model in list_model_remove_move_id:
            if "move_id" in value:
                del value["move_id"]
            if "number" in value:
                del value["number"]
        
        return value

    def set_value_name(self, value, model):
        models_using_seq_name = ["hr.expense.sheet"]
        models_using_number = ["account.pettycash", "account.voucher"]
        value_name = False
        if "name" in value:
            value_name = value["name"]

        if model in models_using_seq_name and "seq_name" in value:
            value_name = value["seq_name"]

        if model in models_using_number and "number" in value:
            value_name = value["number"]
        
        return value_name
    
    def set_conditional_sequence_code(self, value, model, sequence_code):
        if model == "vendor.deposit":
            if 'is_cash_advance' in value and value['is_cash_advance']:
                sequence_code = 'hr.cash.advance'
        
        return sequence_code

    @api.model
    def synchronize(self, server, object):
        list_id = []
        pool = self
        sync_ids = []
        pool1 = RPCProxy(server)
        pool2 = pool
        dt = object.synchronize_date
        module = pool1.get("ir.module.module")
        model_obj = object.model_id.model
        module_id = module.search(
            [("name", "ilike", "base_synchro"), ("state", "=", "installed")]
        )
        module_move = False
        value_line_ids = False
        acc_voucher_seq_code = 'seq.account.voucher.oin'
        acc_multipayment_seq_code = 'vendor.account.multipayment'
        acc_recurring_invoice_seq_code = 'recurring.in.invoice.seq'
        vendor_deposit_seq_code = 'vendor.deposit'
        if not module_id:
            raise ValidationError(
                _(
                    """If your Synchronization direction is/
                          download or both, please install
                          "Multi-DB Synchronization" module in targeted/
                        server!"""
                )
            )
        if object.action in ("d", "b"):
            sync_ids = pool1.get("base.synchro.obj").get_ids(
                model_obj, dt, eval(object.domain), {"action": "d"}
            )

        if object.action in ("u", "b"):
            _logger.debug(
                "Getting ids to synchronize [%s] (%s)",
                object.synchronize_date,
                object.domain,
            )
            sync_ids += pool2.env["base.synchro.obj"].get_ids(
                model_obj, dt, eval(object.domain), {"action": "u"}
            )
        sorted(sync_ids, key=lambda x: str(x[0]))
        for dt, id, action in sync_ids:
            value_name = False
            key_name = 'name'
            destination_inverted = False
            if action == "d":
                pool_src = pool1
                pool_dest = pool2
            else:
                pool_src = pool2
                pool_dest = pool1
                destination_inverted = True
            fields = []
            if not destination_inverted:
                value = pool_src.get(object.model_id.model).read([id], fields)[0]
            else:
                name_table_query = object.model_id.model.replace('.','_')
                query = f"SELECT * FROM {name_table_query} WHERE id = %s"
                self._cr.execute(query,
                    (id,)
                )
                query_record = self.env.cr.fetchall()[0]

                query = """ SELECT column_name  FROM information_schema.columns  WHERE table_name = %s"""
                self._cr.execute(query, (name_table_query,))
                query_field = self._cr.fetchall()
                count = 0
                value = {}
                for field in query_field:
                    value_set = query_record[count]
                    if isinstance(value_set, datetime):
                        value_set = value_set.strftime("%Y-%m-%d %H:%M:%S")
                    if isinstance(value_set, date):
                        value_set = value_set.strftime("%Y-%m-%d")
                    value[field[0]] = value_set
                    count+=1


            if "create_date" in value:
                del value["create_date"]
            if "write_date" in value:
                del value["write_date"]
            if "id" in value:
                del value["id"]

            if str(model_obj) == 'sale.order()':
                value['base_sync'] = True

                if 'sale_hidden_compute_field' in value:
                    del value["sale_hidden_compute_field"]
                if 'sale_fully_paid' in value:
                    del value["sale_fully_paid"]
                if 'sale_partially_paid' in value:
                    del value["sale_partially_paid"]
                if 'sale_fully_delivered' in value:
                    del value["sale_fully_delivered"]
                if 'sale_partially_delivery' in value:
                    del value["sale_partially_delivery"]

                if 'date_confirm' in value:
                    del value["date_confirm"]
                if 'sale_state' in value:
                    del value["sale_state"]

                if 'sale_state_1' in value:
                    del value["sale_state_1"]
                if 'state_2' in value:
                    del value["state_2"]
                if 'revised_state' in value:
                    del value["revised_state"]
                if 'approval_matrix_state' in value:
                    del value["approval_matrix_state"]
                if 'approval_matrix_state_1' in value:
                    del value["approval_matrix_state_1"]

                if 'procurement_group_id' in value:
                    del value["procurement_group_id"]

            elif str(model_obj) == 'account.move()':
                if "kitchen_id" in value:
                    del value["kitchen_id"]
                if "stock_move_id" in value:
                    del value["stock_move_id"]

            elif str(model_obj) == 'stock.picking()':
                if "picking_type_id" in value:
                    picking_type_id = value.pop("picking_type_id")
                    value["picking_type_id"] = picking_type_id
                if "group_id" in value:
                    del value["group_id"]

            elif str(model_obj) == 'invoice.recurring()':
                value['base_sync'] = True

            elif str(model_obj) == 'account.voucher()':
                value['base_sync'] = True

            elif str(model_obj) == 'customer.deposit()':
                value['base_sync'] = True
                if 'deposit_move_id' in value:
                    del value['deposit_move_id']

            elif str(model_obj) == 'vendor.payment.request()':
                value['base_sync'] = True

            elif str(model_obj) == 'vendor.deposit()':
                value['base_sync'] = True
                if 'move_id' in value:
                    del value['move_id']

            elif str(model_obj) == 'account.multipayment()':
                value['base_sync'] = True
                if "partner_type" in value and "payment_type" in value:
                    if value["partner_type"] == "customer":
                        if value["payment_type"] == "payment":
                            acc_multipayment_seq_code = 'customer.account.multipayment'
                        else:
                            acc_multipayment_seq_code = 'receipt.giro'
                    else:
                        if value["payment_type"] == "giro":
                            acc_multipayment_seq_code = 'payment.giro'

            elif str(model_obj) == 'receipt.voucher()':
                value['base_sync'] = True

            elif str(model_obj) == 'account.internal.transfer()':
                value['base_sync'] = True

            elif str(model_obj) == 'account.pettycash()':
                value['base_sync'] = True

            elif str(model_obj) == 'material.request()':
                value['base_sync'] = True

            elif str(model_obj) == 'internal.transfer()':
                value['base_sync'] = True

            elif str(model_obj) == 'dev.rma.rma()':
                value['base_sync'] = True

            elif str(model_obj) == 'account.pettycash.voucher.wizard()':
                value['base_sync'] = True

            elif str(model_obj) == 'stock.inventory()':
                value['base_sync'] = True

            elif str(model_obj) == 'stock.landed.cost()':
                value['base_sync'] = True

            elif str(model_obj) == 'stock.scrap.request()':
                value['base_sync'] = True

            elif str(model_obj) == 'stock.warehouse.orderpoint()':
                value['base_sync'] = True
            elif str(model_obj) == 'purchase.order()' or str(model_obj) == 'purchase.request()' or str(model_obj) == 'purchase.requisition()' or str(model_obj) == 'purchase.agreement()':
                self.improve_value_parent_purchase(value,str(model_obj))

            elif object.model_id.model in ('pos.session', 'pos.order', 'pos.order.line'):
                value['base_sync'] = True
                value['base_sync_origin_id'] = id

                if object.model_id.model == 'pos.session':
                    value['rescue'] = True
                    if 'name' in value:
                        del value['name']

                elif object.model_id.model == 'pos.order.line':
                    new_order = pool_dest.get('pos.order').search_read([('base_sync_origin_id', '=', value['order_id'][0])], fields=['id'], order='id desc', limit=1)
                    value['order_id'] = new_order and new_order[-1]['id'] or False

                elif object.model_id.model == 'pos.order':
                    new_session = pool_dest.get('pos.session').search_read([('base_sync_origin_id', '=', value['session_id'][0])], fields=['id'], order='id desc', limit=1)
                    value['session_id'] = new_session and new_session[-1]['id'] or False

                    order = self.env['pos.order'].browse(id)
                    payment_data = []
                    for payment in order.payment_ids:
                        payment_data += [{
                            'amount': order._get_rounded_amount(payment.amount),
                            'name': payment.name,
                            'payment_method_id': payment.payment_method_id.id,
                        }]
                    value['base_sync_payment_data'] = json.dumps(payment_data, default=str)

            if str(model_obj) not in ('purchase.order()','purchase.request()','purchase.requisition()','purchase.agreement()'):
                for key, val in value.items():
                    if key == 'name':
                        value_name = val
                        key_name = key

                    if key == 'state':
                        value.update({key : 'draft'})
                    if key == 'state1':
                        value.update({key : 'draft'})
                    if key == 'state2':
                        value.update({key : 'draft'})

                    if str(model_obj) == 'account.move()':
                        if key == 'name':
                            value.update({key : '/'})
                        if key == 'state':
                            value.update({key : 'draft'})
                        if key == 'state1':
                            value.update({key : 'draft'})
                        if key == 'state2':
                            value.update({key : 'draft'})
                    elif str(model_obj) == 'stock.picking()':
                        if key == 'base_sync':
                            value.update({key: True})
                        if key == 'name':
                            value.update({key : '/'})
                        if key == 'state':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'sale.order()':
                        if key == 'name':
                            value.update({key : 'New'})
                        if key == 'state':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'invoice.recurring()':
                        if key == 'name':
                            value.update({key : 'New'})
                        if key == 'state':
                            value.update({key : 'draft'})
                        if key == 'type':
                            if value[key] == 'in_invoice':
                                acc_recurring_invoice_seq_code = 'recurring.out.invoice.seq'

                    elif str(model_obj) == 'account.voucher()':
                        if key == 'number':
                            value.update({key : 'New'})
                            value_name = val
                            key_name = key
                        if key == 'state':
                            value.update({key : 'draft'})
                        if key == 'voucher_type':
                            if value[key] == 'purchase':
                                acc_voucher_seq_code = 'seq.account.voucher.oex'

                    elif str(model_obj) == 'customer.deposit()':
                        if key == 'name':
                            value.update({key : 'New'})
                            value_name = val
                        if key == 'state':
                            value.update({key : 'draft'})
                        if key == 'state1':
                            value.update({key : 'draft'})
                        if key == 'state2':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'vendor.payment.request()':
                        if key == 'name':
                            value.update({key : 'New'})
                            value_name = val
                        if key == 'state':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'account.multipayment()':
                        if key == 'name':
                            value.update({key : 'New'})
                            value_name = val
                        if key == 'state':
                            value.update({key : 'draft'})
                        if key == 'state1':
                            value.update({key : 'draft'})
                        if key == 'state2':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'receipt.voucher()':
                        if key == 'name':
                            value.update({key : 'New'})
                            value_name = val
                        if key == 'state':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'payment.voucher()':
                        if key == 'name':
                            value.update({key : '/'})
                            value_name = val
                        if key == 'state':
                            value.update({key : 'draft'})
                        if key == 'state1':
                            value.update({key : 'draft'})
                        if key == 'state2':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'vendor.deposit()':
                        if key == 'name':
                            value.update({key : 'New'})
                            value_name = val
                        if key == 'state':
                            value.update({key : 'draft'})
                        if key == 'state1':
                            value.update({key : 'draft'})
                        if key == 'state2':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'account.internal.transfer()':
                        if key == 'name':
                            value.update({key : 'New'})
                            value_name = val
                        if key == 'state':
                            value.update({key : 'draft'})
                        if key == 'state1':
                            value.update({key : 'draft'})
                        if key == 'state2':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'account.pettycash()':
                        if key == 'number':
                            value.update({key : 'New'})
                            value_name = val
                            key_name = key
                        if key == 'state':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'account.pettycash.voucher.wizard()':
                        if key == 'name':
                            value.update({key : 'New'})
                            value_name = val
                        if key == 'state':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'material.request()':
                        if key == 'name':
                            value.update({key : 'New'})
                        if key == 'status':
                            value.update({key : 'draft'})
                        if key == 'status1':
                            value.update({key : 'draft'})
                        if key == 'status2':
                            value.update({key : 'draft'})
                        if key == 'status3':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'internal.transfer()':
                        if key == 'name':
                            value.update({key : 'New'})
                        if key == 'state':
                            value.update({key : 'draft'})
                        if key == 'state1':
                            value.update({key : 'draft'})
                        if key == 'state2':
                            value.update({key : 'draft'})
                        if key == 'state3':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'dev.rma.rma()':
                        if key == 'name':
                            value.update({key : '/'})
                        if key == 'state':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'stock.inventory()':
                        if key == 'name':
                            value.update({key : '/'})
                        if key == 'state':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'stock.landed.cost()':
                        if key == 'name':
                            value.update({key : 'New'})
                        if key == 'state':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'stock.scrap.request()':
                        if key == 'name':
                            value.update({key : '/'})
                        if key == 'state':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'stock.warehouse.orderpoint()':
                        if key == 'name':
                            value.update({key : '/'})

                    elif str(model_obj) == 'pos.order()':
                        if key == 'name':
                            value.update({key : '/'})
                        elif key == 'state':
                            value.update({key : 'draft'})

                    elif str(model_obj) == 'pos.session()':
                        if key == 'state':
                            value.update({key : 'opened'})

                    if isinstance(val, tuple):
                        value.update({key: val[0]})
            line_ids = []
            list_field_line = []
            res_value_tmp = {}
            serv = self.server_url
            user = serv.login
            for field in object.avoid_ids:
                if field.name in value:
                    del value[field.name]

            value_name = self.set_value_name(value, object.model_id.model)
            value = self.update_name_number_doc(value,object.model_id.model)
            value = self.remove_exceptional_fields(value, object.model_id.model)
            vendor_deposit_seq = self.set_conditional_sequence_code(value, object.model_id.model, vendor_deposit_seq_code)
            if destination_inverted:
                value['create_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                value['create_uid'] = SUPERUSER_ID
                value['base_sync'] = True
            json_value = json.dumps(value, separators=(',', ':'), ensure_ascii=False)
            json_value = json_value.replace('/', '|')
            
            create_in_query_id = pool_dest.get('base.synchro').create_in_query(json_value,object.model_id.model)
            new_id = create_in_query_id
            if object.field_line:
                if not destination_inverted:
                    res2 = pool_dest.get('res.users').search_read([('login', '=', user)], ['id','name', 'company_id'])
                    comp_id = res2[0]['company_id']
                    res2 = pool_src.get(object.model_id.model).search_read([(key_name, '=', value[key_name])], ['id',key_name, 'company_id'])

                    if not value[key_name] in ['/', 'New']:
                        if len(res2) > 0:
                            continue

                for field_line in object.field_line:
                    value_line_ids = False
                    if not destination_inverted:
                        model_obj = pool_dest.env[field_line.relation]
                        module_move = model_obj
                        value_line_ids = module_move.browse(value[field_line.name]).read(fields)
                    else:
                        name_table_query = field_line.relation.replace('.','_')
                        query = f"SELECT * FROM {name_table_query} WHERE {field_line.relation_field} = %s"
                        self._cr.execute(query,
                            (id,)
                        )
                        query_record = self.env.cr.fetchall()
                        if query_record:
                            query = """ SELECT column_name  FROM information_schema.columns  WHERE table_name = %s"""
                            self._cr.execute(query, (name_table_query,))
                            query_field = self._cr.fetchall()
                            value_line_ids = []
                            for value_line in query_record:
                                count = 0
                                value_line_key = {}
                                for field in query_field:
                                    value_set =  value_line[count]
                                    if isinstance(value_set, datetime):
                                        value_set = value_set.strftime("%Y-%m-%d %H:%M:%S")
                                    if isinstance(value_set, date):
                                        value_set = value_set.strftime("%Y-%m-%d")
                                    value_line_key[field[0]] =value_set
                                    count+=1
                                value_line_key[field_line.relation_field] = create_in_query_id
                                value_line_ids.append(value_line_key)


                    if value_line_ids:
                        line_ids = []
                        if str(module_move) == 'account.voucher.line()':
                            fields.clear()
                        
                        for value_line_id in value_line_ids:

                            value_line_id = self.remove_exceptional_fields(value_line_id, object.model_id.model)

                            if "create_date" in value_line_id:
                                del value_line_id["create_date"]
                            if "write_date" in value_line_id:
                                del value_line_id["write_date"]
                            if "id" in value_line_id:
                                del value_line_id["id"]

                            if destination_inverted:
                                value_line_id['create_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                value_line_id['create_uid'] = SUPERUSER_ID

                            #delete unused field
                            if str(module_move) == 'sale.order()':
                                if "qty_delivered" in value_line_id:
                                    del value_line_id["qty_delivered"]
                                if "state" in value_line_id:
                                    value_line_id["state"] = "draft"

                            if str(module_move) == 'stock.picking()':
                                if "state" in value_line_id:
                                    value_line_id["state"] = "draft"

                                a = value_line_id.pop('product_qty')
                                b = value_line_id.pop('product_uom_qty')
                                value_line_id.pop('group_id')
                                value_line_id.pop('purchase_line_id')
                                value_line_id.update({'quantity_done': 0})
                                value_line_id['product_uom_qty'] = b

                            if str(module_move) == 'stock.move()':
                                a = value_line_id.pop('product_qty')
                                b = value_line_id.pop('product_uom_qty')
                                value_line_id.pop('group_id')
                                value_line_id.pop('purchase_line_id')
                                value_line_id.update({'quantity_done': 0})
                                value_line_id.update({'state': 'draft'})
                                value_line_id['product_uom_qty'] = b


                            if str(model_obj) == 'purchase.order.line()' or str(model_obj) == 'purchase.request.line()' or str(model_obj) == 'purchase.requisition.line()' or str(model_obj) == 'purchase.agreement.line()':
                                self.improve_value_child_purchase(value_line_id,str(model_obj))
                            if 'matrix.line' in str(model_obj):
                                self.improve_value_matrix_line(value_line_id,str(model_obj))
                            #=======================================================
                            for key, val in value_line_id.items():
                                if isinstance(val, tuple):
                                    value_line_id.update({key: val[0]})



                if not destination_inverted:
                    if object.model_id.model == "sale.order.line":
                        if value['product_template_id']:
                            value['product_id'] = value['product_template_id']
                            del value['product_template_id']
                            idnew = pool_dest.env[object.model_id.model].create(value)
                            new_id = idnew.id
                        else:
                            idnew = pool_dest.env[object.model_id.model].create(value)
                            new_id = idnew.id
                    elif object.model_id.model == "stock.move.line":
                        a = value.pop('product_qty')
                        b = value.pop('product_uom_qty')
                        idnew = pool_dest.env[object.model_id.model].create(value)
                        idnew.write({
                            'product_uom_qty': b
                        })
                        new_id = idnew.id
                    elif object.model_id.model == "purchase.order.line":
                        a = value.pop('product_qty')
                        b = value.pop('product_uom_qty')
                        idnew = pool_dest.env[object.model_id.model].create(value)
                        idnew.write({
                            'product_uom_qty': b
                        })
                        new_id = idnew.id
                    elif object.model_id.model == "stock.move":
                        a = value.pop('product_qty')
                        b = value.pop('product_uom_qty')
                        value.update({'quantity_done': 0})
                        value.pop('group_id')
                        value.pop('purchase_line_id')
                        idnew = pool_dest.env[object.model_id.model].create(value)
                        idnew.write({
                            'product_uom_qty': b
                        })
                        new_id = idnew.id
                    else:
                        idnew = pool_dest.env[object.model_id.model].create(value)
                        new_id = idnew.id

                    if object.model_id.model == "sale.order":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'sale.order.quotation')])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "purchase.order":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : '/'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'purchase.order.seqs.rfq')])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "purchase.request":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : '/'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'purchase.order.seqs.rfq')])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "purchase.requisition":
                        new_model_obj_name = pool_dest.get(object.model_id.model).write([new_id], {'name' : '/'})
                        seq = pool_dest.get('ir.sequence').search_read([('code', '=', 'purchase.requisition.blanket.order.new')])
                        new_seq_num = pool_dest.get('ir.sequence').write([seq['id']], {'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "purchase.agreement":
                        new_model_obj_name = pool_dest.get(object.model_id.model).write([new_id], {'name' : '/'})
                        seq = pool_dest.get('ir.sequence').search_read([('code', '=', 'purchase.agreement.seqs')])
                        new_seq_num = pool_dest.get('ir.sequence').write([seq['id']], {'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "material.request":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'material.request')])
                        if not seq.use_date_range:
                            new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                        else:
                            date_range = seq.date_range_ids.sorted('create_date', reverse=True)[0]
                            new_seq_num = pool_dest.env['ir.sequence.date_range'].browse([date_range.id]).write({'number_next_actual' : date_range.number_next_actual - 1})
                    elif object.model_id.model == "internal.transfer":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'internal.transfer')])
                        if not seq.use_date_range:
                            new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                        else:
                            date_range = seq.date_range_ids.sorted('create_date', reverse=True)[0]
                            new_seq_num = pool_dest.env['ir.sequence.date_range'].browse([date_range.id]).write({'number_next_actual' : date_range.number_next_actual - 1})
                    elif object.model_id.model == "dev.rma.rma":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : '/'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'dev.rma.rma')])
                        if not seq.use_date_range:
                            new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                        else:
                            date_range = seq.date_range_ids.sorted('create_date', reverse=True)[0]
                            new_seq_num = pool_dest.env['ir.sequence.date_range'].browse([date_range.id]).write({'number_next_actual' : date_range.number_next_actual - 1})
                    elif object.model_id.model == "stock.picking":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : '/'})
                        picking_type = pool_dest.env['stock.picking.type'].browse(value['picking_type_id'])
                        seq = picking_type.sequence_id
                        if not seq.use_date_range:
                            neww_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                        else:
                            date_range = seq.date_range_ids.sorted('create_date', reverse=True)[0]
                            new_seq_num = pool_dest.env['ir.sequence.date_range'].browse([date_range.id]).write({'number_next_actual' : date_range.number_next_actual - 1})
                    elif object.model_id.model == "invoice.recurring":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', acc_recurring_invoice_seq_code)])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "account.voucher":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'number' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', acc_voucher_seq_code)])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "customer.deposit":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'customer.deposit')])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "vendor.payment.request":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'vendor.payment.id.sequence')])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "account.multipayment":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', acc_multipayment_seq_code)])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "receipt.voucher":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'receipt.voucher.code')])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    # elif object.model_id.model == "payment.voucher":
                    #     new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : '/'})
                    #     seq = pool_dest.env['ir.sequence'].search([('code', '=', 'payment.voucher.code')])
                    #     new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "vendor.deposit":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', vendor_deposit_seq)])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "account.internal.transfer":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'account.internal.transfer')])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "account.pettycash":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'number' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'account.pettycash.sequence')])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "account.pettycash.voucher.wizard":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'account.pettycash.voucher.wizard.seq')])
                        new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    elif object.model_id.model == "stock.inventory":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : '/'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'inv.adj.seq')])
                        if not seq.use_date_range:
                            new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                        else:
                            date_range = seq.date_range_ids.sorted('create_date', reverse=True)[0]
                            new_seq_num = pool_dest.env['ir.sequence.date_range'].browse([date_range.id]).write({'number_next_actual' : date_range.number_next_actual - 1})
                    # elif object.model_id.model == "stock.landed.cost":
                    #     new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : '/'})
                    #     seq = pool_dest.env['ir.sequence'].search([('code', '=', 'stock.landed.cost')])
                    #     if not seq.use_date_range:
                    #         new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                    #     else:
                    #         date_range = seq.date_range_ids.sorted('create_date', reverse=True)[0]
                    #         new_seq_num = pool_dest.env['ir.sequence.date_range'].browse([date_range.id]).write({'number_next_actual' : date_range.number_next_actual - 1})
                    elif object.model_id.model == "stock.scrap.request":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'stock.product.usage')])
                        if not seq.use_date_range:
                            new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                        else:
                            date_range = seq.date_range_ids.sorted('create_date', reverse=True)[0]
                            new_seq_num = pool_dest.env['ir.sequence.date_range'].browse([date_range.id]).write({'number_next_actual' : date_range.number_next_actual - 1})
                    elif object.model_id.model == "stock.warehouse.orderpoint":
                        new_model_obj_name = pool_dest.env[object.model_id.model].browse([new_id]).write({'name' : 'New'})
                        seq = pool_dest.env['ir.sequence'].search([('code', '=', 'sequence.stock.warehouse.orderpoint')])
                        if not seq.use_date_range:
                            new_seq_num = pool_dest.env['ir.sequence'].browse([seq.id]).write({'number_next_actual' : seq.number_next_actual - 1})
                        else:
                            date_range = seq.date_range_ids.sorted('create_date', reverse=True)[0]
                            new_seq_num = pool_dest.env['ir.sequence.date_range'].browse([date_range.id]).write({'number_next_actual' : date_range.number_next_actual - 1})

                else:
                    name_table_query = field_line.relation.replace('.','_')
                    if not value_line_ids:
                        continue

                    for value_lines in value_line_ids:
                        value_lines = self.update_name_number_doc(value_lines, field_line.relation)
                        value_lines = self.remove_exceptional_fields(value_lines, field_line.relation)
                        value_lines = self.update_state_to_draft(value_lines)
                        json_value = json.dumps(value_lines, separators=(',', ':'), ensure_ascii=False)
                        json_value = json_value.replace('/', '|')
                        
                        create_in_query_id = pool_dest.get('base.synchro').create_in_query(json_value,field_line.relation)



                self.env["base.synchro.obj.line"].create(
                    {
                        "obj_id": object.id,
                        "local_id": (action == "u") and id or new_id,
                        "remote_id": (action == "d") and id or new_id,
                    }
                )

                object_number_fields = ["account.voucher", "account.pettycash"]

                if object.model_id.model in object_number_fields:
                    source_dest_doc_field = "number"
                elif object.model_id.model == "hr.expense.sheet":
                    source_dest_doc_field = "seq_name"
                else:
                    source_dest_doc_field = "name"

                self.report_total += 1
                self.report_create += 1
                list_id.append(
                                (0, 0, {'module_name' : object.model_id.model,
                                        'source_id' : str((action == "u") and id or new_id),
                                        'source_doc_no' : (action == "u") and value_name or (value.get(source_dest_doc_field) if value.get(source_dest_doc_field) else False),
                                        'dest_id' : str((action == "d") and id or new_id),
                                        'dest_doc_no' : (action == "d") and value_name or (value.get(source_dest_doc_field) if value.get(source_dest_doc_field) else False),
                                      }
                                )
                               )
        return list_id


    def improve_value_matrix_line(self, value, model_obj):
        if "status" in value:
            value["status"] = False
        if "time" in value:
            value["time"] = False
        if "approved" in value:
            value["approved"] = False
        if "user_approved_ids" in value:
            value["user_approved_ids"] = []
        if "last_approved" in value:
            value["last_approved"] = False

    def improve_value_parent_purchase(self, value, model_obj):
        value['base_sync'] = True
        if "name" in value:
            value["name"] = '/'
        if "name2" in value:
            value["name2"] = ''
        if "display_name" in value:
            value["display_name"] = '/'
        if "state" in value:
            value["state"] = 'draft'
        if "state1" in value:
            value["state1"] = 'draft'
        if model_obj != 'purchase.agreement()':
            if "state2" in value:
                value["state2"] = 'draft'
            if "state3" in value:
                value["state3"] = 'draft'
        else:
            if "state2" in value:
                value["state2"] = False
            if "state3" in value:
                value["state3"] = False
        if "state4" in value:
            value["state4"] = 'draft'
        if "state5" in value:
            value["state5"] = 'draft'
        if 'pr_state' in value:
            value["pr_state"] = 'draft'
        if 'pt_state' in value:
            value["pt_state"] = 'draft'
        if 'date_approve' in value:
            value['date_approve'] = False
        if 'is_editable' in value:
            del value["is_editable"]
        if 'to_approve_allowed' in value:
            del value["to_approve_allowed"]
        # if 'product_id' in value:
        #     del value["product_id"]
        if 'invoice_count' in value:
            del value["invoice_count"]
        if 'invoice_ids' in value:
            del value["invoice_ids"]
        if 'invoice_status' in value:
            del value["invoice_status"]
        if 'picking_count' in value:
            del value["picking_count"]
        if 'picking_ids' in value:
            del value["picking_ids"]
        if 'group_id' in value:
            del value["group_id"]
        if 'sh_fully_ship' in value:
            del value["sh_fully_ship"]
        if 'sh_partially_ship' in value:
            del value["sh_partially_ship"]
        if 'sh_fully_paid' in value:
            del value["sh_fully_paid"]
        if 'sh_partially_paid' in value:
            del value["sh_partially_paid"]
        if 'agreement_id' in value:
            del value["agreement_id"]
        if 'sh_po_number' in value:
            del value["sh_po_number"]
        if 'sh_purchase_order_id' in value:
            del value["sh_purchase_order_id"]
        if 'sh_revision_po_id' in value:
            del value["sh_revision_po_id"]
        if 'po_count' in value:
            del value["po_count"]
        if 'total_invoices_amount' in value:
            del value["total_invoices_amount"]
        if 'down_payment_by' in value:
            del value["down_payment_by"]
        if 'is_dp' in value:
            del value["is_dp"]
        if 'dp_journal_id' in value:
            del value["dp_journal_id"]
        if 'hide_create_bill' in value:
            del value["hide_create_bill"]
        if 'message_main_attachment_id' in value:
            del value["message_main_attachment_id"]
        if 'requisition_id' in value:
            del value["requisition_id"]
        if 'line_count' in value:
            del value["line_count"]
        if 'move_count' in value:
            del value["move_count"]
        if 'purchase_count' in value:
            del value["purchase_count"]
        if 'mr_id' in value:
            del value["mr_id"]
        if 'purchase_count' in value:
            del value["purchase_count"]
        if 'purchase_req_state' in value:
            del value["purchase_req_state"]
        if 'purchase_req_state_1' in value:
            del value["purchase_req_state_1"]
        if 'purchase_req_state_2' in value:
            del value["purchase_req_state_2"]
        if 'origin' in value:
            del value["origin"]
        if 'pr_count' in value:
            del value["pr_count"]
        if 'purchase_ids' in value:
            del value["purchase_ids"]
        if 'is_purchase_tender' in value:
            del value["is_purchase_tender"]
        if 'is_pr_to_pt' in value:
            del value["is_pr_to_pt"]
        if 'blanket_order_count' in value:
            del value["blanket_order_count"]
        if 'purchase_tender_count' in value:
            del value["purchase_tender_count"]
        if 'is_purchase_req_direct_purchase' in value:
            del value["is_purchase_req_direct_purchase"]
        if 'order_count' in value:
            del value["order_count"]
        if 'purchase_ids' in value:
            del value["purchase_ids"]
        if 'purchase_id' in value:
            del value["purchase_id"]
        if 'purchase_request_id' in value:
            del value["purchase_request_id"]
        if 'bo_state' in value:
            del value["bo_state"]
        if 'bo_state1' in value:
            del value["bo_state1"]
        if "bo_state2" in value:
            value["bo_state2"] = 'draft'
        if "state_blanket_order" in value:
            value["state_blanket_order"] = 'draft'
        if 'is_bo_confirm' in value:
            del value["is_bo_confirm"]


    def improve_value_child_purchase(self, value, model_obj):
        if "order_id" in value:
            value["order_id"] = False
        if "request_id" in value:
            value["request_id"] = False
        if "invoice_lines" in value:
            value["invoice_lines"] = []
        if "qty_invoiced" in value:
            value["qty_invoiced"] = 0
        if "qty_received" in value:
            value["qty_received"] = 0
        if "qty_received_manual" in value:
            value["qty_received_manual"] = 0
        if "qty_to_invoice" in value:
            value["qty_to_invoice"] = 0
        if "move_ids" in value:
            value["move_ids"] = []
        if "agreement_id" in value:
            value["agreement_id"] = False
        if "sale_order_id" in value:
            value["sale_order_id"] = False
        if "sale_line_id" in value:
            value["sale_line_id"] = False
        if "purchase_budget_lines" in value:
            value["purchase_budget_lines"] = []
        if "delivery_ref" in value:
            value["delivery_ref"] = ""
        if "vendor_bills_ref" in value:
            value["invoice_lines"] = ""
        if "request_line_id" in value:
            value["request_line_id"] = False
        if "state_delivery" in value:
            value["state_delivery"] = "nothing"
        # if "state_inv" in value:
        #     value["state_inv"] = "no"
        if "state" in value:
            value["state"] = "draft"
        if "status" in value:
            value["status"] = "draft"
        if "state_inv" in value:
            del value["state_inv"]
        if 'is_editable' in value:
            del value["is_editable"]
        if "request_state" in value:
            value["request_state"] = "draft"
        if "purchased_qty" in value:
            del value["purchased_qty"]
        if "purchase_lines" in value:
            del value["purchase_lines"]
        if "purchase_state" in value:
            del value["purchase_state"]
        if "qty_in_progress" in value:
            del value["qty_in_progress"]
        if "qty_done" in value:
            del value["qty_done"]
        if "qty_cancelled" in value:
            del value["qty_cancelled"]
        if "qty_to_buy" in value:
            del value["qty_to_buy"]
        if "pending_qty_to_receive" in value:
            del value["pending_qty_to_receive"]
        if "cancelled_qty" in value:
            del value["cancelled_qty"]
        if "remaining_qty" in value:
            del value["remaining_qty"]
        if "purchase_req_state" in value:
            del value["purchase_req_state"]
        if "agreement_state" in value:
            del value["agreement_state"]
        if "tender_qty" in value:
            del value["tender_qty"]
        if "tender_line_ids" in value:
            del value["tender_line_ids"]
        if "purchase_order_line_ids" in value:
            del value["purchase_order_line_ids"]
        if "requisition_id" in value:
            value["requisition_id"] = False
        if "qty_ordered" in value:
            del value["qty_ordered"]
        if "qty_remaining" in value:
            del value["qty_remaining"]
        if 'order_count' in value:
            del value["order_count"]



    @api.model
    def get_id(self, object_id, id, action):
        synchro_line_obj = self.env["base.synchro.obj.line"]
        field_src = (action == "u") and "local_id" or "remote_id"
        field_dest = (action == "d") and "local_id" or "remote_id"
        rec_id = synchro_line_obj.search(
            [("obj_id", "=", object_id), (field_src, "=", id)]
        )
        result = False
        if rec_id:
            result = synchro_line_obj.browse([rec_id[0].id]).read([field_dest])
            if result:
                result = result[0][field_dest]
        return result

    @api.model
    def relation_transform(
        self,
        pool_src,
        pool_dest,
        obj_model,
        res_id,
        action,
        destination_inverted,
    ):

        if not res_id:
            return False
        _logger.debug("Relation transform")
        self._cr.execute(
            """select o.id from base_synchro_obj o left join
                        ir_model m on (o.model_id =m.id) where
                        m.model=%s and o.active""",
            (obj_model,),
        )
        obj = self._cr.fetchone()
        result = False
        if obj:
            result = self.get_id(obj[0], res_id, action)
            _logger.debug(
                "Relation object already synchronized. Getting id%s", result
            )
            if obj_model == "stock.location":
                names = pool_src.get(obj_model).name_get([res_id])[0][1]
                res = pool_dest.env[obj_model]._name_search(names, [], "=")
                from_clause, where_clause, where_clause_params = res.get_sql()
                where_str = where_clause and (" WHERE %s" % where_clause) or ''
                query_str = 'SELECT "%s".id FROM ' % pool_dest.env[obj_model]._table + from_clause + where_str
                order_by = pool_dest.env[obj_model]._generate_order_by(None, query_str)
                query_str = query_str + order_by
                pool_dest.env[obj_model]._cr.execute(query_str, where_clause_params)
                res1 = self._cr.fetchall()
                res = [ls[0] for ls in res1]
                result = res[0]
            if obj_model == "stock.picking.type":
                names = pool_src.get(obj_model).name_get([res_id])[0][1]
                name = names.split(':')[0].strip()
                res = pool_dest.env[obj_model]._name_search(name, [], "=")
                from_clause, where_clause, where_clause_params = res.get_sql()
                where_str = where_clause and (" WHERE %s" % where_clause) or ''
                query_str = 'SELECT "%s".id FROM ' % pool_dest.env[obj_model]._table + from_clause + where_str
                order_by = pool_dest.env[obj_model]._generate_order_by(None, query_str)
                query_str = query_str + order_by
                pool_dest.env[obj_model]._cr.execute(query_str, where_clause_params)
                res1 = self._cr.fetchone()
                result = res1
        else:
            _logger.debug(
                """Relation object not synchronized. Searching/
             by name_get and name_search"""
            )
            report = []
            if not destination_inverted:
                fields = pool_src.get(obj_model).fields_get()
                serv = self.server_url
                user = serv.login
                res2 = pool_dest.env[obj_model].search_read([('login', '=', user)], ['id','name', 'company_id'])
                comp_id = res2[0]['company_id']

                if obj_model == "res.country.state":
                    names = pool_src.get(obj_model).name_get([res_id])[0][1]
                    name = names.split("(")[0].strip()
                    if 'company_id' in fields:
                        res = pool_dest.env[obj_model]._name_search(name, [('company_id', '=', comp_id[0])], "=")
                    else:
                        res = pool_dest.env[obj_model]._name_search(name, [], "=")
                    res = [res]
                elif obj_model == "res.country":
                    names = pool_src.get(obj_model).name_get([res_id])[0][1]
                    if 'company_id' in fields:
                        res = pool_dest.env[obj_model]._name_search(names, [('company_id', '=', comp_id[0])], "=")
                    else:
                        res = pool_dest.env[obj_model]._name_search(names, [], "=")
                    res = [[res[0]]]
                if obj_model == "res.company":
                    names = pool_src.get(obj_model).name_get([res_id])[0][1]
                    res = pool_dest.env[obj_model].name_search(names, [], "=")
                else:
                    names = pool_src.get(obj_model).name_get([res_id])[0][1]
                    if 'company_id' in fields:
                        res = pool_dest.env[obj_model].name_search(names, [('company_id', '=', comp_id[0])], "=")
                    else:
                        res = pool_dest.env[obj_model].name_search(names, [], "=")
            else:
                fields = pool_src.env[obj_model].fields_get()
                serv = self.server_url
                user = serv.login
                res2 = pool_dest.get('res.users').search_read([('login', '=', user)], ['id','name', 'company_id'])
                comp_id = res2[0]['company_id']

                model_obj = pool_src.env[obj_model]
                names = model_obj.browse([res_id]).name_get()[0][1]
                if obj_model == "res.company":
                    res = pool_dest.get(obj_model).name_search(names, [], "=")
                else:
                    if 'company_id' in fields:
                        res = pool_dest.get(obj_model).name_search(names, [('company_id', '=', comp_id[0])], "=")
                    else:
                        res = pool_dest.get(obj_model).name_search(names, [], "=")

            _logger.debug("name_get in src: %s", names)
            _logger.debug("name_search in dest: %s", res)
            if res:
                result = res[0][0]
            else:
                _logger.warning(
                    """Record '%s' on relation %s not found, set/
                                to null.""",
                    names,
                    obj_model,
                )
                _logger.warning(
                    """You should consider synchronize this/
                model '%s""",
                    obj_model,
                )
                report.append(
                    """WARNING: Record "%s" on relation %s not/
                    found, set to null."""
                    % (names, obj_model)
                )
        return result

    @api.model
    def data_transform(
        self,
        pool_src,
        pool_dest,
        obj,
        data,
        action=None,
        destination_inverted=False,
    ):
        if action is None:
            action = {}
        if not destination_inverted:
            fields = pool_src.get(obj).fields_get()
        else:
            fields = pool_src.env[obj].fields_get()
        _logger.debug("Transforming data")
        field_line = False
        if 'field_line' in self.env.context:
            field_line = self.env.context['field_line']
        for f in fields:
            if f in data:
                ftype = fields[f]["type"]
                if ftype in ("function", "one2many", "one2one"):
                    # agar field dari field line object tidak dihapus
                    if field_line:
                        if f not in field_line:
                            _logger.debug("Field %s of type %s, discarded.", f, ftype)
                            del data[f]
                    else:
                        _logger.debug("Field %s of type %s, discarded.", f, ftype)
                        del data[f]
                elif ftype == "many2one":
                    _logger.debug("Field %s is many2one", f)
                    if (isinstance(data[f], list)) or (isinstance(data[f], tuple)) and data[f]:
                        fdata = data[f][0]
                    else:
                        fdata = data[f]

                    df = self.relation_transform(
                        pool_src,
                        pool_dest,
                        fields[f]["relation"],
                        fdata,
                        action,
                        destination_inverted,
                    )
                    # if obj == "stock.picking":
                    #     data[f] = df
                    #     if not data[f]:
                    #         del data[f]
                    # else:
                    data[f] = fdata
                    #data[f] = df
                    #if not data[f]:
                    #    del data[f]

                elif ftype == "many2many":
                    res = map(
                        lambda x: self.relation_transform(
                            pool_src,
                            pool_dest,
                            fields[f]["relation"],
                            x,
                            action,
                            destination_inverted,
                        ),
                        data[f],
                    )
                    data[f] = [(6, 0, [x for x in res if x])]
        if "id" in data:
            del data["id"]
        return data

    def upload_download(self):
        self.ensure_one()
        report = []
        list_ids = []
        start_date = fields.Datetime.now()
        timezone = self._context.get("tz", "UTC")
        start_date = format_datetime(
            self.env, start_date, timezone, dt_format=False
        )
        server = self.server_url
        for obj_rec in server.obj_ids:
            _logger.debug("Start synchro of %s", obj_rec.name)
            dt = fields.Datetime.now()
            list_id = self.synchronize(server, obj_rec)
            if list_id:
                list_ids += list_id
            if obj_rec.action == "b":
                time.sleep(1)
                dt = fields.Datetime.now()
            obj_rec.write({"synchronize_date": dt})
        end_date = fields.Datetime.now()
        end_date = format_datetime(
            self.env, end_date, timezone, dt_format=False
        )
        # Creating res.request for summary results
        if self.user_id:
            request = self.env["res.request"]
            if not report:
                report.append("No exception.")
            summary = """Here is the synchronization report:

     Synchronization started: %s
     Synchronization finished: %s

     Synchronized records: %d
     Records updated: %d
     Records created: %d

     Exceptions:
        """ % (
                start_date,
                end_date,
                self.report_total,
                self.report_write,
                self.report_create,
            )
            summary += "\n".join(report)
            cek = request.create(
                {
                    "name": "Synchronization report",
                    "act_from": self.env.user.id,
                    "date": fields.Datetime.now(),
                    "act_to": self.user_id.id,
                    "body": summary,
                    "res_request_lines" : list_ids,
                }
            )
            # raise ValidationError("ahdgjasgdhsgd")
            return {}

    def upload_download_multi_thread(self):
        threaded_synchronization = threading.Thread(
            target=self.upload_download()
        )
        threaded_synchronization.run()
        id2 = self.env.ref("base_synchro.view_base_synchro_finish").id
        return {
            "binding_view_types": "form",
            "view_mode": "form",
            "res_model": "base.synchro",
            "views": [(id2, "form")],
            "view_id": False,
            "type": "ir.actions.act_window",
            "target": "new",
        }

    def upload_download_scheduler(self):
        threaded_synchronization = threading.Thread(target=self.upload_download())
        threaded_synchronization.run()

    def running_scheduler(self):
        server_ids = self.env["base.synchro.server"].search([])
        for server_id in server_ids:
            sync_id = self.env["base.synchro"].create({ 'server_url' : server_id.id,'user_id': self.env.user.id})
            sync_id.upload_download_scheduler()