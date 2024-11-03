odoo.define('equip3_manuf_kiosk.manuf_kiosk', function (require) {
	"use strict";
	var AbstractAction = require('web.AbstractAction');
	var core = require('web.core');
	var field_utils = require('web.field_utils');
	var QWeb = core.qweb;
	var _t = core._t;

	var hour = 0;
	var minute = 0;
	var seconds = 0;
	var totalSeconds = 0;

	var intervalId = null;
	let selectedDeviceId;
	const codeReader = new ZXing.BrowserMultiFormatReader();
	var Dialog = require('web.Dialog');
	var NotificationService = require("web.NotificationService");

	window.addEventListener('offline', function(e) {
		$('.wifi_in').css('color', 'red');
	  }, false);
	window.addEventListener('online', function(e) {
		$('.wifi_in').css('color', 'green');
		$(".button_sync").trigger("click");
	}, false);

	// Call sync method
	setInterval(function(){
		if(navigator.onLine){
			$(".button_sync").trigger("click");	
		}
	}, 300000);

	var ManufKiosk = AbstractAction.extend({
		events: {
			"click .button_start": "_StartWorkorder",
			"click .button_pause": "_PauseWorkorder",
			"click .button_done": "_DoneWorkorder",
			"click .button_block": "_BlockWorkorder",
			"click .button_unblock": "_UnblockWorkorder",
			'click .js_cls_manuf_kiosk_barcode_mobile_start_btn': '_onClickCameraStartBtn',
			'click .js_cls_manuf_kiosk_open_scan_modal': '_onClickOpenScanModal',
			'click .close_scan_modal': '_onClickCloseScanModal',
			'click .js_cls_manuf_kiosk_att_start_btn': '_onClickCameraStartBtnAtt',
			'click .js_cls_manuf_kiosk_barcode_mobile_reset_btn': '_onClickCameraResetBtn',
			'click .js_cls_manuf_kiosk_att_reset_btn': '_onClickCameraResetBtnAtt',
			'click .js_cls_manuf_kiosk_barcode_mobile_add_comp': '_onClickAddCompBtn',
			'click .js_cls_manuf_kiosk_emp_add': '_onClickAddEmpBtn',
			'keydown .manuf_kiosk_barcode_mobile_manual': '_onClickAddCompPress',
			'keydown .manuf_kiosk_emp_manual': '_onClickAddEmpPress',
			'change .js_cls_produced_finished_goods': '_onChangeFinRej',
			'change .js_cls_produced_rejected_goods': '_onChangeFinRej',
			'click .button_sync': '_SyncData',
			'click .button_close': '_close',
		},
		_ConvertNumToTimeDuration: function (number) {
			var sign = (number >= 0) ? 1 : -1;
			number = number * sign;
			var hour = Math.floor(number);
			var decpart = number - hour;
			var min = 1 / 60;
			decpart = min * Math.round(decpart / min);
			var minute = Math.floor(decpart * 60) + '';
			if (minute.length < 2) {
				minute = '0' + minute;
			}
			sign = sign == 1 ? '' : '-';
			var time = sign + hour + ':' + minute;
			return time;
		},
		formatTimer: function (a) {
			console.log(typeof (a))
			if (a < 10 && typeof (a) != 'string') {
				a = '0' + a;
			}
			return a;
		},
		startTimer: function () {
			console.log('mmmmmmmmmmmmmmmmmm', $("#hour"), $("#hour").length)
			var self = this;
			++totalSeconds;
			// console.log(totalSeconds)
			// var h = Math.floor(resume_time.split(':')[0] / 60);
			// 		var m = resume_time.split(':')[0] % 60;
			// 		var s = resume_time.split(':')[1]
			hour = self.formatTimer(Math.floor(totalSeconds / 3600));
			minute = self.formatTimer(Math.floor((totalSeconds - hour * 3600) / 60));
			seconds = self.formatTimer(totalSeconds - (hour * 3600 + minute * 60));

			if ($("#hour").length > 0) {
				document.getElementById("hour").innerHTML = hour;
				document.getElementById("minute").innerHTML = minute;
				document.getElementById("seconds").innerHTML = seconds;
			}
		},
		_StartWorkorder: function (e) {
			var self = this;
			var bt_st = document.getElementById("button_start");
			var bt_done = document.getElementById("button_done");
			var bt_puse = document.getElementById("button_pause");
			var bt_block = document.getElementById("button_block");
			var bt_unblock = document.getElementById("button_unblock");
			/* Store start time in local */
			var in_date = new Date();
			var str = (in_date.getMonth() + 1) + '/' + in_date.getDate() + '/' + in_date.getFullYear() + ' ' + in_date.getHours() + ":" + in_date.getMinutes() + ":" + in_date.getSeconds();
			console.log('in_date', str)
			var time_ids_list = []
			time_ids_list.push({
				'start': in_date,
			})
			localStorage['time_ids_list'] = JSON.stringify(time_ids_list)
			intervalId = setInterval(function () { self.startTimer() }, 1000);
			self._rpc({
				model: 'mrp.workorder',
				method: 'kiosk_start_workorder',
				args: [
					[], this.workorder_id
				],
			}).then(function (res) {
				var resume_time = '00:' + self._ConvertNumToTimeDuration(res)
				var kiosk_hms = resume_time;
				var split_time = kiosk_hms.split(':'); // split it at the colons

				// minutes are worth 60 seconds. Hours are worth 60 minutes.
				var seconds = (+split_time[0]) * 60 * 60 + (+split_time[1]) * 60 + (+split_time[2]);

				console.log(seconds);
				totalSeconds = 0;
				totalSeconds += seconds;
				console.log('>>>>>>>>>>>>>>>>>>>>>>>>0', resume_time, totalSeconds, seconds, split_time)
			})
			if (bt_st) {
				bt_st.style.display = "none";
			}
			if (bt_done) {
				bt_done.style.display = "block";
			}
			if (bt_puse) {
				bt_puse.style.display = "block";
			}
			if (bt_block) {
				bt_block.style.display = "block";
			}
			if (bt_unblock) {
				bt_unblock.style.display = "none";
			}
			document.getElementById('start_date').innerHTML = str
		},
		_PauseWorkorder: function (e) {
			var self = this;
			var bt_st = document.getElementById("button_start");
			var bt_done = document.getElementById("button_done");
			var bt_puse = document.getElementById("button_pause");
			var bt_block = document.getElementById("button_block");
			var bt_unblock = document.getElementById("button_unblock");
			// var get_time_ids_list = JSON.parse(localStorage['time_ids_list'])
			// _.each(get_time_ids_list,function(rec){
			//   if(get_time_ids_list[rec]['s']){
			// 		console.log('---che',get_time_ids_list[rec]['s'])
			// 	}else{
			// 		console.log('---nathi',get_time_ids_list[rec])
			// 	}
			// })
			if (intervalId) {
				clearInterval(intervalId);
			}
			self._rpc({
				model: 'mrp.workorder',
				method: 'kiosk_pause_workorder',
				args: [
					[], this.workorder_id
				],
			}).then(function (res) {
				$('#duration')[0].innerHTML = self._ConvertNumToTimeDuration(res)
			})
			if (bt_st) {
				bt_st.style.display = "block";
			}
			if (bt_done) {
				bt_done.style.display = "none";
			}
			if (bt_puse) {
				bt_puse.style.display = "none";
			}
			if (bt_block) {
				bt_block.style.display = "block";
			}
			if (bt_unblock) {
				bt_unblock.style.display = "none";
			}
		},
		_DoneWorkorder: function (e) {
			var self = this;
			var bt_st = document.getElementById("button_start");
			var bt_done = document.getElementById("button_done");
			var bt_puse = document.getElementById("button_pause");
			var bt_block = document.getElementById("button_block");
			if (intervalId) {
				clearInterval(intervalId);
			}
			if (bt_done) {
				bt_done.style.display = "none";
			}
			if (bt_puse) {
				bt_puse.style.display = "none";
			}
			if (bt_block) {
				bt_block.style.display = "block";
			}
			var in_date = new Date();
			var str = (in_date.getMonth() + 1) + '/' + in_date.getDate() + '/' + in_date.getFullYear() + ' ' + in_date.getHours() + ":" + in_date.getMinutes() + ":" + in_date.getSeconds();
			document.getElementById('end_date').innerHTML = str

			if(navigator.onLine){
				var wo_info = JSON.parse(localStorage.getItem('wo_info'));
				var new_wo_info = wo_info.map(function (item) {
					item.done_method_sync = true;
					return item;
				});
				localStorage['wo_info'] = JSON.stringify(new_wo_info);
				$(".button_sync").trigger("click");
			} else {
				var wo_info = JSON.parse(localStorage.getItem('wo_info'));
				var new_wo_info = wo_info.map(function (item) {
					item.done_method_sync = true;
					return item;
				});
				localStorage['wo_info'] = JSON.stringify(new_wo_info);
			}
		},
		_BlockWorkorder: function (e) {
			var self = this;
			var bt_st = document.getElementById("button_start");
			var bt_done = document.getElementById("button_done");
			var bt_puse = document.getElementById("button_pause");
			var bt_block = document.getElementById("button_block");
			var bt_unblock = document.getElementById("button_unblock");
			if (intervalId) {
				clearInterval(intervalId);
			}
			totalSeconds = 0;
			if (bt_st) {
				bt_st.style.display = "block";
			}
			if (bt_done) {
				bt_done.style.display = "none";
			}
			if (bt_puse) {
				bt_puse.style.display = "none";
			}
			if (bt_block) {
				bt_block.style.display = "none";
			}
			if (bt_unblock) {
				bt_unblock.style.display = "block";
			}
			return self.do_action({
				type: 'ir.actions.act_window',
				name: _t('Block Workcenter'),
				target: 'new',
				res_id: this.workorder_id,
				res_model: 'mrp.workcenter.productivity',
				context: { 'form_view_ref': 'mrp.mrp_workcenter_block_wizard_form' },
				views: [[false, 'form']],
			});
			// })
		},
		_UnblockWorkorder: function (e) {
			var self = this;
			var bt_st = document.getElementById("button_start");
			var bt_done = document.getElementById("button_done");
			var bt_puse = document.getElementById("button_pause");
			var bt_block = document.getElementById("button_block");
			var bt_unblock = document.getElementById("button_unblock");
			if (intervalId) {
				clearInterval(intervalId);
			}
			totalSeconds = 0;
			self._rpc({
				model: 'mrp.workorder',
				method: 'kiosk_unblock_workorder',
				args: [
					[], this.workorder_id
				],
			}).then(function (res) {
				// $('#duration')[0].innerHTML = self._ConvertNumToTimeDuration(res)
			})
			if (bt_st) {
				bt_st.style.display = "block";
			}
			if (bt_done) {
				bt_done.style.display = "none";
			}
			if (bt_puse) {
				bt_puse.style.display = "none";
			}
			if (bt_block) {
				bt_block.style.display = "block";
			}
			if (bt_unblock) {
				bt_unblock.style.display = "none";
			}
			// })
		},
		/**
	   * Add list of cameras as a options in selection.
	   * 
	   */
		shUpdateCameraControl: function () {
			var self = this;
			codeReader
				.getVideoInputDevices()
				.then(function (result) {
					// Find camera Selection
					var $camSelect = $(document).find(".js_cls_manuf_kiosk_barcode_mobile_cam_select");
					/*
					if ($camSelect.length <= 0) {
						location.reload();
					}
					*/
					if ($camSelect.length > 0) {
						//Add list of cameras as a options in selection.
						_.each(result, function (item) {
							selectedDeviceId = item.deviceId;
							var optionText = item.label;
							var optionValue = item.deviceId;
							$camSelect.append(new Option(optionText, optionValue));
						});

						// Make selected camera selected from local storage.
						var selected_cam = localStorage.getItem('manuf_kiosk_barcode_mobile_selected_device_id') || false;
						if (selected_cam && $camSelect.find('option[value=' + selected_cam + ']').length) {
							var cam_option = $camSelect.find('option[value=' + selected_cam + ']');

							if (cam_option) {
								cam_option.attr('selected', true);
							}
						}

						// TODO: local storage camera assign to selectedDeviceId



					}
					//Trigger Start Click Button Here
					// $(".js_cls_manuf_kiosk_barcode_mobile_start_btn").trigger("click");
				});
		},
		_close: function () {
			var self = this;
			var def = self._rpc({
				model: 'mrp.workorder',
				method: 'get_kiosk_action',
				args: [self.workorder_id],
			}).then(function (result) {
				if (result.action) {
					self.do_action(result.action);
				}
			});
		},

		_show_notification: function (type, message) {
			var self = this;
			if(type == 'success'){
				if (self.manuf_kiosk_bm_is_notify_on_success){
					self.do_notify(false, _t(message));
				}
				if (self.manuf_kiosk_bm_is_sound_on_success) {
					// play success sound
					var src = "/equip3_manuf_kiosk/static/src/sounds/picked.wav";
					$('body').append('<audio src="' + src + '" autoplay="true"></audio>');
				}
			}
			else if(type == 'warning'){
				if(self.manuf_kiosk_bm_is_notify_on_fail){
					self.do_warn(false, _t(message));
				}
				if (self.manuf_kiosk_bm_is_sound_on_fail) {
					//play failed sound
					var src = "/equip3_manuf_kiosk/static/src/sounds/error.wav";
					$('body').append('<audio src="' + src + '" autoplay="true"></audio>');
				}
			}
		},


		/**
		 * ****************************************
		 * Change Camera Selection
		 * ****************************************
		 */
		_onChangeCameraSelection: function (ev) {
			selectedDeviceId = $(ev.currentTarget).val();
			// Save Selected Camera in Session and load that camera in next scan.
			localStorage.setItem('manuf_kiosk_barcode_mobile_selected_device_id', selectedDeviceId);

			$(document).find(".js_cls_manuf_kiosk_barcode_mobile_start_btn").trigger("click");


		},

		_onChangeFinRej: function (ev) {
			var self = this;
			var wo_info = JSON.parse(localStorage.getItem('wo_info'));
			var new_wo_info = wo_info.map(function (item) {
				item.produced_finished_goods = parseInt($('input[name="produced_finished_goods"]').val());
				item.produced_rejected_goods = parseInt($('input[name="produced_rejected_goods"]').val());
				return item;
			});
			localStorage['wo_info'] = JSON.stringify(new_wo_info);
		},


		/**
		 * ****************************************
		 * Reset Camera Button
		 * ****************************************
		 */

		_onClickCameraResetBtn: function (ev) {
			var self = this;
			//RESET READER
			codeReader.reset();

			//HIDE VIDEO
			$(".js_cls_manuf_kiosk_barcode_mobile_vid_div").hide();

			//HIDE STOP BUTTON
			$(".js_cls_manuf_kiosk_barcode_mobile_reset_btn").hide();

		},


		/**
		 * ****************************************
		 * Start Camera Button
		 * ****************************************
		 */

		_onClickCameraStartBtn: function (ev) {
			var self = this;
			self.shUpdateCameraControl();
			//SHOW VIDEO
			$(".js_cls_manuf_kiosk_barcode_mobile_vid_div").show();

			//SHOW STOP BUTTON
			$(".js_cls_manuf_kiosk_barcode_mobile_reset_btn").show();


			if (self.manuf_kiosk_bm_is_cont_scan) {
				self.decodeContinuous(codeReader, selectedDeviceId);
			} else {
				self.decodeOnce(codeReader, selectedDeviceId);
			}

		},
		/**
		 * ****************************************
		 * Add componant on enter press
		 * ****************************************
		 */

		_onClickAddCompPress: function (ev) {
			var self = this;
			var barcode = $('input[name="manuf_kiosk_barcode_mobile_manual"]').val();
			

			if (ev.keyCode === 13) {
				if (barcode != "") {
					// self._onBarcodeScanned(barcode, self.workorder_id)
					self._onBarcodeScannedL(barcode, self.workorder_id)
				} else {
					self._show_notification('warning', 'Please enter a barcode');
				}
			}

		},

		/**
		 * ****************************************
		 * Add componant
		 * ****************************************
		 */

		_onClickAddCompBtn: function (ev) {
			var self = this;
			var barcode = $('input[name="manuf_kiosk_barcode_mobile_manual"]').val();
			
			if (barcode != "") {
				// self._onBarcodeScanned(barcode, self.workorder_id)
				self._onBarcodeScannedL(barcode, self.workorder_id)
			} else {
				self._show_notification('warning', 'Please enter a barcode');
			}
		},

		/**
		 * ****************************************
		 * Decode Scanned Barcode Method
		 * ****************************************
		 */
		 decodeContinuous: function (codeReader, selectedDeviceId) {
			var selected_cam = localStorage.getItem('manuf_kiosk_barcode_mobile_selected_device_id') || selectedDeviceId;
			var self = this;
			codeReader.decodeFromInputVideoDeviceContinuously(selectedDeviceId, "js_id_manuf_kiosk_bm_video", (result, err) => {
				if (result) {
					$('input[name="manuf_kiosk_barcode_mobile"]').val(result.text);
					document.getElementById("js_id_manuf_kiosk_barcode_mobile_result").textContent = result.text;
					// self._onBarcodeScanned(result.text, self.workorder_id)
					self._onBarcodeScannedL(result.text, self.workorder_id)
				}
				if (err) {
					// console.error(err);
				}
			});
		},
		/**
		 * ****************************************
		 * Decode Scanned Barcode Method
		 * ****************************************
		 */
		decodeOnce: function (codeReader, selectedDeviceId) {
			var selected_cam = localStorage.getItem('manuf_kiosk_barcode_mobile_selected_device_id') || selectedDeviceId;
			var self = this;
			codeReader
				.decodeFromInputVideoDevice(selected_cam, "js_id_manuf_kiosk_bm_video")
				.then((result) => {
					$('input[name="manuf_kiosk_barcode_mobile"]').val(result.text);
					document.getElementById("js_id_manuf_kiosk_barcode_mobile_result").textContent = result.text;
					// self._onBarcodeScanned(result.text, self.workorder_id)
					self._onBarcodeScannedL(result.text, self.workorder_id)
				})
				.catch((err) => {
					// console.error(err);
				});
		},

		/**
	   * ****************************************
	   * _onBarcodeScanned method
	   * It will be called when barcode is scanned and save data int DB and reload the component.
	   * ****************************************
	   */
		_onBarcodeScanned: function (barcode, wo_id) {
			var self = this;
			this._rpc({
				model: 'mrp.workorder',
				method: 'kiosk_mobile_scan',
				args: [barcode, wo_id,],
			})
				.then(function (result) {
					if (result.action) {
						// play success sound
						var src = "/equip3_manuf_kiosk/static/src/sounds/picked.wav";
						$('body').append('<audio src="' + src + '" autoplay="true"></audio>');
						self._loadComponentTableLS();

					} else if (result.warning) {
						//play failed sound
						var src = "/equip3_manuf_kiosk/static/src/sounds/error.wav";
						$('body').append('<audio src="' + src + '" autoplay="true"></audio>');

						// self.do_warn(result.warning);
					}
					$('input[name="manuf_kiosk_barcode_mobile_manual"]').val("")
				}, function () {
					// core.bus.on('barcode_scanned', self, self._onBarcodeScanned);
				});
		},
		/**
		 * ****************************************
		 * _onBarcodeScannedL method
		 * It will be called when barcode is scanned and save data int DB and reload the component.
		 * ****************************************
		*/
		_onBarcodeScannedL: function (barcode, wo_id) {
			var self = this;
			console.log("self.manuf_kiosk_barcode_mobile_type", self.manuf_kiosk_barcode_mobile_type)
			// Find and Save data into LS
			var products = JSON.parse(localStorage.getItem('products_list'));
			var components = JSON.parse(localStorage.getItem('equip_component_list'));
			var lots = JSON.parse(localStorage.getItem('lot_products'));

			// When setting MBS >  Lots/Serial numbers ticked
			if(self.manuf_kiosk_barcode_mobile_type == 'lot_sn'){
				console.log("Scan by Lots/Serial numbers")
				self._scanWithLotSN(barcode, wo_id)
			}
			else if (self.manuf_kiosk_barcode_mobile_type == 'int_ref'){
				console.log("Scan by Internal Reference")
				self._scanWithIntRef(barcode, wo_id)
			}
			else if (self.manuf_kiosk_barcode_mobile_type == 'barcode'){
				console.log("Scan by Barcode")
				self._scanWithBarcode(barcode, wo_id)
			}
			else if (self.manuf_kiosk_barcode_mobile_type == 'qr_code'){
				console.log("Scan by QR code")
				self._scanWithQrcode(barcode, wo_id)
			}
			else if (self.manuf_kiosk_barcode_mobile_type == 'all'){
				console.log("Scan by All")
				if (lots.find(x => x.name === barcode)){
					console.log("_scanWithLotSN")
					self._scanWithLotSN(barcode, wo_id)
				}
				else if(products.find(x => x.default_code === barcode)){
					console.log("_scanWithIntRef")
					self._scanWithIntRef(barcode, wo_id)
				}
				else if(products.find(x => x.barcode === barcode)){
					console.log("_scanWithBarcode")
					self._scanWithBarcode(barcode, wo_id)
				}
				else if(products.find(x => x.sh_qr_code === barcode)){
					console.log("_scanWithQrcode")
					self._scanWithQrcode(barcode, wo_id)
				}
				else{
					self._show_notification('warning', _t("Product not found."));
				}
			}
		},

		/**
		 * ****************************************
		 * _scanWithLotSN method
		 * It will be called when Product Scan Options is Lots/Serial numbers.
		 * ****************************************
	   	*/
		_scanWithLotSN: function (barcode, wo_id) {
			var self = this;
			// Find and Save data into LS
			var products = JSON.parse(localStorage.getItem('products_list'));
			var components = JSON.parse(localStorage.getItem('equip_component_list'));
			var lots = JSON.parse(localStorage.getItem('lot_products'));

			var lot = lots.find(x => x.name === barcode); 
			if (lot && lot.product_id > 0) {
				var product = products.find(x => x.id === lot.product_id);
				// if user scanned a Lot Number
				if (product && product.tracking === 'lot') {
					var comps = components.filter(x => x.product_id === product.id);
					var comp = comps.find(x => x.lot_id === lot.id);
					if(comps.length > 0 && !comp){
						var comp = comps.find(x => x.product_id === product.id);
					}
					if (comp) {
						// If product already listed on component table and lot/serial number field is blank
						if (comp.lot_name == "" || comp.lot_name == null) {
							var lot_ids = []
							lot_ids.push({
								'id': lot.id,
							})
							var comp_list_new = components.map(function (item) {
								if (item.product_id === comp.product_id) {
									item.product_uom_qty = item.product_uom_qty + 1;
									item.sync = false;
									item.is_scan = true;
									item.new_qty = item.new_qty + 1;
									item.lot_name = barcode;
									item.lot_id = lot.id;
									item.lot_ids = lot_ids;
								}
								return item;
							});
							localStorage.setItem('equip_component_list', JSON.stringify(comp_list_new));
							self._loadComponentTableLS();
							self._show_notification('success', _t("Product added successfully."));
						}
						// If product already listed on component and lot/serial number filled (point x) and the number scanned is same as the point x
						else if (comp.lot_name == barcode) {
							var comp_list_new = components.map(function (item) {
								if (item.product_id === product.id && item.lot_name == barcode) {
									item.product_uom_qty = item.product_uom_qty + 1;
									item.sync = false;
									item.is_scan = true;
									item.new_qty = item.new_qty + 1;
								}
								return item;
							});
							localStorage.setItem('equip_component_list', JSON.stringify(comp_list_new));
							self._loadComponentTableLS();
							self._show_notification('success', _t("Product added successfully."));
						}
						// If product already listed on component and lot/serial number filled (point x) and the number scanned is different from the point x
						else if (comp.lot_name != barcode) {
							var n_compo = JSON.parse(localStorage.getItem('equip_component_list'))
							var lot_ids = []
								lot_ids.push({
									'id': lot.id,
								})
							n_compo.push({
								'move_id': false,
								'wo_id': self.workorder_id,
								'product_id': product.id,
								'product_name': product.name,
								'product_uom_qty': 1,
								'new_qty': 1,
								'lot_name': lot.name,
								'lot_id': lot.id,
								'lot_ids':lot_ids,
								'sync': false,
								'is_scan': true,
							});
							localStorage.setItem('equip_component_list', JSON.stringify(n_compo));
							self._loadComponentTableLS();
							self._show_notification('success', _t("Product added successfully."));
						}
					}
					// If product not listed on component table
					else if (!comp) {
						if(self.consumption_type == 'strict'){
							self._show_notification('warning', _t("You scanned different product than expected for the following Bill of Material."));
						}else{
							var n_compo = JSON.parse(localStorage.getItem('equip_component_list'))
							var lot_ids = []
								lot_ids.push({
									'id': lot.id,
								})
							n_compo.push({
								'move_id': false,
								'wo_id': self.workorder_id,
								'product_id': product.id,
								'product_name': product.name,
								'product_uom_qty': 1,
								'new_qty': 1,
								'lot_name': lot.name,
								'lot_id': lot.id,
								'lot_ids':lot_ids,
								'sync': false,
								'is_scan': true,
							});
							localStorage.setItem('equip_component_list', JSON.stringify(n_compo));
							self._loadComponentTableLS();
							self._show_notification('success', _t("Product added successfully."));
						}
					}

				}
				// if user scanned a Lot Number
				else if (product && product.tracking === 'serial') {
					// var comp = components.find(x => x.product_id === product.id);
					var comps = components.filter(x => x.product_id === product.id);
					var comp = comps.find(x => x.lot_id === lot.id);
					if (comp) {
						// If product already listed on component table and lot/serial number field is blank
						if (comp.lot_name == "" || comp.lot_name == null) {
							var lot_ids = []
							lot_ids.push({
								'id': lot.id,
							})
							var comp_list_new = components.map(function (item) {
								if (item.product_id === comp.product_id) {
									item.product_uom_qty = item.product_uom_qty + 1;
									item.sync = false;
									item.is_scan = true;
									item.new_qty = item.new_qty + 1;
									item.lot_name = barcode;
									item.lot_id = lot.id;
									item.lot_ids = lot_ids;
								}
								return item;
							});
							localStorage.setItem('equip_component_list', JSON.stringify(comp_list_new));
							self._loadComponentTableLS();
							self._show_notification('success', _t("Product added successfully."));
						}
						else if (comp.lot_name == barcode) {
							console.log("Product already added with this serial number")
							// alert("The Serial Number has been scanned.")
							Dialog.alert(self, "The Serial Number has been scanned.");
						}
						else if (comp.lot_name != barcode){
							var n_compo = JSON.parse(localStorage.getItem('equip_component_list'))
							var lot_ids = []
								lot_ids.push({
									'id': lot.id,
								})
							n_compo.push({
								'move_id': false,
								'wo_id': self.workorder_id,
								'product_id': product.id,
								'product_name': product.name,
								'product_uom_qty': 1,
								'new_qty': 1,
								'lot_name': lot.name,
								'lot_id': lot.id,
								'lot_ids':lot_ids,
								'sync': false,
								'is_scan': true,
							});
							localStorage.setItem('equip_component_list', JSON.stringify(n_compo));
							self._loadComponentTableLS();
							self._show_notification('success', _t("Product added successfully."));
						}
					}
					// If product not listed on component table
					else if (!comp) {
						if(self.consumption_type == 'strict'){
							self._show_notification('warning', _t("You scanned different product than expected for the following Bill of Material."));
						}else{
							var n_compo = JSON.parse(localStorage.getItem('equip_component_list'))
							var lot_ids = []
								lot_ids.push({
									'id': lot.id,
								})
							n_compo.push({
								'move_id': false,
								'wo_id': self.workorder_id,
								'product_id': product.id,
								'product_name': product.name,
								'product_uom_qty': 1,
								'new_qty': 1,
								'lot_name': lot.name,
								'lot_id': lot.id,
								'lot_ids':lot_ids,
								'sync': false,
								'is_scan': true,
							});
							localStorage.setItem('equip_component_list', JSON.stringify(n_compo));
							self._loadComponentTableLS();
							self._show_notification('success', _t("Product added successfully."));
						}
					}
				}
			}
		},

		/**
		 * ****************************************
		 * _scanWithIntRef method
		 * It will be called when Product Scan Options is Internal Reference.
		 * ****************************************
	   	*/
		_scanWithIntRef: function (barcode, wo_id) {
			var self = this;
			// Find and Save data into LS
			var products = JSON.parse(localStorage.getItem('products_list'));
			var components = JSON.parse(localStorage.getItem('equip_component_list'));
			var lots = JSON.parse(localStorage.getItem('lot_products'));

			var product = products.find(x => x.default_code === barcode);
			if (product) {
				var comp = components.find(x => x.product_id === product.id);
				if (comp) {
					if(product.tracking != 'serial'){
						var comp_list_new = components.map(function (item) {
							if (item.product_id === product.id) {
								item.product_uom_qty = item.product_uom_qty + 1;
								item.sync = false;
								item.is_scan = true;
								item.new_qty = item.new_qty + 1;
							}
							return item;
						});
						localStorage.setItem('equip_component_list', JSON.stringify(comp_list_new));
						self._loadComponentTableLS();
						self._show_notification('success', _t("Product added successfully."));
					}
				} else {
					if(self.consumption_type == 'strict'){
						self._show_notification('warning', _t("You scanned different product than expected for the following Bill of Material."));
					}else{
						var lot = lots.filter(x => x.product_id === product.id);
						var lot  = lot[0];
						var n_compo = JSON.parse(localStorage.getItem('equip_component_list'))
						if (lot) {
							var lot_ids = []
							lot_ids.push({
								'id': lot.id,
							})
							n_compo.push({
								'move_id': false,
								'wo_id': self.workorder_id,
								'product_id': product.id,
								'product_name': product.name,
								'product_uom_qty': 1,
								'new_qty': 1,
								'lot_name': lot.name,
								'lot_id': lot.id,
								'lot_ids':lot_ids,
								'sync': false,
								'is_scan': true,
							});
						}else{
							n_compo.push({
								'move_id': false,
								'wo_id': self.workorder_id,
								'product_id': product.id,
								'product_name': product.name,
								'product_uom_qty': 1,
								'new_qty': 1,
								'lot_name': "",
								'lot_id': "",
								'lot_ids': "",
								'sync': false,
								'is_scan': true,
							});
						}
						localStorage.setItem('equip_component_list', JSON.stringify(n_compo));
						self._loadComponentTableLS();
						self._show_notification('success', _t("Product added successfully."));
					}
				}
			}
			else {
				console.log('No product found')
				self._show_notification('warning', _t("Product not found."));
			}
			console.log("product", product)
		},

		/**
		 * ****************************************
		 * _scanWithBarcode method
		 * It will be called when Product Scan Options is Barcode.
		 * ****************************************
	   	*/
		_scanWithBarcode: function (barcode, wo_id) {
			var self = this;
			// Find and Save data into LS
			var products = JSON.parse(localStorage.getItem('products_list'));
			var components = JSON.parse(localStorage.getItem('equip_component_list'));
			var lots = JSON.parse(localStorage.getItem('lot_products'));

			var product = products.find(x => x.barcode === barcode);
			if (product) {
				var comp = components.find(x => x.product_id === product.id);
				if (comp) {
					if(product.tracking != 'serial'){
						var comp_list_new = components.map(function (item) {
							if (item.product_id === product.id) {
								if(item.lot_name == "" || item.lot_name == null){
									var lot = lots.filter(x => x.product_id === product.id);
									var lot  = lot[0];
									if(lot){
										var lot_ids = []
										lot_ids.push({
											'id': lot.id,
										})
										item.lot_name = lot.name;
										item.lot_id = lot.id;
										item.lot_ids = lot_ids;
										item.product_uom_qty = item.product_uom_qty + 1;
										item.sync = false;
										item.is_scan = true;
										item.new_qty = item.new_qty + 1;
									}else{
										item.product_uom_qty = item.product_uom_qty + 1;
										item.sync = false;
										item.is_scan = true;
										item.new_qty = item.new_qty + 1;
									}
								}else{
									item.product_uom_qty = item.product_uom_qty + 1;
									item.sync = false;
									item.is_scan = true;
									item.new_qty = item.new_qty + 1;
								}		
							}
							return item;
						});
						localStorage.setItem('equip_component_list', JSON.stringify(comp_list_new));
						self._loadComponentTableLS();
						self._show_notification('success', _t("Product added successfully."));
					}
				} else {
					if(self.consumption_type == 'strict'){
						self._show_notification('warning', _t("You scanned different product than expected for the following Bill of Material."));
					}else{
						var lot = lots.filter(x => x.product_id === product.id);
						var lot  = lot[0];
						var n_compo = JSON.parse(localStorage.getItem('equip_component_list'))
						if (lot) {
							var lot_ids = []
							lot_ids.push({
								'id': lot.id,
							})
							n_compo.push({
								'move_id': false,
								'wo_id': self.workorder_id,
								'product_id': product.id,
								'product_name': product.name,
								'product_uom_qty': 1,
								'new_qty': 1,
								'lot_name': lot.name,
								'lot_id': lot.id,
								'lot_ids':lot_ids,
								'sync': false,
								'is_scan': true,
							});
						}else{
							n_compo.push({
								'move_id': false,
								'wo_id': self.workorder_id,
								'product_id': product.id,
								'product_name': product.name,
								'product_uom_qty': 1,
								'new_qty': 1,
								'lot_name': "",
								'lot_id': "",
								'lot_ids': "",
								'sync': false,
								'is_scan': true,
							});
						}
						localStorage.setItem('equip_component_list', JSON.stringify(n_compo));
						self._loadComponentTableLS();
						self._show_notification('success', _t("Product added successfully."));
					}
				}
			}
			else {
				console.log('No product found')
				self._show_notification('warning', _t("Product not found."));
			}
			console.log("product", product)
		},
		/**
		 * ****************************************
		 * _scanWithQrcode method
		 * It will be called when Product Scan Options is QR code.
		 * ****************************************
	   	*/
		_scanWithQrcode: function (barcode, wo_id) {
			var self = this;
			// Find and Save data into LS
			var products = JSON.parse(localStorage.getItem('products_list'));
			var components = JSON.parse(localStorage.getItem('equip_component_list'));
			var lots = JSON.parse(localStorage.getItem('lot_products'));

			var product = products.find(x => x.sh_qr_code === barcode);
			if (product) {
				var comp = components.find(x => x.product_id === product.id);
				if (comp) {
					if(product.tracking != 'serial'){
						var comp_list_new = components.map(function (item) {
							if (item.product_id === product.id) {
								item.product_uom_qty = item.product_uom_qty + 1;
								item.sync = false;
								item.is_scan = true;
								item.new_qty = item.new_qty + 1;
							}
							return item;
						});
						localStorage.setItem('equip_component_list', JSON.stringify(comp_list_new));
						self._loadComponentTableLS();
						self._show_notification('success', _t("Product added successfully."));
					}
				} else {
					if(self.consumption_type == 'strict'){
						self._show_notification('warning', _t("You scanned different product than expected for the following Bill of Material."));
					}else{
						var lot = lots.filter(x => x.product_id === product.id);
						var lot  = lot[0];
						var n_compo = JSON.parse(localStorage.getItem('equip_component_list'))
						if (lot) {
							var lot_ids = []
							lot_ids.push({
								'id': lot.id,
							})
							n_compo.push({
								'move_id': false,
								'wo_id': self.workorder_id,
								'product_id': product.id,
								'product_name': product.name,
								'product_uom_qty': 1,
								'new_qty': 1,
								'lot_name': lot.name,
								'lot_id': lot.id,
								'lot_ids':lot_ids,
								'sync': false,
								'is_scan': true,
							});
						}else{
							n_compo.push({
								'move_id': false,
								'wo_id': self.workorder_id,
								'product_id': product.id,
								'product_name': product.name,
								'product_uom_qty': 1,
								'new_qty': 1,
								'lot_name': "",
								'lot_id': "",
								'lot_ids': "",
								'sync': false,
								'is_scan': true,
							});
						}
						localStorage.setItem('equip_component_list', JSON.stringify(n_compo));
						self._loadComponentTableLS();
						self._show_notification('success', _t("Product added successfully."));
					}
				}
			}
			else {
				console.log('No product found')
				self._show_notification('warning', _t("Product not found."));
			}
			console.log("product", product)
		},

		_loadCompotantTable: function () {
			var self = this;
			var def = self._rpc({
				model: 'stock.move',
				method: 'search_read',
				args: [[['mrp_workorder_component_id', '=', self.workorder_id]], ['product_id', 'product_uom_qty', 'lot_ids', 'lot_name']],
			}).then(function (result) {
				var table = $('.manu_kisok_js_components_table');
				table.empty();
				var tbody = $('<tbody>');
				table.append(tbody);
				var tr = $('<tr>');
				tbody.append(tr);
				tr.append($('<th>').text('Product'));
				tr.append($('<th>').text('Lot/Serial Numbers'));
				tr.append($('<th>').text('Qty'));
				_.each(result, function (row) {
					console.log(result)
					var tr = $('<tr>');
					tbody.append(tr);
					tr.append($('<td>').text(row['product_id'][1]));
					if (row['lot_name']) {
						tr.append($('<td>').append($('<input>')
							.attr('value', row['lot_name'])
						));
					} else {
						tr.append($('<td>').append($('<input>')));
					}
					// tr.append($('<td>').text(row['product_uom_qty']));
					tr.append($('<td>').append($('<input>')
						.attr('value', row['product_uom_qty'])
					));
				});
			});
		},
		_loadComponentTableLS: function () {
			var self = this;
			console.log("Load Compotant Table");
			var comp_list = localStorage.getItem("equip_component_list");
			var comp_list_json = JSON.parse(comp_list);
			console.log(comp_list_json)

			var table = $('.manu_kisok_js_components_table');
			table.empty();
			var tbody = $('<tbody>');
			table.append(tbody);
			var tr = $('<tr>');
			tbody.append(tr);
			tr.append($('<th>').text('Product'));
			tr.append($('<th>').text('Lot/Serial Numbers'));
			tr.append($('<th>').text('Qty'));

			for (var i = 0; i < comp_list_json.length; i++) {
				var tr = $('<tr>');
				tbody.append(tr);
				tr.append($('<td>').text(comp_list_json[i].product_name));
				if (comp_list_json[i].lot_name) {
					tr.append($('<td>').append($('<input>')
						.attr('value', comp_list_json[i].lot_name).attr('disabled', 'disabled')
					));
				} else {
					tr.append($('<td>').append($('<input>').attr('disabled', 'disabled')));
				}
				// tr.append($('<td>').text(comp_list_json[i].lot_name));
				if(comp_list_json[i].is_scan){
					if(self.is_qty_editable){
						tr.append($('<td>').append($('<input>').attr('value', comp_list_json[i].product_uom_qty)));
					}
					else{
						tr.append($('<td>').append($('<input>').attr('value', comp_list_json[i].product_uom_qty).attr('disabled', 'disabled')));
					}
					
				}
				else{
					if(self.is_qty_editable){
						tr.append($('<td>').append($('<input>').attr('value', '0')));
					}
					else{
						tr.append($('<td>').append($('<input>').attr('value', '0').attr('disabled', 'disabled')));
					}
				}
			}
			console.log("compo table", table)
			$('input[name="manuf_kiosk_barcode_mobile_manual"]').val("")
		},
		_SyncData: function () {
			var self = this;
			$('.button_sync').text('Syncing Data');
			var comp_list = localStorage.getItem("equip_component_list");
			var comp_list_json = JSON.parse(comp_list);
			console.log(comp_list_json)

			var wo_info = JSON.parse(localStorage.getItem('wo_info'));
			console.log(wo_info[0].id);
			console.log(wo_info[0].produced_finished_goods);
			console.log(wo_info[0].produced_rejected_goods);

			// var compos = comp_list_json.filter(x => x.sync === false);
			var compos = comp_list_json;
			console.log('compos', compos)
			if (compos.length > 0) {
				var def = self._rpc({
					model: 'mrp.workorder',
					method: 'kiosk_online_sync',
					args: [self.workorder_id, compos, wo_info[0].produced_finished_goods, wo_info[0].produced_rejected_goods, wo_info[0].done_method_sync],
				}).then(function (result) {
					console.log("result", result)
					self._loadComponentTableLS();
					$('.button_sync').text('Sync Data');
					// Update local storage status
					for (var i = 0; i < comp_list_json.length; i++) {
						comp_list_json[i].sync = true;
						comp_list_json[i].new_qty = 0;
					}
					localStorage.setItem("equip_component_list", JSON.stringify(comp_list_json));
					if(result){
						var mrp = self._rpc({
							model: 'mrp.workorder',
							method: 'kiosk_online_sync_mrp',
							args: [self.workorder_id, wo_info[0].done_method_sync],
						}).then(function (result) {
							console.log("result", result)
						});
					}
				});
			}
		},
		init: function (parent, action) {
			this._super.apply(this, arguments);
			var dt_planned = action.recordData.date_planned_start
			var dt_finished = action.recordData.date_planned_finished
			this.recordData = action.recordData;
			this.workcenter_id = action.workcenter_id;
			this.workorder_id = action.workorder_id;
			this.workorder_name = action.workorder_name;
			this.production_id = action.production_id;
			this.product_id = action.product_id;
			this.product_uom = action.recordData.product_uom_id;
			this.qty_production = action.recordData.qty_production;
			this.production_bom_id = action.recordData.production_bom_id;
			this.duration_expected = action.duration_expected;
			this.duration = action.duration;
			this.date_planned_start = dt_planned ? dt_planned.format('MM/DD/YYYY') : dt_planned;
			this.date_planned_finished = dt_finished ? dt_finished.format('MM/DD/YYYY') : dt_finished;
			this.working_state = action.recordData.working_state;
			this.state = action.recordData.state;
			this.is_user_working = action.recordData.is_user_working;
			this.date_start = action.date_start;
			this.date_end = action.date_end;
			this.components_ids = action.components_ids;
			this.workcenter_id = action.workcenter_id;
			this.production_id = action.production_id;
			this.manuf_kiosk_barcode_mobile = action.manuf_kiosk_barcode_mobile;
			this.manuf_kiosk_bm_is_cont_scan = action.manuf_kiosk_bm_is_cont_scan;
			this.manuf_kiosk_barcode_mobile_type = action.manuf_kiosk_barcode_mobile_type;
			this.manuf_kiosk_bm_is_notify_on_success = action.manuf_kiosk_bm_is_notify_on_success;
			this.manuf_kiosk_bm_is_notify_on_fail = action.manuf_kiosk_bm_is_notify_on_fail;
			this.manuf_kiosk_bm_is_sound_on_success = action.manuf_kiosk_bm_is_sound_on_success;
			this.manuf_kiosk_bm_is_sound_on_fail = action.manuf_kiosk_bm_is_sound_on_fail;
			this.consumption_type = action.consumption_type;
			this.workorder_dis_name = action.workorder_dis_name;
			this.qty_produced = action.qty_produced;
			this.produced_finished_product = action.produced_finished_product;
			this.produced_rejected_product = action.produced_rejected_product;
			this.produced_finished_product_uom_id = action.produced_finished_product_uom_id;
			this.produced_rejected_product_uom_id = action.produced_rejected_product_uom_id;
			this.digits_value = action.digits_value;
			this.is_show_barcode_scanner = action.is_show_barcode_scanner;
			this.is_qty_editable = action.is_qty_editable;
			this.manuf_kiosk_att_is_cont_scan = action.manuf_kiosk_att_is_cont_scan;
			this.manuf_kiosk_att_is_notify_on_success = action.manuf_kiosk_att_is_notify_on_success;
			this.manuf_kiosk_att_is_notify_on_fail = action.manuf_kiosk_att_is_notify_on_fail;
			this.manuf_kiosk_att_is_sound_on_success = action.manuf_kiosk_att_is_sound_on_success;
			this.manuf_kiosk_att_is_sound_on_fail = action.manuf_kiosk_att_is_sound_on_fail;
			this.employee_id = action.employee_id;
		},

		/**
		 * ****************************************
		 * ********** KIOSK Mode Attendance **********
		 * ****************************************
		 */

		/**
		 * ****************************************
		 * Reset Camera Button
		 * ****************************************
		 */
		_onClickCameraResetBtnAtt: function (ev) {
			var self = this;
			//RESET READER
			codeReader.reset();

			//HIDE VIDEO
			$(".js_cls_manuf_kiosk_att_vid_div").hide();

			//HIDE STOP BUTTON
			$(".js_cls_manuf_kiosk_att_reset_btn").hide();

			// remove the result from the view
			document.getElementById("js_id_manuf_kiosk_att_result").textContent = '';

		},


		/**
		 * ****************************************
		 * Start Camera Button
		 * ****************************************
		 */

		_onClickCameraStartBtnAtt: function (ev) {
			var self = this;
			self.shUpdateCameraControl();
			//SHOW VIDEO
			$(".js_cls_manuf_kiosk_att_vid_div").show();

			//SHOW STOP BUTTON
			$(".js_cls_manuf_kiosk_att_reset_btn").show();
			// remove the result from the view
			document.getElementById("js_id_manuf_kiosk_att_result").textContent = '';


			if (self.manuf_kiosk_att_is_cont_scan) {
				self.decodeContinuousAtt(codeReader, selectedDeviceId);
			} else {
				self.decodeOnceAtt(codeReader, selectedDeviceId);
			}

		},
		_onClickOpenScanModal: function (ev) {
			var self = this;
			$(".labor_man_enter_modal").show();
		},
		_onClickCloseScanModal: function (ev) {
			var self = this;
			$(".labor_man_enter_modal").hide();
		},

		/**
		 * ****************************************
		 * Decode Scanned Barcode Method
		 * ****************************************
		 */
		decodeContinuousAtt: function (codeReader, selectedDeviceId) {
			var selected_cam = localStorage.getItem('manuf_kiosk_barcode_mobile_selected_device_id') || selectedDeviceId;
			var self = this;
			codeReader.decodeFromInputVideoDeviceContinuously(selectedDeviceId, "js_id_manuf_kiosk_att_video", (result, err) => {
				if (result) {
					$('input[name="manuf_kiosk_barcode_mobile"]').val(result.text);
					document.getElementById("js_id_manuf_kiosk_att_result").textContent = result.text;
					self._onBarcodeScannedAtt(result.text, self.workorder_id)
					// self._onBarcodeScannedL(result.text, self.workorder_id)
				}
				if (err) {
					// console.error(err);
				}
			});
		},
		/**
		 * ****************************************
		 * Decode Scanned Barcode Method
		 * ****************************************
		 */
		decodeOnceAtt: function (codeReader, selectedDeviceId) {
			var selected_cam = localStorage.getItem('manuf_kiosk_barcode_mobile_selected_device_id') || selectedDeviceId;
			var self = this;
			codeReader
				.decodeFromInputVideoDevice(selected_cam, "js_id_manuf_kiosk_att_video")
				.then((result) => {
					$('input[name="manuf_kiosk_barcode_mobile"]').val(result.text);
					document.getElementById("js_id_manuf_kiosk_att_result").textContent = result.text;
					self._onBarcodeScannedAtt(result.text, self.workorder_id)
					// self._onBarcodeScannedL(result.text, self.workorder_id)
				})
				.catch((err) => {
					// console.error(err);
				});
		},
		/**
		 * ****************************************
		 * _onBarcodeScannedL method
		 * It will be called when barcode is scanned and save data int DB and reload the component.
		 * ****************************************
		*/
		_onBarcodeScannedAtt: function (barcode, wo_id) {
			var self = this;
			this._rpc({
				model: 'mrp.workorder',
				method: 'kiosk_employee_scan',
				args: [barcode, wo_id,],
			}).then(function (result) {
					console.log('kiosk_employee_scan', result);
					if (result.action) {
						//RESET READER
						codeReader.reset();
						document.getElementById("js_id_manuf_kiosk_att_result").textContent = result.action['name'];
						document.getElementById("labor_name").textContent = result.action['sequence_code'] + " - " +result.action['name'];
						$(".component_scan").show();
						$(".employee_scan").hide();
						// play success sound
						self._show_notification('success', _t("Employee scan successfully."));
						var src = "/equip3_manuf_kiosk/static/src/sounds/picked.wav";
						$('body').append('<audio src="' + src + '" autoplay="true"></audio>');
					} else if (result.warning) {
						//play failed sound
						self._show_notification('warning', _t("Employee not found."));
						var src = "/equip3_manuf_kiosk/static/src/sounds/error.wav";
						$('body').append('<audio src="' + src + '" autoplay="true"></audio>');
					}
					$('input[name="manuf_kiosk_barcode_mobile_manual"]').val("")
				}, function () {
					// core.bus.on('barcode_scanned', self, self._onBarcodeScanned);
				});
			
		},

		/**
		 * ****************************************
		 * Add emp on enter press
		 * ****************************************
		 */

		_onClickAddEmpPress: function (ev) {
			var self = this;
			var barcode = $('input[name="manuf_kiosk_emp_manual"]').val();
			if (ev.keyCode === 13) {
				if (barcode != "") {
					self._onBarcodeScannedAtt(barcode, self.workorder_id)
				} else {
					self._show_notification('warning', 'Please enter a barcode');
				}
			}
		},

		/**
		 * ****************************************
		 * Add emp
		 * ****************************************
		 */

		_onClickAddEmpBtn: function (ev) {
			var self = this;
			var barcode = $('input[name="manuf_kiosk_emp_manual"]').val();
			if (barcode != "") {
				self._onBarcodeScannedAtt(barcode, self.workorder_id)
			} else {
				self._show_notification('warning', 'Please enter a barcode');
			}
		},
		
		start: function () {
			var self = this;
			// self._loadCompotantTable();
			console.log("!!!!!!!!!!!!", this)
			if (self.duration) {
				var d = self.duration.split(':')
				var default_duration_time = '00:' + self.formatTimer(d[0]) + ':' + self.formatTimer(d[1])
				var real_hour = '00';
				var real_minute = '00';
				var real_seconds = '00';

				if (default_duration_time) {
					console.log('****************##########************', d[1], self.formatTimer(d[1]), default_duration_time)
					real_hour = self.formatTimer(default_duration_time.split(':')[0])
					real_minute = self.formatTimer(parseInt(default_duration_time.split(':')[1]))
					real_seconds = self.formatTimer(default_duration_time.split(':')[2])
					self.real_hour = real_hour;
					self.real_minute = real_minute;
					self.real_seconds = real_seconds;
					console.log('****************##########************', default_duration_time, real_hour, real_minute, real_seconds)
					// document.getElementById("hour").innerHTML = real_hour;
					// document.getElementById("minute").innerHTML = real_minute;
					// document.getElementById("seconds").innerHTML = real_seconds;
				}
			}
			self.$el.html(QWeb.render("MRPManuKiosk", {
				widget: self
			}));
			var bt_st = $(self.$el[0]).find('.button_start')[0];
			var bt_pause = $(self.$el[0]).find('.button_pause')[0];
			var bt_done = $(self.$el[0]).find('.button_done')[0];
			var bt_block = $(self.$el[0]).find('.button_block')[0];
			var bt_unblock = $(self.$el[0]).find('.button_unblock')[0];
			var production_btn = $(self.$el[0]).find('.production_name')[0];
			$(production_btn).click(function () {
				$(production_btn).find('a').attr('href', window.location.pathname + window.location.hash)
			})
			if (this.recordData.is_user_working != false && this.recordData.state == 'progress') {
				$(bt_st).hide();
				$(bt_unblock).hide();
			}
			if (this.recordData.is_user_working == false && this.recordData.state == 'progress') {
				$(bt_pause).hide();
				$(bt_done).hide();
				$(bt_unblock).hide();
			}
			if (this.recordData.is_user_working == false && this.recordData.state == 'ready') {
				$(bt_pause).hide();
				$(bt_done).hide();
				$(bt_unblock).hide();
			}
			if (this.recordData.is_user_working == false && this.recordData.state == 'pending') {
				$(bt_st).show();
				$(bt_pause).hide();
				$(bt_done).hide();
				$(bt_block).show();
				$(bt_unblock).hide();
			}
			console.log(this.recordData.is_user_working, this.recordData.state)
			if (this.recordData.working_state == 'blocked') {
				$(bt_st).hide();
				$(bt_pause).hide();
				$(bt_done).hide();
				$(bt_block).hide();
				$(bt_unblock).show();
			}

			var pro_sel = '';
			var data = '';
			self._rpc({
				model: 'product.product',
				method: 'search_read',
				kwargs: {
					domain: [],
					fields: ['id', 'name', 'default_code', 'barcode'],
				},
			}).then(function (prod) {
				var pro_sel = $("<select id=\"right_pro_sele\" name=\"right_pro_sele\" />");

				for (var p in prod) {
					$("<option />", { value: prod[p].id, text: prod[p].display_name }).appendTo(pro_sel);
				}

				// Append table with add row form on add new button click
				console.log("***********************8", $(self.$el[0]), $(self.$el[0]).find('#scan_pro_tbl input[name="pro_sn"]'))
				$(self.$el[0]).find('#scan_pro_tbl input[name="pro_sn"]').on("keypress", function (e) {
					console.log("::::::::::::::::::::::::::::::::::::::::::::: Keypresss")
					if (e.keyCode == 13) {
						var dt = new Date();
						var curr_time = dt.getHours() + ":" + dt.getMinutes();
						var index = $("#wo_component tbody tr:last-child").index();
						pro_sel.appendTo('#pro_sel')
						var selected_val = $(this).val()
						console.log("::::::::::::::::::::::::::::::::::::::::::::: ENTER Key", prod)

						// Load data from LocalStorage 
						var lot_pro_data = JSON.parse(localStorage['lot_products'])
						var all_pro_data = JSON.parse(localStorage['products_list'])

						var product_found = false

						// Product added using lot/serial number
						for (var i = 0; i < lot_pro_data.length; i++) {

							if (lot_pro_data[i]['name'] && lot_pro_data[i]['name'] == selected_val) {

								var spcl_row = '<tr>' +
									'<td><span id="time">' + lot_pro_data[i]['product_id'][1] + '</span></td>' +
									'<td style="word-wrap: break-word">' + selected_val + '</td>' +
									'<td>' + lot_pro_data[i]['product_qty'] + '</td></tr>';

								// self.validate_sn(selected_val)
								if (!self.duplicate_row) {
									$("#wo_component").append(spcl_row);
									$('[data-toggle="tooltip"]').tooltip();
									// $("#wo_component tbody tr").find('#right_pro_sele option[value='+lot_pro_data[i]['product_id'][0]+']').last().attr('selected','selected');
								}

								$('input[name="pro_sn"]').val("")

								product_found = true
							}
						}

						// Product added using default_code and barcode field
						for (var i = 0; i < all_pro_data.length; i++) {

							var row = '<tr>' +
								'<td><span id="time">' + prod[i].name + '</span></td>' +
								'<td style="word-wrap: break-word">' + selected_val + '</td>' +
								'<td><input type="text" class="form-control" name="qty" id="qty"></td></tr>';

							if (all_pro_data[i]['default_code'] && all_pro_data[i]['default_code'] == selected_val) {

								// self.validate_sn(selected_val)
								if (!self.duplicate_row) {
									$("#wo_component").append(row);
									$('[data-toggle="tooltip"]').tooltip();
									// $("#wo_component tbody tr").find('#right_pro_sele option[value='+all_pro_data[i]['id']+']').last().attr('selected','selected');
								}

								$('input[name="pro_sn"]').val("")

								product_found = true

							} else if (all_pro_data[i]['barcode'] && all_pro_data[i]['barcode'] == selected_val) {

								// self.validate_sn(selected_val)
								if (!self.duplicate_row) {
									$("#wo_component").append(row);
									$('[data-toggle="tooltip"]').tooltip();
									// $("#wo_component tbody tr").find('#right_pro_sele option[value='+all_pro_data[i]['id']+']').last().attr('selected','selected');
								}

								$('input[name="pro_sn"]').val("")

								product_found = true

							}
						}

						if (!product_found) {
							alert('No Product Found')
							return false
						}
						// })

					}
				})
			})

			// window.setTimeout(function(){
			// 	self.shUpdateCameraControl();
			// }, 1000);

			// self.shUpdateCameraControl();


			return self._super.apply(this, arguments);
		},
		destroy: function () {
			this._super.apply(this, arguments);
		},
	});
	core.action_registry.add('manuf_kiosk_mode', ManufKiosk);
	return ManufKiosk;
});