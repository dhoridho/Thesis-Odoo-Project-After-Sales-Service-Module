odoo.define('setu_cash_flow_forecasting_dashboard.dashboard', function (require) {
"use strict";

const { useRef } = owl.hooks;
var AbstractField = require('web.AbstractField');
var core = require('web.core');
var AbstractAction = require('web.AbstractAction');
var ajax = require('web.ajax');
var time = require('web.time');
var web_client = require('web.web_client');
var _t = core._t;
var QWeb = core.qweb;
var field_utils = require('web.field_utils');
var viewRegistry = require('web.view_registry');
var session = require('web.session');
var registry = require('web.field_registry');


var setu_cash_flow_forecasting_dashboard = AbstractAction.extend({
    contentTemplate: 'SetuCashForecastDashboard',
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],
    events: {
        'click .selectBtn': 'on_click_selectBtn',
        'click .option-cashin': 'on_click_option',
        'click .option-cashout': 'on_click_option',
        'click .view_action': 'on_click_view',
        'click .info-badge' : 'on_click_info_badge',
    },
    willStart: async function() {
        var self = this;
        this.dashboardData = {};
        var dashboard_data = this._rpc({
                model: 'setu.cash.flow.forecasting.dashboard',
                method: 'get_dashboard_data',
            })
            .then(function (res) {
               self.dashboardData = res;
            });
        return Promise.all([dashboard_data, this._super.apply(this, arguments)]);
    },

    on_attach_callback: function () {
        var self = this;

         $('.nav-tabs.setu-tabs a').on('show.bs.tab', function(el){
            if((el.target.getAttribute("href") == '#tab2') || (el.target.getAttribute("href") == '#tab3')){
                 $('.filter-navbar').removeClass('hide-content')
            }
            else{
                $('.filter-navbar').addClass('hide-content')
            }
        });

       self.filterFiscalPeriod();
	   // call card line chart method
        self.card_line_chart('expansesChart',this.dashboardData[10]['month'],this.dashboardData[10]['total'],this.dashboardData[10]['currency'])
        self.card_line_chart('incomeChart',this.dashboardData[11]['month'],this.dashboardData[11]['total'],this.dashboardData[11]['currency'])


        // Call methods for generating line and bar chart for income and expense
        this.setu_charts('expanse','bar','false');
        this.setu_charts('income','bar','false');

        self.income_vs_expense_value_chart('income_vs_expense_value')

        // onchange methods for expense and income bar and line chart when change switch button configuration
        $('#switchBar').change(function() {
                 self.setu_charts('expanse','bar','true');
        });
        $('#switchLine').change(function() {
                 self.setu_charts('expanse','line','true');
        });
        $('#switchIncomeBar').change(function() {
                 self.setu_charts('income','bar','true');
        });
        $('#switchIncomeLine').change(function() {
                 self.setu_charts('income','line','true');
        });

         $('#switchValueChart').change(function() {
         
               $('.income_vs_expense_ratio').html('')
               self.income_vs_expense_value_chart('income_vs_expense_value')
               $('.switch_header_text').html('Cash In V/S Cash Out Forecasted Value')
               $('.switch_header_tooltip').html('Cash In V/S Cash Out Forecasted Value')
        });

        $('#switchRatioChart').change(function() {
                
               $('.income_vs_expense_value').html('')
               self.income_vs_expense_ratio_chart('income_vs_expense_ratio')
               $('.switch_header_text').html('Cash In V/S Cash Out Forecasted Ratio')
               $('.switch_header_tooltip').html('Cash In V/S Cash Out Forecasted Ratio')
        });

        this._super.apply(this, arguments);

     },

    // click event for toggle custom select dropdown menu = Done
    on_click_selectBtn: function (ev) {
        var select = $(ev.currentTarget)
        var selectDropdown = select.parent().find('.selectDropdown')
        if($(selectDropdown).hasClass('toggle'))
            $(selectDropdown).removeClass('toggle')
        else
            $(selectDropdown).addClass('toggle')
     },

    // click event for selection option and refresh charts according to selected options
    on_click_option: function (ev) {
        var self= this;
        var option =  $(ev.currentTarget)
        var selectBtn = option.parent().parent().parent().find('.selectBtn')
        var selectDropdown = option.parent().parent()

        if(option.html() != $(selectBtn).html()){
            if(option[0].innerText != "Custom Fiscal Period"){
                var dashboard_data = this._rpc({
                    model: 'setu.cash.flow.forecasting.dashboard',
                    method: 'get_dashboard_data',
                    args: [[{"filter": option[0].innerText}]]

                })
                .then(function (res) {
                   self.dashboardData = res;
                    if($(option).hasClass('option-cashout')){
                        self.setu_charts('expanse','bar','false');
                    }
                    if($(option).hasClass('option-cashin')){
                        self.setu_charts('income','bar','false');
                        //self.setu_charts('expanse','bar','false');
                    }

                    $('#switchBar').prop("checked", true);
                    $('#switchIncomeBar').prop("checked", true);
                });
            }
        }
        $(selectBtn).html(option.html())
        $("#DashboardName").html(option.html())
        $(selectDropdown).removeClass('toggle')
        $('.current_filter_msg').html('')
        if($(option).hasClass('option-cashin')){
            $("#apply_filter").addClass('filter-option-cashin')
             $("#apply_filter").removeClass('filter-option-cashout')
        }
         if($(option).hasClass('option-cashout')){
              $("#apply_filter").removeClass('filter-option-cashin')
            $("#apply_filter").addClass('filter-option-cashout')
        }

    },

    // Prepare doughnut chart data
    doughnut_chart: function(chart_id){

        var canvas = $('.'+chart_id).html("<canvas id="+chart_id+" class='chart-canvas' height='120' style='width: 100%; max-width: 250px'/>")
        var ctx = document.getElementById(chart_id).getContext("2d");

        var gradientStrokeViolet = ctx.createLinearGradient(0, 0, 0, 181);
        gradientStrokeViolet.addColorStop(0, 'rgba(218, 140, 255, 1)');
        gradientStrokeViolet.addColorStop(1, 'rgba(154, 85, 255, 1)');
        var gradientLegendViolet = 'linear-gradient(to right, rgba(218, 140, 255, 1), rgba(154, 85, 255, 1))';

        var gradientStrokeBlue = ctx.createLinearGradient(0, 0, 0, 360);
        gradientStrokeBlue.addColorStop(0, 'rgba(54, 215, 232, 1)');
        gradientStrokeBlue.addColorStop(1, 'rgba(177, 148, 250, 1)');
        var gradientLegendBlue = 'linear-gradient(to right, rgba(54, 215, 232, 1), rgba(177, 148, 250, 1))';

        var chart_dataset_data = [];
        var chart_dataset_label = [];
        var chart_dataset_display_data = [];
        if(chart_id == "expansesChart"){
            for(var data=0;data<Object.values(this.dashboardData[6])[0][1].length;data++){
                chart_dataset_label.push(Object.values(this.dashboardData[6])[0][0][data]);
                chart_dataset_data.push(Object.values(this.dashboardData[6])[0][1][data]);
                chart_dataset_display_data.push(Object.values(this.dashboardData[6])[0][2][data]);
            }
        }
        if(chart_id == "incomeChart"){
            for(var data=0;data<Object.values(this.dashboardData[7])[0][1].length;data++){
                chart_dataset_label.push(Object.values(this.dashboardData[7])[0][0][data]);
                chart_dataset_data.push(Object.values(this.dashboardData[7])[0][1][data]);
                chart_dataset_display_data.push(Object.values(this.dashboardData[7])[0][2][data]);
            }
        }
        if(chart_id == "incomeVsExpanseChart"){
             for(var data=0;data<Object.values(this.dashboardData[8])[0][1].length;data++){
                chart_dataset_label.push(Object.values(this.dashboardData[8])[0][0][data]);
                chart_dataset_data.push(Object.values(this.dashboardData[8])[0][1][data]);
                chart_dataset_display_data.push(Object.values(this.dashboardData[8])[0][2][data]);
            }
        }
        if(chart_dataset_data.every(item => item === 0)){
             var myPie = new Chart(ctx, {
              type: 'doughnut',
              data: {
                labels: chart_dataset_label,
                datasets: [{
                    label: 'chart_dataset_label',
                  backgroundColor: "#dadada",
                   legendColor: [gradientLegendViolet,gradientLegendBlue],
                  data: [100],
                  display_data: chart_dataset_display_data,
                }],
              },
              options: {
              circumference: Math.PI,
              rotation: -Math.PI,
                legend: {
                    display: false
                },
                legendCallback: function(chart) {
                var text = [];
                text.push('<div class="row w-100 text-center m-0 mt-4 text-capitalize card-heading heading-color f-16"><p>No Data Found</p></div>');
                return text.join('');
              },
              tooltips: {
                     enabled: false
                }
              }
            });
             $("#"+chart_id+"Legend").html(myPie.generateLegend());
        }
        else{
            var myPie = new Chart(ctx, {
              type: 'doughnut',
              data: {
                labels: chart_dataset_label,
                datasets: [{
                    label: chart_dataset_label,
                  backgroundColor: [gradientStrokeViolet,gradientStrokeBlue],
                   legendColor: [gradientLegendViolet,gradientLegendBlue],
                  data: chart_dataset_data,
                  display_data: chart_dataset_display_data,
                }],
              },
              options: {
              circumference: Math.PI,
              rotation: -Math.PI,
                legend: {
                    display: false
                },
                legendCallback: function(chart) {
                var text = [];
                text.push('<ul>');
                for (var i = 0; i < chart.data.datasets.length; i++) {
                    for (var j = 0; j < chart.data.datasets[i].legendColor.length; j++){
                        text.push('<li><span class="legend-dots" style="background:' +
                               chart.data.datasets[i].legendColor[j] +
                               '"></span>');

                        if (chart.data.datasets[i].label[j]) {
                            text.push("<span class='text-sm mb-0 pl-2 font-weight-bold heading-color chart-label f-12'>"+chart.data.datasets[i].label[j]+"</span>");
                        }
                        if(chart_id == "incomeVsExpanseChart"){
                            if(chart.data.datasets[i].data[j]<=1){
                                text.push("<span class='chart-value text-danger ml-4 pl-1 font-weight-bolder'>"+chart.data.datasets[i].display_data[j]+"</span>");
                            }
                            else{
                                text.push("<span class='chart-value text-success ml-4 pl-1 font-weight-bolder'>"+chart.data.datasets[i].display_data[j]+"</span>");
                            }
                        }
                        else{
                            text.push("<span class='chart-value heading-color ml-4 pl-1 font-weight-bolder'>"+chart.data.datasets[i].display_data[j]+"</span>");
                        }
                    }

                    text.push('</li>');
                }
                text.push('</ul>');
                return text.join('');
              },
              }
            });
            $("#"+chart_id+"Legend").html(myPie.generateLegend());
        }
        myPie.update();
     },

    // Prepare line and bar chart data
    setu_charts: function(chart_id,chartType,isFilter){
        this.dashboardData;
        var chart_data = this.dashboardData[1].chart_data;
        var month=[],income=[],expense=[],expanse_name=[],expanse_forecasted_value=[],expanse_real_value=[],expanse_month=[],income_name=[],income_forecasted_value=[],income_real_value=[],income_month = [];
        const monthNames = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG','SEPT','OCT','NOV','DEC'];


        for (var data = 0;data<this.dashboardData[2].expense_chart_data.length ;data++){
            expanse_name.push(this.dashboardData[2].expense_chart_data[data].name[0].toUpperCase() + this.dashboardData[2].expense_chart_data[data].name.slice(1));
            expanse_forecasted_value.push(this.dashboardData[2].expense_chart_data[data].forecast_value);
            expanse_real_value.push(this.dashboardData[2].expense_chart_data[data].real_value);
            expanse_month.push(this.dashboardData[2].expense_chart_data[data].month);
        }
        for (var data = 0;data<this.dashboardData[3].income_chart_data.length ;data++){
            income_name.push(this.dashboardData[3].income_chart_data[data].name[0].toUpperCase() +this.dashboardData[3].income_chart_data[data].name.slice(1));
            income_forecasted_value.push(this.dashboardData[3].income_chart_data[data].forecast_value);
            income_real_value.push(this.dashboardData[3].income_chart_data[data].real_value);
            income_month.push(this.dashboardData[3].income_chart_data[data].month);
        }
        var canvas = $('.'+chart_id).html("<canvas id="+chart_id+" class='chart-canvas' height='400' />")
        var ctx = document.getElementById(chart_id).getContext("2d");

        var gradientStrokeViolet = ctx.createLinearGradient(0, 0, 0, 181);
        gradientStrokeViolet.addColorStop(0, 'rgba(218, 140, 255, 1)');
        gradientStrokeViolet.addColorStop(1, 'rgba(154, 85, 255, 1)');
        var gradientLegendViolet = 'linear-gradient(to right, rgba(218, 140, 255, 1), rgba(154, 85, 255, 1))';

        var gradientStrokeBlue = ctx.createLinearGradient(0, 0, 0, 360);
        gradientStrokeBlue.addColorStop(0, 'rgba(54, 215, 232, 1)');
        gradientStrokeBlue.addColorStop(1, 'rgba(177, 148, 250, 1)');

        var gradientStroke1 = ctx.createLinearGradient(0, 230, 0, 50);

        gradientStroke1.addColorStop(1, 'rgba(218, 140, 255, 1)');
        gradientStroke1.addColorStop(0.2, 'rgba(218, 140, 255, 0.2)');
        gradientStroke1.addColorStop(0, 'rgba(218, 140, 255, 0)');

        var ChartBackgroundColor1 = gradientStrokeViolet;
        var ChartBackgroundColor2 = gradientStrokeBlue;

        if(chartType == 'line'){
            ChartBackgroundColor1 = gradientStroke1;
            ChartBackgroundColor2 = gradientStroke1;
        }
        if(chart_id == 'income'){
            expanse_name = income_name;
            expanse_forecasted_value = income_forecasted_value;
            expanse_real_value = income_real_value;
            expanse_month = income_month;
        }

        var gradientLegendBlue = 'linear-gradient(to right, rgba(54, 215, 232, 1), rgba(177, 148, 250, 1))';
        if(isFilter == 'true'){
                if(chart_id == "income"){
                   document.getElementById(chart_id).remove();
                   $('#chart_income_expanse2').append('<canvas id='+chart_id+' class="chart-canvas" height="400"><canvas>');
                   ctx = document.getElementById(chart_id).getContext("2d");
                }
                else{
                   document.getElementById(chart_id).remove();
                   $('#chart_income_expanse').append('<canvas id='+chart_id+' class="chart-canvas" height="400"><canvas>');
                   ctx = document.getElementById(chart_id).getContext("2d");
                }
            }
            if(chartType == "line"){
              var dataset = []
              var dataset_data = []
              var line_labels = []
              if(chart_id == 'income'){
                  for (var data=0;data<this.dashboardData[5][0].length;data++){
                      var dict = {};
                      dict["label"] = this.dashboardData[5][0][data]['name'][0].toUpperCase() + this.dashboardData[5][0][data]['name'].slice(1);
                      dict["data"] = this.dashboardData[5][0][data]['forecast_value'];
                      dict["type"] = 'line';
                      dict["borderColor"] = this.getRandomColor();
                      dict['legendColor'] = gradientLegendViolet;
                      dict['backgroundColor'] = ChartBackgroundColor1;
                      dict['fill'] = false;
                      dict['tension'] = 0.1;
                        dict['pointBorderWidth']= 4,
                        dict['pointHoverRadius']= 8,
                        dict['pointHoverBorderWidth']= 5,
                        dict['pointRadius']= 4,
                        dict['pointHitRadius']= 16,
                      dataset.push(dict)
                  }
                  if(this.dashboardData[5][0].length > 0){
                       line_labels = this.dashboardData[5][0][0]['forecast_period'];
                  }
              }
              else{
                  for (var data=0;data<this.dashboardData[4][0].length;data++){
                      var dict = {};
                      dict["label"] = this.dashboardData[4][0][data]['name'][0].toUpperCase() + this.dashboardData[4][0][data]['name'].slice(1);
                      dict["data"] = this.dashboardData[4][0][data]['forecast_value'];
                      dict["type"] = 'line';
                      dict["borderColor"] = this.getRandomColor();
                      dict['legendColor'] = gradientLegendViolet;
                      dict['backgroundColor'] = ChartBackgroundColor1;
                      dict['fill'] = false;
                      dict['tension'] = 0.1;
                      dict['pointBorderWidth']= 4,
                        dict['pointHoverRadius']= 8,
                        dict['pointHoverBorderWidth']= 5,
                        dict['pointRadius']= 4,
                        dict['pointHitRadius']= 16,
                      dataset.push(dict)
                  }
                  if(this.dashboardData[4][0].length > 0){
                      line_labels =  this.dashboardData[4][0][0]['forecast_period'];
                  }
              }
               var is_offset = false
               if(line_labels.length == 1){
                    is_offset = true
               }
              if(dataset.every(item => item['data'].length === 0)){
                  var myChart = new Chart(ctx, {
                  type: chartType,
                  data: {
                      labels: monthNames,
                      datasets:  [{
                          label: 'Series 1',
                          data: [6,10,9,6,14,12,16,13,9,7,6,10],
                          fill: false,
                          borderColor: '#dadada',
                          backgroundColor: '#dadada',
                          borderWidth: 2
                      },
                                {
                          label: 'Series 2',
                          data: [10,8,6,5,12,8,16,17,6,7,6,10],
                          fill: false,
                          borderColor: '#dadada',
                          backgroundColor: '#dadada',
                          borderWidth: 2
                      }]
                  },
                  options: {
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      display: false,
                    }
                  },
                  interaction: {
                    intersect: false,
                    mode: 'index',
                  },
                  scales: {
                    y: {
                        beginAtZero: true,
                        min: 0,
                      grid: {
                        drawBorder: false,
                        display: true,
                        drawOnChartArea: true,
                        drawTicks: false,
                        borderDash: [5, 5]
                      },
                      ticks: {
                        display: true,
                        padding: 10,
                        color: '#fbfbfb',
                        font: {
                          size: 11,
                          family: "Open Sans",
                          style: 'normal',
                          lineHeight: 2
                        },
                      }
                    },
                    x: {
                      grid: {
                        drawBorder: false,
                        display: false,
                        drawOnChartArea: false,
                        drawTicks: true,
                        borderDash: [5, 5]
                      },
                      ticks: {
                        display: true,
                        color: '#ccc',
                        padding: 20,
                        font: {
                          size: 11,
                          family: "Open Sans",
                          style: 'normal',
                          lineHeight: 2
                        },
                      }
                    },
                  },
                },
  
                  });
  
                  $("#"+chart_id+"_no_data").addClass("d-block")
              }
              else{
                  var myChart = new Chart(ctx, {
                  type: chartType,
                  data: {
                      labels: line_labels,
                      datasets:  dataset,
                  },
                  options: {
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      display: false,
                    }
                  },
                  interaction: {
                    intersect: false,
                    mode: 'index',
                  },
                  scales: {
                    xAxes: [{
                        offset: is_offset,
                      scaleLabel: {
                            display: true,
                            labelString: 'Fiscal Period',
                            fontStyle: "bold",
                          },
                   }],
  
                   yAxes: [{
                          ticks: {
                              beginAtZero: true
                          },
                          scaleLabel: {
                            display: true,
                            labelString: 'Value ('+this.dashboardData[12]+')',
                            fontStyle: "bold",
                          },
                      }],
                    y: {
                        beginAtZero: true,
                        min: 0,
                      grid: {
                        drawBorder: false,
                        display: true,
                        drawOnChartArea: true,
                        drawTicks: false,
                        borderDash: [5, 5]
                      },
                      ticks: {
                        display: true,
                        padding: 10,
                        color: '#fbfbfb',
                        font: {
                          size: 11,
                          family: "Open Sans",
                          style: 'normal',
                          lineHeight: 2
                        },
                      }
                    },
                    x: {
                      grid: {
                        drawBorder: false,
                        display: false,
                        drawOnChartArea: false,
                        drawTicks: true,
                        borderDash: [5, 5]
                      },
                      ticks: {
                        display: true,
                        color: '#ccc',
                        padding: 20,
                        font: {
                          size: 11,
                          family: "Open Sans",
                          style: 'normal',
                          lineHeight: 2
                        },
                      }
                    },
                  },
                },
  
                  });
                  if($("#"+chart_id+"_no_data").hasClass("d-block")){
                    $("#"+chart_id+"_no_data").removeClass("d-block");
                  }
                  $("#"+chart_id+"_no_data").addClass("d-none")
              }
          }
          else{
              if(expanse_real_value.length == 0 || expanse_forecasted_value.length == 0){
                  var myChart = new Chart(ctx, {
                  type: chartType,
                  data: {
                      labels: monthNames,
                      datasets:  [
                            {
                              label: "Forecasted Value",
                              backgroundColor: "#dadada",
                              borderWidth: 1,
                              borderColor: "#dadada",
                              fill: false,
                              data: [6,10,9,6,14,12,16,13,9,7,6,10]
                            },
                            {
                              label: "Real Value",
                              backgroundColor: "#dadada",
                              borderWidth: 1,
                              borderColor: "#dadada",
                              fill: false,
                              data: [10,8,6,5,12,8,16,17,6,7,6,10]
                            }
                      ]
                  },
                  options: {
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      display: false,
                    }
                  },
                  interaction: {
                    intersect: false,
                    mode: 'index',
                  },
                  tooltips: {
                       enabled: false
                  },
                  scales: {
                    y: {
                        beginAtZero: true,
                        min: 0,
                      grid: {
                        drawBorder: false,
                        display: true,
                        drawOnChartArea: true,
                        drawTicks: false,
                        borderDash: [5, 5]
                      },
                      ticks: {
                        display: true,
                        padding: 10,
                        color: '#fbfbfb',
                        font: {
                          size: 11,
                          family: "Open Sans",
                          style: 'normal',
                          lineHeight: 2
                        },
                      }
                    },
                    x: {
                      grid: {
                        drawBorder: false,
                        display: false,
                        drawOnChartArea: false,
                        drawTicks: true,
                        borderDash: [5, 5]
                      },
                      ticks: {
                        display: true,
                        color: '#ccc',
                        padding: 20,
                        font: {
                          size: 11,
                          family: "Open Sans",
                          style: 'normal',
                          lineHeight: 2
                        },
                      }
                    },
                  },
                },
  
                  });
                  $("#"+chart_id+"_no_data").addClass("d-block")
              }
              else{
                  var chart_label = ""
                  if (chart_id == 'expanse'){
                      chart_label = "Cash Out Type"
                  }
                  else{
                      chart_label = "Cash In Type"
                  }
                  var myChart = new Chart(ctx, {
                  type: chartType,
                  data: {
                      labels: expanse_name,
                      datasets: [
                        {
                          label: "Forecasted Value",
                          borderColor: gradientStrokeViolet,
                          backgroundColor: ChartBackgroundColor1,
                          legendColor: gradientLegendViolet,
                          fill: true ,
                          data: expanse_forecasted_value,
                          tension: 0.4,
                          pointRadius: 0,
                        },
                        {
                          label: 'Real Value',
                          borderColor: gradientStrokeBlue,
                          backgroundColor: ChartBackgroundColor2,
                          legendColor: gradientStrokeBlue,
                          fill: true,
                          data: expanse_real_value,
                           tension: 0.4,
                          pointRadius: 0,
                        },
  
                    ]
                  },
                  options: {
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      display: false,
                    }
                  },
                  interaction: {
                    intersect: false,
                    mode: 'index',
                  },
                  scales: {
                  xAxes: [{
                      scaleLabel: {
                            display: true,
                            labelString: chart_label,
                            fontStyle: "bold",
                          }
                   }],
                   yAxes: [{
                          ticks: {
                              beginAtZero: true
                          },
                           scaleLabel: {
                            display: true,
                            labelString: 'Value ('+this.dashboardData[12]+')',
                            fontStyle: "bold",
                          }
                      }],
                    y: {
                        beginAtZero: true,
                        suggestedMin: 0,
                        min: 0,
                      grid: {
                        drawBorder: false,
                        display: true,
                        drawOnChartArea: true,
                        drawTicks: false,
                        borderDash: [5, 5]
                      },
                      ticks: {
                        display: true,
                        padding: 10,
                        color: '#fbfbfb',
                        font: {
                          size: 11,
                          family: "Open Sans",
                          style: 'normal',
                          lineHeight: 2
                        },
                      }
                    },
                    x: {
                      grid: {
                        drawBorder: false,
                        display: false,
                        drawOnChartArea: false,
                        drawTicks: true,
                        borderDash: [5, 5]
                      },
                      ticks: {
                        display: true,
                        color: '#ccc',
                        padding: 20,
                        font: {
                          size: 11,
                          family: "Open Sans",
                          style: 'normal',
                          lineHeight: 2
                        },
                      }
                    },
                  },
                },
  
                  })
                   if($("#"+chart_id+"_no_data").hasClass("d-block")){
                    $("#"+chart_id+"_no_data").removeClass("d-block");
                  }
                  $("#"+chart_id+"_no_data").addClass("d-none")
              }
          }




    },

    // Card Line Chart Method
    card_line_chart: function(chart_id,month,total,currency){
        var self = this;
        var canvas = $('.'+chart_id).html("<canvas id="+chart_id+" class='chart-canvas pt' height='400' />")
        var display_data =  currency;
        var ctx = document.getElementById(chart_id).getContext("2d");

        var gradientStrokeViolet = ctx.createLinearGradient(0, 0, 0, 181);
        gradientStrokeViolet.addColorStop(0, 'rgba(218, 140, 255, 1)');
        gradientStrokeViolet.addColorStop(1, 'rgba(154, 85, 255, 1)');
        var gradientLegendViolet = 'linear-gradient(to right, rgba(218, 140, 255, 1), rgba(154, 85, 255, 1))';
        var is_offset = false
         if(month.length == 1){
                is_offset = true
           }

        var myChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: month,
                    datasets:  [{
                        data: total,
                        fill: true,
                        borderColor: gradientStrokeViolet,
                        //backgroundColor: gradientStrokeViolet,
                        pointBorderWidth: 4,
                        pointHoverRadius: 8,
                        pointHoverBackgroundColor: gradientStrokeViolet,
                        pointHoverBorderColor: gradientStrokeViolet,
                        pointHoverBorderWidth: 5,
                        pointRadius: 4,
                        pointHitRadius: 16,

                    }]
                },
                options: {
                responsive: true,
                maintainAspectRatio: false,
                tooltips: {
                    callbacks: {
                        label: function(tooltipItem) {
                            return " " + display_data[tooltipItem.index];
                        }
                    }
                },
               legend: {
                    position: "bottom",
                   display: false
                },
                scales: {
                  xAxes: [{
                    offset: is_offset,
                    scaleLabel: {
                          display: true,
                          labelString: 'Fiscal Period',
                          fontStyle: "bold",
                        }
                 }],
                 yAxes: [{
                  scaleLabel: {
                      display: true,
                     labelString: 'Value ('+this.dashboardData[12]+')',
                      fontStyle: "bold",
                    },
                        ticks: {
                            beginAtZero: true,
                        }
                    }],

                },
              },
        });

    },

    // Prepare Income Vs Expense Value Chart
    income_vs_expense_value_chart: function(chart_id){

         var self = this;
        var canvas = $('.'+chart_id).html("<canvas id="+chart_id+" class='chart-canvas pt' height='400' />")
        var ctx = document.getElementById(chart_id).getContext("2d");

        var gradientStrokeViolet = ctx.createLinearGradient(0, 0, 0, 181);
        gradientStrokeViolet.addColorStop(0, 'rgba(218, 140, 255, 1)');
        gradientStrokeViolet.addColorStop(1, 'rgba(154, 85, 255, 1)');
        var gradientLegendViolet = 'linear-gradient(to right, rgba(218, 140, 255, 1), rgba(154, 85, 255, 1))';

         var gradientStrokeBlue = ctx.createLinearGradient(0, 0, 0, 360);
        gradientStrokeBlue.addColorStop(0, 'rgba(54, 215, 232, 1)');
        gradientStrokeBlue.addColorStop(1, 'rgba(177, 148, 250, 1)');

        var period = []
        var data = []
        var income = []
        var expense = []
        for(var i=0;i<self.dashboardData[13].length;i++){
            period.push(Object.keys(self.dashboardData[13][i])[0])
            income.push(Object.values(self.dashboardData[13][i])[0][0])
            expense.push(Object.values(self.dashboardData[13][i])[0][1])
//            data.push(Object.values(self.dashboardData[13][i])[0] )
        }
        var myChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: period,
                    datasets:  [{
                        label:'Cash In',
                        data: income,
                        fill: true,
                        borderColor: gradientStrokeViolet,
                        backgroundColor: gradientStrokeViolet,
                        pointBorderWidth: 4,
                        pointHoverRadius: 8,
                        pointHoverBackgroundColor: gradientStrokeViolet,
                        pointHoverBorderColor: gradientStrokeViolet,
                        pointHoverBorderWidth: 5,
                        pointRadius: 4,
                        pointHitRadius: 16,

                    },
                    {
                        label:'Cash Out',
                        data: expense,
                        fill: true,
                        borderColor: gradientStrokeBlue,
                        backgroundColor: gradientStrokeBlue,
                        pointBorderWidth: 4,
                        pointHoverRadius: 8,
                        pointHoverBackgroundColor: gradientStrokeBlue,
                        pointHoverBorderColor: gradientStrokeBlue,
                        pointHoverBorderWidth: 5,
                        pointRadius: 4,
                        pointHitRadius: 16,

                    }]
                },
                options: {
                responsive: true,
                maintainAspectRatio: false,
               legend: {
                   display: true,
                },
                scales: {
                  xAxes: [{
                    scaleLabel: {
                          display: true,
                          labelString: 'Fiscal Period',
                          fontStyle: "bold",
                        }
                 }],
                 yAxes: [{
                  scaleLabel: {
                      display: true,
                     labelString: 'Ratio',
                      fontStyle: "bold",
                    },
                        ticks: {
                            beginAtZero: true,
                        }
                    }],

                },
              },
        });
    },

    // Prepare Income Vs Expense Ratio Chart
    income_vs_expense_ratio_chart: function(chart_id){

         var self = this;
        var canvas = $('.'+chart_id).html("<canvas id="+chart_id+" class='chart-canvas pt' height='400' />")
        var ctx = document.getElementById(chart_id).getContext("2d");

        var gradientStrokeViolet = ctx.createLinearGradient(0, 0, 0, 181);
        gradientStrokeViolet.addColorStop(0, 'rgba(218, 140, 255, 1)');
        gradientStrokeViolet.addColorStop(1, 'rgba(154, 85, 255, 1)');
        var gradientLegendViolet = 'linear-gradient(to right, rgba(218, 140, 255, 1), rgba(154, 85, 255, 1))';

         var gradientStrokeBlue = ctx.createLinearGradient(0, 0, 0, 360);
        gradientStrokeBlue.addColorStop(0, 'rgba(54, 215, 232, 1)');
        gradientStrokeBlue.addColorStop(1, 'rgba(177, 148, 250, 1)');

        var period = []
        var data = []
        for(var i=0;i<self.dashboardData[14].length;i++){
            period.push(Object.keys(self.dashboardData[14][i])[0])
            data.push(Object.values(self.dashboardData[14][i])[0] )
        }
       var myChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: period,
                    datasets:  [{
                        label:'Ratio',
                        data: data,
                        fill: true,
                        borderColor: gradientStrokeViolet,
                        backgroundColor: gradientStrokeViolet,
                        pointBorderWidth: 4,
                        pointHoverRadius: 8,
                        pointHoverBackgroundColor: gradientStrokeViolet,
                        pointHoverBorderColor: gradientStrokeViolet,
                        pointHoverBorderWidth: 5,
                        pointRadius: 4,
                        pointHitRadius: 16,

                    }]
                },
                options: {
                responsive: true,
                maintainAspectRatio: false,
               legend: {
                   display: true,
                },
                scales: {
                  xAxes: [{
                    scaleLabel: {
                          display: true,
                          labelString: 'Fiscal Period',
                          fontStyle: "bold",
                        }
                 }],
                 yAxes: [{
                  scaleLabel: {
                      display: true,
                     labelString: 'Ratio',
                      fontStyle: "bold",
                    },
                        ticks: {
                            beginAtZero: true,
                        }
                    }],

                },
              },
        });
    },

    // click event for open expanse list view = Done
    on_click_view:function(ev){
        var view = $(ev.currentTarget).attr('data-view')
        console.log(view)
        return this.do_action({
                name: 'Cash Forecast Report Analysis',
                type: 'ir.actions.act_window',
                res_model: 'setu.cash.forecast',
                target: 'current',
                views: [[false, 'list']],
                domain: [['forecast_type','=',view]],
                });
    },

    //
    on_click_info_badge: function(ev){
         $(ev.currentTarget.parentElement.parentElement).find('.tooltip-dialog').slideToggle(500);
            setTimeout(function() {
                $(ev.currentTarget.parentElement.parentElement).find('.tooltip-dialog').slideToggle(500)
            }, 4000);
    },

    // generating random color foe charts
    getRandomColor: function () {
        var letters = '0123456789ABCDEF'.split('');
        var color = '#';
        for (var i = 0; i < 6; i++ ) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    },

    // Call method for getting year vise data
    filterdateRangePicker: function(){
        var self= this;
        self.filterFiscalPeriod();
    },

    // get data according to date filter
    filterFiscalPeriod: function(){
        var self = this;
        $('#apply_filter').on('click', function() {
            var StartDate = document.getElementById("filterFiscalPeriodStart");
            var EndDate = document.getElementById("filterFiscalPeriodEnd");
            if(EndDate.options[EndDate.selectedIndex] == null && StartDate.options[StartDate.selectedIndex]== null){
                $("#filterAlert").html("Please Select Start Date And End Date");
                 $("#filterAlert").slideDown(500)
                setTimeout(function() {
                    $("#filterAlert").slideUp(500)
                }, 4000);
            }
            else if(new Date(EndDate.options[ EndDate.selectedIndex ].getAttribute('end-date')) > new Date(StartDate.options[ StartDate.selectedIndex ].getAttribute('start-date'))){
                var dashboard_data = self._rpc({
                    model: 'setu.cash.flow.forecasting.dashboard',
                    method: 'get_dashboard_data',
                    args: [[{"filter":"time_period"},{"start_date":StartDate.options[ StartDate.selectedIndex ].getAttribute('start-date')},{"end_date":EndDate.options[ EndDate.selectedIndex ].getAttribute('end-date')},]]
                })
                .then(function (res) {
                   self.dashboardData = res;
                    if($("#apply_filter").hasClass('filter-option-cashin')){
                        console.log("filter-option-cashin")
                         self.setu_charts('income','bar','false');
                         $('#switchIncomeBar').prop("checked", true);
                          $('.option-cashin-message').html('Custom Fiscal Period ( '+$('#filterFiscalPeriodStart').val()+' To '+$('#filterFiscalPeriodEnd').val()+' )')
                    }
                     if($("#apply_filter").hasClass('filter-option-cashout')){
                       console.log("filter-option-cashout")
                        self.setu_charts('expanse','bar','false');
                        $('#switchBar').prop("checked", true);
                        $('.option-cashout-message').html('Custom Fiscal Period ( '+$('#filterFiscalPeriodStart').val()+' To '+$('#filterFiscalPeriodEnd').val()+' )')
                    }



     

                });
                $('#myModal').modal('hide');
            }
            else{
                $("#filterAlert").html("Please Select Proper Start Date OR End Date");
                $("#filterAlert").slideDown(500)
                setTimeout(function() {
                    $("#filterAlert").slideUp(500)
                }, 4000);
            }

        });
    }

});

core.action_registry.add('setu_cash_flow_forecasting_dashboard', setu_cash_flow_forecasting_dashboard);
return setu_cash_flow_forecasting_dashboard;

});
