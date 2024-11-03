odoo.define('aspl_vehicle_rental.vehicle_booking_calender', function (require) {
    "use strict";
    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var Widget = require('web.Widget');
    var rpc = require('web.rpc');
    var QWeb = core.qweb;
    var ajax = require('web.ajax');
    var session = require('web.session');
    var dialogs = require('web.view_dialogs');
    var field_utils = require('web.field_utils');
    var _lt = core._lt;
    var _t = core._t;
    var datepicker = require('web.datepicker');
    var config = require('web.config');
    var Domain = require('web.Domain');
    var DropdownMenu = require('web.DropdownMenu');

    var ResourceView = AbstractAction.extend({
        title: core._t('Vehical Rental Booking'),
        template: 'ResourceViewTemplate',

        init: function (parent, params) {
            this._super.apply(this, arguments);
            var self = this;
            this.action_manager = parent;
            this.params = params;
            this.filtersMapping = [];
            this.items = [];
            this.hotel_domain = [];
            this.propositions = [];
            this.fields = _(fields).chain()
                .map(function (val, key) { return _.extend({}, val, {'name': key}); })
                .filter(function (field) { return !field.deprecated && field.searchable; })
                .sortBy(function (field) {return field.string;})
                .value();
            this.attrs = {_: _, fields: this.fields, selected: null};
            this.value = null;
            this.items = []
            self.get_title = false;
            self.resource_obj = false;
            self.event_obj = false;
            self.first_start = false;
            self.first_end = false;
            self.second_start = false;
            self.second_end = false;
            self.final_date = false,
            self.cust_list = [];
            self.color_dict = false;
            self.calendar_cust_search_string = '';
            self.highlight_dates = [];
            self.beautician_lst = [];
            self.event_date_list = []
            var fields = {}
        },

        start: function () {
            this._super.apply(this, arguments);
            this.set("title", this.title);
            var self = this;
            this.items = [];
        },
        custom_events: {
            hotel_remove_proposition: '_onHotelRemoveProposition',
            hotel_confirm_proposition: '_onHotelConfirmProposition',
            hotel_new_filters: '_onHotelNewFilters',
        },
        events: {
            'click #model_type_ids': 'my_method',
            'click #fuel_type_ids': 'my_method',
            'change .o_searchview_extended_prop_field': 'changed',
            'change .o_searchview_extended_prop_op': 'operator_changed',
            'click .o_searchview_extended_delete_prop': function (e) {
                e.stopPropagation();
                this.trigger_up('hotel_remove_proposition');
            },
            'keyup .o_searchview_extended_prop_value': function (ev) {
                if (ev.which === $.ui.keyCode.ENTER) {
                    var abc = this.trigger_up('hotel_confirm_proposition');
                }
            },
            'click .o_apply_hotel_filter': '_onHotelApplyClick',
            'click .o_add_custom_filter': 'add_custom_filter',
            'click .autocomplete_li': 'autocomplete_click',
        },

        my_method: function(e){
            var model_id=$('#model_type_ids').val()
            var fuel_id=$('#fuel_type_ids').val()
            var self = this;
            var moment_date = false;
            rpc.query({
                model:'fleet.vehicle.order',
                method:'get_booking_data',
                args:[model_id,fuel_id]
            }).then(function (data){
                $('#backend_resource_view').fullCalendar('destroy');
                self.prepareResourceView(moment_date,data)
            })
        },

        prepareResourceView: function (moment_date,data) {
            var self = this;
            var resourceList = false;
            var eventList = false;
            var color_dict = false;
            var counter = -1;
            if (data){
                resourceList = data[0];
                if (data[1]){
                    eventList=data[1]
                }
            }
            self.event_obj = eventList;
            self.event_date_list = eventList;
            self.$el.find('#backend_resource_view').fullCalendar({

                defaultView: 'timelineWeek',
                defaultDate: moment_date ? moment(momentt_date).format('YYYY-MM-DD') : moment(),
                aspectRatio: 5,
                editable: true,
                allDaySlot: false,
                eventOverlap: false,
                selectable: true,
                height: 550,
                resourceAreaWidth: "17%",
                slotDuration: '00:00',
                eventLimit: true, // allow "more" link when too many eventsfullcalendar
                slotEventOverlap: true,
                resourceGroupField: 'building',
                resources: resourceList,
                events: eventList,

                customButtons: {
                },
                header: {
                    left: 'prev, today, next',
                    center: 'title',
                    right: 'month, timelineWeek',
                },
                buttonText: {
                    month: 'Month',
                    today: 'Today',
                },
                buttonIcons:{
                     prev: 'left-double-arrow',
                     next: 'right-double-arrow',
                },
                resourceColumns: [{
                    labelText: 'Vehicles',
                    field: 'title'
                }],

                eventRender: function (event, element) {
                    $(element).css({
                        "font-weight": "bold",
                        'font-size': '12px',
                        'color':'white',
                    });
                    if (event['rendering'] === 'background') {} else {

                        var id = event.resourceId;
                        var line_id = event.line_id;
                        var vehical_type=event.type
                        var vehical_id=event.vehicle_id
                        element.prepend("<div data-id=" + id + " data-type=" + vehical_type + " data-vehicle-id=" + vehical_id + " class='ibox-tools' style='cursor:pointer;float:right;position:relative;height:20px;width: auto;z-index: 1000;'><a style='position:relative;background-color: transparent; margin-right: 12px;height: auto;' class='testing pull-left'><i class='fa fa-times remove_booking' data-id=" + id + " data-line-id=" + line_id + " style='position:absolute;height:auto;margin-left: 2px;'></i></a></div>");
                    }
                    element.find(".remove_booking").click(function (e) {
                        if (confirm('Are you sure you want to delete ?')) {
                            $('#backend_resource_view').fullCalendar('removeEvents', $(e.currentTarget).attr('data-id'));
                            rpc.query({
                                model: 'fleet.vehicle.order',
                                method: 'remove_event',
                                args: [$(e.currentTarget).attr('data-line-id')]
                            }, {
                                async: false
                            }).then(function (res) {
                                $('#backend_resource_view').fullCalendar('removeEvents', event._id);
                                return true;
                            });
                        } else {}
                    });
                },

                /*EVENT RESIZE*/
                eventResize: function (event, delta, revertFunc) {
                    var params = {
                        model: 'walk.in.detail',
                        method: 'remove_event',
                        args: [parseInt(event.id), moment(event.start).format("YYYY-MM-DD HH:mm:ss"), moment(event.end).format("YYYY-MM-DD HH:mm:ss")],
                    }
                    rpc.query(params, {
                            async: false
                        })
                        .then(function (res) {

                        });
                },
                eventClick: function (event, element) {
                    var self = this;
                },

                /*SELECT EVENT ON VIEW CLICK*/
                select: function (start, end, jsEvent, view, resource) {
                    var current_time = moment().format('YYYY-MM-DD HH:mm:ss')
                    var start_date = moment(start).format('YYYY-MM-DD HH:mm:ss')
                    var end_date = moment(end).format('YYYY-MM-DD HH:mm:ss')
                    var context=false
                    context=rpc.query({
                        model: 'fleet.vehicle.order',
                        method: 'start_and_end_date_global',
                        args:[start_date, end_date],
                    }).then(function (sdate) {
                        if (sdate) {
                            context={
                                'default_from_date': sdate[0],
                                'default_to_date': sdate[1],
                                'default_is_true':true,
                            }
                        }
                        if(resource){
                            var id = resource.id
                            var vehicle_type= resource.type
                            var vehicle_id=resource.vehicle_id
                            var list=[[6,0,[vehicle_id]]]
                            context['default_vehicle_type_id']=vehicle_type
                            context['default_vehicle_order_lines_ids']=list
                            context['default_is_true']=true
                        }
                        var dialog = new dialogs.FormViewDialog(self, {
                            res_model: 'fleet.vehicle.order',
                            res_id: false,
                            title: _t("Rental Order"),
                            readonly: false,
                            context: context,
                            on_saved: function (record, changed) {
                                $('#backend_resource_view').fullCalendar('destroy');
                                self.renderElement()
                                $('.fc-divider').find('.fc-cell-content').addClass('fc-expander');
                            },
                        }).open();
                    });

                },

                eventDrop: function (event, delta, revertFunc) {
                    rpc.query({
                        model: 'walk.in.detail',
                        method: 'update_resource_view_event_drop',
                        args: [event.id,
                            parseInt(event.resourceId),
                            moment(event.start).format('YYYY-MM-DD HH:mm:ss'),
                            moment(event.end).format('YYYY-MM-DD HH:mm:ss'),
                            moment(event.start).format('YYYY-MM-DD'),
                            moment(event.end).format('YYYY-MM-DD'),
                        ]
                    }, {
                        async: false
                    }).then(function (res) {
                        if (res) {
                        } else {
                            revertFunc()
                        }
                    });
                },
                selectAllow: function (selectInfo) {
                    if (selectInfo.start.isBefore(moment().subtract(1, 'days').toDate()))
                        return false;
                    return true;
                },
                viewRender: function (view, element) {
                    if (view.type && view.type == "customWeek") {
                        $('.fc-divider').find('.fc-cell-content').addClass('fc-expander');
                    }
                }
            });


        },

        next_prev_today_BtnClick: function () {
            var self = this;
            var date = moment($('#backend_resource_view').fullCalendar('getDate')).format('YYYY-MM-DD');
            $('#backend_resource_view').fullCalendar('destroy');
            self.prepareResourceView(date);
            $('.fc-divider').find('.fc-cell-content').addClass('fc-expander');
        },

        changed: function (e) {
            var nval = this.$(".o_searchview_extended_prop_field").val();
            if(this.attrs.selected === null || this.attrs.selected === undefined || nval != this.attrs.selected.name) {
                this.select_field(_.detect(this.fields, function (x) {return x.name == nval;}));
            }
        },

        operator_changed: function (e) {
            this.value.show_inputs($(e.target));
        },
        select_field: function (field) {
            var self = this;
            if(this.attrs.selected !== null && this.attrs.selected !== undefined) {
                this.value.destroy();
                this.value = null;
                this.$('.o_searchview_extended_prop_op').html('');
            }
            this.attrs.selected = field;
            if(field === null || field === undefined) {
                return;
            }

            var type = field.type;
            var Field = core.search_filters_registry.getAny([type, "char"]);

            this.value = new Field(this, field);
            _.each(this.value.operators, function (operator) {
                $('<option>', {value: operator.value})
                    .text(String(operator.text))
                    .appendTo(self.$('.o_searchview_extended_prop_op'));
            });
            var $value_loc = this.$('.o_searchview_extended_prop_value').show().empty();
            this.value.appendTo($value_loc);
        },

        renderElement: function () {
            var self = this;
            this._super.apply(this, arguments);
            var user_ids = [];
            rpc.query({
                    model: 'fleet.vehicle.model.brand',
                    method: 'search_read',
                    fields: ['id', 'name'],
                }, {
                    async: false
                }).then(function (model_name) {
                    var model_type_html = QWeb.render('model_template', {
                        model_name: model_name,
                        widget: self,
                    });
                    self.$el.find('#model_selection').empty();
                    self.$el.find('#model_selection').append(model_type_html);
            });
            rpc.query({
                    model: 'fuel.type',
                    method: 'search_read',
                    fields: ['id', 'name'],
                }, {
                    async: false
                }).then(function (model_name) {
                    var model_type_html = QWeb.render('fuel_template', {
                        model_name: model_name,
                        widget: self,
                    });
                    self.$el.find('#fuel_selection').empty();
                    self.$el.find('#fuel_selection').append(model_type_html);
            });
            setTimeout(function () {
                this.$('#cal_cust_search').autocomplete({
                    source: function (request, response) {
                        var query = request.term;
                        var search_timeout = null;
                        self.loaded_partners = [];
                        if (query) {
                            search_timeout = setTimeout(function () {
                                var partners_list = [];
                                self.loaded_partners = self.load_partners(query);
                                _.each(self.loaded_partners, function (partner) {
                                    partners_list.push({
                                        'id': partner.id,
                                        'value': partner.name,
                                        'label': partner.name
                                    });
                                });
                                response(partners_list);
                            }, 70);
                        }
                    },

                    select: function (event, partner) {
                        event.stopImmediatePropagation();
                        if (partner.item && partner.item.id) {
                            var selected_partner = _.find(self.loaded_partners, function (customer) {
                                return customer.id == partner.item.id;
                            });

                            var highlight_dates = [];
                            _.find(self.event_obj, function (customer) {
                                if (customer.partner_id === selected_partner.id) {
                                    highlight_dates.push(moment(customer.start, 'YYYY-MM_DD').format('D-M-YYYY'));
                                }
                            });
                            self.highlight_dates = highlight_dates;
                            if (highlight_dates && highlight_dates.length > 0) {
                                $(".ui-datepicker-trigger").trigger("click");
                                $('#ui-datepicker-div').show();
                            } else {
                                self.highlight_dates = [];
                            }
                        }
                    },
                    focus: function (event, ui) {
                        event.preventDefault(); // Prevent the default focus behavior.
                    },
                    close: function (event) {
                        // it is necessary to prevent ESC key from propagating to field
                        // root, to prevent unwanted discard operations.
                        if (event.which === $.ui.keyCode.ESCAPE) {
                            event.stopPropagation();
                        }
                    },
                    autoFocus: true,
                    html: true,
                    minLength: 1,
                    delay: 200
                });

                self.prepareResourceView();

                var input = document.createElement("input");
                input.type = "text";
                input.name = "";
                input.setAttribute("id", "select_date");
                input.setAttribute("class",'datepicker');
                input.setAttribute("style", "display:none;");

                var span_tag = document.createElement("SPAN");
                span_tag.name = "";
                span_tag.setAttribute('class', 'title-display');
                $('.fc-left').find('.fc-next-button').after(input);
                $('.fc-left').find('.fc-next-button').after(span_tag);
                $('.title-display').html(self.get_title)
                $("#select_date").datepicker({
                    showOn: "button",
                    buttonText: "<i class='fa fa-calendar'></i>",
                    beforeShowDay: function (date) {
                        if (self.highlight_dates) {
                            var month = date.getMonth() + 1;
                            var year = date.getFullYear();
                            var day = date.getDate();
                            var newdate = day + "-" + month + '-' + year;
                            var tooltip_text = "New event on " + newdate;
                            if ($.inArray(newdate, self.highlight_dates) != -1) {
                                return [true, "highlight", tooltip_text];
                            }
                            return [true];
                        }
                    },
                    onSelect: function(dateText) {
                        $('#backend_resource_view').fullCalendar('gotoDate', moment(dateText).format('YYYY-MM-DD'));
                        $('.title-display').html(self.get_title)
                        $('#backend_resource_view').fullCalendar('destroy');
                        self.prepareResourceView(moment(dateText).format('YYYY-MM-DD'))

                        var input = document.createElement("input");
                        input.type = "text";
                        input.name = "";
                        input.setAttribute("id", "select_date");
                        input.setAttribute("class",'datepicker');

                        var span_tag = document.createElement("SPAN");
                        input.name = "";
                        span_tag.setAttribute('class', 'title-display');
                        $('.fc-left').find('.fc-calendarButton-button').after(input);
                        $('.fc-left').find('.fc-calendarButton-button').after(span_tag);
                        $('.fc-divider').find('.fc-cell-content').addClass('fc-expander');
                        display("Selected date: " + dateText + "; input's current value: " + this.value);
                    }
                });

                $('button.o_dropdown_toggler_btn').on('click', function(e){
                    e.preventDefault()
                    e.stopPropagation();
                    this.generatorMenuIsOpen = !this.generatorMenuIsOpen;
                    var def;
                    if (!this.generatorMenuIsOpen) {
                        _.invoke(this.propositions, 'destroy');
                        this.propositions = [];
                    }
                    $('.o_filters_menu').toggle()
                    self.changed()
                });

                $("#room_type_ids").select2({
                    placeholder: "Room Type",
                    allowClear: true,
                });

                $("#select_filter").select2({
                    placeholder: "Filter",
                    allowClear: true,
                });

                $('#select_filter').change(function (e) {
                });

                $('.o_hotel_searchview_input').keyup(function(event){
                    var keycode = (event.keyCode ? event.keyCode : event.which);
                    var li = $('.o_hotel_searchview_autocomplete li');
                    var liSelected;
                    if(keycode == 40){
                        if(! liSelected){
                            liSelected = $('.o_hotel_searchview_autocomplete li.o-selection-focus')
                            liSelected.removeClass('o-selection-focus');
                            var next = liSelected.next();
                            if(next.length > 0){
                                liSelected = next.addClass('o-selection-focus');
                            }else{
                                liSelected = li.eq(0).addClass('o-selection-focus');
                            }
                        }else{
                            liSelected = li.eq(0).addClass('o-selection-focus');
                        }
                    }
                    else if(keycode == 38){
                        if(! liSelected){
                            liSelected = $('.o_hotel_searchview_autocomplete li.o-selection-focus')
                            liSelected.removeClass('o-selection-focus');
                            var next = liSelected.prev();
                             if(next.length > 0){
                                liSelected = next.addClass('o-selection-focus');
                            }else{
                                liSelected = li.last().addClass('o-selection-focus');
                            }
                        }else{
                            liSelected = li.last().addClass('o-selection-focus');
                        }
                    }
                    if(keycode == '13'){
                        $(this).parents('.o_hotel_searchview_input_container').find('.o_hotel_searchview_autocomplete li.o-selection-focus').trigger('click')
                    }
                    if(keycode == 8){
                     $('.o_hotel_facet_remove').trigger('click');
                    }
                    if($('.o_hotel_searchview_input').val()){
                        $('.o_hotel_searchview_autocomplete').show()
                        $('.o_hotel_searchview_autocomplete li strong').html($('.o_hotel_searchview_input').val())
                    }
                    else{
                        $('.o_hotel_searchview_autocomplete li strong').html($('.o_hotel_searchview_input').val())
                    }
                });

                $('.autocomplete_li').mouseover(function (e){
                    $(e.currentTarget).addClass('o-selection-focus');
                });
                $('.autocomplete_li').mouseout(function (e){
                    $(e.currentTarget).removeClass('o-selection-focus');
                });
            },
            0);
        },

        load_partners: function (query) {
            var self = this;
            var loaded_partners = [];
            rpc.query({
                model: 'res.partner',
                method: 'search_read',
                fields: ['name'],
                domain: ['|', '|', ['name', 'ilike', query],
                    ['mobile', 'ilike', query],
                    ['email', 'ilike', query]
                ],
                limit: 7,
            }, {
                async: false
            }).then(function (partners) {
                loaded_partners = partners
            });
            return loaded_partners;
        },
    });

    core.action_registry.add('resource_view_new', ResourceView);
    return {
        ResourceView: ResourceView,
    };
});
