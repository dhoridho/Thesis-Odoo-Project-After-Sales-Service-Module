odoo.define('equip3_crm_tracking.CrmSalesTrackingHistory', function(require){

    var FormRenderer = require('web.FormRenderer');
    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    var markerColors = {
        0:"http://maps.google.com/mapfiles/ms/icons/red-dot.png",
        1:"http://maps.google.com/mapfiles/ms/icons/green-dot.png",
        2:"http://maps.google.com/mapfiles/ms/icons/blue-dot.png",
        3:"http://maps.google.com/mapfiles/ms/icons/yellow-dot.png",
        4:"http://maps.google.com/mapfiles/ms/icons/pink-dot.png",
        5:"http://maps.google.com/mapfiles/ms/icons/orange-dot.png",
        6:"http://maps.google.com/mapfiles/ms/icons/purple-dot.png",
        };
    var colors = ["#FD7567", "#00E64D", "#6991FD", "#FDF569", "#E661AC", "#FF9900","#8E67FD"];


    var sales_ids = new Array();
    var currentIds = [];

    var salesTrackingController = FormController.extend({
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.$el.find('.o_control_panel').hide();
            });
        },

        _confirmChange: function (id, fields, e) {
            currentIds = [];
            this._super.apply(this, arguments);
            const PersonData = document.getElementsByClassName("badge badge-pill  o_tag_color_0");
            var CurrentIds = new Array();
            for (var i=0; i < PersonData.length; i++) {
                var node = PersonData[i];
                const sale_id = node.getAttribute('data-id');
                CurrentIds.push(parseInt(sale_id));
            }
            currentIds = CurrentIds;
            this.renderer._updateMaps()

        },

        _onFieldChanged: function (ev) {
            try{
                var operations = ev.data.changes.sales_ids.operation
                ev.stopPropagation();
                const PersonData = document.getElementsByClassName("badge badge-pill  o_tag_color_0");
                var CurrentIds = new Array();
                for (var i=0; i < PersonData.length; i++) {
                    var node = PersonData[i];
                    const sale_id = node.getAttribute('data-id');
                    CurrentIds.push(parseInt(sale_id));
                }
                }catch(error){
                    console.log("error : ",error)}
            this._super.apply(this, arguments);
            var changedData = {};
            if ('sales_ids' in ev.data.changes){
                changedData = {fieldName: 'sales_ids', fieldValue: ev.data.changes.sales_ids};
            } else if ('date' in ev.data.changes){
                changedData = {fieldName: 'date', fieldValue: ev.data.changes.date};
            }
            if (changedData){
                this.renderer._updateValues(changedData);
            }
        },

        canBeDiscarded: function (recordID) {
            return Promise.resolve(false);
        }
    });
    
    var salesTrackingRenderer = FormRenderer.extend({
        init: function (parent, state, params) {
            this._super.apply(this, arguments);

            this.salesId = false;
            this.date = false;

            this.maps = null;
            this.markers = [];
            this.polyLine = new google.maps.Polyline({
                strokeColor: '#6991FD',
            });
        },

        willStart: function(){
            var self = this;
            currentIds = [];
            var crmModel = this._rpc({
                        model: 'crm.sales.tracking.history',
                        method: 'search_read',
                        fields: ['name','sales_ids','date']
                    }).then(function(d){
                    const salesperson_id = d[0]['sales_ids']
                    for(i=0;i<salesperson_id.length;i++){
                    currentIds.push(salesperson_id[i])
                    }});

            var historyDef = this._rpc({
                model: 'crm.salesperson.tracking',
                method: 'search_read'
            })
            .then(function (result) {
                _.each(result, function(history){
                    var historyDate = new Date(history.current_datetime);
                    historyDate.setHours(0, 0, 0, 0);
                    history.timestamp = historyDate.getTime();

                    self.markers.push({
                        history: history,
                        marker: new google.maps.Marker({
                            position: new google.maps.LatLng(
                                parseFloat(history.latitude), 
                                parseFloat(history.longitude)
                            ),
                            title: history.location_name,
                            icon: {
                            url: "http://maps.google.com/mapfiles/ms/icons/red-dot.png"
                            },
                        })
                    });
                });
    
            });
            return Promise.all([this._super.apply(this, arguments), historyDef]);
        },

        _renderView: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var mapOptions = {
                    zoom: 10,
                    mapTypeId: google.maps.MapTypeId.ROADMAP
                };
//                if (self.markers.length){
//                    mapOptions.center = new google.maps.LatLng(
//                        self.markers[0].history.latitude,
//                        self.markers[0].history.longitude
//                    );
//                }
                var $mapContainer = self.$el.find('#google_maps_container');
                self.maps = new google.maps.Map($mapContainer.get(0), mapOptions);

                var salesId = false;
                if (self.state.data.sales_ids){
                    salesId = self.state.data.sales_ids.res_id;
                }
                self.salesId = salesId;
                self.date = self.state.data.date;
                self._updateMaps();
            });
        },

        _updateValues: function(data){
            if (data.fieldName === 'sales_ids'){
                this.salesId = data.fieldValue.ids.id;
                if(typeof data.fieldValue.ids.id == "number"){
                    sales_ids.push(data.fieldValue.ids.id)
                }
            } else if (data.fieldName === 'date'){
                this.date = data.fieldValue;
            } else {
                return;
            }
        },

        _updateMaps: function(){
            this.maps = null;
            var $mapContainer_new = this.$el.find('#google_maps_container');
            var self = this;
            this.seperatedMarkers = false;
            var coordinates = false;
            var markers = false;
            this.polyLine = null;
            var timestamp = false;
            if (this.date){
                timestamp = this.date.toDate();
                timestamp.setHours(0, 0, 0, 0);
                timestamp = timestamp.getTime();
            }

            _.each(this.markers, function(marker){
                marker.marker.setMap(null);
            });
            this.seperatedMarkers = [];
            var markers = [];
            for (i = 0; i<currentIds.length; i++){

                var filteredMarker = _.filter(this.markers, function(marker){
                    return marker.history.sales_person[0] == currentIds[i] && marker.history.timestamp === timestamp;
                    });
                this.seperatedMarkers.push(filteredMarker);
                for (j = 0;j < filteredMarker.length;j++){
                    filteredMarker[j].marker.icon.url = markerColors[i]
                    markers.push(filteredMarker[j])
                };

            };
            var mapOptions_new = {
                        zoom: 12,
                        mapTypeId: "roadmap",
                    };
            var map = new google.maps.Map($mapContainer_new.get(0), mapOptions_new);
            if (!markers.length){
                this.maps = map;
            }
            var latlngbounds = new google.maps.LatLngBounds();

            var service = new google.maps.DirectionsService();
            var polyPath = new google.maps.MVCArray();
            for (var i = 0; i < markers.length; i++) {
                var marker = markers[i].marker;
                var history = markers[i].history;
                marker.setMap(map);
                latlngbounds.extend(marker.position);

                var infowindow = new google.maps.InfoWindow({
                    content: history.location_name
                });

                google.maps.event.addListener(marker, "click", function(e) {
                    infowindow.open(map, marker);
                });
            }
            var coordinates = new Array();
            for(var i=0;i<this.seperatedMarkers.length;i++){
                    var data = this.seperatedMarkers[i];
                    var separatedCoordinates = new Array();
                    for(j=0;j<data.length;j++){
                    var history = data[j].history;
                    var latitude = history.latitude;
                    var longitude = history.longitude;
                    separatedCoordinates.push({lat: parseFloat(latitude),lng: parseFloat(longitude)})
                    }
                    coordinates.push(separatedCoordinates);
            };
            for(var i=0;i<coordinates.length;i++){
            this.polyLine = new google.maps.Polyline({
                path: coordinates[i],
                geodesic: true,
                strokeColor:colors[i],
                strokeOpacity: 1.0,
                strokeWeight: 2,
              });
              this.polyLine.setMap(map);
              }
            if (markers.length){
            map.setCenter(new google.maps.LatLng({lat: parseFloat(markers[0].history.latitude), lng: parseFloat(markers[0].history.longitude)}));
            }else{
            map.setCenter(latlngbounds.getCenter());
            }
        }
    });
    
    var salesTrackingView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Renderer: salesTrackingRenderer,
            Controller: salesTrackingController
        }),
    });
    
    viewRegistry.add('crm_sales_tracking_history', salesTrackingView);
    
    return {
        salesTrackingRenderer: salesTrackingRenderer,
        salesTrackingView: salesTrackingView
    };
});