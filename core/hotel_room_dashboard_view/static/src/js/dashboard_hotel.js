odoo.define('hotel_room_dashboard_view.dashboard_hotel', function (require) {
    "use strict";
    var core = require('web.core');
    var Widget = require('web.Widget');
    var AbstractAction = require('web.AbstractAction');
    var webclient = require('web.WebClient');
    var datepicker = require('web.datepicker');
    var time = require('web.time');
    var framework = require('web.framework');
    var session = require('web.session');
    var _t = core._t;
    var _lt = core._lt;
    var QWeb = core.qweb;
    var Class = core.Class;
    //	var session = require('web.session');

    var rpc = require('web.rpc');
    var ajax = require('web.ajax');
    var dialogs = require('web.view_dialogs');
    var field_utils = require('web.field_utils');
    var field_registry = require('web.field_registry');
    var field_utils = require('web.field_utils');
    var _lt = core._lt;
    //    var search_inputs = require('web.search_inputs');
    //    var config = require('web.config');
    var Domain = require('web.Domain');
    //    var DropdownMenu = require('web.DropdownMenu');
    var context = {}
    var id_id = false;
    var self = this
    var HotelDashboardView = AbstractAction.extend({
        template: 'hotel_dashboard_template',

        init: function (parent, options) {
            console.log("INit ")
            this._super(parent, options);
            options = options || {};
            var self = this;
            this.reservation_lines = null;
            this.reservations = null;

            this.reservation_lines1 = null;
            this.reservations1 = null;
            this.hotel_room = null;
            this.booking_data = new Array();
            this.categories;
            this.product_lines;
            this.product_template_lines;
            this.selected_categ = new Array();
            this.selected_categ_room = new Array();
            this.guest_details = new Array();
            this.housekeeping_lines = new Array();
            this.folio_id = null
            this.view_ids;
            this.value = null;
            this.items = []
            self.event_data = false;

        },

        start: function () {
            var self = this;
            self._super.apply(this,arguments);
            self.renderElement();
            self.fetch('sale.shop', ['id', 'name'], [], {}).then(function (shop) {
                for (var i = 0; i < shop.length; i++) {
                    $("#shops").append($("<option>", {
                        text: shop[i].name,
                        value: shop[i].id
                    }));
                }
                self.load_hotel_function();
            });
        },

        load_hotel_function: function (e) {
            var self = this;
            var domain = []
            self.hotel_dashboard_view(domain)
            $('#booking_calendar').fullCalendar('removeEvents');
            $('#booking_calendar').fullCalendar('renderEvent', self.event_data)
            $('#booking_calendar').fullCalendar('addEventSource', self.event_data);
            $('#booking_calendar').fullCalendar('refetchEvents');
            $('#shops').change(function (e) {
                var hotel_id = $('#shops').val()
                $('#booking_calendar').fullCalendar('destroy');
                self.hotel_dashboard_view()

            });
            $('#dashboard_reload').on('click', function (e) {
                $('[data-toggle="popover"]').each(function () {
                    if (!$(this).is(e.target) && $(this).has(e.target).length === 0 && $('.popover').has(e.target).length === 0) {
                        $(this).popover('hide');
                    }
                });
                var list_of_cls_name = e.target.className
                var x = 'fc-prev-button'
                var y = 'fc-next-button'
                var z = 'fc-month-button'
                var w = 'fc-customWeek-button'
                var t = 'fc-today-button'
                if (!(list_of_cls_name.includes(x) || list_of_cls_name.includes(y) || list_of_cls_name.includes(z) || list_of_cls_name.includes(w) || list_of_cls_name.includes(t))) {
                    $('#booking_calendar').fullCalendar('destroy');
                    self.hotel_dashboard_view()
                    $('.fc-divider').find('.fc-cell-content').addClass('fc-expander');
                    $('.popover').popover('hide')
                }
            });
        },

        hotel_dashboard_view: function (moment_date) {
            var self = this;
            var resourceList = false;
            var eventList = false;
            var room_type_list_data = [];
            var room_data_event_list = [];
            var ml = [];
            var data = {}
            var room_k = false
            var room_dirty = false
            var remaining = false
            var vals_folio_id = false

            $.when(this.load_hotel()).then(function () {
                self.selected_categ = new Array();
                self.selected_categ_room = new Array();
                for (var res = 0; res < self.hotel_room.length; res++) {
                    self.selected_categ.push({
                        id: self.hotel_room[res].product_id[0],
                        building: self.hotel_room[res].categ_id[1],
                        room: self.hotel_room[res].name,
                    });


                    var today = new Date();
                    var Today = moment(today).format("YYYY-MM-DD")
                    for (var hline = 0; hline < self.housekeeping_lines.length; hline++) {
                        if (self.housekeeping_lines[hline].room_no[0] == self.hotel_room[res].product_id[0]) {
                            if ((self.housekeeping_lines[hline].current_date >= Today) && (Today <= self.housekeeping_lines[hline].end_date)) {
                                //                                       console.log("self1::::::::",self.hotel_room[res].product_id[0])
                                if (self.housekeeping_lines[hline].quality == 'clean') {
                                    self.selected_categ_room.push({

                                        title: 'Unavailable/ Under Cleaning',
                                        description: 'Unavailable/ Under Cleaning',
                                        start: moment(self.housekeeping_lines[hline].current_date).format('YYYY-MM-DD 14:00:00'),
                                        end: moment(self.housekeeping_lines[hline].end_date).format('YYYY-MM-DD 12:00:00'),
                                        resourceIds: [self.hotel_room[res].product_id[0]],
                                        color: 'black',
                                        partner_id: false,
                                        resourceEditable: false,
                                        disableResizing: false,

                                    })
                                }
                                else {
                                    self.selected_categ_room.push({

                                        title: 'Unavailable/ Under Maintenance',
                                        description: 'Unavailable/ Under Maintenance',
                                        start: moment(self.housekeeping_lines[hline].current_date).format('YYYY-MM-DD 14:00:00'),
                                        end: moment(self.housekeeping_lines[hline].end_date).format('YYYY-MM-DD 12:00:00'),
                                        resourceIds: [self.hotel_room[res].product_id[0]],
                                        color: 'purple',
                                        partner_id: false,
                                        resourceEditable: false,
                                        disableResizing: false,

                                    })
                                }
                            }
                        }



                    }
                }
                for (var res_line_id = 0; res_line_id < self.reservation_lines1.length; res_line_id++) {
                    room_dirty = false
                    for (var res_line = 0; res_line < self.reservations1.length; res_line++) {
                        if (self.reservations1[res_line].id == self.reservation_lines1[res_line_id].line_id[0]) {

                            if (self.reservations1[res_line].state == 'done') {
                                remaining = false
                                vals_folio_id = false
                                for (var res = 0; res < self.folio_id.length; res++) {
                                    if (self.reservations1[res_line].id == self.folio_id[res].reservation_id[0]) {
                                        remaining = self.folio_id[res].remaining_amt;
                                        if (self.folio_id[res].state == 'check_out') {
                                            vals_folio_id = true

                                        }

                                    }

                                }


                                if (vals_folio_id == true) {


                                    self.selected_categ_room.push({

                                        title: self.reservations1[res_line].reservation_no + self.reservations1[res_line].partner_id[1] + "[" + remaining + "]",
                                        description: self.reservations1[res_line].reservation_no,
                                        start: self.reservation_lines1[res_line_id].checkin,
                                        end: self.reservation_lines1[res_line_id].checkout,
                                        resourceIds: [self.reservation_lines1[res_line_id].room_number[0]],
                                        color: 'royalBlue',
                                        partner_id: self.reservations1[res_line].partner_id,
                                        state: self.reservations1[res_line].state,

                                        checkin: moment(self.reservation_lines1[res_line_id].checkin).format('YYYY-MM-DD 14:00:00'),
                                        checkout: moment(self.reservation_lines1[res_line_id].checkout).format('YYYY-MM-DD 12:00:00'),

                                        room_number: self.reservation_lines1[res_line_id].room_number,


                                    })


                                }

                                else {

                                    self.selected_categ_room.push({

                                        title: self.reservations1[res_line].reservation_no + self.reservations1[res_line].partner_id[1] + "[" + remaining + "]",
                                        description: self.reservations1[res_line].reservation_no,
                                        start: self.reservation_lines1[res_line_id].checkin,
                                        end: self.reservation_lines1[res_line_id].checkout,
                                        resourceIds: [self.reservation_lines1[res_line_id].room_number[0]],
                                        color: 'red',
                                        partner_id: self.reservations1[res_line].partner_id,
                                        state: self.reservations1[res_line].state,

                                        checkin: moment(self.reservation_lines1[res_line_id].checkin).format('YYYY-MM-DD 14:00:00'),
                                        checkout: moment(self.reservation_lines1[res_line_id].checkout).format('YYYY-MM-DD 12:00:00'),

                                        room_number: self.reservation_lines1[res_line_id].room_number,


                                    })


                                }




                            }
                            else if (self.reservations1[res_line].state == 'confirm') {

                                self.selected_categ_room.push({

                                    // title: self.reservations1[res_line].reservation_no + self.reservations1[res_line].partner_id[1] + "[" + [self.reservations1[res_line].total_cost1 - self.reservations1[res_line].deposit_cost2] + "]",
                                    title: self.reservations1[res_line].partner_id[1] +' ' + self.reservations1[res_line].reservation_no + "[" + [self.reservations1[res_line].total_cost1 - self.reservations1[res_line].deposit_cost2] + "]",
                                    description: self.reservations1[res_line].reservation_no,
                                    start: self.reservation_lines1[res_line_id].checkin,
                                    end: self.reservation_lines1[res_line_id].checkout,
                                    resourceIds: [self.reservation_lines1[res_line_id].room_number[0]],
                                    color: '#A6A6A6',
                                    partner_id: self.reservations1[res_line].partner_id,
                                    state: self.reservations1[res_line].state,
                                    checkin: moment(self.reservation_lines1[res_line_id].checkin).format('YYYY-MM-DD 14:00:00'),
                                    checkout: moment(self.reservation_lines1[res_line_id].checkout).format('YYYY-MM-DD 12:00:00'),

                                    room_number: self.reservation_lines1[res_line_id].room_number

                                })


                            }
                            else if (self.reservations1[res_line].state == 'draft') {




                                self.selected_categ_room.push({

                                    title:  self.reservations1[res_line].partner_id[1]+' ' + self.reservations1[res_line].reservation_no + "[" + self.reservations1[res_line].total_cost1 + "]",
                                    description: self.reservations1[res_line].reservation_no,
                                    start: self.reservation_lines1[res_line_id].checkin,
                                    end: self.reservation_lines1[res_line_id].checkout,
                                    resourceIds: [self.reservation_lines1[res_line_id].room_number[0]],
                                    color: '#FFDA2F',
                                    partner_id: self.reservations1[res_line].partner_id,
                                    state: self.reservations1[res_line].state,
                                    checkin: moment(self.reservation_lines1[res_line_id].checkin).format('YYYY-MM-DD 14:00:00'),
                                    checkout: moment(self.reservation_lines1[res_line_id].checkout).format('YYYY-MM-DD 12:00:00'),

                                    room_number: self.reservation_lines1[res_line_id].room_number

                                })

                            }
                            else {
                            }
                        }
                    }
                }
                room_type_list_data = self.selected_categ
                room_data_event_list = self.selected_categ_room
                self.event_data = room_data_event_list
                self.$el.find('#booking_calendar').fullCalendar({

                    defaultView: 'customWeek',
                    //                    defaultDate: moment_date ? moment(moment_date).format('YYYY-MM-DD') : moment(),
                    aspectRatio: 1.5,
                    editable: true,
                    allDaySlot: false,
                    eventOverlap: false,
                    selectable: true,
                    height: 420,
                    resourceAreaWidth: "17%",
                    slotDuration: '00:00',
                    eventLimit: true,
                    header: {
                        left: 'title',
                        center: '',
                        right: 'today prev,next,month,customWeek'
                    },
                    views: {
                        customWeek: {
                            type: 'timeline',
                            duration: {
                                weeks: 4
                            },
                            slotDuration: {
                                days: 1
                            },
                            buttonText: 'Week',
                            columnHeaderFormat: 'ddd M/D'
                        },
                        month: {
                            editable: false,
                            selectable: false,
                        }
                    },
                    resourceColumns: [
                        {
                            labelText: 'Room Types',
                            field: 'room'
                        },

                    ],
                    resources: room_type_list_data,
                    resourceGroupField: 'building',
                    weekNumberTitle: 'W',
                    weekNumberCalculation: 'local',
                    buttonText: {
                        prev: "Prev",
                        next: "Next",
                        prevYear: "Prev year",
                        nextYear: "Next year",
                        year: 'Year', // TODO: locale files need to specify this
                        today: 'Today',
                        month: 'Month',
                        week: 'Week',
                        day: 'Day'
                    },
                    selectAllow: function (selectInfo) {
                        //                        console.log("selectInfo::::::::::",selectInfo.resourceId,moment(selectInfo.start).format('YYYY-MM-DD'))
                        if (selectInfo.start.isBefore(moment().subtract(1, 'd').toDate()))
                            return false;
                        //                        var today = new Date();
                        //                        var Today=moment(today).format("YYYY-MM-DD")
                        //                        for (var hline = 0; hline < self.housekeeping_lines.length; hline++) {
                        //                            console.log("product_id::::::::::::::::",self.housekeeping_lines[hline].room_no[0],selectInfo.resourceId)
                        //                            if (self.housekeeping_lines[hline].room_no[0] == selectInfo.resourceId) {
                        //                                console.log("qqqqqqqqqqqqq",self.housekeeping_lines[hline].current_date,)
                        //                                if ((self.housekeeping_lines[hline].current_date <= moment(selectInfo.start).format('YYYY-MM-DD')) && (moment(selectInfo.start).format('YYYY-MM-DD') <= self.housekeeping_lines[hline].end_date)) {
                        //
                        //                                    return false;
                        //                                    break;
                        //                                }
                        //                            }
                        //                        }



                        return true;
                    },
                    select: function (start, end, jsEvent, view, resource) {
                        $('.popover').popover('hide')
                        $(this).popover('hide')
                        var hotel_id = $('#shops').val()
                        var current_time = moment().format('YYYY-MM-DD HH:mm:ss')
                        var start_date = moment(start).format('YYYY-MM-DD 11:00:00')
                        var end_date = moment(end).format('YYYY-MM-DD 09:00:00')


                        var HotelresourceId = resource.id;
                        var dialog = new dialogs.FormViewDialog(self, {
                            res_model: 'hotel.reservation',
                            res_id: false,
                            title: _t("Hotel Reservation"),
                            readonly: false,
                            context: {
                                'checkin': start_date,
                                'checkout': end_date,
                                'hotel_resource': resource.id,
                                'shop': parseInt(hotel_id),
                            },

                            on_saved: function (record, changed) {
                                $('#booking_calendar').fullCalendar('destroy');
                                self.hotel_dashboard_view(moment_date)
                                $('.fc-divider').find('.fc-cell-content').addClass('fc-expander');
                            },
                        }).open();

                    },
                    buttonIcons: {
                        prev: 'left-single-arrow',
                        next: 'right-single-arrow',
                        prevYear: 'left-double-arrow',
                        nextYear: 'right-double-arrow'
                    },
                    eventRender: function (eventObj, $el) {
                        //                      console.log("eventObj::::::::::::",eventObj)
                        // console.log("eventObj::::::::::::",eventObj)
                        $el.popover({
                            title: eventObj.title,
                            content:
                                "<table class='tooltip_table'><tr>"
                                + "<td >" + "Reservation No :" + "</td><td>" + eventObj.description + "</td></tr>"
                                + "<tr><td>" + "Checkin Date :" + "</td><td>" + (eventObj.checkin) + "</td></tr>"
                                + "<tr><td>" + "Checkout Date :" + "</td><td>" + (eventObj.checkout) + "</td></tr>"
                                + "<tr><td>" + "Customer :" + "</td><td>" + eventObj.partner_id[1] + "</td></tr>"
                                + "<tr><td>" + "Status :" + "</td><td>" + eventObj.state + "</td></tr>",
                            html: true,
                            trigger: 'hover',
                            placement: 'top',
                            container: 'body'
                        });
                        $el.css({
                            "font-weight": "bold",
                            'font-size': '12px',



                        });
                    },
                    events: room_data_event_list,
                    eventClick: function (calEvent, jsEvent, view) {
                        var res_info = self.get_reservation(calEvent.description);
                        var res = false
                        var folio_state = false
                        if (res_info == undefined) {
                            res = false
                        }
                        else {
                            res = res_info.id
                            var params = {
                                model: 'hotel.reservation',
                                method: 'get_folio_status',
                                args: [parseInt(res_info.id)],
                            }
                            rpc.query(params, {
                                async: false
                            }).then(function (res_state) {
                                if (res_state) {
                                    folio_state = res_state

                                }

                                var view_ids = self.get_view_id();
                                var eventObj = self.do_action({

                                    name: _t("Hotel Reservation"),
                                    res_model: 'hotel.reservation',
                                    views: [[view_ids, 'form']],
                                    res_id: res,
                                    view_mode: ['form'],
                                    type: 'ir.actions.act_window',
                                    target: "new",
                                    context: { 'state': res_state },
                                    /*on_saved: function(record, changed) {
                                             $('#booking_calendar').fullCalendar('destroy');
                                             self.hotel_dashboard_view(moment_date)
                                             $('.fc-divider').find('.fc-cell-content').addClass('fc-expander');
                                         },*/
                                });

                            });
                        }

                    },
                    eventResize: function (event, delta, revertFunc) {
                        //                    console.log("ffffffffffffffffff",event,event.start,event.end)
                        $('.popover').popover('hide')
                        $(this).popover('hide')
                        var params = {
                            model: 'hotel.reservation',
                            method: 'update_reservation_line',
                            args: [parseInt(event.id), event.description, moment(event.start).format("YYYY-MM-DD HH:mm:ss"), moment(event.end).format("YYYY-MM-DD HH:mm:ss"), event.resourceId, moment(event.start).format("YYYY-MM-DD"), moment(event.end).format("YYYY-MM-DD")],
                        }
                        rpc.query(params, {
                            async: false
                        }).then(function (res) { });
                        $('#booking_calendar').fullCalendar('destroy');
                        self.hotel_dashboard_view(moment_date)
                        $('.fc-divider').find('.fc-cell-content').addClass('fc-expander');

                    },
                    eventDrop: function (event, oldEvent, delta, reverse, view, el, jsEvent) {
                        $('.popover').popover('hide')
                        $(this).popover('hide')

                        rpc.query({
                            model: 'hotel.reservation',
                            method: 'update_room',
                            args: [event.id, event.description, parseInt(event.resourceId), moment(event.start).format('YYYY-MM-DD HH:mm:ss'), moment(event.end).format('YYYY-MM-DD HH:mm:ss'), id_id, moment(event.start).format('YYYY-MM-DD '), moment(event.start).format('YYYY-MM-DD')]
                        }, {
                            async: false
                        }).then(function (res) { });
                        if (res) { }
                        else { reverse() }
                        $('#booking_calendar').fullCalendar('destroy');
                        self.hotel_dashboard_view(moment_date)
                        $('.fc-divider').find('.fc-cell-content').addClass('fc-expander');

                    },
                    eventDragStart: function (event, jsEvent, view) {

                        id_id = false
                        id_id = event.resourceId
                    },
                });


            });

        },

        fetch: function (model, fields, domain, ctx) {
            var domain = domain;
            return this._rpc({
                model: model,
                method: 'search_read',
                domain: domain,
                fields: fields,
            })
        },

        get_reservation_line: function (line_id) {

            //		    console.log("innnnnnnnnnnnnnnnnnnnnnnnnnnnnn1")


            for (var rline = 0; rline < this.reservation_lines.length; rline++) {
                if (this.reservation_lines[rline].id == line_id) {
                    return this.reservation_lines[rline];
                }
            }

        },

        get_reservation: function (res_name) {
            //		    console.log("innnnnnnnnnnnnnnnnnnnnnnnnnnnnn2",res_name,this.reservations1)
            for (var rline = 0; rline < this.reservations1.length; rline++) {
                if (this.reservations1[rline].reservation_no == res_name) {
                    return this.reservations1[rline];
                }
            }

        },
        get_view_id: function () {
            return this.view_ids[0].id;

        },

        get_dirty_room: function (compare_date, product_id) {

            for (var hline = 0; hline < this.housekeeping_lines.length; hline++) {
                //			    console.log("product_id::::::::::::::::",this.housekeeping_lines[hline].room_no[0],product_id)
                if (this.housekeeping_lines[hline].room_no[0] == product_id) {
                    //				    console.log("qqqqqqqqqqqqq",this.housekeeping_lines[hline].current_date,compare_date)
                    if ((this.housekeeping_lines[hline].current_date <= compare_date) && (compare_date <= this.housekeeping_lines[hline].end_date)) {
                        return true;
                    } else {
                        return false;
                    }
                }
            }
        },

        load_data: function () {
            var self = this;
            var loaded = self.fetch('hotel.reservation.line', ['id', 'room_number', 'categ_id', 'checkin', 'checkout', 'number_of_days'], ['&', ['line_id', '!=', false], ['checkin', '<=', $("#to_date").val()]], {}).then(function (res_lines) {
                self.reservation_lines = res_lines;
                return self.fetch('hotel.reservation', ['id', 'reservation_no', 'reservation_line', 'state', 'id_line_ids', 'partner_id', 'folio_id'], [['state', 'not in', ['cancel']]], {});
            }).then(function (reservation) {
                self.reservations = reservation;
                return self.fetch('hotel.resv.id.details', ['id', 'name', 'partner_name', 'gender', 'country_id', 'date_birth', 'client_id'], [], [], {});
            }).then(function (guest_details) {
                self.guest_details = guest_details;
                return self.fetch('hotel.housekeeping', ['id', 'current_date', 'end_date', 'room_no', 'state', 'quality'], [['state', 'in', ['dirty']], ['current_date', '>=', $("#from_date").val()]], {});
            }).then(function (housekeeping_details) {
                self.housekeeping_lines = housekeeping_details;
                return self.fetch('product.product', ['id', 'product_tmpl_id'], [], [], {});
            }).then(function (productlines) {
                self.product_lines = productlines;
                return self.fetch('ir.ui.view', ['id', 'name', 'model', 'type'], [['name', '=', 'hotel.reservation.form1'], ['model', '=', 'hotel.reservation'], ['type', '=', 'form']], {});
            }).then(function (views) {
                self.view_ids = views;
            });



            return loaded;
        },


        load_hotel: function () {
            var self = this;
            var dddd = self.fetch('hotel.room', ['id', 'name', 'categ_id', 'room_folio_ids', 'product_id'], [], {}).then(function (shop) {
                self.hotel_room = shop;
            });

            var reservation = self.fetch('hotel.reservation.line', ['id', 'room_number', 'categ_id', 'checkin', 'checkout', 'number_of_days', 'line_id'], ['&', ['line_id', '!=', false], ['company_id', '=', session.company_id]], {}).then(function (res_lines) {
                self.reservation_lines1 = res_lines;
                return self.fetch('hotel.reservation', ['id', 'reservation_no', 'reservation_line', 'state', 'id_line_ids', 'partner_id', 'total_cost1', 'deposit_cost2'], [['state', 'not in', ['cancel']]], {});
            }).then(function (reservation) {
                self.reservations1 = reservation;
                return self.fetch('ir.ui.view', ['id', 'name', 'model', 'type'], [['name', '=', 'hotel.reservation.form1'], ['model', '=', 'hotel.reservation'], ['type', '=', 'form']], {});
            }).then(function (views) {
                self.view_ids = views;
                return self.fetch('hotel.housekeeping', ['id', 'current_date', 'end_date', 'room_no', 'state', 'quality'], [['state', 'in', ['dirty']],], {});
            }).then(function (housekeeping_details) {
                self.housekeeping_lines = housekeeping_details;

                return self.fetch('hotel.folio', ['id', 'reservation_id', 'remaining_amt', 'state'], [], {});
            }).then(function (folio_id) {
                self.folio_id = folio_id;


            });



            return dddd, reservation;
        },

    });
    core.action_registry.add('HotelDashboardView_temp', HotelDashboardView);

    return {
        HotelDashboardView: HotelDashboardView,
    };
});
