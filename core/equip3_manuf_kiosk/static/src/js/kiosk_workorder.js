odoo.define('equip3_manuf_kiosk.KioskWorkorder', function (require) {
    'use strict';

    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var fieldUtils = require('web.field_utils');
    var session = require('web.session');
    var Dialog = require('web.Dialog');

    var _t = core._t;
    var QWeb = core.qweb;

    var kioskWorkorder = AbstractAction.extend({
        contentTemplate: 'MrpKioskWorkorder',

        events: {
            'click .o_button_add_qty': '_onClickButtonAddQty',
            'click .o_button_close': '_onClickButtonClose',
            'click .o_button_sync': '_onClickButtonSync',
            'click .o_button_workorder': '_onClickButtonWorkorder',
            'click .o_button_add_material': '_onClickButtonAddMaterial',
            'click .o_button_scan': '_onClickButtonScan',
            'click .o_button_stop_scan': '_onClickButtonStopScan',
            'change .o_input_quantityDone': '_onChangeQuantityDone',
            'change .o_device': '_onChangeDevice'
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.resId = action.res_id;
            this.previousContext = action.previousContext;
            this.employee = action.employee;
            
            this.audio = {
                success: new Audio('/equip3_manuf_kiosk/static/src/sounds/picked.wav'),
                error: new Audio('/equip3_manuf_kiosk/static/src/sounds/error.wav')
            }

            this.codeReader = new ZXing.BrowserMultiFormatReader();
            this.activeScan = false;
            this.deviceIds = [];
            this.deviceId = {};

            this.finishedQty = 1.0;
            this.rejectedqty = 0.0;
            this.isDirty = false;

            this.fields = {
                'mrp.workorder': [
                    'id', 'name', 'workorder_id', 'operation_id', 'date_start', 'date_finished', 'workcenter_id',
                    'date_planned_start', 'date_planned_finished', 'duration', 'duration_expected',
                    'move_raw_ids', 'product_id', 'production_state', 'is_user_working', 'working_state', 'state',
                    'operation_id'
                ],
                'stock.move': [
                    'product_id', 'lot_ids', 'product_uom_qty', 'product_uom', 'quantity_done'
                ],
                'mrp.routing.workcenter': [
                    'worksheet_type', 'worksheet', 'worksheet_google_slide', 'note'
                ]
            };
        },

        willStart: function(){
            var self = this;
            var _super = this._super.bind(this);
            var args = arguments;

            var settingsProm = this._rpc({
                model: 'res.company',
                method: 'search_read',
                fields: [
                    'id', 'name', 'manuf_kiosk_att_is_cont_scan', 'manuf_kiosk_barcode_mobile_type',
                    'manuf_kiosk_bm_is_notify_on_success', 'manuf_kiosk_bm_is_sound_on_success',
                    'manuf_kiosk_bm_is_notify_on_fail', 'manuf_kiosk_bm_is_sound_on_fail'
                ],
                domain: [['id', '=', session.company_id]]
            }).then(function(companies){
                self.company = companies[0];
            });
            var stateProm = this._updateState();
            return Promise.all([settingsProm, stateProm]).then(function(){
                return _super.apply(self, args);
            });
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self._notify('success', 'Welcome ' + self.employee.name + ' !');
                self._renderButtons();
                self._renderInfo();
                self._renderMaterials();
                self._startTimeCounter();
                self._renderWorksheet();
                self.$el.find('#instructionCarousel').carousel();

                window.addEventListener('offline', function(e) {
                    self.$el.find('.o_button_wifi').css('color', 'red');
                  }, false);
                window.addEventListener('online', function(e) {
                    self.$el.find('.o_button_wifi').css('color', 'green');
                }, false);
                
                // setInterval(function(){
                //     if(navigator.onLine){
                //         self._updateAndRenderState();	
                //     }
                // }, 5000);
            });
        },

        formatFloat(tuple){
            return fieldUtils.format.float(tuple[0], false, {digits: [false, tuple[1]]});
        },

        formatFloatTime: function(tuple){
            return fieldUtils.format.float_time_hms(tuple[0]);
        },

        formatDatetime(dtString){
            if (!dtString){
                return '-';
            }
            return fieldUtils.format.datetime(moment(dtString), false, {timezone: true});
        },

        _startTimeCounter: function(){
            var self = this;
            clearTimeout(this.timer);
            if (this.recordData.is_user_working) {
                this.timer = setTimeout(function () {
                    self.recordData.duration[0] += 1/60;
                    self._startTimeCounter();
                }, 1000);
            } else {
                clearTimeout(this.timer);
            }
            this.$el.find('.o_time_counter').text(this.formatFloatTime(this.recordData.duration));
            this.$el.find('.o_duration').text(this.formatFloatTime(this.recordData.duration));
        },

        _updateState: function(){
            var self = this;
            return this._rpc({
                model: 'mrp.workorder',
                method: 'kiosk_get_record_data',
                args: [this.resId],
                kwargs: {allfields: this.fields}
            }).then(function(result){
                self.recordData = result;
                self.isDirty = false;
                return result;
            });
        },

        _renderButtons: function(){
            var $buttons = QWeb.render('MrpKioskWorkorderButtons', {o: this.recordData});
            this.$el.find('.o_workorder_buttons').html($buttons);

            let disabledState = this.recordData.state !== 'progress' ? 'disabled': null;
            this.$el.find('.o_input_material').prop('disabled', disabledState);
            this.$el.find('.o_button_add_material').prop('disabled', disabledState);
            this.$el.find('.o_button_scan').prop('disabled', disabledState);
            this.$el.find('.o_button_add_qty').prop('disabled', disabledState);
            this.$el.find('.o_button_sync').prop('disabled', this.isDirty ? null : 'disabled');
            this.$el.find('.o_input_finishedQty').prop('disabled', disabledState);
            this.$el.find('.o_input_rejectedQty').prop('disabled', disabledState);
        },

        _renderInfo: function(){
            var $info = QWeb.render('MrpKioskWorkorderInfo', {
                o: this.recordData,
                formatFloatTime: this.formatFloatTime,
                formatDatetime: this.formatDatetime,
                employee: this.employee
            });
            this.$el.find('.o_workorder_info').html($info);
        },

        _renderMaterials: function(){
            var $tbody = this.$el.find('table.o_table_material > tbody');
            $tbody.html('');
            var self = this;
            _.each(this.recordData.move_raw_ids, function(move){
                var $tr = QWeb.render('MrpKioskMaterial', {'move': move, 'widget': self});
                $tbody.append($tr);
            });
        },

        _renderPdf: function(){
            var self = this;
            var $container = $('<div class="o_field_pdfviewer w-100 h-100"/>');
            var $iFrame = $('<iframe class="o_pdfview_iframe o_field_pdfviewer w-100 h-100"/>');

            $iFrame.on('load', function () {
                self.PDFViewerApplication = this.contentWindow.window.PDFViewerApplication;
            });
            var queryObj = {
                model: 'mrp.routing.workcenter',
                field: 'worksheet',
                id: this.recordData.operation_id.id,
            };
            var queryString = $.param(queryObj);
            fileURI = '/web/content?' + queryString;
            var fileURI = encodeURIComponent(fileURI);
            var viewerURL = '/web/static/lib/pdfjs/web/viewer.html?file=';
            var URI = viewerURL + fileURI + '#page=' + 1;
            $iFrame.attr('src', URI);
            $container.append($iFrame);
            return $container;
        },
        
        _renderGoogleSlide: function(){
            var self = this;
            var $container = $('<div class="o_embed_url_viewer o_field_widget w-100 h-100"/>');
            var $iFrame = $('<iframe class="o_embed_iframe w-100 h-100" allowfullscreen="true"/>');
            var src = false;
            if (this.recordData.operation_id.worksheet_google_slide){
                var googleRegExp = /(^https:\/\/docs.google.com).*(\/d\/e\/|\/d\/)([A-Za-z0-9-_]+)/;
                var google = this.recordData.operation_id.worksheet_google_slide.match(googleRegExp);
                if (google && google[3]) {
                    src = 'https://docs.google.com/presentation' + google[2] + google[3] + '/preview?slide=' + this.page;
                }
            }
            src = src || this.recordData.operation_id.worksheet_google_slide
            $iFrame.attr('src', src);
            $container.append($iFrame);
            return $container;
        },

        _renderNote: function(){
            var $note = $('<div></div');
            var note = this.recordData.operation_id.note || _t('No instruction found!');
            $note.text(note);
            return $note;
        },

        _renderWorksheet: function(){
            let $content;
            if (this.recordData.operation_id.worksheet_type == 'text'){
                $content = this._renderNote()
            } else if (this.recordData.operation_id.worksheet_type == 'google_slide'){
                $content = this._renderGoogleSlide()
            } else {
                $content = this._renderPdf()
            }
            this.$el.find('.o_instruction').append($content);
        },

        _decode: function () {
            var self = this;
            if (this.company.manuf_kiosk_att_is_cont_scan){
                this.codeReader.decodeFromInputVideoDeviceContinuously(this.deviceId.id, 'kiosk_device_video', (result, err) => {
                    if (result){
                        var barcode = result.text;
                        self.$el.find(".o_device_result").text(barcode);
                        self._processBarcode(barcode);
                    }
                });
            } else {
                this.codeReader.decodeFromInputVideoDevice(this.deviceId.id, 'kiosk_device_video', (result, err) => {
                    if (result){
                        var barcode = result.text;
                        self.$el.find(".o_device_result").text(barcode);
                        self._processBarcode(barcode);
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

                self._decode();
            });
        },

        _findProduct: function(value){
            var domain;
            switch (this.company.manuf_kiosk_barcode_mobile_type){
                case 'int_ref':
                    domain = [['default_code', '=', value]];
                    break;
                case 'barcode':
                    domain = [['barcode', '=', value]];
                    break
                case 'qr_code':
                    domain = [['sh_qr_code', '=', value]];
                    break;
                case 'all':
                    domain = [
                        '|', '|', 
                        ['default_code', '=', value], 
                        ['barcode', '=', value], 
                        ['sh_qr_code', '=', value]
                    ];
                    break;
            }

            if (!domain){
                return false;
            }

            return this._rpc({
                model: 'product.product',
                method: 'search_read',
                domain: domain,
                fields: ['id', 'uom_id', 'display_name']
            }).then(function(products){
                if (products){
                    return products[0];
                }
                return false;
            })
        },

        _assignMaterial: function(material){
            var moves = _.filter(this.recordData.move_raw_ids, function(move){
                return move.product_id.id === material.id && !['done', 'cancel'].includes(move.state);
            });
            if (moves.length){
                _.each(moves, function(move){
                    move.quantity_done[0] ++;
                });
            } else {
                this.recordData.move_raw_ids.push({
                    id: 'New',
                    name: 'New',
                    product_id: [material.id, material.display_name],
                    lot_ids: [],
                    product_uom_qty: [material.product_uom_qty, 2],
                    quantity_done: [1.0, 2],
                    product_uom: material.uom_id
                });
            }
            this.isDirty = true;
            this._renderButtons();
            this._renderMaterials();
            this._notify('success', 'Material added successfully!');
        },

        _processBarcode: async function(value){
            var material = await this._findProduct(value);
            if (material){
                this._assignMaterial(material);
                
            } else {
                this._notify('warning', 'Material Not Found!');
            }
        },

        _toggleInstructionScan: function(){
            var label = 'MATERIALS';
            if (this.activeScan){
                label = 'SCANNER';
            }
            this.$el.find('.o_label_container').text(label);
            this.$el.find('.o_device_container').toggleClass('d-none');
            this.$el.find('.o_materials').toggleClass('d-none');
            this.$el.find('.o_button_stop_scan').toggleClass('d-none');
            this.$el.find('.o_button_scan').toggleClass('d-none');
            this.$el.find('.o_device_result').text('');
        },

        _updateAndRenderState: function(){
            if (this.isDirty){
                return;
            }
            var self = this;
            this._updateState().then(function(){
                self._renderButtons();
                self._renderInfo();
                self._renderMaterials();
            });
        },

        _onChangeQuantityDone: function(ev){
            let target = $(ev.currentTarget)
            let materialId = parseInt(target.closest('tr').data('id'));
            var moves = _.filter(this.recordData.move_raw_ids, function(move){
                return move.id === materialId;
            });
            if (moves.length){
                _.each(moves, function(move){
                    move.quantity_done[0] = target.val();
                });
            }
            this.isDirty = true;
            this._renderButtons();
        },

        _onClickButtonWorkorder: function(ev){
            ev.stopPropagation();
            var self = this;
            var $target = $(ev.target);
            var actionName = $target.data('name');
            var actionType = $target.data('type');
            var context = $target.data('context');

            if (!context){
                context = {};
            }

            context['from_kiosk'] = true;
            context['consumption_confirmed'] = true;

            function doIt() {
                if (actionType === 'action'){
                    return self.do_action(actionName, {additional_context: context});
                } else if (actionType === 'object'){
                    return self._rpc({
                        model: 'mrp.workorder',
                        method: actionName,
                        args: [[self.resId]],
                        context: context
                    }).then(function(result){
                        self._updateState().then(function(){
                            self._renderButtons();
                            self._renderInfo();
                            self._renderMaterials();
                            self._startTimeCounter();
                        });
                    });
                }
            }
            if (this.isDirty){
                Dialog.confirm(this, _t("There's component(s) that must be synchronize first, discard and continue action?"), {
                    confirm_callback: doIt,
                });
            } else {
                doIt();
            }
        },

        _onClickButtonAddMaterial: function(ev){
            ev.stopPropagation();
            var $input = this.$el.find('.o_input_material');
            var barcode = $input.val();
            if (!barcode){
                this._notify('warning', 'Please type barcode/lot/serial number!')
                return;
            }
            this._processBarcode(barcode);
            $input.val('');
        },

        _onClickButtonClose: function(ev){
            ev.stopPropagation();
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

        _onClickButtonAddQty: function(ev){
            var $target = $(ev.target);
            var fieldName = $target.data('name');
            var $input = this.$el.find('.o_input_' + fieldName);
            this[fieldName] = parseFloat($input.val() ? $input.val() : 0.0) + 1;
            $input.val(this.formatFloat([this[fieldName], 2]));
        },

        _onClickButtonScan: function(ev){
            ev.stopPropagation();
            if (this.activeScan){
                return;
            }
            this._setupDevice();
            this.activeScan = true;
            this._toggleInstructionScan();
        },

        _onClickButtonStopScan: function(ev){
            ev.stopPropagation();
            if (!this.activeScan){
                return;
            }

            this.codeReader.reset();
            this.deviceIds = [];
            this.deviceId = {};
            this.activeScan = false;
            this._toggleInstructionScan();
        },

        _onClickButtonSync: function(ev){
            ev.stopPropagation();
            var self = this;
            this._rpc({
                model: 'mrp.workorder',
                method: 'kiosk_synchronize',
                args: [[this.resId], this.recordData.move_raw_ids]
            }).then(function(result){
                if (result !== true){
                    self._notify('warning', result);
                    return;
                }
                self._updateState().then(function(){
                    self._renderButtons();
                    self._renderInfo();
                    self._renderMaterials();
                });
                self._notify('success', 'Synchronize successfully!');
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

    core.action_registry.add('mrp_kiosk_workorder', kioskWorkorder);
    return kioskWorkorder;
});