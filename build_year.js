L.TimeDimension.Layer.CP = L.TimeDimension.Layer.GeoJson.extend({
    _getFeatureTimes: function(feature) {
        if (!feature.properties) {
            return [];
        }
        if (feature.properties.hasOwnProperty('time')) {
            return [feature.properties.time * 1000];
        }
        return [];
    },
    _getFeatureBetweenDates: function(feature, minTime, maxTime) {
        var featureStringTimes = this._getFeatureTimes(feature);
        if (featureStringTimes.length == 0) {
            return feature;
        }
        var featureTimes = [];
        for (var i = 0, l = featureStringTimes.length; i < l; i++) {
            var time = featureStringTimes[i]
            if (typeof time == 'string' || time instanceof String) {
                time = Date.parse(time.trim());
            }
            featureTimes.push(time);
        }
        if (featureTimes[0] > maxTime || featureTimes[l - 1] < minTime) {
            return null;
        }
        return feature;
    },
});

L.timeDimension.layer.cP = function(layer, options) {
    return new L.TimeDimension.Layer.CP(layer, options);
};

function slugify(text)
{
  return text.toString().toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^\w\-]+/g, '')
    .replace(/\-\-+/g, '-')
    .replace(/^-+/, '')
    .replace(/-+$/, '');
}

var startDate = new Date();
startDate.setUTCHours(0, 0, 0, 0);
var map = L.map('map', {
    zoom: 7,
    preferCanvas: true,
    maxBounds: [[-90, -200], [90, 180]],
    maxZoom: 17,
    minZoom: 2,
    fullscreenControl: true,
    fullscreenControlOptions: {
       position: 'bottomleft'
    },
    attributionControl: false,
    attributionControlOptions: {
       prefix: ''
    },
    zoomControl: true,
    timeDimensionControl: false,
    timeDimensionControlOptions: {
        position: 'topleft',
        autoPlay: true,
        displayDate: true,
        timeSlider: true,
        loopButton: true,
        minSpeed: 1,
        maxSpeed: 5,
        speedStep: 1,
        playerOptions: {
            transitionTime: 125,
            startOver: true,
            loop: false,
        }
    },
    timeDimension: true
});

    var cLegend = L.control({
        position: 'bottomright'
    });
    cLegend.onAdd = function(map) {
        var div = L.DomUtil.create('div', 'info legend');
        div.innerHTML += '<span="small"><strong>{{wcount}} wildfires</strong> in <strong>{{yyyy}}</strong></span>';
        return div;
    };
    //cLegend.addTo(map);

var gC = chroma.scale(['violet','indigo','blue','green','yellow','orange','red']).mode('lch').colors(447+1);

$.getJSON('data.json.packed').done(addTopoData);

L.TopoJSON = L.GeoJSON.extend({
  addData: function(jsonData) {    
    if (jsonData.type === "Topology") {
      for (key in jsonData.objects) {
        geojson = topojson.feature(jsonData, jsonData.objects[key]);
        L.GeoJSON.prototype.addData.call(this, geojson);
      }
    }    
    else {
      L.GeoJSON.prototype.addData.call(this, jsonData);
    }
  }  
});

var plain = {
    'fillColor': 'FireBrick',
    'color': 'FireBrick',
    'fillOpacity': 0.2,
    'weight': 1.5,
    'opacity': 1
};

var highlighted = {
    'fillColor': 'FireBrick',
    'color': 'Black',
    'fillOpacity': 0.0,
    'weight': 3,
    'opacity': 1
};

var fSearch = [];
$(window).resize(function() {
  sizeLayerControl();
});

$(document).on("click", ".feature-row", function(e) {
  $(document).off("mouseout", ".feature-row", clearHighlight);
  sidebarClick(parseInt($(this).attr("id"), 10));
});

if ( !("ontouchstart" in window) ) {
  $(document).on("mouseover", ".feature-row", function(e) {
    //layer.setStyle(highlighted);
    //highlight.clearLayers().addLayer(L.circleMarker([$(this).attr("lat"), $(this).attr("lng")], highlightStyle));
  });
}

$(document).on("mouseout", ".feature-row", clearHighlight);

$("#sidebar-toggle-btn").click(function() {
  animateSidebar();
  return false;
});

$("#sidebar-hide-btn").click(function() {
  animateSidebar();
  return false;
});

function animateSidebar() {
  $("#sidebar").animate({
    width: "toggle"
  }, 350, function() {
    map.invalidateSize();
  });
}

function sizeLayerControl() {
  $(".leaflet-control-layers").css("max-height", $("#map").height() - 50);
}

function clearHighlight() {
  //highlight.clearLayers();
  layer.setStyle(plain);
}

function sidebarClick(id) {
  var layer = topoLayer.getLayer(id);
  map.fitBounds(layer.getBounds());
  layer.fire("click");
  if (document.body.clientWidth <= 767) {
    $("#sidebar").hide();
    map.invalidateSize();
  }
}

function syncSidebar() {
  $("#feature-list tbody").empty();
  fs.eachLayer(function (layer) {
    if (map.hasLayer(wcmLayer)) {
      if (map.getBounds().contains(layer.getBounds())) {
        $("#feature-list tbody").append('<tr class="feature-row" id="' + L.stamp(layer) + '" geom="' + layer.geometry + '"><td class="dot" style="vertical-align:middle;padding:3px;"><div class="prog-icon" style="float:left;height:11px;width:11px;margin-top:7px;margin-right:5px;"></div></td><td class="feature-number"><a href="/fuels/' + layer.feature.properties.u + '>"' + layer.feature.properties.u + '</a></td><td class="feature-name">' + layer.feature.properties.i + '</td></tr>');
      }
    }
  });
  featureList = new List("features", {
    valueNames: ["feature-name"]
  });
  featureList.sort("feature-name", {
    order: "asc"
  });
}

topoLayer = new L.TopoJSON(null, {
                    style: function(feature) {
                        return { 
                            color: 'FireBrick',
                            fillColor:  'FireBrick',
                            fillOpacity: 0.2,
                            weight: 1.5,
                            opacity: 0.8
                        };
                    },
                  onEachFeature: function (feature, layer) {
                    if (feature.properties) {
                      var content = "<span class='small'><strong><a class='url-break text-prog' href='/fuels/{{yyyy}}/" + feature.properties.u + "/" + "' target='_blank'><span style='color:Black'>" + feature.properties.u + "</a></span></strong></span><br><span class='small'>Name: <strong>" + feature.properties.i + "</strong><br>Acres: <strong>" + feature.properties.a + "</strong><br>Status: <strong>" + feature.properties.s + "</strong></span>";
                      layer.on({
                        click: function (e) {
                          $("#perims").html(content);
                            topoLayer.setStyle(plain);
                            layer.setStyle(highlighted);
                        },
                      });
                  $("#feature-list tbody").append('<tr class="feature-row" id="' + L.stamp(layer) + '" geom="' + layer.geometry + '"><td class="dot" style="vertical-align:middle;padding:3px;"></td><td class="feature-number small">' + layer.feature.properties.u + '</td><td class="feature-name small">' + layer.feature.properties.i + '</td></tr>');
                  fSearch.push({
                    number: layer.feature.properties.u,
                    name: layer.feature.properties.i,
                    source: "fs",
                    id: L.stamp(layer)
                  });
                    }
                  }
                });

function addTopoData(topoData){
  topoLayer.addData(topoData);
    topoLayer.addTo(map);
    map.fitBounds(topoLayer.getBounds());

    var cFull = L.control({
        position: 'bottomleft'
    });
    cFull.onAdd = function(map) {
        var div = L.DomUtil.create('div', 'leaflet-control-zoom leaflet-bar leaflet-control');
        div.id += 'full-extent-btn';
        div.innerHTML += '<a class="leaflet-control-zoom-home home-icon" href="#" title="Full extent" role="button" aria-label="Full extent"><span class=\'glyphicon glyphicon-bookmark small\'></span></a>';
        return div;
    };
    cFull.addTo(map);

    $("#full-extent-btn").click(function() {
      map.fitBounds(topoLayer.getBounds());
      return false;
    });
}

var baseLayers = getCommonBaseLayers(map);
L.control.layers(baseLayers, {}).addTo(map);

    var info = L.control({
        position: 'topleft'
    });
    info.onAdd = function(map) {
        var div = L.DomUtil.create('div', 'info');
        div.id += 'perims';
        div.innerHTML += '<small></small>';
        return div;
    };
    info.addTo(map);

$(document).one("ajaxStop", function () {
  $("#loading").hide();
  sizeLayerControl();
  featureList = new List("features", {valueNames: ["feature-name"]});
  featureList.sort("feature-name", {order:"asc"});
});

$("#about-btn").click(function() {
  $("#aboutModal").modal("show");
  $(".navbar-collapse.in").collapse("hide");
  return false;
});
