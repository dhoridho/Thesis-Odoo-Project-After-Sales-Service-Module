odoo.define('advanced_web_domain_widget.BasicModel', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var localStorage = require('web.local_storage');
var Domain = require('web.Domain');

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

BasicModel.include({

    /**
     * Fetches the number of records associated to the domain the value of the
     * given field represents.
     *
     * @param {Object} record - an element from the localData
     * @param {Object} fieldName - the name of the field
     * @param {Object} fieldInfo
     * @returns {Promise<any>}
     *          The promise is resolved with the fetched special data. If this
     *          data is the same as the previously fetched one (for the given
     *          parameters), no RPC is done and the promise is resolved with
     *          the undefined value.
     */
    _fetchSpecialDomain: function (record, fieldName, fieldInfo) {
        var self = this;
        var context = record.getContext({fieldName: fieldName});
        var domainModel = fieldInfo.options.model;
        if (record.data.hasOwnProperty(domainModel)) {
            domainModel = record._changes && record._changes[domainModel] || record.data[domainModel];
        }
        var domainValue = record._changes && record._changes[fieldName] || record.data[fieldName] || [];

        // avoid rpc if not necessary
        var hasChanged = this._saveSpecialDataCache(record, fieldName, {
            context: context,
            domainModel: domainModel,
            domainValue: domainValue,
        });
        if (!hasChanged) {
            return Promise.resolve();
        } else if (!domainModel) {
            return Promise.resolve({
                model: domainModel,
                nbRecords: 0,
            });
        }

        return new Promise(function (resolve) {
            var evalContext = self._getEvalContext(record);
            const newDomain = [];
            Domain.prototype.stringToArray(domainValue, evalContext)
            .forEach((ele) => {
                if (ele.includes("date_filter")) {
                calculateDate(ele).forEach((el) =>
                    newDomain.push(el)
                );
                } else {
                newDomain.push(ele);
                }
            });
            self._rpc({
                model: domainModel,
                method: 'get_widget_count',
                args: [newDomain],
                context: context
            })
            .then(function (nbRecords) {
                resolve({
                    model: domainModel,
                    nbRecords: nbRecords,
                });
            })
            .guardedCatch(function (reason) {
                var e = reason.event;
                e.preventDefault(); // prevent traceback (the search_count might be intended to break)
                resolve({
                    model: domainModel,
                    nbRecords: 0,
                });
            });
        });
    },
});
});
