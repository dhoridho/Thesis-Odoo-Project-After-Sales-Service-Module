odoo.define('website_booking_axis.MyCustomAction',  function (require) {
"use strict";
var AbstractAction = require('web.AbstractAction');
var core = require('web.core');
var rpc = require('web.rpc');
var ActionManager = require('web.ActionManager');
var view_registry = require('web.view_registry');
var Widget = require('web.Widget');
var ajax = require('web.ajax');
var session = require('web.session');
var web_client = require('web.web_client');
var _t = core._t;
var QWeb = core.qweb;

var MyCustomAction = AbstractAction.extend({
    template: 'AppointmentDashboardView',
    cssLibs: [
        '/website_booking_axis/static/src/scss/lib/nv.d3.css'
    ],
    jsLibs: [
        '/website_booking_axis/static/src/js/lib/d3.min.js',
        '/website_booking_axis/static/src/js/Chart.js',
       
    ],
    events: {
        'click .more-service': 'action_appointment_group',
        'click .more-appointment': 'action_view_calendar_event_calendar',
        'click .more-pending-appointment': 'action_pending_appointment',
        'click .more-approved-appointment':'action_approved_appointment',
        'click .more-rejected-appointment': 'action_rejected_appointment',
        'click .more-today-appointment': 'action_today_appointment',
       
    },

    
    init: function(parent, context) {
        this._super(parent, context);
        var employee_data = [];
        var self = this;
    
  
    
    },



    willStart: function() {
        var self = this;
            return self.fetch_data();
    },


    start: function() {
    	
        var self = this;
      
        self.get_top_sold_order();
        self.get_sale_order_cancel();
        self.get_order();
        self.get_customer_count();
        self.render_dashboards();
        self.render_graphs();
        return this._super();
        
    },

    fetch_data: function() {
        
        var self = this;
        var abcd = self._rpc({
                model: 'sale.order',
                method: 'get_value',
            }, []).then(function(result){
                self.employee_data = result; 
            })
        
        return abcd

    },

    on_attach_callback: function () {
        var self = this;
        return self.fetch_data();
    },

    on_detach_callback: function () {
        var self = this;
        return self.fetch_data();
    },

    render_dashboards: function(value) {
        var self = this;     
        var appointment_dashboard = QWeb.render('AppointmentDashboardView', {
            widget: self,
        });

        rpc.query({
                model: 'appointment.group',
                method: 'get_count_list',
                args: []
            })
            .then(function (result){
                    self.$el.find('.total-service').text(result['total_service'])
                    self.$el.find('.total-appointment').text(result['total_appointment'])
                    self.$el.find('.pending-appointment').text(result['pending_appointment'])
                    self.$el.find('.approved-appointment').text(result['approved_appointment'])
                    self.$el.find('.rejected-appointment').text(result['rejected_appointment'])
                    self.$el.find('.today-appointment').text(result['today_appointment'])
                    self.$el.find('.table').text(result['sale_tables'])                  
            });
        
        return appointment_dashboard
    },

    action_appointment_group:function(event){
        var self = this;
        event.stopPropagation();
        event.preventDefault();
        this.do_action({
            name: _t("Appointment Group"),
            type: 'ir.actions.act_window',
            res_model: 'appointment.group',
            view_mode: 'tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            // context: {                        
            //             'search_default_all_quotation':true,                   
            //         },
            target: 'current'
        },)


    },

    
    action_view_calendar_event_calendar:function(event){
        var self = this;
        event.stopPropagation();
        event.preventDefault();
        this.do_action({
            name: _t("Meetings"),
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'tree',
            views: [[false, 'list'],[false, 'calendar'],[false, 'form']],
            target: 'current'
        },)


    },

     action_pending_appointment:function(event){
        var self = this;
        event.stopPropagation();
        event.preventDefault();
        this.do_action({
            name: _t("Meetings"),
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'calendar',
            views: [[false, 'calendar'],[false, 'list'],[false, 'form']],
            views: [[false, 'list'],[false, 'form']],
            context: {                        
                        'search_default_pending_appointment':true,                   
                    },
            domain: [['attendee_ids.state','in',['needsAction']]],
            target: 'current'
        },)


    },

    action_approved_appointment:function(event){
        var self = this;
        event.stopPropagation();
        event.preventDefault();
        this.do_action({
            name: _t("Meetings"),
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'calendar'],[false, 'list'],[false, 'form']],
            views: [[false, 'list'],[false, 'form']],
            context: {                        
                        'search_default_approved_appointment':true,                   
                    },
            domain: [['attendee_ids.state','in',['accepted']]],
            target: 'current'
        },)


    },

    action_rejected_appointment:function(event){
        var self = this;
        event.stopPropagation();
        event.preventDefault();
        this.do_action({
            name: _t("Meetings"),
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'calendar'],[false, 'list'],[false, 'form']],
            views: [[false, 'list'],[false, 'form']],
            context: {                        
                        'search_default_rejected_appointment':true,                   
                    },
            domain: [['attendee_ids.state','in',['declined']]],
            target: 'current'
        },)


    },
    
     action_today_appointment:function(event){
        var self = this;
        var timeElapsed = Date.now();
        var today = new Date(timeElapsed)
        today.toLocaleDateString();
        // var today = new Date();
        // var dd = String(today.getDate()).padStart(2, '0');
        // var mm = String(today.getMonth() + 1).padStart(2, '0'); //January is 0!
        // var yyyy = today.getFullYear();

        // today = mm + '/' + dd + '/' + yyyy;
        event.stopPropagation();
        event.preventDefault();
        this.do_action({
            name: _t("Meetings"),
            type: 'ir.actions.act_window',
            res_model: 'calendar.event',
            view_mode: 'calendar,tree,form',
            view_type: 'list',
            views: [[false, 'calendar'],[false, 'list'],[false, 'form']],
            views: [[false, 'list'],[false, 'form']],
            context: {                        
                        'search_default_today_appointment':true,                   
                    },
            domain: [['start_at','=',today]],
            target: 'current'
        },)


    },

    action_to_be_invoiced:function(event){
        var self = this;
        event.stopPropagation();
        event.preventDefault();
        this.do_action({
            name: _t("To be Invoiced"),
            type: 'ir.actions.act_window',
            res_model: 'sale.order',
            view_mode: 'kanban,tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['state','in',['invoiced']]],
            target: 'current'
        },)


    },

    action_fully_invoiced:function(event){
        var self = this;
        event.stopPropagation();
        event.preventDefault();
        this.do_action({
            name: _t("Fully  Invoiced"),
            type: 'ir.actions.act_window',
            res_model: 'account.move',
            view_mode: 'kanban,tree,form',
            view_type: 'form',
            views: [[false, 'list'],[false, 'form']],
            domain: [['state','in',['no']]],
            target: 'current'
        },)


    },

    get_top_sold_order : function(value){
            var self = this;

            rpc.query({
                model: 'sale.order',
                method: 'get_sale_table',
                args : []
            }, {async: false}).then(function (result) {
                if(result){
                    var contents = self.$el.find('.top-sold');
                    contents.empty();
                    var res = result['sale_tables']
                    var dataSet = []
                    for(var i=0;i<res.length;i++){
                        dataSet.push([res[i].order_reference, res[i].partner_name,res[i].amount,res[i].date_order,'<span class="label label-success">' + '</span>'])
                    }
                    if(dataSet.length > 0){
                        $('.top-sold').DataTable( {
                            lengthChange : false,
                            info: false,
                            "destroy": true,
                            "responsive": false,
                            pagingType: 'simple',
                            "pageLength": 10,
                            language: {
                                paginate: {
                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                                }
                            },
                            searching: false,
                            data: dataSet,
                            columns: [
                                { title: "Order Reference" },
                                { title: "Customer Name" },
                                { title: "Total" },
                                { title: "Creation Order" }
                            ]
                        });
                    }
                }
            });
        },

    get_sale_order_cancel : function(value){
            var self = this;

            rpc.query({
                model: 'sale.order',
                method: 'get_sale_table',
                args : []
            }, {async: false}).then(function (result) {
                if(result){
                    var contents = self.$el.find('.sale-cancel');
                    contents.empty();
                    var res = result['sale_cancel']
                    var dataSet = []
                    for(var i=0;i<res.length;i++){
                        dataSet.push([res[i].order_reference, res[i].partner_name,res[i].date_order,'<span class="label label-success">' + '</span>'])
                    }
                    if(dataSet.length > 0){
                        $('.sale-cancel').DataTable( {
                            lengthChange : false,
                            info: false,
                            "destroy": true,
                            "responsive": false,
                            pagingType: 'simple',
                            "pageLength": 4,
                            language: {
                                paginate: {
                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                                }
                            },
                            searching: false,
                            data: dataSet,
                            columns: [
                                { title: "Order Reference" },
                                { title: "Customer Name" },
                                { title: "Creation Order" }
                            ]
                        });
                    }
                }
            });
        },


    get_customer_count : function(value){
            var self = this;

            rpc.query({
                model: 'sale.order',
                method: 'get_sale_table',
                args : []
            }, {async: false}).then(function (result) {
                if(result){
                    var contents = self.$el.find('.customer');
                    contents.empty();
                    var res = result['count_customer']
                    var dataSet = []
                    for(var i=0;i<res.length;i++){
                        dataSet.push([res[i].customer_name,'<span class="label label-success">' + '</span>'])
                    }
                    if(dataSet.length > 0){
                        $('.customer').DataTable( {
                            lengthChange : false,
                            info: false,
                            "destroy": true,
                            "responsive": false,
                            pagingType: 'simple',
                            "pageLength": 10,
                            language: {
                                paginate: {
                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                                }
                            },
                            searching: false,
                            data: dataSet,
                            columns: [
                                { title: "Customer Name" },
        
                            ]
                        });
                    }
                }
            });
        },

    get_order : function(value){
            var self = this;

            rpc.query({
                model: 'sale.order',
                method: 'get_sale_table',
                args : []
            }, {async: false}).then(function (result) {
                if(result){
                    var contents = self.$el.find('.sale');
                    contents.empty();
                    var res = result['order']
                    var dataSet = []
                    for(var i=0;i<res.length;i++){
                        dataSet.push([res[i].order_reference, res[i].partner_name,res[i].date_order,res[i].delievery_date,'<span class="label label-success">' + '</span>'])
                    }
                    if(dataSet.length > 0){
                        $('.sale').DataTable( {
                            lengthChange : false,
                            info: false,
                            "destroy": true,
                            "responsive": false,
                            pagingType: 'simple',
                            "pageLength": 4,
                            language: {
                                paginate: {
                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                                }
                            },
                            searching: false,
                            data: dataSet,
                            columns: [
                                { title: "Order Reference" },
                                { title: "Customer Name" },
                                { title: "Creation Order" },
                                { title: "Delivery Date" }
                            ]
                        });
                    }
                }
            });
        },

    getRandomColor: function () {
        var letters = '0123456789ABCDEF'.split('');
        var color = '#';
        for (var i = 0; i < 6; i++ ) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    },

    render_graphs: function(){
        var self = this;
        self.graph_max_price();
        self.monthlyappointment();
    },

    // Here we are plotting bar,pie chart

    graph_max_price: function() {
        var self = this;
        var ctx = this.$el.find('#highprice')
        Chart.plugins.register({
          beforeDraw: function(chartInstance) {
            var ctx = chartInstance.chart.ctx;
            ctx.fillStyle = "white";
            ctx.fillRect(0, 0, chartInstance.chart.width, chartInstance.chart.height);
          }
        });
        var bg_color_list = []
        for (var i=0;i<=12;i++){
            bg_color_list.push(self.getRandomColor())
        }
        rpc.query({
                model: 'calendar.event',
                method: 'get_value_price',
                
            })
            .then(function (result) {
                var data = result.data;
                var day = ["Monday", "Tuesday", "Wednesday", "Thursday", 
                         "Friday", "Saturday", "Sunday"]
                var week_data = [];
                if (data){
                    for(var i = 0; i < day.length; i++){
                        day[i] == data[day[i]]
                        var day_data = day[i];
                        var day_count = data[day[i]];
                        if(!day_count){
                                day_count = 0;
                        }
                        week_data[i] = day_count

                    }
                }
                              
                

                var myChart = new Chart(ctx, {
                type: 'bar',
                data: {
                   
                    labels: day ,
                    datasets: [{
                        label: ' Appointees',
                        data: week_data,
                        backgroundColor: bg_color_list,
                        borderColor: bg_color_list,
                        borderWidth: 1,
                        pointBorderColor: 'white',
                        pointBackgroundColor: 'red',
                        pointRadius: 5,
                        pointHoverRadius: 10,
                        pointHitRadius: 30,
                        pointBorderWidth: 2,
                        pointStyle: 'rectRounded'
                    }]
                },
                options: {
                    scales: {
                        yAxes: [{
                            ticks: {
                                min: 0,
                                max: Math.max.apply(null,week_data),
                              }
                        }]
                    },
                    responsive: true,
                    maintainAspectRatio: true,
                    leged: {
                        display: true,
                        labels: {
                            fontColor: 'black'
                        }
                },
            },
        });

            });

    
    },

    monthlyappointment: function() {
        var self = this;
        var ctx = this.$el.find('#monthlyappointment')
        Chart.plugins.register({
          beforeDraw: function(chartInstance) {
            var ctx = chartInstance.chart.ctx;
            ctx.fillStyle = "white";
            ctx.fillRect(0, 0, chartInstance.chart.width, chartInstance.chart.height);
          }
        });
        var bg_color_list = []
        for (var i=0;i<=12;i++){
            bg_color_list.push(self.getRandomColor())
        }
        rpc.query({
                model: 'calendar.event',
                method: 'get_monthly_appointments',
            })
            .then(function (result) {
                var data = result.data
                var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                                'August', 'September', 'October', 'November', 'December']
                var month_data = [];

                if (data){
                    for(var i = 0; i < months.length; i++){
                        months[i] == data[months[i]]
                        var day_data = months[i];
                        var month_count = data[months[i]];
                        if(!month_count){
                                month_count = 0;
                        }
                        month_data[i] = month_count

                    }
                }
                var myChart = new Chart(ctx, {
                type: 'bar',
                data: {
                   
                    labels: months,
                    datasets: [{
                        label: ' Appointees',
                        data: month_data,
                        backgroundColor: bg_color_list,
                        borderColor: bg_color_list,
                        borderWidth: 1,
                        pointBorderColor: 'white',
                        pointBackgroundColor: 'red',
                        pointRadius: 1,
                        pointHoverRadius: 10,
                        pointHitRadius: 30,
                        pointBorderWidth: 1,
                        pointStyle: 'rectRounded'
                    }]
                },
                options: {
                    scales: {
                        yAxes: [{
                            ticks: {
                                min: 0,
                                max: Math.max.apply(null,month_data),
                                //min: 1000,
                                //max: 100000,
                                // stepSize: result.
                                // mycount.reduce((pv,cv)=>{return pv + (parseFloat(cv)||0)},0)
                                // /result.mycount.length
                              }
                        }]
                    },
                    responsive: true,
                    maintainAspectRatio: true,
                    leged: {
                        display: true,
                        labels: {
                            fontColor: 'black'
                        }
                },
            },
        });

            });

    
    },
           
});


core.action_registry.add("appointment_dashboard", MyCustomAction);
return MyCustomAction
});