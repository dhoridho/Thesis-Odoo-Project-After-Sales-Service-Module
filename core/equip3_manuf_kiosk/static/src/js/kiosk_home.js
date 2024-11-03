odoo.define('equip3_manuf_kiosk.KioskHome', function (require) {
    'use strict';

    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var session = require('web.session');

    var _t = core._t;

    var kioskHome = AbstractAction.extend({
        contentTemplate: 'MrpKioskHome',

        events: {
            'click .o_btn_scan': '_onClickScan',
            'click .o_btn_stop': '_onClickStop',
            'click .o_btn_enter': '_onClickEnter',
            'click .o_btn_close': '_onClickClose',
            'change .o_device': '_onChangeDevice'
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.codeReader = new ZXing.BrowserMultiFormatReader();
            this.activeScan = false;
            this.deviceIds = [];
            this.deviceId = {};

            this.resId = action.res_id;
            this.previousContext = action.previousContext;

            this.audio = {
                success: new Audio('/equip3_manuf_kiosk/static/src/sounds/picked.wav'),
                error: new Audio('/equip3_manuf_kiosk/static/src/sounds/error.wav')
            }
        },

        willStart: function(){
            var fields = {
                'mrp.workorder': [
                    'id', 'name', 'workorder_id', 'workcenter_id'
                ]
            };

            var self = this;
            var recordProm = this._rpc({
                model: 'mrp.workorder',
                method: 'kiosk_get_record_data',
                args: [this.resId],
                kwargs: {allfields: fields}
            }).then(function(result){
                self.recordData = result;
            });

            var settingsProm = this._rpc({
                model: 'res.company',
                method: 'search_read',
                fields: [
                    'id', 'name', 'manuf_kiosk_att_is_cont_scan', 
                    'manuf_kiosk_bm_is_notify_on_success', 'manuf_kiosk_bm_is_sound_on_success',
                    'manuf_kiosk_bm_is_notify_on_fail', 'manuf_kiosk_bm_is_sound_on_fail'
                ],
                domain: [['id', '=', session.company_id]]
            }).then(function(companies){
                self.company = companies[0];
            });
            return Promise.all([this._super.apply(this, arguments), recordProm, settingsProm]);
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self.$buttons = {
                    scan: self.$el.find('.o_btn_scan'),
                    stop: self.$el.find('.o_btn_stop'),
                    close: self.$el.find('.o_btn_close'),
                    enter: self.$el.find('.o_btn_enter')
                }
            });
        },

        _decode: function () {
            var self = this;
            if (this.company.manuf_kiosk_att_is_cont_scan){
                this.codeReader.decodeFromInputVideoDeviceContinuously(this.deviceId.id, 'kiosk_device_video', (result, err) => {
                    if (result){
                        var barcode = result.text;
                        self.$el.find(".o_device_result").text(barcode);
                        return self._authenticateEmployee(barcode).then(function(){
                            self.codeReader.reset();
                        });
                    }
                });
            } else {
                this.codeReader.decodeFromInputVideoDevice(this.deviceId.id, 'kiosk_device_video', (result, err) => {
                    if (result){
                        var barcode = result.text;
                        self.$el.find(".o_device_result").text(barcode);
                        return self._authenticateEmployee(barcode).then(function(){
                            self.codeReader.reset();
                        });
                    }
                });
            }
		},

        _setupDevice: function(){
            var self = this;
			this.codeReader.getVideoInputDevices().then(function (result) {
                var $deviceSelector = self.$el.find('.o_device');
                $deviceSelector.html('');
                $.each(result, function (index, item) {
                    self.deviceIds.push({
                        id: item.deviceId, 
                        name: item.label
                    });
                    var $option = $('<option value="' + item.deviceId + '">' + item.label + '</option>');
                    if (index === 0){
                        $option.attr('selected', 'selected');
                    }
                    $deviceSelector.append($option);
                });

                if (self.deviceIds.length){
                    self.deviceId = self.deviceIds[0];
                }

                self.$el.find('.o_device_container').show();
                self._decode();
            });
        },

        _authenticateEmployee: function(barcode){
            var self = this;
            return this._rpc({
                model: 'hr.employee',
                method: 'search_read',
                domain: [['sequence_code', '=', barcode]],
                fields: ['id', 'name', 'sequence_code'],
                limit: 1
            }).then(function(employees){
                if (employees.length){
                    return self.do_action({
                        type: 'ir.actions.client',
                        name: 'Machine KIOSK Workorder',
                        tag: 'mrp_kiosk_workorder',
                        res_model: 'mrp.workorder',
                        res_id: self.resId,
                        previousContext: self.previousContext,
                        employee: employees[0]
                    });
                } else {
                    self._notify('warning', 'Employee not found!');
                }
            });
        },

        _onClickScan: function(ev){
            ev.stopPropagation();
            if (this.activeScan){
                return;
            }
            this._setupDevice();
            this.$buttons.scan.hide();
            this.$buttons.stop.show();
            this.activeScan = true;
        },

        _onClickStop: function(ev){
            ev.stopPropagation();
            if (!this.activeScan){
                return;
            }

            this.codeReader.reset();
            this.deviceIds = [];
            this.deviceId = {};

            this.$el.find('.o_device_container').hide();
            this.$buttons.stop.hide();
            this.$buttons.scan.show();
            this.activeScan = false;
        },

        _onClickEnter: function(ev){
            ev.stopPropagation();
            var barcode = this.$el.find('.o_input_labor').val();
            var self = this;
            return this._authenticateEmployee(barcode).then(function(){
                self.codeReader.reset();
            });
        },

        _onClickClose: function(ev){
            var self = this;
			return this._rpc({
				model: 'mrp.workcenter',
				method: 'action_work_order_kiosk',
				args: [[this.recordData.workcenter_id.id]]
			}).then(function (action) {
				if (action) {
                    action.target = 'main';
                    action.context = self.previousContext
					self.do_action(action);
				}
			});
        },

        _onChangeDevice: function(ev){
            var $target = $(ev.target);
            var selectedDeviceId = $target.val(); 
            this.deviceId = _.find(this.deviceIds, function(device){
                device.id = selectedDeviceId;
            })
        },

        _notify: function (type, message) {
			var self = this;
			if(type === 'success'){
				if (self.company.manuf_kiosk_bm_is_notify_on_success){
					self.do_notify(false, _t(message));
				}
				if (self.company.manuf_kiosk_bm_is_sound_on_success) {
                    this.audio.success.play();
				}
			}
			else if(type === 'warning'){
				if(self.company.manuf_kiosk_bm_is_notify_on_fail){
					self.do_warn(false, _t(message));
				}
				if (self.company.manuf_kiosk_bm_is_sound_on_fail) {
					this.audio.error.play();
				}
			}
		}
    });

    core.action_registry.add('mrp_kiosk_home', kioskHome);
    return kioskHome;
});