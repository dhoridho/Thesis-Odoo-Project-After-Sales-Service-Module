odoo.define('equip3_property_masterdata.property_tracking_asset_new', function(require){

    "use strict";
    var ajax = require("web.ajax");
    var sync = true
    let mapDiv;

    $(".o_control_panel").remove();
    clearInterval(window.get_property);

    function propertyOnClickTable(ev){
    };

    function get_property_asset(){
        ajax.jsonRpc("/asset_property", "call", {}).then(function(data){
            let map;
            let locations = [];
            let trElement = ""
            let trElementAll = ""
            let trElementSaleable = ""
            let trElementSold = ""
            let trElementReserved = ""
            let trElementRentable = ""
            let saleable_count = 0
            let sold_count = 0
            let reserved_count = 0
            let rentable_count = 0
            let s_text = ''
            let markers = ''

            for (let i = 0; i < data.length; i++) {
               var id = data[i]['id']
               var idString = id.toString();

               trElement = `<div class="row vehicle_row" data-plate="${data[i]['name']}" data-longitude="${data[i]['lat']}" data-latitude="${data[i]['lng']}" data-status="${data[i]['state']}" style="padding: 0px; cursor: pointer; height:auto; box-sizing: border-box;box-shadow: 0px 0px 8px rgb(0 0 0 / 15%);border-radius: 5px;overflow: hidden;margin-bottom: 10px;">
                    <a id="${data[i]['id']}"href="/property-detail/${data[i]['id']}" style="display:flex; color: black; width:100%;">
                    <div class="col-4 display_name">
                        <b style="color: black">${data[i]['name']}</b>
                    </div>
                    <div class="col-4">
                        ${data[i]['state']}
                    </div>`
//                    <div class="col-4">
//                        ${data[i]['property_book_for']}
//                    </div>
//                </div>`
                if (data[i]['property_book_for'] == 'Sale'){
                trElement += `<div class="col-4">
                                <b style="color: red">${data[i]['property_book_for']}</b>
                             </div>`
                } else {
                trElement += `<div class="col-4">
                                <b style="color: green">${data[i]['property_book_for']}</b>
                             </div>`
                }
                trElement += `</a></div>`

                if(data[i]['state'] == 'Sold'){
                  trElementSold += trElement
                  sold_count += 1
                }
                else if(data[i]['state'] == 'Saleable'){
                  trElementSaleable += trElement
                  saleable_count += 1
                }
                else if(data[i]['state'] == 'Reserve'){
                  trElementReserved += trElement
                  reserved_count += 1
                }
                else if(data[i]['state'] == 'Rentable'){
                  trElementRentable += trElement
                  rentable_count += 1
                }

                trElementAll += trElement

                locations.push({
                    'lat': parseFloat(data[i]['lat']),
                    'lng': parseFloat(data[i]['lng']),
                })
            }
            $("#property-all-table").html(trElementAll)
            $("#property-reserved-table").html(trElementReserved)
            $("#property-rentable-table").html(trElementRentable)
            $("#property-saleble-table").html(trElementSaleable)
            $("#property-sold-table").html(trElementSold)

            let all_nav = $("li.nav-item").find("a");
            all_nav.each(function(){
              let $nav = $(this);

              if($nav.html() == 'Saleable'){
                $nav.html(`<span>Saleable</span> (${saleable_count})`)
              }
              if($nav.html() == 'Sold'){
                $nav.html(`<span>Sold</span> (${sold_count})`)
              }
              if($nav.html() == 'Reserved'){
                $nav.html(`<span>Reserved</span> (${reserved_count})`)
              }
              if($nav.html() == 'Rentable'){
                $nav.html(`<span>Rentable</span> (${rentable_count})`)
              }
            });

            //  Init Mape here
            function initMap() {
                var myLatLng = { lat: -6.121435, lng: 106.774124 };
                var zoom = 8

                const map = new google.maps.Map($("#map")[0], {
                    zoom: zoom,
                    center: myLatLng,
                    mapId: "4504f8b37365c3d0",
                });
                const infoWindow = new google.maps.InfoWindow({
                  content: "",
                  disableAutoPan: true,
                });

                for (let i = 0; i < data.length; i++) {

                   if(data[i]['state']== 'Rentable'){
                      console.log('state',i)
                      const propertyTagImg = document.createElement("img");
                      propertyTagImg.className = "property_icon";
                      propertyTagImg.style.width='50px';
                      propertyTagImg.style.height='50px';
                      propertyTagImg.src =
                            "/equip3_property_masterdata/static/src/img/green_house.png";
                      const propertyTagMarkerView = new google.maps.marker.AdvancedMarkerView({
                        map,
                        position: {
                          'lat': (Number(data[i]['lat'])),
                          'lng': (Number(data[i]['lng']))
                        },
                        content: propertyTagImg,
                      });
                  }

                  else if(data[i]['state'] == 'Saleable'){
                      const propertyTagImg = document.createElement("img");
                      propertyTagImg.className = "property_icon";
                      propertyTagImg.style.width='50px';
                      propertyTagImg.style.height='50px';
                      propertyTagImg.src =
                            "/equip3_property_masterdata/static/src/img/green_house.png";
                      const propertyTagMarkerView = new google.maps.marker.AdvancedMarkerView({
                        map,
                        position: {
                          'lat': (Number(data[i]['lat'])),
                          'lng': (Number(data[i]['lng']))
                        },
                        content: propertyTagImg,
                      });
                  }

                  else if (data[i]['state'] == 'Sold') {
                      const propertyTagImg = document.createElement("img");
                      propertyTagImg.className = "property_icon";
                      propertyTagImg.style.width='50px';
                      propertyTagImg.style.height='50px';
                      propertyTagImg.src =
                            "/equip3_property_masterdata/static/src/img/red_house.png";
                      const propertyTagMarkerView = new google.maps.marker.AdvancedMarkerView({
                        map,
                        position: {
                          'lat': (Number(data[i]['lat'])),
                          'lng': (Number(data[i]['lng']))
                        },
                        content: propertyTagImg,
                    });

                  }

                  else if (data[i]['state'] == 'Reserve') {
                      const propertyTagImg = document.createElement("img");
                      propertyTagImg.className = "property_icon";
                      propertyTagImg.style.width='50px';
                      propertyTagImg.style.height='50px';
                      propertyTagImg.src =
                            "/equip3_property_masterdata/static/src/img/red_house.png";
                      const propertyTagMarkerView = new google.maps.marker.AdvancedMarkerView({
                        map,
                        position: {
                          'lat': (Number(data[i]['lat'])),
                          'lng': (Number(data[i]['lng']))
                        },
                      content: propertyTagImg,
                    });
                  }
                  }
                }

            initMap();
        })
    }

    $(document).ready(function(){
      console.log("$(document).find('#map')",$(document).find('#map'));
      mapDiv = $(document).find('#map')[0];
      get_property_asset();
    })

})