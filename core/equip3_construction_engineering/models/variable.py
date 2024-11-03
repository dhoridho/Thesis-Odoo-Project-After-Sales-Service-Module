# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class VariableTemplate(models.Model):
    _inherit = 'variable.template'
    
    bom_id = fields.Many2one('mrp.bom', 'BOM', compute='_find_bom')
    is_manuf = fields.Boolean(string='Is manufacturing', default=False)
    manufacture_line_variable = fields.One2many('to.manufacture.variable','manufacture_id', string="To Manufacture")
    total_variable_manufacture = fields.Monetary(compute='_calculate_total', string="Total To Manufacture", default=0.0, readonly=True)
    construction_type = fields.Selection([('construction','Construction'),('engineering','Engineering')], string="Construction Type", default='construction', required=True)

    @api.onchange('construction_type')
    def type_onchange(self):
        for rec in self:
            if rec.construction_type == 'construction':
                rec.manufacture_line_variable = False

    def _find_bom(self):
        self.bom_id = self.env['mrp.bom'].search([('variable_ref', '=', self.id)])

    @api.depends('material_variable_ids.subtotal', 'labour_variable_ids.subtotal', 
                 'subcon_variable_ids.subtotal', 'overhead_variable_ids.subtotal', 
                 'equipment_variable_ids.subtotal', 'service_variable_ids.subtotal',
                 'asset_variable_ids.subtotal', 'manufacture_line_variable.subtotal', 
                 'is_manuf', 'bom_id.forecast_cost')
    def _calculate_total(self):
        total_job_cost = 0.0
        for order in self:
            if order.is_manuf == True:
                order.total_variable = order.bom_id.forecast_cost
                order.total_variable_material = 0
                order.total_variable_labour = 0
                order.total_variable_overhead = 0
                order.total_variable_subcon = 0
                order.total_variable_service = 0
                order.total_variable_equipment = 0
                order.total_variable_internal_asset = 0
                order.total_variable_manufacture = 0
            else:
                if order.manufacture_line_variable : 
                    for line in order.manufacture_line_variable:
                        manufacture_price = line.subtotal
                        order.total_variable_manufacture += manufacture_price
                        # total_job_cost += manufacture_price

                else : 

                    order.total_variable_manufacture = 0

                if order.material_variable_ids : 
                    for line in order.material_variable_ids:
                        material_price =  (line.quantity * line.unit_price)
                        order.total_variable_material += material_price
                        total_job_cost += material_price

                else : 

                    order.total_variable_material = 0

                if order.labour_variable_ids :
                    for line in order.labour_variable_ids:
                        labour_price =  (line.quantity * line.unit_price) 
                        order.total_variable_labour += labour_price
                        total_job_cost += labour_price
                else :

                    order.total_variable_labour = 0

                if order.overhead_variable_ids: 
                    for line in order.overhead_variable_ids:
                        overhead_price =  (line.quantity * line.unit_price) 
                        order.total_variable_overhead += overhead_price
                        total_job_cost += overhead_price

                else :

                    order.total_variable_overhead = 0
                
                if order.subcon_variable_ids :
                    for line in order.subcon_variable_ids:
                        subcon_price =  (line.quantity * line.unit_price) 
                        order.total_variable_subcon += subcon_price
                        total_job_cost += subcon_price
                else :

                    order.total_variable_subcon = 0

                if order.service_variable_ids :
                    for line in order.service_variable_ids:
                        service_price =  (line.quantity * line.unit_price) 
                        order.total_variable_service += service_price
                        total_job_cost += service_price
                else :

                    order.total_variable_service = 0

                if order.equipment_variable_ids :
                    for line in order.equipment_variable_ids:
                        equipment_price =  (line.quantity * line.unit_price) 
                        order.total_variable_equipment += equipment_price
                        total_job_cost += equipment_price
                else :

                    order.total_variable_equipment = 0

                if order.asset_variable_ids :
                    for line in order.asset_variable_ids:
                        asset_price =  (line.quantity * line.unit_price) 
                        order.total_variable_internal_asset += asset_price
                        total_job_cost += asset_price
                else :

                    order.total_variable_internal_asset = 0

                order.total_variable_asset = order.total_variable_equipment + order.total_variable_internal_asset
                order.total_variable = total_job_cost

    @api.onchange('manufacture_line_variable')
    def _check_exist_to_manufacture(self):
        exist_group_list = []
        for line in self.manufacture_line_variable:
            same = str(line.finish_good_id.id) + ' - ' + str(line.bom_id.id) 
            if same in exist_group_list:
                raise ValidationError(_('The BOM "%s" already exists, please change the selected BOM.'%((line.bom_id.name))))
            exist_group_list.append(same)
    
    @api.onchange('material_variable_ids')
    def _check_exist_product_id_material(self):
        exist_group_list = []
        for line in self.material_variable_ids:
            same = str(line.bom_id.id) + ' - ' + str(line.product_id.id) + ' - ' + str(line.operation_two_id.id)
            if len(line.bom_id) == 0:
                if same in exist_group_list:
                    raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
            else:
                if same in exist_group_list:
                    raise ValidationError(_('The Product "%s" already exists in BOM "%s", please change the selected Product.'%((line.product_id.name),(line.bom_id.name))))
            exist_group_list.append(same)
                 
    
    @api.onchange('labour_variable_ids')
    def _check_exist_product_id_labour(self):
        exist_group_list = []
        for line in self.labour_variable_ids:
            same = str(line.bom_id.id) + ' - ' + str(line.product_id.id) + ' - ' + str(line.operation_two_id.id)
            if len(line.bom_id) == 0:
                if same in exist_group_list:
                    raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
            else:
                if same in exist_group_list:
                    raise ValidationError(_('The Product "%s" already exists in BOM "%s", please change the selected Product.'%((line.product_id.name),(line.bom_id.name))))
            exist_group_list.append(same)

    @api.onchange('overhead_variable_ids')
    def _check_exist_product_id_overhead(self):
        exist_group_list = []
        for line in self.overhead_variable_ids:
            same = str(line.bom_id.id) + ' - ' + str(line.product_id.id) + ' - ' + str(line.operation_two_id.id)
            if len(line.bom_id) == 0:
                if same in exist_group_list:
                    raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
            else:
                if same in exist_group_list:
                    raise ValidationError(_('The Product "%s" already exists in BOM "%s", please change the selected Product.'%((line.product_id.name),(line.bom_id.name))))
            exist_group_list.append(same)

    @api.onchange('equipment_variable_ids')
    def _check_exist_product_id_equipment(self):
        exist_group_list = []
        for line in self.equipment_variable_ids:
            same = str(line.bom_id.id) + ' - ' + str(line.product_id.id) + ' - ' + str(line.operation_two_id.id)
            if len(line.bom_id) == 0:
                if same in exist_group_list:
                    raise ValidationError(_('The Product "%s" already exists, please change the selected Product.'%((line.product_id.name))))
            else:
                if same in exist_group_list:
                    raise ValidationError(_('The Product "%s" already exists in BOM "%s", please change the selected Product.'%((line.product_id.name),(line.bom_id.name))))
            exist_group_list.append(same)
    
    @api.onchange('asset_variable_ids')
    def _check_exist_group_of_product_asset(self):
        exist_group_list = []
        for line in self.asset_variable_ids:
            same = str(line.bom_id.id) + ' - ' + str(line.asset_id.id) + ' - ' + str(line.operation_two_id.id)
            if len(line.bom_id) == 0:
                if same in exist_group_list:
                    raise ValidationError(_('The Asset "%s" already exists, please change the selected Asset.'%((line.asset_id.name))))
            else:
                if same in exist_group_list:
                    raise ValidationError(_('The Asset "%s" already exists in BOM "%s", please change the selected Asset.'%((line.asset_id.name),(line.bom_id.name))))
            exist_group_list.append(same)

    @api.onchange('subcon_variable_ids')
    def _check_exist_subcon(self):
        exist_subcon_list = []
        for line in self.subcon_variable_ids:
            same = str(line.bom_id.id) + ' - ' + str(line.variable.id) + ' - ' + str(line.operation_two_id.id)
            if len(line.bom_id) == 0:
                if same in exist_subcon_list:
                    raise ValidationError(_('The Job Subcon "%s" already exists, please change the selected Job Subcon.'%((line.variable.name))))
            else:
                if same in exist_subcon_list:
                    raise ValidationError(_('The Job Subcon "%s" already exists in BOM "%s", please change the selected Job Subcon.'%((line.variable.name),(line.bom_id.name))))
            exist_subcon_list.append(same)

    @api.onchange('manufacture_line_variable')
    def update_material(self):
        material = []
        labour = []
        overhead = []
        equip = []
        asset = []
        subcon = []
        fg_list = []
        
        for rec in self.manufacture_line_variable:
            finish_good = rec.finish_good_id
            bom = rec.bom_id
            quantity = rec.quantity
        
            if finish_good and bom:
                if quantity > 0:
                    if rec.onchange_pass == False:
                        rec.write({'onchange_pass': True})

                        if bom.can_be_subcontracted == True:
                            if bom.bom_line_ids or bom.labour_ids or bom.overhead_ids or bom.asset_ids or bom.equipment_ids:
                                for sub in self.subcon_variable_ids:
                                    if sub.finish_good_id != False and len(sub.bom_id) != 0:
                                        if (sub.finish_good_id.name, sub.bom_id.name) not in fg_list:
                                            self.subcon_variable_ids = [(2, sub.id)]
                                for bom_sub in bom.bom_line_ids:
                                    subx = (0, 0, {
                                        'finish_good_id': finish_good.id,
                                        'bom_id': bom.id,
                                        'variable': bom.variable_ref.id,
                                        'description': rec.finish_good_id.display_name,
                                        'quantity': quantity * bom_sub.product_qty,
                                        'uom_id': bom_sub.product_uom_id.id,
                                        'unit_price': bom_sub.cost,
                                        'subtotal': bom_sub.cost * (quantity * bom_sub.product_qty),
                                        'operation_two_id': bom_sub.operation_two_id.id,
                                    })
                                    subcon.append(subx)
                                self.subcon_variable_ids = subcon
                        
                        else:
                            # for material
                            if bom.bom_line_ids:
                                for mater in self.material_variable_ids:
                                    if mater.finish_good_id != False and len(mater.bom_id) != 0:
                                        if (mater.finish_good_id.name, mater.bom_id.name) not in fg_list:
                                            self.material_variable_ids = [(2, mater.id)]
                                for bom_mat in bom.bom_line_ids:
                                    matx = (0, 0, {
                                        'finish_good_id': finish_good.id,
                                        'bom_id': bom.id,
                                        'group_of_product': bom_mat.group_of_product.id,
                                        'product_id': bom_mat.product_id.id,
                                        'description': bom_mat.product_id.name,
                                        'quantity': quantity * bom_mat.product_qty,
                                        'uom_id': bom_mat.product_uom_id.id,
                                        'unit_price': bom_mat.cost,
                                        'subtotal': bom_mat.cost * (quantity * bom_mat.product_qty),
                                        'operation_two_id': bom_mat.operation_two_id.id,
                                    })
                                    material.append(matx)
                                self.material_variable_ids = material
                        
                            # for labor
                            if bom.labour_ids:
                                for labo in self.labour_variable_ids:
                                    if labo.finish_good_id != False and len(labo.bom_id) != 0:
                                        if (labo.finish_good_id.name, labo.bom_id.name) not in fg_list:
                                            self.labour_variable_ids = [(2, labo.id)]
                                for bom_lab in bom.labour_ids:
                                    labx = (0, 0, {
                                        'finish_good_id': finish_good.id,
                                        'bom_id': bom.id,
                                        'group_of_product': bom_lab.group_of_product.id,
                                        'product_id': bom_lab.product_id.id,
                                        'description': bom_lab.product_id.name,
                                        'contractors': bom_lab.contractors,
                                        'time': bom_lab.time,
                                        'quantity': quantity * bom_lab.quantity,
                                        'uom_id': bom_lab.uom_id,
                                        'unit_price': bom_lab.cost,
                                        'subtotal': bom_lab.cost * (quantity * bom_lab.quantity),
                                        'operation_two_id': bom_lab.operation_two_id.id,
                                    })
                                    labour.append(labx)
                                self.labour_variable_ids = labour

                            # for over
                            if bom.overhead_ids:
                                for ov in self.overhead_variable_ids:
                                    if ov.finish_good_id != False and len(ov.bom_id) != 0:
                                        if (ov.finish_good_id.name, ov.bom_id.name) not in fg_list:
                                            self.overhead_variable_ids = [(2, ov.id)]
                                for bom_over in bom.overhead_ids:
                                    overx = (0, 0, {
                                        'finish_good_id': finish_good.id,
                                        'bom_id': bom.id,
                                        'overhead_catagory': bom_over.overhead_catagory,
                                        'group_of_product': bom_over.group_of_product.id,
                                        'product_id': bom_over.product_id.id,
                                        'description': bom_over.product_id.name,
                                        'quantity': quantity * bom_over.quantity,
                                        'uom_id': bom_over.uom_id,
                                        'unit_price': bom_over.cost,
                                        'subtotal': bom_over.cost * (quantity * bom_over.quantity),
                                        'operation_two_id': bom_over.operation_two_id.id,
                                    })
                                    overhead.append(overx)
                                self.overhead_variable_ids = overhead

                            # for equip
                            if bom.equipment_ids:
                                for eq in self.equipment_variable_ids:
                                    if eq.finish_good_id != False and len(eq.bom_id) != 0:
                                        if (eq.finish_good_id.name, eq.bom_id.name) not in fg_list:
                                            self.equipment_variable_ids = [(2, eq.id)]
                                for bom_eqp in bom.equipment_ids:
                                    eqpx = (0, 0, {
                                        'finish_good_id': finish_good.id,
                                        'bom_id': bom.id,
                                        'group_of_product': bom_eqp.group_of_product.id,
                                        'product_id': bom_eqp.product_id.id,
                                        'description': bom_eqp.product_id.name,
                                        'quantity': quantity * bom_eqp.quantity,
                                        'uom_id': bom_eqp.uom_id,
                                        'unit_price': bom_eqp.cost,
                                        'subtotal': bom_eqp.cost * (quantity * bom_eqp.quantity),
                                        'operation_two_id': bom_eqp.operation_two_id.id,
                                    })
                                    equip.append(eqpx)
                                self.equipment_variable_ids = equip
                            
                            # for asset
                            if bom.asset_ids:
                                for asse in self.asset_variable_ids:
                                    if asse.finish_good_id != False and len(asse.bom_id) != 0:
                                        if (asse.finish_good_id.name, asse.bom_id.name) not in fg_list:
                                            self.asset_variable_ids = [(2, asse.id)]
                                for bom_ass in bom.asset_ids:
                                    assx = (0, 0, {
                                        'finish_good_id': finish_good.id,
                                        'bom_id': bom.id,
                                        'asset_category_id': bom_ass.asset_category_id.id,
                                        'asset_id': bom_ass.asset_id.id,
                                        'description': bom_ass.asset_id.name,
                                        'quantity': quantity * bom_ass.quantity,
                                        'uom_id': bom_ass.uom_id,
                                        'unit_price': bom_ass.cost,
                                        'subtotal': bom_ass.cost * (quantity * bom_ass.quantity),
                                        'operation_two_id': bom_ass.operation_two_id.id,
                                    })
                                    asset.append(assx)
                                self.asset_variable_ids = asset
                    
                    fg_list.append((finish_good.name, bom.name))

                    # else:
                    #     if rec._origin.quantity:
                    #         if rec._origin.quantity != quantity:
                    #             for mater in self.material_variable_ids:
                    #                 if len(mater.finish_good_id) != 0 and len(mater.bom_id) != 0:
                    #                     if mater.finish_good_id.id == finish_good.id and mater.bom_id.id == bom.id:
                    #                         material = []
                    #                         for bom_mat in bom.bom_line_ids:
                    #                             material = [(1, mater.id, {
                    #                                 'quantity': quantity * bom_mat.product_qty,
                    #                                 # 'uom_id': bom_mat.product_uom_id.id,
                    #                                 'unit_price': bom_mat.cost,
                    #                                 'subtotal': bom_mat.cost * (quantity * bom_mat.product_qty),
                    #                             })]
                    #                         self.material_variable_ids = material
                    #             for labour in self.labour_variable_ids:
                    #                 if  len(
                    #                         labour.finish_good_id) != 0 and len(labour.bom_id) != 0:
                    #                     if labour.finish_good_id.id == finish_good.id and labour.bom_id.id == bom.id:
                    #                         labourx = []
                    #                         for bom_lab in bom.labour_ids:
                    #                             labourx = [(1, labour.id, {
                    #                                 'contractors': bom_lab.contractors,
                    #                                 'time': quantity * bom_lab.time,
                    #                                 'uom_id': bom_lab.uom_id,
                    #                                 'unit_price': bom_lab.cost,
                    #                                 'quantity': bom_lab.contractors * (quantity * bom_lab.time),
                    #                                 'subtotal': bom_lab.cost * (
                    #                                             bom_lab.contractors * (quantity * bom_lab.time)),
                    #                             })]
                    #                         self.labour_variable_ids = labourx
                    #             for overhead in self.overhead_variable_ids:
                    #                 if len(
                    #                         overhead.finish_good_id) != 0 and len(overhead.bom_id) != 0:
                    #                     if overhead.finish_good_id.id == finish_good.id and overhead.bom_id.id == bom.id:
                    #                         overheadx = []
                    #                         for bom_over in bom.overhead_ids:
                    #                             overheadx = [(1, overhead.id, {
                    #                                 'quantity': quantity * bom_over.quantity,
                    #                                 'uom_id': bom_over.uom_id,
                    #                                 'unit_price': bom_over.cost,
                    #                                 'subtotal': bom_over.cost * (quantity * bom_over.quantity)
                    #                             })]
                    #                         self.overhead_variable_ids = overheadx
                    #             for equipment in self.equipment_variable_ids:
                    #                 if len(
                    #                         equipment.finish_good_id) != 0 and len(equipment.bom_id) != 0:
                    #                     if equipment.finish_good_id.id == finish_good.id and equipment.bom_id.id == bom.id:
                    #                         equipmentx = []
                    #                         for bom_eqp in bom.equipment_ids:
                    #                             equipmentx = [(1, equipment.id, {
                    #                                 'quantity': quantity * bom_eqp.quantity,
                    #                                 'uom_id': bom_eqp.uom_id,
                    #                                 'unit_price': bom_eqp.cost,
                    #                                 'subtotal': bom_eqp.cost * (quantity * bom_eqp.quantity)
                    #                             })]
                    #                         self.equipment_variable_ids = equipmentx
                    #             for asset in self.asset_variable_ids:
                    #                 if len(
                    #                         asset.finish_good_id) != 0 and len(asset.bom_id) != 0:
                    #                     if asset.finish_good_id.id == finish_good.id and asset.bom_id.id == bom.id:
                    #                         assetx = []
                    #                         for bom_ass in bom.asset_ids:
                    #                             assetx = [(1, asset.id, {
                    #                                 'quantity': quantity * bom_ass.quantity,
                    #                                 'uom_id': bom_ass.uom_id,
                    #                                 'unit_price': bom_ass.cost,
                    #                                 'subtotal': bom_ass.cost * (quantity * bom_ass.quantity),
                    #                             })]
                    #                         self.asset_variable_ids = assetx
                    #         else:
                    #             for mater in self.material_variable_ids:
                    #                 if len(
                    #                         mater.finish_good_id) != 0 and len(mater.bom_id) != 0:
                    #                     if mater.finish_good_id.id == finish_good.id and mater.bom_id.id == bom.id:
                    #                         material = []
                    #                         for bom_mat in bom.bom_line_ids:
                    #                             material = [(1, mater.id, {
                    #                                 'quantity': quantity * bom_mat.product_qty,
                    #                                 # 'uom_id': bom_mat.product_uom_id.id,
                    #                                 'unit_price': bom_mat.cost,
                    #                                 'subtotal': bom_mat.cost * (quantity * bom_mat.product_qty),
                    #                             })]
                    #                         self.material_variable_ids = material
                    #             for labour in self.labour_variable_ids:
                    #                 if  len(
                    #                         labour.finish_good_id) != 0 and len(labour.bom_id) != 0:
                    #                     if labour.finish_good_id.id == finish_good.id and labour.bom_id.id == bom.id:
                    #                         labourx = []
                    #                         for bom_lab in bom.labour_ids:
                    #                             labourx = [(1, labour.id, {
                    #                                 'contractors': bom_lab.contractors,
                    #                                 'time': quantity * bom_lab.time,
                    #                                 'uom_id': bom_lab.uom_id,
                    #                                 'unit_price': bom_lab.cost,
                    #                                 'quantity': bom_lab.contractors * (quantity * bom_lab.time),
                    #                                 'subtotal': bom_lab.cost * (
                    #                                             bom_lab.contractors * (quantity * bom_lab.time)),
                    #                             })]
                    #                         self.labour_variable_ids = labourx
                    #             for overhead in self.overhead_variable_ids:
                    #                 if len(
                    #                         overhead.finish_good_id) != 0 and len(overhead.bom_id) != 0:
                    #                     if overhead.finish_good_id.id == finish_good.id and overhead.bom_id.id == bom.id:
                    #                         overheadx = []
                    #                         for bom_over in bom.overhead_ids:
                    #                             overheadx = [(1, overhead.id, {
                    #                                 'quantity': quantity * bom_over.quantity,
                    #                                 'uom_id': bom_over.uom_id,
                    #                                 'unit_price': bom_over.cost,
                    #                                 'subtotal': bom_over.cost * (quantity * bom_over.quantity)
                    #                             })]
                    #                         self.overhead_variable_ids = overheadx
                    #             for equipment in self.equipment_variable_ids:
                    #                 if len(
                    #                         equipment.finish_good_id) != 0 and len(equipment.bom_id) != 0:
                    #                     if equipment.finish_good_id.id == finish_good.id and equipment.bom_id.id == bom.id:
                    #                         equipmentx = []
                    #                         for bom_eqp in bom.equipment_ids:
                    #                             equipmentx = [(1, equipment.id, {
                    #                                 'quantity': quantity * bom_eqp.quantity,
                    #                                 'uom_id': bom_eqp.uom_id,
                    #                                 'unit_price': bom_eqp.cost,
                    #                                 'subtotal': bom_eqp.cost * (quantity * bom_eqp.quantity)
                    #                             })]
                    #                         self.equipment_variable_ids = equipmentx
                    #             for asset in self.asset_variable_ids:
                    #                 if len(
                    #                         asset.finish_good_id) != 0 and len(asset.bom_id) != 0:
                    #                     if asset.finish_good_id.id == finish_good.id and asset.bom_id.id == bom.id:
                    #                         assetx = []
                    #                         for bom_ass in bom.asset_ids:
                    #                             assetx = [(1, asset.id, {
                    #                                 'quantity': quantity * bom_ass.quantity,
                    #                                 'uom_id': bom_ass.uom_id,
                    #                                 'unit_price': bom_ass.cost,
                    #                                 'subtotal': bom_ass.cost * (quantity * bom_ass.quantity),
                    #                             })]
                    #                         self.asset_variable_ids = assetx
                        
                    
        
        for mat in self.material_variable_ids:
            if mat.finish_good_id != False and len(mat.bom_id) != 0:
                if (mat.finish_good_id.name, mat.bom_id.name) not in fg_list:
                    self.material_variable_ids = [(2, mat.id)]
        for lab in self.labour_variable_ids:
            if lab.finish_good_id != False and len(lab.bom_id) != 0:
                if (lab.finish_good_id.name, lab.bom_id.name) not in fg_list:
                    self.labour_variable_ids = [(2, lab.id)]
        for ov in self.overhead_variable_ids:
            if ov.finish_good_id != False and len(ov.bom_id) != 0:
                if (ov.finish_good_id.name, ov.bom_id.name) not in fg_list:
                    self.overhead_variable_ids = [(2, ov.id)]
        for asset in self.asset_variable_ids:
            if asset.finish_good_id != False and len(asset.bom_id) != 0:
                if (asset.finish_good_id.name, asset.bom_id.name) not in fg_list:
                    self.asset_variable_ids = [(2, asset.id)]
        for eq in self.equipment_variable_ids:
            if eq.finish_good_id != False and len(eq.bom_id) != 0:
                if (eq.finish_good_id.name, eq.bom_id.name) not in fg_list:
                    self.equipment_variable_ids = [(2, eq.id)]
        for sub in self.subcon_variable_ids:
            if sub.finish_good_id != False and len(sub.bom_id) != 0:
                if (sub.finish_good_id.name, sub.bom_id.name) not in fg_list:
                    self.subcon_variable_ids = [(2, sub.id)]
 
class ToManufactureEstimation(models.Model):
    _name = 'to.manufacture.variable'
    _order = 'sequence'
    _check_company_auto = True
    _rec_name = 'finish_good_id'

    @api.depends('manufacture_id.manufacture_line_variable', 'manufacture_id.manufacture_line_variable.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.manufacture_id.manufacture_line_variable:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('finish_good_id')
    def _onchange_finish_good_id(self):
        if self._origin.finish_good_id._origin.id:
            if self._origin.finish_good_id._origin.id != self.finish_good_id.id:
                self.update({
                    'bom_id': False,
                })
        else:
            self.update({
                'bom_id': False,
            })
        
        if self.finish_good_id:
            product_tmpl = self.finish_good_id.product_tmpl_id.id
            return {
                'domain': {'bom_id': [('product_tmpl_id', '=', product_tmpl)]}
            }
    
    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        if self.bom_id:
            self.quantity = 1.0
            self.uom_id = self.bom_id.product_uom_id.id
        else:
            self.quantity = 1.0
            self.uom_id = False
    
    @api.onchange('quantity')
    def onchange_quantity(self):
        self.write({'onchange_pass': False})

    # Add Quantity with onchange from Bom_id.Product_qty
    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        self.quantity = self.bom_id.product_qty or 1.0
        self.uom_id = self.bom_id.product_uom_id.id or False

    manufacture_id = fields.Many2one('variable.template', string="Variable", ondelete="cascade")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    finish_good_id = fields.Many2one('product.product', 'Finished Goods', required=True, options="{'no_create': True, 'no_create_edit':True}")
    bom_id = fields.Many2one('mrp.bom', 'BOM', required=True)
    company_id = fields.Many2one(related='manufacture_id.company_id', string='Company', readonly=True)
    quantity = fields.Float(string="Quantity", default=1.0)
    uom_id = fields.Many2one('uom.uom', required=True, string="Unit of Measure")
    subtotal = fields.Float(string="Subtotal", compute="_amount_total_manuf")
    currency_id = fields.Many2one('res.currency', compute='get_currency_id', string="Currency")
    onchange_pass = fields.Boolean(string="Pass", default=False)

    @api.depends('manufacture_id.material_variable_ids', 'manufacture_id.labour_variable_ids',
					'manufacture_id.overhead_variable_ids', 'manufacture_id.subcon_variable_ids',
					'manufacture_id.equipment_variable_ids', 'manufacture_id.asset_variable_ids',
					'manufacture_id.material_variable_ids.subtotal', 'manufacture_id.labour_variable_ids.subtotal',
					'manufacture_id.overhead_variable_ids.subtotal', 'manufacture_id.subcon_variable_ids.subtotal',
					'manufacture_id.equipment_variable_ids.subtotal', 'manufacture_id.asset_variable_ids.subtotal')
    def _amount_total_manuf(self):
        for manuf in self:
            total_subtotal = 0.0
            material_ids = manuf.manufacture_id.material_variable_ids.filtered(
                    lambda m: m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for mat in material_ids:
                total_subtotal += mat.subtotal
            
            labour_ids = manuf.manufacture_id.labour_variable_ids.filtered(
                    lambda m: m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for lab in labour_ids:
                total_subtotal += lab.subtotal
            
            overhead_ids = manuf.manufacture_id.overhead_variable_ids.filtered(
                    lambda m: m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for ove in overhead_ids:
                total_subtotal += ove.subtotal
            
            subcon_ids = manuf.manufacture_id.subcon_variable_ids.filtered(
                    lambda m: m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for sub in subcon_ids:
                total_subtotal += sub.subtotal
            
            equipment_ids = manuf.manufacture_id.equipment_variable_ids.filtered(
                    lambda m: m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for equ in equipment_ids:
                total_subtotal += equ.subtotal
            
            asset_ids = manuf.manufacture_id.asset_variable_ids.filtered(
                    lambda m: m.finish_good_id.id == manuf.finish_good_id.id and
                              m.bom_id.id == manuf.bom_id.id)
            for ass in asset_ids:
                total_subtotal += ass.subtotal

            manuf.subtotal = total_subtotal

class MaterialEstimationInherit(models.Model):
    _inherit = 'material.variable'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods', options="{'no_create': True, 'no_create_edit':True}")
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    @api.onchange('finish_good_id')
    def _onchange_finish_good(self):
        self.update({
            'bom_id': False,
            'group_of_product': False,
        })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        self.update({
            'group_of_product': False
        })
    
class LabourEstimationInherit(models.Model):
    _inherit = 'labour.variable'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods', options="{'no_create': True, 'no_create_edit':True}")
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    @api.onchange('finish_good_id')
    def _onchange_finish_good(self):
        self.update({
            'bom_id': False,
            'group_of_product': False,
        })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        self.update({
            'group_of_product': False
        })

class OverheadEstimationInherit(models.Model):
    _inherit = 'overhead.variable'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods', options="{'no_create': True, 'no_create_edit':True}")
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    @api.onchange('finish_good_id')
    def _onchange_finish_good(self):
        self.update({
            'bom_id': False,
            'group_of_product': False,
        })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        self.update({
            'group_of_product': False
        })

class EquipmentEstimationInherit(models.Model):
    _inherit = 'equipment.variable'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods', options="{'no_create': True, 'no_create_edit':True}")
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    @api.onchange('finish_good_id')
    def _onchange_finish_good(self):
        self.update({
            'bom_id': False,
            'group_of_product': False,
        })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        self.update({
            'group_of_product': False
        })

class InternalAssetsEstimationInherit(models.Model):
    _inherit = 'asset.variable'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods', options="{'no_create': True, 'no_create_edit':True}")
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    @api.onchange('finish_good_id')
    def _onchange_finish_good(self):
        self.update({
            'bom_id': False,
            'asset_category_id': False,
        })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        self.update({
            'asset_category_id': False
        })

class SubconEstimationInherit(models.Model):
    _inherit = 'subcon.variable'

    finish_good_id = fields.Many2one('product.product', 'Finished Goods', options="{'no_create': True, 'no_create_edit':True}")
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Consumed in Operation')

    @api.onchange('finish_good_id')
    def _onchange_finish_good(self):
        self.update({
            'bom_id': False,
            'variable': False
        })

    @api.onchange('bom_id')
    def _onchange_bom_handling(self):
        self.update({
            'variable': False
        })

    @api.onchange('variable')
    def onchange_variable(self):
        res = super(SubconEstimationInherit, self).onchange_variable()
        self.update({
            'quantity': 1,
            'unit_price': 1,
        })
        return res