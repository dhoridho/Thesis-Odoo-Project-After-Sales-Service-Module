odoo.define('equip3_list_view_manager_extend.renderer', function (require) {

    "use strict";

    var core = require('web.core');
    var _t = core._t;
    var ListRenderer = require('web.ListRenderer');
    var AbstractView = require('web.AbstractView');
    var QWeb = core.qweb;
    var BasicController = require('web.BasicController');
    var datepicker = require("web.datepicker");
    var fieldUtils = require('web.field_utils');
    var config = require('web.config');
    var pyUtils = require('web.py_utils');
    var ks_basic_view = require('web.BasicView');
    var abstractCont = require('web.AbstractController');
    var listCont = require('web.ListController');
    var framework = require('web.framework');
    const session = require('web.session');
    const { WidgetAdapterMixin } = require('web.OwlCompatibility');
    var ks_list_view_manager = require('ks_list_view_manager.renderer')

    ListRenderer.include({
        ks_textBox: function (node) {
            var self = this;
            if (node.tag === "field") {
                if (!(self.state.fields[node.attrs.name].type === "one2many" || self.state.fields[node.attrs.name].type === "many2many")) {
                    var ks_name = node.attrs.name;
                    var ks_fields = self.state.fields[ks_name];
                    var ks_selection_values = []
                    var ks_description;
                    var ks_field_type;
                    var $ks_from;
                    var ks_field_identity;
                    var ks_identity_flag = false;
                    var ks_field_id = ks_name;
                    var ks_is_hide = true;
                    var ks_widget_flag = true;
                    if (node.attrs.widget) {
                        ks_description = self.state.fieldsInfo.list[ks_name].Widget.prototype.description;
                    }
                    if (ks_fields) {
                        ks_field_type = self.state.fields[ks_name].type;

                        if (ks_field_type === "selection") {
                            ks_selection_values = self.state.fields[ks_name].selection;
                        }
                        if (ks_description === undefined) {
                            ks_description = node.attrs.string || ks_fields.string;
                        }
                    }

                    var $th = $('<th>').addClass("ks_advance_search_row ");
                    if (ks_field_type === "date" || ks_field_type === "datetime") {
                        if (self.ks_call_flag > 1) {
                            $th.addClass("ks_fix_width");
                        }
                    }

                    if (ks_field_type === "date" || ks_field_type === "datetime") {
                        if (!(self.ks_call_flag > 1)) {
                            self.ks_call_flag += 1;
                            $ks_from = self.ks_textBox(node);
                            ks_identity_flag = true
                        }
                        if (self.ks_call_flag == 2 && ks_identity_flag == false) {
                            ks_field_id = ks_name + "_lvm_end_date"
                            ks_field_identity = ks_field_id + " lvm_end_date"
                        } else {
                            ks_field_id = ks_name + "_lvm_start_date"
                            ks_field_identity = ks_field_id + " lvm_start_date"
                        }
                    }

                    var $input = $(QWeb.render("ks_list_view_advance_search", {
                        ks_id: ks_field_id,
                        ks_description: ks_description,
                        ks_type: ks_field_type,
                        ks_field_identifier: ks_field_identity,
                        ks_selection: ks_selection_values
                    }));

                    if ((ks_field_type === "date" || ks_field_type === "datetime") && (self.ks_call_flag == 2 && ks_identity_flag == false)) {
                        if (self.state.domain.length === 0) {
                            $input.addClass("d-none");
                            $th.addClass("ks_date_inner");
                        }

                        if (!(self.state.domain.length === 0)) {
                            if (Object.values(self.ks_field_popup) !== undefined) {
                                for (var ks_hide = 0; ks_hide < Object.keys(self.ks_field_popup).length; ks_hide++) {
                                    if ((Object.keys(self.ks_field_popup)[ks_hide] === ks_name)) {
                                        ks_is_hide = false
                                        break
                                    }
                                }
                                if (self.ksDomain) {
                                    if (ks_is_hide === true) {
                                        $input.addClass("d-none");
                                        $th.addClass("d-none");
                                    } else {
                                        $th.addClass("ks_date_inner");
                                    }
                                } else {
                                    $input.addClass("d-none");
                                    $th.addClass("d-none");
                                }
                            }
                        }
                    }

                    if (self.ksDomain != null && self.ksDomain.length) {
                        if (self.ksDomain[self.ksDomain.length - 1] === self.state.domain[self.state.domain.length - 1]) {
                            if (ks_field_type === "date" || ks_field_type === "datetime") {
                                for (var ks_add_span = 0; ks_add_span < Object.keys(self.ks_field_popup).length; ks_add_span++) {
                                    if (Object.keys(self.ks_field_popup)[ks_add_span] === ks_name) {
                                        for (var ks_add_span_inner = 0; ks_add_span_inner < Object.values(self.ks_field_popup)[ks_add_span].length - 1; ks_add_span_inner++) {

                                            var $div = $('<div>').addClass("ks_inner_search")
                                            $div.attr('id', ks_name + '_value' + ks_add_span_inner)
                                            var $span = $('<span>');
                                            if (ks_field_type === "datetime") {
                                                $span = $span.addClass("ks_date_chip_ellipsis");
                                            }
                                            $span.attr('id', ks_name + '_ks_span' + ks_add_span_inner)

                                            var $i = $('<i>').addClass("fa fa-times")
                                            $i.addClass('ks_remove_popup');

                                            if (self.ks_call_flag == 2 && ks_identity_flag == false) {
                                                $span.text(Object.values(self.ks_field_popup)[ks_add_span][1])
                                                $span.attr("title", Object.values(self.ks_field_popup)[ks_add_span][1]);
                                                $input.prepend($div);
                                                $input.find("#" + Object.keys(self.ks_field_popup)[ks_add_span] + "_value" + ks_add_span_inner).prepend($i);
                                                $input.find("#" + Object.keys(self.ks_field_popup)[ks_add_span] + "_value" + ks_add_span_inner).prepend($span)
                                            } else {
                                                $input.addClass("ks_date_main");
                                                $span.text(Object.values(self.ks_field_popup)[ks_add_span][0]);
                                                $span.attr("title", Object.values(self.ks_field_popup)[ks_add_span][0]);
                                                $input.prepend($div);
                                                $input.find("#" + Object.keys(self.ks_field_popup)[ks_add_span] + "_value" + ks_add_span_inner).prepend($i);
                                                $input.find("#" + Object.keys(self.ks_field_popup)[ks_add_span] + "_value" + ks_add_span_inner).prepend($span);
                                            }
                                        }
                                    }
                                }
                            } else if (ks_field_type === "selection") {
                                for (var ks_add_span = 0; ks_add_span < Object.keys(self.ks_field_popup).length; ks_add_span++) {
                                    if (Object.keys(self.ks_field_popup)[ks_add_span] === ks_name) {
                                        for (var ks_add_span_inner = 0; ks_add_span_inner < Object.values(self.ks_field_popup)[ks_add_span].length; ks_add_span_inner++) {
                                            var value;
                                            var $div = $('<div>').addClass("ks_inner_search")
                                            $div.attr('id', ks_name + '_value' + ks_add_span_inner)

                                            var $span = $('<span>').addClass("ks_advance_chip");
                                            $span.attr('id', ks_name + '_ks_span' + ks_add_span_inner)
                                            $span.addClass("ks_advance_chip_ellipsis");

                                            var $i = $('<i>').addClass("fa fa-times")
                                            $i.addClass('ks_remove_popup');

                                            for (var sel = 0; sel < ks_selection_values.length; sel++) {
                                                if (ks_selection_values[sel][0] === Object.values(self.ks_field_popup)[ks_add_span][ks_add_span_inner]) {
                                                    value = ks_selection_values[sel][1];
                                                }
                                            }

                                            $span.text(value)
                                            $span.attr("title", value);
                                            $input.prepend($div);
                                            $input.find("#" + Object.keys(self.ks_field_popup)[ks_add_span] + "_value" + ks_add_span_inner).prepend($i);
                                            $input.find("#" + Object.keys(self.ks_field_popup)[ks_add_span] + "_value" + ks_add_span_inner).prepend($span)
                                        }
                                    }
                                }
                            } else {
                                for (var ks_add_span = 0; ks_add_span < Object.keys(self.ks_field_popup).length; ks_add_span++) {
                                    if (Object.keys(self.ks_field_popup)[ks_add_span] === ks_name) {
                                        for (var ks_add_span_inner = 0; ks_add_span_inner < Object.values(self.ks_field_popup)[ks_add_span].length; ks_add_span_inner++) {

                                            var $div = $('<div>').addClass("ks_inner_search")
                                            $div.attr('id', ks_name + '_value' + ks_add_span_inner)

                                            var $span = $('<span>').addClass("ks_advance_chip");

                                            if (!(ks_field_type === "date" || ks_field_type === "datetime")) {
                                                $span.addClass("ks_advance_chip_ellipsis");
                                            }


                                            $span.attr('id', ks_name + '_ks_span' + ks_add_span_inner)
                                            var $i = $('<i>').addClass("fa fa-times")

                                            $i.addClass('ks_remove_popup');
                                            if (ks_field_type === 'monetary' || ks_field_type === 'integer' || ks_field_type === 'float') {
                                                var currency = self.getSession().get_currency(self.ks_list_view_data.currency_id);
                                                var formatted_value = fieldUtils.format.float(Object.values(self.ks_field_popup)[ks_add_span][ks_add_span_inner] || 0, {
                                                    digits: currency && currency.digits
                                                });
                                                $span.text(formatted_value);
                                                $span.attr('title', formatted_value);

                                            } else {
                                                $span.text(Object.values(self.ks_field_popup)[ks_add_span][ks_add_span_inner])
                                                $span.attr('title', Object.values(self.ks_field_popup)[ks_add_span][ks_add_span_inner]);
                                            }
                                            if (!(ks_field_type === 'many2one' || ks_field_type === 'many2many' || ks_field_type === 'one2many'))
                                                $input.find('input').removeAttr('placeholder');
                                            $input.prepend($div);
                                            $input.find("#" + Object.keys(self.ks_field_popup)[ks_add_span] + "_value" + ks_add_span_inner).prepend($i);
                                            $input.find("#" + Object.keys(self.ks_field_popup)[ks_add_span] + "_value" + ks_add_span_inner).prepend($span)
                                        }
                                    }
                                }
                            }
                        }
                    }

                    if (self.ksDomain != null && self.ksDomain.length) {
                        if (!(self.ksDomain[self.ksDomain.length - 1] === self.state.domain[self.state.domain.length - 1])) {
                            delete self.ks_field_domain_dict
                            delete self.ksDomain
                            self.ksBaseDomain = []
                            self.ks_field_domain_dict = {}
                            self.ks_key_fields.splice(0, self.ks_key_fields.length)
                            self.ks_field_domain_list.splice(0, self.ks_field_domain_list.length)
                        }
                    }


                    if (ks_field_type === "date" || ks_field_type === "datetime") {
                        for (var i = 0; i < self.state.domain.length; i++) {
                            if (ks_field_identity.split("_lvm_end_date")[0] === self.state.domain[i][0] || ks_field_identity.split("_lvm_start_date")[0] === self.state.domain[i][0]) {
                                ks_widget_flag = false
                                break;
                            }
                        }
                    }

                    if (ks_widget_flag && ks_field_type === "date") {
                        var widget_key = "ksStartdatePickerWidget" + ks_field_identity;
                        self[widget_key] = new(datepicker.DateWidget)(this);
                        self[widget_key].appendTo($input.find('.custom-control-searchbar-change')).then((function () {
                            self["ksStartdatePickerWidget" + ks_field_identity].$el.addClass("ks_btn_middle_child o_input");
                            self["ksStartdatePickerWidget" + ks_field_identity].$el.find("input").attr("placeholder", "Search");
                        }).bind(this));

                        self[widget_key].on("datetime_changed", widget_key, function () {
                            self.ks_on_date_filter_change(widget_key);
                        });
                    }


                    if (ks_widget_flag && ks_field_type === "datetime") {
                        var widget_key = "ksStartdatetimePickerWidget" + ks_field_identity;
                        self[widget_key] = new(datepicker.DateTimeWidget)(this);
                        self[widget_key].appendTo($input.find('.custom-control-searchbar-change')).then((function () {
                            self["ksStartdatetimePickerWidget" + ks_field_identity].$el.addClass("ks_btn_middle_child o_input");
                            self["ksStartdatetimePickerWidget" + ks_field_identity].$el.find("input").attr("placeholder", "Search");
                        }).bind(this));

                        self[widget_key].on("datetime_changed", widget_key, function () {
                            self.ks_on_date_filter_change(widget_key);
                        });
                    }


                    if (self.ksDomain != null && this.ksDomain.length) {
                        if (self.ksDomain.length === self.state.domain.length) {
                            for (var i = 0; i < self.state.domain.length; i++) {
                                if (!(self.state.domain[i] === self.ksDomain[i])) {
                                    self.ksbaseFlag = true
                                }
                            }
                        }

                        if (self.ksbaseFlag === true) {
                            self.ksBaseDomain = self.state.domain
                            self.ksbaseFlag = false
                        }
                    }

                    if ((self.ksDomain === null || self.ksDomain === undefined || self.ksDomain.length === 0) && self.state.domain.length) {
                        self.ksBaseDomain = self.state.domain
                    }
                    if ((self.ksDomain === null || self.ksDomain === undefined || self.ksDomain.length === 0) && self.state.domain.length === 0) {
                        self.ksBaseDomain = self.state.domain
                    }

                    $th.append($input);
                    if (self.ks_call_flag == 2) {
                        $th.append($ks_from);
                        self.ks_datepicker_flag += 1;
                    }
                    if (self.ks_datepicker_flag == 2) {
                        self.ks_call_flag = 1;
                        self.ks_datepicker_flag = 0;
                    }
                } else {
                    var $th = $('<th>').addClass("ks_advance_search_row ");
                }
                return $th;
            } else {
                return $('<th>').addClass("ks_advance_search_row ");;
            }
        },
    });

        
});