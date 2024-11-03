odoo.define('equip3_asset_fsm_tracking.asset_tracking', function(require){
    "use strict";
    var ajax = require("web.ajax");
    var sync = true

    // remove control panel for clean view
    $(".o_control_panel").remove();
    clearInterval(window.get_vehicle);

    // vehicle assets
    // function get_vehicle_asset(){
    //     ajax.jsonRpc("/asset", "call", {}).then(function(data){
    //         let map;
    //         let locations = [];
    //         let locations_rand = [
    //             {lat: -6.198445981556965, lng:106.90584745102132},
    //             {lat: -6.2336003195126635, lng:106.89829435087425},
    //             {lat: -6.238037107627609, lng:106.8443926816431},
    //             {lat: -6.223361434525296, lng:106.79770078982503},
    //             {lat: -6.249640837389649, lng:106.77229490751226},
    //             {lat: -6.21073320161295, lng:106.75821867542004},
    //             {lat: -6.210050585794067, lng:106.87220182309358},
    //             {lat: -6.158510542770864, lng:106.80216398536646},
    //             {lat: -6.139395080647239, lng:106.88387479604809},
    //             {lat: -6.233941612238805, lng:106.95906247478456},
    //             {lat: -6.249374429885525, lng:106.80537672660833},
    //             {lat: -6.202107608187848, lng:106.77157041079003},
    //             {lat: -6.198523806612542, lng:106.77500363812959},
    //             {lat: -6.197499858832934, lng:106.78187009280872},
    //             {lat: -6.2097871009452525, lng:106.763845649276},
    //             {lat: -6.1829937186291675, lng:106.80779095922243},
    //         ]

    //         data.forEach((element) => {
    //             const trElement = $("<tr></tr>");
    //             trElement.attr("data-id", element.id);
    //             trElement.append($("<td></td>").attr("class", "display_name").text(element.display_name));
    //             trElement.append($("<td></td>").text("4 Hours"));
    //             trElement.append($("<td></td>").text("Active"));
    //             locations.push(locations_rand[Math.floor(Math.random() * (locations_rand.length + 1))])
    //             $("#vehicle-all-table>tbody").append(trElement)
    //         });

    //         function initMap(){
    //             map = new google.maps.Map(document.getElementById('map'), {
    //                 center: { lat: -6.210391893814135, lng: 106.84542264984498 },
    //                 zoom: 12
    //             });

    //             const markers = locations.map((position, i)=>{
    //                 const marker = new google.maps.Marker({
    //                     position,
    //                     map: map
    //                 })
    //                 return marker;
    //             })
    //         }
    //         initMap();
    //     })
    // }


    function get_vehicle_asset(){
        if (!$('#asset_tracking_page').length){
          return;
        }
        ajax.jsonRpc("/asset", "call", {}).then(function(data){
            console.log(data)
            // Load vehicle data 
            let map;
            let locations = [];
            let trElement = ""
            let trElementAll = ""
            let trElementOffline = ""
            let trElementOnline = ""
            let online_count = 0
            let offline_count = 0
            let s_text = ''
            let live_status = ''
            const batchTrack = document.getElementById("licence_plate");
            for (let i = 0; i < _.size(data['status']); i++) {
                const newOption = document.createElement("option");
                newOption.value = data['status'][i]['license_plate'];
                newOption.text = data['status'][i]['license_plate'];
                batchTrack.appendChild(newOption);
                // text += cars[i] + "<br>";
                // console.log(data[i]['vehicle_name'])
                // const trElement = $("<tr></tr>");
                // trElement.attr("data-id", data[i]['id']);
                // trElement.append($("<td></td>").attr("class", "display_name").text(data[i]['license_plate']));
                // trElement.append($("<td></td>").text(timeSince(data[i]['last_data'])));

                var from_local = localStorage.getItem('load_single_vehicle');
                var plate_from_ls = localStorage.getItem('plate');
                if(from_local){
                  if (plate_from_ls == data['status'][i]['license_plate']){
                    localStorage.setItem('latitude', data['status'][i]['latitude']);
                    localStorage.setItem('longitude', data['status'][i]['longitude']);
                  }
                }


                
                if(data['status'][i]['status'] == 'Parking'){
                  // trElement.append($("<td></td>").attr("class", "text-danger").text(data[i]['status']));
                  s_text = `<span class="text-danger">${data['status'][i]['status']}</span>`
                  live_status = `<b style="color: black">${timeAgo(data['speed'][i]['last_data'])}</b>
                  `
                  
                } else if (data['status'][i]['status'] == 'Moving'){
                    // trElement.append($("<td></td>").attr("class", "text-success").text(data[i]['status']));
                    s_text = `<span class="text-success">${data['status'][i]['status']}</span>`
                    // let obj = data['speed'].find(obj => obj.license_plate == data['status'][i]['license_plate']);
                    // console.log("find 'x'", filterIt(data['speed'],"351510092821985"));
                    live_status = `<b style="color: black">${data['speed'][i]['speed']} Kmph</b>`
                }
                else if (data['status'][i]['status'] == 'Offline'){
                  // trElement.append($("<td></td>").attr("class", "text-muted").text(data[i]['status']));
                  s_text = `<span class="text-muted">${data['status'][i]['status']}</span>`
                  live_status = `<b style="color: black">${timeAgo(data['speed'][i]['last_data'])}</b>
                  `
                }
                else if (data['status'][i]['status'] == 'Idle'){
                  s_text = `<span style="color: #b0cf06;">${data['status'][i]['status']}</span>`
                  live_status = `<b style="color: black">${timeAgo(data['speed'][i]['last_data'])}</b>
                  `
                } else{
                  s_text = `<span>${data['status'][i]['status']}</span>`
                  live_status = `<b style="color: black">${timeAgo(data['speed'][i]['last_data'])}</b>
                  `
                }

                trElement = `<div class="row vehicle_row" data-plate="${data['status'][i]['license_plate']}" data-longitude="${data['status'][i]['longitude']}" data-latitude="${data['status'][i]['latitude']}" data-status="${data['status'][i]['status']}" style="padding: 4.5px; cursor: pointer;height: 30px;box-sizing: border-box;box-shadow: 0px 0px 8px rgb(0 0 0 / 15%);border-radius: 5px;overflow: hidden;margin-bottom: 10px;">
                    <div class="col-4 display_name">
                        <b style="color: black">${data['status'][i]['license_plate']}</b>
                    </div>
                    <div class="col-4">
                        ${live_status}
                    </div>
                    <div class="col-4">
                        ${s_text}
                    </div>
                </div>`
                
                // console.log(trElement)

                

                if(data['status'][i]['status'] == 'Offline'){
                  trElementOffline += trElement
                  offline_count += 1
                }else{
                  trElementOnline += trElement
                  online_count += 1
                }
                trElementAll += trElement

                locations.push({
                    'lat': parseFloat(data['status'][i]['latitude']),
                    'lng': parseFloat(data['status'][i]['longitude']),
                })
            }
            // console.log(locations)
            $("#vehicle-all-table").html(trElementAll)
            $("#vehicle-online-table").html(trElementOnline)
            $("#vehicle-offline-table").html(trElementOffline)

            // Set Counter
            let all_nav = $("li.nav-item").find("a");
            all_nav.each(function(){ 
              let $nav = $(this);
              if($nav.html() == 'Online'){
                $nav.html(`<span>Online</span> (${online_count})`)
              }
              if($nav.html() == 'Offline'){
                $nav.html(`<span>Offline</span> (${offline_count})`)
              }
            });
            


            // function initMap(){
            //     map = new google.maps.Map(document.getElementById('map'), {
            //         center: { lat: -6.210391893814135, lng: 106.84542264984498 },
            //         zoom: 4
            //     });

            //     const markers = locations.map((position, i)=>{
            //         const marker = new google.maps.Marker({
            //             position,
            //             map: map,
            //         })
            //         return marker;
            //     })
            // }

            // initMap();

            //  Init Mape here
            function initMap() {
                var myLatLng = { lat: -6.210391893814135, lng: 106.84542264984498 };
                var zoom = 11
                var from_local = localStorage.getItem('load_single_vehicle');
                if(from_local){
                  zoom = 18;
                  myLatLng = { lat: parseFloat(localStorage.getItem('latitude')), lng: parseFloat(localStorage.getItem('longitude'))}; 
                }

                
                const map = new google.maps.Map(document.getElementById("map"), {
                    zoom: zoom,
                    center: myLatLng,
                    mapId: "4504f8b37365c3d0",
                });

                const infoWindow = new google.maps.InfoWindow({
                  content: "",
                  disableAutoPan: true,
                });
                
                
                for (let i = 0; i < _.size(data['status']); i++) {
                  const label = data['status'][i]['license_plate'];

                  const priceTag = document.createElement("div");
                  priceTag.className = "price-tag";
                  priceTag.textContent = label

                  // const marker = new google.maps.Marker({
                  //       position: {
                  //           'lat': parseFloat(data['status'][i]['latitude']),
                  //           'lng': parseFloat(data['status'][i]['longitude'])
                  //       },
                  //       map,
                  //       title: data['status'][i]['license_plate'],
                  //       animation: google.maps.Animation.DROP,
                  //   });
                  // marker.addListener("click", () => {
                  //   infoWindow.setContent(label);
                  //   infoWindow.open(map, marker);
                  // });
                  // return marker;

                  const markerView = new google.maps.marker.AdvancedMarkerView({
                    map,
                    position: {
                      'lat': parseFloat(data['status'][i]['latitude']),
                      'lng': parseFloat(data['status'][i]['longitude'])
                    },
                    content: priceTag,
                  });

                  if(data['status'][i]['status'] == 'Moving'){
                      // A marker with a with a URL pointing to a PNG.
                      const beachFlagImg = document.createElement("img");
                      beachFlagImg.className = "car-icon";

                      beachFlagImg.src =
                        "/equip3_asset_fms_tracking/static/car-green-32.png";


                      const beachFlagMarkerView = new google.maps.marker.AdvancedMarkerView({
                        map,
                        position: {
                          'lat': parseFloat(data['status'][i]['latitude']),
                          'lng': parseFloat(data['status'][i]['longitude'])
                        },
                        content: beachFlagImg,
                      });
                  }
                  else if (data['status'][i]['status'] == 'Parking') {
                    // A marker with a with a URL pointing to a PNG.
                    const beachFlagImg = document.createElement("img");
                    beachFlagImg.className = "car-icon";

                    beachFlagImg.src =
                      "/equip3_asset_fms_tracking/static/car-red-32.png";


                    const beachFlagMarkerView = new google.maps.marker.AdvancedMarkerView({
                      map,
                      position: {
                        'lat': parseFloat(data['status'][i]['latitude']),
                        'lng': parseFloat(data['status'][i]['longitude'])
                      },
                      content: beachFlagImg,
                    });

                  }
                  else if (data['status'][i]['status'] == 'Parking') {
                    // A marker with a with a URL pointing to a PNG.
                    const beachFlagImg = document.createElement("img");
                    beachFlagImg.className = "car-icon";

                    beachFlagImg.src =
                      "/equip3_asset_fms_tracking/static/car-black-32.png";


                    const beachFlagMarkerView = new google.maps.marker.AdvancedMarkerView({
                      map,
                      position: {
                        'lat': parseFloat(data['status'][i]['latitude']),
                        'lng': parseFloat(data['status'][i]['longitude'])
                      },
                      content: beachFlagImg,
                    });

                  }
                  else if (data['status'][i]['status'] == 'Idle') {
                    // A marker with a with a URL pointing to a PNG.
                    const beachFlagImg = document.createElement("img");
                    beachFlagImg.className = "car-icon";

                    beachFlagImg.src =
                      "/equip3_asset_fms_tracking/static/car-yellow-32.png";


                    const beachFlagMarkerView = new google.maps.marker.AdvancedMarkerView({
                      map,
                      position: {
                        'lat': parseFloat(data['status'][i]['latitude']),
                        'lng': parseFloat(data['status'][i]['longitude'])
                      },
                      content: beachFlagImg,
                    });

                  }
                }
            }
                
            initMap()
            search_vehicle_asset()
            
        })
    }

    function filterIt(arr, searchKey) {
      return arr.filter(function(obj) {
        return Object.keys(obj).some(function(key) {
          return obj[key].includes(searchKey);
        })
      });
    }


    var timeSince = function(date) {
        // console.log(date)
        if (typeof date !== 'object') {
          date = new Date(date);
        }
      
        var seconds = Math.floor((new Date() - date) / 1000);
        var intervalType;
      
        var interval = Math.floor(seconds / 31536000);
        if (interval >= 1) {
          intervalType = 'year';
        } else {
          interval = Math.floor(seconds / 2592000);
          if (interval >= 1) {
            intervalType = 'month';
          } else {
            interval = Math.floor(seconds / 86400);
            if (interval >= 1) {
              intervalType = 'day';
            } else {
              interval = Math.floor(seconds / 3600);
              if (interval >= 1) {
                intervalType = "hour";
              } else {
                interval = Math.floor(seconds / 60);
                if (interval >= 1) {
                  intervalType = "minute";
                } else {
                  interval = seconds;
                  intervalType = "second";
                }
              }
            }
          }
        }
      
        if (interval > 1 || interval === 0) {
          intervalType += 's';
        }
      
        return interval + ' ' + intervalType;
      };

    function search_vehicle_asset(){
        let input, filter, td, i, txtValue;
        // input = document.getElementById('input-plat');
        // filter = input.value.toUpperCase();
        filter = localStorage.getItem('search_key');
        if(filter){
          td = $(".display_name").find("b");
          // console.log(td)

          for (i = 0; i < td.length; i++) {
              txtValue = td[i].innerText || td[i].outerText;
              if (txtValue.toUpperCase().indexOf(filter) > -1) {
                  td[i].parentElement.parentElement.style.display = "";
              } else {
                  td[i].parentElement.parentElement.style.display = "none";
              }
          }
        }else{
          td = $(".display_name").find("b");
          // console.log(td)

          for (i = 0; i < td.length; i++) {
            td[i].parentElement.parentElement.style.display = "";
          }
        }
    }
    
    
    
    // --- Main function
    function timeAgo(string) {
      var split_datetime = string.split(' ')
      var split_date = split_datetime[0].split('-')
      var date_o = split_date[2] + '-' + split_date[1] + '-' + split_date[0] + ' ' + split_datetime[1] + ' GMT+0700'
      // 22-12-2022 20:40:20
      // format("YYYY-MM-DD HH:mm")
      // console.log(date)

      // const s = '2022-12-22 20:42:48';
      const date = new Date(date_o);
      // console.log(string)
      // console.log(date)
      // console.log(d);
      
      // var seconds = Math.floor((new Date() - date) / 1000);

      // var interval = seconds / 31536000;

      // if (interval > 1) {
      //   return Math.floor(interval) + " years";
      // }
      // interval = seconds / 2592000;
      // if (interval > 1) {
      //   return Math.floor(interval) + " months";
      // }
      // interval = seconds / 86400;
      // if (interval > 1) {
      //   return Math.floor(interval) + " days";
      // }
      // interval = seconds / 3600;
      // if (interval > 1) {
      //   return Math.floor(interval) + " hours";
      // }
      // interval = seconds / 60;
      // if (interval > 1) {
      //   return Math.floor(interval) + " minutes";
      // }
      // return Math.floor(seconds) + " seconds";
      return moment(date).fromNow()
    }

    $(document).ready(function(){
      if ($('#asset_tracking_page').length > 0){
        localStorage.setItem('search_key', '');
        localStorage.setItem('plate', '');
        localStorage.setItem('load_single_vehicle', '');
        get_vehicle_asset()
  
        window.get_vehicle = setTimeout( async function(){
        get_vehicle_asset()}, 20000);
      }
      
      
      // if ($('#asset_tracking_page').length){
      //   localStorage.setItem('search_key', '');
      //   localStorage.setItem('plate', '');
      //   get_vehicle_asset()

      //   window.get_vehicle = setInterval(function() {
      //     get_vehicle_asset();
      //   }, 20000); 
      // }
     

    })

    $("#input-plat").keyup(function(){
      localStorage.setItem('search_key', document.getElementById('input-plat').value.toUpperCase());
      search_vehicle_asset()
    })

    function load_single_vehicle(){
      var plate_ls = localStorage.getItem('plate');
      console.log(`plate from ls ${plate_ls}`)

      ajax.jsonRpc("/asset", "call", {}).then(function(data){
        console.log(data)
        // Load vehicle data 
        for (let i = 0; i < _.size(data['status']); i++) {
          console.log(`${data['status'][i]['license_plate']} and ${plate_ls}`)
          if (data['status'][i]['license_plate'] == plate_ls){
            console.log('yes, matched!')

            var plate = data['status'][i]['license_plate'];
            var latitude = data['status'][i]['latitude'];
            var longitude = data['status'][i]['longitude'];
            var status = data['status'][i]['status'];

            const myLatLng = { lat: parseFloat(latitude), lng: parseFloat(longitude) };
            const map = new google.maps.Map(document.getElementById("map"), {
                zoom: 18,
                center: myLatLng,
                mapId: "4504f8b37365c3d0",
            });


            const label = plate;
            const priceTag = document.createElement("div");
            priceTag.className = "price-tag";
            priceTag.textContent = label


            const markerView = new google.maps.marker.AdvancedMarkerView({
              map,
              position: {
                'lat': parseFloat(latitude),
                'lng': parseFloat(longitude)
              },
              content: priceTag,
            });

            if(status == 'Moving'){
                // A marker with a with a URL pointing to a PNG.
                const beachFlagImg = document.createElement("img");
                beachFlagImg.className = "car-icon";

                beachFlagImg.src =
                  "/equip3_asset_fms_tracking/static/sport-car.png";


                const beachFlagMarkerView = new google.maps.marker.AdvancedMarkerView({
                  map,
                  position: {
                    'lat': parseFloat(latitude),
                    'lng': parseFloat(longitude)
                  },
                  content: beachFlagImg,
                });
            }
            else if (status == 'Parking') {
              // A marker with a with a URL pointing to a PNG.
              const beachFlagImg = document.createElement("img");
              beachFlagImg.className = "car-icon";

              beachFlagImg.src =
                "/equip3_asset_fms_tracking/static/sedan.png";


              const beachFlagMarkerView = new google.maps.marker.AdvancedMarkerView({
                map,
                position: {
                  'lat': parseFloat(latitude),
                  'lng': parseFloat(longitude)
                },
                content: beachFlagImg,
              });

            }

          }

        }
      })
      

    }

    $(document.body).on('click', '.vehicle_row' ,function(){
      clearInterval(window.get_vehicle);
      

      var plate = $(this).attr('data-plate');
      var latitude = $(this).attr('data-latitude');
      var longitude = $(this).attr('data-longitude');
      var status = $(this).attr('data-status');

      localStorage.setItem('load_single_vehicle', true);
      localStorage.setItem('plate', plate);
      localStorage.setItem('latitude', latitude);
      localStorage.setItem('longitude', longitude);
      localStorage.setItem('status', status);
      console.log("click", plate)

      get_vehicle_asset()
      window.get_vehicle_sin = setTimeout( async function() {
        console.log('setInterval btn click', new Date().toLocaleString())
        get_vehicle_asset();
      }, 20000);
      // window.get_single_vehicle = setInterval(function() {
      //   load_single_vehicle();
      // }, 10000);

      // const myLatLng = { lat: parseFloat(latitude), lng: parseFloat(longitude) };
      // const map = new google.maps.Map(document.getElementById("map"), {
      //     zoom: 18,
      //     center: myLatLng,
      //     mapId: "4504f8b37365c3d0",
      // });


      // const label = plate;
      // const priceTag = document.createElement("div");
      // priceTag.className = "price-tag";
      // priceTag.textContent = label


      // const markerView = new google.maps.marker.AdvancedMarkerView({
      //   map,
      //   position: {
      //     'lat': parseFloat(latitude),
      //     'lng': parseFloat(longitude)
      //   },
      //   content: priceTag,
      // });

      // if(status == 'Moving'){
      //     // A marker with a with a URL pointing to a PNG.
      //     const beachFlagImg = document.createElement("img");
      //     beachFlagImg.className = "car-icon";

      //     beachFlagImg.src =
      //       "/equip3_asset_fms_tracking/static/sport-car.png";


      //     const beachFlagMarkerView = new google.maps.marker.AdvancedMarkerView({
      //       map,
      //       position: {
      //         'lat': parseFloat(latitude),
      //         'lng': parseFloat(longitude)
      //       },
      //       content: beachFlagImg,
      //     });
      // }
      // else if (status == 'Parking') {
      //   // A marker with a with a URL pointing to a PNG.
      //   const beachFlagImg = document.createElement("img");
      //   beachFlagImg.className = "car-icon";

      //   beachFlagImg.src =
      //     "/equip3_asset_fms_tracking/static/sedan.png";


      //   const beachFlagMarkerView = new google.maps.marker.AdvancedMarkerView({
      //     map,
      //     position: {
      //       'lat': parseFloat(latitude),
      //       'lng': parseFloat(longitude)
      //     },
      //     content: beachFlagImg,
      //   });

      // }

    })
})