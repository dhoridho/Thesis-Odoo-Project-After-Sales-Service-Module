odoo.define("app_web_superbar.RangeControlPanelModelExtension", function (require) {
    "use strict";

    const ActionModel = require("web/static/src/js/views/action_model.js");
    const ControlPanelModelExtension = require("web/static/src/js/control_panel/control_panel_model_extension.js");
    const session = require('web.session');
    const time = require('web.time');
    const core = require('web.core');
    const _t = core._t;

    class RangeControlPanelModelExtension extends ControlPanelModelExtension {
        getDomain()  {
            var curr_model_name = localStorage.getItem('curr_model_name')
            if(curr_model_name !== this.config.modelName){
                if($('.app-search-range-date-container').length > 0){
                    $('.app-search-range-date-container').find('input').eq(0).val("")
                    $('.app-search-range-date-container').find('input').eq(1).val("")
                }
            }
            localStorage.setItem('curr_model_name', this.config.modelName);
            const ret = super.getDomain(...arguments);
            var appDomain = this.app_search();
            try {
                _.each(appDomain, function (domain) {
                    ret.push(domain);
                });
            } catch (e) {}
            return ret;
        }
        //返回范围数组
        app_search() {
            var self = this;
            var domain = [];
            // 注意，date和datetime型的处理是不同的，已处理完
            var $search_date = $('.app-search-range-date-container');
            if ($search_date.length) {
                var $sd = $search_date.find('input');
                var start_date = $sd.eq(0).val(),
                    end_date = $sd.eq(1).val(),
                    field = $(document).find('.app_select_field_date').val(),
                    field_type = 'datetime';
                var tz = session.user_context.tz,
                    start_utc,
                    end_utc;

                _.each(self.fields, function (value, key, list) {
                    if (value.name == field) {
                        field_type = value.type;
                        return false;
                    }
                });

                // odoo 14处理时区方式改变，不可用 moment，参考 https://www.cnblogs.com/goloving/p/10514914.html
                moment.locale(tz);
                let _dif = new Date().getTimezoneOffset();
                var l10n = _t.database.parameters;
                if (start_date) {
                    if (field_type === 'date') {
                        //日期类型，无须utc处理
//                        start_date = moment(start_date).utc().format('YYYY-MM-DD HH:mm:ss');
                        start_date = moment(start_date).utc().format('YYYY-MM-DD 00:00:00');
                        domain.push([field, '>=', start_date]);
                    } else {
                        //日期时间，处理utc
                        /*start_date = moment(start_date).format('YYYY-MM-DD HH:mm:ss');
                        start_utc = moment(start_date).utc().format('YYYY-MM-DD HH:mm:ss');*/
                        let a = start_date.split(' ')
                        let b = a[0].split('/')
//                        start_date = b[2]+'-'+b[1]+'-'+b[0]+' '+a[1]
                        start_date = b[2]+'-'+b[0]+'-'+b[1]+' 00:00:00'//+a[1]
                        domain.push([field, '>=', new Date(start_date)]);
                    }
                }
                if (end_date) {
                    if (field_type === 'date') {
//                        end_date = moment(end_date).utc().format('YYYY-MM-DD HH:mm:ss');
                        end_date = moment(end_date).utc().format('YYYY-MM-DD 23:59:59');
                        domain.push([field, '<=', end_date]);
                    } else {
                        //日期时间，处理utc
                        /*end_date = moment(end_date).format('YYYY-MM-DD HH:mm:ss');
                        end_utc = moment(end_date).utc().format('YYYY-MM-DD HH:mm:ss');*/
                        let a = end_date.split(' ')
                        let b = a[0].split('/')
//                        end_date = b[2]+'-'+b[1]+'-'+b[0]+' '+a[1]
                        end_date = b[2]+'-'+b[0]+'-'+b[1]+' 23:59:59'//+a[1]
                        domain.push([field, '<=', new Date(end_date)]);
                    }
                }
            }

            if ($(document).find('.app_select_field_number')) {
                var start_range = $(document).find('.app_start_number').val(),
                    end_range = $(document).find('.app_end_number').val(),
                    range_field = $(document).find('.app_select_field_number').val();

                if (start_range) {
                    domain.push([range_field, '>=', parseInt(start_range)]);
                }
                if (end_range) {
                    domain.push([range_field, '<=', parseInt(end_range)]);
                }
            }
            return domain;
        }
    }
    ActionModel.registry.add("RangeControlPanel", RangeControlPanelModelExtension, 10);

    return RangeControlPanelModelExtension;
});
