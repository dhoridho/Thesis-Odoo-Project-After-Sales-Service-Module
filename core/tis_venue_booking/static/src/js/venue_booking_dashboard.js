odoo.define('tis_venue_booking.dashboard', function (require) {
'use strict';

var core = require('web.core');
var framework = require('web.framework');
var session = require('web.session');
var ajax = require('web.ajax');
var ActionManager = require('web.ActionManager');
var view_registry = require('web.view_registry');
var Widget = require('web.Widget');
var AbstractAction = require('web.AbstractAction');
//var ControlPanelMixin = require('web.ControlPanelMixin');
var QWeb = core.qweb;

var _t = core._t;
var _lt = core._lt;

var Dashboard = AbstractAction.extend({
    hasControlPanel: true,
	init: function(parent, context) {
        this._super(parent, context);
        var booking_data = [];
        var self = this;
        if (context.tag == 'venue_booking_dashboard') {
            self._rpc({
                model: 'booking.dashboard',
                method: 'get_booking_info',
            }, []).then(function(result){
                self.booking_data = result
            }).then(function(){
                self.render();
                self.href = window.location.href;
            });
        }
    },
    willStart: function() {
         return $.when(ajax.loadLibs(this), this._super());
    },
    start: function() {
        var self = this;
        return this._super();
    },
    render: function() {
        var super_render = this._super;
        var self = this;
        var venue_booking_dashboard = QWeb.render( 'BookingDashboardMain', {
            widget: self,
        });
        $( ".o_control_panel" ).addClass( "o_hidden" );
        $(venue_booking_dashboard).prependTo(self.$el);
        self.graph();
        return venue_booking_dashboard
    },
    reload: function () {
            window.location.href = this.href;
    },

//     Function which gives random color for charts.
    getRandomColor: function () {
        var letters = '0123456789ABCDEF'.split('');
        var color = '#';
        for (var i = 0; i < 6; i++ ) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    },

    graph: function() {
        var self = this
        Chart.defaults.global.defaultFontColor = 'black';
        var ctx = this.$el.find('#barChartDemo')
//         Fills the canvas with white background
        Chart.plugins.register({
          beforeDraw: function(chartInstance) {
            var ctx = chartInstance.chart.ctx;
            ctx.fillStyle = "transparent";
            ctx.fillRect(0, 0, chartInstance.chart.width, chartInstance.chart.height);
          }
        });
        var bg_color_list = []
        for (var i=0;i<=11;i++){
            bg_color_list.push(self.getRandomColor())
        }
        var bookingChart = new Chart(ctx, {
            type: 'bar',
            data: {

                datasets: [{
                    label: 'Amount By Month',
                    data: self.booking_data[14],
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
                }],
                     	labels: self.booking_data[13],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                animation: {
                    duration: 100, // general animation time
                },
                hover: {
                    animationDuration: 500, // duration of animations when hovering an item
                },
                responsiveAnimationDuration: 500, // animation duration after a resize
                legend: {
                    display: true,
                    labels: {
                        fontColor: 'black'
                    }
                },
            },
        });
// Line chart for booking
        var linectx = this.$el.find('#lineChartDemo')
        var bg_color_list = []
        for (var i=0;i<=self.booking_data[16];i++){
            bg_color_list.push(self.getRandomColor())
        }
        var bookingChart = new Chart(linectx, {
            type: 'line',
            data: {
               	labels: self.booking_data[15],
                datasets: [{
                    label: "Amount by Date",
                  	data: self.booking_data[16],

                    backgroundColor: "blue",
                    borderColor: "lightblue",
                    fill: false,
                    lineTension: 0,
                    radius: 5}]
                    },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                animation: {
                    duration: 100, // general animation time
                },
                hover: {
                    animationDuration: 500, // duration of animations when hovering an item
                },
                responsiveAnimationDuration: 500, // animation duration after a resize
                legend: {
                    display: true,
                    labels: {
                        fontColor: 'black'
                    }
                },
            },
        });
//      Pie Chart for top 5 customers
        var piectx = this.$el.find('#pieChartDemo');
        var bg_color_list = []
        for (var i=0;i<=self.booking_data[8].length;i++){
            bg_color_list.push(self.getRandomColor())
        }
//        piectx.fillText('20000' + "%", 20/2 - 20, 20/2, 200);
        var pieChart = new Chart(piectx, {
            type: 'pie',
            data: {
                datasets: [{
                    data: self.booking_data[8],
                    backgroundColor: bg_color_list,
                    label: 'Top 5 Customers of '
                }],
                labels: self.booking_data[7],
            },
            options: {
                responsive: true,
                legend: {
                        display: true,
                        labels: {
                            fontColor: 'white'
                        }
                },
            }
        });
//        Pie Top 5 Booked Venues of current year
        var piectx1 = this.$el.find('#pieChartDemo1');
        var bg_color_list = []
        for (var i=0;i<=self.booking_data[10].length;i++){
            bg_color_list.push(self.getRandomColor())
        }
//        piectx.fillText('20000' + "%", 20/2 - 20, 20/2, 200);
        var pieChart = new Chart(piectx1, {
            type: 'pie',
            data: {
                datasets: [{
                    data: self.booking_data[10],
                    backgroundColor: bg_color_list,
                    label: 'Top 5 Customers of '
                }],
                labels:self.booking_data[9],
            },
            options: {
                responsive: true,
                legend: {
                        display: true,
                        labels: {
                            fontColor: 'white'
                        }
                },
            }
        });
        //        Pie Top 5 Booked Venues of current month
      var piectx1 = this.$el.find('#pieChartDemo2');
        var bg_color_list = []
        for (var i=0;i<=self.booking_data[12].length;i++){
            bg_color_list.push(self.getRandomColor())
        }
//        piectx.fillText('20000' + "%", 20/2 - 20, 20/2, 200);
        var pieChart = new Chart(piectx1, {
            type: 'pie',
            data: {
                datasets: [{
                    data: self.booking_data[12],
                    backgroundColor: bg_color_list,
                    label: 'Top 5 Customers of '
                }],
                labels:self.booking_data[11],
            },
            options: {
                responsive: true,
                legend: {
                        display: true,
                        labels: {
                            fontColor: 'white'
                        }
                },
            }
        });
    },
});
core.action_registry.add('venue_booking_dashboard', Dashboard);
return Dashboard
});


