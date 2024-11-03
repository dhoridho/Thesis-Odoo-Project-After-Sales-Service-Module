odoo.define('advanced_web_domain_widget.basic_fields', function (require) {
"use strict";

/**
 * This module contains most of the basic (meaning: non relational) field
 * widgets. Field widgets are supposed to be used in views inheriting from
 * BasicView, so, they can work with the records obtained from a BasicModel.
 */

var AbstractField = require('web.AbstractField');
var config = require('web.config');
var core = require('web.core');
var Domain = require('web.Domain');
var DomainSelector = require('advanced_web_domain_widget.TerabitsDomainSelector');
var {DomainSelectorDialog, DomainSelectorDialog2} = require('advanced_web_domain_widget.DomainSelectorDialog');
var view_dialogs = require('web.view_dialogs');

require("web.zoomodoo");

var qweb = core.qweb;
var _t = core._t;
var _lt = core._lt;

function calculateDate(domain) {
  if (Array.isArray(domain)) {
    const field_name = domain[0];
    const operator = domain[1];
    const val = domain[2];

    const current_date = new Date();
    current_date.setHours(0, 0, 0, 0);

    if (operator !== "date_filter") {
        return [domain];
    }

    if (val === "today") {
        const start_of_today = new Date(current_date);
        const end_of_today = new Date(current_date);
        end_of_today.setDate(end_of_today.getDate() + 1);

        return ["&", [field_name, ">=", start_of_today], [field_name, "<", end_of_today]];
    }

    if (val === "this_week") {
        const start_of_week = new Date(current_date);
        start_of_week.setDate(current_date.getDate() - current_date.getDay());
        const end_of_week = new Date(start_of_week);
        end_of_week.setDate(end_of_week.getDate() + 7);

        return ["&", [field_name, ">=", start_of_week], [field_name, "<", end_of_week]];
    }

    if (val === "this_month") {
        const start_of_month = new Date(current_date);
        start_of_month.setDate(1);
        const end_of_month = new Date(current_date);
        end_of_month.setMonth(end_of_month.getMonth() + 1, 0);

        return ["&", [field_name, ">=", start_of_month], [field_name, "<=", end_of_month]];
    }

    if (val === "this_quarter") {
        const start_of_quarter = new Date(current_date);
        start_of_quarter.setMonth(Math.floor(start_of_quarter.getMonth() / 3) * 3, 1);
        const end_of_quarter = new Date(start_of_quarter);
        end_of_quarter.setMonth(end_of_quarter.getMonth() + 3, 0);

        return ["&", [field_name, ">=", start_of_quarter], [field_name, "<", end_of_quarter]];
    }

    if (val === "this_year") {
        const start_of_year = new Date(current_date);
        start_of_year.setMonth(0, 1);
        const end_of_year = new Date(start_of_year);
        end_of_year.setFullYear(end_of_year.getFullYear() + 1, 0, 0);

        return ["&", [field_name, ">=", start_of_year], [field_name, "<", end_of_year]];
    }

    if (val === "last_day") {
        const start_of_yesterday = new Date(current_date);
        start_of_yesterday.setDate(start_of_yesterday.getDate() - 1);

        return ["&", [field_name, ">=", start_of_yesterday], [field_name, "<", current_date]];
    }

    if (val === "last_week") {
        const end_of_last_week = new Date(current_date);
        end_of_last_week.setDate(end_of_last_week.getDate() - end_of_last_week.getDay());
        const start_of_last_week = new Date(end_of_last_week);
        start_of_last_week.setDate(start_of_last_week.getDate() - 6);

        return ["&", [field_name, ">=", start_of_last_week], [field_name, "<", end_of_last_week]];
    }

    if (val === "last_month") {
        const start_of_last_month = new Date(current_date);
        start_of_last_month.setMonth(start_of_last_month.getMonth() - 1, 1);
        const end_of_last_month = new Date(start_of_last_month);
        end_of_last_month.setMonth(end_of_last_month.getMonth() + 1, 0);

        return ["&", [field_name, ">=", start_of_last_month], [field_name, "<", end_of_last_month]];
    }

    if (val === "last_quarter") {
        const start_of_this_quarter = new Date(current_date);
        start_of_this_quarter.setMonth(Math.floor(start_of_this_quarter.getMonth() / 3) * 3, 1);
        const end_of_last_quarter = new Date(start_of_this_quarter);
        end_of_last_quarter.setMonth(end_of_last_quarter.getMonth() - 1, 0);
        const start_of_last_quarter = new Date(end_of_last_quarter);
        start_of_last_quarter.setMonth(start_of_last_quarter.getMonth() - 3, 1);

        return ["&", [field_name, ">=", start_of_last_quarter], [field_name, "<", end_of_last_quarter]];
    }

    if (val === "last_year") {
        const end_of_last_year = new Date(current_date);
        end_of_last_year.setFullYear(end_of_last_year.getFullYear() - 1, 0, 0);
        const start_of_last_year = new Date(end_of_last_year);
        start_of_last_year.setFullYear(start_of_last_year.getFullYear() - 1, 0, 1);

        return ["&", [field_name, ">=", start_of_last_year], [field_name, "<", end_of_last_year]];
    }

    if (val === "last_7_days") {
        const start_of_last_7_days = new Date(current_date);
        start_of_last_7_days.setDate(start_of_last_7_days.getDate() - 7);

        return [[field_name, ">=", start_of_last_7_days]];
    }

    if (val === "last_30_days") {
        const start_of_last_30_days = new Date(current_date);
        start_of_last_30_days.setDate(start_of_last_30_days.getDate() - 30);

        return [[field_name, ">=", start_of_last_30_days]];
    }

    if (val === "last_90_days") {
        const start_of_last_90_days = new Date(current_date);
        start_of_last_90_days.setDate(start_of_last_90_days.getDate() - 90);

        return [[field_name, ">=", start_of_last_90_days]];
    }

    if (val === "last_365_days") {
        const start_of_last_365_days = new Date(current_date);
        start_of_last_365_days.setDate(start_of_last_365_days.getDate() - 365);

        return [[field_name, ">=", start_of_last_365_days]];
    }

    if (val === "next_day") {
        const start_of_next_day = new Date(current_date);
        start_of_next_day.setDate(start_of_next_day.getDate() + 1);
        const end_of_next_day = new Date(start_of_next_day);
        end_of_next_day.setDate(end_of_next_day.getDate() + 1);

        return ["&", [field_name, ">=", start_of_next_day], [field_name, "<", end_of_next_day]];
    }

    if (val === "next_week") {
        const start_of_next_week = new Date(current_date);
        start_of_next_week.setDate(current_date.getDate() + (7 - current_date.getDay()));
        const end_of_next_week = new Date(start_of_next_week);
        end_of_next_week.setDate(end_of_next_week.getDate() + 7);

        return ["&", [field_name, ">=", start_of_next_week], [field_name, "<", end_of_next_week]];
    }

    if (val === "next_month") {
      const start_of_next_month = new Date(current_date);
            start_of_next_month.setMonth(current_date.getMonth() + 1, 1);
            const end_of_next_month = new Date(start_of_next_month);
            end_of_next_month.setMonth(end_of_next_month.getMonth() + 1, 1);

            return ["&", [field_name, ">=", start_of_next_month], [field_name, "<", end_of_next_month]];
        }

        if (val === "next_quarter") {
            const start_of_this_quarter = new Date(current_date);
            start_of_this_quarter.setMonth(Math.floor(start_of_this_quarter.getMonth() / 3) * 3, 1);
            const end_of_next_quarter = new Date(start_of_this_quarter);
            end_of_next_quarter.setMonth(end_of_next_quarter.getMonth() + 3, 0);
            const start_of_next_quarter = new Date(end_of_next_quarter);
            start_of_next_quarter.setMonth(start_of_next_quarter.getMonth() + 1, 1);

            return ["&", [field_name, ">=", start_of_next_quarter], [field_name, "<", end_of_next_quarter]];
        }

        if (val === "next_year") {
            const start_of_next_year = new Date(current_date);
            start_of_next_year.setFullYear(current_date.getFullYear() + 1, 0, 1);
            const end_of_next_year = new Date(start_of_next_year);
            end_of_next_year.setFullYear(end_of_next_year.getFullYear() + 1, 0, 0);

            return ["&", [field_name, ">=", start_of_next_year], [field_name, "<", end_of_next_year]];
        }
    }
    return [domain];
}

/**
 * The "Domain" field allows the user to construct a technical-prefix domain
 * thanks to a tree-like interface and see the selected records in real time.
 * In debug mode, an input is also there to be able to enter the prefix char
 * domain directly (or to build advanced domains the tree-like interface does
 * not allow to).
 */
var TerabitsFieldDomain = AbstractField.extend({
    /**
     * Fetches the number of records which are matched by the domain (if the
     * domain is not server-valid, the value is false) and the model the
     * field must work with.
     */
    specialData: "_fetchSpecialDomain",

    events: _.extend({}, AbstractField.prototype.events, {
        "click .o_domain_show_selection_button": "_onShowSelectionButtonClick",
        "click .o_field_domain_dialog_button": "_onDialogEditButtonClick",
    }),
    custom_events: _.extend({}, AbstractField.prototype.custom_events, {
        domain_changed: "_onDomainSelectorValueChange",
        domain_selected: "_onDomainSelectorDialogValueChange",
        open_record: "_onOpenRecord",
    }),
    /**
     * @constructor
     * @override init from AbstractField
     */
    init: function () {
        this._super.apply(this, arguments);
         
        this.inDialog = !!this.nodeOptions.in_dialog;
        this.fsFilters = this.nodeOptions.fs_filters || {};
 
        this.className = "o_field_domain";
        if (this.mode === "edit") {
            this.className += " o_edit_mode";
        }
        if (!this.inDialog) {
            this.className += " o_inline_mode";
        }

        this._setState();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * A domain field is always set since the false value is considered to be
     * equal to "[]" (match all records).
     *
     * @override
     */
    isSet: function () {
        return true;
    },
    /**
     * @override isValid from AbstractField.isValid
     * Parsing the char value is not enough for this field. It is considered
     * valid if the internal domain selector was built correctly and that the
     * query to the model to test the domain did not fail.
     *
     * @returns {boolean}
     */
    isValid: function () {
        return (
            this._super.apply(this, arguments)
            && (!this.domainSelector || this.domainSelector.isValid())
            && this._isValidForModel
        ) || this.domainSelector.rawDomain.includes("date_filter");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override _render from AbstractField
     * @returns {Promise}
     */
    _render: function () {
        // If there is no model, only change the non-domain-selector content
        if (!this._domainModel) {
            this._replaceContent();
            return Promise.resolve();
        }

        // Convert char value to array value
        var value = this.value || "[]";

        // Create the domain selector or change the value of the current one...
        var def;
         
        if (!this.domainSelector) {
            this.domainSelector = new DomainSelector.TerabitsDomainSelector(this, this._domainModel, value, {
                readonly: this.mode === "readonly" || this.inDialog,
                filters: this.fsFilters,
                debugMode: config.isDebug(),
            });
            def = this.domainSelector.prependTo(this.$el);
        } else {
            def = this.domainSelector.setDomain(value);
        }
        // ... then replace the other content (matched records, etc)
        return def.then(this._replaceContent.bind(this));
    },
    /**
     * Render the field DOM except for the domain selector part. The full field
     * DOM is composed of a DIV which contains the domain selector widget,
     * followed by other content. This other content is handled by this method.
     *
     * @private
     */
    _replaceContent: function () {
        if (this._$content) {
            this._$content.remove();
        }
        this._$content = $(qweb.render("TerabitsFieldDomain.content", {
            hasModel: !!this._domainModel,
            isValid: !!this._isValidForModel,
            nbRecords: this.record.specialData[this.name].nbRecords || 0,
            inDialogEdit: this.inDialog && this.mode === "edit",
            isDateFilter: this.value[0] && this.value[0]?.length>0? this.value[0][1] == "date_filter": false
        }));
        this._$content.appendTo(this.$el);
    },

    /**
     * @override _reset from AbstractField
     * Check if the model the field works with has (to be) changed.
     *
     * @private
     */
    _reset: function () {
        this._super.apply(this, arguments);
        var oldDomainModel = this._domainModel;
        this._setState();
        if (this.domainSelector && this._domainModel !== oldDomainModel) {
            // If the model has changed, destroy the current domain selector
            this.domainSelector.destroy();
            this.domainSelector = null;
        }
    },
    /**
     * Sets the model the field must work with and whether or not the current
     * domain value is valid for this particular model. This is inferred from
     * the received special data.
     *
     * @private
     */
    _setState: function () {
        var specialData = this.record.specialData[this.name];
        this._domainModel = specialData.model;
        this._isValidForModel = (specialData.nbRecords !== false);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the "Show selection" button is clicked
     * -> Open a modal to see the matched records
     *
     * @param {Event} e
     */
    _onShowSelectionButtonClick: function (e) {
        e.preventDefault();
        const newDomain = [];
        Domain.prototype
          .stringToArray(this.value, this.record.evalContext)
          .forEach((ele) => {
            if (ele.includes("date_filter")) {
              calculateDate(ele).forEach((el) =>
                newDomain.push(el)
              );
            } else {
              newDomain.push(ele);
            }
          });
        new view_dialogs.SelectCreateDialog(this, {
            title: _t("Selected records"),
            res_model: this._domainModel,
            context: this.record.getContext({fieldName: this.name, viewType: this.viewType}),
            domain: JSON.stringify(newDomain),
            no_create: true,
            readonly: true,
            disable_multiple_selection: true,
        }).open();
    },
    /**
     * Called when the "Edit domain" button is clicked (when using the in_dialog
     * option) -> Open a DomainSelectorDialog to edit the value
     *
     * @param {Event} e
     */
    _onDialogEditButtonClick: function (e) {
        e.preventDefault();
        new DomainSelectorDialog(this, this._domainModel, this.value || "[]", {
            readonly: this.mode === "readonly",
            filters: this.fsFilters,
            debugMode: config.isDebug(),
        }).open();
    },
    /**
     * Called when the domain selector value is changed (do nothing if it is the
     * one which is in a dialog (@see _onDomainSelectorDialogValueChange))
     * -> Adapt the internal value state
     *
     * @param {OdooEvent} e
     */
    _onDomainSelectorValueChange: function (e) {
        if (this.inDialog) return;
        this._setValue(Domain.prototype.arrayToString(this.domainSelector.getDomain()));
    },
    /**
     * Called when the in-dialog domain selector value is confirmed
     * -> Adapt the internal value state
     *
     * @param {OdooEvent} e
     */
    _onDomainSelectorDialogValueChange: function (e) {
        this._setValue(Domain.prototype.arrayToString(e.data.domain));
    },
    /**
     * Stops the propagation of the 'open_record' event, as we don't want the
     * user to be able to open records from the list opened in a dialog.
     *
     * @param {OdooEvent} event
     */
    _onOpenRecord: function (event) {
        event.stopPropagation();
    },
});

var TerabitsFieldDomain2 = TerabitsFieldDomain.extend({
    _replaceContent: function () {
        if (this._$content) {
            this._$content.remove();
        }
        this._$content = $(qweb.render("TerabitsFieldDomain.content2", {
            hasModel: !!this._domainModel,
            isValid: !!this._isValidForModel,
            nbRecords: this.record.specialData[this.name].nbRecords || 0,
            inDialogEdit: this.inDialog && this.mode === "edit",
            isDateFilter: this.value[0] && this.value[0]?.length>0? this.value[0][1] == "date_filter": false
        }));
        this._$content.appendTo(this.$el);
    },

    _render: function () {
        // If there is no model, only change the non-domain-selector content
        if (!this._domainModel) {
            this._replaceContent();
            return Promise.resolve();
        }

        // Convert char value to array value
        var value = this.value || "[]";

        // Create the domain selector or change the value of the current one...
        var def;
         
        if (!this.domainSelector) {
            this.domainSelector = new DomainSelector.TerabitsDomainSelector2(this, this._domainModel, value, {
                readonly: this.mode === "readonly" || this.inDialog,
                filters: this.fsFilters,
                debugMode: config.isDebug(),
            });
            def = this.domainSelector.prependTo(this.$el);
        } else {
            def = this.domainSelector.setDomain(value);
        }
        // ... then replace the other content (matched records, etc)
        return def.then(this._replaceContent.bind(this));
    },

    _onDialogEditButtonClick: function (e) {
        e.preventDefault();
        new DomainSelectorDialog2(this, this._domainModel, this.value || "[]", {
            readonly: this.mode === "readonly",
            filters: this.fsFilters,
            debugMode: config.isDebug(),
        }).open();
    },
})

return {
    TerabitsFieldDomain: TerabitsFieldDomain,
    TerabitsFieldDomain2: TerabitsFieldDomain2
};

});
