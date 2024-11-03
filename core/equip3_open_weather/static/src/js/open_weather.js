odoo.define('equip3_open_weather.openWeather', function(require){
    "use strict";

    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');

    var OpenWeather = Widget.extend({
	    template: 'OpenWeather',

        jsLibs: [
			'https://openweathermap.org/themes/openweathermap/assets/vendor/owm/js/d3.min.js'
		],

        init: function(parent, params){
            this._super.apply(this, arguments);
            this.containerId = params.containerId;
            this.identicalIds = [];
        },

        willStart: function () {
            var self = this;
            var openWeatherProm = this._getData().then(function(result){
                self._loadData(result);
                self._initializeParams();
            });
            
            return Promise.all([this._super.apply(this, arguments), openWeatherProm]);
        },

        start: function () {
            this.$el = $(this.el);
            this._replaceIdenticalIds();
            var self = this;
			return this._super.apply(this, arguments).then(function(){
                self._attachScript();
                setTimeout(function(){
                    self._revertIdenticalIds();
                }, 1000);
			});
	    },

        destroy: function(){
            this._detachScript();
            this._removeParam();
            this._super.apply(this, arguments);
        },

        _removeParam: function(){
            var self = this;
            let index = _.findIndex(window.myWidgetParam, (widget) => {
                return widget.containerid === self.containerId;
            });
            if (index >= 0){
                window.myWidgetParam.splice(index, 1);
            }
        },

        _replaceIdenticalIds: function(){
            var self = this;
            _.each(['graphic', 'graphic1', 'graphic2', 'graphic3'], function(graphicId){
                document.querySelectorAll("[id='" + graphicId + "']").forEach(function(el){
                    let $el = $(el);
                    $el.attr('id',  graphicId + '_old');
                    self.identicalIds.push($el);
                });
            });
        },

        _revertIdenticalIds: function(){
            _.each(this.identicalIds, function($el){
                $el.attr('id', $el.attr('id').replace('_old', ''));
            });
        },

        _attachScript: function(){
            this._detachScript();
            if (this.oWeatherApiKey){
                var script = document.createElement('script');
                script.setAttribute('name', 'open-weather-generator');
                script.append(`var script = document.createElement('script');
                script.async = true;
                script.charset = "utf-8";
                script.src = "/equip3_open_weather/static/src/lib/weather-widget-generator.js";
                var s = document.getElementsByTagName('script')[0];
                s.parentNode.insertBefore(script, s);`);

                if (this.$el.find('.o_no_apikey').length){
                    this.$el.find('.o_no_apikey').remove();
                }
                $('head').append(script);
            } else {
                this.$el.append('<div class="o_no_apikey"><b>Please provide Open Weather API Key in the settings!</b></div>')
            }
        },

        _detachScript: function(){
            let $script = $('script[name="open-weather-generator"]');
            if ($script.length){
                $script.remove();
            }
        },

        _rpcData: function(){
            return {
                model: 'res.config.settings',
                method: 'get_open_weather_data'
            }
        },

        _getData: function(){
            return this._rpc(this._rpcData());
        },

        _loadData: function(result){
            this.oWeatherApiKey = result.apikey;
            this.oWeatherUnits = result.units;
            this.oWeatherWidget = result.widget;
            this.oWeatherCity = result.city;
        },

        _initializeParams: function(){
            var self = this;
            window.myWidgetParam ? window.myWidgetParam : window.myWidgetParam = [];
            let values = {
                id: this.oWeatherWidget,
                cityid: this.oWeatherCity,
                appid: this.oWeatherApiKey,
                units: this.oWeatherUnits,
                containerid: this.containerId,
            };
            let param = _.find(window.myWidgetParam, function(p){return p.containerid === self.containerId;});
            if (param){
                Object.assign(param, values);
            } else {
                window.myWidgetParam.push(values);
            }
        }
    });

    var OpenWeatherSystray = Widget.extend({
        template: 'equip3_open_weather.systray.OpenWeather',

        on_attach_callback() {
            this.$content = this.$el.find('.o_open_weather_systray_dropdown_items');
            this.$content.html('');
            this.openWeather = new OpenWeather(this, {containerId: 'openWeatherSystray'});
            this.openWeather.appendTo(this.$content);
        }
    });

    SystrayMenu.Items.push(OpenWeatherSystray);

	return {
        OpenWeather: OpenWeather,
        OpenWeatherSystray: OpenWeatherSystray
    };
});