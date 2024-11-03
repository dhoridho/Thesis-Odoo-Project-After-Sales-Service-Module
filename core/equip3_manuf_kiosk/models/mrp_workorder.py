# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class StockMoveInherit(models.Model):
    _inherit = "stock.move"

    lot_name = fields.Char(
        string='Lot Name',
    )
    
    is_scan = fields.Boolean(
        string='Is Scan', default=False,
    )
    
    

class MrpWorkorderInheritKiosk(models.Model):
    _inherit = "mrp.workorder"


    manuf_kiosk_barcode_mobile = fields.Char(string="Mobile Barcode")

    manuf_kiosk_bm_is_cont_scan = fields.Boolean(
        related='company_id.manuf_kiosk_bm_is_cont_scan', readonly=False)
    
    manuf_kiosk_barcode_mobile_type = fields.Selection(
        related='company_id.manuf_kiosk_barcode_mobile_type', string='Product Scan Options In Mobile (KIOSK)', translate=True, readonly=False)
    
    manuf_kiosk_bm_is_notify_on_success = fields.Boolean(
        related='company_id.manuf_kiosk_bm_is_notify_on_success', string='Notification On Product Succeed? (KIOSK)', readonly=False)

    manuf_kiosk_bm_is_notify_on_fail = fields.Boolean(
        related='company_id.manuf_kiosk_bm_is_notify_on_fail', string='Notification On Product Failed? (KIOSK)', readonly=False)

    manuf_kiosk_bm_is_sound_on_success = fields.Boolean(
        related='company_id.manuf_kiosk_bm_is_sound_on_success', string='Play Sound On Product Succeed? (KIOSK)', readonly=False)

    manuf_kiosk_bm_is_sound_on_fail = fields.Boolean(
        related='company_id.manuf_kiosk_bm_is_sound_on_fail', string='Play Sound On Product Failed? (KIOSK)', readonly=False)
    
    # cofig for employee scan
    manuf_kiosk_att_is_cont_scan = fields.Boolean(
        related='company_id.manuf_kiosk_att_is_cont_scan', readonly=False)

    manuf_kiosk_att_is_notify_on_success = fields.Boolean(
        related='company_id.manuf_kiosk_att_is_notify_on_success', string='Notification On Attendance Succeed? (KIOSK)', readonly=False)

    manuf_kiosk_att_is_notify_on_fail = fields.Boolean(
        related='company_id.manuf_kiosk_att_is_notify_on_fail', string='Notification On Attendance Failed? (KIOSK)', readonly=False)

    manuf_kiosk_att_is_sound_on_success = fields.Boolean(
        related='company_id.manuf_kiosk_att_is_sound_on_success', string='Play Sound On Attendance Succeed? (KIOSK)', readonly=False)

    manuf_kiosk_att_is_sound_on_fail = fields.Boolean(
        related='company_id.manuf_kiosk_att_is_sound_on_fail', string='Play Sound On Attendance Failed? (KIOSK)', readonly=False)
    
    produced_finished_product = fields.Float('Produced Finished Goods', digits='Product Unit of Measure')
    produced_finished_product_uom_id = fields.Many2one('uom.uom', related='product_uom_id', string='Unit of Measure #2', readonly=True)
    produced_rejected_product = fields.Float('Produced Rejected Goods', digits='Product Unit of Measure')
    produced_rejected_product_uom_id = fields.Many2one('uom.uom', related='product_uom_id', string='Unit of Measure #3', readonly=True)
    digits_value = fields.Integer(
        compute='_compute_digits_value' )
    
    @api.model
    def _compute_digits_value(self):
        for record in self:
            record.digits_value = self.env['decimal.precision'].precision_get('Product Unit of Measure')
    
    
    is_show_barcode_scanner = fields.Boolean(string='Show Scan Barcode feature', compute='_compute_get_kiosk_cofig')
    is_qty_editable = fields.Boolean(string='Qty Editable', compute='_compute_get_kiosk_cofig')
    consumption_type = fields.Selection([
        ('flexible', 'Allowed'),
        ('warning', 'Allowed with warning'),
        ('strict', 'Blocked'),
    ], default='warning', string='Flexible Consumption', compute='_compute_get_consumption')
    
    employee_id = fields.Many2one('hr.employee', string='Employee')
        
    @api.model
    def _compute_get_consumption(self):
        for rec in self:
            rec.consumption_type = rec.production_id.bom_id.consumption
    
    @api.model
    def _compute_get_kiosk_cofig(self):
        self.is_show_barcode_scanner = False
        self.is_qty_editable = False
    
    
    @api.model            
    def get_kiosk_action(self, workorder_id):
        wo_id = self.env['mrp.workorder'].browse(workorder_id)
        kanban_view_ref = self.env.ref("equip3_manuf_kiosk.workcenter_line_kanban_kiosk", False)
        action = {
            "name": _("Work Orders"),
            "type": "ir.actions.act_window",
            "view_mode": "kanban",
            "res_model": "mrp.workorder",
            "domain": [
                ["state", "in", ["ready", "progress", "pending"]],
                ["workcenter_id.id", "=", wo_id.workcenter_id.id],
            ],
            "views": [(kanban_view_ref.id, "kanban")],
            "target": "main",
            "res_id": wo_id.workcenter_id.id,
        }
        return {'action': action}
    
    @api.model
    def kiosk_mobile_scan(self, barcode, wo_id):
        wo_id = self.env['mrp.workorder'].browse(wo_id)
        err_msg = ""
        product = self.env['product.product'].sudo().search(['|',('barcode', '=', barcode),('sh_qr_code', '=', barcode)], limit=1)
        if product:
            raw_id = self.env['stock.move'].search([('product_id', '=', product.id), ('mrp_workorder_component_id', '=', wo_id.id)], limit=1)
            if raw_id:
                raw_id.quantity_done = raw_id.quantity_done + 1
                raw_id.product_uom_qty = raw_id.quantity_done
            else:
                lot = self.env['stock.production.lot'].search([('product_id', '=', product.id)], limit=1)
                
                self.env['stock.move'].create({
                    'product_id': product.id,
                    'name': product.name,
                    'product_uom': product.uom_id.id,
                    'location_id': wo_id.workcenter_id.location_id.id,
                    'location_dest_id': wo_id.workcenter_id.location_id.id,
                    'product_uom_qty': 1,
                    'mrp_workorder_component_id': wo_id.id,
                    'workorder_id': wo_id.id,
                    'lot_ids': lot,
                    'lot_name': lot.name
                })
            return {'action': _("%(product)s.'") % {'product': wo_id.move_raw_ids}}
            # employee._attendance_action('hr_attendance.hr_attendance_action_kiosk_mode')
        else:
            err_msg = {'warning': _("No product corresponding to Barcode '%(barcode)s.'") % {'barcode': barcode}}
            return err_msg
    
    @api.model
    def kiosk_online_sync(self, workorder_id, component, produced_finished_goods, produced_rejected_goods, done_method_sync):
        # Update data
        wo_id = self.env['mrp.workorder'].browse(workorder_id)
        # check the wo status done or not
        if wo_id.state in ['progress']:
            for comp in component:
                _logger.info("APPLE %s: %s" % (comp['product_id'], comp['sync']))
                if comp['sync'] == False:
                    _logger.info("APPLE IF %s: %s" % (comp['product_id'], comp['sync']))
                    product = self.env['product.product'].browse(comp['product_id'])
                    if product:
                        # Update MO component consumed qty
                        m_comp = self.env['stock.move'].search([('product_id', '=', product.id), ('raw_material_production_id', '=', wo_id.production_id.id)], limit=1)
                        if m_comp:
                            m_comp.quantity_done = comp['product_uom_qty']
                        
                        if comp['move_id']:
                            raw_id = self.env['stock.move'].browse(comp['move_id'])
                            lot = self.env['stock.production.lot'].browse(comp['lot_id'])
                            if raw_id:
                                raw_id.product_uom_qty = comp['product_uom_qty']
                                raw_id.lot_name = lot.name
                                raw_id.lot_ids = lot
                                raw_id.is_scan = True
                            
                        else:
                            lot = self.env['stock.production.lot'].browse(comp['lot_id'])
                            
                            self.env['stock.move'].create({
                                'product_id': product.id,
                                'name': product.name,
                                'product_uom': product.uom_id.id,
                                'location_id': wo_id.workcenter_id.location_id.id,
                                'location_dest_id': wo_id.workcenter_id.location_id.id,
                                'product_uom_qty': comp['product_uom_qty'],
                                'mrp_workorder_component_id': wo_id.id,
                                'workorder_id': wo_id.id,
                                'lot_ids': lot,
                                'lot_name': lot.name,
                                'is_scan': True
                            })
            # Create MRP records
            done_method_sync = done_method_sync
            t_type = "create"
            cons_id = False
            if len(wo_id.consumption_ids) == 0:
                t_type = "create"
            
            for cons in wo_id.consumption_ids:
                if cons.state == 'draft':
                    t_type = "update"
                    cons_id = cons.id
                elif cons.state == 'confirm':
                    t_type = "create_new"
            
            approval_matrix = self.env['mrp.approval.matrix'].sudo()
            if self.env.user.branch_id:
                approval_matrix = approval_matrix.search([('company_id', '=', self.env.company.id), ('branch_id', '=', self.env.user.branch_id.id), ('matrix_type', '=', 'pr')], limit=1)

            all_workorder_ids = sorted(wo_id.production_id.workorder_ids.ids)
            is_last_workorder = all_workorder_ids[-1] == wo_id.id
            move_finished_ids = self.env['stock.move']
            if is_last_workorder:
                move_finished_ids = wo_id.production_id.move_finished_ids.filtered(
                    lambda m: m.state not in ('done', 'cancel') and not m.byproduct_id)
            byproduct_ids = wo_id.byproduct_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
                    
            # check consumption_ids and create consumption records
            if t_type == "create" or t_type == "create_new":
                consumption = self.env['mrp.consumption'].with_env(self.env(user=wo_id.employee_id.user_id.id)).create({
                    'manufacturing_plan': wo_id.mrp_plan_id.id,
                    'name': _('New'),
                    'create_date': fields.Datetime.now(),
                    'create_uid': wo_id.employee_id.user_id.id or self.env.user.id,
                    'manufacturing_order_id': wo_id.production_id.id,
                    'workorder_id': wo_id.id,
                    'product_id': wo_id.product_id.id,
                    'date_finished': fields.Datetime.now(),
                    'branch_id': self.env.user.branch_id.id,
                    'approval_matrix_id': approval_matrix.id,
                    'finished_qty': produced_finished_goods or 0,
                    'rejected_qty': produced_rejected_goods or 0,
                    'is_last_workorder': is_last_workorder,
                    'move_finished_ids': [(6, 0, move_finished_ids.ids)],
                    'byproduct_ids': [(6, 0, byproduct_ids.ids)],
                    'move_raw_ids': [(0, 0, {
                            "name": "New",
                            "product_id": line["product_id"],
                            "quantity_done": line["product_uom_qty"],
                            "product_uom_qty": line["product_uom_qty"],
                            "product_uom": self.env['product.product'].browse(line['product_id']).uom_id.id,
                            "location_id": wo_id.workcenter_id.location_id.id,
                            "location_dest_id": wo_id.workcenter_id.location_id.id,
                            "lot_ids": [(6, 0, [line["lot_id"]])],
                    }) for line in component]
                })
                # consumption.oc_finished_product_rejected_product()  
            elif t_type == "update":
                if cons_id:
                    self.env['mrp.consumption'].browse(cons_id).write({
                                'finished_qty': produced_finished_goods or 0,
                                'rejected_qty': produced_rejected_goods or 0,
                    })
                    # self.env['mrp.consumption'].browse(cons_id).move_raw_ids.unlink()
                    for comp in component:
                        move_id = self.env['stock.move'].search([('product_id', '=', comp["product_id"]), ('mrp_consumption_id', '=', cons_id)], limit=1)
                        if move_id:
                            move_id.quantity_done = move_id.quantity_done + comp["new_qty"]
                            move_id.product_uom_qty = move_id.product_uom_qty + comp["new_qty"]
                            move_id.state = "done"
                        else:
                            if comp["new_qty"] > 0:
                                self.env['mrp.consumption'].browse(cons_id).write({
                                    'move_raw_ids': [(0, 0, {
                                            "name": "New",
                                            "product_id": comp["product_id"],
                                            "quantity_done": comp["new_qty"],
                                            "product_uom_qty": comp["new_qty"],
                                            "product_uom": self.env['product.product'].browse(comp['product_id']).uom_id.id,
                                            "location_id": wo_id.workcenter_id.location_id.id,
                                            "location_dest_id": wo_id.workcenter_id.location_id.id,
                                            "lot_ids": [(6, 0, [comp["lot_id"]])],
                                    })]
                                })

        return True
    
    @api.model
    def kiosk_online_sync_mrp(self, workorder_id, done_method_sync):
        """
        This method is used to update mrp record
        @param workorder_id: workorder id
        @return: True
        """
        wo_id = self.env['mrp.workorder'].browse(workorder_id)
        if done_method_sync:
                if wo_id:
                    wo_id.with_context(bypass_consumption=True).button_finish()
                    done_method_sync = False
                con_rec = self.env['mrp.consumption'].search([('workorder_id', '=', wo_id.id), ('state', '=', 'draft')], limit=1)
                if con_rec:
                    # Update employee id 
                    con_rec.write({
                        'create_uid': wo_id.employee_id.user_id.id or self.env.user.id
                    })
                    if wo_id.company_id.production_record_conf:
                        con_rec.action_approval()
                        # _logger.info("APPLE action_approval(): %s" % (con_rec.approval_matrix.id))
                    else:
                        con_rec.move_raw_done_ids = con_rec.move_raw_ids.filtered(lambda m: m.state == 'done')
                        # con_rec.button_confirm()
                        action = con_rec.button_confirm()
                        if action:
                            return action
                        # _logger.info("APPLE button_confirm(): %s" % (con_rec.approval_matrix.id))
                return True
            
    @api.model
    def kiosk_employee_scan(self, barcode, wo_id):
        wo_id = self.env['mrp.workorder'].browse(wo_id)
        err_msg = ""
        employee = self.env['hr.employee'].sudo().search([('sequence_code', '=', barcode)], limit=1)
        if employee:
            wo_id.write({'employee_id': employee.id})
            employee = {
                "name": employee.name,
                "id": employee.id,
                "sequence_code": employee.sequence_code,
            }
            return {'action': employee}
        else:
            err_msg = {'warning': _("No employee corresponding to Barcode '%(barcode)s.'") % {'barcode': barcode}}
            return err_msg

    def kiosk_get_record_data(self, allfields=None, max_level=1):
        self.ensure_one()
        if not allfields:
            allfields = dict()

        precision = self.env['decimal.precision'].sudo()

        def _get_fields(model_name):
            model = self.env[model_name].sudo()
            field_list = list(set(allfields.get(model._name, []) + ['id', 'display_name', model._rec_name]))
            return {fname: model._fields[fname] for fname in field_list}

        def _read_records(records, level=0, max_level=1):
            records = records.sudo()
            
            fields_to_dump = _get_fields(records._name)
            relational_fields = {
                field_name: field
                for field_name, field in fields_to_dump.items()
                if field.type in ('many2one', 'one2many', 'many2many')}

            float_fields = {
                field_name: field
                for field_name, field in fields_to_dump.items()
                if field.type == 'float'}
    
            record_datas = records.read(fields_to_dump.keys())
            for record_data in record_datas:
                record = records.filtered(lambda r: r.id == record_data['id'])
                for field_name, field in relational_fields.items():
                    fields_to_dump = _get_fields(field.comodel_name)
                    if field.type == 'many2one':
                        field_data = record[field_name].read(fields_to_dump.keys())
                        if field_data:
                            field_data = field_data[0]
                        else:
                            field_data = {'id': False}
                    else:
                        if level < max_level:
                            field_data = _read_records(record[field_name], level=level+1)
                        else:
                            field_data = record[field_name].read(fields_to_dump.keys())
                    record_data[field_name] = field_data

                for field_name, field in float_fields.items():
                    field_digits = field._digits
                    digits = 2
                    if isinstance(field_digits, str):
                        digits = precision.precision_get(field_digits)
                    elif (isinstance(field_digits, tuple) or isinstance(field_digits, list)) and len(field_digits) == 2:
                        digits = field_digits[1]
                    record_data[field_name] = (record_data[field_name], digits)

            return record_datas

        return _read_records(self)[0]

    def kiosk_synchronize(self, lines):
        self.ensure_one()

        if self.state != 'progress':
            message = 'The state of workorder must be in progress!'
            if self.state in ('pending', 'ready', 'pause'):
                message += ' Please start workorder first!'
            return message

        consumption_id = self.env['mrp.consumption']
        draft_consumptions = self.consumption_ids.filtered(lambda c: c.state == 'draft')
        if draft_consumptions:
            consumption_id = draft_consumptions[0]

        move_raw_values = []
        for line in lines:
            product_id = self.env['product.product'].browse(line['product_id']['id'])
            if line['id'] == 'New':
                values = {
                    'sequence': 10,
                    'name': self.production_id.name,
                    'date': self.production_id.date_planned_start,
                    'date_deadline': self.production_id.date_planned_start,
                    'bom_line_id': False,
                    'picking_type_id': self.production_id.picking_type_id.id,
                    'product_id': product_id.id,
                    'kiosk_qty': line['product_uom_qty'][0],
                    'quantity_done': line['quantity_done'][0],
                    'product_uom': product_id.uom_id.id,
                    'location_id': self.production_id.location_src_id.id,
                    'location_dest_id': product_id.with_company(self.company_id).property_stock_production.id,
                    'mrp_plan_id': self.production_id.mrp_plan_id and self.production_id.mrp_plan_id.id or False,
                    'raw_material_production_id': self.production_id.id,
                    'company_id': self.company_id.id,
                    'operation_id': self.operation_id.id,
                    'price_unit': product_id.standard_price,
                    'procure_method': 'make_to_stock',
                    'origin': self.production_id.name,
                    'state': 'draft',
                    'warehouse_id': self.production_id.location_src_id.get_warehouse().id,
                    'group_id': self.production_id.procurement_group_id.id,
                    'propagate_cancel': self.production_id.propagate_cancel,
                    'mrp_consumption_id': consumption_id.id
                }
                move_raw_values += [(0, 0, values)]
            else:
                move_id = self.env['stock.move'].browse(line['id'])
                values = {
                    'kiosk_qty': line['product_uom_qty'][0],
                    'quantity_done': line['quantity_done'][0],
                }
                move_raw_values += [(1, line['id'], values)]
        
        self.move_raw_ids = move_raw_values
        return True
        
    # def create_consumption(self, confirm_and_assign=False):
    #     consumption_id = super(MrpWorkorderInheritKiosk, self).create_consumption(confirm_and_assign=confirm_and_assign)
    #     if self.env.context.get('from_kiosk', False):    
    #         for move in consumption_id.move_raw_ids:
    #             kiosk_qty = move.kiosk_qty
    #             move.write({
    #                 'quantity_done': kiosk_qty,
    #                 'kiosk_qty': 0.0
    #             })
    #     return consumption_id

    def button_finish_wizard(self):
        res = super(MrpWorkorderInheritKiosk, self).button_finish_wizard()
        if self.env.context.get('consumption_confirmed', False):
            if res is None:
                consumption = self.consumption_ids.filtered(lambda o: o.state != 'confirm')
            else:
                consumption = self.env['mrp.consumption'].browse(res['res_id'])
            consumption.action_generate_serial()
            consumption.button_confirm()
        return res
