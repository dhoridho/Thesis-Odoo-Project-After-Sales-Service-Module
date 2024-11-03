odoo.define('equip3_hr_dashboard_extend.hr_operational_dashboard', function (require){
"use strict";
    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');
    var session = require('web.session');
    var QWeb = core.qweb;
    var rpc = require('web.rpc');
    var attendance_data = []
    var datas_per_page = 7

    var hr_operational_dashboard = AbstractAction.extend({
        contentTemplate: "hr_operational_dashboard_configuration_action",
        hasControlPanel: !1,
        dashboard_widgets: {},
        events: {
            "click .dropdown-submenu": "_onClikSubmenu",
            "click .dropdown-menu-data": "_onClikDropdownMenuData",
            "click .btn-detail": "_onClickButtonDetail",
            "click .checkbox-item": "_onClickCheckboxItem",
            "click .o_pager_previous": "_onClickPrevious",
            "click .o_pager_next": "_onClickNext",
            "click #attendance_status_filter": "_onClickAttendanceStatusFilter",
            "click #btn_refresh": "_onClickBtnRefresh",
            "click #btn_get_data": "_onClickBtnGetData",
            "input #attendance_search": "_onAttendanceSearchKeyup",
        },

        _onClickBtnRefresh: function(ev){
            this.renderElement();

            ev.stopPropagation();
            ev.preventDefault();
        },

        _onClickBtnGetData: function(ev){
            const self = this;
            this._rpc({
                model: 'hr.attendance',
                method: 'cron_create_attendance_daily',
            }).then(function (res) {
                self.renderElement();
            });

            ev.stopPropagation();
            ev.preventDefault();
        },

        _onClikSubmenu: function(ev){
            // this.fetch_filter();
            $(".dropdown-ul").css('display', 'none');
            $(ev.currentTarget).find('.dropdown-ul').toggle();

            ev.stopPropagation();
            ev.preventDefault();
        },

        _onClickAttendanceStatusFilter: function(ev){
            $(ev.currentTarget).find('.dropdown-ul').toggle();

            ev.stopPropagation();
            ev.preventDefault();
        },

        _onClickCheckboxItem: function(ev){
            this.fetch_attendance_data()

            ev.stopPropagation();
        },

        _onClikDropdownMenuData: function(ev){
            var filter = ev.currentTarget.offsetParent.id;
            var value = ev.currentTarget.id;
            var graph_arr = [];
            graph_arr.push(ev.currentTarget.offsetParent.className)

            if ($.inArray('graph_1', graph_arr) >= 0) {
                $("#btn_filter_graph_1").text(ev.currentTarget.innerText);
            }
            this.fetch_data(filter, value, graph_arr);

            ev.stopPropagation();
            ev.preventDefault();
        },

        _onClickButtonDetail: function(ev){
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'hr.attendance',
                res_id: parseInt(ev.currentTarget.id),
                views: [[false, 'form']],
                target: 'current',
            });
        },

        _onClickPrevious: function(ev){
            var total_value = parseInt($('.o_pager_limit').text())
            var prevValue1 = parseInt($('.o_pager_value').val().split('-')[0])
            var prevValue2 = false

            if (prevValue1 != 1 && prevValue1 != 0) {
                prevValue2 = prevValue1 - 1
                prevValue1 = prevValue1 - datas_per_page

                this.fetch_attendance_data_pagination(prevValue1, prevValue2)
            }
        },

        _onClickNext: function(ev){
            var total_value = parseInt($('.o_pager_limit').text())
            var nextValue1 = parseInt($('.o_pager_value').val().split('-')[1]) + 1
            var nextValue2 = false

            if ((nextValue1 + datas_per_page) > total_value && !((nextValue1 - 1) == total_value)) {
                nextValue2 = total_value
            } else if (nextValue1 < total_value) {
                nextValue2 = nextValue1 + (datas_per_page - 1)
            }

            if (nextValue2 != false) {
                this.fetch_attendance_data_pagination(nextValue1, nextValue2)
            }
        },

        _onAttendanceSearchKeyup: function(ev){
            var search_value = ev.currentTarget.value.toLowerCase()
            var table_html_str =''
            var data_length = 0
            var data_count = 0

            $('#attendance_table_body').replaceWith('<tbody id="attendance_table_body"></tbody>');
            for (var i=0; i < attendance_data.length; i++){
                if (attendance_data[i].employee_name.toLowerCase().includes(search_value)) {
                    if (data_count < datas_per_page) {
                        table_html_str += this.create_attendance_table(i)

                        data_count += 1
                    }
                    data_length += 1
                }
            }
            $('#attendance_table_body').append(table_html_str)

            var pager_value = '0-0'
            if (data_length) {
                if (data_length <= datas_per_page) {
                    pager_value = `1-${data_length}`
                } else {
                    pager_value = `1-${datas_per_page}`
                }
            } 
            $('.o_pager_value').prop("value", pager_value)
            $('.o_pager_limit').text(data_length)
        },

        init: function(parent, action) {
            this._super(parent, action);
        },

        start: function () {
            const self = this;
            return this._super().then(function () {
                self.renderElement();
            });
        },

        create_attendance_table: function (array) {
            var attendance_table = `
                <tr>
                <td>${attendance_data[array].employee_name}</td>
                <td>${attendance_data[array].employee_id}</td>
                <td>${attendance_data[array].department}</td>
                <td>${attendance_data[array].attendance_status}</td>
                <td>${attendance_data[array].leave_type}</td>
                <td>${attendance_data[array].working_date}</td>
                <td style=" min-width:70px;">`

            if (attendance_data[array].check_in) {
                attendance_table +=`<button class="btn btn-primary btn-detail" id=${attendance_data[array].attendance_id} type="button">Detail</button>`
            }
            attendance_table += '</td></tr>'

            return attendance_table
        },

        fetch_attendance_data: function () {
            var self = this
            var checked_option = []
            self.$(".checkbox-item").each(function() {
                var option = $(this)[0].id
                var value = $(this)[0].checked
                
                if (value == true) {
                    checked_option.push(option)
                }
            });

            this._rpc({
                route: '/hr_operational_dashboard/fetch_attendance_data',
                params: {
                    status: checked_option,
                },
            }).then(function (res) {
                var table_html_str =''
                var data_length = 0
                attendance_data = res['attendance_data']

                if (attendance_data.length > 0) {
                    $('#btn_get_data').css('display','none');
                }

                $('#attendance_table_body').replaceWith('<tbody id="attendance_table_body"></tbody>');
                for (var i=0; i < attendance_data.length; i++) {
                    if (i < datas_per_page) {
                        table_html_str += self.create_attendance_table(i)
                    }
                    data_length += 1
                }
                $('#attendance_table_body').append(table_html_str)

                var pager_value = '0-0'
                if (data_length) {
                    if (data_length <= datas_per_page) {
                        pager_value = `1-${data_length}`
                    } else {
                        pager_value = `1-${datas_per_page}`
                    }
                } 
                $('.o_pager_value').prop("value", pager_value)
                $('.o_pager_limit').text(data_length)
            });
        },

        fetch_attendance_data_pagination: function (page_1, page_2) {
            var checked_option = []
            $(".checkbox-item").each(function() {
                var option = $(this)[0].id
                var value = $(this)[0].checked
                
                if (value == true) {
                    checked_option.push(option)
                }
            });

            var table_html_str =''
            $('#attendance_table_body').replaceWith('<tbody id="attendance_table_body"></tbody>');
            for (var i=(page_1-1); i <= (page_2-1); i++){
                table_html_str += this.create_attendance_table(i)
            }
            $('#attendance_table_body').append(table_html_str)

            $('.o_pager_value').prop("value", `${page_1}-${page_2}`)
        },

        fetch_filter: function () {
            var self = this;
            this._rpc({
                route: '/hr_operational_dashboard/fetch_dashboard_filter',
                params: {},
            }).then(function (res) {
                var quarterlyFilterGraph1 = $('#quarterly_filter_graph_1');
                if ($('#quarterly_graph_1').length == 0) {
                    for (var i = 0; i < res['filter_graph_1'].length; i++) {
                        quarterlyFilterGraph1.append(`
                            <li id="quarterly_graph_1" class="graph_1">
                                <a tabindex="-1" href="#" id="${res['filter_graph_1'][i]}" class="dropdown-menu-data dropdown-item">
                                    ${res['filter_graph_1'][i]}
                                </a>
                            </li>
                        `)
                    }
                }

                var monthlyFilterGraph1 = $('#monthly_filter_graph_1');
                if ($('#monthly_graph_1').length == 0) {
                    for (var i = 0; i < res['filter_graph_1'].length; i++) {
                        monthlyFilterGraph1.append(`
                            <li id="monthly_graph_1" class="graph_1">
                                <a tabindex="-1" href="#" id="${res['filter_graph_1'][i]}" class="dropdown-menu-data dropdown-item">
                                    ${res['filter_graph_1'][i]}
                                </a>
                            </li>
                        `)
                    }
                }

                var filter = $('#monthly_graph_1')[0].id
                var value = $('#monthly_graph_1')[0].firstElementChild.id
                var graph_arr = [$('#monthly_graph_1')[0].className]

                self.fetch_data(filter, value, graph_arr);
                $("#btn_filter_graph_1").text(value);
            });
        },

        fetch_data: function (filter, value, graph_arr) {
            this._rpc({
                route: '/hr_operational_dashboard/fetch_dashboard_data',
                params: {
                    filter: filter,
                    value: value,
                    graph_arr: graph_arr,
                },
            }).then(function (res) {
                var graph_1_period = []

                if (graph_arr.includes('graph_1')) {
                    for(var data=0; data < res['graph_1_data'].length; data++) {
                        graph_1_period.push(res['graph_1_data'][data]['period']);
                    }

                    $('#leaves_table_head_tr').replaceWith('<tr style="background: lightgrey; width: 100%; position: sticky; top: -10px; z-index: 1;" id="leaves_table_head_tr"></tr>');
                    $('#leaves_table_head_tr').append('<th></th>');

                    for(var i=0; i < graph_1_period.length; i++) {
                        $('#leaves_table_head_tr').append(`<th>${graph_1_period[i]}</th>`);
                    }

                    $('#leaves_table_body').replaceWith('<tbody id="leaves_table_body"></tbody>');
                    
                    var count = 0

                    for(var i=0; i < res['leave_type_data'].leave_type_list.length; i++){
                        var table_html_str = ''
                        
                        table_html_str +=
                            `<tr style="width: 100%; height: 10%;">
                                 <th style="text-align: left; background: lightgrey; text-align: center;">${res['leave_type_data'].leave_type_list[i]['leave_type_name']}</th>
`
                        for(var j=0; j < res['graph_1_data'].length; j++){
                            table_html_str += `<td style="background: lightgrey;">${res['graph_1_data'][j].pivot_total_data[count]}</td>`
                        }

                        table_html_str += '</tr>'

                        for(var j=0; j < res['leave_type_data'].leave_type_list[i]['department_list'].length; j++){
                            table_html_str += 
                                `<tr style="width: 100%; height: 10%;">
                                    <th style="text-align: left; font-weight: normal;">${res['leave_type_data'].leave_type_list[i]['department_list'][j]}</th>`

                            count += 1

                            for (var k=0; k < res['graph_1_data'].length; k++) {
                                table_html_str += `<td>${res['graph_1_data'][k].pivot_total_data[count]}</td>`
                            }

                            table_html_str += '</tr>'
                        }

                        count += 1

                        $('#leaves_table_body').append(table_html_str)
                    }
                }
            });

            this.fetch_attendance_data()
        },

        renderElement: function () {
            var self = this;
            this._super.apply(this, arguments);

            var filter = 'days_graph_1';
            var value = 'next_7_days';
            var graph_arr = ['graph_1']
            this.fetch_data(filter, value, graph_arr);
            this.fetch_filter();
        },
    });

    core.action_registry.add('hr_operational_dashboard_tag', hr_operational_dashboard);
    return hr_operational_dashboard;
});