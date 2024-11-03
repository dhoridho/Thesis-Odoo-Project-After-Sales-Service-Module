odoo.define('equip3_pos_report.analytic_dashboard_pos_js', function (require) {
    "use strict";


    var AbstractAction = require('web.AbstractAction');
    // var ControlPanelMixin = require('web.ControlPanelMixin');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;
    var session = require('web.session');
    var QWeb = core.qweb;
        
    var analytic_pos_dashboard = AbstractAction.extend({
        title: core._t('Analytic Dashboard POS'),
        template: 'equip3_pos_report.analytic_pos_dashboard',
        dashboard_widgets: {},
        events: {
            'click .apd_button_left_top button': 'click_apd_button_top',

            'click #apd_button_print': 'click_apd_button_print',

            'change #compare_datepicker': 'onchange_selector',
            'change #select_day_sp': 'onchange_selector',
            'change #select_top_10_p': 'onchange_selector',
            'change #date_top_bottom_branch': 'onchange_selector',
            'change #select_top_bottom_branch': 'onchange_selector',

            'change #select_top_10_RP': 'onchange_selector',
            'change #select_top_10_PP': 'onchange_selector',
            'change #select_promotion_overview': 'onchange_selector',
            'change #select_top_10_Promotion': 'onchange_selector',
            'change #select1_Promotion_impact': 'onchange_selector',
            'change #select2_Promotion_impact': 'onchange_selector',
            'change #select_loyalty_overview': 'onchange_selector',
            // 'change .req_approval_modul_name': 'change_req_approval_modul_name',
        },
        jsLibs: [
            '/equip3_pos_report/static/src/js/analytic_dashboard_support.js'
        ],


        init: function (parent, params) {
            this._super.apply(this, arguments);
        },

        start: function () {
            const self = this;
            // this._computeControlPanelProps();
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
         onchange_selector: async function (e) {
            var self = this
            await setTimeout(
              async function() 
              {

                await self.fetch_data()
                await self.render_dashboard_widgets()
              }, 1000);
            
        },

        click_apd_button_print: function (e) {
             window.print();
        },

        click_apd_button_top: function (e) {
            $('.apd_section1').hide()
            $('.apd_section3').hide()
            $('.apd_section4').hide()

            $('.apd_button_left_top button').removeClass('apd_button_top_active')
            $(e.target).addClass('apd_button_top_active')
            if(($(e.target).text()).trim()=='-All') {
                $('.apd_section1').show()
                $('.apd_section3').show()
                $('.apd_section4').show()
            }
            else if(($(e.target).text()).trim()=='-SALES') {
                $('.apd_section1').show()
            }
            else if(($(e.target).text()).trim()=='-PROMOTION') {
                $('.apd_section3').show()
            }
            else if(($(e.target).text()).trim()=='-LOYALTIES') {
                $('.apd_section4').show()
            }
        },


        fetch_data: async function () {
            const self = this;
            return await this._rpc({
                route: '/analytic_pos_dashboard/fetch_dashboard_data',
                params: {
                    company_id: session.user_companies.current_company[0],
                    sales_date_compare:$('#compare_datepicker').val() || false,
                    sales_performance: $('#select_day_sp').val() || false,
                    top_10_sort:$('#select_top_10_p').val(),
                    topbottom_branch_sort: $('#select_top_bottom_branch').val(),
                    topbottom_branch_date:$('#date_top_bottom_branch').val() || false,
                    top_10_redeem_sort: $('#select_top_10_RP').val() || 'sa',
                    top_10_plus_sort: $('#select_top_10_PP').val()  || 'sa',
                    promotion_overview_filter:$('#select_promotion_overview').val()  || 'today',
                    top10_promotion_filter:$('#select_top_10_Promotion').val()  || 's_tpu',
                    promotion_impact_filter1:$('#select1_Promotion_impact').val(),
                    promotion_impact_filter2:$('#select2_Promotion_impact').val(),
                    select_loyalty_overview:$('#select_loyalty_overview').val(),
                },
            }).then(function (result) {
                self.dashboard_widgets = result;
            });
        },



        render_dashboard_widgets: function () {
            $.getScript('/equip3_pos_report/static/src/js/analytic_dashboard_support.js');

            const self = this;
            var result_data = self.dashboard_widgets
            let $content_block = self.$el.find('.o_website_dashboard_content');
            $content_block.empty();
            $content_block.append(
                    QWeb.render("equip3_pos_report.analytic_pos_dashboard_body_content", self.dashboard_widgets)
                );
            $(self.$el.find('#compare_datepicker')).datepicker({ dateFormat:'dd/mm/yy', maxDate: new Date() });
             $(self.$el.find('#date_top_bottom_branch')).datepicker({ dateFormat:'dd/mm/yy', maxDate: new Date() });
            if(result_data.sales_performance) {
                $(self.$el.find('#select_day_sp')).val(result_data.sales_performance);
            }
            if(result_data.top_10_sort) {
                $(self.$el.find('#select_top_10_p')).val(result_data.top_10_sort);
            }
            if(result_data.topbottom_branch_sort) {
                $(self.$el.find('#select_top_bottom_branch')).val(result_data.topbottom_branch_sort);
            }
            if(result_data.top_10_redeem_sort) {
                $(self.$el.find('#select_top_10_RP')).val(result_data.top_10_redeem_sort);
            }
            if(result_data.top_10_plus_sort) {
                $(self.$el.find('#select_top_10_PP')).val(result_data.top_10_plus_sort);
            }
            if(result_data.promotion_overview_filter) {
                $(self.$el.find('#select_promotion_overview')).val(result_data.promotion_overview_filter);
            }
            if(result_data.top10_promotion_filter) {
                $(self.$el.find('#select_top_10_Promotion')).val(result_data.top10_promotion_filter);
            }
            if(result_data.promotion_impact_filter1) {
                $(self.$el.find('#select1_Promotion_impact')).val(result_data.promotion_impact_filter1);
            }
            if(result_data.promotion_impact_filter2) {
                $(self.$el.find('#select2_Promotion_impact')).val(result_data.promotion_impact_filter2);
            }
            if(result_data.select_loyalty_overview) {
                $(self.$el.find('#select_loyalty_overview')).val(result_data.select_loyalty_overview);
            }
            $(self.$el.find('#select_day_sp')).select2();
            $(self.$el.find('#select_top_10_p')).select2();
            $(self.$el.find('#select_top_bottom_branch')).select2();
            $(self.$el.find('#select_top_10_RP')).select2();
            $(self.$el.find('#select_top_10_PP')).select2();
            $(self.$el.find('#select_promotion_overview')).select2();
            $(self.$el.find('#select_top_10_Promotion')).select2();
            $(self.$el.find('#select2_Promotion_impact')).select2();
            $(self.$el.find('#select1_Promotion_impact')).select2();
            $(self.$el.find('#select_loyalty_overview')).select2();

            let TaCRCanvas = $(self.$el.find('#TaCRCanvas')).get(0).getContext('2d');
            let SP_APD_Canvas = $(self.$el.find('#SP_APD_Canvas')).get(0).getContext('2d');
            let Top_10_p_Canvas = $(self.$el.find('#Top_10_p_Canvas')).get(0).getContext('2d');
            let TCSCanvas = $(self.$el.find('#TCSCanvas')).get(0).getContext('2d');
            let Top_Bottom_Branch_Canvas = $(self.$el.find('#Top_Bottom_Branch_Canvas')).get(0).getContext('2d');
            let Top_10_PR_Canvas = $(self.$el.find('#Top_10_PR_Canvas')).get(0).getContext('2d');
            let Top_10_PP_Canvas = $(self.$el.find('#Top_10_PP_Canvas')).get(0).getContext('2d');
            let promotion_overview_Canvas = $(self.$el.find('#promotion_overview_Canvas')).get(0).getContext('2d');
            let Top_10_Promotion_Canvas = $(self.$el.find('#Top_10_Promotion_Canvas')).get(0).getContext('2d');
            let Promotion_Impact_SalesVolume_Canvas = $(self.$el.find('#Promotion_Impact_SalesVolume_Canvas')).get(0).getContext('2d');
            let Promotion_Impact_uplift_Canvas = $(self.$el.find('#Promotion_Impact_uplift_Canvas')).get(0).getContext('2d');
            var Promotion_Impact_Uplift_option = {
                responsive: true,
                maintainAspectRatio: false,
                tooltips: {
                                        callbacks: {
                                            title: function (tooltipItems, data) {
                                                return data.labels[tooltipItems[0].index]
                                            }
                                        }
                                    },
                legend: {
                        display: false,
                    },
                    scales: {
                        xAxes: [{
                                ticks: {
                                    fontSize: 8,
                                    fontStyle:'bolder',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.split(/(?=(?:...)*$)/);
                                        value = value.join(',');
                                        return value;
                                    },
                                     suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                }
                            }],
                            yAxes: [{
                                ticks: {
                                    fontSize: 6,
                                    maxTicksLimit: 10 ,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.substring(0, 0);
                                        return value;
                                    },
                                    fontStyle:'bold',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    autoSkip: false,
                                    suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                },
                                
                            }],
                    },
            }
            var Promotion_Impact_SalesVolume_option = {
                responsive: true,
                maintainAspectRatio: false,
                tooltips: {
                                        callbacks: {
                                            title: function (tooltipItems, data) {
                                                return data.labels[tooltipItems[0].index]
                                            }
                                        }
                                    },
                legend: {
                        display: false,
                    },
                    scales: {
                        xAxes: [{
                                ticks: {
                                    fontSize: 8,
                                    fontStyle:'bolder',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.split(/(?=(?:...)*$)/);
                                        value = value.join(',');
                                        return value;
                                    },
                                     suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                }
                            }],
                            yAxes: [{
                                ticks: {
                                    fontSize: 6,
                                    maxTicksLimit: 10 ,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.substring(0, 9);
                                        return value;
                                    },
                                    fontStyle:'bold',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    autoSkip: false,
                                    suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                },
                                
                            }],
                    },
            }


            var Top_10_Promotion_Option = {
                responsive: true,
                maintainAspectRatio: false,
                tooltips: {
                                        callbacks: {
                                            title: function (tooltipItems, data) {
                                                return data.labels[tooltipItems[0].index]
                                            }
                                        }
                                    },
                legend: {
                        labels: {
                            usePointStyle: true,
                            pointStyle: 'circle',
                            fontSize: 11,
                            fontColor:'black',
                            fontStyle:'bold',
                            position: "top",
                            align: "start"

                        }
                    },
                    scales: {
                        yAxes: [{
                                ticks: {
                                    fontSize: 8,
                                    fontStyle:'bolder',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    maxTicksLimit: 8 ,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.split(/(?=(?:...)*$)/);
                                        value = value.join(',');
                                        return value;
                                    },
                                     suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                }
                            }],
                            xAxes: [{
                                ticks: {
                                    fontSize: 6,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.substring(0, 9);
                                        return value;
                                    },
                                    fontStyle:'bold',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    autoSkip: false,
                                    maxRotation: 90,
                                    minRotation: 90,
                                    suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                },
                                
                            }],
                    },
            }

            var promotion_overview_option = {
                responsive: true,
                maintainAspectRatio: false,
                legend: {
                        display: false,
                    },
                plugins: {
                  doughnutlabel: {
                    labels: [
                      {
                        text: result_data.promotion_overview_percentage+'%',
                        font: {
                          size: 23,
                          weight: 'bold',
                        },
                        color:'#407E9F',
                      },
                    ],
                  },
                },
     
            }

            var TCSChart_option = {
                responsive: true,
                maintainAspectRatio: false,
                tooltips: {
                                      callbacks: {
       
                    label: function(item, data) {
                      var dataset = data.datasets[item.datasetIndex];
                      var dataItem = dataset.data[item.index];
                      var obj = dataItem._data;
                      var label = obj.name;
                      return label + ': ' + dataItem.v;
                    }
                  }  ,
              },
                legend: {
                        display: false,
                    },
                scales: {
                        yAxes: [{
                                ticks: {
                                    fontColor:'white',
                                
                                }
                            }],
                            xAxes: [{
                                ticks: {
                                    fontColor:'white',
                                
                                }
                                
                            }],
                    },
                   
            }

            var Top_10_point_option = {
                responsive: true,
                maintainAspectRatio: false,
                tooltips: {
                                        callbacks: {
                                            title: function (tooltipItems, data) {
                                                return data.labels[tooltipItems[0].index]
                                            }
                                        }
                                    },
                legend: {
                        display: false,
                    },
                    scales: {
                        yAxes: [{
                                ticks: {
                                    fontSize: 8,
                                    fontStyle:'bolder',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    maxTicksLimit: 8 ,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.split(/(?=(?:...)*$)/);
                                        value = value.join(',');
                                        return value;
                                    },
                                     suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                }
                            }],
                            xAxes: [{
                                ticks: {
                                    fontSize: 6,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.substring(0, 9);
                                        return value;
                                    },
                                    fontStyle:'bold',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    autoSkip: false,
                                    maxRotation: 90,
                                    minRotation: 90,
                                    suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                },
                                
                            }],
                    },
            }

            var Top_10_p_option = {
                responsive: true,
                maintainAspectRatio: false,
                tooltips: {
                                        callbacks: {
                                            title: function (tooltipItems, data) {
                                                return data.labels[tooltipItems[0].index]
                                            }
                                        }
                                    },
                legend: {
                        display: false,
                    },
                    scales: {
                        yAxes: [{
                                ticks: {
                                    fontSize: 8,
                                    fontStyle:'bolder',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    maxTicksLimit: 8 ,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.split(/(?=(?:...)*$)/);
                                        value = value.join(',');
                                        return value;
                                    },
                                     suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                }
                            }],
                            xAxes: [{
                                ticks: {
                                    fontSize: 6,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.substring(0, 9);
                                        return value;
                                    },
                                    fontStyle:'bold',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    autoSkip: false,
                                    maxRotation: 90,
                                    minRotation: 90,
                                    suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                },
                                
                            }],
                    },
            }
            var Top_Bottom_Branch_option = {
                responsive: true,
                maintainAspectRatio: false,
                tooltips: {
                                        callbacks: {
                                            title: function (tooltipItems, data) {
                                                return data.labels[tooltipItems[0].index]
                                            }
                                        }
                                    },
                legend: {
                        display: false,
                    },
                    scales: {
                        yAxes: [{
                                ticks: {
                                    fontSize: 8,
                                    fontStyle:'bolder',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    maxTicksLimit: 8 ,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.split(/(?=(?:...)*$)/);
                                        value = value.join(',');
                                        return value;
                                    },
                                     suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                }
                            }],
                            xAxes: [{
                                ticks: {
                                    fontSize: 6,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.substring(0, 9);
                                        return value;
                                    },
                                    fontStyle:'bold',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    autoSkip: false,
                                    maxRotation: 90,
                                    minRotation: 90,
                                    suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                },
                                
                            }],
                    },
            }
            var SP_APD_option = {
                responsive: true,
                maintainAspectRatio: false,
                legend: {
                        labels: {
                            usePointStyle: true,
                            pointStyle: 'rectRounded',
                            fontSize: 11,
                            fontColor:'black',
                            fontStyle:'bold',
                            position: "top",
                            align: "start"

                        }
                    },
                    scales: {
                        yAxes: [{
                                ticks: {
                                    fontSize: 8,
                                    fontStyle:'bolder',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    maxTicksLimit: 15 ,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.split(/(?=(?:...)*$)/);
                                        value = value.join(',');
                                        return value;
                                    },
                                     suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                }
                            }],
                            xAxes: [{
                                ticks: {
                                    fontSize: 8,
                                    fontStyle:'bold',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                }
                            }],
                    },
            }

            var TaCRChartoptions = {
                responsive: true,
                maintainAspectRatio: false,
                legend: {
                        labels: {
                            usePointStyle: true,
                            pointStyle: 'circle',
                            fontSize: 11,
                            fontColor:'black',
                            fontStyle:'bold',
                            position: "top",
                            align: "start"

                        }
                    },
                    scales: {
                        yAxes: [{
                                ticks: {
                                    fontSize: 8,
                                    fontStyle:'bolder',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    maxTicksLimit: 12 ,
                                    userCallback: function(value, index, values) {
                                        value = value.toString();
                                        value = value.split(/(?=(?:...)*$)/);
                                        value = value.join(',');
                                        return value;
                                    },
                                     suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                }
                            }],
                            xAxes: [{
                                ticks: {
                                    fontSize: 8,
                                    fontStyle:'bold',
                                    fontFamily:'Poppins',
                                    fontColor:'black',
                                    suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
                                        beginAtZero: true
                                }
                            }],
                    },
            }
            if (result_data.chartTopCategSold){
                setTimeout(function(){ 
                    var TCSchart =  new Chart(TCSCanvas, {
                        type: "treemap",
                        data: {
                           datasets:[{
                                    tree: result_data.chartTopCategSold,
                                    key: "Total Qty",
                                    groups: ["name"],
                                    label:'Category',
                                    fontWeight:'bolder',
                                    fontColor:'white',
                                    backgroundColor: function(ctx) {
                                      var item = ctx.dataset.data[ctx.dataIndex];
                                      if (item) {
                                        return item._data.children[0].color
                                      }
                                      
                                      return 'red';
                                    },
                           }]
                        },
                        options: TCSChart_option
                    });
                }, 3000);


            }

            if (result_data.chartTopBottomBranch.array_data){
                result_data.chartTopBottomBranch.array_data[0]['backgroundColor'] = function(ctx) {
                                  var index = ctx.dataIndex;
                   
                                    return result_data.chartTopBottomBranchcolor[index]
                                                           }
            }
            if (result_data.promotion_impact_uplift_sales_volume_chart){
                result_data.promotion_impact_uplift_sales_volume_chart[0]['backgroundColor'] = function(ctx) {
                                  var index = ctx.dataIndex;
                   
                                    return result_data.promotion_impact_uplift_sales_volume_chart_BC[index]
                                                           }
            }
            var promotion_percentange = 100
            if (promotion_percentange){
                promotion_percentange-=result_data.promotion_overview_percentage
            }
            const promotion_overview_chart = new Chart(promotion_overview_Canvas,{
                data: {
                    labels: ['Not Use', 'Used'],
                    datasets: [
                        {
                          label: 'Promotion Percentage',
                          data: [promotion_percentange,result_data.promotion_overview_percentage],
                          backgroundColor: ['#8db6cc','#407E9F'],
                        },
                    ]
                  },
                type:'doughnut',
               options: promotion_overview_option
            })

            const Promotion_Impact_SalesVolume_Chart = new Chart(Promotion_Impact_SalesVolume_Canvas, {
               type: 'horizontalBar',
               data: {
                   datasets: result_data.promotion_impact_sales_volume_chart,
                   labels: result_data.promotion_impact_chart_labels
               },
               options: Promotion_Impact_SalesVolume_option
            });

            const Promotion_Impact_uplift_Chart = new Chart(Promotion_Impact_uplift_Canvas, {
               type: 'horizontalBar',
               data: {
                   datasets: result_data.promotion_impact_uplift_sales_volume_chart,
                    labels: result_data.promotion_impact_uplift_sales_volume_labels
               },
               options: Promotion_Impact_Uplift_option
            });

            const Top_10_Promotion_Chart = new Chart(Top_10_Promotion_Canvas, {
               type: 'bar',
               data: {
                   datasets: result_data.top10_promotion_chart_data,
                   labels: result_data.top10_promotion_chart_labels
               },
               options: Top_10_Promotion_Option
            });

            const Top_Bottom_Branch_Chart = new Chart(Top_Bottom_Branch_Canvas, {
               type: 'bar',
               data: {
                   datasets: result_data.chartTopBottomBranch.array_data,
                   labels: result_data.chartTopBottomBranch.labels
               },
               options: Top_Bottom_Branch_option
            });

            const Top_10_point_redeem_Chart = new Chart(Top_10_PR_Canvas, {
               type: 'bar',
               data: {
                   datasets: result_data.chart_Top_10_PR_array_data,
                   labels: result_data.chart_Top_10_PR_label
               },
               options: Top_10_point_option
            });

            const Top_10_point_plus_Chart = new Chart(Top_10_PP_Canvas, {
               type: 'bar',
               data: {
                   datasets: result_data.chart_Top_10_PP_array_data,
                   labels: result_data.chart_Top_10_PP_label
               },
               options: Top_10_point_option
            });


            const Top_10_p_Chart = new Chart(Top_10_p_Canvas, {
               type: 'bar',
               data: {
                   datasets: result_data.chart_Top_10_p.array_data,
                   labels: result_data.chart_Top_10_p.labels
               },
               options: Top_10_p_option
            });

            const SP_APD_Chart = new Chart(SP_APD_Canvas, {
               type: 'line',
               data: {
                   datasets: result_data.chart_SP.array_data,
                   labels: result_data.chart_SP.label_time
               },
               options: SP_APD_option
            });

            const TaCRChart = new Chart(TaCRCanvas, {
               type: 'bar',
               data: {
                   datasets: [
                   {
                       label: 'Revenue',
                       data: result_data.chart_TaCR.revenue,
                       borderColor: '#C33727',
                       backgroundColor:'rgba(255, 255, 255, 0.0)',
                       borderWidth: 1,
                       type: 'line',
                       order: 1
                   },
                   {
                       label: 'Total Amount',
                       data: result_data.chart_TaCR.total_amount,
                       backgroundColor: '#BC5090',
                       borderRadius: 15,
                       borderSkipped: false,
                       fill: true,
                       order: 2
                   }, 
                   {
                       label: 'COGS',
                       data: result_data.chart_TaCR.cogs,
                       backgroundColor: '#58508D',
                       borderRadius: 5,
                       order: 3
                   }, 
                   ],
                   labels: result_data.chart_TaCR.label_date
               },
               options: TaCRChartoptions
            });
                

        },

        reload: function () {
                window.location.href = this.href;
        },

    });
    core.action_registry.add('tag_analytic_pos_dashboard', analytic_pos_dashboard);
    return {
        analytic_pos_dashboard: analytic_pos_dashboard,
    };
});
