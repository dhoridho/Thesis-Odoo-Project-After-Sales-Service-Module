odoo.define('tis_venue_booking.GanttModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');

// optional behavior if this model fields is contains in the view
// var fields_optional = [
//     "color",
//     "active",
// ];

return AbstractModel.extend({

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.gantt = null;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {Object}
     */
    get: function () {
        return _.extend({}, this.gantt);
    },
    /**
     * Load gantt data
     *
     * @param {Object} params
     * @returns {Deferred<any>}
     */
    load: function (params) {
        this.modelName = params.modelName;
        this.mapping = params.mapping;
        this.fields = params.fields;
        this.gantt = {
            fields: this.fields,
            mapping: this.mapping,
            to_grouped_by: params.groupedBy,
            domain: params.domain || [],
            context: params.context || {},
        };
        this._setFocusDate(params.initialDate, params.scale);
        return this._loadGantt();
    },
    /**
     * Same as 'load'
     *
     * @returns {Deferred<any>}
     */
    reload: function (handle, params) {
        if (params.domain) {
            this.gantt.domain = params.domain;
        }
        if (params.context) {
            this.gantt.context = params.context;
        }
        if (params.groupBy) {
            this.gantt.to_grouped_by = params.groupBy;
        }
        return this._loadGantt();
    },
    /**
     * @param {Moment} focusDate
     */
    setFocusDate: function (focusDate) {
        this._setFocusDate(focusDate, this.gantt.scale);
    },
    /**
     * @param {string} scale
     */
    setScale: function (scale,id) {
        this.gantt.btn_id = id;
        this._setFocusDate(this.gantt.focus_date, scale);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @returns [any[]]
     */
    _focusDomain: function () {
        var domain = [[this.gantt.mapping.date_start, '<', this.gantt.to_date.locale('en').format("YYYY-MM-DD")]];
        if (this.fields[this.gantt.mapping.date_stop]) {
             domain = domain.concat([
                '|',
                [this.gantt.mapping.date_stop, ">", this.gantt.start_date.locale('en').format("YYYY-MM-DD")],
                [this.gantt.mapping.date_stop, '=', false]
            ]);
        }
        return domain;
    },
    /**
     * @private
     * @param {any} date
     * @param {any} scale
     * @returns {string}
     */
    _formatDate: function (date, scale) {
        // range date
        // Format to display it
        switch(scale) {
            case "day":
                return date.format("D MMM");
            case "week":
                var date_start = date.clone().startOf("week").format("D MMM");
                var date_end = date.clone().endOf("week").format("D MMM");
                return date_start + " - " + date_end;
            case "month":
                return date.format("MMMM YYYY");
            case "year":
                return date.format("YYYY");
        }
    },
    /**
     * @private
     * @returns {Deferred<any>}
     */
    _loadGantt: function () {
        var self = this;
        var fields = _.values(this.mapping).concat(this.gantt.to_grouped_by);
        fields.push('display_name');
        return this._rpc({
                model: this.modelName,
                method: 'search_read',
                context: this.gantt.context,
                domain: this.gantt.domain.concat(this._focusDomain()),
                fields: _.uniq(fields),
            })
            .then(function (records) {
                self.gantt.data = records;
            });
    },
    /**
     * @private
     * @param {any} focusDate
     * @param {string} scale
     */
    _setFocusDate: function (focusDate, scale) {
        this.gantt.scale = scale;
        this.gantt.focus_date = focusDate;
        this.gantt.start_date = focusDate.clone().subtract(1, scale).startOf(scale);
        this.gantt.to_date = focusDate.clone().add(3, scale).endOf(scale);
        this.gantt.end_date = this.gantt.to_date.add(1, scale);
        this.gantt.date_display = this._formatDate(focusDate, scale);
    },
});

});
