odoo.define("equip3_manuf_kiosk.mrp_work_center", function(require) {
	"use strict";
	var action_manager = require('web.ActionManager');
	var framework = require('web.framework');
	var session = require('web.session');
	var KanbanRecord = require('web.KanbanRecord');
	KanbanRecord.include({
		_ConvertNumToTimeDuration: function(number) {
			var sign = (number >= 0) ? 1 : -1;
			number = number * sign;
			var hour = Math.floor(number);
			var decpart = number - hour;
			var min = 1 / 60;
			decpart = min * Math.round(decpart / min);
			var minute = Math.floor(decpart * 60) + '';
			if(minute.length < 2) {
				minute = '0' + minute;
			}
			sign = sign == 1 ? '' : '-';
			var time = sign + hour + ':' + minute;
			return time;
		},
		formatTimer : function(a) {
			if (a < 10) {
				a = '0' + a;
			}                              
			return a;
		},
		getValueWithDigits : function(a,b) {                           
			return a.toFixed(b);
		},
		_openRecord: function() {
			var self = this
			if(self.modelName === 'mrp.workorder' && self.$el.parents('.o_mrp_workorder_kanban_kisok').length) {
				var def = self._rpc({
					model: 'stock.move',
					method: 'search_read',
					args: [[['mrp_workorder_component_id', '=', self.id]],['product_id', 'product_uom_qty', 'lot_ids', 'lot_name', 'is_scan']],
				}).then(function(result2) {
					var date_start = false;
					var date_end = false;
					var components_ids = result2;
					var workcenter_id = self.recordData.workcenter_id.data.display_name;
					var production_id = self.record.production_id.value
					self._rpc({
						model: 'mrp.workcenter.productivity',
						method: 'search_read',
						args: [[['workorder_id', '=', self.id]],['date_start', 'date_end', 'duration']],
					}).then(function(r3) {
						var time_ids_arr = []
						_.each(r3,function(e){
							time_ids_arr.push(e.id)
						})
						var st_dt_line_id = Math.min.apply(Math, time_ids_arr);
						var ed_dt_line_id = Math.max.apply(Math, time_ids_arr);
						_.each(r3,function(e){
							// console.log('@@@@@@',e.id,r3)
							if(e.id == st_dt_line_id){
								if(e.date_start){
									// console.log(e.date_start,r3)
									date_start = moment(e.date_start).format('MM/DD/YYYY HH:mm:ss')
									// console.log(date_start)
								}
							}
							if(e.id == ed_dt_line_id){
								if(e.date_end){
									// console.log(e.date_end)
									date_end = moment(e.date_end).format('MM/DD/YYYY HH:mm:ss')
									// console.log(date_end)
								}
							}
						})
						var action = {
							type: 'ir.actions.client',
							name: self.recordData.name,
							tag: 'manuf_kiosk_mode',
							recordData: self.recordData,
							workcenter_id: self.workcenter_id,
							workorder_id: self.recordData.id,
							workorder_name: self.recordData.name,
							workorder_dis_name: self.recordData.display_name,
							production_id: self.recordData.production_id,
							product_id: self.recordData.product_id,
							product_uom: self.recordData.product_uom_id,
							qty_production: self.recordData.qty_production,
							production_bom_id: self.recordData.production_bom_id,
							duration_expected: self._ConvertNumToTimeDuration(self.recordData.duration_expected),
							duration: self._ConvertNumToTimeDuration(self.recordData.duration),
							date_planned_start: self.recordData.date_planned_start,
							date_planned_finished: self.recordData.date_planned_finished,
							working_state: self.recordData.working_state,
							state: self.recordData.state,
							is_user_working: self.recordData.is_user_working,
							date_start: date_start ? date_start : false,
							date_end: date_end ? date_end : false,
							components_ids: components_ids,
							workcenter_id: workcenter_id,
							production_id: production_id,
							manuf_kiosk_barcode_mobile: self.recordData.manuf_kiosk_barcode_mobile,
							manuf_kiosk_bm_is_cont_scan: self.recordData.manuf_kiosk_bm_is_cont_scan,
							manuf_kiosk_barcode_mobile_type: self.recordData.manuf_kiosk_barcode_mobile_type,
							manuf_kiosk_bm_is_notify_on_success: self.recordData.manuf_kiosk_bm_is_notify_on_success,
							manuf_kiosk_bm_is_notify_on_fail: self.recordData.manuf_kiosk_bm_is_notify_on_fail,
							manuf_kiosk_bm_is_sound_on_success: self.recordData.manuf_kiosk_bm_is_sound_on_success,
							manuf_kiosk_bm_is_sound_on_fail: self.recordData.manuf_kiosk_bm_is_sound_on_fail,
							consumption_type: self.recordData.consumption_type,
							qty_produced: self.recordData.qty_produced,
							produced_finished_product: self.getValueWithDigits((self.recordData.qty_production-self.recordData.qty_produced), self.recordData.digits_value),
							produced_rejected_product: self.getValueWithDigits(self.recordData.produced_rejected_product, self.recordData.digits_value),
							produced_finished_product_uom_id: self.recordData.produced_finished_product_uom_id,
							produced_rejected_product_uom_id: self.recordData.produced_rejected_product_uom_id,
							digits_value: self.recordData.digits_value,
							is_show_barcode_scanner: self.recordData.is_show_barcode_scanner,
							is_qty_editable: self.recordData.is_qty_editable,
							manuf_kiosk_att_is_cont_scan: self.recordData.manuf_kiosk_att_is_cont_scan,
							manuf_kiosk_att_is_notify_on_success: self.recordData.manuf_kiosk_att_is_notify_on_success,
							manuf_kiosk_att_is_notify_on_fail: self.recordData.manuf_kiosk_att_is_notify_on_fail,
							manuf_kiosk_att_is_sound_on_success: self.recordData.manuf_kiosk_att_is_sound_on_success,
							manuf_kiosk_att_is_sound_on_fail: self.recordData.manuf_kiosk_att_is_sound_on_fail,
							employee_id: self.recordData.employee_id,
						};
						self.do_action(action);
						// self._ConvertNumToTimeDuration(date_start.split(' ')[1].split(':')[1]),
						// self._ConvertNumToTimeDuration(date_end.split(' ')[1].split(':')[1])
						var resume_time = '0:'+self._ConvertNumToTimeDuration(self.recordData.duration)
						var real_hour = '00';
						var real_minute = '00';
						var real_seconds = '00';

						if(resume_time){
							real_hour = self.formatTimer(resume_time.split(':')[0])
							real_minute = self.formatTimer(resume_time.split(':')[1])
							real_seconds = self.formatTimer(resume_time.split(':')[2])
							console.log('****************##########************')
							// document.getElementById("hour").innerHTML = real_hour;
							// document.getElementById("minute").innerHTML = real_minute;
							// document.getElementById("seconds").innerHTML = real_seconds;
						}
						console.log('>>>>>>>>> Yeeee 111111 >>>>>>>>>>>>>>>>>>>>>>>>>>>>',this,resume_time,real_hour,real_minute,real_seconds)

						/*-- Store Lot Products in localstorage --*/
						self._rpc({
							model: 'stock.production.lot',
							method: 'search_read',
							kwargs: {
								domain: [],
								fields: ['id','name','product_id','product_qty'],
							},
						}).then(function(pro_lot) {
							var pro_lot_list = []
							for(var i=0;i<pro_lot.length;i++){
								pro_lot_list.push({
									'id':pro_lot[i]['id'],
									'name':pro_lot[i]['name'],
									'product_id':pro_lot[i]['product_id'][0],
									'product_name':pro_lot[i]['product_id'][1],
									'product_qty':pro_lot[i]['product_qty'],
								})
							}
							localStorage['lot_products'] = JSON.stringify(pro_lot_list)
						})

						/*-- Store Products in localstorage which can access using barcode and default_code fields --*/
						self._rpc({
							model: 'product.product',
							method: 'search_read',
							kwargs: {
								domain: [],
								fields: ['id','name','default_code','barcode', 'sh_qr_code', 'tracking'],
							},
						}).then(function(pro_rec) {
							var pro_dfc_list = []
							for(var i=0;i<pro_rec.length;i++){
								pro_dfc_list.push({
									'id':pro_rec[i]['id'],
									'name':pro_rec[i]['name'],
									'default_code':pro_rec[i]['default_code'],
									'barcode':pro_rec[i]['barcode'],
									'sh_qr_code': pro_rec[i]['sh_qr_code'],
									'tracking': pro_rec[i]['tracking'],
								})
							}
							console.log('::::::::::::::::::::',pro_rec,pro_dfc_list)
							localStorage['products_list'] = JSON.stringify(pro_dfc_list)
						})
						/* -- Store Lot Products in localstorage -- */
						// var pro_lot_mo = new Model('stock.production.lot');
						// var pro_lot_fields = ['id','name','product_id']
						// pro_lot_mo.query(pro_lot_fields).all().then(function(pro_lot){
						//     var pro_lot_list = []
						//     for(var i=0;i<pro_lot.length;i++){
						//         pro_lot_list.push({
						//             'id':pro_lot[i]['id'],
						//             'name':pro_lot[i]['name'],
						//             'product_id':pro_lot[i]['product_id'],
						//         })
						//     }
						//     localStorage['lot_products'] = JSON.stringify(pro_lot_list)
						// })

						//  -- Store Products in localstorage which can access using barcode and default_code fields -- 
						// var pro_pro = new Model('product.product');
						// var pro_flds = ['id','name','default_code','barcode']
						// pro_pro.query(pro_flds).all().then(function(pro_rec){
						//     var pro_dfc_list = []
						//     for(var i=0;i<pro_rec.length;i++){
						//         pro_dfc_list.push({
						//             'id':pro_rec[i]['id'],
						//             'name':pro_rec[i]['name'],
						//             'default_code':pro_rec[i]['default_code'],
						//             'barcode':pro_rec[i]['barcode'],
						//         })
						//     }
						//     localStorage['products_list'] = JSON.stringify(pro_dfc_list)
						// })

						// Store Component data in localstorage
						var component = self._rpc({
							model: 'stock.move',
							method: 'search_read',
							args: [[['mrp_workorder_component_id', '=', self.recordData.id]], ['id', 'product_id', 'product_uom_qty', 'lot_ids', 'lot_name', 'is_scan']],
						}).then(function (result_comp) {
							var compo_list = []
							for(var i=0;i<result_comp.length;i++){
								var lot_ids = []
								for(var j=0;j<result_comp[i]['lot_ids'].length;j++){
									lot_ids.push({
										'id':result_comp[i]['lot_ids'][j],
									})
								}
								var lot_id = false
								if(result_comp[i]['lot_ids'].length > 0){
									lot_id = result_comp[i]['lot_ids'][0]
								}
								if(result_comp[i]['is_scan'] == true){
									compo_list.push({
										'move_id': result_comp[i]['id'],
										'wo_id': self.recordData.id,
										'product_id':result_comp[i]['product_id'][0],
										'product_name':result_comp[i]['product_id'][1],
										'product_uom_qty':result_comp[i]['product_uom_qty'],
										'new_qty': 0,
										'lot_name':result_comp[i]['lot_name'],
										'lot_id':lot_id,
										'lot_ids':lot_ids,
										'sync': true,
										'is_scan': result_comp[i]['is_scan'],
									})
								}else{
									compo_list.push({
										'move_id': result_comp[i]['id'],
										'wo_id': self.recordData.id,
										'product_id':result_comp[i]['product_id'][0],
										'product_name':result_comp[i]['product_id'][1],
										'product_uom_qty':0,
										'new_qty': 0,
										'lot_name':result_comp[i]['lot_name'],
										'lot_id': lot_id,
										'lot_ids':lot_ids,
										'sync': true,
										'is_scan': result_comp[i]['is_scan'],
									})
								}
								
							}
							console.log('Comp List:: ',result_comp,compo_list)
							localStorage['equip_component_list'] = JSON.stringify(compo_list)
						});

						// Store WO data
						var wo_info = []
						wo_info.push({
							'id': self.recordData.id,
							'produced_finished_goods': self.recordData.qty_production - self.recordData.qty_produced,
							'produced_rejected_goods': 0,
							'done_method_sync': false,
						})
						localStorage['wo_info'] = JSON.stringify(wo_info)
					})
				});
			} else {
				self._super.apply(this, arguments);
			}
		},
	});
});