odoo.define('equip3_inventory_masterdata.3DViewRenderer', function (require) {
    "use strict";

    var container;
    var scope;

    var stock_3dview = require('stock_3dview.3DViewRenderer');
    stock_3dview.include({
        _addEventHandlers: function() {
            this._super.apply(this, arguments);
            container = document.getElementById( 'threedview_container' );
            $( container ).click( this.onContainerClick );
            scope = this;
            $("#close_location_all_info_icon").click(function(e) {
                e.preventDefault();
                //console.log("Closing window");
                var location = scope.scene.getObjectByName( "mesh" + $("#location_full_info").data("current") );
                $("#location_full_info").data("current", 0).hide();
                $("#frame_location_icon").off("click").hide();
                $("#map_marker_icon").off("click").hide();
                scope.controls.enabled = true;
                scope.render();
                e.stopPropagation();
            });
        },
        onContainerClick: function(event) {
            event.preventDefault();
            var location = scope.findLocation( event );
            if (location) {
                $('#products_stock_data').html('');
                $("#location_full_info")
                    .css({
                        'top': event.clientY - $('#threedview_container').offset().top - 10,
                        'left': event.clientX - $('#threedview_container').offset().left - 10
                        })
                    .data('current', location.userData.location.barcode)
                    .show()
                    ;
                if ( parseInt($("#location_full_info").css("right"), 10 ) < 0 )
                {
                    $("#location_full_info").css('left', event.clientX - $('#threedview_container').offset().left - $("#location_full_info").width() - 30 );
                }
                $('<span class="current_stock"><b>Current Stock: </b></span>').appendTo($('#products_stock_data'));
                _.each(location.userData.location.quants, function(value) {
                    $('<br/><span class="product_location_data ml-3"> - '+
                        '<span class="product_name ml-1">'+ value.name + '</span>' +
                        '<span class="product_qty ml-1"><b>'+ value.on_hand + '</b></span>' +
                        '<span class="uom_name ml-1">' + value.uom_name + ',available</span>' +
                        '<span class="product_qty ml-1"><b>' + value.qty +'</b></span>' +
                        '<span class="uom_name ml-1">' + value.uom_name + '</span>').appendTo($('#products_stock_data'));
                })
                $("#location_name").text(location.userData.location.location);
                $("#occupied_percent").text(location.userData.location.occupied_percent);
                $("#frame_location_icon").show().click( function( event ) {
                    event.preventDefault();
                    scope.camera.position.fromArray( scope._realTo3dvSizes( parseInt(info.camx, 10), -parseInt(info.camy, 10), parseInt(info.camz, 10) ) );
                    scope.target.position.copy(location.position);
                    scope.camera.lookAt(scope.target);
                    scope.controls.target.copy(scope.target.position);
                    scope.controls.update();
                });
                scope.controls.enabled = false;
                scope.render();
            }
        },
    });

});