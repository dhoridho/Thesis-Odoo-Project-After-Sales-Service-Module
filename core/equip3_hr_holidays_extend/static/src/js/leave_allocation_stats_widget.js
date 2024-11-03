odoo.define('equip3_hr_holidays_extend.LeaveAllocationStatsWidget', function (require) {
    "use strict";

    var time = require('web.time');
    var Widget = require('web.Widget');
    var widget_registry = require('web.widget_registry');

    var LeaveAllocationStatsWidget = Widget.extend({
        template: 'equip3_hr_holidays_extend.leave_allocation_stats',

        /**
         * @override
         * @param {Widget|null} parent
         * @param {Object} params
         */
        init: function (parent, params) {
            this._setState(params);
            this._super(parent);
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * @override to fetch data before rendering.
         */
        willStart: function () {
            return Promise.all([this._super(), this._fetchLeaveTypesData()]);
        },

        /**
         * Fetch new data if needed (according to updated fields) and re-render the widget.
         * Called by the basic renderer when the view changes.
         * @param {Object} state
         * @returns {Promise}
         */
        updateState: function (state) {
            var self = this;
            var to_await = [];
            var updatedFields = this._setState(state);

            if (_.intersection(updatedFields, ['employee', 'date']).length) {
                to_await.push(this._fetchLeaveTypesData());
            }
            return Promise.all(to_await).then(function () {
                self.renderElement();
            });
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Update the state
         * @param {Object} state
         * @returns {String[]} list of updated fields
         */
        _setState: function (state) {
            var updatedFields = [];
            if (state.data.employee_id.res_id !== (this.employee && this.employee.res_id)) {
                updatedFields.push('employee');
                this.employee = state.data.employee_id;
            }
            if (state.data.effective_date !== this.date) {
                updatedFields.push('date');
                this.date = state.data.effective_date;
            }
            return updatedFields;
        },

        /**
         * Fetch the number of leaves, grouped by leave type, taken by ``this.employee``
         * in the year of ``this.date``.
         * The resulting data is assigned to ``this.leavesPerType``
         * @private
         * @returns {Promise}
         */
        _fetchLeaveTypesData: function () {
            if (!this.date || !this.employee) {
                this.leavesPerType = null;
                return Promise.resolve();
            }
            var self = this;
            var year_date_from = this.date.clone().startOf('year');
            var year_date_to = this.date.clone().endOf('year');
            return this._rpc({
                model: 'hr.leave.allocation',
                method: 'read_group',
                lazy: false,
                kwargs: {
                    domain: [['employee_id', '=', this.employee.res_id], ['state', 'in', ['confirm','validate','refuse']], ['effective_date', '<=', year_date_to], ['effective_date', '>=', year_date_from]],
                    fields: ['holiday_status_id', 'state', 'number_of_days:sum'],
                    groupby: ['holiday_status_id', 'state'],
                },
            }).then(function (data) {
                self.leavesPerType = data;
            });
        }
    });

    widget_registry.add('hr_leave_allocation_stats', LeaveAllocationStatsWidget);

    return LeaveAllocationStatsWidget;
});
