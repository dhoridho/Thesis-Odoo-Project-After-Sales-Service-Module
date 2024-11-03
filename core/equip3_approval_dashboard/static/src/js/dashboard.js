odoo.define('equip3_approval_dashboard.approval_dashboard_board_js', function (require) {
    "use strict";


    var AbstractAction = require('web.AbstractAction');
    // var ControlPanelMixin = require('web.ControlPanelMixin');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;
    var session = require('web.session');
    var QWeb = core.qweb;
        
    var approval_dashboard = AbstractAction.extend({
        title: core._t('Approval Dashboard'),
        template: 'equip3_approval_dashboard.approval_dashboard',
        dashboard_widgets: {},
        events: {
            'click .approval_table_tr': 'click_approval_table_tr',
            'change .approval_modul_name': 'change_approval_modul_name',
            'change .req_approval_modul_name': 'change_req_approval_modul_name',
        },

        // init(parent, action, options = {}) {
        //     this._super(...arguments);
        //     // dashboard params
        //     this.current_year = moment().year();
        //     this.group_by = this.default_group_by;
        //     // control panel attributes
        //     this.action = action;
        //     this.actionManager = parent;
        //     this.searchModelConfig.modelName = 'purchase.order';
        //     this.options = options;
        // },

        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.approval_modul_name = ''
            this.req_approval_modul_name = ''
        },

        start: function () {
            const self = this;
            // this._computeControlPanelProps();
            this.approval_modul_name = ''
            this.req_approval_modul_name = ''
            return this._super().then(function () {
                self.render_dashboard_widgets();
            });
        },

        willStart: function () {
            return $.when(
                this._super.apply(this, arguments),
                this.fetch_data(),
            );
        },

        fetch_data: function () {
            const self = this;
            return this._rpc({
                route: '/approval_dashboard/fetch_dashboard_data',
                params: {
                    // date_from: this.date_from.year()+'-'+(this.date_from.month()+1)+'-'+(this.date_from.date()),
                    // date_to: this.date_to.year()+'-'+(this.date_to.month()+1)+'-'+(this.date_to.date()),
                },
            }).then(function (result) {
                self.dashboard_widgets = result;
            });
        },


        change_approval_modul_name: function (e) {
            var name = $('.approval_modul_name').val()
            if (name=='0' || name==0){
                this.approval_modul_name = ''
            }
            else{
                this.approval_modul_name = name
            }
            this.render_dashboard_widgets()
                
        },

        change_req_approval_modul_name: function (e) {
            var name = $('.req_approval_modul_name').val()
            if (name=='0' || name==0){
                this.req_approval_modul_name = ''
            }
            else{
                this.req_approval_modul_name = name
            }
            this.render_dashboard_widgets()

        },

        click_approval_table_tr: function (e) {
            const self = this;
            var $currentTarget = $(e.currentTarget);
            var data_id = $currentTarget.data('id')
            var model = $currentTarget.data('model')
            var name = $currentTarget.data('name')
            var dict = {
                   name : name,
                   views: [[false, 'form']],
                   res_model: model,
                   type: 'ir.actions.act_window',
                   res_id:data_id,
                   target: 'new',
                   flags: {mode: 'readonly'},
                   context: {edit: false,
                             create: false,
                             },
            }
            if (model=='hr.employee'){
                dict = {
                       name : name,
                       views: [[false, 'form']],
                       res_model: model,
                       type: 'ir.actions.act_window',
                       context:{'form_view_ref':'equip3_employee_selfservice.employee_edit_self_service'},
                       res_id:data_id,
                       target: 'new',
                       flags: {mode: 'readonly'},
                       context: {edit: false,
                                 create: false,
                                 },
                }
            }
            return self.do_action(dict);
        },

        render_dashboard_widgets: function () {
            const self = this;
            var chart_data = self.dashboard_widgets.chart_data
            var chart_data_labels = chart_data.labels
            var chart_data_labels_pie = chart_data.labels_pie
            var chart_data_data = chart_data.data
            var list_modul = chart_data.origin_label
            var detail_data = self.dashboard_widgets.detail_data
            var my_req_approval = self.dashboard_widgets.my_req_approval
            var chart_total = self.dashboard_widgets.total
            let $content_block = self.$el.find('.o_website_dashboard_content');
            $content_block.empty();
            $content_block.append(
                    QWeb.render("equip3_approval_dashboard.o_website_dashboard_content_body", {'approval_modul_name':this.approval_modul_name,'list_modul':list_modul,'detail_data': detail_data,'total':chart_total, 'req_approval_modul_name':this.req_approval_modul_name, 'my_req_approval': my_req_approval,})
                );
            // o_action_manager
            self.$el.addClass('o_action o_view_controller o_view_sample_data')
            let myChartbar = $(self.$el.find('#myChartbar')).get(0).getContext('2d');
            let myChartcicrle = $(self.$el.find('#myChartcicrle')).get(0).getContext('2d');
            let $table_bordered= $(self.$el.find('.table-bordered'))
            $.getScript("/equip3_approval_dashboard/static/src/js/pagination.js");
            $.getScript("/equip3_approval_dashboard/static/src/js/chart.js", function() {
                console.log($table_bordered,'$table_bordered$table_bordered')
                $table_bordered.DataTable();
                var backgroundColorpie = []
                for (let i = 0; i < chart_data_labels.length; i++) {
                     var colorR = Math.floor((Math.random() * 256));
                      var colorG = Math.floor((Math.random() * 256));
                      var colorB = Math.floor((Math.random() * 256));
                      backgroundColorpie.push("rgb(" + colorR + "," + colorG + "," + colorB + ")")
                }

                const myChart = new Chart(myChartbar, {
                    type: 'bar',
                    data: {
                        labels: chart_data_labels,
                        datasets: [{
                            label: '# of Votes',
                            data: chart_data_data,
                            backgroundColor: backgroundColorpie,
                        }]
                    },
                    options: {
                        legend: {
                                    display: false,

                                },
                        scales: {
                            y: {
                                beginAtZero: true
                            },
                            yAxes: [{
                                ticks: {
                                    fontSize: 13,
                                    fontFamily:'Poppins',
                                     suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        // OR //
                                        beginAtZero: true
                                }
                            }],
                            xAxes: [{
                                ticks: {
                                    fontSize: 13,
                                    fontFamily:'Poppins',
                                }
                            }],
                        }

                    }
                });
                

                const myChartp = new Chart(myChartcicrle, {
                    type: 'outlabeledPie',
                    defaults:{
                        global:{plugins:
                            {
                                fontFamily:'Poppins',
                                font: {
                                    family:'Poppins',
                                    fontFamily:'Poppins',
                                }
                            }
                        },
                        font: {
                                    family:'Poppins',
                                    fontFamily:'Poppins',
                                },
                        fontFamily:'Poppins',
                    },
                    font: {
                                    family:'Poppins',
                                    fontFamily:'Poppins',
                                },
                        fontFamily:'Poppins',

                    data: {
                        labels: chart_data_labels_pie,
                        datasets: [{
                            label: '# of Votes',
                            data: chart_data_data,
                            backgroundColor: backgroundColorpie,
                            font: {
                                family:'Poppins',
                                fontFamily:'Poppins',
                            }
     
                        }]
                    },
                    options: {
                        labels: {
                            font: {
                                family:'Poppins',
                                fontFamily:'Poppins',
                                Family:'Poppins',
                            },
                            fontFamily:'Poppins',
                        },
                        legend: {
                            labels: {
                            font: {
                                family:'Poppins',
                                fontFamily:'Poppins',
                                Family:'Poppins',
                            },
                            fontFamily:'Poppins',
                        },
                        },
                        plugins:{
                            outlabels: {
                           text: '%l',
                           color: '#616161',
                           stretch: 26,
                           backgroundColor: "white",
                           valuePrecision: 1,
                           fontFamily:'Poppins',
                           font: {
                                size:13,
                                family:'Poppins',
                                fontFamily:'Poppins',
                                Family:'Poppins',
                               resizable: true,
                               minSize: 13,
                               maxSize: 13,
                           }
                        }
                        },
                        // zoomOutPercentage: 15,
                        legend: false,
                        
                    }
                });

             

            })
            
                

        },

        reload: function () {
                window.location.href = this.href;
        },

    });
    core.action_registry.add('rr_approval_dashboard_board', approval_dashboard);
    return {
        approval_dashboard: approval_dashboard,
    };
});