odoo.define('equip3_hr_dashboard_extend.director_dashboard', function (require){
"use strict";
    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var session = require('web.session');
    var QWeb = core.qweb;
    var rpc = require('web.rpc');

    var director_dashboard = AbstractAction.extend({
        contentTemplate: "director_dashboard_configuration_action",
        hasControlPanel: !1,
        dashboard_widgets: {},
        events: {
            'click #btn_other': '_onClickOther',
            "click .dropdown-submenu": "_onClikSubmenu",
            "click .dropdown-submenu-2": "_onClikSubmenu2",
            "click .dropdown-menu-data": "_onClikDropdownMenuData",
            "click": "_onAnyWhereClick",
            "click #btn_employee_analysis": "_onClickViewEmployeeAnalysis",
            "click #btn_attendance_analysis": "_onClickViewAttendanceAnalysis",
            "click #btn_overtime_analysis": "_onClickViewOvertimeAnalysis",
            "click #btn_leave_analysis": "_onClickViewLeaveAnalysis",
            "click #btn_expense_analysis": "_onClickViewExpensesAnalysis",
            "click #btn_cash_advance_analysis": "_onClickViewCashAdvanceAnalysis",
            "click #btn_payslip_report": "_onClickViewPayslipReport",
            "click #btn_loan_analysis": "_onClickViewLoanAnalysis",
            "click #btn_career_transition_analysis": "_onClickViewCarerTransitionAnalysis",
            "click #btn_travel_analysis": "_onClickViewTravelAnalysis",
            "click #btn_training_conduct": "_onClickViewTrainingConductAnalysis",
        },

        _onAnyWhereClick: function(ev){
            ev.preventDefault();
            if ($('.other_content').css('display') != 'none') {
                $( ".other_content" ).slideUp("fast");
            }
        },

        _onClikSubmenu: function(ev){
            this.fetch_filter();
            $(".dropdown-ul").css('display', 'none');
            $(ev.currentTarget).find('.dropdown-ul').toggle();

            ev.stopPropagation();
            ev.preventDefault();
        },

        _onClikSubmenu2: function(ev){
            this.fetch_filter();
            $(".dropdown-ul-2").css('display', 'none');
            $(ev.currentTarget).find('.dropdown-ul-2').toggle();

            ev.stopPropagation();
            ev.preventDefault();
        },

        _onClikDropdownMenuData: function(ev){
            var filter = ev.currentTarget.offsetParent.id;
            var value = ev.currentTarget.id;
            var graph_arr = [];
            graph_arr.push(ev.currentTarget.offsetParent.className)

            if ($.inArray('graph_1', graph_arr) >= 0) {
                $("#btn_filter_graph_1").text(ev.currentTarget.innerText);
            } else if ($.inArray('graph_3', graph_arr) >= 0) {
                $("#btn_filter_graph_3").text(ev.currentTarget.innerText);
            } else if ($.inArray('graph_4', graph_arr) >= 0) {
                $("#btn_filter_graph_4").text(ev.currentTarget.innerText);
            }

            this.fetch_data(filter, value, graph_arr);

            ev.stopPropagation();
            ev.preventDefault();
        },

        init: function(parent, action) {
            var currentDate = new Date();
            var weekday = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
            var month = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
            var formattedDate = weekday[currentDate.getDay()] + ', ' + currentDate.getDate() + ' ' + month[currentDate.getMonth()] + ' ' + currentDate.getFullYear();
            
            var currentDate = new Date();
            var currentHour = currentDate.getHours();
            var timeOfDay;
            if (currentHour >= 5 && currentHour < 11) {
              timeOfDay = "Morning";
            } else if (currentHour >= 11 && currentHour < 15) {
              timeOfDay = "Afternoon";
            } else if (currentHour >= 15 && currentHour < 19) {
              timeOfDay = "Evening";
            } else {
              timeOfDay = "Night";
            }

            this._super(parent, action);
            this.user_login = session.name;
            this.current_date = formattedDate;
            this.time_of_day = timeOfDay;
        },

        start: function () {
            const self = this;

            return this._super().then(function () {
                self.renderElement();
            });
        },

        fetch_filter: function () {
            this._rpc({
                route: '/director_dashboard/fetch_dashboard_filter',
                params: {},
            }).then(function (res) {
                var yearlyFilterGraph1 = $('#yearly_filter_graph_1');
                if ($('#yearly_graph_1').length == 0) {
                    for (var i = 0; i < res['yearly_filter_graph_1'].length; i++) {
                        yearlyFilterGraph1.append(`
                            <li id="yearly_graph_1" class="graph_1">
                                <a tabindex="-1" href="#" id="${res['yearly_filter_graph_1'][i]}" class="dropdown-menu-data dropdown-item">
                                    ${res['yearly_filter_graph_1'][i]}
                                </a>
                            </li>
                        `)
                    }
                }

                var semesterlyFilterGraph1 = $('#semesterly_filter_graph_1');
                if ($('#semesterly_graph_1').length == 0) {
                    for (var i = 0; i < res['semesterly_filter_graph_1'].length; i++) {
                        semesterlyFilterGraph1.append(`
                            <li id="semesterly_graph_1" class="graph_1">
                                <a tabindex="-1" href="#" id="${res['semesterly_filter_graph_1'][i]}" class="dropdown-menu-data dropdown-item">
                                    ${res['semesterly_filter_graph_1'][i]}
                                </a>
                            </li>
                        `)
                    }
                }

                var monthlyFilterGraph1 = $('#monthly_filter_graph_1');
                if ($('#monthly_graph_1').length == 0) {
                    for (var i = 0; i < res['yearly_filter_graph_1'].length; i++) {
                        monthlyFilterGraph1.append(`
                            <li id="monthly_graph_1" class="dropdown-submenu-2 dropdown-toggle dropdown-item">
                                <a id="${res['yearly_filter_graph_1'][i]}">
                                    ${res['yearly_filter_graph_1'][i]}
                                </a>
                                <ul id="monthly_filter_2_graph_1_${res['yearly_filter_graph_1'][i]}" class="dropdown-menu dropdown-ul-2 "></ul>
                            </li>
                        `)
                    }
                }

                var monthlyFilter2Graph1 = $("ul[id*='monthly_filter_2_graph_1_']");
                monthlyFilter2Graph1.each(function(index, element) {
                    var classes = $(element).attr("id");
                    var split_class = classes.split('_')
                    var year = split_class[split_class.length - 1];

                    var eachMonthlyFilter2Graph1 = $(`#${classes}`);
                    if ($(`#monthly_2_graph_1_${year}`).length == 0) {
                        for (var i = 0; i < res['monthly_filter_graph_1'].length; i++) {
                            if (res['monthly_filter_graph_1'][i].includes(year)) {
                                eachMonthlyFilter2Graph1.append(`
                                    <li id="monthly_2_graph_1_${year}" class="graph_1">
                                        <a id="${res['monthly_filter_graph_1'][i]}" class="dropdown-menu-data dropdown-item">
                                            ${res['monthly_filter_graph_1'][i]}
                                        </a>
                                    </li>
                                `)
                            }
                        }
                    }
                });
               
                var yearlyFilterGraph3 = $('#yearly_filter_graph_3');
                if ($('#yearly_graph_3').length == 0) {
                    for (var i = 0; i < res['yearly_filter_graph_3'].length; i++) {
                        yearlyFilterGraph3.append(`
                            <li id="yearly_graph_3" class="graph_3">
                                <a tabindex="-1" href="#" id="${res['yearly_filter_graph_3'][i]}" class="dropdown-menu-data dropdown-item">
                                    ${res['yearly_filter_graph_3'][i]}
                                </a>
                            </li>
                        `)
                    }
                }

                var semesterlyFilterGraph3 = $('#semesterly_filter_graph_3');
                if ($('#semesterly_graph_3').length == 0) {
                    for (var i = 0; i < res['semesterly_filter_graph_3'].length; i++) {
                        semesterlyFilterGraph3.append(`
                            <li id="semesterly_graph_3" class="graph_3">
                                <a tabindex="-1" href="#" id="${res['semesterly_filter_graph_3'][i]}" class="dropdown-menu-data dropdown-item">
                                    ${res['semesterly_filter_graph_3'][i]}
                                </a>
                            </li>
                        `)
                    }
                }

                var monthlyFilterGraph3 = $('#monthly_filter_graph_3');
                if ($('#monthly_graph_3').length == 0) {
                    for (var i = 0; i < res['yearly_filter_graph_3'].length; i++) {
                        monthlyFilterGraph3.append(`
                            <li id="monthly_graph_3" class="dropdown-submenu-2 dropdown-toggle dropdown-item">
                                <a id="${res['yearly_filter_graph_3'][i]}">
                                    ${res['yearly_filter_graph_3'][i]}
                                </a>
                                <ul id="monthly_filter_2_graph_3_${res['yearly_filter_graph_3'][i]}" class="dropdown-menu dropdown-ul-2 "></ul>
                            </li>
                        `)
                    }
                }

                var monthlyFilter2Graph3 = $("ul[id*='monthly_filter_2_graph_3_']");
                monthlyFilter2Graph3.each(function(index, element) {
                    var classes = $(element).attr("id");
                    var split_class = classes.split('_')
                    var year = split_class[split_class.length - 1];

                    var eachMonthlyFilter2Graph3 = $(`#${classes}`);
                    if ($(`#monthly_2_graph_3_${year}`).length == 0) {
                        for (var i = 0; i < res['monthly_filter_graph_3'].length; i++) {
                            if (res['monthly_filter_graph_3'][i].includes(year)) {
                                eachMonthlyFilter2Graph3.append(`
                                    <li id="monthly_2_graph_3_${year}" class="graph_3">
                                        <a id="${res['monthly_filter_graph_3'][i]}" class="dropdown-menu-data dropdown-item">
                                            ${res['monthly_filter_graph_3'][i]}
                                        </a>
                                    </li>
                                `)
                            }
                        }
                    }
                });

                var quarterlyFilterGraph4 = $('#quarterly_filter_graph_4');
                if ($('#quarterly_graph_4').length == 0) {
                    for (var i = 0; i < res['quarterly_filter_graph_4'].length; i++) {
                        quarterlyFilterGraph4.append(`
                            <li id="quarterly_graph_4" class="graph_4">
                                <a tabindex="-1" href="#" id="${res['quarterly_filter_graph_4'][i]}" class="dropdown-menu-data dropdown-item">
                                    ${res['quarterly_filter_graph_4'][i]}
                                </a>
                            </li>
                        `)
                    }
                }
            });
        },

        fetch_data: function (filter, value, graph_arr) {
            this._rpc({
                route: '/director_dashboard/fetch_dashboard_data',
                params: {
                    filter: filter,
                    value: value,
                    graph_arr: graph_arr,
                },
            }).then(function (res) {
                var pie_1_quantity = []
                var pie_2_quantity = []
                var pie_3_quantity = []
                var bar_4_quantity = []

                var pie_1_description = []
                var pie_2_description = []
                var pie_3_description = []
                var bar_4_description = []

                var pie_1_color = []
                var pie_2_color = []
                var pie_3_color = []
                var bar_4_color = []

                if (graph_arr.includes('graph_1')) {
                    for(var data=0;data<res['pie_1_data'].length;data++){
                        pie_1_quantity.push(res['pie_1_data'][data]['qty']);
                        pie_1_description.push(res['pie_1_data'][data]['contract_state']);
                        // pie_1_color.push('#'+Math.floor(100000 + Math.random() * 800000));
                        var rgb = `rgb(${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)})`
                        pie_1_color.push(rgb);

                    }

                    if (res['pie_1_data'].length >= 1){
                        $( "#graph_1_display" ).replaceWith("<canvas id='graph_1_display'></canvas>");
                        new Chart(document.getElementById("graph_1_display"), {
                            type: 'pie',
                            data: {
                                labels: pie_1_description,
                                datasets: [{
                                    backgroundColor: pie_1_color,
                                    data: pie_1_quantity
                                }]
                            },
                            options: {
                                legend: {display: true },
                                title: {
                                    display: false,
                                    text: ''
                                }
                            },
                        });
                    } else {
                        $('#graph_canvas_1').append("<h2>No Data</h2><canvas id='graph_1_display'></canvas>");
                    }
                }

                if (graph_arr.includes('graph_2')) {
                    for(var data=0;data<res['pie_2_data'].length;data++){
                        pie_2_quantity.push(res['pie_2_data'][data]['qty']);
                        pie_2_description.push(res['pie_2_data'][data]['job_position']);
                        // pie_2_color.push('#'+Math.floor(100000 + Math.random() * 800000));
                        var rgb = `rgb(${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)})`
                        pie_2_color.push(rgb);
                    }

                    if (res['pie_2_data'].length >= 1){
                        new Chart(document.getElementById("graph_2_display"), {
                            type: 'doughnut',
                            data: {
                                labels: pie_2_description,
                                datasets: [{
                                    backgroundColor: pie_2_color,
                                    data: pie_2_quantity
                                }]
                            },
                            options: {
                                legend: {display: true },
                                title: {
                                    display: false,
                                    text: ''
                                }
                            },
                        });
                    } else {
                        $('#graph_canvas_2').append("<h2>No Data</h2><canvas id='graph_2_display'></canvas>");
                    }
                }
                
                if (graph_arr.includes('graph_3')) {
                    for(var data=0;data<res['pie_3_data'].length;data++){
                        pie_3_quantity.push(res['pie_3_data'][data]['qty']);
                        pie_3_description.push(res['pie_3_data'][data]['department_name']);
                        // pie_3_color.push('#'+Math.floor(100000 + Math.random() * 800000));
                        var rgb = `rgb(${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)})`
                        pie_3_color.push(rgb);
                    }

                    if (res['pie_3_data'].length >= 1){
                        $( "#graph_3_display" ).replaceWith("<canvas id='graph_3_display'></canvas>");
                        new Chart(document.getElementById("graph_3_display"), {
                            type: 'pie',
                            data: {
                                labels: pie_3_description,
                                datasets: [{
                                    backgroundColor: pie_3_color,
                                    data: pie_3_quantity
                                }]
                            },
                            options: {
                                legend: {display: true },
                                title: {
                                    display: false,
                                    text: ''
                                }
                            },
                        });
                    } else {
                        $('#graph_canvas_3').append("<h2>No Data</h2><canvas id='graph_3_display'></canvas>");
                    }
                }

                if (graph_arr.includes('graph_4')) {
                    for(var data=0;data<res['bar_4_data'].length;data++){
                        bar_4_quantity.push(res['bar_4_data'][data]['hours']);
                        bar_4_description.push(res['bar_4_data'][data]['period']);
                        // pie_1_color.push('#'+Math.floor(100000 + Math.random() * 800000));
                        var rgb = `rgb(${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)}, ${Math.floor(Math.random() * 255)})`
                        bar_4_color.push(rgb);
                    }

                    if (res['bar_4_data'].length >= 1){
                        $( "#graph_4_display" ).replaceWith("<canvas id='graph_4_display'></canvas>");
                        new Chart(document.getElementById("graph_4_display"), {
                            type: 'bar',
                            data: {
                                  labels: bar_4_description,
                                  datasets: [{
                                    backgroundColor: bar_4_color,
                                    data: bar_4_quantity
                                }]
                            },
                            options: {
                                responsive: true,
                                title: {
                                    display: false,
                                    position: "top",
                                    text: "",
                                    fontSize: 18,
                                    fontColor: "#111"
                                },
                                legend: {
                                    display: false,
                                },
                                scales: {
                                    yAxes: [{
                                        scaleLabel: {
                                            display: false,
                                            // fontColor: "black",
                                            // fontSize : 15,
                                            // labelString: "Quantity",
                                            // barThickness: '10px'
                                        },
                                        ticks: {
                                            display: false,
                                            // fontColor: "black",
                                            beginAtZero:true,
                                        }, 
                                        gridLines: {
                                            display: false
                                        }
                                    }],
                                    xAxes: [{
                                        barPercentage: 0.5,
                                        scaleLabel: {
                                            display: false,
                                            fontColor: "black",
                                            fontSize : 12,
                                            labelString: "Product",
                                        },
                                        ticks: {
                                            // display: false,
                                            autoSkip: false,
                                            fontColor: "black",
                                            fontStyle: 'bold',
                                            beginAtZero:true,
                                        },
                                        gridLines: {
                                            display: false
                                            // drawOnChartArea: true,
                                        }
                                    }]
                                },
                            },
                        });
                    } else {
                        $('#graph_canvas_4').append("<canvas id='graph_4_display'></canvas>");
                    }

                    if (filter == 'quarterly_graph_4') {
                        $('#period_desc').text(`Period ${value}`);
                    } else{
                        $('#period_desc').text("");
                    }

                    $('#overtime_table_head_tr_2').replaceWith(`<tr style="width: 100%; position: sticky; top: -1px; z-index: 1;" id="overtime_table_head_tr_2"></tr>`);
                    $('#overtime_table_head_tr_2').append(`<th colspan="2">Department</th>`);

                    for(var i=0; i < bar_4_description.length; i++){
                        $('#overtime_table_head_tr_2').append(`<th>${bar_4_description[i]}</th>`);
                    }

                    $('#overtime_table_body').replaceWith(`<tbody id="overtime_table_body"></tbody>`);
                    
                    for(var i=0; i < res['pivot_4_data']['department_list'].length; i++){
                        var table_html_str = ''

                        table_html_str +=
                            `<tr style="width: 100%; height: 10%; background: #324960; color: white;">
                                 <th colspan="2" style="text-align: left;">${res['pivot_4_data']['department_list'][i].parent}</th>
                                 <td colspan="5"></td>
                             </tr>`

                        for(var j=0; j < res['pivot_4_data']['department_list'][i].child.length; j++){
                            table_html_str += 
                                `<tr style="width: 100%; height: 10%;">
                                    <th style="min-width: 35px;"></th>
                                    <th style="text-align: left; font-weight: normal;">${res['pivot_4_data']['department_list'][i].child[j]}</th>`

                            for (var k=0; k < res['bar_4_data'].length; k++) {
                                table_html_str += `<td>${res['bar_4_data'][k].pivot_hours_data[i]}</td>`
                            }

                            table_html_str += '</tr>'
                        }
                        
                        $('#overtime_table_body').append(table_html_str)
                    }
                }
            });
        },

        _onClickOther: function(ev) {
            ev.preventDefault();
            if ($('.other_content').css('display') == 'none') {
                $( ".other_content" ).slideDown( "fast" );
                $(".other_content").css('display', 'inline-grid');
            } else {
                // $(".other_content").css('display', 'none');
                $( ".other_content" ).slideUp("fast");
            }
            return false;
        },

        renderElement: function () {
            var self = this;
            this._super.apply(this, arguments);

            var filter = 'yearly_graph_1';
            var value = new Date().getFullYear();
            var graph_arr = ['graph_1', 'graph_2', 'graph_3', 'graph_4']
            this.fetch_data(filter, value, graph_arr);
        },

        // Main button shortcuts
        _onClickViewEmployeeAnalysis: function(event){
            event.preventDefault();
            var action = {
                name: 'Employee Analysis',
                type: 'ir.actions.act_window',
                view_mode: 'pivot',
                res_model: 'hr.employee.analysis',
                views: [[false, 'pivot']],
                target: 'current'
            };
            return this.do_action(action);
        },

        _onClickViewAttendanceAnalysis: function(event){
            event.preventDefault();
            var action = {
                name: 'Attendance Analysis',
                type: 'ir.actions.act_window',
                view_mode: 'graph',
                res_model: 'hr.attendance',
                views: [[false, 'graph']],
                target: 'current'
            };
            return this.do_action(action);
        },

        _onClickViewOvertimeAnalysis: function(event){
            event.preventDefault();
            var action = {
                name: 'Overtime Analysis',
                type: 'ir.actions.act_window',
                view_mode: 'pivot',
                res_model: 'hr.overtime.actual.line',
                views: [[false, 'pivot']],
                target: 'current'
            };
            return this.do_action(action);
        },

        // Others button shorcuts
        _onClickViewLeaveAnalysis: function(event){
            event.preventDefault();
            var action = {
                name: 'Leave Analysis',
                type: 'ir.actions.act_window',
                view_mode: 'graph',
                res_model: 'hr.leave',
                views: [[false, 'graph']],
                target: 'current'
            };
            return this.do_action(action);
        },

        _onClickViewExpensesAnalysis: function(event){
            event.preventDefault();
            var action = {
                name: 'Expenses Analysis',
                type: 'ir.actions.act_window',
                view_mode: 'graph',
                res_model: 'hr.expense',
                views: [[false, 'graph']],
                target: 'current'
            };
            return this.do_action(action);
        },

        _onClickViewCashAdvanceAnalysis: function(event){
            event.preventDefault();
            var action = {
                name: 'Cash Advance Analysis',
                type: 'ir.actions.act_window',
                view_mode: 'pivot',
                res_model: 'vendor.deposit',
                views: [[false, 'pivot']],
                target: 'current'
            };
            return this.do_action(action);
        },

        _onClickViewPayslipReport: function(event){
            event.preventDefault();
            var action = {
                name: 'Payslip Report',
                type: 'ir.actions.act_window',
                view_mode: 'pivot',
                res_model: 'hr.payroll.report.view',
                views: [[false, 'pivot']],
                target: 'current'
            };
            return this.do_action(action);
        },

        _onClickViewLoanAnalysis: function(event){
            event.preventDefault();
            var action = {
                name: 'Loan Analysis',
                type: 'ir.actions.act_window',
                view_mode: 'pivot',
                res_model: 'employee.loan.details',
                views: [[false, 'pivot']],
                target: 'current'
            };
            return this.do_action(action);
        },

        _onClickViewCarerTransitionAnalysis: function(event){
            event.preventDefault();
            var action = {
                name: 'Career Transition Analysis',
                type: 'ir.actions.act_window',
                view_mode: 'pivot',
                res_model: 'hr.career.transition',
                views: [[false, 'pivot']],
                target: 'current'
            };
            return this.do_action(action);
        },

        _onClickViewTravelAnalysis: function(event){
            event.preventDefault();
            var action = {
                name: 'Travel Analysis',
                type: 'ir.actions.act_window',
                view_mode: 'pivot',
                res_model: 'travel.request',
                views: [[false, 'pivot']],
                target: 'current'
            };
            return this.do_action(action);
        },

        _onClickViewTrainingConductAnalysis: function(event){
            event.preventDefault();
            var action = {
                name: 'Training Conduct',
                type: 'ir.actions.act_window',
                view_mode: 'list',
                res_model: 'training.conduct',
                views: [[false, 'list']],
                target: 'current'
            };
            return this.do_action(action);
        },
        
    });

    core.action_registry.add('director_dashboard_tag', director_dashboard);
    return director_dashboard;
});