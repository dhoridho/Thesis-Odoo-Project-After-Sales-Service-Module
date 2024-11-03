odoo.define('equip3_hr_masterdata_employee.employee_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');

        var FieldResume = require('web.FieldResume');
        var ListRenderer = require('web.ListRenderer');
        var qweb = core.qweb;
        var time = require('web.time');
        var _t = core._t;
        
    
        var employee_flow = AbstractAction.extend({
            contentTemplate: "employee_configuration_action",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
            },
            start: function() {
                var self = this;
                var btn_department = self.$('#btn-department')
                var btn_job_position = self.$('#btn-job-posistion')
                var btn_job_classification = self.$('#btn-job-classification')
                var btn_disciplinary_stages = self.$('#btn-disciplinary-stages')
                var btn_race = self.$('#btn-race')
                var btn_religion = self.$('#btn-religion')
                var btn_work = self.$('#btn-work')
                var btn_contract_type = self.$('#btn-contract-type')
                var btn_types = self.$('#btn-types')
                var btn_orientation_checklist = self.$('#btn-orientation-checklist')
                var btn_employee_change_request_approval = self.$('#btn-employee-change-request-approval')
                var btn_employee_marital_status = self.$('#btn-employee-marital-status')
                var report_employee = self.$('#report-employee')
                var master_data_employee = self.$('#master-data-employee')
                var btn_salary_increment = self.$('#btn-salary-increment')
                var btn_employee_analysis = self.$('#btn-employee-analysis')
                this.getSession().user_has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader').then(function(has_group) {
                    if(!has_group) {
                        btn_department.remove();
                        master_data_employee.remove();
                    } 
                });

                this.getSession().user_has_group('equip3_hr_employee_access_right_setting.group_hr_officer').then(function(has_group) {
                    if(!has_group) {
                        btn_job_position.remove();
                        btn_job_classification.remove();
                        btn_race.remove();
                        btn_religion.remove();
                        btn_work.remove();
                        btn_contract_type.remove();
                        btn_types.remove();
                        btn_disciplinary_stages.remove();
                        btn_orientation_checklist.remove();
                        btn_employee_change_request_approval.remove();
                        btn_employee_marital_status.remove();
                        btn_salary_increment.remove();
                        report_employee.remove();
                        
                    } 
                });

                this.getSession().user_has_group('hr.group_hr_manager').then(function(has_group) {
                    if(!has_group) {
                        btn_employee_analysis.remove()
                        
                        
                    } 
                });

                
                return this._super.apply(this, arguments);
            },

            _onClickAccordion: function(ev){
                let $target = $(ev.currentTarget);
                let _id = $target.attr('data-target');
                let $accordion = $(`#${_id}`);
                if($accordion.hasClass('show')){
                    $accordion.removeClass('show').addClass('collapse');
                    $accordion.parent().find('.accordion-button').addClass('collapse');
                }else{
                    $accordion.removeClass('collapse').addClass('show');
                    $accordion.parent().find('.accordion-button').removeClass('collapse');
                }
            },
            _onOpen: function(ev){ 
                let self = this;
                let $target = $(ev.currentTarget);
                let $button_name = $target.attr('name')
                if ($button_name != 'action_button_none'){
                    self.do_action( $button_name);
                }
            }
        });

        var AbstractGroupedOne2ManyRenderer = ListRenderer.extend({
            groupBy: '',
            groupTitleTemplate: 'hr_default_group_row',
            dataRowTemplate: '',
            addLineButtonTemplate: 'group_add_item',

            /**
             * @override
             * @private
             */
            _freezeColumnWidths: function () {},

             /**
             * @override
             * @private
             */
            _renderHeader: function () {
                return $('<thead/>');
            },

             /**
             * @override
             * @private
             */
            _renderFooter: function () {
                return $('<tfoot/>');
            },

            /**
             * @override
             * @private
             */
            _renderGroupRow: function (display_name) {
                return qweb.render(this.groupTitleTemplate, {display_name: display_name});
            },

            /**
             * @private
            */
            _formatData: function (data) {
                return data;
            },

            _renderRow: function (record, isLast) {
                return $(qweb.render(this.dataRowTemplate, {
                    id: record.id,
                    data: this._formatData(record.data),
                    is_last: isLast,
                }));
            },

            /**
             * @private
            */
            _getCreateLineContext: function (group) {
                return {};
            },

            _renderTrashIcon: function() {
                return qweb.render('hr_trash_button');
            },

            _renderAddItemButton: function (group) {
                return qweb.render(this.addLineButtonTemplate, {
                    context: JSON.stringify(this._getCreateLineContext(group)),
                });
            },

            _renderBody: function () {
                var self = this;

                var grouped_by = _.groupBy(this.state.data, function (record) {
                    return record.data[self.groupBy].res_id;
                });

                var groupTitle;
                var $body = $('<tbody>');
                for (var key in grouped_by) {
                    var group = grouped_by[key];
                    if (key === 'undefined') {
                        groupTitle = _t("Other");
                    } else {
                        groupTitle = group[0].data[self.groupBy].data.display_name;
                    }
                    var $title_row = $(self._renderGroupRow(groupTitle));
                    $body.append($title_row);

                    // Render each rows
                    group.forEach(function (record, index) {
                        var isLast = (index + 1 === group.length);
                        var $row = self._renderRow(record, isLast);
                        if (self.addTrashIcon) $row.append(self._renderTrashIcon());
                        $body.append($row);
                    });

                    if (self.addCreateLine) {
                        $title_row.find('.o_group_name').append(self._renderAddItemButton(group));
                    }
                }

                if ($body.is(':empty') && self.addCreateLine) {
                    $body.append(this._renderAddItemButton());
                }
                return $body;
            },

        });

        var ResumeLineRenderer = AbstractGroupedOne2ManyRenderer.extend({
            groupBy: 'line_type_id',
            groupTitleTemplate: 'hr_resume_group_row',
            dataRowTemplate: 'hr_resume_data_row',

            _formatData: function (data) {
                var dateFormat = time.getLangDateFormat();
                var date_start = data.date_start && moment(data.date_start).format(dateFormat) || "";
                var date_end = data.date_end && moment(data.date_end).format(dateFormat) || _t("Current");
                return _.extend(data, {
                    date_start: date_start,
                    date_end: date_end,
                });
            },

            _getCreateLineContext: function (group) {
                var ctx = this._super(group);
                return group ? _.extend({default_line_type_id: group[0].data[this.groupBy] && group[0].data[this.groupBy].data.id || ""}, ctx) : ctx;
            },

            _render: function () {
                var self = this;
                return this._super().then(function () {
                    self.$el.find('table').removeClass('table-striped o_list_table_ungrouped');
                    self.$el.find('table').addClass('o_resume_table table-borderless');
                });
            },
        });

        FieldResume.include({
            /**
             * @override
             * @param {Object} prop
             * @returns {Boolean}
             */
            _getRenderer: function () {
                return ResumeLineRenderer;
            },
        });
    
        core.action_registry.add('employee_flow_tag', employee_flow);
        return employee_flow;
    });