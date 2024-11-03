odoo.define('equip3_crm_operation.FieldMap', function(require) {
"use strict";

var core = require('web.core');
var AbstractField = require('web.AbstractField');
var registry = require('web.field_registry');

var FieldMap = AbstractField.extend({
    template: 'FieldMap',
    start: function() {
        var self = this;

        this.map = new google.maps.Map(this.el, {
            center: {lat:0,lng:0},
            zoom: 0,
            disableDefaultUI: true,
        });
        this.marker = new google.maps.Marker({
            position: {lat:0,lng:0},
        });

        this.map.addListener('click', function(e) {
            if(!self.mode === 'readonly' && self.marker.getMap() == null) {
                self.marker.setPosition(e.latLng);
                self.marker.setMap(self.map);
                self._setValue(JSON.stringify({position:self.marker.getPosition(),zoom:self.map.getZoom()}));
            }
        });
        this.map.addListener('zoom_changed', function() {
            if(!self.mode === 'readonly' && self.marker.getMap()) {
                self._setValue(JSON.stringify({position:self.marker.getPosition(),zoom:self.map.getZoom()}));
            }
        });
        this.marker.addListener('click', function() {
            if(!self.mode === 'readonly') {
                self.marker.setMap(null);
                self._setValue(false);
            }
        });
        this.marker.addListener('dragend', function() {
            self._setValue(JSON.stringify({position:self.marker.getPosition(),zoom:self.map.getZoom()}));
        });
        this.getParent().$('a[data-toggle="tab"]').on('shown.bs.tab', function() {
            self.trigger('resize');
        });
        this.getParent().on('attached', this.getParent(), function() {
            self.trigger('resize');
        });
        this.on('change:effective_readonly', this, this.update_mode);
        this.on('resize', this, this._toggle_label);
        this.update_mode();
        this._super();
    },
    _render: function () {
        if(this.value) {
            this.marker.setPosition(JSON.parse(this.value).position);
            this.map.setCenter(JSON.parse(this.value).position);
            this.map.setZoom(JSON.parse(this.value).zoom);
            this.marker.setMap(this.map);
        } else {
            this.marker.setPosition({lat:0,lng:0});
            this.map.setCenter({lat:0,lng:0});
            this.map.setZoom(2);
            this.marker.setMap(null);
        }
    },
    update_mode: function() {
        if(this.mode == 'readonly') {
            this.map.setOptions({
                disableDoubleClickZoom: true,
                draggable: false,
                scrollwheel: false,
            });
            this.marker.setOptions({
                draggable: false,
                cursor: 'default',
            });
        } else {
            this.map.setOptions({
                disableDoubleClickZoom: false,
                draggable: true,
                scrollwheel: true,
            });
            this.marker.setOptions({
                draggable: true,
                cursor: 'pointer',
            });
        }
    },
    _toggle_label: function() {
        this._super();
        google.maps.event.trigger(this.map, 'resize');
    },
});

registry.add('map', FieldMap);

return {
    FieldMap: FieldMap,
};

});