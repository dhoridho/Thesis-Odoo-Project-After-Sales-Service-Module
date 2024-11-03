odoo.define('equip3_mining_dashboard.OpenWeatherSite', function(require){
    "use strict";

    var core = require('web.core');
    var AbstractAction = require('web.AbstractAction');

    var OpenWeatherSite = AbstractAction.extend({
        template: 'OpenWeatheSite',
        hasControlPanel: true,

        jsLibs: [
			'https://openweathermap.org/themes/openweathermap/assets/vendor/owm/js/d3.min.js'
		],

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.resId = action.res_id;
        },

        willStart: function () {
            var self = this;
            var openWeatherProm = this._rpc({
                model: 'mining.site.control',
                method: 'get_open_weather_data',
                args: [[this.resId]]
            }).then(function(result){
                self.oWeatherApiKey = result.apikey;
                self.oWeatherUnits = result.units;
                self.oWeatherWidget = result.widget;
                self.oWeatherCity = result.city;
            });
            
            return Promise.all([this._super.apply(this, arguments), openWeatherProm]);
        },

        start: function () {
            var self = this;
			return this._super.apply(this, arguments).then(function(){
                if (self.oWeatherApiKey){
                    var script = document.createElement('script');
                    script.append(`window.myWidgetParamSite ? window.myWidgetParamSite : window.myWidgetParamSite = []; 
                    window.myWidgetParamSite.push({
                        id: ` + self.oWeatherWidget + `,
                        cityid: `+ self.oWeatherCity +`,
                        appid: '` + self.oWeatherApiKey + `',
                        units: '` + self.oWeatherUnits + `',
                        containerid: 'openWeatherSiteWidget',
                    });
                    var script = document.createElement('script');
                    script.async = true;
                    script.charset = "utf-8";
                    script.src = "/equip3_mining_dashboard/static/src/lib/open_weather/weather-widget-generator.js";
                    var s = document.getElementsByTagName('script')[0];
                    s.parentNode.insertBefore(script, s);`);

                    if (self.$el.find('.o_no_apikey').length){
                        self.$el.find('.o_no_apikey').remove();
                    }
                    self.$el.append(script);
                } else {
                    self.$el.append('<div class="o_no_apikey">Please provide Open Weather API Key in the settings!</div>')
                }
			});
	    },

        destroy: function () {
            if ($('#openWeatherSiteScript').length){
                $('#openWeatherSiteScript').remove();
            }
            this._super.apply(this, arguments);
        },
    });

    core.action_registry.add('open_weather_site', OpenWeatherSite);
    return OpenWeatherSite;
});