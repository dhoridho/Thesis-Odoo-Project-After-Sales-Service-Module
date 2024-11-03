odoo.define('app_search_range_date_number.ControlPanel', function (require) {
    "use strict";

    const ControlPanelModelExtension = require('web/static/src/js/control_panel/control_panel_model_extension.js');
    const ControlPanel = require("web.ControlPanel");
    const { device } = require("web.config");
    const { Component } = owl;
    const session = require('web.session');
    //不能用 owl date，因为其要求必须有值
    // const { DatePicker, DateTimePicker } = require('web.DatePickerOwl');
    var datepicker = require('web.datepicker');

    if (device.isMobile) {
        //移动端不处理
        return;
    }

    ControlPanel.patch("app_search_range_date_number.ControlPanel", (T) => {
        //继承处理 ControlPanel
        ControlPanel.defaultProps = Object.assign(ControlPanel.defaultProps, {
            app_fields_date: [],
            app_fields_number: [],
            app_search_range_date_show: session.app_search_range_date_show,
            app_search_range_number_show: session.app_search_range_number_show,
            app_search_range_btn_show: session.app_search_range_date_show || session.app_search_range_number_show,
            app_start_date: '',
            app_end_date: '',
        });
            
        ControlPanel.props = Object.assign(ControlPanel.props, {
            app_fields_date: Array,
            app_fields_number: Array,
            app_search_range_date_show: Boolean,
            app_search_range_number_show: Boolean,
            app_search_range_btn_show: Boolean,
            app_start_date:  { type: String, optional: 1 },
            app_end_date: { type: String, optional: 1 },
        });
            
        class appControlPanel extends T {
            
            constructor() {
                //初始化
                super(...arguments);
                    this.setRange();
                    self.st_date = false
    //                self.st_date = moment(new Date()).format("DD/MM/YYYY HH:mm:ss");
    //                self.st_date = new Date();
                    self.ed_date = false
            }
            _attachAdditionalContent() {
                //渲染
                super._attachAdditionalContent(...arguments);
                //todo 要patch action_mixin 中的 updateControlPanel
                //web.AbstractController, updateControlPanel
                this.setRange();
                if($('.app-search-range-date select').length > 0){
                    if(!$('.app-search-range-date select')[0].options.length > 0){
                        $('.app-search-range-date-container').hide()
                        $('.o_control_panel').css('min-height','inherit')
                    }else{
                        $('.o_control_panel').css('min-height','180px')
                    }
                }
                if($('.app-search-range-number select').length > 0){
                    if(!$('.app-search-range-number select')[0].options.length > 0){
                        $('.app-search-range-number-container').hide()
                        $('.o_control_panel').css('min-height','inherit')
                    }else{
                        $('.o_control_panel').css('min-height','180px')
                    }
                }
            }
            //dom渲染
            setRange() {
                var self = this;
                self.props.app_fields_date = [];
                self.props.app_fields_number = [];
                if (self.props.withSearchBar && self.props.app_search_range_date_show) {
                    _.each(self.props.fields, function (value, key, list) {
                        if (value.store && value.type === "datetime" || value.type === "date") {
                            self.props.app_fields_date.push([key, value.string, value.type]);
                        }
                    });
                };
                //处理number
                if (self.props.withSearchBar && self.props.app_search_range_number_show) {
                    _.each(self.props.fields, function (value, key, list) {
                        if (value.string && value.string.length > 1 && value.store && (value.type === "integer" || value.type === "float" || value.type === "monetary")) {
                            self.props.app_fields_number.push([key, value.string]);
                        }
                    });
                };

                //每次init时，清除render的日期
                // if(self.env.action){
                //     if (self.env.action.xml_id == 'equip3_inventory_reports.action_stock_per_wh' && $('.o_cp_top_right').length){
                //         var cp_top_right = $('.o_cp_top_right')[0]
                //         $(cp_top_right).addClass('d-none')
                //         var cp_bottom = $('.o_cp_bottom')[0]
                //         $(cp_bottom).addClass('d-none')
                //         var control_p = $('.o_control_panel')[0]
                //         $(control_p).addClass('ba_cp_style')
                //         cp_bottom.style.setProperty("min-height", "0px", "important");
                //     }
                // }
                var $search_date = $('.app-search-range-date-container');
                if ($search_date.length) {
                    var $sd = $search_date.find('input');
                    $sd.each(function (index, el) {
                        $sd.eq(index).val('');
                    });
                };

                //渲染日期组件
                if (self.props.app_fields_date.length > 0 && self.props.app_search_range_date_show) {
                    if (self.$app_start_date)
                        self.$app_start_date.destroy();
                    if (self.$app_end_date)
                        self.$app_end_date.destroy();
                        if (self.el && self.el.querySelector(`[name="app_start_date"]`)){
//                            var $app_start_date = new datepicker.DateTimeWidget(this,{defaultDate: '09/14/2022 00:00:00'});
                            var $app_start_date = new datepicker.DateWidget(this,{defaultDate: null});
//                            var $app_start_date = new datepicker.DateTimeWidget(this,{defaultDate: moment(new Date().setHours(0, 0, 0))});
                        //按owl处理找元素
                        $app_start_date.appendTo(self.el.querySelector(`[name="app_start_date"]`)).then(function() {
//                            self.$app_start_date.$input.val(moment(new Date()).format("DD/MM/YYYY HH:mm:ss"));
                                self.$app_end_date.$input.val(self.st_date);
                            if (self.st_date === undefined){
                                if (self.env.action && self.env.action.xml_id == 'base.open_module_tree'){
                                    self.$app_start_date.$input.val('')
                                }
//                                else{
////                                    self.$app_start_date.$input.val(moment(new Date()).format("DD/MM/YYYY HH:mm:ss"));
//                                    self.$app_start_date.$input.val(moment(new Date()).format("MM/DD/YYYY HH:mm:ss"));
//                                }
                            }else{
                                self.$app_start_date.$input.val(self.st_date);
                            }
                            self.$app_start_date.$input.on('blur',function(e){
                                    self.st_date = self.$app_start_date.$input.val();
                                    self.do_search();
                            })
                        })
                        self.$app_start_date = $app_start_date;
                        console.log(self.st_date);
                    }
                    if (self.el && self.el.querySelector(`[name="app_end_date"]`)) {
//                        var $app_end_date = new datepicker.DateTimeWidget(this,{defaultDate: '09/14/2022 23:59:59'});
                        var $app_end_date = new datepicker.DateWidget(this,{defaultDate: null});
//                        var $app_end_date = new datepicker.DateTimeWidget(this,{defaultDate: moment(new Date()), format: 'MM/DD/YYYY 23:59:59'});
                        $app_end_date.appendTo(self.el.querySelector(`[name="app_end_date"]`)).then(function() {
                            self.$app_end_date.$input.val(self.ed_date);
//                            self.$app_end_date.$input.val( moment(new Date()).format("DD/MM/YYYY HH:mm:ss"));
                            if (self.ed_date === undefined){
                                if (self.env.action && self.env.action.xml_id == 'base.open_module_tree'){
                                    self.$app_end_date.$input.val('')
                                }
                            }else{
                                self.$app_end_date.$input.val(self.ed_date);
                            }
                            self.$app_end_date.$input.on('blur',function(){
                                self.ed_date = self.$app_end_date.$input.val();
                                self.do_search()
                            })
                        });
                        self.$app_end_date = $app_end_date;
                        console.log(self.ed_date);
                    }
                }

                // For Floats
                if (self.props.app_fields_date.length > 0 && self.props.app_search_range_number_show) {
                    if (self.el && self.el.querySelector('input.app_start_number'))    {
                        var $app_start_number = $(self.el.querySelector('input.app_start_number'))
                        self.$app_start_number = $app_start_number;
                        self.$app_start_number.on('blur',function(){
                            if(self.$app_start_number.val()){
                                self.do_search()
                            }
                        })
                    }
                    if (self.el && self.el.querySelector('input.app_end_number')) {
                        var $app_end_number = $(self.el.querySelector('input.app_end_number'))
                        self.$app_end_number = $app_end_number;
                        self.$app_end_number.on('blur',function(){
                            if(self.$app_end_number.val()){
                                self.do_search()
                            }
                        })
                    }
                }

            }

            do_search(e) {
                //驱动search, action_model.js
                this.model.dispatch('search');
            }

            do_keypress (e) {
                var self = this;
                var keynum = window.event ? e.keyCode : e.which;
                if (keynum == 13)
                    return self.do_search();
            }
            do_clear () {
                // console.log('do_clear');
                var self = this;
                if ($(document).find('.app-search-range')) {
                    self.$app_start_date.setValue();
                    self.$app_end_date.setValue();
                }
                if ($(document).find('.app-search-range')) {
                    $('.app_start_number').find('input').val('');
                    $('.app_end_number').find('input').val('');
                }
                return self.do_search();
            }
        };

        //增加components
        // appControlPanel.components.DatePicker = DatePicker;
        // appControlPanel.components.DateTimePicker = DateTimePicker;

        //todo: ActionModel, modelExtension 现在都只会扩展，how to 继承改原来
        ControlPanel.modelExtension = "RangeControlPanel";
        return appControlPanel;
    });

    return ControlPanel;
});
