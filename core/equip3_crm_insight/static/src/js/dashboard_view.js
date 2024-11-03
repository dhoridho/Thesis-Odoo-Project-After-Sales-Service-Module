odoo.define('equip3_crm_insight.CRMDashboard', function (require) {
    'use strict';
    var AbstractAction = require('web.AbstractAction');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var web_client = require('web.web_client');
    var session = require('web.session');
    var _t = core._t;
    var QWeb = core.qweb;
    var self = this;
    var currency;
    var DashBoard = AbstractAction.extend({
        contentTemplate: 'CRMdashboard',
        events: {
            'click .exp_revenue_this_month': 'exp_revenue_this_month',
            'click .exp_revenue_this_quarter': 'exp_revenue_this_quarter',
            'click .revenue_card': 'revenue_card',
        },

        init: function(parent, context) {
            this._super(parent, context);
            this.upcoming_events = [];
            this.dashboards_templates = ['LoginUser','Managercrm'];
            this.login_user = [];
        },

        willStart: function(){
            var self = this;
            this.login_user = {};
            return this._super()
            .then(function() {

                var def0 =  self._rpc({
                    model: 'crm.lead',
                    method: 'check_user_group'
                }).then(function(result) {
                    if (result == true){
                        self.is_manager = true;
                    }
                    else{
                        self.is_manager = false;
                    }
                });

                var def1 = self._rpc({
                    model: "crm.lead",
                    method: "get_monthly_goal",
                })
                .then(function (res) {
                    self.monthly_goals = res['goals'];
                });

                var def2 = self._rpc({
                    model: "crm.lead",
                    method: "count_generate_account",
                })
                .then(function (res) {
                    self.generate_account = res['generate_accounts'];
                });

                var def3 = self._rpc({
                    model: "crm.lead",
                    method: "count_won_revenue",
                })
                .then(function (res) {
                    self.won_revenue = res['won_revenue'];
                });

                var def4 = self._rpc({
                    model: "crm.lead",
                    method: "count_opportunities",
                })
                .then(function (res) {
                    self.opportunity = res['opportunity'];
                });

                var def5 = self._rpc({
                    model: "crm.lead",
                    method: "get_trending_data",
                })
                .then(function (res) {
                    self.trending = res['trendings'];
                });

                return $.when(def0, def1, def2, def3, def4, def5);
            });
        },

        //exp_revenue_this_month
        exp_revenue_this_month: function(e) {
            var self = this;
            e.stopPropagation();
            e.preventDefault();
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.do_action({
                name: _t("Total Closing This Month"),
                type: 'ir.actions.act_window',
                res_model: 'crm.lead',
                view_mode: 'tree,form,calendar',
                views: [[false, 'list'],[false, 'form']],
                domain: [['stage_id','=', 4]],
                target: 'current',
            }, options)
        },

        //exp_revenue_this_quarter
        exp_revenue_this_quarter: function(e) {
            var self = this;
            e.stopPropagation();
            e.preventDefault();
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.do_action({
                name: _t("Expected Revenue"),
                type: 'ir.actions.act_window',
                res_model: 'crm.lead',
                view_mode: 'tree,form,calendar',
                views: [[false, 'list'],[false, 'form']],
                domain: [['stage_id','=', 4]],
                target: 'current',
            }, options)
        },

        //revenue
        revenue_card: function(e) {
            var self = this;
            e.stopPropagation();
            e.preventDefault();
            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };
            this.do_action({
                name: _t("Revenue"),
                type: 'ir.actions.act_window',
                res_model: 'crm.lead',
                view_mode: 'tree,form,calendar',
                views: [[false, 'list'],[false, 'form']],
                domain: [['user_id','=', session.uid], ['type','=', 'opportunity'], ['stage_id.is_won','=', True]],
                target: 'current',
            }, options)
        },

        start: function() {
            var self = this;
            this.set("title", 'Dashboard');
            return this._super().then(function() {
                self.update_cp();
                self.render_dashboards();
                self.render_graphs();
                self.$el.parent().addClass('oe_background_grey');
            });
        },

        render_graphs: function(){
            var self = this;
            self.render_revenue_graph();
            self.render_lost_graph();
            self.render_top_source_graph();
            self.render_top_team_graph();
        },

        render_revenue_graph:function(){
           var self = this
           var ctx = self.$(".revenue_lead_type");
                rpc.query({
                    model: "crm.lead",
                    method: "get_lead_type_data",
                }).then(function (arrays) {
                  var backgroundColor = arrays[2].value === 'This Quarter' ? '#b3627e' : '#4536e2';
                  var labels = arrays[2].value === 'This Quarter' ? 'Last Quarter' : 'This Quarter';
                  var data = {
                    labels: arrays[1],
                    datasets: [
                      {
                        label: labels,
                        data: arrays[0],
                        backgroundColor: backgroundColor,
                        borderWidth: 1
                      },
                    ]
                  };

          //options
                  var options = {
                    responsive: true,
                    title: {
                      display: true,
                      position: "top",
                      text: "Revenue per Lead Type",
                      align: "left"
//                      fontSize: 18,
//                      fontColor: "#111"
                    },
                    legend: {
                      display: true,
                      position: "top",
//                      labels: {
//                        fontColor: "#333",
//                        fontSize: 16
//                      }
                    },
                    scales: {
                      yAxes: [{
                        categoryPercentage: 0.8,
                        barPercentage: 0.9,
                        ticks: {
                          min: 0
                        }
                      }]
                    }
                  };

                  //create Chart class object
                  var chart = new Chart(ctx, {
                    type: "horizontalBar",
                    data: data,
                    options: options
                  });
            });
        },

        render_lost_graph:function(){
           var self = this
           var ctx = self.$(".lost_reason_graph");
                rpc.query({
                    model: "crm.lead",
                    method: "get_lost_data",
                }).then(function (arrays) {
                  var backgroundColor = arrays[2].value === 'This Quarter' ? '#b3627e' : '#87CEFA';
                  var labels = arrays[2].value === 'This Quarter' ? 'Last Quarter' : 'This Quarter';
                  var data = {
                    labels: arrays[1],
                    datasets: [
                      {
                        label: labels,
                        data: arrays[0],
                        backgroundColor: backgroundColor,
                        borderWidth: 1
                      },
                    ]
                  };

          //options
                  var options = {
                    responsive: true,
                    title: {
                      display: true,
                      position: "top",
                      text: "Most Reason of Lost Lead",
                      align: "left"
//                      fontSize: 18,
//                      fontColor: "#111"
                    },
                    legend: {
                      display: true,
                      position: "top",
//                      labels: {
//                        fontColor: "#333",
//                        fontSize: 16
//                      }
                    },
                    scales: {
                      yAxes: [{
                        categoryPercentage: 0.6,
                        barPercentage: 0.7,
                        ticks: {
                          min: 0
                        }
                      }]
                    }
                  };

                  //create Chart class object
                  var chart = new Chart(ctx, {
                    type: "horizontalBar",
                    data: data,
                    options: options
                  });
            });
        },

        render_top_source_graph:function(){
            rpc.query({
                model: "crm.lead",
                method: "get_top_source_data",
            }).then(function (callbacks) {
                var backgroundColor = ["#00348d", "#0349c0", "#0058ec", "#3175ed", "#5090ff"];
                Highcharts.chart("top_source", {
                    chart: {
                        type: "funnel",
                    },
                    title: {
                        text: "Top Sources of This Month",
                        align: "left"
                    },
                    credits: {
                        enabled: false
                    },
                    plotOptions: {
                        series: {
                            dataLabels: {
                                enabled: true,
                                format: '<b>{point.name}</b> ({point.y:,.0f})',
                                softConnector: true
                            },
                            center: ['40%', '50%'],
                            colors: backgroundColor,
                            neckWidth: '30%',
                            neckHeight: '0%',
                            width: '80%',
                            height: '90%'
                        }
                    },
                    legend: {
                        enabled: false
                    },
                    series: [{
                        name: "Expected Revenue",
                        data: callbacks,
                    }],
                    responsive: {
                        rules: [{
                            condition: {
                                maxWidth: 500
                            },
                            chartOptions: {
                                plotOptions: {
                                    series: {
                                        dataLabels: {
                                            inside: true
                                        },
                                        center: ['50%', '50%'],
                                        width: '100%'
                                    }
                                }
                            }
                        }]
                    }
                });
            });
        },

        render_top_team_graph:function(){
            rpc.query({
                model: "crm.lead",
                method: "get_top_team_data",
            }).then(function (callbacks) {
                Highcharts.chart("top_team", {
                    chart: {
                        type: 'line'
                    },
                    title: {
                        text: "Best Team of This Month",
                        align: "left"
                    },
                    yAxis: {
                        title: false,
                    },
                    xAxis: {
                        categories: callbacks[0]
                    },
                    legend: false,
                    plotOptions: {
                        line: {
                            dataLabels: {
                                enabled: true
                            },
                            enableMouseTracking: false
                        }
                    },
                    series: [{
                        name: 'Expected Revenue',
                        data: callbacks[1]
                    }],
                    responsive: {
                        rules: [{
                            condition: {
                                maxWidth: 500
                            },
                            chartOptions: {
                                legend: {
                                    layout: 'horizontal',
                                    align: 'center',
                                    verticalAlign: 'bottom'
                                }
                            }
                        }]
                    }
                });
            });
        },

        fetch_data: function() {
            var self = this;

            var def0 =  self._rpc({
                model: 'crm.lead',
                method: 'check_user_group'
            }).then(function(result) {
                if (result == true){
                    self.is_manager = true;
                }
                else{
                    self.is_manager = false;
                }
            });

            var def1 = self._rpc({
                model: "crm.lead",
                method: "get_monthly_goal",
            })
            .then(function (res) {
                self.monthly_goals = res['goals'];
            });

            var def2 = self._rpc({
                model: "crm.lead",
                method: "count_generate_account",
            })
            .then(function (res) {
                self.generate_account = res['generate_accounts'];
            });

            var def3 = self._rpc({
                model: "crm.lead",
                method: "count_won_revenue",
            })
            .then(function (res) {
                self.won_revenue = res['won_revenue'];
            });

            var def4 = self._rpc({
                model: "crm.lead",
                method: "count_opportunities",
            })
            .then(function (res) {
                self.opportunity = res['opportunity'];
            });

            var def5 = self._rpc({
                model: "crm.lead",
                method: "get_trending_data",
            })
            .then(function (res) {
                self.trending = res['trendings'];
            });

            return $.when(def0, def1, def2, def3, def4, def5);
        },

        render_dashboards: function() {
            var self = this;
            if (this.login_user){
                var templates = []
                if( self.is_manager == true){
                    templates = ['LoginUser', 'Managercrm'];
                }
                else{
                    templates = ['LoginUser','Managercrm'];
                }
                _.each(templates, function(template) {
                    self.$('.o_crm_insight').append(QWeb.render(template, {widget: self}));
                });
            }
            else{
                self.$('.o_crm_insight').append(QWeb.render('UserWarning', {widget: self}));
            }
        },

        on_reverse_breadcrumb: function() {
            var self = this;
            web_client.do_push_state({});
            this.update_cp();
            this.fetch_data().then(function() {
                self.$('.o_crm_insight').reload();
                self.render_dashboards();
            });
        },

         update_cp: function() {
            var self = this;
         },
    });

    core.action_registry.add('equip3_crm_insight_tag', DashBoard);
    return DashBoard;
});