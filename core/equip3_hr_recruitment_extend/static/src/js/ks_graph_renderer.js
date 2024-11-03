odoo.define("ks_custom_report.GraphRenderer", function(require){

    var GraphRenderer = require("web.GraphRenderer");
    var CHART_TYPES = ['pie', 'bar', 'line','scatter'];

    var MyCOLORS = ["#556ee6", "#f1b44c", "#50a5f1", "#ffbb78", "#34c38f", "#98df8a", "#d62728",
        "#ff9896", "#9467bd", "#c5b0d5", "#8c564b", "#c49c94", "#e377c2", "#f7b6d2",
        "#7f7f7f", "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5"];
    var MyCOLOR_NB = MyCOLORS.length;

    function hexToRGBA(hex, opacity) {
        var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        var rgb = result.slice(1, 4).map(function (n) {
            return parseInt(n, 16);
        }).join(',');
        return 'rgba(' + rgb + ',' + opacity + ')';
    }

    GraphRenderer.include({

        ksDoAction: function(domain){
            this.getParent().model.getKsmodelDomain(domain);
        },

        _getMyColor: function (index) {
            return MyCOLORS[index % MyCOLOR_NB];
        },

        _renderBarChart: function(dataPoints){
            var self = this;
      

            // prepare data
            var data = this._prepareData(dataPoints);

            data.datasets.forEach(function (dataset, index) {
                // used when stacked
                dataset.stack = self.state.stacked ? self.state.origins[dataset.originIndex] : undefined;
                // set dataset color
                var color = self._getMyColor(index);
                dataset.backgroundColor = color;
            });

            // prepare options
            var options = this._prepareOptions(data.datasets.length);

            // create chart
            var ctx = document.getElementById(this.chartId);
            var scatter = false
            if(this.arch){
                if(this.arch.attrs){
                    if(this.arch.attrs.string=='Quadrant Analysis'){
                        scatter = true
                        $('div[role="toolbar"].o_cp_buttons').hide()
                        // $('.o_control_panel .o_cp_top_right').hide()
                        $('.o_control_panel').css("min-height", "unset");
                        $('.o_control_panel .o_group_by_menu').hide()
                        // $('.o_control_panel div[role="search"]').hide()
                        // $('.o_control_panel .o_cp_bottom').css("position", "absolute");
                        // $('.o_control_panel .o_cp_bottom').css("top", "50px");
                        // $('.o_control_panel .o_cp_bottom').css("z-index", "9");
                        // $('.o_control_panel .o_cp_bottom').css("right", "0");
                    }
                }
            }
            if (scatter){
                this._rpc({
                    model: 'hr.applicant',
                    method: 'get_all_quadrant_score',
                    args:this.state.domains,
          
                }).then(function (dataresult) {
                    get_all_quadrant_score = dataresult['result']
                    options.plugins= {
                      quadrants: {
                        topLeft: 'red',
                        topRight: 'blue',
                        bottomRight: 'green',
                        bottomLeft: 'yellow',
                      }
                    }
                    const quadrants = {
                          id: 'quadrants',
                          beforeDraw(chart, args, options) {
                            const {ctx, chartArea: {left, top, right, bottom}, scales: {x, y}} = chart;
                            const p = chart.scales['x-axis-1']
                            const t = chart.scales['y-axis-1']
                            const midX = p.getPixelForValue(0);
                            const midY = t.getPixelForValue(0);

                            ctx.save();
                            // ctx.fillStyle = options.topLeft;
                            ctx.strokeRect(left, top, midX - left, midY - top);
                            
                            // ctx.fillStyle = options.topRight;
                            ctx.strokeRect(midX, top, right - midX, midY - top);
                            // ctx.fillStyle = options.bottomRight;
                            ctx.strokeRect(midX, midY, right - midX, bottom - midY);
                            // ctx.fillStyle = options.bottomLeft;
                            ctx.strokeRect(left, midY, midX - left, bottom - midY);
                            ctx.restore();
                          }
                        };

                    const datalabel = {
                          id: 'datalabel',
                          afterDatasetsDraw: function (chart, args, options) {
                             var ctx = chart.ctx
                             chart.data.datasets.forEach(function (dataset, i) {
                               var meta = chart.getDatasetMeta(i)
                               if (meta.type == 'scatter') {
                                 meta.data.forEach(function (element, index) {
                                   ctx.textAlign = 'center'
                                   ctx.textBaseline = 'middle'
                                   var position = element.tooltipPosition()
                                   if(dataset.label.length>0){
                                    ctx.fillStyle = "#000000";
                                    ctx.font = "bold 11px verdana, sans-serif ";
                                    var datalong = [33,30,27,24,21,18]
                                    ctx.fillText(dataset.label.toString(), position.x, position.y+datalong[dataset.datalong])
                                   }
                                    
                                 })
                               }
                             })
                           },
                        };

                    if(get_all_quadrant_score.length > 0){
                        var categ_settle = {
                            'Personality, Qualification, Skillset Fit with Fast Response':{'x':90,'y':20},
                            'Skillset and Qualification Fit with Lesser Personality Fit':{'x':-90,'y':20},
                            'Personality Fit but Less Qualified':{'x':15,'y':-70},
                            'Least Fit in Terms of Personality and Qualifications':{'x':-90,'y':-70},
                        }
                        var rcd_data = [{
                              label: ' ',
                              data: [{x:100,y:100},{x:-100,y:-100}],
                             pointRadius: 2,
                              backgroundColor: 'white',
                            }]
                        var label_arr = []
                        
                        var countaddset = [30,27,24,21,18,15]
                        var countcolum = [20,20,16,16,8,8]

                        for (let i = 0; i < get_all_quadrant_score.length; i++) {
                             var colorR = Math.floor((Math.random() * 256));
                              var colorG = Math.floor((Math.random() * 256));
                              var colorB = Math.floor((Math.random() * 256));
                        var pointRadiusset1 = [24,20,16,12,8,4]
                          var pointRadiusget = pointRadiusset1[dataresult[get_all_quadrant_score[i]['category_name']]]
                          
                          rcd_data.push({
                            label:get_all_quadrant_score[i]['name'],
                            pointRadius: pointRadiusget,
                            idbubble:get_all_quadrant_score[i]['id'],
                            backgroundColor: "rgb(" + colorR + "," + colorG + "," + colorB + ")",
                            data: [{x:categ_settle[get_all_quadrant_score[i]['category_name']]['x'],y:categ_settle[get_all_quadrant_score[i]['category_name']]['y'],}],
                            indexa:get_all_quadrant_score[i]['line'][0],
                            indexb:get_all_quadrant_score[i]['line'][1],
                            datalong:dataresult[get_all_quadrant_score[i]['category_name']],
                            data_y:categ_settle[get_all_quadrant_score[i]['category_name']]['y'],
                          })
                          label_arr.push(get_all_quadrant_score[i]['name'])
                          var countadd = countaddset[dataresult[get_all_quadrant_score[i]['category_name']]]
                          var countcolumset = countcolum[dataresult[get_all_quadrant_score[i]['category_name']]]
                          categ_settle[get_all_quadrant_score[i]['category_name']]['y']+=countadd


                          if((categ_settle[get_all_quadrant_score[i]['category_name']]['y'])>=90){
                            if(get_all_quadrant_score[i]['category_name'] == 'Skillset and Qualification Fit with Lesser Personality Fit' || get_all_quadrant_score[i]['category_name'] == 'Personality, Qualification, Skillset Fit with Fast Response'){
                                categ_settle[get_all_quadrant_score[i]['category_name']]['y'] = 20
                                categ_settle[get_all_quadrant_score[i]['category_name']]['x'] += countcolumset
                            }
                          }

                          if((categ_settle[get_all_quadrant_score[i]['category_name']]['y'])>=-10){
    
                            if(get_all_quadrant_score[i]['category_name'] == 'Least Fit in Terms of Personality and Qualifications' || get_all_quadrant_score[i]['category_name'] == 'Personality Fit but Less Qualified'){
                                categ_settle[get_all_quadrant_score[i]['category_name']]['y'] = -70
                                categ_settle[get_all_quadrant_score[i]['category_name']]['x'] += countcolumset
                            }
                          }
                        }
                    }

                    data1 = {datasets: rcd_data,label:label_arr}
                    
                    self.chart = new Chart(ctx, {
                        type: 'scatter',
                        data: data1,
                        options: {
                            onHover: function(e) {
                                var point = this.getElementAtEvent(e);
                                 if (point.length) e.target.style.cursor = 'pointer';
                                 else e.target.style.cursor = 'default';
                            },
                            onResize: function(e) {

                                 e.config.data.datasets.forEach(function (dataset, index) {
                                    var fontsize = 12
                                    if(dataset.backgroundColor != 'white'){
                                        var zoomRatio = Math.round(window.devicePixelRatio * 100);
                                        var pointRadiusset = [24,20,16,12,8,4]
                                        var pointRadiusnumber = pointRadiusset[dataset.datalong]
                                        dataset.data['y'] = dataset.data_y
                                        if (zoomRatio >= 100) {
                                            pointRadiusnumber-=3
                                            dataset.data['y'] += 3
                                          }
                                          // if (zoomRatio >= 125) {
                                          //   pointRadiusnumber-=4
                       
                                          // }
                                          // if (zoomRatio >= 155) {
                                          //   pointRadiusnumber+=4
                                          //   dataset.data['y'] += 6
                                          // }
                                        if (zoomRatio <= 80) {
                                            pointRadiusnumber+=5
                                            // dataset.data['y'] -= 4
                                          }
                                       
                                       
                                        dataset.pointRadius = pointRadiusnumber;
                                 
                                    }
                                });
                            },

                             onClick: function(e) {
                                var element = this.getElementAtEvent(e);

                                // If you click on at least 1 element ...
                                if (element.length > 0) {
                                    var idbubble = this.config.data.datasets[element[0]._datasetIndex].idbubble;
                                    var label_bubble = this.config.data.datasets[element[0]._datasetIndex].label;
                                    self.do_action({
                                        name: label_bubble,
                                        view_type: 'form',
                                        view_mode: 'form',
                                        views:[[false, 'form']],
                                        res_model: 'hr.applicant',
                                        res_id: idbubble,
                                        type: 'ir.actions.act_window',
                                        target: 'current',
                                    });    
                                
                                }
                            },

                             legend: {
                                    display: false,

                                },
                                scales: {
                                    xAxes: [{
                                        ticks: {
                                            display: false
                                        },
                                        display: false,
                                    }],
                                    yAxes: [{
                                        ticks: {
                                            display: false
                                        },
                                        display: false,
                                    }],
                                },
                            tooltips: {
                               callbacks: {
                                  label: function(t, d) {
                                     var xLabel = [d.datasets[t.datasetIndex].label,d.datasets[t.datasetIndex].indexa,d.datasets[t.datasetIndex].indexb];
                                    console.log(xLabel,'xLabelxLabel')
                                     return xLabel;
                                  }
                               }
                            },
                        plugins: {
                          quadrants: {
                            topLeft: 'white',
                            topRight: 'white',
                            bottomRight: 'white',
                            bottomLeft: 'white',
                          },
                          
                        }
                      },

                         plugins: [quadrants,datalabel]
                    });
                    $('.chartjs-render-monitor').css("padding-left",'52px');
                    $('.chartjs-render-monitor').css("padding-right",'10px');
                     $('.chartjs-render-monitor').css("padding-bottom",'3%');
                    $( "<p style='font-size: 11px !important; font-weight: bold; left: 95px; margin-top: -6%; position: absolute;'>Least Fit in Terms of Personality and Qualifications</p>" ).insertAfter(".chartjs-render-monitor");
                     $( "<p style='font-size: 11px !important; font-weight: bold; left: 54%; margin-top: -6%; position: absolute;'>Personality Fit but Less Qualified</p>" ).insertAfter(".chartjs-render-monitor");

                     $( "<p style='font-size: 11px !important; font-weight: bold; left: 54%; top: 20px; position: absolute;'>Personality, Qualification, Skillset Fit with Fast Response</p>" ).insertBefore(".chartjs-render-monitor");
                     $( "<p style='font-size: 11px !important; font-weight: bold; top: 20px;left: 95px; position: absolute;'>Skillset and Qualification Fit with Lesser Personality Fit</p>" ).insertBefore(".chartjs-render-monitor");
                    $( "<p style='font-size: 16px !important; font-weight: bold; margin-top: -30%; left: -88px; position: absolute; -webkit-transform: rotate( 270deg); -moz-transform: rotate(270deg); -o-transform: rotate(270deg); -ms-transform: rotate(270deg); transform: rotate( 270deg);'><b>Qualifications & Quantitave Fit</b></p>" ).insertAfter(".chartjs-render-monitor");
                    $( "<p style='margin-top: -3%;font-size: 16px !important; font-weight: bold; position: absolute; text-align: center; width: 100%;'><b>Personality & Qualitative Fit</b></p>" ).insertAfter(".chartjs-render-monitor");

                });



            }
            else{
                this.chart = new Chart(ctx, {
                    type: 'bar',
                    data: data,
                    options: options,
                });

                $("#"+this.chartId).click(function(e) {
                    activePoint = self.chart.getElementAtEvent(e)[0];
                    if (activePoint){
                        var domain = activePoint._chart.data.domains[activePoint._index];
                        self.ksDoAction(domain);
                    }
                });
            }
                

                

            return undefined;
        },

        _renderPieChart: function(){
            var self = this;
            this._super.apply(this, arguments);
            $("#"+this.chartId).click(function(e) {
                activePoint = self.chart.getElementAtEvent(e)[0];
                if(activePoint && activePoint._chart.data.domains){
                    var domain = activePoint._chart.data.domains[activePoint._index]
                    self.ksDoAction(domain);
                }
            });

        },

        _renderLineChart: function(){
            var self = this;
            this._super.apply(this, arguments);
            $("#"+this.chartId).click(function(e) {
                activePoint = self.chart.getElementAtEvent(e)[0]
                if(activePoint){
                domain = activePoint._chart.data.domains[activePoint._index]
                self.ksDoAction(domain);
                }
            });
        },

        _prepareData: function(dataPoints){
            var self = this;
            var data = this._super.apply(this, arguments);

            var domains = _.values(dataPoints.reduce(
                function (acc, dataPt) {
                    var datasetLabel = self._getDatasetLabel(dataPt);
                    if (!('data' in acc)) {
                       acc['data'] = new Array(self._getDatasetDataLength(dataPt.originIndex, data.labels.length)).fill(0)
                    }
                    var label = self._getLabel(dataPt);
                    var labelIndex = self._indexOf(data.labels, label);
                    acc.data[labelIndex] = dataPt.domain;
                    return acc;
                },
                {}
            ));

            data['domains'] = domains[0]
            return data
        },
    });
});